# 리뷰 노트 09 — SPEC-006 Phase 3 진입 전 하드닝

> 2026-11-04 작성 (TASK-001). TASK마다 절을 덧붙인다. 판정 원칙은 리뷰 노트 07·08과 같다: **"이 명령의 이 출력이 근거다."**

## 1. TASK-001 — 요청 횟수 제한 (#2·#3·#45·#46)

### 1-1. 무엇이 바뀌었나

| 범위 | 내용 |
| --- | --- |
| 한도 | #3 로그인 IP 20회/분 + **계정 10회/시간**, #2 가입 IP 10회/시간, #45 재설정 요청 IP 10회/시간 + **이메일 3회/시간**, #46 확정 IP 20회/시간 (결정 2) |
| 응답 | 429 + `Retry-After` + `RATE_LIMITED` 봉투. 본문은 고정 문구 |
| 카운터 저장소 | Django 기본(프로세스별 LocMem) → **PostgreSQL 캐시 테이블** `django_cache` (결정 1) |
| 클라이언트 IP | `NUM_PROXIES`를 명시(`DRF_NUM_PROXIES`, 기본 0) — 미설정이면 위조한 `X-Forwarded-For`로 IP 한도를 우회할 수 있었다 |

**근거**: `manage.py test` **439개 OK**(새 15개) · `check` 0 issues · `makemigrations --check` No changes · `ruff check` passed · 변이 15건 전건 검출 · 실제 compose 앱에서 10×401 → 11번째 **429** `Retry-After: 3599`.

### 1-2. 왜 이렇게 구현했나

* **DRF 내장 throttling을 쓰되, 한도를 요청 때마다 읽는다.** DRF는 한도 표를 import 시점에 클래스 속성으로 복사해 둔다. 그래서 설정을 바꾸거나 테스트에서 덮어써도 반영되지 않는다. `_RateFromSettings.get_rate()`가 매번 다시 읽는다 — 이 한 줄을 지우면 테스트 8개가 실패한다(변이 M12).
* **계정 기준 한도가 진짜 방어선이다.** IP 한도는 IP를 바꾸면 새로 시작한다. 계정 한도는 "입력한 이메일 문자열"로 세므로 IP를 바꿔도 이어진다.
* **가입 여부를 보지 않고 센다.** 스로틀은 뷰보다 먼저 돌고 키는 입력 문자열에서 나온다. 그래서 #45의 429는 가입·미가입이 바이트 단위로 같다(ADR-008 §2).
* **키는 HMAC이다.** 캐시 테이블은 DB에 남는다. 그냥 sha256은 후보 주소를 해시해 보면 되돌릴 수 있다(이메일은 추측 가능한 값이다). SECRET_KEY를 섞으면 테이블만으로는 아무것도 알 수 없다. IP도 같은 방식으로 다룬다.

### 1-3. 핵심 파일

`common/throttling.py`(신규) · `accounts/views.py`(4개 뷰에 `throttle_classes`) · `common/exceptions.py`(429 고정 문구) · `config/settings/{base,test}.py` · 테스트 `accounts/tests.py` `RateLimitTests`(15개)

### 1-4. 테스트 방법

```bash
uv run python manage.py test accounts.tests.RateLimitTests --settings=config.settings.test   # 15 OK
# 실제 앱: 없는 계정으로 11번 → 10번째까지 401, 11번째 429
docker compose exec app python manage.py createcachetable      # 처음 한 번 (smoke-test §2-1)
curl -s -c /tmp/j http://localhost:8000/api/v1/csrf >/dev/null
T=$(awk '$6=="csrftoken"{print $7}' /tmp/j)
for i in $(seq 11); do curl -s -o /dev/null -w "%{http_code}\n" -b /tmp/j -H "X-CSRFToken: $T" \
  -H "Content-Type: application/json" -d '{"email":"x@example.com","password":"wrong-pass-1"}' \
  http://localhost:8000/api/v1/auth/login; done
```

변이 검증 15건: IP 한도·계정 한도·재설정 이메일 한도·가입·확정 IP 한도 제거 / 해시 제거 / HMAC → sha256 / 정규화 제거 / `NUM_PROXIES` 제거 / 캐시 → LocMem / `MAX_ENTRIES` 제거 / 호출 시점 한도 읽기 제거 / 429 고정 문구 제거 / 본문을 지역변수에 보관 / 본문 형태 검사 제거 — **전부 테스트가 잡았다.**

### 1-5. DevOps 설명 포인트

* **캐시 테이블은 마이그레이션 밖이다.** `createcachetable`이 만든다. 빠뜨리면 다른 API는 멀쩡하고 인증 4개만 500이라 놓치기 쉽다. 로그에는 `relation "django_cache" does not exist`가 찍힌다. Phase 3 k8s 마이그레이션 Job에는 `migrate` 다음 줄로 넣는다(Owner 손코딩). 두 번 실행해도 안전하다.
* **"프로세스 메모리 캐시"는 수평 확장과 함께 쓸 수 없다.** gunicorn 워커 3개 × 파드 N개면 각자 따로 세서 한도가 3N배가 된다. 공유 저장소가 DB인 이유가 이것이다. 요청량이 늘면 Redis(ElastiCache)로 옮기는데, 바뀌는 것은 `CACHES` 블록 하나뿐이다.
* **비용 실측**: 스로틀 1개 = SQL 6문. #3·#45는 요청마다 **+12문**이었다(1문 → 13문, 테스트 DB에서 `CaptureQueriesContext`로 측정). 대상이 인증 엔드포인트 4개뿐이라 감수한다. Redis 전환을 판단할 기준이 이 숫자다.
* **`NUM_PROXIES`는 배포 구성과 짝이다.** 로컬은 0이다. ALB 하나 뒤에서는 `DRF_NUM_PROXIES=1`(ALB가 XFF 맨 끝에 붙인 값이 진짜 클라이언트 IP), CloudFront + ALB면 2다. 값이 실제 프록시 수보다 크면 위조 값을 믿게 되고, 작으면 모든 사용자가 프록시 IP 하나로 묶인다. `.env.example`에는 Owner가 손으로 추가한다(기본값 0이라 로컬은 지금 그대로 동작).
* **로컬에서는 호스트의 모든 요청이 같은 IP다**(Docker 게이트웨이). 그래서 브라우저·curl·스모크 스크립트가 IP 한도를 함께 쓴다. 막혔을 때 비우는 명령은 smoke-test §6에 있다.

### 1-6. 보안 노트

* **명세 단계에서 찾은 위험 2건**(XFF 우회, 프로세스별 카운터)을 닫았다.
* **구현 중 찾은 위험 2건**도 다뤘다. 첫 번째는 11-04에 "닫았다"고 적었지만 **반만 닫힌 상태였다**(1-8에서 마저 닫음).
  * **DatabaseCache 컬링 우회**: 기본 `MAX_ENTRIES=300`을 넘으면 Django가 **키 순서로 행 1/3을 지운다.** 키는 누구나 늘릴 수 있다(시도한 주소마다 1개). 기본값 그대로면 공격자가 무작위 주소를 섞어 보내 피해자의 카운터를 지울 수 있다 → 100,000으로 올렸다. 350개를 넣어 하나도 지워지지 않는지 테스트로 고정했다. **다만 IP 한도에 막힌 요청도 행을 만들고 있어서**, 한 IP가 10만 행을 채우는 데 걸림돌이 없었다 → 1-8.
  * **오류 리포트의 비밀번호**: 스로틀은 뷰의 `sensitive_variables()` **밖**에서 본문을 읽는다. 그 프레임에서 예외가 나면 운영 오류 리포트에 지역변수가 찍힌다. 본문을 지역변수에 담기만 해도 비밀번호가 찍힌다는 것을 변이 M14가 실제로 보여 줬다. 그래서 지역변수에 담지 않는다.
* **감수하는 것**: 계정 기준 한도는 남이 일부러 다 써 버릴 수 있다. 그러면 그 계정은 1시간 동안 로그인 429를 받는다(잠금형 서비스 거부). 계정 잠금보다는 약한 피해다(spec §5가 잠금을 기각한 이유). 실패만 세기·CAPTCHA는 Phase 3.
* **기존 테스트 1개의 단언 범위를 좁혔다**: `test_changes_nothing_in_the_database`(#45는 DB를 쓰지 않는다)가 결정 1의 카운터 쓰기와 부딪혔다. 목적(토큰·세션·사용자 행을 쓰지 않는다)은 유지하고 `django_cache` 쓰기만 예외로 했다. → Owner 조건부 승인(2026-11-07, "운영에 치명적 영향이 없으면"). 예외를 **#45 카운터 2개로 다시 좁혀** 사각지대를 없앴다(1-8).

### 1-7. 다음 개선

* 요청량이 늘면 Redis로 전환(`CACHES` 블록만).
* 로그인 계정 한도를 "실패만 세기"로 — 정상 로그인이 한도를 쓰지 않게 한다(Phase 3, 뷰 후처리 필요).
* Phase 3 배포 체크리스트: `DRF_NUM_PROXIES`를 실제 프록시 수에 맞춘다 + `createcachetable`을 마이그레이션 Job에 넣는다.
* **만료된 카운터 행 정리**: DatabaseCache는 만료 행을 그 키를 다시 읽거나 컬링할 때만 지운다. 한 번 쓰이고 다시 오지 않은 IP·주소의 HMAC 행은 1시간 뒤 효력이 없어도 표에 남는다. Phase 3 CronJob으로 `DELETE FROM django_cache WHERE expires < now()`를 하루 1회 돌린다 — 개인정보 처리방침(C-1)의 보존 기간 문구가 이것을 전제로 한다.

### 1-8. 후속 (2026-11-07) — 첫 거절에서 멈춘다 + 테스트 예외를 카운터 2개로

**계기**: Owner가 좁힌 테스트를 "운영에 치명적 영향이 없으면 승인"했다. 그 조건을 확인하려고 카운터가 어떻게 쌓이는지 다시 읽다가 1-6의 컬링 대응에 구멍을 찾았다.

| 발견 | 근거 |
| --- | --- |
| DRF는 스로틀 하나가 거절해도 **나머지를 모두 평가**하고, 통과한 스로틀은 기록한다 | DRF 3.18.2 `APIView.check_throttles` — 전부 돈 뒤 가장 긴 대기 시간으로 거절 |
| 그래서 **IP 한도에 막힌 요청도 주소마다 새 행**을 만든다 | 새 테스트의 선-실패: 한 IP에서 주소 5개 → 3번째부터 429인데 주소 행은 **5개**(기대 2) |
| 한 IP가 주소만 바꿔 10만 행을 채우면 컬링이 **키 순서로 1/3**을 지운다. 맨 앞이 `throttle_auth_login_email_*`(계정 한도) | Django `DatabaseCache._cull` — `ORDER BY cache_key` |

**수정**: `common/throttling.StopAtFirstLimit` — 첫 거절에서 평가를 멈추는 뷰 믹스인. 인증 뷰 4개에 붙였다. IP 스로틀을 먼저 둔다(순서가 바뀌면 다시 행이 생긴다 — 변이 M4가 잡는다).

* **효과**: 한 IP가 만들 수 있는 행 = 그 IP 한도(#45 시간당 10, #3 분당 20). 10만 행을 채우려면 IP가 수천 개 필요해진다. 거절된 요청의 비용도 줄어든다 — 코드상 IP 카운터 읽기 1번으로 끝나고 주소 카운터의 `COUNT(*)`·`INSERT`가 없다(실측은 안 함).
* **바뀐 것 하나**: 두 한도를 동시에 넘으면 `Retry-After`는 먼저 거절한 한도(IP)의 대기 시간이다. 그 뒤 다시 와서 다른 한도에 걸리면 그 대기 시간을 다시 받는다. 429 본문·상태 코드는 그대로다.
* **남는 위험**: IP가 많은 공격자(봇넷, IPv6 대역)는 여전히 행을 늘릴 수 있다. 그 규모면 Redis(eviction 정책 선택 가능) 또는 WAF가 답이다(Phase 3).

**테스트 예외 재조정**: `test_changes_nothing_in_the_database`가 이제 캐시 테이블에 생긴 키가 **정확히 `throttle_password_reset_email`·`throttle_password_reset_ip` 두 개**인지 본다. #45가 그 밖의 무엇이든 캐시에 쓰면 실패한다(변이 M5).

**Owner 조건에 대한 답 — "운영에 치명적 영향이 없는가"**: 없다.
* 테스트는 운영에서 돌지 않는다. 테스트를 좁히면 **무엇을 못 잡게 되느냐**가 문제인데, 재조정 뒤에는 사각지대가 없다(카운터 2개 외의 쓰기는 전부 잡는다).
* 테스트가 허용하는 운영 동작(카운터 쓰기)의 비용은 1-5의 실측 그대로다(요청당 +12문, 인증 4개만). 최대 행 수는 `MAX_ENTRIES` 근처에서 멈춘다.

**근거**: 테스트 **440개 OK**(새 1개) · `check` 0 issues · `makemigrations --check` No changes · `ruff check` passed · 변이 5건 전건 검출(M1 Login 믹스인 제거 · M2 #45 믹스인 제거 · M3 멈추지 않음 · M4 스로틀 순서 뒤바꿈 · M5 #45가 캐시에 다른 것을 씀).

> 변이 측정 주의: M4는 같은 길이의 이름 두 개를 맞바꾸는 변이라, 처음에는 오래된 바이트코드가 쓰여 **"놓침"으로 잘못 나왔다.** 손으로 적용하면 `5 != 2`로 실패했다. 변이마다 `__pycache__`를 지우도록 스크립트를 고친 뒤 다시 돌려 5/5를 얻었다. 변이 검증 결과 "놓침"은 테스트를 의심하기 전에 측정을 먼저 의심한다.

## 2. TASK-002 — readiness 분리 (`/readyz`) + 헬스 미들웨어 (2026-11-07)

### 2-1. 무엇이 바뀌었나

| 범위 | 내용 |
| --- | --- |
| 헌법 | **ADR-010 Accepted** → CLAUDE.md §5(47 → 48)·§7(비-버전 엔드포인트 둘)·§16 개정. ADR의 Consequences 문구를 그대로 옮겼다(diff 5곳) |
| `/readyz` (#48) | DB에 `SELECT 1` → 200 `{"status":"ok","checks":{"database":"ok"}}` / 실패 503 `{"status":"unavailable",...}`. 원인은 서버 로그 WARNING에만 |
| `/healthz` (#1) | **변경 없음** — 여전히 DB를 보지 않는다 |
| `HealthCheckMiddleware` | `MIDDLEWARE` 맨 앞. 경로가 **정확히** `/healthz`·`/readyz`이고 GET/HEAD인 요청만 HTTPS 리다이렉트·Host 검증보다 먼저 답한다 |

**근거**: 테스트 **446개 OK**(새 6개, 선-실패 3개 + 회귀 방지 3개) · `check` 0 issues · `makemigrations --check` No changes · `ruff check` passed · 변이 10건 전건 검출 · 실제 compose 앱에서 DB 정지 중 `/readyz` 503·`/healthz` 200, DB 재기동 직후 `/readyz` 200.

### 2-2. 왜 이렇게 구현했나

* **질의까지 한다.** 처음 테스트는 "연결 실패"만 흉내 냈다. 그래서 `SELECT 1`을 지운 변이(M9)를 놓쳤다. 운영에서 이 차이는 진짜다 — 워커는 연결을 `CONN_MAX_AGE`(60초) 동안 들고 있고, DB가 재시작되면 그 연결 객체는 남은 채 끊겨 있다. "질의 단계 실패" 케이스를 추가한 뒤 10/10.
* **`db.Error` 전체를 잡는다.** 연결 거부는 `OperationalError`, 끊긴 연결은 `InterfaceError`로 계열이 다르다(M5가 잡는다).
* **설정이 아니라 미들웨어.** `SECURE_REDIRECT_EXEMPT`는 301만 풀고 400(Host 검증)은 남는다. `ALLOWED_HOSTS`는 CIDR을 지원하지 않고, `*`는 Host 검증을 통째로 끈다(ADR-010).
* **전제부터 고정한다.** "prod 보안 설정에서 일반 경로는 정말 400·301이다"를 먼저 단언한다. 그래야 "probe는 200"이 의미를 갖는다.

### 2-3. 핵심 파일

`config/health.py`(readyz·미들웨어) · `config/urls.py` · `config/settings/base.py`(`MIDDLEWARE` 맨 앞) · `config/tests.py`(신규, 6개) · `docs/adr/ADR-010-readiness-endpoint.md`(신규) · `CLAUDE.md`

### 2-4. 테스트 방법

```bash
uv run python manage.py test config --settings=config.settings.test     # 6 OK
curl -s -w "  [%{http_code}]\n" http://localhost:8000/readyz                          # 200
curl -s -w "  [%{http_code}]\n" -H "Host: 10.0.3.17:8000" http://localhost:8000/readyz  # 파드 IP Host도 200
docker compose stop db   # → /readyz 503, /healthz 200
docker compose start db  # → /readyz 200
```

변이 10건: 미들웨어 제거 / SecurityMiddleware 뒤로 / 경로 앞부분 비교 / 모든 메서드 허용 / `OperationalError`만 잡음 / 예외 문자열을 본문에 / 실패를 500으로 / healthz가 DB를 봄 / readyz가 질의를 안 함 / 원인 로그 없음 — **전부 테스트가 잡았다**(M9는 테스트 보강 후).

### 2-5. DevOps 설명 포인트

* **liveness와 readiness는 질문이 다르다.** liveness 실패 → 재시작. readiness 실패 → 트래픽에서만 뺀다. DB 장애는 재시작으로 고쳐지지 않으므로 readiness의 일이다. liveness가 DB를 보면 DB 장애 한 번에 모든 파드가 CrashLoopBackOff에 빠진다.
* **probe는 파드 IP로, 평문 HTTP로 온다.** 그래서 prod의 HTTPS 리다이렉트(301)와 Host 검증(400)보다 앞에서 답해야 한다. ALB 헬스체크는 기본적으로 200만 성공으로 본다.
* **실측**: DB 컨테이너를 멈추면 이름 `db`가 사라져 `failed to resolve host 'db'`로 **0.05초 만에** 실패했다. 패킷만 버리는 장애(보안그룹 차단 등)라면 연결 시도가 OS 타임아웃까지 매달린다. 그동안 gunicorn sync 워커가 묶인다. `connect_timeout`은 Phase 3 probe의 `timeoutSeconds`와 함께 정한다.
* **compose healthcheck는 그대로 `/healthz`다.** compose는 의존 서비스 기동 순서에만 쓰므로 liveness가 맞다. k8s 매니페스트(Phase 3, Owner 손코딩)에서 `livenessProbe: /healthz`, `readinessProbe: /readyz`로 나눈다.

### 2-6. 보안 노트

* **두 경로는 Host 검증을 건너뛴다.** 본문이 고정값이고 Host를 쓰지 않는다. 정확한 경로·GET/HEAD만 받는다. `/healthz/`, `/readyzx`, `/HEALTHZ`, `/api/v1/readyz`, POST·DELETE는 평소대로 400인지 테스트로 고정했다.
* **응답에 예외를 싣지 않는다.** psycopg 오류에는 DB 호스트명·내부 주소·포트가 들어 있다(테스트용 오류 문자열도 실제 모양으로 만들었다). 본문은 고정이고, 원인은 서버 로그에만 남긴다.
* **보안 헤더가 없다.** `SecurityMiddleware`보다 앞이라 HSTS·nosniff가 붙지 않는다. 고정 JSON이라 실익이 없다(ADR-010 Trade-offs).

### 2-7. 다음 개선

* Phase 3: probe `timeoutSeconds`와 DB `connect_timeout`을 함께 정한다.
* Phase 3: AWS ALB는 대상이 **전부** unhealthy이면 모든 대상에 요청을 보낸다(fail open). Ingress·대상 그룹 구성을 정할 때 확인한다.
* TASK-003: 실제 이미지(gunicorn + prod 설정)로 두 경로를 파드 IP Host·HTTP로 다시 확인한다.
