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

* **효과**: 한 IP가 만들 수 있는 행 = 그 IP 한도(#45 시간당 10, #3 분당 20). ~~10만 행을 채우려면 IP가 수천 개 필요해진다.~~ **정정(2026-11-09, TASK-005 보안 리뷰 M-2)**: #3은 분당 20이라 IP 하나가 **시간당 1,200행**을 만든다. 주소 행은 1시간 동안 남으므로 10만 행에는 **IP 약 84개**면 된다(100,000 ÷ 1,200). 그 뒤 컬링이 키 순서로 1/3을 지우고, 맨 앞이 `throttle_auth_login_email_*`라 계정 한도가 되풀이해 초기화된다. "수천 개"는 시간당 한도(#45)만 보고 분당 한도(#3)를 시간으로 환산하지 않은 계산 실수였다. 대응은 §5(TASK-005) 결정 사항. 거절된 요청의 비용도 줄어든다 — 코드상 IP 카운터 읽기 1번으로 끝나고 주소 카운터의 `COUNT(*)`·`INSERT`가 없다(실측은 안 함).
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

* ~~Phase 3: probe `timeoutSeconds`와 DB `connect_timeout`을 함께 정한다.~~ → `connect_timeout` 3초는 2026-11-16 앞당김(§5-6). probe `timeoutSeconds`는 Phase 3.
* Phase 3: AWS ALB는 대상이 **전부** unhealthy이면 모든 대상에 요청을 보낸다(fail open). Ingress·대상 그룹 구성을 정할 때 확인한다.
* ~~TASK-003: 실제 이미지(gunicorn + prod 설정)로 두 경로를 파드 IP Host·HTTP로 다시 확인한다.~~ → **완료**(3-4 #1·#2).

## 3. TASK-003 — 운영 경로: prod 가드 · 진입점 · 정적파일 · 실제 이미지 기동 (2026-11-07)

### 3-1. 무엇이 바뀌었나

| 범위 | 내용 |
| --- | --- |
| prod 기동 가드 | `DJANGO_EMAIL_BACKEND`(신규 환경변수, 기본 SMTP)가 console·filebased면 `ImproperlyConfigured`(S-3). `PASSWORD_RESET_URL`이 `https://`로 시작하지 않으면 `ImproperlyConfigured`(S-6) — 빠뜨리면 base.py의 `http://localhost` 기본값이 들어오므로 같은 검사에 걸린다 |
| 진입점 (결정 4) | `config/wsgi.py`·`config/asgi.py` 기본값 **prod**. `manage.py`는 local 유지. compose는 `DJANGO_SETTINGS_MODULE: config.settings.local`을 명시하므로 로컬 동작은 그대로 |
| 정적파일 (결정 3) | `whitenoise` 6.12.0 추가(§16 승인 2026-11-04). 미들웨어는 `SecurityMiddleware` 바로 다음, 저장소는 `CompressedManifestStaticFilesStorage` — **둘 다 base.py**(아래 3-2) |
| 테스트 설정 | 정적파일 저장소를 Django 기본으로, `STATIC_ROOT = None` — 테스트는 `collectstatic`을 돌리지 않는다 |

**근거**: 테스트 **453개 OK**(새 7개) · `check` 0 issues · `makemigrations --check` No changes · `ruff check` passed · 변이 10건 전건 검출 · 실제 이미지 기동 12항목(3-4).

### 3-2. 왜 이렇게 구현했나

* **저장소를 prod.py가 아니라 base.py에 둔다 — 계획(plan.md §4)과 다르다.** Dockerfile은 빌드 때 `python manage.py collectstatic`을 돌리고, 그때 설정은 `manage.py`의 기본값인 **local**이다. 계획대로 prod에만 두면 이미지에 매니페스트(`staticfiles.json`)가 없다. **실제로 그렇게 빌드해 봤다**(반대 사례 이미지): 빌드 로그에 `post-processed`가 사라지고, prod로 띄우면 `/admin/login/`·DRF 화면이 **500**, `/healthz`·`/readyz`·JSON API는 **200**. 즉 헬스체크는 "정상"이라고 답하는데 Admin은 깨진 채로 배포된다.
* **미들웨어도 base.py.** 로컬·운영이 같은 미들웨어 목록을 쓴다. `runserver`는 `/static/`을 미들웨어보다 먼저 가로채므로 로컬 개발에는 영향이 없다.
* **`DJANGO_EMAIL_BACKEND`를 새로 읽는다.** 지금까지 prod의 메일 백엔드는 코드에 고정(Django 기본 SMTP)이라 "콘솔 메일 금지" 가드가 걸릴 입력 자체가 없었다(계획의 `docker run -e EMAIL_BACKEND=...`도 읽히지 않았을 것이다). 기본값이 SMTP라 **설정하지 않아도 된다.** filebased도 막는다 — 재설정 링크가 디스크에 남는 것은 로그에 남는 것과 같은 문제다.
* **설정 테스트는 새 인터프리터로.** Django 설정은 프로세스당 한 번 읽힌다. 가드·진입점 테스트는 `subprocess`로 매번 새로 띄운다. 호스트의 `.env`가 빈 자리를 채울 수 있으므로 "값 없음"은 재현하지 않고 **그 값이 빠졌을 때 실제로 들어오는 값**(base.py의 http 기본값)으로 시험한다.

### 3-3. 핵심 파일

`config/settings/prod.py`(가드 2개) · `config/settings/base.py`(WhiteNoise 미들웨어·`STORAGES`) · `config/settings/test.py` · `config/wsgi.py`·`config/asgi.py` · `config/tests.py`(+7) · `pyproject.toml`·`uv.lock`

### 3-4. 테스트 방법 — 실제 이미지 (Dockerfile·compose 무수정)

```bash
docker build -t chamneul:prodcheck .          # collectstatic: 154 copied, 444 post-processed
docker run --rm chamneul:prodcheck python -c "import config.wsgi"   # → KeyError: 'DJANGO_SECRET_KEY'
SK=$(openssl rand -base64 48 | tr -d '\n')     # 일회용 — 화면에 찍지 않는다
docker run -d --name chamneul-prodcheck --network chamneul_default --env-file .env \
  -e DJANGO_SETTINGS_MODULE=config.settings.prod -e DB_HOST=db -e DB_PORT=5432 \
  -e DJANGO_SECRET_KEY="$SK" -e DJANGO_ALLOWED_HOSTS=localhost \
  -e PASSWORD_RESET_URL=https://chamneul.com/reset-password -p 18000:8000 chamneul:prodcheck
unset SK
docker rm -f chamneul-prodcheck               # 끝나면 지운다
```

> 2026-11-09부터 prod는 `DRF_NUM_PROXIES`도 필수다(§5-1). 위 `docker run`에 `-e DRF_NUM_PROXIES=0`을 더한다 — 로컬에서는 앞에 프록시가 없다.

실제 결과(2026-11-07):

| # | 요청 | 결과 |
| --- | --- | --- |
| 0 | 환경변수 없이 이미지 기본 `CMD`(gunicorn) | 워커 3개 전부 `KeyError: 'DJANGO_SECRET_KEY'` → 컨테이너 종료(exit 1). **결정 4의 fail closed** |
| 1 | `/healthz` — Host `10.0.3.17:8000`, http | **200** |
| 2 | `/readyz` — 같은 조건 | **200** `{"status": "ok", "checks": {"database": "ok"}}` |
| 3 | Admin 로그인 페이지가 가리키는 CSS(`base.96c479cedf7a.css`), XFP https | **200**, `text/css`, `Content-Encoding: gzip`, `Cache-Control: max-age=315360000, public, immutable` |
| 4 | `/api/v1/csrf` — XFP https | **200** |
| 5 | `/api/v1/csrf` — 평문 http | **301** → `https://localhost/api/v1/csrf` |
| 6 | `/api/v1/csrf` — 파드 IP Host, XFP https | **400** (헬스 경로 밖은 Host 검증이 그대로) |
| 7 | HSTS | `max-age=31536000; includeSubDomains; preload` |
| 8 | `/admin/login/` | **200** |
| 9 | DRF 브라우저 화면 + 그 JS(`jquery-3.7.1.min.2c872dbe60f4.js`) | **200** / **200** |
| 10 | `manage.py check --deploy` | `System check identified no issues (0 silenced).` |
| 11 | gunicorn 기동 로그 | `Starting gunicorn 26.0.0`, 워커 3개 `Booting`, 액세스 로그 14줄 — 그리고 `[ERROR] Control server error: [Errno 13] Permission denied: '/home/appuser'`(3-7) |

변이 10건: console 허용 / filebased 허용 / 메일 백엔드를 환경변수에서 안 읽음 / 재설정 URL 검사 제거 / `https` 대신 `http`로 시작만 검사 / wsgi 기본값 local / asgi 기본값 local / manage.py 기본값 prod / WhiteNoise 제거 / WhiteNoise를 SecurityMiddleware 앞으로 — **전부 테스트가 잡았다.** 저장소 배치(3-2)는 단위 테스트가 볼 수 없는 빌드 단계 문제라 반대 사례 이미지로 확인했다.

### 3-5. DevOps 설명 포인트

* **fail closed.** 설정을 빠뜨린 배포는 "조용히 개발 설정으로 돈다"가 아니라 "워커가 뜨지 않는다"로 끝난다. k8s에서는 readiness가 실패해 트래픽을 받지 않고, 롤링 업데이트가 멈춘다 — 사고가 아니라 **배포 실패**로 드러난다.
* **헬스체크가 모든 것을 보지는 않는다.** 반대 사례 이미지는 `/healthz`·`/readyz`·JSON API가 200인 채로 Admin만 500이었다. 정적파일·템플릿처럼 빌드 산출물에 달린 것은 배포 후 스모크(Admin 한 번 열기)로 본다.
* **빌드 산출물은 빌드 때의 설정으로 만들어진다.** 실행 때 prod를 지정해도 빌드는 local로 돌았다. "이 파일은 어느 설정으로 만들어졌나"를 묻는 습관이 이 버그를 잡았다.
* **로컬 compose 앱을 다시 만들 때는 `-V`.** 의존성을 추가하면 `docker compose up -d --build --no-deps -V app`. `-V`가 없으면 예전 컨테이너의 익명 볼륨(`/app/.venv`)이 그대로 붙어 새 패키지가 가려진다. 이번에 실제로 `ModuleNotFoundError: No module named 'whitenoise'`로 앱이 멈췄다가 이 명령으로 복구했다.

### 3-6. 보안 노트

* **정적파일은 Host 검증을 거치지 않는다.** WhiteNoise는 `CommonMiddleware`보다 앞에서 파일을 내준다. 공개 파일(Admin·DRF CSS/JS)뿐이고 HTTPS 리다이렉트·HSTS는 그대로 받는다(WhiteNoise가 `SecurityMiddleware` 다음이므로 — 변이 M10이 고정).
* **일회용 시크릿.** 기동 확인에 실제 `DJANGO_SECRET_KEY`를 쓰지 않았고 값을 출력하지 않았다. `.env`는 `--env-file`로 넘기기만 하고 읽지 않았다. 확인용 컨테이너 2개와 이미지 2개(`prodcheck`·반대 사례 `prodcheck-cf`)는 확인 뒤 지웠다.

### 3-7. 다음 개선 — 이번에 새로 발견한 것 (결정 필요)

* **운영에서 500의 원인이 로그에 남지 않는다.** 프로젝트에 `LOGGING` 설정이 없어 Django 기본값을 쓴다. 기본값은 `DEBUG=False`에서 요청 오류를 **관리자 메일로만** 보내는데(`mail_admins`), `ADMINS`가 비어 있으니 아무 데도 남지 않는다. 반대 사례 이미지에서 500이 3번 났는데 컨테이너 로그에는 액세스 로그의 `500`만 있었고 트레이스백은 0줄이었다. CloudWatch로 가도 같다. → `LOGGING`으로 오류를 stdout에 보내는 설정(Django 내장, 패키지 없음). **SPEC-006에 넣을지 Owner 결정.** → **Owner 승인(2026-11-09), 해소 — 3-8.**
* **gunicorn 26의 제어 소켓이 홈 디렉터리를 찾는다.** gunicorn 25.1부터 `gunicornc`용 제어 소켓을 `$HOME/.gunicorn/gunicorn.ctl`에 만든다. 이미지의 `appuser`는 `--no-create-home`이라 매 기동마다 ERROR 한 줄이 남는다. 서비스는 정상이지만, ERROR 로그 알람을 걸면 오탐이 된다. 쓰지 않는 기능이므로 `CMD`에 `--no-control-socket`(Dockerfile — **Owner 영역**).
* `GOOGLE_OAUTH_REDIRECT_URI`도 `PASSWORD_RESET_URL`처럼 prod에서 `http://localhost` 기본값으로 조용히 돈다. 콜백이 실패할 뿐 유출은 없어 이번 범위 밖 — Phase 3 배포 체크리스트.
* `.env.example`(Owner 영역)에 `DJANGO_EMAIL_BACKEND`(선택, 기본 SMTP)와 "prod는 `PASSWORD_RESET_URL`이 https 필수"를 적을 것을 권한다.

### 3-8. 후속 (2026-11-09) — 운영 500의 원인을 컨테이너 로그에 (갭 12)

**Owner 승인 2026-11-09**("Production에서 500 에러의 원인이 로그에 남도록 SPEC-006에 넣기").

| 무엇 | 어떻게 |
| --- | --- |
| 출력 위치 | **stderr 하나**. 컨테이너 런타임이 모은다(`docker logs`, Phase 3 CloudWatch). 컨테이너 안에 로그 파일을 두지 않는다 |
| `django` 로거 | Django 기본의 "DEBUG일 때만 콘솔 + `mail_admins`" 쌍을 **stderr 핸들러 하나로 대체**. 루트로 전파하지 않는다 — 전파하면 모든 줄이 두 번 찍힌다(변이 L2·L4가 고정) |
| `django.request` | **ERROR 이상만**(5xx와 트레이스백). 4xx는 액세스 로그(gunicorn·runserver)에 상태 코드와 함께 이미 있다. Django가 4xx마다 한 줄씩 더 쓰면 양만 늘고, 운영에서는 **누구나 그 양을 늘릴 수 있다**(CloudWatch 수집 비용) |
| 루트 | WARNING 이상 → stderr. 앱 로거(`accounts.emails`, `config.health`)는 지금까지 파이썬의 최후 수단 출력으로만 보였다 — 이제 같은 형식(`시각 레벨 로거 메시지`)으로 나온다 |
| 테스트 설정 | `django.request`를 CRITICAL로 — 테스트는 5xx를 일부러 만든다(OAuth 502, readyz 503 …). 예상 밖 예외는 테스트 클라이언트가 다시 던지므로 트레이스백과 함께 테스트가 실패한다. 실제 설정은 `ErrorLoggingTests`가 새 인터프리터에서 본다 |

**근거**:

* 기본 검증: 테스트 **454개 OK**(새 1개 — prod·local 두 환경), `check` 0 issues, `makemigrations --check` No changes, `ruff` passed.
* 변이 4건 전부 검출: L1 종전과 같은 빈 설정 / L2 `django` 로거 전파 / L3 4xx 줄을 남김 / L4 `django` 로거 없이 루트만.
* 처음에는 L1을 `LOGGING` 삭제로 만들었다. 그러면 test.py가 `LOGGING["loggers"]`를 못 읽어 설정 로딩에서 죽는다. **"검출"이지만 틀린 이유였다**(결과 줄이 `?`). 종전과 동작이 같은 빈 설정으로 바꿔 다시 쟀다.
* 테스트 출력은 609줄 → 13줄. 남은 4줄은 CSRF 거부 WARNING이다. 일부러 거부를 만드는 테스트이고, 운영에서도 보안 신호라 남긴다.

**실제 이미지**(compose 무수정, 테이블이 없는 `postgres` DB에 연결 — "migrate를 안 돌린 배포"):

```text
세션 쿠키 + /api/v1/users/me → 500     쿠키 없이 → 401     없는 경로 → 404
ERROR django.request Internal Server Error: /api/v1/users/me
django.db.utils.ProgrammingError: relation "django_session" does not exist
'Unauthorized' 줄 0 · 'Not Found' 줄 0  (401·404는 액세스 로그에만)
```

이 500 하나에 ERROR 기록이 **두 개** 남았다. 핸들러 중복이 아니라 **예외가 두 번 난 것**이다 — ① 뷰의 인증 단계(`perform_authentication`)가 세션을 읽다 실패하고 ② 그 500 응답을 처리하던 `SessionMiddleware.process_response`가 세션을 다시 읽다 또 실패했다(기록마다 프레임으로 확인). 테스트는 예외 하나 = 트레이스백 하나를 고정한다.

**DevOps 설명 포인트**: "로그가 어디로 가는가"는 설정이 정한다. Django 기본은 개발자 모드(DEBUG)를 전제로 짜여 있다. 운영 모드의 기본 목적지는 메일이었다. 컨테이너 세계의 표준은 **stdout/stderr 하나, 수집은 런타임**(12-factor의 logs)이다.

**보안 노트**: 트레이스백에는 예외 메시지가 들어간다. DB 오류 메시지에는 값이 섞일 수 있다(예: 중복 키 오류의 이메일). 로그도 개인정보 처리 대상이다 — C-1 처리방침의 접속기록 보관 조항과 Phase 3 CloudWatch 보존 기간을 함께 정한다. 지역변수는 찍히지 않는다. 지역변수를 싣는 것은 오류 리포트(메일·DEBUG 페이지)이고 이 핸들러는 아니다.

**다음 개선**:

* Phase 3: 구조화(JSON) 로그는 CloudWatch Logs Insights를 쓸 때 검토한다.
* Phase 3: 잘못된 Host로 오는 스캐너 요청은 `django.security.DisallowedHost` ERROR + 트레이스백을 남긴다 — ALB 리스너 규칙에서 Host를 먼저 거르면 앱까지 오지 않는다.

## 4. TASK-004 — 스모크 여정 15단계 맨바닥 재통과 + 백업·복원 실증 (2026-11-09)

### 4-1. 무엇이 바뀌었나

| 범위 | 내용 |
| --- | --- |
| `scripts/smoke-journey.sh` | 13 재설정(#45 → 콘솔 메일 링크 → #46 → 재사용 400 → 옛 비밀번호 401 → 새 비밀번호 200) / 14 고민 수정(배정 전 200 → 배정 후 409 `NOT_EDITABLE`) / 15 같은 주소 로그인 11번째 429. 스크립트가 저장소 루트에서 돌도록 `cd` |
| 문서 | smoke-test §2(맨바닥 재통과 기록·`/readyz` 주의·역할 표시 보충) · §3(15단계) · §6(**빈 볼륨 복원 순서**) · AI-TOOLING-SETUP-GUIDE §7.3(복원 뒤 역할 스크립트 재실행) |

코드(앱) 변경 없음 — 테스트 수 454 그대로.

### 4-2. 실행 순서와 결과 (실제 출력)

| # | 단계 | 결과 |
| --- | --- | --- |
| 1 | 백업 전 행 수 기록 | 21개 테이블 |
| 2 | §6대로 `pg_dump` → `~/chamneul-backup-20261109.sql`(저장소 밖, 권한 600) | 완료 마커 1, COPY 21, `chamneul_ro` 권한 34줄 |
| 3 | `down -v` → `up -d --build` | `pgdata` 삭제·재생성, `db Waiting → Healthy → app Started` |
| 4 | 마이그레이션 전 `/healthz`·`/readyz` | **200 · 200** (4-4) |
| 5 | `migrate` / `createcachetable` | 25개 적용 / exit 0 |
| 6 | 일회용 관리자 `createsuperuser --noinput` | `UserRole` 행 `['ADMIN']`, API `["USER","ADMIN"]` |
| 7 | 여정 15단계 | **첫 실행에 전항 통과**, 출력에 실제 토큰 0개 |
| 8 | 역할 없이 **연습용 DB**(`restore_probe`)에 복원 | 데이터 21/21 들어간 뒤 `ERROR: role "chamneul_ro" does not exist`, **exit 3** |
| 9 | `setup-postgres-ro-role.sh` | 비밀번호 열·세션 거부. `default_transaction_read_only`를 끄고도 UPDATE·DELETE·CREATE 거부(권한이 진짜 경계) |
| 10 | §6대로 실제 복원 | exit 0, ERROR 0. **행 수 21개 테이블 전부 백업 전과 일치** |
| 11 | 복원 뒤 읽기 전용 역할 | ⚠️ **비밀번호 열·세션 읽기 허용**(4-3) |
| 12 | 스크립트 재실행 | 다시 거부 `f\|f` |
| 13 | MCP `postgres-ro` | `password authentication failed` — 서버가 기동 때 읽은 옛 비밀번호. **Owner `/mcp` Reconnect 필요** |

### 4-3. 찾은 것 — 복원이 읽기 전용 역할의 권한을 넓힌다

* **현상**: 9단계에서 거부되던 `accounts_user.password`와 `django_session`이 10단계 복원 뒤 읽혔다(비밀번호 해시 89자 확인, 세션은 키를 읽으면 로그인 탈취가 된다).
* **원인**: 역할 스크립트는 "앞으로 만들어질 테이블은 이 역할이 읽어도 된다"(`ALTER DEFAULT PRIVILEGES ... GRANT SELECT ON TABLES`)를 건다. `--clean` 복원은 테이블을 지우고 **새로 만든다** — 그 순간 기본 권한이 붙어 테이블 전체 SELECT가 생긴다. 덤프에는 원래 상태가 "열 단위 GRANT"로만 기록돼 있다. "테이블 전체 권한 없음"은 기록되지 않으므로 아무것도 그것을 되돌리지 않는다.
* **원래 DB는 안전했다**: 덤프의 권한 줄을 보면 `accounts_user`는 비밀번호를 뺀 열 단위 GRANT만 있고, `django_session`에는 GRANT가 없다. 문제는 **복원 경로에서만** 생긴다.
* **왜 순서로 피할 수 없나**: 역할이 없으면 복원이 `GRANT`에서 멈춘다(8단계). 역할을 먼저 만들면 권한이 넓어진다(11단계). 둘 다 문제다. 지금의 답은 **복원 뒤 스크립트를 한 번 더**다(회수 → 재부여, 12단계).

### 4-4. DevOps 설명 포인트

* **readiness는 스키마를 보지 않는다.** 마이그레이션 전에도 `/readyz` 200이었다. Phase 3에서는 마이그레이션 Job 완료 뒤에 롤아웃을 시작한다. readiness가 "준비됨"이라고 해도 테이블이 없을 수 있다.
* **백업은 복원해 봐야 백업이다.** 이번에 처음으로 §6 절차를 끝까지 돌렸다. 문서에 없던 순서 조건 2개가 나왔다. 그중 하나는 오류 없이 지나가는 보안 문제였다. 복원 후 검증은 "exit 0"이 아니라 **행 수 비교 + 권한 확인**이다.
* **역할은 DB가 아니라 클러스터에 속한다.** `pg_dump`는 한 DB만 뜬다. 역할(`chamneul_ro`)은 덤프에 없다. 운영(RDS)에서도 같다 — 역할·권한은 IaC나 마이그레이션으로 관리해야 복원·재생성 때 재현된다.

### 4-5. 보안 노트

* 재설정 토큰은 스크립트가 `docker compose logs`에서 읽어 바로 쓰고 **화면에 찍지 않는다**(`uid` 앞 6자만, `token=<가림>`). 실행 출력에서 실제 토큰 패턴 0개를 확인했다.
* 일회용 관리자 비밀번호는 스크래치패드의 권한 600 파일에만 두었다가 복원 뒤 지웠다. 덤프 내용은 화면에 출력하지 않았다(개수·권한 줄만).
* 11단계의 넓어진 권한은 복원 직후부터 12단계까지 몇 분간 열려 있었다. 그동안 MCP 서버는 옛 비밀번호로 접속에 실패하는 상태였다(13단계). 그 권한으로 실행된 것은 이 문제를 확인한 쿼리 2건뿐이다(비밀번호 열 SELECT — 값은 출력하지 않고 길이만 봤다).

### 4-6. 테스트 방법 (재현)

```bash
# 1) 백업 (§6)   2) down -v → up -d --build   3) migrate → createcachetable → createsuperuser --noinput
SMOKE_ADMIN_PASSWORD='…' bash scripts/smoke-journey.sh      # 15단계
./.claude/mcp/setup-postgres-ro-role.sh                     # 역할 생성
# 4) 복원 (§6)   5) 스크립트 재실행   6) /mcp → postgres-ro Reconnect
```

같은 시간에 네 번 이상 돌리면 가입 IP 한도(10회/시간, 실행당 3회)에 걸린다 — §6 카운터 비우기.

### 4-7. 다음 개선 — 결정 필요

* **역할 스크립트의 "새 테이블 자동 읽기 허용"을 없앨지.** 지금은 fail open이다 — 앞으로 마이그레이션이 민감한 테이블(예: 토큰 저장)을 추가해도 이 역할이 **자동으로** 읽는다. 없애면 새 테이블은 스크립트를 다시 돌릴 때까지 안 보이고(fail closed), 4-3의 복원 문제도 함께 사라진다(복원 때 붙을 기본 권한이 없다 — 단 **변경 뒤에 뜬 덤프부터**. 지금 덤프는 끝부분에 그 기본 권한 설정을 담고 있어 복원하면 다시 생긴다. 그래서 스크립트가 그것을 명시적으로 회수해야 한다). 대가는 마이그레이션마다 스크립트 재실행. ADR-009 도구 설계 변경이라 **Owner 결정**. 권고: 없앤다. → **Owner 결정 2026-11-09 "보안이 우선시되는 쪽" — 없앴다.**

### 4-8. 후속 (2026-11-09) — 읽기 전용 역할을 fail closed로

| 확인 | 결과 |
| --- | --- |
| 스크립트 실행 전 → 후 자동 읽기 규칙(`pg_default_acl`) | **1개 → 0개** (스크립트가 `ALTER DEFAULT PRIVILEGES ... REVOKE`로 회수) |
| 기존 경계 | password 열 `false` · `django_session` `false` · email 열 `true` · `concerns_concern` `true` · `django_cache` `true` |
| 실행 뒤 새로 만든 테이블 | 읽기 권한 **`false`** (만들고 바로 지움) |
| 지금 DB의 스키마 덤프 | 자동 규칙 줄 **0개** (파일로 저장하지 않고 개수만) |
| 옛 덤프(11-09 백업)를 연습용 DB에 복원 | exit 0, ERROR 0, password 열 **`false`**, 세션 **`false`**, 사용자 27명. 단 옛 덤프가 끝부분에서 자동 규칙 **1개를 되살린다** → 복원 뒤 스크립트 재실행은 계속 필수 |

대가: 마이그레이션으로 테이블이 생기면 스크립트를 다시 돌려야 MCP에서 보인다(AI-TOOLING-SETUP-GUIDE §7.3 5번). 실행할 때마다 비밀번호가 바뀌므로 `/mcp` Reconnect.

## 5. TASK-005 — 마무리: 서브에이전트 리뷰 2종 (2026-11-09)

`security-reviewer`와 `devops-local-platform`을 병렬 백그라운드로 돌렸다. 대상은 리뷰 시점의 `origin/main...HEAD`(커밋 10개 — 리뷰 반영 커밋 전)이고, 둘 다 읽기 전용이다.

| 리뷰 | 판정 | 건수 |
| --- | --- | --- |
| security-reviewer | Needs fix, **Blocker·High 없음** | Medium 3 · Low 4 · Info 7 |
| devops-local-platform | Needs fix, **Blocker 없음** | High 1 · Medium 4 · Low 5 · Info 2 |

리뷰가 지적한 사실은 전부 직접 다시 확인했다(README 문구, `.env.example` 4행, Django `_cull`·`COUNT(*)` 소스, 계산).

### 5-1. 이 PR에서 고친 것 (결정 불필요)

| 출처 | 내용 | 확인 |
| --- | --- | --- |
| devops H-1 | **README Quick Start와 smoke-test §6 "DB 안전 초기화"에 `createcachetable`이 없었다** — 이 브랜치가 만든 회귀. 그대로 따르면 #2·#3·#45·#46만 500 | 두 곳에 추가 + 초기화에 역할 스크립트 |
| devops M-1 | 의존성이 바뀐 뒤 `up -d --build -V app`이 STATUS·리뷰 노트에만 있었다 | README·smoke-test §6에 절차로 |
| 보안 M-1 | **prod가 `DRF_NUM_PROXIES` 없이 조용히 0으로 뜬다.** ALB 뒤에서는 모두가 ALB 주소 하나로 세어져, 한 명이 전체 가입·로그인을 막는다 | prod 기동 가드(값은 배포가 정한다). 빈 값은 없음으로 본다. 테스트 +1(전체 **455개**), 가드 제거 변이 검출 |
| 보안 M-2(일부) | 리뷰 노트 §1-8의 "IP 수천 개"는 계산 실수 — 실제 **약 84개** | §1-8 정정 |
| 보안 L-3(일부) | 일반 복원 절차에 역할 재실행·검증이 없었다(빈 볼륨 순서에만) | §6 복원 코드에 재실행, 검증 `f\|f\|0`(`pg_default_acl` 포함) |
| 보안 L-4 · devops L-2·L-3 | 스모크 쿠키 항아리가 공유 `/tmp/smoke`(기본 umask)에 남고 관리자 세션을 로그아웃하지 않았다. 덤프 명령에 umask가 없었다 | `mktemp -d` + `umask 077` + `trap` 삭제 + 관리자 로그아웃. 덤프는 `(umask 077; …)`. 폴더 700·파일 600·종료 후 삭제 확인 |
| devops L-1 | `/readyz` 안내가 "Job 뒤 롤아웃"까지만 있었다 | expand/contract, Job에 `createcachetable`, 이미지 안 `manage.py`는 prod 명시 |
| devops I-2 | README의 엔드포인트 44·테스트 291이 낡았다 | 48·455, `/readyz` |

### 5-2. Owner 결정 필요

| # | 출처 | 쟁점 | 권고 |
| --- | --- | --- | --- |
| 1 | devops M-2 | **DB `connect_timeout`이 없다.** DB가 패킷을 버리는 장애(보안그룹 차단 등)면 `/readyz`가 연결을 기다리며 sync 워커 3개를 다 잡는다. 그러면 같은 워커가 답하는 `/healthz`도 응답하지 못한다. liveness가 실패해 모든 파드가 재시작된다 — **ADR-010이 막으려던 연쇄 그대로다.** ADR-010은 `connect_timeout`을 Phase 3로 미뤘다 | **이 PR에서** `DATABASES OPTIONS connect_timeout: 3`(+ `CONN_HEALTH_CHECKS: True`). `docker compose pause db`로 재현 확인 → **`connect_timeout` 3초만 승인·반영 2026-11-16(§5-6)**. `CONN_HEALTH_CHECKS`는 넣지 않았다(요청마다 질의 1회 추가 — 따로 결정할 것) |
| 2 | 보안 M-2 | 컬링으로 계정 한도를 지우는 데 IP 약 84개면 된다. 쓰기마다 `SELECT COUNT(*)`도 돈다 | 로그인에 **시간당 IP 한도**를 하나 더(예: 200회/시간 → 필요한 IP 약 500개). 근본 해결은 Phase 3 Redis. 결정 2의 수치 변경이라 Owner 몫 → **승인·반영 2026-11-16, 200회/시간(§5-6)** |
| 3 | 보안 M-3 | `.env.example` 4행 `DJANGO_SETTINGS_MODULE=config.settings.local` — 이 파일을 배포 환경변수로 그대로 쓰면 `wsgi.py`의 prod 기본값이 무력화된다(DEBUG=True, 콘솔 메일, prod 가드 미실행). compose는 `docker-compose.yml:31`에서 이미 지정하므로 이 줄은 필요 없다 | **Owner가 그 줄 삭제**(Owner 파일). `local.py`의 배포 환경 감지는 Phase 3에 → **이번에 한해 AI 수정 허락(2026-11-16), 삭제·반영(§5-6)** |
| 4 | 보안 L-3 | 역할 스크립트는 재실행 때 금지 목록(비밀번호 열·세션) 밖의 **새 테이블을 전부** 다시 연다 — fail closed는 다음 재실행까지만 | 허용 목록 방식은 ADR-009 도구 설계라 Phase 3 전 검토. 그때까지 테이블을 추가하는 마이그레이션은 스크립트 재실행 전에 금지 목록을 확인 |

### 5-3. Owner 인프라 파일 — 코멘트만 (devops)

| # | 파일 | 권고 |
| --- | --- | --- |
| M-3 | docker-compose.yml | 나중에 prod 프로필을 만들 때 `.:/app` bind mount를 빼야 한다. 그대로 두면 매니페스트가 가려져 §3-2의 "Admin 500 + 헬스 200"이 재현된다. venv를 `/app` 밖(`UV_PROJECT_ENVIRONMENT=/opt/venv`)에 두면 익명 볼륨과 `-V` 함정이 함께 사라진다 |
| M-4 | .dockerignore | `COPY . .`가 `.playwright-mcp/`(로컬 화면 내용), `.claude/`(로컬 설정), `specs/`·`scripts/`·`README_AIUSAGE.md`까지 이미지에 넣는다. 레지스트리에 올리기 전에 제외해야 한다 |
| L-4 | Dockerfile | `CMD`에 `--no-control-socket`(갭 13, gunicorn 26.0.0에 옵션 있음 확인). `/app/logs` 생성 줄은 "로그는 stderr" 원칙과 맞지 않는다 |
| L-5 | Dockerfile | 런타임 스테이지에 `ENV DJANGO_SETTINGS_MODULE=config.settings.prod`. 이미지 안 `manage.py`(Job·`check --deploy`)가 local로 도는 것을 막는다. compose는 local로 덮어쓴다 |

### 5-4. Phase 3 체크리스트로 (기록만)

* 보안 L-1: 메일 백엔드를 허용 목록으로(SMTP·SES만), `SECRET_KEY` 길이·placeholder 검사, `GOOGLE_OAUTH_REDIRECT_URI`의 prod http 기본값.
* 보안 L-2: ALB 리스너 규칙으로 외부에서 오는 `/healthz`·`/readyz`를 막는다(대상 그룹 헬스체크는 영향 없음).
* devops I-1: DB 장애 중에는 `/readyz` 503마다 `ERROR django.request Service Unavailable: /readyz`가 찍힌다(코드상 추정). ERROR 알람 규칙에 반영한다.
* 의도적으로 남긴 위험: 계정 잠금형 DoS, 동시 요청 시 카운터 과소집계(DRF 스로틀의 읽기→쓰기가 원자적이지 않음), IPv6 /64 집계, 메일 발송을 요청 경로 밖으로.

### 5-5. DevOps 설명 포인트

* **리뷰가 잡은 가장 큰 것은 코드가 아니라 절차였다.** `createcachetable`을 §2-1에는 넣었다. 하지만 README와 초기화 절차에는 넣지 않았다. 같은 절차가 문서 여러 곳에 있으면, 하나를 바꿀 때 나머지가 낡는다.
* **분리는 자원까지 분리돼야 분리다.** liveness와 readiness를 나눠도 같은 sync 워커 3개가 둘 다 답한다. 느린 readiness 하나가 liveness를 함께 죽일 수 있다(5-2 #1).

### 5-6. 후속 (2026-11-16) — Owner 승인 3건 반영

| 항목 | 구현 | 확인 |
| --- | --- | --- |
| DB `connect_timeout` 3초 | `DATABASES["default"]["OPTIONS"]` | 테스트 2개: 연결 인자에 실제로 들어가는가 + 새 인터프리터에서 DB를 패킷만 버리는 주소(`10.255.255.1`)로 돌렸을 때 `/readyz`가 6초 안에 503을 내는가. 넣기 전에는 **20초 안에 돌아오지 않았다**. 넣은 뒤 실측 **503, 3.0초** |
| 로그인 시간당 IP 한도 200회 | `LoginIPHourThrottle`(`auth_login_ip_hour`)을 분당 IP 한도 다음, 주소 한도 **앞**에 | 테스트 1개 + 결정 표 테스트 갱신. 변이 2건 검출: 한도 제거 / 주소 한도 뒤로 옮김(그러면 거절된 요청이 주소 카운터를 연다). 10만 행을 채우는 데 필요한 IP: 약 84개 → **약 500개** |
| `.env.example` | `DJANGO_SETTINGS_MODULE` 줄을 지우고 이유를 주석으로. 운영 전용 값(`DJANGO_EMAIL_BACKEND`·`DRF_NUM_PROXIES`)은 **주석으로만** 안내한다 — 미리 채운 값이 배포로 복사되면 틀린 숫자가 조용히 통과한다. 값 뒤 같은 줄 주석(`docker run --env-file`은 주석을 값으로 읽는다)과 끝 줄바꿈 정리 | 로컬 compose·호스트 테스트 영향 없음(compose가 local을 직접 지정, `manage.py` 기본값 local). Owner의 실제 `.env`에 같은 줄이 있다면 지워도 된다 |

**남은 것**: `connect_timeout`은 **새 연결**만 지킨다. 이미 열린 영구 연결(`CONN_MAX_AGE` 60초) 위의 질의가 매달리는 경우는 막지 못한다. Phase 3에서 probe `timeoutSeconds`와 `tcp_user_timeout`을 함께 검토한다(ADR-010 후속 기록).
