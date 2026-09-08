---
spec: SPEC-001
title: 로컬 세션 인증 + CSRF 부트스트랩 + 테스트 하네스
prd: docs/2 mvp-scope_v1.md
endpoints: [1, 2, 3, 4, 7]
routing: 위임
adr: [ADR-001, ADR-002, ADR-005]
status: draft
---

# SPEC-001: 로컬 세션 인증 + CSRF 부트스트랩 + 테스트 하네스

## 1. Intent

이메일·비밀번호로 가입하고 로그인해 **세션 쿠키를 발급받고**, 그 세션으로 본인 정보를 조회하고, 로그아웃하면 **서버 세션이 실제로 삭제되는** 것까지를 구현한다.

동시에 이 프로젝트의 **첫 API 계층**과 **첫 테스트 하네스**를 세운다. 지금 `config/urls.py`는 10줄이고 `/api/v1/` 프리픽스 자체가 없으며, 테스트는 0건이고 테스트 러너가 한 번도 실행된 적이 없다.

### 왜 이것이 첫 SPEC인가

1. **나머지 38개 엔드포인트 전부의 전제조건이다.** 라우터·에러 봉투·페이지네이션·권한 클래스가 여기서 처음 선다.
2. **판정 장치를 여기서 세운다.** 엔드포인트 5개짜리 SPEC에서 하네스를 부트스트랩하는 것이, 나중에 큰 SPEC에서 미지수 두 개를 동시에 디버깅하는 것보다 안전하다.
3. **M4를 막고 있는 학습 부채 ④·⑤를 실물로 해소한다.** 부채 ④(401/403/409)는 권한 클래스 그 자체이고, 부채 ⑤(atomic)는 가입 트랜잭션 그 자체다. M2 퀴즈 42/100에서 ④는 2회 연속 오답이었고 "M4 착수 전 재퀴즈 필수"로 기록되어 있다. **별도 재퀴즈 이벤트를 잡는 대신 이 SPEC의 테스트가 두 항목을 실행 가능한 형태로 고정한다.**
4. **DRF 설정이 M1 이후 한 번도 검증된 적 없다.** `config/settings/base.py:138-147`에 `SessionAuthentication`·`IsAuthenticated`·`PageNumberPagination`이 설정되어 있으나 소비하는 코드가 한 줄도 없다. 이 SPEC이 그 설정이 실제로 맞는지 처음 확인한다.

## 2. Preconditions

* PostgreSQL 16이 Docker Compose로 기동 중이고 마이그레이션 6개가 적용되어 있다.
* `accounts.User`가 존재한다 — `USERNAME_FIELD="email"`, `nickname` unique(2~20자), `active_role`, UUIDv7 PK.
* `accounts.UserRole`이 존재한다. **`USER`는 row로 저장하지 않는다** (암묵적 기본 역할).
* DRF가 설치·설정되어 있다.

## 3. Functional Behavior

### 시나리오 1 — 회원가입 (api.md #2)

**GIVEN** 비로그인 상태이고 `csrftoken` 쿠키를 보유하고 있다
**WHEN** `POST /api/v1/auth/signup`에 `email` · `password` · `nickname`을 보낸다
**THEN** `201`과 `user_id` · `email` · `nickname` · `active_role`("USER") · `created_at`을 받는다
**AND** `Set-Cookie: sessionid=...; HttpOnly; Secure; SameSite=Lax`가 함께 온다 — **가입 즉시 로그인된다** (Owner 결정 Q13)
**AND** 비밀번호는 PBKDF2로 해시되어 저장된다

### 시나리오 2 — 중복 가입 (api.md #2)

**GIVEN** `a@example.com`으로 이미 가입된 사용자가 있다
**WHEN** 같은 이메일로 가입을 시도한다
**THEN** `409`와 `error.code = "DUPLICATE_EMAIL"`을 받는다
**AND** 새 `User` row가 생기지 않는다

닉네임 중복도 같다 (`DUPLICATE_NICKNAME`).

### 시나리오 3 — 가입 실패 시 부분 커밋 없음 (학습 부채 ⑤)

**GIVEN** 가입 처리 중간에 예외가 발생한다
**WHEN** 트랜잭션이 롤백된다
**THEN** `User` row도 세션도 **아무것도 남지 않는다**

### 시나리오 4 — 로그인 (api.md #3)

**GIVEN** 가입된 활성 사용자가 있다
**WHEN** `POST /api/v1/auth/login`에 올바른 `email` · `password`를 보낸다
**THEN** `200`과 `user` 객체를 받고 세션 쿠키가 발급된다

**WHEN** 비밀번호가 틀리면 → `401` (`INVALID_CREDENTIALS`)
**AND** 존재하지 않는 이메일도 **같은 401·같은 메시지**다 — 계정 존재 여부를 노출하지 않는다
**WHEN** `is_active=False` 계정이면 → `403` (`ACCOUNT_DISABLED`)

### 시나리오 5 — 로그아웃 (api.md #4)

**GIVEN** 로그인된 세션이 있다
**WHEN** `POST /api/v1/auth/logout`을 보낸다
**THEN** `200`을 받는다
**AND** **서버의 세션 레코드가 실제로 삭제된다** — 클라이언트 쿠키 삭제에만 의존하지 않는다 (§10)
**AND** `Set-Cookie: sessionid=; Max-Age=0`이 온다
**AND** 같은 쿠키로 재요청하면 `401`이다

**WHEN** 비로그인 상태로 로그아웃하면 → `401`

### 시나리오 6 — 내 정보 조회 (api.md #7)

**GIVEN** 로그인된 세션이 있다
**WHEN** `GET /api/v1/users/me`를 보낸다
**THEN** `200`과 `user_id` · `email` · `nickname` · `active_role` · `roles[]` · `created_at`을 받는다
**AND** `password` · `is_staff` · `is_superuser`는 **응답에 없다**

**WHEN** 비로그인이면 → `401` (**404가 아니다** — 라우트는 존재한다)

### 시나리오 7 — 역할 보유 ≠ 활성 역할 (학습 부채 ④)

**GIVEN** ADVISOR 역할을 **보유**했으나 `active_role`이 `USER`인 사용자가 로그인해 있다
**WHEN** 조언가 전용 리소스에 접근한다
**THEN** **`403`이다. `401`이 아니다** — 인증은 성공했고 권한만 없다

> SPEC-001 시점에는 조언가 리소스가 아직 없다. 이 시나리오는 **권한 클래스 단위 테스트**로 검증하고, 엔드포인트 통합 테스트는 SPEC-006에서 채운다.

### 시나리오 8 — CSRF 부트스트랩 (UX C-8)

**GIVEN** 쿠키를 하나도 갖고 있지 않은 최초 방문자다
**WHEN** 가입·로그인 전에 `csrftoken` 쿠키를 발급받아야 한다
**THEN** 정해진 경로로 발급받을 수 있다 (§11 OQ-1에서 방식 확정)

**미해결 시 회원가입 자체가 불가능하다.** 상태 변경 요청은 CSRF 토큰을 요구하는데(api.md §1.2) 최초 방문자는 토큰을 얻을 경로가 없다.

## 4. Inputs

### `POST /api/v1/auth/signup`

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `email` | string | ✓ | 이메일 형식. 소문자 정규화 후 unique |
| `password` | string | ✓ | 최소 8자 |
| `nickname` | string | ✓ | 2~20자. unique |

### `POST /api/v1/auth/login`

| 필드 | 타입 | 필수 |
| --- | --- | --- |
| `email` | string | ✓ |
| `password` | string | ✓ |

`POST /api/v1/auth/logout` · `GET /api/v1/users/me` — body 없음.

## 5. Outputs

| 엔드포인트 | 응답 필드 |
| --- | --- |
| `#2` signup | `user_id` `email` `nickname` `active_role` `created_at` |
| `#3` login | `user`: { `user_id` `email` `nickname` `active_role` } |
| `#4` logout | `{"message": "로그아웃 되었습니다."}` |
| `#7` users/me | `user_id` `email` `nickname` `active_role` `roles[]` `created_at` |

**응답에 절대 포함하지 않는 것**: `password` · `is_staff` · `is_superuser` · `is_active` · `intended_lane` · `advisor_type`(Owner 결정 Q15).

> 테스트는 `assertIn`이 아니라 **키 집합 전체 비교**로 검증한다. 초과 노출을 잡기 위해서다 (TEST_CRITERIA §5).

## 6. Error Behavior

에러 봉투는 api.md §1.5 형식이다.

```json
{"error": {"code": "INVALID_FIELD", "message": "사람이 읽을 수 있는 한국어 메시지", "details": {"field": "email"}}}
```

| 조건 | 상태 | `error.code` |
| --- | --- | --- |
| 필수 필드 누락 / 형식 오류 | 400 | `INVALID_FIELD` |
| 비밀번호 8자 미만, 닉네임 길이 위반 | 422 | `VALIDATION_FAILED` |
| 이메일 중복 | 409 | `DUPLICATE_EMAIL` |
| 닉네임 중복 | 409 | `DUPLICATE_NICKNAME` |
| 자격 증명 불일치 (**존재하지 않는 이메일 포함**) | 401 | `INVALID_CREDENTIALS` |
| 비로그인 상태로 인증 필요 엔드포인트 | 401 | `AUTHENTICATION_REQUIRED` |
| 비활성 계정 로그인 | 403 | `ACCOUNT_DISABLED` |
| 인증됨 + 권한 없음 | 403 | `PERMISSION_DENIED` |
| CSRF 토큰 누락·불일치 | 403 | `CSRF_FAILED` |

## 7. Invariants

1. **비밀번호는 어떤 응답·로그에도 나타나지 않는다.** 평문·가역 암호화 저장 금지.
2. **로그아웃 후 그 세션 키로는 어떤 인증 요청도 성공하지 않는다.**
3. **가입은 원자적이다.** 사용자와 세션이 함께 성공하거나 함께 실패한다.
4. **401과 403을 혼동하지 않는다.** 인증 없음 = 401, 인증됨+권한없음 = 403.
5. **로그인 실패 응답은 계정 존재 여부를 드러내지 않는다.**

## 8. Security Requirements

`ADR-002` + `.claude/rules/30-security.md`.

* 세션 쿠키: `sessionid`, **HttpOnly + Secure + SameSite=Lax**, 14일, 슬라이딩 갱신(`SESSION_SAVE_EVERY_REQUEST=True`). `Secure`는 localhost 외 전 환경 필수 (`config/settings/local.py`가 로컬에서만 해제).
* 비밀번호: Django 기본 **PBKDF2**, 프로젝트 기본 iteration.
* **CSRF는 모든 상태 변경 엔드포인트에서 켠다.** 클라이언트는 `csrftoken` 쿠키를 읽어 `X-CSRFToken` 헤더로 보낸다.
* 로그아웃은 **서버 세션 레코드를 삭제**한다.
* 인증 실패 로그에 비밀번호·세션 ID를 남기지 않는다.

## 9. Acceptance Criteria

`acceptance.md`에 체크박스와 테스트 경로가 있다.

* **AC-001** `tests/` 하네스가 PostgreSQL 테스트 DB에 붙어 실행되고, 최소 1개 테스트가 통과한다
* **AC-002** 비로그인 `GET /api/v1/users/me` → **401** (404가 아님)
* **AC-003** 가입 → 201 + `Set-Cookie: sessionid` + 응답 키 집합이 §5와 정확히 일치
* **AC-004** 이메일 중복 가입 → 409, `User` row가 늘지 않음
* **AC-005** 닉네임 중복 가입 → 409
* **AC-006** 로그인 성공 → 200 + 세션 발급
* **AC-007** 잘못된 비밀번호 → 401 / 존재하지 않는 이메일 → **동일한 401·동일 메시지**
* **AC-008** 비활성 계정 로그인 → 403
* **AC-009** 로그아웃 → 200, **서버 세션 레코드 삭제 확인**, 같은 쿠키 재사용 시 401
* **AC-010** `users/me` 응답에 `password`·`is_staff`·`is_superuser` 부재
* **AC-011** ADVISOR 보유 + `active_role=USER` → 조언가 권한 클래스가 **403** 판정 (부채 ④)
* **AC-012** 가입 중간 실패 주입 시 `User` row가 남지 않음 (부채 ⑤)
* **AC-013** CSRF 토큰 없이 `POST /api/v1/auth/signup` → 403 (`enforce_csrf_checks=True` 클라이언트로 검증)
* **AC-014** 에러 응답이 전부 api.md §1.5 봉투 형식

## 10. Non-Goals

이번 SPEC에서 **하지 않는다.**

* **Google OAuth** (api.md #5·#6) → SPEC-002. HTTP 클라이언트 미설치 문제로 §16 게이트가 걸릴 수 있어 뒤로 뺐다. ADR-002상 모든 인증 경로가 같은 세션을 발급하므로 나머지가 기다릴 필요가 없다.
* **프로필 수정 · 역할 목록 · active-role 전환** (#8·#9·#10) → SPEC-003
* **브루트포스 방어 (IP·계정 rate limit)** → Phase 3. §10이 명시적으로 이월했다. **Phase 2에서 이것은 알려진 갭이다.**
* **비밀번호 재설정 · 이메일 인증** → Phase 3 (43개 범위 밖)
* **계정 탈퇴 · 정지 API** → Phase 3
* 조언가 전용 엔드포인트 자체 → SPEC-006 (여기서는 권한 클래스만)

## 11. Open Questions

| # | 질문 | 출처 | 상태 |
| --- | --- | --- | --- |
| **OQ-1** | **CSRF 부트스트랩 방식.** (A) 기존 GET에 `ensure_csrf_cookie` 적용 — 신규 엔드포인트 0개, 43개 유지 (B) 전용 `GET /api/v1/auth/csrf` 신설 — **§16 승인 게이트** | UX C-8 / §8-1 | **Owner 결정 필요 — 구현 차단** |
| OQ-2 | 로그인 실패 시 `details`에 필드를 넣을 것인가. 넣으면 계정 존재 여부가 새어나갈 수 있다 | 본 SPEC | 권고: **넣지 않는다** |
| OQ-3 | `users/me`의 `roles[]`에 암묵적 `USER`를 포함할 것인가. `UserRole` row로는 저장하지 않는다 | `accounts/models.py` | 권고: **포함한다** (클라이언트가 역할 스위처를 그리려면 필요) |

**권고 (OQ-1)**: (A)를 택한다. 엔드포인트 수가 43으로 유지되어 §16 게이트를 건드리지 않고, `docs/api.md` §3 요약표를 고칠 필요도 없다.

## 12. Definition of Done

- [ ] AC-001 ~ AC-014 전부 충족, 각 항목에 테스트 경로 기재
- [ ] `manage.py test --settings=config.settings.test` 전체 통과 (실측 출력 `evidence/`)
- [ ] `ruff check .` · `manage.py check` · `makemigrations --check --dry-run` 통과
- [ ] OQ-1 결정 반영 + `docs/api.md` §1.2 갱신
- [ ] `handoff.md` 작성 (Owner 선요약 먼저)
- [ ] `docs/00-project/LEARNING_DEBT.md` ④·⑤ 상태 갱신
- [ ] `docs/00-project/STATUS.md` 갱신 — 활성 SPEC을 SPEC-002로
