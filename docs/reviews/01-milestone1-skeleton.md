# Review 01 — Milestone 1: Runnable Django + PostgreSQL skeleton with custom User

> CLAUDE.md §14 리뷰 노트. 코드 세션마다 1건. 본 노트는 **임베디드 학습**(초급→고급 + DevOps 관점)을 포함한다.

| 항목 | 값 |
| --- | --- |
| 날짜 | 2026-06-29 |
| 범위 | 프로젝트 골격 + 설정 분리 + `common/uuid7` + `accounts.User` + `/healthz` + Docker Compose(app+postgres) |
| 선행 | CLAUDE.md, docs/model.md §7.1, ADR-002 |
| 다음 | Milestone 2 — `accounts`의 `UserRole`/`RoleGrant`/`GoogleIdentity` + createsuperuser→ADMIN UserRole 훅 |

---

## 1. 무엇이 바뀌었나 (changed files)

```
manage.py
config/__init__.py
config/settings/{__init__,base,local,test,prod}.py
config/{urls,health,wsgi,asgi}.py
common/{__init__,uuid7}.py
accounts/{__init__,apps,managers,models,admin}.py
accounts/migrations/{__init__,0001_initial}.py
Dockerfile  docker-compose.yml  .dockerignore
.env.example  .gitignore(보강)
pyproject.toml(django-environ→python-dotenv)  uv.lock
```

## 2. 왜 이렇게 했나 (key decisions)

* **`AUTH_USER_MODEL`을 첫 마이그레이션 전에 선언** — Django는 첫 migrate 이후 user 모델 교체를 사실상 허용하지 않는다(전체 DB 재생성 요구). 그래서 Milestone 1의 "검증 가능한 최소 단위"가 곧 커스텀 `User`까지 포함하는 이유다(model.md §7.1).
* **설정 4분할(base/local/test/prod)** — 12-factor. 공통은 base, 환경차만 override. 비밀/호스트는 환경변수로 주입하고(`§10`) dev 편의를 위해 `python-dotenv`가 `.env`를 로드. prod는 `SECRET_KEY`/`ALLOWED_HOSTS`가 없으면 **fail-fast**(raise)로 잘못된 배포를 차단.
* **UUIDv7 앱 레벨 생성** — `uuid_utils.uuid7()`(Rust)을 stdlib `uuid.UUID(bytes=...)`로 변환해 Django `UUIDField`가 기대하는 타입으로 맞춤. PG 확장(`pg_uuidv7`)은 관리형 RDS/Aurora에서 설치가 막히므로 앱 레벨이 환경 drift를 0으로 만든다(model.md §1.2).
* **`/healthz`는 DB 비의존** — "앱 프로세스가 살아있는가"만 답하는 liveness probe. DB 장애와 분리해야 오탐을 막는다. DB까지 보는 readiness(`/healthz/db`)는 의도된 후속.
* **python-dotenv 채택**(django-environ 대체) — MVP 수준에서 가볍고 직관적. 추후 `pydantic-settings` 전환 여지를 남김(Owner 결정 2026-06-29).

## 3. 어떻게 테스트했나 (verification — 실행 완료)

```bash
uv run python -c "from common.uuid7 import uuid7; print(uuid7().version)"   # 7
uv run python manage.py check                                              # 0 issues
uv run python manage.py makemigrations --check --dry-run                   # No changes
docker compose build
docker compose up -d                                                       # db healthy → app up
docker compose exec -T app uv run python manage.py migrate                 # accounts.0001 OK
curl -s -w '%{http_code}' http://localhost:8000/healthz                    # 200 {"status":"ok"}
docker compose exec -T -e DJANGO_SUPERUSER_PASSWORD=... app \
  uv run python manage.py createsuperuser --noinput --email a@b.local --nickname admin
# → User.id.version == 7, is_staff/is_superuser True, password PBKDF2 해시
```

정리: `docker compose down`(컨테이너 정지) / `docker compose down -v`(PG 볼륨까지 삭제 = DB 초기화).

## 4. DevOps 설명 포인트 (요청: 초급→고급 관점)

* **레이어 캐시(초급)** — Dockerfile에서 `pyproject.toml uv.lock`만 먼저 COPY → `uv sync` → 그다음 `COPY . .`. 소스만 바뀌면 의존성 레이어는 재실행되지 않는다. "잘 안 바뀌는 것 위, 자주 바뀌는 것 아래" 원칙.
* **compose 서비스명 = DNS(중급)** — app 컨테이너의 `DB_HOST=db`가 동작하는 이유는 compose가 만든 사용자 네트워크에서 서비스명이 호스트명이 되기 때문. 호스트에서 직접 돌릴 땐 `localhost:15432`(포트 매핑), 컨테이너 안에선 `db:5432`. base.py 기본값(localhost)을 compose가 override한다.
* **`depends_on` + `healthcheck`(중급)** — `depends_on`만으로는 "db 프로세스 시작"만 보장. `condition: service_healthy` + `pg_isready` healthcheck가 있어야 "접속 준비 완료"까지 대기. 이게 없으면 app이 db보다 먼저 떠서 첫 쿼리가 깨질 수 있다.
* **venv 셰도잉 함정(고급)** — `volumes: - .:/app`로 소스를 마운트하면 호스트의 `.venv`(macOS 빌드)가 컨테이너 `.venv`(linux 빌드)를 덮어써 바이너리가 깨진다. 익명 볼륨 `- /app/.venv`로 그 경로만 보호한다. `.dockerignore`에도 `.venv/`를 넣어 이미지 빌드 시 호스트 venv가 복사되지 않게 한다.
* **마이그레이션 = 스키마 단일 진실원천(고급)** — DB를 손으로 바꾸지 않고 모델→makemigrations→migrate만 사용. 마이그레이션 파일은 git에 커밋(.gitignore가 제외하지 않음). `makemigrations`/`check`는 DB 연결이 필요 없다(그래서 PG 없이도 CI 1차 검증 가능). 실제 적용(`migrate`)만 PG가 필요.

## 5. 보안 노트 (§10 / ADR-002)

* 비밀은 `.env`로만, `.env.example`만 커밋. `.gitignore`가 `.env`·`.env.*` 제외(`!.env.example` 예외).
* 세션 쿠키 baseline: `HttpOnly` + `SameSite=Lax` + `Secure`(기본 True), 14일 만료 + 매 요청 슬라이딩 갱신. local.py만 `Secure=False`(http localhost).
* 비밀번호는 Django 기본 PBKDF2(검증: 해시 prefix `pbkdf2_`).
* prod.py는 `SECRET_KEY`/`ALLOWED_HOSTS` 미설정 시 raise + `DEBUG=False` + HSTS/SSL redirect.
* **갭(문서화)**: 로그인 brute-force rate limiting은 Phase 3(§10). 실제 login/logout/OAuth 구현은 Milestone 3 예정 — 현재는 쿠키 정책 baseline만.

## 6. 다음 개선 (follow-ups)

1. `createsuperuser` → 첫 ADMIN `UserRole` row 자동 생성(ADR-003) — `UserRole` 모델이 생기는 Milestone 2에서.
2. 운영용 `gunicorn` CMD 분리(현재 runserver는 로컬 전용).
3. readiness probe `/healthz/db`(DB 의존) 검토.
4. ruff(lint/format) dev 의존성 도입 여부 — §16 패키지 추가 게이트로 Owner 확인 후.
5. Notion 원본 drift 해소(api.md §7 패치) — Owner 직접 작업.
