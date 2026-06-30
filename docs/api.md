# API Specification v1

본 문서는 `chamneul` Phase 2 v1의 공식 API 명세이다. Notion v0 export(41건)을 정합성 검토한 뒤, `토큰 재발급`을 제거하고 `/healthz` + 관리자 역할 부여/해제 2건을 추가하여 **총 43 엔드포인트**를 확정한다.

확정 결정의 출처:

* CLAUDE.md (2026-06-22 정합성 갱신본)
* ADR-001 (로컬 컨테이너 아키텍처)
* ADR-002 (Session 인증 정책)
* ADR-003 (ADMIN 역할 부여/해제)
* Owner 결정 Q1 ~ Q22 (2026-06-22 본 정합성 세션)

---

## 1. Common Rules

### 1.1 Base URL

* 로컬 개발: `http://localhost:8000`
* 모든 버전 관리 API의 prefix: `/api/v1/`
* 비-버전 엔드포인트: `/healthz` 뿐

### 1.2 인증 (Auth)

* Session-based (HttpOnly Cookie `sessionid`). 자세한 정책은 ADR-002.
* 인증이 필요한 모든 요청은 `Cookie: sessionid=...` 헤더를 동반한다.
* 상태 변경(POST/PATCH/DELETE) 요청은 CSRF 토큰을 동반한다: `X-CSRFToken: <csrftoken cookie 값>`.

### 1.3 공통 Request Header (인증 필요 API)

| Header | 필수 | 설명 |
| --- | --- | --- |
| `Cookie` | 필수 | `sessionid=...` |
| `X-CSRFToken` | 상태 변경 시 필수 | 클라이언트가 `csrftoken` 쿠키에서 읽어 전송 |
| `Content-Type` | Body 있을 때 | `application/json` |

### 1.4 공통 응답 형태

성공 응답은 자원 별 스키마를 그대로 반환한다. 단일 자원이면 객체, 컬렉션이면 다음 형태를 사용한다.

```json
{
  "items": [ ... ],
  "page_info": {
    "page": 1,
    "size": 20,
    "total": 137,
    "total_pages": 7
  }
}
```

### 1.5 공통 에러 형태

```json
{
  "error": {
    "code": "INVALID_FIELD",
    "message": "사람이 읽을 수 있는 한국어 메시지",
    "details": { "field": "email" }
  }
}
```

* `code`는 SCREAMING_SNAKE_CASE.
* `details`는 선택. 필드 검증 오류 시 어떤 필드가 문제인지 표기.

### 1.6 페이지네이션

* 쿼리: `?page=1&size=20`
* `size` 기본값 20, 최대 100.
* 응답에는 항상 `page_info`가 포함된다.

### 1.7 DateTime

* ISO 8601 with timezone. 예: `"2026-06-22T14:06:00+09:00"`.
* 서버 저장은 UTC. 응답은 KST(`+09:00`)로 직렬화.

### 1.8 Status Code 정책

| 상황 | 코드 |
| --- | --- |
| 정상 조회 | 200 |
| 정상 생성 | 201 |
| 정상 삭제(본문 없음) | 204 |
| 입력 형식 오류 | 400 |
| 비즈니스 규칙 위반(상태 전이 불가, 중복 등) | 409 |
| 인증 필요/실패 | 401 |
| 권한 없음 | 403 |
| 자원 없음 | 404 |
| 의미 검증 실패(필드 형식은 맞으나 값 부적합) | 422 |
| 서버 오류 | 500 |

### 1.9 URI 컨벤션

CLAUDE.md §7 참조. 요지:

* 마지막 `/` 없음, 하이픈, 소문자, 명사형.
* 사용자 소유 자원은 `/users/me/{resource}`.
* 관리자 전용 자원은 `/admin/{resource}`.
* 조언가 전용 자원은 `/advisor/{resource}` 또는 `/users/me/{resource}` (역할 컨텍스트가 명확한 쪽).

---

## 2. Roles

| Role | 설명 |
| --- | --- |
| Anonymous | 비로그인. 회원가입, 로그인, Google OAuth 시작 가능. |
| User | 로그인 사용자 기본 역할. 고민 작성, 받은 조언 조회, 피드백 작성 가능. |
| Advisor | `USER` + ADVISOR 역할이 부여된 사용자. 활성 역할을 ADVISOR로 전환하면 배정 고민 조회 / 조언 작성 가능. |
| Admin | 관리자. 신청 심사, 고민 배정, 조언 승인, 피드백 관리, 역할 부여/회수 가능. |

권한 모델:

* 사용자는 동시에 여러 role을 보유할 수 있다(`USER`, `ADVISOR`, `ADMIN`).
* `active_role`은 사용자가 현재 전환 상태를 가리키는 단일 값이다(`USER` 또는 `ADVISOR`). `ADMIN`은 별도 활성 전환을 거치지 않고 권한 검사 시 항상 적용된다.

---

## 3. API Summary Table

총 43 엔드포인트. **MVP 열 ✓ = Phase 2 v1 구현 대상 (전 항목 ✓)**.

| # | Domain | Method | Endpoint | Permission | Description | MVP |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | health | GET | `/healthz` | Anonymous | 헬스 체크 | ✓ |
| 2 | auth | POST | `/api/v1/auth/signup` | Anonymous | 이메일 회원가입 + 자동 로그인 | ✓ |
| 3 | auth | POST | `/api/v1/auth/login` | Anonymous | 이메일 로그인 | ✓ |
| 4 | auth | POST | `/api/v1/auth/logout` | Authenticated | 로그아웃 (서버 세션 삭제) | ✓ |
| 5 | auth | GET | `/api/v1/auth/google/authorize` | Anonymous | Google OAuth 동의 화면으로 302 | ✓ |
| 6 | auth | GET | `/api/v1/auth/google/callback` | Anonymous | Google OAuth 콜백 → 세션 발급 | ✓ |
| 7 | user | GET | `/api/v1/users/me` | Authenticated | 내 정보 조회 | ✓ |
| 8 | user | PATCH | `/api/v1/users/me` | Authenticated | 내 정보 수정 | ✓ |
| 9 | user | GET | `/api/v1/users/me/roles` | Authenticated | 내 보유 역할 조회 | ✓ |
| 10 | user | PATCH | `/api/v1/users/me/active-role` | Authenticated | 활성 역할 전환 (USER ↔ ADVISOR) | ✓ |
| 11 | advisor-app | POST | `/api/v1/advisor-applications` | User | 조언가 신청 | ✓ |
| 12 | advisor-app | GET | `/api/v1/advisor-applications/me` | User | 내 신청 상태 조회 | ✓ |
| 13 | admin · advisor-app | GET | `/api/v1/admin/advisor-applications` | Admin | 신청 목록 | ✓ |
| 14 | admin · advisor-app | GET | `/api/v1/admin/advisor-applications/{application-id}` | Admin | 신청 상세 | ✓ |
| 15 | admin · advisor-app | PATCH | `/api/v1/admin/advisor-applications/{application-id}` | Admin | 신청 승인/반려 | ✓ |
| 16 | concern | POST | `/api/v1/users/me/concerns` | User | 내 고민 생성 | ✓ |
| 17 | concern | GET | `/api/v1/users/me/concerns` | User | 내 고민 목록 | ✓ |
| 18 | concern | GET | `/api/v1/users/me/concerns/{concern-id}` | User | 내 고민 상세 | ✓ |
| 19 | concern | DELETE | `/api/v1/users/me/concerns/{concern-id}` | User | 내 고민 소프트 삭제 | ✓ |
| 20 | concern · advisor | GET | `/api/v1/users/me/assigned-concerns` | Advisor | 내가 배정받은 고민 목록 | ✓ |
| 21 | concern · advisor | GET | `/api/v1/users/me/assigned-concerns/{concern-id}` | Advisor | 내가 배정받은 고민 상세 | ✓ |
| 22 | admin · concern | GET | `/api/v1/admin/concerns` | Admin | 전체 고민 목록 | ✓ |
| 23 | admin · concern | GET | `/api/v1/admin/concerns/{concern-id}` | Admin | 전체 고민 상세 | ✓ |
| 24 | admin · concern | POST | `/api/v1/admin/concerns/{concern-id}/assignments` | Admin | 고민에 조언가 배정 | ✓ |
| 25 | admin · concern | DELETE | `/api/v1/admin/concerns/{concern-id}/assignments/{assignment-id}` | Admin | 배정 해제 | ✓ |
| 26 | advice · user | GET | `/api/v1/users/me/advices` | User | 받은 조언 목록 (APPROVED만) | ✓ |
| 27 | advice | GET | `/api/v1/advices/{advice-id}` | Mixed (소유자/Admin) | 조언 상세 | ✓ |
| 28 | advice | POST | `/api/v1/concerns/{concern-id}/advices` | Advisor | 조언 작성 | ✓ |
| 29 | advice | PATCH | `/api/v1/advices/{advice-id}` | Advisor (작성자) | 조언 수정 | ✓ |
| 30 | advice | DELETE | `/api/v1/advices/{advice-id}` | Advisor (작성자) | 조언 삭제 | ✓ |
| 31 | advice · advisor | GET | `/api/v1/users/me/advices-written` | Advisor | 내가 작성한 조언 목록 | ✓ |
| 32 | admin · advice | GET | `/api/v1/admin/advices` | Admin | 조언 리뷰 목록 | ✓ |
| 33 | admin · advice | PATCH | `/api/v1/admin/advices/{advice-id}/review` | Admin | 조언 승인/반려 | ✓ |
| 34 | feedback | POST | `/api/v1/advices/{advice-id}/feedbacks` | User (고민 작성자) | 조언 피드백 작성 | ✓ |
| 35 | feedback | GET | `/api/v1/users/me/feedbacks` | User | 내 작성 피드백 목록 | ✓ |
| 36 | admin · feedback | GET | `/api/v1/admin/feedbacks` | Admin | 피드백 목록 | ✓ |
| 37 | admin · feedback | GET | `/api/v1/admin/feedbacks/{feedback-id}` | Admin | 피드백 상세 | ✓ |
| 38 | admin · feedback | PATCH | `/api/v1/admin/feedbacks/{feedback-id}` | Admin | 피드백 상태 변경 | ✓ |
| 39 | notification | GET | `/api/v1/notifications` | Authenticated | 내 알림 목록 | ✓ |
| 40 | notification | GET | `/api/v1/notifications/{notification-id}` | Authenticated (수신자) | 알림 상세 | ✓ |
| 41 | notification | PATCH | `/api/v1/notifications/{notification-id}/read` | Authenticated (수신자) | 알림 읽음 처리 | ✓ |
| 42 | admin · role | POST | `/api/v1/admin/users/{user-id}/roles` | Admin | 역할 부여 (ADMIN/ADVISOR) | ✓ |
| 43 | admin · role | DELETE | `/api/v1/admin/users/{user-id}/roles/{role}` | Admin | 역할 해제 | ✓ |

URI 변경 요약 (Notion v0 → v1):

| v0 | v1 | 사유 |
| --- | --- | --- |
| `POST /api/v1/concerns` | `POST /api/v1/users/me/concerns` | Q4 사용자 자원 통일 |
| `DELETE /api/v1/concerns/{concern_id}` | `DELETE /api/v1/users/me/concerns/{concern-id}` | Q4 사용자 자원 통일 + 하이픈 |
| `GET /api/v1/advisor/assigned-concerns` | `GET /api/v1/users/me/assigned-concerns` | Q4 사용자 자원 통일 |
| `GET /api/v1/advisor/assigned-concerns/{concern_id}` | `GET /api/v1/users/me/assigned-concerns/{concern-id}` | 위와 동일 |
| `GET /api/v1/advisor/advices` | `GET /api/v1/users/me/advices-written` | Q4 + 명확성 (받은 조언과 구분) |
| `PATCH /api/v1/admin/advisor-applications/{application_id}/status` | `PATCH /api/v1/admin/advisor-applications/{application-id}` | 상태를 sub-resource로 빼지 않고 자원 PATCH로 표현 |
| `PATCH /api/v1/admin/feedbacks/{feedback_id}/status` | `PATCH /api/v1/admin/feedbacks/{feedback-id}` | 위와 동일 |

`/admin/advices/{advice-id}/review`와 `/notifications/{id}/read`는 단순 상태 변경이 아니라 별도 의미를 가진 액션(review = 승인/반려 판정 + 부수효과 트리거, read = is_read 플래그 토글)이므로 액션-스타일 sub-resource로 유지한다.

---

## 4. Detailed API Specification

### 1. GET /healthz

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/healthz` |
| Permission | Anonymous |
| Description | 앱 컨테이너의 단순 헬스 체크. 의존성(DB) 체크는 별도 엔드포인트(`/healthz/db`)를 차후 검토. |
| Request 주요 필드 | 없음 |
| Response 주요 필드 | `{"status": "ok"}` |
| Status | 200 / 500 |
| 접근 제어 조건 | 없음 |
| Side Effect | 없음 |
| MVP 여부 | ✓ |

### 2. POST /api/v1/auth/signup

| 항목 | 내용 |
| --- | --- |
| Method | POST |
| Endpoint | `/api/v1/auth/signup` |
| Permission | Anonymous |
| Description | 이메일 회원가입. 성공 시 자동 로그인되어 `Set-Cookie: sessionid` 응답. |
| Request 주요 필드 | `email` (필수, 이메일 형식, unique), `password` (필수, 최소 8자), `nickname` (필수, 2~20자, unique) |
| Response 주요 필드 | `user_id`, `email`, `nickname`, `active_role` ("USER"), `created_at` |
| Response Header | `Set-Cookie: sessionid=...; HttpOnly; Secure; SameSite=Lax` |
| Status | 201 / 400 / 409 / 500 |
| 접근 제어 조건 | 없음 |
| Side Effect | User 생성, Session 생성, 환영 알림 없음(MVP 정책). |
| MVP 여부 | ✓ |

### 3. POST /api/v1/auth/login

| 항목 | 내용 |
| --- | --- |
| Method | POST |
| Endpoint | `/api/v1/auth/login` |
| Permission | Anonymous |
| Description | 이메일 + 비밀번호 로그인. |
| Request 주요 필드 | `email`, `password` |
| Response 주요 필드 | `user`: { `user_id`, `email`, `nickname`, `active_role` } |
| Response Header | `Set-Cookie: sessionid=...; HttpOnly; Secure; SameSite=Lax` |
| Status | 200 / 400 / 401 / 403(정지/탈퇴) / 500 |
| 접근 제어 조건 | 정지/탈퇴 계정은 403. |
| Side Effect | Session 생성. |
| MVP 여부 | ✓ |

### 4. POST /api/v1/auth/logout

| 항목 | 내용 |
| --- | --- |
| Method | POST |
| Endpoint | `/api/v1/auth/logout` |
| Permission | Authenticated |
| Description | 서버 세션 삭제 + 클라이언트 쿠키 만료. |
| Request 주요 필드 | 없음 |
| Response 주요 필드 | `{"message": "로그아웃 되었습니다."}` |
| Response Header | `Set-Cookie: sessionid=; Max-Age=0; HttpOnly; Secure; SameSite=Lax` |
| Status | 200 / 401 / 500 |
| 접근 제어 조건 | 인증 필요. |
| Side Effect | 서버 세션 레코드 삭제. |
| MVP 여부 | ✓ |

### 5. GET /api/v1/auth/google/authorize

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/auth/google/authorize` |
| Permission | Anonymous |
| Description | Google OAuth 동의 화면으로 302 리다이렉트. `state` 발급. |
| Request 주요 필드 | 없음 |
| Response Header | `Location: <Google authorize URL>`, `Set-Cookie: oauth_state=...; HttpOnly; Secure; SameSite=Lax` |
| Status | 302 / 500 |
| 접근 제어 조건 | 없음. |
| Side Effect | 서버에 `state` 임시 저장. |
| MVP 여부 | ✓ |

### 6. GET /api/v1/auth/google/callback

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/auth/google/callback` |
| Permission | Anonymous |
| Description | Google 콜백 처리. `state` 검증 → ID token 검증 → User 조회/생성 → Session 발급 → 프론트 진입 URL로 302. |
| Request 주요 필드 | Query: `code`, `state`, `error?` |
| Response Header | `Set-Cookie: sessionid=...; HttpOnly; Secure; SameSite=Lax`, `Location: /` |
| Status | 302 / 400 / 401 / 409(다른 로그인 방식으로 이미 가입) / 500 / 502 |
| 접근 제어 조건 | `state` 불일치 시 400. |
| Side Effect | User 조회 또는 생성, Session 생성. 이메일 매칭 시 OAuth 식별자만 기존 계정에 링크. |
| MVP 여부 | ✓ |

### 7. GET /api/v1/users/me

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/users/me` |
| Permission | Authenticated |
| Description | 내 정보 조회. |
| Request 주요 필드 | 없음 |
| Response 주요 필드 | `user_id`, `email`, `nickname`, `active_role`, `roles[]`, `created_at`. ※ `advisor_type` 노출 안 함(Q15). |
| Status | 200 / 401 / 500 |
| 접근 제어 조건 | 본인만. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 8. PATCH /api/v1/users/me

| 항목 | 내용 |
| --- | --- |
| Method | PATCH |
| Endpoint | `/api/v1/users/me` |
| Permission | Authenticated |
| Description | 내 정보 수정. |
| Request 주요 필드 | `nickname?`, `job?`, `interest?`, `profile_image_url?` (모두 선택, 부분 수정) |
| Response 주요 필드 | `user_id`, `email`, `nickname`, `updated_at` |
| Status | 200 / 400 / 401 / 409(nickname 중복) / 500 |
| 접근 제어 조건 | 본인만. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 9. GET /api/v1/users/me/roles

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/users/me/roles` |
| Permission | Authenticated |
| Description | 내 보유 역할 목록 + 현재 활성 역할 + 조언가 신청 상태. |
| Request 주요 필드 | 없음 |
| Response 주요 필드 | `roles[]` (예: `["USER","ADVISOR"]`), `active_role`, `advisor_status` (`NONE`/`PENDING`/`REVIEWING`/`APPROVED`/`REJECTED`) |
| Status | 200 / 401 / 500 |
| 접근 제어 조건 | 본인만. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 10. PATCH /api/v1/users/me/active-role

| 항목 | 내용 |
| --- | --- |
| Method | PATCH |
| Endpoint | `/api/v1/users/me/active-role` |
| Permission | Authenticated |
| Description | 활성 역할 전환. ADVISOR로 전환은 ADVISOR 역할 보유자만 가능. |
| Request 주요 필드 | `active_role` (`"USER"` 또는 `"ADVISOR"`) |
| Response 주요 필드 | `user_id`, `active_role`, `roles[]` |
| Status | 200 / 400 / 401 / 403 / 500 |
| 접근 제어 조건 | 본인만, 보유 역할로만 전환 가능. |
| Side Effect | 세션 컨텍스트에 `active_role` 저장. |
| MVP 여부 | ✓ |

### 11. POST /api/v1/advisor-applications

| 항목 | 내용 |
| --- | --- |
| Method | POST |
| Endpoint | `/api/v1/advisor-applications` |
| Permission | User |
| Description | 조언가 신청. 진행 중인 신청이 있으면 중복 불가(409). |
| Request 주요 필드 | `display_name` (필수, 2~20자, advisor 프로필명, unique), `domain_category` (enum), `experience_band` (`5-7`/`8-12`/`13+`), `current_status` (enum: 재직/프리랜서/휴직/휴식/은퇴), `intended_lane` (enum: `expert`/`senior` — Q5에 따라 참고용), `career_narrative` (text), `advisable_concern_types[]` (CLAUDE.md §6.5 영문 enum, 1개 이상), `sample_advice_response` (text, 200~400자) |
| Response 주요 필드 | `application_id`, `status` (`PENDING`), `submitted_at` |
| Status | 201 / 400 / 401 / 409 / 500 |
| 접근 제어 조건 | 로그인 사용자, 진행 중 신청 없음(`PENDING`/`REVIEWING`/`APPROVED` 중 어느 것도 아님). |
| Side Effect | AdvisorApplication 생성. |
| MVP 여부 | ✓ |

### 12. GET /api/v1/advisor-applications/me

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/advisor-applications/me` |
| Permission | User |
| Description | 내가 제출한 가장 최근 조언가 신청 1건의 상태 조회. |
| Request 주요 필드 | 없음 |
| Response 주요 필드 | `application_id`, `display_name`, `status`, `submitted_at`, `reviewed_at?`, `reject_reason?` (Q16에 따라 노출) |
| Status | 200 / 401 / 404(신청 이력 없음) / 500 |
| 접근 제어 조건 | 본인 신청만. `intended_lane`은 응답에 포함하지 않는다. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 13. GET /api/v1/admin/advisor-applications

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/admin/advisor-applications` |
| Permission | Admin |
| Description | 신청 목록 조회. |
| Request 주요 필드 | Query: `status?`, `page?`, `size?` |
| Response 주요 필드 | `items[]`: { `application_id`, `applicant_user_id`, `display_name`, `status`, `submitted_at` }, `page_info` |
| Status | 200 / 400 / 401 / 403 / 500 |
| 접근 제어 조건 | ADMIN. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 14. GET /api/v1/admin/advisor-applications/{application-id}

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/admin/advisor-applications/{application-id}` |
| Permission | Admin |D
| Description | 신청 상세. 관리자만 `intended_lane`을 볼 수 있다. |
| Request 주요 필드 | Path: `application-id` |
| Response 주요 필드 | `application_id`, `applicant_user_id`, `display_name`, `domain_category`, `experience_band`, `current_status`, `intended_lane`, `career_narrative`, `advisable_concern_types[]`, `sample_advice_response`, `status`, `submitted_at`, `reviewed_at?`, `reviewed_by?`, `reject_reason?` |
| Status | 200 / 401 / 403 / 404 / 500 |
| 접근 제어 조건 | ADMIN. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 15. PATCH /api/v1/admin/advisor-applications/{application-id}

| 항목 | 내용 |
| --- | --- |
| Method | PATCH |
| Endpoint | `/api/v1/admin/advisor-applications/{application-id}` |
| Permission | Admin |
| Description | 신청 상태 변경(승인/반려/검토 시작). |
| Request 주요 필드 | `status` (enum: `REVIEWING`/`APPROVED`/`REJECTED`), `reject_reason?` (status=REJECTED 시 필수, 422 검증) |
| Response 주요 필드 | `application_id`, `status`, `reviewed_at`, `reviewed_by` |
| Status | 200 / 400 / 401 / 403 / 404 / 409(허용되지 않는 전이) / 422 / 500 |
| 접근 제어 조건 | ADMIN. 허용 전이: `PENDING → REVIEWING → APPROVED|REJECTED`. `APPROVED`/`REJECTED`/`WITHDRAWN`에서의 재전이는 409. |
| Side Effect | `APPROVED` 시 신청자에게 `ADVISOR` 역할 부여(별도 RoleGrant 레코드 작성). `APPROVED`/`REJECTED` 시 알림 생성(`ADVISOR_APPLICATION_APPROVED`/`ADVISOR_APPLICATION_REJECTED`). |
| MVP 여부 | ✓ |

### 16. POST /api/v1/users/me/concerns

| 항목 | 내용 |
| --- | --- |
| Method | POST |
| Endpoint | `/api/v1/users/me/concerns` |
| Permission | User |
| Description | 내 고민 생성. |
| Request 주요 필드 | `concern_summary` (필수, ≤100자), `concern_type` (필수, taxonomy enum), `concern_type_secondary[]?` (taxonomy enum, 최대 2개), `preferred_advisor_lane?` (`expert`/`senior`/`no_preference`, default `no_preference`), `decision_context?` (text), `display_alias?` (string), `is_anonymous?` (bool, default true) |
| Response 주요 필드 | `concern_id`, `status` (`SUBMITTED`), `message` |
| Status | 201 / 400 / 401 / 500 |
| 접근 제어 조건 | User 역할 활성 상태에서만 가능. |
| Side Effect | Concern 생성(`status=SUBMITTED`, `is_deleted=false`). |
| MVP 여부 | ✓ |

### 17. GET /api/v1/users/me/concerns

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/users/me/concerns` |
| Permission | User |
| Description | 내 고민 목록. 소프트 삭제된 항목 제외. |
| Request 주요 필드 | Query: `keyword?`, `from_date?`, `to_date?`, `status?`, `page?`, `size?` |
| Response 주요 필드 | `items[]`: { `concern_id`, `concern_summary`, `concern_type`, `status`, `has_approved_advice` (bool), `created_at` }, `page_info` |
| Status | 200 / 401 / 500 |
| 접근 제어 조건 | 본인 고민만. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 18. GET /api/v1/users/me/concerns/{concern-id}

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/users/me/concerns/{concern-id}` |
| Permission | User |
| Description | 내 고민 상세. 본인 고민만 (Q11). 첨부된 APPROVED advice 목록 포함. |
| Request 주요 필드 | Path: `concern-id` |
| Response 주요 필드 | `concern_id`, `concern_summary`, `concern_type`, `concern_type_secondary[]`, `preferred_advisor_lane`, `decision_context`, `is_anonymous`, `status`, `created_at`, `approved_advices[]`: { `advice_id`, `advisor_display_name`, `created_at` } |
| Status | 200 / 401 / 403 / 404 / 500 |
| 접근 제어 조건 | 본인만. `is_deleted=true`는 404. `approved_advices`는 APPROVED 상태만 포함(CLAUDE.md §6.2). |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 19. DELETE /api/v1/users/me/concerns/{concern-id}

| 항목 | 내용 |
| --- | --- |
| Method | DELETE |
| Endpoint | `/api/v1/users/me/concerns/{concern-id}` |
| Permission | User |
| Description | 내 고민 소프트 삭제(`is_deleted=true`). 연결된 advice/assignment는 보존. |
| Request 주요 필드 | Path: `concern-id` |
| Response 주요 필드 | 본문 없음(204). |
| Status | 204 / 401 / 403 / 404 / 409(이미 삭제됨) / 500 |
| 접근 제어 조건 | 본인 고민만. |
| Side Effect | `is_deleted=true`. 추가 작성 advice / 배정 트리거 금지. |
| MVP 여부 | ✓ |

### 20. GET /api/v1/users/me/assigned-concerns

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/users/me/assigned-concerns` |
| Permission | Advisor (active_role=ADVISOR) |
| Description | 내가 배정받은 고민 목록. |
| Request 주요 필드 | Query: `status?` (assignment 상태), `page?`, `size?` |
| Response 주요 필드 | `items[]`: { `concern_id`, `concern_summary` (익명 처리 적용), `concern_type`, `assigned_at`, `assignment_id`, `advice_status?` (내가 작성한 advice 상태) }, `page_info` |
| Status | 200 / 401 / 403 / 500 |
| 접근 제어 조건 | `active_role=ADVISOR` 일 때만. ADVISOR 역할만 보유하고 active_role이 USER면 403. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 21. GET /api/v1/users/me/assigned-concerns/{concern-id}

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/users/me/assigned-concerns/{concern-id}` |
| Permission | Advisor (배정된 경우만) |
| Description | 배정된 고민 상세. |
| Request 주요 필드 | Path: `concern-id` |
| Response 주요 필드 | `concern_id`, `concern_summary`, `concern_type`, `concern_type_secondary[]`, `decision_context`, `is_anonymous`, `requester_display_alias?`, `assigned_at`, `assignment_id`, `my_advice?`: { `advice_id`, `status`, `version` } |
| Status | 200 / 401 / 403(배정 안 됨) / 404 / 500 |
| 접근 제어 조건 | 해당 concern에 active 배정이 있는 advisor 본인만. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 22. GET /api/v1/admin/concerns

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/admin/concerns` |
| Permission | Admin |
| Description | 전체 고민 목록. 소프트 삭제 포함 여부는 query로 제어. |
| Request 주요 필드 | Query: `status?`, `keyword?`, `include_deleted?` (bool, default false), `page?`, `size?` |
| Response 주요 필드 | `items[]`: { `concern_id`, `author_user_id`, `concern_summary`, `concern_type`, `status`, `is_deleted`, `created_at`, `assignment_count` }, `page_info` |
| Status | 200 / 400 / 401 / 403 / 500 |
| 접근 제어 조건 | ADMIN. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 23. GET /api/v1/admin/concerns/{concern-id}

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/admin/concerns/{concern-id}` |
| Permission | Admin |
| Description | 고민 상세 + 배정 + 모든 advice 목록(상태 무관). |
| Request 주요 필드 | Path: `concern-id` |
| Response 주요 필드 | concern 필드 전체, `assignments[]`: { `assignment_id`, `advisor_user_id`, `advisor_display_name`, `assigned_at`, `assigned_by`, `is_active` }, `advices[]`: { `advice_id`, `advisor_user_id`, `status`, `version`, `created_at` } |
| Status | 200 / 401 / 403 / 404 / 500 |
| 접근 제어 조건 | ADMIN. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 24. POST /api/v1/admin/concerns/{concern-id}/assignments

| 항목 | 내용 |
| --- | --- |
| Method | POST |
| Endpoint | `/api/v1/admin/concerns/{concern-id}/assignments` |
| Permission | Admin |
| Description | 고민에 advisor 배정. **1 concern ↔ N advisor** (Q9). 동일 active 배정 중복은 409. |
| Request 주요 필드 | `advisor_user_id` (필수, APPROVED ADVISOR 역할 보유), `triage_decision` (enum: `suitable`/`needs_more_info`/`out_of_scope`), `match_rationale?`: { `matched_types[]?`, `lane_match?`, `note?` }, `priority?` (enum: `low`/`normal`/`high`, default `normal`) |
| Response 주요 필드 | `assignment_id`, `concern_id`, `advisor_user_id`, `assigned_by`, `assigned_at`, `priority`, `concern_status` (전이 후 상태) |
| Status | 201 / 400 / 401 / 403 / 404(concern 없음) / 409(중복 active 배정 또는 concern이 CLOSED) / 422 / 500 |
| 접근 제어 조건 | ADMIN. concern이 `CLOSED`이거나 `is_deleted=true`면 409. |
| Side Effect | Assignment 생성. concern.status가 `SUBMITTED`였다면 `ASSIGNED`로 전이. 알림 발송(`ASSIGNMENT_CREATED`). |
| MVP 여부 | ✓ |

### 25. DELETE /api/v1/admin/concerns/{concern-id}/assignments/{assignment-id}

| 항목 | 내용 |
| --- | --- |
| Method | DELETE |
| Endpoint | `/api/v1/admin/concerns/{concern-id}/assignments/{assignment-id}` |
| Permission | Admin |
| Description | 배정 해제. 배정 레코드는 보존하되 `is_active=false`로 표시(감사 로그). |
| Request 주요 필드 | Path: `concern-id`, `assignment-id` |
| Response 주요 필드 | 본문 없음(204) 또는 `{ "concern_status": "..." }` (200). 본 명세는 204로 통일. |
| Status | 204 / 401 / 403 / 404 / 409(이미 비활성) / 500 |
| 접근 제어 조건 | ADMIN. 해당 assignment가 active 상태여야 함. |
| Side Effect | `is_active=false`. 모든 assignment가 비활성이 되면 concern.status를 `ASSIGNED` → `SUBMITTED`로 되돌림. |
| MVP 여부 | ✓ |

### 26. GET /api/v1/users/me/advices

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/users/me/advices` |
| Permission | User |
| Description | 내가 작성한 고민들에 달린 **APPROVED** advice 목록 (CLAUDE.md §6.2). |
| Request 주요 필드 | Query: `keyword?`, `from_date?`, `to_date?`, `page?`, `size?` |
| Response 주요 필드 | `items[]`: { `advice_id`, `concern_id`, `concern_summary`, `advisor_display_name`, `created_at`, `is_feedback_submitted` (bool) }, `page_info` |
| Status | 200 / 401 / 500 |
| 접근 제어 조건 | 본인 고민에 달린 APPROVED advice만. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 27. GET /api/v1/advices/{advice-id}

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/advices/{advice-id}` |
| Permission | Mixed |
| Description | 조언 상세. 조회 가능 주체별로 응답 필드가 다르다. |
| Request 주요 필드 | Path: `advice-id` |
| Response 주요 필드 | `advice_id`, `concern_id`, `advisor_display_name`, `directional_guidance`, `reflective_questions?`, `considerations?`, `out_of_scope_flag`, `status`, `version`, `created_at`, `updated_at` |
| Status | 200 / 401 / 403 / 404 / 500 |
| 접근 제어 조건 | (a) 조언 작성자: 자신의 advice는 상태 무관 조회 가능. (b) 고민 작성자: 해당 advice가 APPROVED일 때만 조회 가능. (c) ADMIN: 상태 무관 조회 가능. 그 외 403. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 28. POST /api/v1/concerns/{concern-id}/advices

| 항목 | 내용 |
| --- | --- |
| Method | POST |
| Endpoint | `/api/v1/concerns/{concern-id}/advices` |
| Permission | Advisor (배정된 경우만) |
| Description | 배정받은 고민에 대한 조언 작성. **advisor 1명당 concern 1건은 advice 1개만 작성 가능** (Q10). |
| Request 주요 필드 | `directional_guidance` (필수, ≤1500자), `reflective_questions?`, `considerations?`, `out_of_scope_flag?` (bool, default false), `submit?` (bool, default true) |
| Response 주요 필드 | `advice_id`, `concern_id`, `advisor_user_id`, `status` (`PENDING` 또는 `PENDING`+draft 표시), `version` (1), `created_at` |
| Status | 201 / 400 / 401 / 403(미배정) / 404 / 409(이미 advice 존재) / 422 / 500 |
| 접근 제어 조건 | 해당 concern에 active 배정이 있는 advisor만. `submit=true` → 상태 `PENDING`(관리자 리뷰 대상). `submit=false` → 동일 advisor가 작성 중인 draft 상태(`PENDING`을 그대로 유지하되 별도 `is_submitted` 플래그). |
| Side Effect | Advice 생성. `submit=true`로 처음 제출되는 순간 `is_submitted=true`로 기록. |
| MVP 여부 | ✓ |

### 29. PATCH /api/v1/advices/{advice-id}

| 항목 | 내용 |
| --- | --- |
| Method | PATCH |
| Endpoint | `/api/v1/advices/{advice-id}` |
| Permission | Advisor (작성자) |
| Description | 조언 수정. `PENDING` 또는 `REVIEWING` 상태에서만 가능. 수정 시 `version`이 +1되고 이전 본문은 audit 테이블에 보존. |
| Request 주요 필드 | `directional_guidance?`, `reflective_questions?`, `considerations?`, `out_of_scope_flag?`, `submit?` |
| Response 주요 필드 | `advice_id`, `status`, `version`, `updated_at` |
| Status | 200 / 400 / 401 / 403 / 404 / 409(승인/반려/삭제 후 수정) / 500 |
| 접근 제어 조건 | 작성자 본인 + 상태 ∈ {PENDING, REVIEWING}. |
| Side Effect | Advice 본문 갱신, `version` 증가, AdviceHistory 행 추가. |
| MVP 여부 | ✓ |

### 30. DELETE /api/v1/advices/{advice-id}

| 항목 | 내용 |
| --- | --- |
| Method | DELETE |
| Endpoint | `/api/v1/advices/{advice-id}` |
| Permission | Advisor (작성자) |
| Description | 조언 삭제(소프트). `status=DELETED`로 전이. |
| Request 주요 필드 | Path: `advice-id` |
| Response 주요 필드 | 본문 없음(204). |
| Status | 204 / 401 / 403 / 404 / 409(이미 APPROVED 또는 DELETED) / 500 |
| 접근 제어 조건 | 작성자 본인 + 상태 ∈ {PENDING, REVIEWING}. APPROVED 후 삭제는 ADMIN 별도 흐름(Phase 2 v1에서는 미제공, 후순위로 Django Admin 처리). |
| Side Effect | Advice 상태를 `DELETED`로 전이. |
| MVP 여부 | ✓ |

### 31. GET /api/v1/users/me/advices-written

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/users/me/advices-written` |
| Permission | Advisor |
| Description | 내가 작성한 조언 전체 목록(상태 무관). |
| Request 주요 필드 | Query: `concern_id?`, `status?`, `from_date?`, `to_date?`, `page?`, `size?` |
| Response 주요 필드 | `items[]`: { `advice_id`, `concern_id`, `status`, `version`, `created_at`, `updated_at` }, `page_info` |
| Status | 200 / 401 / 403 / 500 |
| 접근 제어 조건 | active_role=ADVISOR. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 32. GET /api/v1/admin/advices

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/admin/advices` |
| Permission | Admin |
| Description | 조언 리뷰 목록. |
| Request 주요 필드 | Query: `status?` (default `PENDING`), `page?`, `size?` |
| Response 주요 필드 | `items[]`: { `advice_id`, `concern_id`, `advisor_user_id`, `status`, `version`, `created_at`, `updated_at` }, `page_info` |
| Status | 200 / 400 / 401 / 403 / 500 |
| 접근 제어 조건 | ADMIN. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 33. PATCH /api/v1/admin/advices/{advice-id}/review

| 항목 | 내용 |
| --- | --- |
| Method | PATCH |
| Endpoint | `/api/v1/admin/advices/{advice-id}/review` |
| Permission | Admin |
| Description | 조언 승인/반려. `review`는 단순 status 변경 이상의 액션(부수효과 다수) 이므로 액션 sub-resource 유지. |
| Request 주요 필드 | `decision` (필수, `approved`/`rejected`), `reason?` (rejected 시 필수 — 422 검증) |
| Response 주요 필드 | `advice_id`, `status`, `review`: { `decision`, `reviewed_by`, `reviewed_at`, `reason` }, `concern_id`, `concern_status` (전이 후), `version` |
| Status | 200 / 401 / 403 / 404 / 409(허용되지 않는 전이) / 412(advice가 이미 외부에서 변경됨 — version mismatch) / 422 / 500 |
| 접근 제어 조건 | ADMIN. 허용 전이: `PENDING|REVIEWING → APPROVED|REJECTED`. |
| Side Effect | `APPROVED` → 고민 작성자에게 `ADVICE_APPROVED` 알림 + concern.status → `ANSWERED` (아직 ANSWERED가 아닌 경우). `REJECTED` → advisor에게 `ADVICE_REJECTED` 알림. |
| MVP 여부 | ✓ |

### 34. POST /api/v1/advices/{advice-id}/feedbacks

| 항목 | 내용 |
| --- | --- |
| Method | POST |
| Endpoint | `/api/v1/advices/{advice-id}/feedbacks` |
| Permission | User (해당 고민 작성자) |
| Description | 받은 조언에 대한 피드백 작성. 조언 1개당 1회. 제출 후 수정/삭제 불가. |
| Request 주요 필드 | `score` (필수, int 1~5), `content?` (text) |
| Response 주요 필드 | `feedback_id`, `advice_id`, `status` (`SUBMITTED`), `created_at` |
| Status | 201 / 400 / 401 / 403(작성자 아님 또는 advice가 APPROVED 아님) / 404 / 409(이미 피드백 존재) / 500 |
| 접근 제어 조건 | 해당 advice가 연결된 concern의 작성자만. advice.status=APPROVED 필수. |
| Side Effect | Feedback 생성. |
| MVP 여부 | ✓ |

### 35. GET /api/v1/users/me/feedbacks

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/users/me/feedbacks` |
| Permission | User |
| Description | 내가 작성한 피드백 목록. |
| Request 주요 필드 | Query: `page?`, `size?` |
| Response 주요 필드 | `items[]`: { `feedback_id`, `advice_id`, `score`, `content`, `status`, `created_at` }, `page_info` |
| Status | 200 / 401 / 500 |
| 접근 제어 조건 | 본인 작성 피드백만. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 36. GET /api/v1/admin/feedbacks

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/admin/feedbacks` |
| Permission | Admin |
| Description | 피드백 목록. |
| Request 주요 필드 | Query: `status?`, `score_min?`, `score_max?`, `page?`, `size?` |
| Response 주요 필드 | `items[]`: { `feedback_id`, `advice_id`, `advisor_user_id`, `author_user_id`, `score`, `status`, `created_at` }, `page_info` |
| Status | 200 / 400 / 401 / 403 / 500 |
| 접근 제어 조건 | ADMIN. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 37. GET /api/v1/admin/feedbacks/{feedback-id}

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/admin/feedbacks/{feedback-id}` |
| Permission | Admin |
| Description | 피드백 상세. |
| Request 주요 필드 | Path: `feedback-id` |
| Response 주요 필드 | `feedback_id`, `advice_id`, `advisor_user_id`, `author_user_id`, `author_nickname`, `score`, `content`, `status`, `reviewed_at?`, `reviewed_by?`, `memo?`, `created_at` |
| Status | 200 / 401 / 403 / 404 / 500 |
| 접근 제어 조건 | ADMIN. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 38. PATCH /api/v1/admin/feedbacks/{feedback-id}

| 항목 | 내용 |
| --- | --- |
| Method | PATCH |
| Endpoint | `/api/v1/admin/feedbacks/{feedback-id}` |
| Permission | Admin |
| Description | 피드백 상태 변경. |
| Request 주요 필드 | `status` (enum: `SUBMITTED`/`REVIEWED`/`ARCHIVED`), `memo?` |
| Response 주요 필드 | `feedback_id`, `status`, `reviewed_at`, `reviewed_by` |
| Status | 200 / 400 / 401 / 403 / 404 / 409 / 500 |
| 접근 제어 조건 | ADMIN. 허용 전이: `SUBMITTED → REVIEWED → ARCHIVED` (역방향 불가). |
| Side Effect | 상태 갱신. 알림 없음. |
| MVP 여부 | ✓ |

### 39. GET /api/v1/notifications

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/notifications` |
| Permission | Authenticated |
| Description | 내 알림 목록. |
| Request 주요 필드 | Query: `is_read?`, `type?`, `page?`, `size?` |
| Response 주요 필드 | `items[]`: { `notification_id`, `type`, `title`, `message`, `target_url`, `is_read`, `created_at` }, `page_info`, `unread_count` |
| Status | 200 / 401 / 500 |
| 접근 제어 조건 | 본인 수신 알림만. |
| Side Effect | 없음. |
| MVP 여부 | ✓ |

### 40. GET /api/v1/notifications/{notification-id}

| 항목 | 내용 |
| --- | --- |
| Method | GET |
| Endpoint | `/api/v1/notifications/{notification-id}` |
| Permission | Authenticated (수신자) |
| Description | 알림 상세. |
| Request 주요 필드 | Path: `notification-id` |
| Response 주요 필드 | `notification_id`, `type`, `title`, `message`, `target_url`, `is_read`, `read_at?`, `created_at`, `actor?`: { `user_id?`, `display_name?` } |
| Status | 200 / 401 / 403 / 404 / 500 |
| 접근 제어 조건 | 수신자 본인만. |
| Side Effect | 없음(읽음 처리는 별도 API). |
| MVP 여부 | ✓ |

### 41. PATCH /api/v1/notifications/{notification-id}/read

| 항목 | 내용 |
| --- | --- |
| Method | PATCH |
| Endpoint | `/api/v1/notifications/{notification-id}/read` |
| Permission | Authenticated (수신자) |
| Description | 알림 읽음 처리. |
| Request 주요 필드 | 없음 |
| Response 주요 필드 | `notification_id`, `is_read` (true), `read_at` |
| Status | 200 / 401 / 403 / 404 / 500 |
| 접근 제어 조건 | 수신자 본인만. |
| Side Effect | `is_read=true`, `read_at=now()`. |
| MVP 여부 | ✓ |

### 42. POST /api/v1/admin/users/{user-id}/roles

| 항목 | 내용 |
| --- | --- |
| Method | POST |
| Endpoint | `/api/v1/admin/users/{user-id}/roles` |
| Permission | Admin |
| Description | 대상 사용자에게 역할(`ADMIN` 또는 `ADVISOR`)을 부여. 자세한 규칙은 ADR-003. |
| Request 주요 필드 | `role` (enum: `ADMIN`/`ADVISOR`), `reason?` |
| Response 주요 필드 | `user_id`, `roles[]` (변경 후 보유 역할), `granted_role`, `granted_at`, `granted_by` |
| Status | 201 / 400 / 401 / 403 / 404 / 409(이미 보유 중) / 422 / 500 |
| 접근 제어 조건 | ADMIN. `USER`는 부여 대상이 아니다. |
| Side Effect | UserRole 추가, RoleGrant audit 레코드 추가. 알림 없음. |
| MVP 여부 | ✓ |

### 43. DELETE /api/v1/admin/users/{user-id}/roles/{role}

| 항목 | 내용 |
| --- | --- |
| Method | DELETE |
| Endpoint | `/api/v1/admin/users/{user-id}/roles/{role}` |
| Permission | Admin |
| Description | 대상 사용자에게서 역할을 회수. |
| Request 주요 필드 | Path: `user-id`, `role` (`ADMIN`/`ADVISOR`). Query: `reason?` |
| Response 주요 필드 | 본문 없음(204) 또는 `{ user_id, roles[] }` (200). 본 명세는 204. |
| Status | 204 / 401 / 403 / 404 / 409(자기 자신 ADMIN 회수, 마지막 ADMIN 회수, 보유하지 않은 역할) / 500 |
| 접근 제어 조건 | ADMIN. 자기 자신의 ADMIN 회수 불가. 마지막 ADMIN 회수 불가. `USER`는 회수 대상이 아니다. |
| Side Effect | UserRole 삭제, RoleGrant(action=REVOKE) audit 레코드 추가. ADVISOR 회수 시 active_role이 ADVISOR였다면 USER로 강제 전환. |
| MVP 여부 | ✓ |

---

## 5. Deferred APIs

Owner 결정(2026-06-22)에 따라 **Notion v0 명세에서 v1으로 미루는 API는 없다.** 본 명세의 43건이 Phase 2 v1 구현 대상이다.

다음 항목은 **본 명세에 의도적으로 포함하지 않은 것**으로, Phase 3+ 분리한다:

* 조언가 신청 사용자측 취소(`WITHDRAWN`) — CLAUDE.md §6.1에 따라 model에만 enum 유지.
* outcome tracking (조언 결과 장기 추적) — 별도 도메인.
* trust score 계산 — 알고리즘 결정 후.
* 알림 자동 푸시(WebSocket/SSE/Email) — 본 명세는 알림 생성 + 조회만.
* 사용자 계정 정지/탈퇴 흐름 — 정책 결정 필요.

---

## 6. Open Questions

Phase 2 코드 시작 전 / 진행 중 확정해야 할 작은 결정들. **차단 결정 아님**.

1. `concern_summary` 100자 제한이 최종? (현재 명세 기준 100자, 추후 도메인 검증에서 조정 가능)
2. `decision_context`의 글자 수 상한은? (현재 미정 — 4000자 권장)
3. `directional_guidance` 1500자 상한이 최종?
4. advice draft(`submit=false`)를 별도 status로 모델링할지, 같은 `PENDING`에 플래그로 표현할지 — 본 명세는 후자(`is_submitted` 플래그)로 가정.
5. concern의 `CLOSED` 전이는 사용자가 명시적으로 트리거하는 API가 필요한지? (현재 미정. Phase 2 v1에서는 Django Admin으로만 전이 가능)
6. 알림 `target_url`의 도메인은 환경별로 다를 수밖에 없음 — 응답에서는 상대 경로(`/users/me/concerns/{id}` 등)로 통일 권장.
7. 페이지네이션 `size` 최대 100이 적절한지 (현재 미검증).
8. Google OAuth 첫 가입 시 `nickname`을 어떻게 산정하는가? — 권장: Google profile name → unique 충돌 시 `name_NNNN` 자동 부여. 최종 확정 필요.

---

## 7. Notion Update Plan (notion_editing_rule 준수)

Notion DB는 직접 수정하지 않는다. 다음 패치 테이블을 Notion에 복사해 v0 → v1 일괄 갱신할 수 있도록 정리한다.

### 7.1 수정 대상 API (URI/스펙 변경)

| Notion 페이지명 | v0 → v1 변경 |
| --- | --- |
| 내 고민 생성 | URI: `/api/v1/concerns` → `/api/v1/users/me/concerns` |
| 내 고민 상세 조회 | "인증 필요" No → Yes |
| 내 고민 삭제 | URI: `/api/v1/concerns/{concern_id}` → `/api/v1/users/me/concerns/{concern-id}`. 시맨틱: 소프트 삭제. 응답: 204 |
| 조언가 배정 고민 목록 | URI: `/api/v1/advisor/assigned-concerns` → `/api/v1/users/me/assigned-concerns` |
| 조언가 배정 고민 상세 | URI: 위와 동일하게 `/users/me/assigned-concerns/{concern-id}` |
| 조언 목록 조회 | URI: `/api/v1/advisor/advices` → `/api/v1/users/me/advices-written` |
| 관리자 승인/반려 (신청) | URI: `/api/v1/admin/advisor-applications/{application_id}/status` → `/api/v1/admin/advisor-applications/{application-id}` (Method PATCH 유지) |
| 관리자 피드백 상태 변경 | URI: `/api/v1/admin/feedbacks/{feedback_id}/status` → `/api/v1/admin/feedbacks/{feedback-id}` |
| 조언가 신청 | `intended_lane` Public 노출 정책 추가 (응답 제거) |
| 조언가 신청 상태 조회 | `intended_lane` 제거, `reject_reason` 노출 명시 |
| 내 정보 조회 | `advisor_type` 응답에서 제거 |
| 조언 생성 | `submit=false`는 draft 플래그로 명시. version 시맨틱 추가. |
| 조언 수정 | 작성자 + 상태 ∈ {PENDING, REVIEWING} 제약 명시. version 증가 명시. |
| 조언 삭제 | 소프트 삭제(상태 → DELETED) 명시. APPROVED 후 삭제 금지 명시. |
| 관리자 조언 승인/반려 | enum 값 `approved`/`rejected` → 응답의 `status`는 `APPROVED`/`REJECTED`. `published`/`answered` 등 비표준 값 제거. `concern_status` 전이 `ANSWERED` 명시. |
| 조언 피드백 작성 | advice.status=APPROVED 조건 명시. |
| 회원가입 | 응답 헤더 `Set-Cookie: sessionid` 명시. 자동 로그인. nickname Nullable → Required. role 필드 제거(active_role로 통일). |
| 로그인 | 응답에서 access_token/refresh_token/expires_in/token_type 제거. `Set-Cookie: sessionid` 헤더 명시. |
| 로그아웃 | 응답 헤더 `Set-Cookie: sessionid=; Max-Age=0` 명시. |
| 활성 역할 전환 | 응답 형태 표준화. |

### 7.2 신규 추가 (Notion에 새 페이지 3건 생성 권고)

| 페이지명 | 요약 |
| --- | --- |
| 헬스 체크 | `GET /healthz`. Anonymous. `{status:"ok"}`. |
| 역할 부여 | `POST /api/v1/admin/users/{user-id}/roles`. ADMIN. |
| 역할 회수 | `DELETE /api/v1/admin/users/{user-id}/roles/{role}`. ADMIN. |

### 7.3 삭제 / 병합

| 항목 | 처리 |
| --- | --- |
| 토큰 재발급 | **삭제** (Session 채택으로 불필요) |
| new Endpoint (빈 페이지) | **삭제** |
| 제목 없음 (빈 페이지) | **삭제** |

### 7.4 상태값 변경 매핑

| 발견 위치 | 비표준 값 | 표준 값 |
| --- | --- | --- |
| 조언가 신청 응답 | `REVIEWED` | `REVIEWING` 또는 `APPROVED`/`REJECTED` (전이 시점에 따라) |
| 관리자 조언 리뷰 목록 query | `PENDING_REVIEW` | `PENDING` |
| 조언 생성 submit=true | `pending_review` | `PENDING` (with `is_submitted=true`) |
| 조언 생성 submit=false | `draft` | `PENDING` (with `is_submitted=false`) |
| 관리자 조언 승인/반려 응답 status | `published` | `APPROVED` |
| 관리자 조언 승인/반려 응답 concern_status | `answered` | `ANSWERED` |

### 7.5 Owner 승인 요청

위 7.1~7.4의 Notion 갱신은 Owner가 직접 수행하거나 별도 작업 세션으로 일괄 진행. 본 세션에서는 Notion DB를 직접 수정하지 않는다.
