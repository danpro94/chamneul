"""SPEC-006 TASK-002 — liveness와 readiness (ADR-010)."""

from unittest.mock import patch

from django.db import InterfaceError, OperationalError, connections
from django.test import TestCase, override_settings

HEALTHZ = "/healthz"
READYZ = "/readyz"

READY = {"status": "ok", "checks": {"database": "ok"}}
UNAVAILABLE = {"status": "unavailable", "checks": {"database": "unavailable"}}

# kubelet·ALB가 보내는 모양: 파드 IP를 Host로, 평문 HTTP로.
POD_IP_HOST = "10.0.3.17:8000"

# prod.py에서 probe를 301·400으로 만드는 두 설정만 재현한다(prod.py는 시크릿
# 환경변수 없이는 import되지 않는다).
prod_security = override_settings(
    DEBUG=False,
    ALLOWED_HOSTS=["chamneul.com"],
    SECURE_SSL_REDIRECT=True,
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
)

# 실제 psycopg 오류처럼 호스트·주소·포트가 들어 있다 — 응답에 새면 안 되는 것들.
CONNECT_REFUSED = OperationalError(
    'connection to server at "db" (172.18.0.2), port 5432 failed: Connection refused'
)


CONNECTION_CLOSED = InterfaceError("connection already closed")


def database_down(error=CONNECT_REFUSED):
    """연결 단계에서 실패한다 — DB가 꺼졌을 때."""
    return patch.object(connections["default"], "ensure_connection", side_effect=error)


def query_fails(error=CONNECTION_CLOSED):
    """연결 객체는 있는데 질의에서 실패한다 — DB가 재시작돼, 워커가
    CONN_MAX_AGE 동안 들고 있던 연결이 끊겼을 때. 연결만 확인하면 놓친다."""
    return patch("django.db.backends.utils.CursorWrapper.execute", side_effect=error)


class ReadinessTests(TestCase):
    """AC-2 — readiness는 DB를 보고, liveness는 보지 않는다."""

    def test_ready_when_the_database_answers(self):
        response = self.client.get(READYZ)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), READY)

    def test_unavailable_without_saying_why(self):
        """연결 거부(OperationalError)와 끊긴 연결(InterfaceError)은 다른 계열이고
        실패하는 단계도 다르다 — 둘 다 503이어야 한다. 본문은 고정이고, 원인은
        서버 로그에만 남는다."""
        failures = [
            ("connect", database_down, "OperationalError"),
            ("query", query_fails, "InterfaceError"),
        ]
        for stage, failure, error_name in failures:
            with self.subTest(stage):
                with failure(), self.assertLogs("config.health", "WARNING") as logs:
                    response = self.client.get(READYZ)

                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), UNAVAILABLE)
                self.assertIn(error_name, logs.output[0])

    def test_liveness_stays_up_while_the_database_is_down(self):
        """liveness가 DB를 보면 DB 장애 한 번에 모든 파드가 재시작된다(ADR-010)."""
        with database_down():
            response = self.client.get(HEALTHZ)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


@prod_security
class ProbesBehindProdSecurityTests(TestCase):
    """AC-2 — 두 probe는 HTTPS 리다이렉트와 Host 검증보다 먼저 답한다."""

    def test_premise_this_setup_refuses_a_pod_ip_and_plain_http(self):
        """전제: 이 설정이 정말 400·301을 만든다. 아니면 아래 테스트는 아무것도
        증명하지 않는다."""
        with self.assertLogs("django.security.DisallowedHost", "ERROR"):
            pod_ip = self.client.get("/api/v1/csrf", HTTP_HOST=POD_IP_HOST)
        plain_http = self.client.get("/api/v1/csrf", HTTP_HOST="chamneul.com")

        self.assertEqual(pod_ip.status_code, 400)
        self.assertEqual(plain_http.status_code, 301)

    def test_both_probes_answer_a_pod_ip_over_plain_http(self):
        for path in (HEALTHZ, READYZ):
            for method in ("get", "head"):
                with self.subTest(path=path, method=method):
                    response = getattr(self.client, method)(path, HTTP_HOST=POD_IP_HOST)
                    self.assertEqual(response.status_code, 200)

    def test_anything_but_an_exact_probe_takes_the_normal_path(self):
        """경로가 정확히 같고 GET/HEAD일 때만 검사를 건너뛴다. 나머지는 평소처럼
        Host 검증에 걸린다(400)."""
        cases = [
            ("get", "/healthz/"),
            ("get", "/readyz/"),
            ("get", "/healthzx"),
            ("get", "/readyzx"),
            ("get", "/HEALTHZ"),
            ("get", "/api/v1/readyz"),
            ("post", HEALTHZ),
            ("post", READYZ),
            ("delete", READYZ),
        ]
        for method, path in cases:
            with self.subTest(method=method, path=path):
                with self.assertLogs("django.security.DisallowedHost", "ERROR"):
                    response = getattr(self.client, method)(path, HTTP_HOST=POD_IP_HOST)
                self.assertEqual(response.status_code, 400)
