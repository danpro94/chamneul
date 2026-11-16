# ADR-010. readiness 엔드포인트 `/readyz` — 두 번째 비-버전 엔드포인트 (47 → 48)

## Status

Accepted

## Date

2026-11-07 (Owner 승인: SPEC-006 결정 5 — 2026-11-04, ADR 작성·CLAUDE.md 개정 — 2026-11-07)

## Context

`/healthz`는 **일부러 DB를 보지 않는다**(`config/health.py` 주석, 리뷰 노트 01). "앱 프로세스가 살아 있는가"만 답한다. 그래서 DB가 죽어도 200이다.

Phase 3의 k8s는 질문을 두 가지로 나눠서 한다.

| probe | 질문 | 실패하면 |
| --- | --- | --- |
| liveness | 이 프로세스가 살아 있나? | 파드를 **재시작**한다 |
| readiness | 지금 요청을 받을 수 있나? | 파드를 **트래픽에서 뺀다**(재시작하지 않는다) |

지금은 readiness에 쓸 엔드포인트가 없다. 그러면 DB에 닿지 못하는 파드에도 트래픽이 가고, 사용자는 500을 받는다(smoke-test §5 갭 7).

이 공백을 메우는 것은 CLAUDE.md 두 조항과 충돌한다.

* **§5** — Phase 2 API 표면이 **47개**로 고정돼 있다(ADR-008).
* **§7** — "`/healthz` is the **only** unversioned endpoint."

ADR-007의 교훈("SPEC 결정이 CLAUDE.md 조항과 어긋나면 결정 시점에 ADR")에 따라 구현 전에 이 ADR을 둔다.

## Decision

### 1. `GET /readyz` 추가 (#48, 버전 없음, Anonymous)

| 상황 | 상태 | 본문 |
| --- | --- | --- |
| DB 질의(`SELECT 1`) 성공 | 200 | `{"status": "ok", "checks": {"database": "ok"}}` |
| DB 연결·질의 실패 | **503** | `{"status": "unavailable", "checks": {"database": "unavailable"}}` |

* 응답에 **예외 문자열·호스트명·포트를 싣지 않는다**(CLAUDE.md §8). 원인은 서버 로그에만 남긴다.
* `/healthz`는 **바꾸지 않는다** — 여전히 DB를 보지 않는다.

### 2. 두 헬스 경로는 Host 검증·HTTPS 리다이렉트보다 먼저 답한다

kubelet과 ALB는 `http://<파드 IP>:8000/healthz`처럼 **파드 IP를 Host로, 평문 HTTP로** 묻는다. Django 기본 흐름에서는 그 요청이 다음처럼 막힌다.

* prod의 `SECURE_SSL_REDIRECT`가 **301**을 준다(ALB 헬스체크는 기본적으로 200만 성공으로 본다).
* `ALLOWED_HOSTS`에 없는 파드 IP라서 **400**(DisallowedHost)이 된다.

그래서 `MIDDLEWARE` 맨 앞에 `config.health.HealthCheckMiddleware`를 둔다. 이 미들웨어는 경로가 **정확히** `/healthz` 또는 `/readyz`이고 메서드가 **GET/HEAD**인 요청에만 직접 답한다. 그 밖의 모든 요청(`/healthz/`, `/readyzx`, POST 등)은 평소 흐름을 탄다.

### 3. 이름은 `/healthz/db`가 아니라 `/readyz`

예전 문서(api.md #1, 리뷰 노트 01)는 `/healthz/db`를 후보로 적었다. k8s 생태계의 관례 이름 `/readyz`를 쓴다(kube-apiserver의 `/livez`·`/readyz`). 이름만 보고도 probe의 종류를 알 수 있고, `/healthz` 아래에 두면 "liveness의 일부"로 오해받는다.

## Rationale (Why)

### 왜 `/healthz`에 DB 검사를 합치지 않나 (SPEC-006 결정 5의 기각안 b)

liveness가 DB를 보면 **DB 장애 한 번에 모든 파드가 재시작**된다. 재시작해도 DB는 그대로 죽어 있으니 파드는 다시 실패하고, CrashLoopBackOff에 빠진다. DB가 돌아와도 백오프 때문에 회복이 늦어진다. readiness는 파드를 **살려 둔 채 트래픽만** 뺀다. DB가 돌아오면 다음 probe에서 바로 복귀한다.

### 왜 버전(`/api/v1/`)을 붙이지 않나

probe 경로는 **인프라 계약**이다(k8s 매니페스트·ALB 대상 그룹 설정이 가리킨다). API 버전이 v2로 바뀔 때 매니페스트까지 고치게 만들 이유가 없다. `/healthz`가 버전 없이 남은 것과 같은 이유다.

### 왜 설정이 아니라 미들웨어인가

| 안 | 301 해결 | 400 해결 | 채택하지 않은 이유 |
| --- | --- | --- | --- |
| `SECURE_REDIRECT_EXEMPT` | ✅ | ❌ | Host 검증은 남는다 |
| `ALLOWED_HOSTS`에 파드 대역 추가 | — | ❌ | Django는 CIDR을 지원하지 않고, 파드 IP는 바뀐다. `*`는 Host 검증을 통째로 끈다 |
| **미들웨어(경로 정확히 일치 + GET/HEAD)** | ✅ | ✅ | — **채택** |

## Trade-offs

* **두 경로는 Host 검증을 건너뛴다.** 위험은 작다. 둘 다 데이터가 없는 고정 본문이라 Host 값을 응답에 쓰지 않는다. 경로는 정확히 일치할 때만, 메서드는 GET/HEAD만 받는다(테스트로 고정).
* **보안 헤더가 붙지 않는다.** `SecurityMiddleware`보다 앞에서 답하므로 HSTS·nosniff가 없다. JSON 고정 본문이라 실익이 없다.
* **probe가 DB에 질의를 더한다.** 파드당 probe 주기마다 `SELECT 1` 한 번이다. 무시할 수준이다.
* **연결이 오래 매달리면 워커가 묶인다.** DB 호스트가 응답 없이 패킷만 버리면 연결 시도가 OS 기본 타임아웃까지 걸린다. gunicorn sync 워커가 그동안 묶인다. `connect_timeout`은 Phase 3 probe 설정(`timeoutSeconds`)과 함께 정한다(SPEC-006 plan §3, 기록만).
  * *후속 2026-11-16 (Owner 승인, SPEC-006 TASK-005 devops 리뷰 M-2)*: **3초로 앞당겼다.** 미루면 이 ADR의 목적 자체가 깨진다는 것이 드러났기 때문이다. `/healthz`도 같은 sync 워커가 답한다. 그래서 매달린 readiness가 워커 3개를 다 잡으면 liveness도 실패하고, DB 장애 한 번에 모든 파드가 재시작된다. 패킷을 버리는 주소로 실측하니 `/readyz` 503이 3.0초에 나왔다. 아직 남은 것도 있다. **이미 열린 연결 위의 질의가 매달리는 경우**는 `connect_timeout`이 막지 못한다. 이것은 Phase 3에서 probe `timeoutSeconds`와 함께 `tcp_user_timeout`을 검토한다.
* **DB 장애 때 모든 파드가 not-ready가 된다.** 의도한 동작이다. 사용자는 Django의 500 대신 로드밸런서의 503을 받는다. 다만 AWS ALB는 대상이 전부 unhealthy이면 **모든 대상에 요청을 보내는**(fail open) 동작이 있다. Phase 3에서 Service·Ingress 구성을 정할 때 확인한다.

## Consequences

CLAUDE.md 개정 5곳 — 본 ADR이 **Accepted**가 된 뒤에만, 아래 문구를 **그대로** 옮겨 적용한다(§16 헌법 잠금 절차).

**① §5 첫 문단** — `— see docs/api.md §3` 앞에 한 구절을 넣는다.

```text
바꾸기 전: ... and **extended again to 47 on 2026-09-22 (ADR-008)** — see docs/api.md §3 for the authoritative count.
바꾼 뒤:   ... **extended again to 47 on 2026-09-22 (ADR-008)**, and **to 48 on 2026-11-07 (ADR-010)** with the readiness probe `GET /readyz` — see docs/api.md §3 for the authoritative count.
```

**② §5 "In scope for Phase 2"의 첫 항목**

```text
바꾸기 전: * `/healthz`
바꾼 뒤:   * `/healthz` (liveness) and `/readyz` (readiness, ADR-010)
```

**③ §7 URI rules 첫 항목**

```text
바꾸기 전: * All versioned APIs use the `/api/v1/` prefix. `/healthz` is the only unversioned endpoint.
바꾼 뒤:   * All versioned APIs use the `/api/v1/` prefix. `/healthz` (liveness) and `/readyz` (readiness, ADR-010) are the only unversioned endpoints.
```

**④ §7 Good 예시** — `` * `/healthz` `` 바로 다음 줄에 추가한다.

```text
* `/readyz`
```

**⑤ §16 Constitutional lock** — ADR-008 항목 다음에 추가한다.

```text
* ADR-010 (readiness endpoint `/readyz`, Accepted 2026-11-07) explicitly supersedes §5's endpoint count (47 → 48) and §7's "`/healthz` is the only unversioned endpoint" sentence. Liveness and readiness stay separate on purpose: **a DB outage must take pods out of rotation, not restart every one of them.**
```

그 밖의 결과:
* `docs/api.md`: §1.1 비-버전 엔드포인트, §3 요약표(#48, 총계 48), #1 설명, #48 절 신설.
* `config/health.py`에 `readyz`와 `HealthCheckMiddleware`, `config/urls.py`에 `/readyz` 경로, `config/settings/base.py` `MIDDLEWARE` 맨 앞에 미들웨어를 추가한다. **모델·마이그레이션 변경은 없다.**
* 구현은 `specs/SPEC-006-pre-phase3-hardening/` TASK-002에서 TDD 루프로 진행한다.
* STATUS.md의 엔드포인트 총계가 47 → 48이 된다.

## Validation

* `grep -cE "^### [0-9]+\. (GET|POST|PATCH|PUT|DELETE) " docs/api.md`가 48을 반환한다. (ADR-008이 적은 `grep -c "^### [0-9]"`는 `### 1.1` 같은 소제목까지 세어 63이 나온다 — 2026-11-07 실측.)
* DB 정상 → `/readyz` 200 / DB 연결 실패(모의) → 503, 본문에 예외 문자열·호스트명 없음.
* DB 실패 중에도 `/healthz` 200.
* prod 보안 설정(`SECURE_SSL_REDIRECT`, 명시적 `ALLOWED_HOSTS`)에서 파드 IP Host + HTTP로 두 경로 200 — 같은 조건에서 일반 경로는 여전히 400·301.
* 비슷한 경로(`/healthz/`, `/readyzx`)와 GET/HEAD 외의 메서드는 미들웨어가 건드리지 않는다.
