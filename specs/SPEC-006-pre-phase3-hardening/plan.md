# SPEC-006 — plan

> §7 결정이 권고안대로 승인된다는 전제의 설계다. 다른 안이 선택되면 해당 절만 바꾼다.

## 1. 파일 계획

| 파일 | 작업 | TASK |
| --- | --- | --- |
| `common/throttling.py` (**신규**) | 스로틀 클래스 — IP 기준·이메일 기준, 한도를 **호출 시점에** 읽는다 | 001 |
| `accounts/views.py` (수정) | #2·#3·#45·#46에 `throttle_classes` | 001 |
| `config/settings/base.py` (수정) | `CACHES`(DatabaseCache), 스로틀 한도 표, `NUM_PROXIES` | 001 |
| `config/settings/test.py` (수정) | 제한 테스트 밖에서는 한도를 크게 | 001 |
| `config/health.py` (수정) | `readyz` 추가 + 헬스 경로를 먼저 받는 미들웨어 | 002 |
| `config/urls.py` (수정) | `/readyz` | 002 |
| `config/settings/prod.py` (수정) | 콘솔 메일·http 재설정 URL 거부, WhiteNoise·정적파일, `SECURE_REDIRECT_EXEMPT` 대체(미들웨어) | 003 |
| `config/wsgi.py`·`config/asgi.py` (수정) | 기본값 → prod (결정 4) | 003 |
| `pyproject.toml`·`uv.lock` (수정) | `whitenoise` (결정 3, §16) | 003 |
| `scripts/smoke-journey.sh` (수정) | 13~15단계 | 004 |
| `docs/api.md`·`docs/smoke-test.md`·STATUS·리뷰 노트 09 | 문서 | 005 |
| `docs/adr/ADR-010-readiness-endpoint.md` (**신규**) | CLAUDE.md §5·§7 supersede | 002 전 |

**마이그레이션 없음.** 캐시 테이블은 `createcachetable`이 만든다(Django가 마이그레이션 밖에서 관리하는 테이블). `makemigrations --check`가 `No changes`여야 한다.

**Dockerfile·docker-compose는 고치지 않는다**(소유권 정책). 배포 절차에 필요한 한 줄(`createcachetable`)은 smoke-test 문서에 적고, Phase 3의 k8s 마이그레이션 Job에는 Owner가 넣는다.

## 2. 요청 횟수 제한 설계 (TASK-001) — 구현 완료 2026-11-04

```text
common/throttling.py
  pseudonymize(value)         # HMAC-SHA256(SECRET_KEY) — 이메일·IP 모두 이 값으로만 키를 만든다
  _RateFromSettings           # get_rate()가 settings에서 매번 읽는다 (DRF의 import 시점 고정 회피)
  IPRateThrottle              # 키 = pseudonymize(DRF get_ident) — NUM_PROXIES 반영
  EmailRateThrottle           # 키 = pseudonymize(canonical_email(request.data["email"]))
                              # 본문이 객체가 아니거나 주소가 문자열이 아니면 None → 이 스로틀은 건너뛰고
                              # (IP 기준이 막는다) 400은 시리얼라이저가 낸다
  LoginIPThrottle 등 6개      # DRF는 스로틀을 인자 없이 만든다 → 스코프마다 클래스 하나
```

**계획 대비 구현에서 강화한 4가지** (Owner 결정 범위 안의 구현 세부):

| 계획 | 구현 | 이유 |
| --- | --- | --- |
| 이메일 키 = `sha256` | **HMAC-SHA256**(SECRET_KEY), IP 키도 같은 방식 | 그냥 sha256은 후보 주소를 해시해 보면 되돌릴 수 있다(이메일은 추측 가능한 값). IP도 개인정보로 취급하고, 조작된 긴 XFF 값도 고정 길이 키가 된다 |
| `CACHES` 기본 옵션 | **`MAX_ENTRIES` 100,000** | DatabaseCache 기본 300개를 넘으면 **키 순서로 1/3을 지운다**. 누구나 키를 늘릴 수 있으므로(시도한 주소마다 1개) 공격자가 남의 카운터를 지우는 우회가 된다 |
| 429 본문 = DRF 기본 | **고정 한국어 문구**(기다릴 초는 `Retry-After`에만) | DRF 문구에는 초가 들어가 두 #45 요청의 본문이 1초 차이로 달라질 수 있다 |
| — | 스로틀 안에서 `request.data`를 **지역변수에 담지 않는다** | 스로틀은 뷰의 `sensitive_variables()` 밖에서 돈다. 여기서 터지면 운영 오류 리포트에 그 프레임의 지역변수가 찍힌다 — 본문을 담아 두면 비밀번호까지(변이 M14가 실제로 잡았다) |
| DRF 기본(스로틀 전부 평가) | **첫 거절에서 멈춘다** `StopAtFirstLimit` (2026-11-07 후속) | DRF는 거절 뒤에도 나머지 스로틀을 평가·기록한다 → IP 한도에 막힌 요청도 주소 행을 만들어 한 IP가 컬링을 일으킬 수 있었다. IP 스로틀을 먼저 둔다 |

| 뷰 | 스로틀 |
| --- | --- |
| `LoginView` (#3) | IP `auth_login_ip` + 이메일 `auth_login_email` |
| `SignupView` (#2) | IP `auth_signup_ip` |
| `PasswordResetView` (#45) | IP `password_reset_ip` + 이메일 `password_reset_email` |
| `PasswordResetConfirmView` (#46) | IP `password_reset_confirm_ip` |

**왜 이메일 키를 해시하나**: `DatabaseCache`는 키를 DB 테이블에 쓴다. 원문 주소를 키로 쓰면 "누가 재설정을 시도했는가"가 캐시 테이블에 개인정보로 남는다. 위 표대로 해시는 HMAC이다.

**왜 스로틀이 뷰보다 먼저인가**: DRF는 `initial()`에서 인증·권한·스로틀을 본 뒤 핸들러를 부른다. 그래서 #45의 429는 **계정 조회 이전**에 결정된다 — 가입 여부가 429에 섞일 길이 구조적으로 없다.

**`NUM_PROXIES`**: `REST_FRAMEWORK["NUM_PROXIES"] = int(os.environ.get("DRF_NUM_PROXIES", "0"))`. 0이면 XFF를 아예 보지 않는다.

**캐시**:
```python
CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "django_cache"}}
```

## 3. 헬스 엔드포인트 설계 (TASK-002)

```text
config/health.py
  healthz(request)  → 200 {"status": "ok"}                      # 변경 없음, DB 안 봄
  readyz(request)   → connection.ensure_connection() + SELECT 1
                      성공 200 {"status":"ok","checks":{"database":"ok"}}
                      실패 503 {"status":"unavailable","checks":{"database":"unavailable"}}  # 예외 문자열 미노출
  HealthCheckMiddleware   # MIDDLEWARE 맨 앞. request.path가 정확히 "/healthz" 또는 "/readyz"인 GET/HEAD만 직접 응답
```

**미들웨어가 왜 필요한가**: kubelet과 ALB는 `http://<파드IP>:8000/healthz`로 묻는다. Django 기본 흐름이면 ① `SecurityMiddleware`가 `SECURE_SSL_REDIRECT`로 **301**을 돌려주고(ALB 헬스체크는 기본 200만 성공) ② `CommonMiddleware`가 `ALLOWED_HOSTS`에 없는 파드 IP를 **400**(DisallowedHost)으로 막는다. 두 검사보다 앞에서, 데이터가 없는 두 경로만 받는다.

DB 체크는 짧게 끝나야 한다 — 연결 시도가 길어지면 probe 타임아웃이 먼저 온다. `connect_timeout`은 Phase 3 probe 설정(`timeoutSeconds`)과 함께 정한다(기록만). → **2026-11-16 3초로 앞당김**(Owner 승인, TASK-005 devops 리뷰 M-2 — ADR-010 후속).

## 4. 운영 경로 설계 (TASK-003)

`config/settings/prod.py`에 추가:
```python
if EMAIL_BACKEND.endswith("console.EmailBackend"):  raise ImproperlyConfigured(...)   # S-3
if not PASSWORD_RESET_URL.startswith("https://"):     raise ImproperlyConfigured(...)   # S-6
MIDDLEWARE.insert(<SecurityMiddleware 다음>, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES["staticfiles"] = CompressedManifestStaticFilesStorage
```

**실제 이미지로 1회 기동** — compose를 고치지 않는다:
```bash
docker build -t chamneul:prodcheck .
docker run --rm -d --name chamneul-prodcheck --network <compose 네트워크> --env-file .env \
  -e DJANGO_SETTINGS_MODULE=config.settings.prod -e DB_HOST=db -e DB_PORT=5432 \
  -e DJANGO_SECRET_KEY=<일회용> -e DJANGO_ALLOWED_HOSTS=localhost \
  -e PASSWORD_RESET_URL=https://chamneul.com/reset-password -e EMAIL_BACKEND=... \
  -p 18000:8000 chamneul:prodcheck
```
확인: `curl -H "Host: 10.0.0.7" http://localhost:18000/healthz` → 200 / `/readyz` → 200 / Admin CSS → 200 / `X-Forwarded-Proto: https`로 `/api/v1/csrf` → 200 / 일반 http 요청 → 301 / `manage.py check --deploy` 출력 기록.

**계획 대비 구현에서 바꾼 3가지** (2026-11-07, 결정 3·4 범위 안의 구현 세부 — 리뷰 노트 09 §3-2):

| 계획 | 구현 | 이유 |
| --- | --- | --- |
| WhiteNoise 미들웨어·저장소를 **prod.py**에 | **base.py**에 | Dockerfile의 빌드 때 `collectstatic`은 `manage.py` 기본값(local)으로 돈다. prod에만 두면 이미지에 매니페스트가 없어 prod에서 Admin·DRF 화면이 500 — 반대 사례 이미지로 실측했다(헬스체크는 200이라 배포가 "성공"한다) |
| `docker run -e EMAIL_BACKEND=...` | prod.py가 **`DJANGO_EMAIL_BACKEND`**를 읽는다(기본 SMTP) | 종전 prod는 메일 백엔드를 어디서도 읽지 않아 "콘솔 금지" 가드가 걸릴 입력이 없었다. 이름은 다른 Django 핵심 설정(`DJANGO_SECRET_KEY` 등)과 같은 접두사 |
| 콘솔만 거부 | 콘솔 + **filebased** 거부 | 둘 다 재설정 링크를 서버에 남긴다(로그 / 디스크) |

## 5. 스모크 재통과 (TASK-004)

1. `pg_dump` 백업 → **저장소 밖**(`~/chamneul-backups/`)
2. `docker compose down -v` → `up -d` → `migrate` → `createcachetable` → 관리자 부트스트랩(smoke-test §2-2)
3. `scripts/smoke-journey.sh` 15단계 실행
4. `./.claude/mcp/setup-postgres-ro-role.sh`(읽기 전용 MCP 계정 재생성)

## 6. 검증

TASK마다 4종(`check` / `makemigrations --check` / `ruff` / `test`) + 변이 검증(방어 코드를 하나씩 지워 해당 테스트가 실패하는지). TASK-003·004는 실제 컨테이너 출력 첨부. 마무리에 `security-reviewer`·`devops-local-platform` 서브에이전트 리뷰.
