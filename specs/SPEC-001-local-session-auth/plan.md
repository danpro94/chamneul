# SPEC-001 — Technical Plan

> Gate 2. Owner 승인 후 구현에 들어간다.
> **아직 코드를 쓰지 않은 상태의 계획서다.** 구현 시 실제와 달라지면 이 문서를 고친다.

## 1. 변경되는 컴포넌트

### 신규 — 공통 계층 (나머지 38개 엔드포인트가 전부 재사용)

| 파일 | 역할 |
| --- | --- |
| `common/exceptions.py` | DRF custom exception handler → api.md §1.5 에러 봉투(`{"error":{"code","message","details"}}`)로 변환 |
| `common/permissions.py` | `IsAuthenticatedUser` · `IsActiveAdvisor` · `IsAdmin`. **401/403 판정이 여기 있다** (부채 ④) |
| `common/pagination.py` | api.md §1.6 `page_info` 형태 고정. SPEC-001은 목록이 없지만 SPEC-003부터 필요 |
| `config/api_urls.py` | `/api/v1/` 하위 라우팅 |

### 신규 — accounts API 계층

| 파일 | 역할 |
| --- | --- |
| `accounts/serializers.py` | `SignupSerializer` · `LoginSerializer` · `MeSerializer` — 액션별로 분리 (CLAUDE.md §8) |
| `accounts/services.py` | `signup()` · `login()` · `logout()` — **`transaction.atomic`이 여기 있다** (부채 ⑤) |
| `accounts/views.py` | `SignupView` · `LoginView` · `LogoutView` · `MeView` (APIView) |
| `accounts/urls.py` | auth + users/me 라우팅 |

### 변경

| 파일 | 변경 |
| --- | --- |
| `config/urls.py` | `path("api/v1/", include("config.api_urls"))` 한 줄 추가. 현재 10줄 |
| `config/settings/base.py` | `REST_FRAMEWORK`에 `EXCEPTION_HANDLER` 추가 |

### 신규 — 테스트 하네스

```
tests/__init__.py
tests/base.py                        ApiTestCase + CSRF 클라이언트 헬퍼
tests/factories.py                   make_user() — factory_boy 미사용(§16)
tests/unit/__init__.py
tests/unit/test_permissions.py       AC-011 (부채 ④) — 엔드포인트 없이 권한 클래스만
tests/integration/__init__.py
tests/integration/test_auth.py       AC-002~AC-010, AC-013, AC-014
tests/integration/test_signup_atomicity.py   AC-012 (부채 ⑤)
```

**최상위 `tests/`인 이유**: API 테스트는 본질적으로 앱을 가로지른다(고민 테스트 하나에 User + UserRole + Concern이 필요). 그리고 테스트는 Django 앱이 아니라 **`acceptance.md`의 AC에 매핑**된다.

### ViewSet이 아니라 APIView인 이유

CLAUDE.md §4는 단순 CRUD에 ModelViewSet을 허용하고, 비즈니스 로직이 복잡해지면 명시적 Serializer + APIView + 서비스 레이어로 리팩터링하라고 한다. 인증은 **처음부터** 후자다 — signup/login/logout은 CRUD가 아니고 각각 부수효과(세션 생성·삭제)를 가진다. ViewSet으로 시작했다가 곧바로 리팩터링하는 것보다 처음부터 APIView가 맞다.

## 2. 데이터 흐름

```
Browser
  │ POST /api/v1/auth/login  (Cookie: csrftoken, Header: X-CSRFToken)
  ▼
gunicorn / runserver
  ▼
Django 미들웨어
  ├─ SecurityMiddleware
  ├─ SessionMiddleware        ← 세션 로드 (DB backend)
  ├─ CsrfViewMiddleware       ← X-CSRFToken 검증
  └─ AuthenticationMiddleware ← request.user 결정
  ▼
DRF APIView
  ├─ SessionAuthentication    ← 인증 (실패 = 401)
  └─ permission_classes       ← 인가 (실패 = 403)   ← 부채 ④
  ▼
Serializer (입력 검증 — 실패 = 400/422)
  ▼
Service (transaction.atomic)                        ← 부채 ⑤
  ▼
ORM → psycopg → PostgreSQL
  ▼
Response + Set-Cookie: sessionid
```

**커넥션은 어디서 열리고 닫히는가**: Django가 요청 시작 시 커넥션을 얻고 응답 후 반환한다. `CONN_MAX_AGE=60`(기본)이므로 60초 동안 재사용된다. 세션 백엔드가 DB이므로 **인증 요청 하나마다 세션 조회 쿼리가 최소 1회** 발생한다. `SESSION_SAVE_EVERY_REQUEST=True`(슬라이딩 갱신)라서 **쓰기도 매 요청 발생**한다 — 트래픽이 늘면 첫 번째 병목 후보다.

## 3. DB 변경

**없음.**

`django.contrib.sessions`가 이미 `INSTALLED_APPS`에 있고 `django_session` 테이블은 마이그레이션되어 있다. `accounts.User`·`UserRole`도 그대로 쓴다.

`makemigrations --check --dry-run`이 **"No changes"**를 유지해야 한다. 변화가 나오면 모델을 건드린 것이므로 되돌린다.

## 4. API 변경

| api.md | 변경 |
| --- | --- |
| #1 `/healthz` | 없음. 테스트만 추가 |
| #2 #3 #4 #7 | 명세대로 신규 구현 |
| §1.2 인증 | **OQ-1 결정 반영 필요** — CSRF 부트스트랩 경로 명시 |

**신규 엔드포인트 0개** (OQ-1에서 A안을 택할 경우). 43개가 43개로 유지되므로 §16 MVP 범위 게이트를 건드리지 않는다.

## 5. 기존 결정과의 충돌

| 조항 | 충돌 | 처리 |
| --- | --- | --- |
| ADR-002 세션 정책 | 없음 | 그대로 구현 |
| CLAUDE.md §4 세션 단일 전략 | 없음 | JWT·Token 미도입 |
| CLAUDE.md §6.6 소프트 삭제 | 해당 없음 | `User`는 소프트 삭제가 아니라 `is_active`를 쓴다 |
| CLAUDE.md §16 서드파티 | **없음 — 신규 패키지 0개** | Django `contrib.auth`·`contrib.sessions` + DRF만 |
| Owner 결정 G5 (pytest 미도입) | 없음 | Django 기본 러너 + `APITestCase` |
| UX C-8 CSRF | **미해결** | OQ-1 — Owner 결정 필요 |

## 6. 되돌리기

**조건**: 세션 인증이 SPA 프론트와 맞지 않는 것으로 판명될 때 (CORS·서드파티 쿠키 문제).

**방법**: 이 SPEC은 순수 추가다 — 기존 파일 변경은 `config/urls.py` 한 줄과 settings 한 줄뿐이다. 브랜치를 되돌리면 원상복구된다. **DB 스키마 변경이 없으므로 마이그레이션 롤백이 필요 없다.**

단, 인증 전략 자체를 바꾸는 것은 ADR-002를 supersede하는 새 ADR이 필요하다. 코드만 되돌리는 것으로는 부족하다.
