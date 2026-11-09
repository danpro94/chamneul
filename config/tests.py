"""SPEC-006 TASK-002 — liveness와 readiness (ADR-010), TASK-003 — 운영 경로."""

import os
import subprocess
import sys
from unittest.mock import patch

from django.conf import settings
from django.db import InterfaceError, OperationalError, connections
from django.test import SimpleTestCase, TestCase, override_settings

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


# prod.py가 import되는 데 필요한 값 전부. 테스트용이라 실제 시크릿이 아니다.
PROD_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.prod",
    "DJANGO_SECRET_KEY": "test-only-" + "x" * 50,
    "DJANGO_ALLOWED_HOSTS": "chamneul.com",
    "PASSWORD_RESET_URL": "https://chamneul.com/reset-password",
    "DJANGO_EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
}


def run_python(*args, **env):
    """새 인터프리터에서 실행한다 — 설정은 프로세스당 한 번만 읽히므로, 경우마다
    따로 띄워야 한다. 지금 테스트가 쓰는 DJANGO_SETTINGS_MODULE은 물려주지 않는다.
    .env는 load_dotenv가 읽지만, 여기서 준 값을 덮어쓰지는 않는다."""
    environ = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
    environ.update(env)
    return subprocess.run(
        [sys.executable, *args],
        cwd=settings.BASE_DIR,
        env=environ,
        capture_output=True,
        text=True,
        timeout=60,
    )


class ProdStartupGuardTests(SimpleTestCase):
    """AC-3 — 운영에서 재설정 링크가 새거나 깨지는 설정이면 기동하지 않는다."""

    BOOT = ("-c", "import django; django.setup()")

    def test_premise_prod_boots_with_complete_settings(self):
        """전제: 값이 다 있으면 뜬다. 아니면 아래 실패는 다른 이유일 수 있다."""
        result = run_python(*self.BOOT, **PROD_ENV)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_refuses_a_mail_backend_that_keeps_the_mail_on_the_server(self):
        """콘솔은 로그에, 파일은 디스크에 재설정 링크를 남긴다 — 로그나 파일을
        읽을 수 있는 사람이 남의 비밀번호를 바꿀 수 있다(보안 리뷰 S-3)."""
        for backend in ("console", "filebased"):
            with self.subTest(backend):
                result = run_python(
                    *self.BOOT,
                    **{
                        **PROD_ENV,
                        "DJANGO_EMAIL_BACKEND": f"django.core.mail.backends.{backend}.EmailBackend",
                    },
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ImproperlyConfigured", result.stderr)
                self.assertIn("DJANGO_EMAIL_BACKEND", result.stderr)

    def test_refuses_a_reset_url_that_is_not_https(self):
        """빠뜨리면 base.py의 개발용 기본값이 들어온다 — 그대로 돌면 링크가 사용자
        PC를 가리킨다(S-6). http 페이지는 오가는 중에 고쳐져 토큰을 읽힐 수 있다.
        (빠뜨림 자체는 재현하지 않는다: .env가 그 자리를 채울 수 있다.)"""
        missing = "http://localhost:3000/reset-password"  # base.py의 기본값
        for url in (missing, "", "http://chamneul.com/reset-password"):
            with self.subTest(url=url):
                result = run_python(*self.BOOT, **{**PROD_ENV, "PASSWORD_RESET_URL": url})

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ImproperlyConfigured", result.stderr)
                self.assertIn("PASSWORD_RESET_URL", result.stderr)


class EntryPointDefaultTests(SimpleTestCase):
    """AC-3 — 결정 4: 서버 진입점은 지정이 없으면 prod, manage.py는 local.
    지정을 빠뜨린 배포가 조용히 개발 설정(DEBUG=True·콘솔 메일)으로 돌지 않고,
    prod의 필수값 검사에 걸려 기동에 실패하게 한다."""

    PRINT_MODULE = "from django.conf import settings; print(settings.SETTINGS_MODULE)"

    def test_server_entry_points_default_to_prod(self):
        env = {k: v for k, v in PROD_ENV.items() if k != "DJANGO_SETTINGS_MODULE"}
        for entry in ("config.wsgi", "config.asgi"):
            with self.subTest(entry):
                result = run_python("-c", f"import {entry}; {self.PRINT_MODULE}", **env)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "config.settings.prod")

    def test_manage_py_stays_local_for_development(self):
        result = run_python("manage.py", "shell", "--no-imports", "-c", self.PRINT_MODULE)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "config.settings.local")


@prod_security
@override_settings(WHITENOISE_USE_FINDERS=True)
class StaticFilesTests(SimpleTestCase):
    """AC-3 — DEBUG=False에서는 Django가 정적파일을 내주지 않는다. WhiteNoise가
    맡는다. 테스트는 collectstatic을 돌리지 않으므로 앱의 static 폴더에서 바로
    찾게 한다(collectstatic이 복사하는 바로 그 파일들)."""

    ADMIN_CSS = "/static/admin/css/base.css"

    def test_admin_css_is_served_over_https(self):
        response = self.client.get(
            self.ADMIN_CSS, HTTP_HOST="chamneul.com", HTTP_X_FORWARDED_PROTO="https"
        )
        body = b"".join(response.streaming_content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/css"))
        self.assertGreater(len(body), 0)

    def test_plain_http_is_redirected_first(self):
        """WhiteNoise는 SecurityMiddleware 다음이다 — 앞에 두면 HTTPS 리다이렉트와
        HSTS 헤더 없이 파일이 나간다(WhiteNoise 문서의 배치)."""
        response = self.client.get(self.ADMIN_CSS, HTTP_HOST="chamneul.com")

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], f"https://chamneul.com{self.ADMIN_CSS}")


# /healthz를 일부러 깨뜨려 500을 만든다. 미들웨어에서 답하는 경로라 DB·Host 검증·
# HTTPS 리다이렉트를 거치지 않는다 — 실패 원인이 로깅 설정 하나로 좁혀진다.
# 이어서 없는 경로로 404를 하나 만든다(그 환경이 허용하는 Host, https로).
REQUESTS_500_THEN_404 = """
import django
django.setup()
from unittest import mock
from django.conf import settings
from django.test import Client
from config import health

def broken(request):
    raise RuntimeError("marker-for-logging-test")

client = Client(raise_request_exception=False)
with mock.patch.dict(health._PROBES, {"/healthz": broken}):
    print(client.get("/healthz").status_code)
print(client.get(
    "/no-such-page", HTTP_HOST=settings.ALLOWED_HOSTS[0], HTTP_X_FORWARDED_PROTO="https"
).status_code)
"""


class ErrorLoggingTests(SimpleTestCase):
    """SPEC-006 TASK-003 후속 — 500의 원인이 컨테이너 로그(stderr)에 남는다.
    Django 기본 로깅은 DEBUG=False에서 요청 오류를 관리자 메일로만 보낸다.
    ADMINS가 비어 있으면 원인이 아무 데도 남지 않는다(smoke-test §5 갭 12)."""

    def test_a_500_leaves_its_traceback_once_and_a_4xx_adds_nothing(self):
        """4xx는 액세스 로그(gunicorn·runserver)에 상태 코드와 함께 이미 남는다.
        Django가 4xx마다 한 줄씩 더 쓰면 양만 늘고, 운영에서는 누구나 그 양을
        늘릴 수 있다."""
        environments = [
            ("prod", PROD_ENV),
            ("local", {"DJANGO_SETTINGS_MODULE": "config.settings.local"}),
        ]
        for name, env in environments:
            with self.subTest(name):
                result = run_python("-c", REQUESTS_500_THEN_404, **env)

                self.assertEqual(result.stdout.split(), ["500", "404"], result.stderr)
                self.assertIn("Internal Server Error: /healthz", result.stderr)
                self.assertIn("RuntimeError: marker-for-logging-test", result.stderr)
                # 두 번이면 핸들러가 겹친 것이다(django 로거 + 루트 로거).
                self.assertEqual(result.stderr.count("Traceback"), 1)
                self.assertNotIn("Not Found: /no-such-page", result.stderr)
