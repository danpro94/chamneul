# ADR-002. Session 인증 정책

## Status

Accepted

## Date

2026-06-22

## Supersedes

ADR-001 Decision 4의 "JWT 기반 토큰 인증" 잠정안 — 본 ADR로 대체.

## Context

ADR-001에서 인증 전략을 "Session(SSR) 기반"으로 확정하면서 세션 정책의 세부(쿠키 속성, 만료, 갱신, 로그아웃 시맨틱, OAuth 통합)를 별도 ADR로 분리하기로 했다. 본 ADR이 그 분리 문서이다.

본 결정은 다음 흐름에서 일관되게 적용되어야 한다.

- 이메일/비밀번호 회원가입 후 자동 로그인 (Q13 결정)
- 이메일/비밀번호 로그인
- Google OAuth 콜백을 통한 로그인
- 로그아웃
- 인증이 필요한 모든 API 호출

---

## Decision

### 1. 단일 세션 모델

이메일 로그인, 가입 직후 자동 로그인, Google OAuth 콜백 — 어느 경로로 인증되어도 **하나의 동일한 세션 레코드**(`django.contrib.sessions` 기반)를 발급한다. 별도의 OAuth 토큰을 클라이언트에 노출하지 않는다.

### 2. 쿠키 속성

| 속성 | 값 |
| --- | --- |
| Name | `sessionid` (Django 기본) |
| HttpOnly | `true` (필수) |
| Secure | `true` (운영) / 로컬 개발 환경에서만 `false` 허용 — `.env`로 분리 |
| SameSite | `Lax` |
| Path | `/` |
| Domain | 발급 환경의 도메인 (로컬은 미지정으로 호스트만) |

### 3. 만료 (TTL)

* Hard expiry: **14일** (`SESSION_COOKIE_AGE = 1209600`)
* Sliding renewal: **요청마다 만료 갱신** (`SESSION_SAVE_EVERY_REQUEST = True`)
* 사용자가 14일 이상 무활동이면 자동 만료. 14일 내 활동이 있으면 매 요청마다 만료 시각이 14일 뒤로 갱신된다.

### 4. 로그아웃

`POST /api/v1/auth/logout`은 다음 두 가지를 모두 수행한다.

1. 서버 측 세션 레코드 삭제 (`request.session.flush()`).
2. 응답 헤더에 `Set-Cookie: sessionid=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax`를 포함하여 클라이언트 쿠키 즉시 만료.

클라이언트 단독 쿠키 삭제에 의존하지 않는다.

### 5. CSRF

* `django.middleware.csrf.CsrfViewMiddleware`를 활성화한다.
* 상태 변경 엔드포인트(POST/PATCH/DELETE)는 모두 CSRF 토큰을 요구한다.
* 클라이언트는 `csrftoken` 쿠키를 읽어 `X-CSRFToken` 헤더로 전송한다.
* `csrftoken` 쿠키는 HttpOnly가 아니다 (클라이언트가 읽어야 함). `Secure` + `SameSite=Lax`.

### 6. 세션 저장소

* Phase 2: Django 기본 DB 백엔드 (`django.contrib.sessions.backends.db`).
* Phase 3+ (트래픽 발생 시): Redis 백엔드 검토. 본 ADR과 별도 ADR로 결정.

### 7. Google OAuth 통합

* `GET /api/v1/auth/google/authorize` → Google 동의 화면으로 302.
* `GET /api/v1/auth/google/callback` → `state` 검증 → Google ID token 검증 → 사용자 조회/생성 → **동일한 세션 발급** → 프론트 진입 URL로 302.
* 동일 검증 이메일이 이미 자체 가입 계정으로 존재할 경우, 동일 사용자에 OAuth 식별자만 추가로 연결한다 (계정 분리하지 않는다).

### 8. 비밀번호 저장

* Django 기본 PBKDF2 해셔 사용. 평문/가역 암호화 저장 금지.

### 9. 가입 직후 자동 로그인

* `POST /api/v1/auth/signup` 응답에서 곧바로 `Set-Cookie: sessionid=...`를 발급한다.
* Response body는 user 정보를 반환하고, 토큰 필드는 포함하지 않는다.

---

## Rationale (Why)

* **단순성**: 한 종류의 자격증명만 관리한다 — 디버깅, 로그 분석, 보안 검토 모두 단순해진다.
* **신뢰성**: 사용자 개인의 의사결정 고민 = 민감 정보. HttpOnly 쿠키는 XSS로 인한 자격증명 탈취 표면을 줄인다.
* **확장 경로**: DB 세션 → Redis 세션은 Django 설정 변경만으로 가능. JWT 대비 운영 부담이 낮은 단계.
* **OAuth 통합**: 세션 통합 모델로 사용자 1명 = 세션 1개를 유지. 토큰/쿠키 혼재로 인한 race condition을 차단.

## Trade-offs

* 무상태(stateless) 확장에는 불리. 하지만 Phase 2 트래픽 가정에서는 비-이슈.
* 모바일 네이티브 클라이언트는 쿠키 처리가 필요. Phase 2에서는 웹만 다루므로 비-이슈.

## Consequences

* `settings.py`에 다음 항목이 명시되어야 한다.
  ```python
  SESSION_COOKIE_AGE = 14 * 24 * 60 * 60
  SESSION_COOKIE_HTTPONLY = True
  SESSION_COOKIE_SECURE = True   # 로컬에서는 .env로 False
  SESSION_COOKIE_SAMESITE = "Lax"
  SESSION_SAVE_EVERY_REQUEST = True
  CSRF_COOKIE_SECURE = True
  CSRF_COOKIE_SAMESITE = "Lax"
  ```
* JWT/DRF Token/Knox 관련 패키지 추가는 금지. 새 ADR로 명시 결정해야만 변경 가능.
* `POST /api/v1/auth/refresh` 는 명세에서 제외된다.

## Validation

* `docker compose up -d` 후 가입 → 응답 헤더에 `Set-Cookie: sessionid=...` 존재 확인.
* 인증이 필요한 API를 같은 쿠키로 호출 → 200.
* 14일 대기 시뮬레이션은 단위 테스트에서 `time.sleep` 대신 `SESSION_COOKIE_AGE` 모킹으로 검증.
* 로그아웃 → 응답 헤더에 `Set-Cookie: sessionid=; Max-Age=0` 확인 + 동일 쿠키 재사용 시 401.

## Review Triggers

* 트래픽이 다중 인스턴스를 요구하기 시작할 때 → Redis 세션 ADR.
* 모바일 네이티브 클라이언트가 추가될 때 → 토큰 인증 추가 ADR.
* 동시 로그인 세션 제한이 요구사항이 될 때 → 사용자별 세션 인덱스 ADR.
