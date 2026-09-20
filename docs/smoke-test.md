# 스모크 테스트 — Phase 2 로컬 런타임

> 최초 작성 2026-09-16 (SPEC-004/TASK-001). 아래 출력은 **실제 실행 결과**다 — 추측으로 적은 값은 없다.
> 실행하지 않은 명령은 "권장 명령"으로 표시한다(CLAUDE.md §12).

## 1. 목적

이 문서가 답하는 질문은 하나다. **"볼륨을 비운 맨바닥에서 이 시스템이 일어서고, 사용자가 처음부터 끝까지 지나갈 수 있는가?"**

자동 테스트(작성 시점 283개, 이후 SPEC-004/TASK-003까지 **291개**)는 전부 **테스트 전용 DB**에서 돌았다. Django는 테스트마다 DB를 새로 만들고 끝나면 지운다. 따라서 "코드가 의도대로 동작한다"는 확인됐지만 **"진짜 컨테이너가 맨바닥에서 일어선다"는 이 문서 이전에 미확인이었다.**

## 2. 맨바닥 기동

> ⚠️ **이 문서의 모든 측정은 `runserver` 위에서 수행됐다.** 저장소에 `docker-compose.override.yml`이 커밋돼 있고(`command: python manage.py runserver`), Compose는 override를 자동으로 병합하므로 그냥 `docker compose up`을 하면 **항상 개발 서버**로 뜬다. 이미지의 `CMD`는 `gunicorn --workers 3`(`Dockerfile:61`)이며 **그 경로는 아직 한 번도 검증하지 않았다**(§5 갭 3). 확인 방법: `docker compose ps`의 COMMAND 열, 또는 응답 헤더의 `Server: WSGIServer/...`.

> ⚠️ `down -v`는 **PostgreSQL 볼륨을 삭제**한다. 로컬 데이터가 전부 사라진다. 보존이 필요하면 §6의 백업 절차를 먼저 수행한다.

```bash
docker compose down -v          # 컨테이너 + 네트워크 + named volume 삭제
docker compose up -d --build
docker compose ps
```

실제 출력:

```
 Volume chamneul_pgdata Removing / Removed
 ...
 Volume chamneul_pgdata Creating / Created
 Container chamneul-db-1 Starting / Started
 Container chamneul-db-1 Waiting / Healthy      <- app은 db가 healthy가 된 뒤에 뜬다
 Container chamneul-app-1 Starting / Started

NAME             SERVICE   STATUS
chamneul-app-1   app       Up
chamneul-db-1    db        Up (healthy)
```

`db Waiting -> Healthy -> app Starting` 순서가 핵심이다. compose의 `depends_on: condition: service_healthy`가 동작한다는 증거이며, 이것이 없으면 앱이 DB보다 먼저 떠서 첫 요청이 실패한다.

### 2-1. 마이그레이션 적용

```bash
docker compose exec app python manage.py migrate
```

25개 마이그레이션이 적용된다(contenttypes/auth → accounts → admin → concerns → advice → advisors → notifications → sessions). `accounts.0001_initial`이 `admin.0001_initial`보다 먼저 와야 한다 — 커스텀 User 모델이기 때문이다.

### 2-2. 관리자 부트스트랩

```bash
docker compose exec -it app python manage.py createsuperuser
```

비대화식(스크립트용):

```bash
docker compose exec -T \
  -e DJANGO_SUPERUSER_EMAIL=root@chamneul.local \
  -e DJANGO_SUPERUSER_NICKNAME=root \
  -e DJANGO_SUPERUSER_PASSWORD='<password>' \
  app python manage.py createsuperuser --noinput
```

**확인해야 할 것**: superuser 생성이 `UserRole(ADMIN)` 행까지 만들었는가 (ADR-003 §1).

```
superuser : root@chamneul.local | is_superuser: True | is_staff: True
보유 역할 : ['USER', 'ADMIN']
```

이 행이 없으면 `IsAdmin`은 `is_superuser`로 통과시키지만, #43의 "마지막 관리자" 판정은 `UserRole` 행만 세므로 관리자 수가 0으로 계산된다.

### 2-3. 기동 확인

```bash
curl -i http://localhost:8000/healthz
```

```
HTTP 200  (0.0075s)   {"status": "ok"}
```

## 3. 사용자 여정 — 12단계 전항 통과

`curl`로 세 배우(사용자 / 조언가 / 관리자)의 세션을 **동시에** 유지하며 한 줄로 이어 통과시켰다. 각 단계는 직전 응답의 id를 다음 요청에 쓴다.

세션·CSRF 처리 방식:

```bash
# 배우마다 쿠키 항아리를 따로 둔다
curl -s -c user.jar http://localhost:8000/api/v1/csrf      # csrftoken 쿠키 획득 (#44)
TOKEN=$(grep csrftoken user.jar | awk '{print $7}')
curl -s -c user.jar -b user.jar -X POST \
     -H 'Content-Type: application/json' -H "X-CSRFToken: $TOKEN" \
     -d '{...}' http://localhost:8000/api/v1/auth/signup
```

**상태 변경 요청은 전부 `X-CSRFToken`이 필요하다** — 익명 요청(회원가입·로그인)도 예외가 아니다(ADR-002 §5). 토큰 없이 보내면 403이며, 이는 정상 동작이다.

| # | 단계 | 결과 | 확인한 것 |
| --- | --- | --- | --- |
| 1 | 회원가입 (#2) | **201** | `sessionid` 쿠키 발급 — 가입 즉시 로그인 |
| 2 | 로그인 (#3) | **200** | 관리자(superuser) 세션 |
| 3 | 고민 작성 (#16) / 목록 (#17) | **201 / 200** | `total=1` |
| 4 | 관리자 고민 목록 (#22) | **200** | 방금 만든 고민이 보인다 |
| 4b | 역할 부여 (#42) | **201** | `roles=['USER','ADVISOR']` |
| 4c | 배정 (#24) | **201** | `assignment_id` 발급 |
| 5 | 역할 전환 (#10) | **200** | `active_role=ADVISOR` |
| 5b | 배정 고민 목록/상세 (#20·#21) | **200 / 200** | `total=1` |
| 6 | 조언 작성 (#28) | **201** | `status=PENDING`, `version=1` |
| 7 | 리뷰 목록 (#32) / 승인 (#33) | **200 / 200** | `status=APPROVED` |
| 7b | concern 상태 전이 | **200** | `ASSIGNED → ANSWERED` |
| 8 | 받은 조언 (#26) / 상세 (#27) | **200 / 200** | `reject_reason` **미노출**(승인 건, §6.2) |
| 9 | 피드백 (#34) | **201** | `status=SUBMITTED` |
| 10 | 알림 (#39·#41) | **200 / 200** | `unread_count 1 → 0`, `target_url` 이동 **200** |
| 10b | 조언가 알림함 | **200** | 본문이 **고정 문구**(고민 요약 사본 아님) |
| 11 | 역할 회수 (#43) | **204** | 직후 #20 → **403**, `roles=["USER"]` |
| 12 | 로그아웃 (#4) | **200** | 직후 `/users/me` → **401**(서버 세션 삭제) |

### 이번 실행에서 실제로 확인된 설계 판단 3건

* **알림 `target_url`이 실제로 열린다** — `ADVICE_APPROVED` 알림의 `target_url`을 수신자 세션으로 GET → 200. C-10 규약이 실환경에서 동작한다.
* **알림 본문에 고민 요약 사본이 없다** — 조언가 알림함의 `message`가 `"배정된 고민의 내용은 배정 상세에서 확인할 수 있습니다."`. 2026-09-16 결정(리뷰 S-2/AR-08)이 반영돼 있다.
* **역할 회수가 즉시 권한을 닫는다** — 회수 직후 #20이 403, `/users/me/roles`가 `["USER"]` + `active_role=USER`. A-3가 실환경에서 닫혀 있다.

### 실행 중 발견한 것

**#28의 `reflective_questions`는 배열이 아니라 문자열이다.** 스모크 스크립트가 배열을 보냈고 API가 400 + `{"reflective_questions": ["Not a valid string."]}`로 정확히 거절했다. api.md·model.md·모델 정의가 모두 `TextField`로 일치하므로 **스크립트가 틀린 것**이지 제품 결함이 아니다. 다만 같은 오해가 테스트 픽스처 3곳에도 있어(`accounts/tests.py`, `notifications/tests.py`) 함께 정정했다 — 단언 대상이 아니라 통과에는 영향이 없었지만, 읽는 사람이 배열 필드로 오해할 여지가 있었다.

## 4. 비정상 경로 — DB가 없을 때 무슨 일이 일어나는가

CLAUDE.md §11이 Owner에게 설명할 수 있기를 요구하는 항목이다. **실측 결과는 아래와 같다.**

### 4-1. 마이그레이션을 적용하지 않고 기동했을 때

| 요청 | 결과 |
| --- | --- |
| `GET /healthz` | **200** `{"status": "ok"}` |
| `GET /api/v1/csrf` | **200** (DB 미접촉) |
| `GET /api/v1/users/me` | **401** (인증 검사가 DB보다 먼저) |
| `POST /api/v1/auth/signup` | **500** |

앱 로그:

```
django.db.utils.ProgrammingError: relation "accounts_user" does not exist
```

**판별 요령**: `/healthz`는 초록인데 쓰기 API가 500이고 로그에 `relation ... does not exist`가 보이면 **마이그레이션 미적용**이다. `migrate`를 실행하면 해결된다.

### 4-2. DB를 정지시켰을 때

```bash
docker compose stop db
```

| 요청 | 결과 |
| --- | --- |
| `GET /healthz` | **200** (0.04s) |
| `GET /api/v1/users/me` | **500** (0.14s) |

앱 로그:

```
django.db.utils.OperationalError: failed to resolve host 'db': [Errno -2] Name or service not known
```

**중요**: `/healthz`는 **DB 장애 중에도 200을 반환한다.** 이는 버그가 아니라 설계다 — [config/health.py](../config/health.py)의 주석이 명시하듯 liveness 프로브(앱 프로세스가 살아 있는가)이지 readiness 프로브(요청을 처리할 수 있는가)가 아니다. **운영 함의**: 로드밸런서가 `/healthz`만 보면 DB가 죽은 인스턴스에도 트래픽을 보낸다. DB 인지 readiness 프로브(`/healthz/db`)는 의도된 후속 과제다(§5 갭 7).

### 4-3. DB를 다시 켰을 때 — 앱 재시작이 필요한가

```bash
docker compose start db      # healthy까지 6초
```

**앱을 재시작하지 않고** 같은 요청을 다시 보냈다:

| 확인 | 결과 |
| --- | --- |
| `app StartedAt` | 재기동 전후 **동일** (재시작 없음) |
| `GET /api/v1/users/me` | **200** (0.09s) |
| 사용자 여정 12단계 전체 | **전항 재통과** |

**답**: 앱 재시작이 **필요 없다.** 다만 이유를 정확히 말해야 한다 — 이 프로젝트의 `CONN_MAX_AGE`는 **60**이다(`config/settings/base.py`, `DB_CONN_MAX_AGE` 기본값). 즉 연결을 재사용한다. 그럼에도 회복되는 것은 Django가 **요청이 끝날 때 오류가 난 연결을 폐기**하기 때문이다(`close_if_unusable_or_obsolete`). 죽은 연결이 다음 요청까지 살아남지 않으므로 새로 맺는다.

> **이 결론은 서버에 의존한다.** 위 측정은 단일 프로세스(`runserver`)에서 했다. `gunicorn --workers 3`에서는 워커마다 연결을 쥐고 있어, DB 재기동 직후 **워커 수만큼 실패 요청이 먼저 발생**할 수 있다. gunicorn 경로는 아직 검증하지 않았다(§5 갭 3).

## 5. 알려진 갭 — Phase 2에서 의도적으로 열어둔 것

해결이 아니라 **기록**이 목적이다. Phase 3 진입 전에 이 목록을 다시 읽는다.

| # | 갭 | 영향 | 처리 |
| --- | --- | --- | --- |
| 1 | **브루트포스 로그인 방어 부재** — IP·계정 기준 레이트 리밋 없음 | 비밀번호 대입 공격에 무방비. 로컬 전용이라 현재 노출 없음 | Phase 3 (`.claude/rules/security.md` 명시) |
| 2 | **정적파일이 서빙되지 않는다** — `collectstatic`은 **빌드 때 수행된다**(`Dockerfile:31`). 문제는 ① bind mount `.:/app`(`docker-compose.yml`)이 이미지의 `/app/staticfiles`를 **가리고**, ② `DEBUG=False`에서 정적파일을 서빙할 주체(WhiteNoise·리버스프록시)가 없다는 것 | `DEBUG=False`에서 Django Admin CSS가 깨진다. API 응답에는 영향 없음 | Phase 3. *(2026-09-17 정정: 종전 서술 "collectstatic 없음"은 사실이 아니었다 — 원인이 틀리면 이미 있는 것을 다시 추가하게 된다)* |
| 3 | **운영 경로(gunicorn + prod settings)를 한 번도 띄워보지 않았다** — override를 빼는 것만으로는 부족하다. `docker-compose.yml`이 `DJANGO_SETTINGS_MODULE: config.settings.local`을 **고정**하므로, override만 제거하면 `gunicorn + local settings`라는 어느 쪽도 아닌 조합이 된다. 진짜 운영 경로는 **둘 다** 필요하다: `docker compose -f docker-compose.yml up -d` + `DJANGO_SETTINGS_MODULE=config.settings.prod` 주입 | gunicorn 실기동·정적파일·HTTPS 리다이렉트가 전부 미검증 | Phase 3 |
| 4 | **고민 종료(`CLOSED`) 사용자 API 부재** | CLAUDE.md §6.6은 "사용자가 명시적으로 닫는다"고 서술하나 그 API가 없다. Phase 2는 **Django Admin으로만** 닫는다(Owner 결정 2026-09-16, D-4) | Phase 3 후보 |
| 5 | **회수된 조언가의 배정 잔존** | 자격을 잃은 조언가의 배정이 남고 concern은 `ASSIGNED` 유지. #23 admin 상세에서 식별 가능하며 관리자가 #25로 해제한다 | 의도된 동작(SPEC-003 §7 결정 3) |
| 6 | **실제 경합 미재현** | 잠금의 *존재*는 SQL 수준 테스트(`StateTransitionLockingTests`)로 고정했으나, 두 요청을 실제로 동시에 보내본 적은 없다 | Phase 3 (`TransactionTestCase` + 스레드) |
| 7 | **DB 인지 readiness 프로브 부재** | §4-2 참조. `/healthz`가 DB 장애 중에도 초록 | Phase 3 (`/healthz/db`) |
| 8 | **`DEBUG=True`에서 500이 전체 트레이스백 HTML** | 로컬 전용. 운영은 `DEBUG=False` 강제(§10) | 의도된 동작 |
| 9 | **`accounts`의 M4-1~M4-3 자동 테스트 0건** | 이 스모크가 회원가입(#2)·로그인(#3)·로그아웃(#4)은 실환경에서 덮는다. 그러나 **#5·#6(Google OAuth)과 #8(프로필 수정)은 자동 테스트도 스모크도 없다** — 이 프로젝트에서 **검증 수단이 0개인 유일한 영역**이다 | Phase 3 **최우선** |

## 6. 운영 체크리스트

### 로그 확인

```bash
docker compose logs app --tail 50        # 앱
docker compose logs db --tail 50         # DB
docker compose logs -f app               # 실시간
docker compose logs app 2>&1 | grep -iE "error|exception"
```

운영 경로(gunicorn)에서는 요청 로그도 같은 스트림으로 나온다 — 이미지 `CMD`에 `--access-logfile -`·`--error-logfile -`이 있다(2026-09-17 추가). 이 옵션이 없으면 gunicorn은 액세스 로그를 내보내지 않아 `docker compose logs app`에 **요청 기록이 한 줄도 남지 않는다**.

### DB 백업 (볼륨 삭제 전 필수)

```bash
# 자격증명을 화면에 찍지 않고 컨테이너 환경변수를 그대로 쓴다
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' \
  > ~/chamneul-backup-$(date +%Y%m%d).sql

# 검증: 정상 종료 마커가 있어야 한다
grep -c "PostgreSQL database dump complete" ~/chamneul-backup-*.sql
```

> **덤프를 저장소에 두지 말 것.** CLAUDE.md §10이 로컬 DB 덤프를 커밋 금지 대상으로 규정한다. 프로젝트 디렉터리 바깥에 둔다.

### 복원

```bash
docker compose stop app          # 앱이 잡은 연결 때문에 --clean의 DROP이 락 대기할 수 있다
cat ~/chamneul-backup-YYYYMMDD.sql | \
  docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose start app
```

`ON_ERROR_STOP=1`이 없으면 **부분 복원이 성공처럼 보인다** — psql은 기본적으로 오류를 만나도 계속 진행한다.

### DB 안전 초기화

```bash
docker compose down -v          # 볼륨 삭제
docker compose up -d
docker compose exec app python manage.py migrate
docker compose exec -it app python manage.py createsuperuser
```

### ⚠️ 화면 캡처 전 확인

`docker compose config`는 병합된 설정을 출력하면서 **`.env`의 값을 전부 평문으로 찍는다** — Google OAuth client secret과 DB 비밀번호가 포함된다. 디버깅용으로는 유용하지만 **터미널 캡처를 공유·공개할 때 사고 1순위**다. 설정 구조만 보려면 서비스·키만 추려서 본다:

```bash
docker compose config --services
docker compose config | grep -vE "SECRET|PASSWORD|CLIENT_SECRET"
```

### 포트 충돌

| 포트 | 용도 | 충돌 시 |
| --- | --- | --- |
| `8000` | 앱 | 다른 Django/개발 서버와 흔히 충돌. `lsof -i :8000`으로 확인 |
| `15432` | PostgreSQL(호스트 노출) | 표준 5432를 피해 매핑했으므로 로컬 PostgreSQL과 충돌하지 않는다 |

### 현재 상태 빠른 점검

```bash
docker compose ps                                        # 두 서비스, db는 healthy
curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/healthz   # 200
docker compose exec app python manage.py migrate --check          # 미적용 마이그레이션 여부
```

> **두 서비스 모두 `healthy`가 표시된다** (2026-09-17, Owner 승인 후 app healthcheck 추가). app은 `/healthz`를 10초 간격으로 호출하며 기동 유예 20초를 둔다.
>
> 다만 **app의 `healthy`는 "프로세스가 요청을 받는다"까지만 뜻한다** — `/healthz`는 DB를 건드리지 않는 liveness 프로브이므로 **DB가 죽어도 healthy가 유지된다**(§4-2). DB까지 포함한 판정은 여전히 `/healthz/db`(갭 7)가 필요하다.

## 7. 재실행

§3의 여정은 **[`scripts/smoke-journey.sh`](../scripts/smoke-journey.sh)로 커밋돼 있다.**

```bash
SMOKE_ADMIN_PASSWORD='<createsuperuser로 만든 비밀번호>' bash scripts/smoke-journey.sh
```

관리자 비밀번호는 환경변수로 받는다 — 자격증명을 저장소에 두지 않기 위해서다(§10). 관리자 계정은 §2-2로 미리 만들어져 있어야 한다.

실행할 때마다 **새 계정을 만들므로 반복 실행이 가능하다**(계정 이메일에 실행 시각 접미사를 붙인다). 다만 `db` 로그에는 과거 실행에서 남은 중복키 `ERROR`가 보일 수 있는데, 이는 API가 409로 올바르게 막은 흔적이다.

자동 테스트와의 역할 분담:

| | 자동 테스트 (291개) | 스모크 테스트 (이 문서) |
| --- | --- | --- |
| DB | 테스트 전용(매번 생성·삭제) | **실제 볼륨** |
| 범위 | 함수·엔드포인트 단위 + 교차 검증 | 컨테이너 기동부터 사용자 여정까지 |
| 답하는 질문 | "코드가 의도대로 동작하는가" | **"시스템이 맨바닥에서 일어서는가"** |
| 실행 | `uv run python manage.py test` | 이 문서의 절차 |

둘은 대체 관계가 아니다. **그리고 둘 다 통과해도 `gunicorn` 경로와 Google OAuth는 여전히 미검증이다.** SPEC-003에서 알림 `target_url` 5종이 전부 옳았지만 **아무도 눌러본 적이 없어** 옳다는 사실 자체가 미확인이었던 것처럼, 자동 테스트가 초록이어도 "실제로 일어서는가"는 별개의 질문이다.
