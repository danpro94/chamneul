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
* **구현 중 찾은 위험 2건**도 닫았다.
  * **DatabaseCache 컬링 우회**: 기본 `MAX_ENTRIES=300`을 넘으면 Django가 **키 순서로 행 1/3을 지운다.** 키는 누구나 늘릴 수 있다(시도한 주소마다 1개). 기본값 그대로면 공격자가 무작위 주소를 섞어 보내 피해자의 카운터를 지울 수 있다 → 100,000으로 올렸다. 350개를 넣어 하나도 지워지지 않는지 테스트로 고정했다.
  * **오류 리포트의 비밀번호**: 스로틀은 뷰의 `sensitive_variables()` **밖**에서 본문을 읽는다. 그 프레임에서 예외가 나면 운영 오류 리포트에 지역변수가 찍힌다. 본문을 지역변수에 담기만 해도 비밀번호가 찍힌다는 것을 변이 M14가 실제로 보여 줬다. 그래서 지역변수에 담지 않는다.
* **감수하는 것**: 계정 기준 한도는 남이 일부러 다 써 버릴 수 있다. 그러면 그 계정은 1시간 동안 로그인 429를 받는다(잠금형 서비스 거부). 계정 잠금보다는 약한 피해다(spec §5가 잠금을 기각한 이유). 실패만 세기·CAPTCHA는 Phase 3.
* **기존 테스트 1개의 단언 범위를 좁혔다**: `test_changes_nothing_in_the_database`(#45는 DB를 쓰지 않는다)가 결정 1의 카운터 쓰기와 부딪혔다. 목적(토큰·세션·사용자 행을 쓰지 않는다)은 유지하고 `django_cache` 쓰기만 예외로 했다 — **Owner 확인 대상**.

### 1-7. 다음 개선

* 요청량이 늘면 Redis로 전환(`CACHES` 블록만).
* 로그인 계정 한도를 "실패만 세기"로 — 정상 로그인이 한도를 쓰지 않게 한다(Phase 3, 뷰 후처리 필요).
* Phase 3 배포 체크리스트: `DRF_NUM_PROXIES`를 실제 프록시 수에 맞춘다 + `createcachetable`을 마이그레이션 Job에 넣는다.
