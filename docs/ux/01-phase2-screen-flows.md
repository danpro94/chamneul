# chamneul Phase 2 — 화면 흐름 + API-to-Screen 매핑 명세 (UX Spec v1)

> 성격: **향후 프론트 구현을 위한 사양 + API 설계의 소비자 관점 교차검증**. Phase 2에서 프론트엔드 구현은 범위 밖(CLAUDE.md §5)이며, 본 문서는 코드 생성을 전제하지 않는다.
> 근거: CLAUDE.md §5·§6·§7·§8·§10, docs/api.md v1(43 엔드포인트), docs/model.md §3·§9, ADR-002, ADR-003, docs/reviews/03-milestone3-definition.md.
> 작성: frontend-ux-architect 에이전트 (2026-07-07), 43개 엔드포인트 전수 대조 완료.

## 1. UX 판정 요약

- 현재 api.md v1 + model.md 기준으로 3개 역할(USER/ADVISOR/ADMIN)의 전체 화면 흐름 설계가 **가능**하다.
- 단, 화면에서 즉시 드러난 소비자 관점 공백 4건(CSRF 부트스트랩, advice draft 구분 불가, 반려 사유 미노출, 리뷰 낙관적 잠금 수단 부재)은 M4 구현 전 수정이 저렴하다(§8).
- 창작으로 메우지 않은 미해결 지점은 §7 충돌 표에 보고했다.

---

## 2. 역할별 핵심 화면 구조 (사이트맵)

프론트 라우트는 제안값이며, 모든 화면 요소는 근거 API 번호(api.md §3)를 가진다.

### 2.1 공통 (비로그인 / 전역)

| 라우트(제안) | 화면 | 근거 API |
| --- | --- | --- |
| `/` | 랜딩(비로그인) / 로그인 후 홈으로 전환 | — / 7·9·17·39 |
| `/login` | 로그인 (이메일 + "Google로 계속하기") | 3, 5→6 |
| `/signup` | 회원가입 (가입 즉시 자동 로그인) | 2 |
| 전역 헤더 | 알림 벨(unread 배지) · 역할 스위처 · 프로필 메뉴 · 로그아웃 | 39, 10, 7, 4 |
| `/notifications` | 알림 목록/읽음 처리 | 39, 40, 41 |
| `/me` | 내 프로필 조회/수정 | 7, 8 |

### 2.2 USER (active_role=USER)

로그인 후 첫 화면은 **소셜 피드가 아니라 "내 고민 현황" 중심의 조용한 홈**이다: 진행 중 고민 상태 카드(최근 3건, API 17) + 새 조언 도착 안내(39) + "고민 남기기" 단일 CTA. 타인의 고민/조언은 어디에도 노출되지 않는다(공개 마켓플레이스 없음).

| 라우트(제안) | 화면 | 근거 API |
| --- | --- | --- |
| `/concerns` | 내 고민 목록 (상태 필터/검색) | 17 |
| `/concerns/new` | 고민 작성 — **비공개 인테이크** (단계형) | 16 |
| `/concerns/{id}` | 고민 상세 + 승인된 조언 목록 + 삭제 | 18, 19 |
| `/advices` | 받은 조언함 (APPROVED만) | 26 |
| `/advices/{id}` | 조언 상세 + 피드백 작성 | 27, 34 |
| `/feedbacks` | 내가 남긴 피드백 목록 | 35 |
| `/advisor/apply` | 조언가 신청 폼 | 11 |
| `/advisor/application` | 내 신청 상태 | 12 (+9의 `advisor_status`) |

### 2.3 ADVISOR (active_role=ADVISOR — 헤더 스위처로 전환, API 10)

역할 스위처는 **9의 `roles[]`에 ADVISOR가 있을 때만** 렌더링. 전환 후 홈은 "배정받은 고민" 목록이다.

| 라우트(제안) | 화면 | 근거 API |
| --- | --- | --- |
| `/advisor/assigned` | 배정 고민 목록 (내 조언 상태 병기) | 20 |
| `/advisor/assigned/{concern-id}` | 배정 고민 상세 + 조언 작성/수정/삭제 (인라인 에디터) | 21, 28, 29, 30 |
| `/advisor/advices` | 내가 작성한 조언 목록 (상태 무관) | 31 |
| `/advisor/advices/{advice-id}` | 내 조언 상세 (상태·버전) | 27 |

### 2.4 ADMIN (active_role 아님 — 별도 전환 없이 항상 적용)

`accounts/models.py`의 `ActiveRole` 주석 및 api.md §2와 동일하게, ADMIN은 "입는" 역할이 아니다. 따라서 **역할 스위처에 ADMIN 항목을 두지 않고**, 9의 `roles[]`에 ADMIN이 포함되면 헤더에 "관리 콘솔" 진입점을 상시 노출한다(현재 active_role이 USER든 ADVISOR든 무관). 관리자 화면은 테이블 중심의 실용적(utilitarian) UI를 허용한다.

| 라우트(제안) | 화면 | 근거 API |
| --- | --- | --- |
| `/admin/applications` | 조언가 신청 심사 큐 | 13 |
| `/admin/applications/{id}` | 신청 상세 + 검토시작/승인/반려 | 14, 15 |
| `/admin/concerns` | 전체 고민 테이블 (삭제 포함 토글) | 22 |
| `/admin/concerns/{id}` | 고민 상세 + 배정 패널(배정/해제) + 조언 현황 | 23, 24, 25 (+13 `status=APPROVED` 조언가 선택기) |
| `/admin/advices` | 조언 리뷰 큐 | 32 |
| `/admin/advices/{id}` | 조언 리뷰 상세 + 승인/반려 | 27, 33 |
| `/admin/feedbacks` | 피드백 테이블 | 36 |
| `/admin/feedbacks/{id}` | 피드백 상세 + 상태 변경/메모 | 37, 38 |
| `/admin/roles` | 역할 부여/회수 (user-id 입력식 — §7 C-9 참조) | 42, 43 |

---

## 3. 주요 사용자 흐름

### 3.1 USER 여정

```
[진입]
1. 랜딩 → 회원가입(2, 자동 로그인 Set-Cookie) 또는 로그인(3) 또는 Google(5→6, 302 복귀)
2. 앱 부트스트랩: GET /users/me(7) + GET /users/me/roles(9)
   → 401이면 로그인 화면, 200이면 홈

[핵심 여정: 고민 → 조언 → 피드백]
3. 홈 "고민 남기기" → /concerns/new
   단계형 인테이크 (progressive disclosure):
   Step 1  요약(≤100자) + 고민 유형(taxonomy 11종 한국어 라벨, §6.5)
   Step 2  (선택) 배경 맥락 decision_context + 보조 유형(최대 2)
   Step 3  공개 방식: is_anonymous 기본 ON + display_alias(선택)
           + preferred_advisor_lane(기본 "상관없음")
   → 제출(16) → 완료 화면: 기대 설정 카피 (§6 참조. "관리자가 확인 후
     조언가를 연결" — 자동 매칭 아님을 명시)
4. /concerns 목록(17): 상태 뱃지 + has_approved_advice 표시
5. /concerns/{id} 상세(18): 상태 타임라인 + approved_advices[]
6. 조언 도착: 알림(39, ADVICE_APPROVED) 클릭 → 읽음(41) → target_url 이동
   → 조언 상세(27) → 피드백 1회 작성(34, 점수 1~5 + 내용, 수정/삭제 불가 사전 고지)

[상태별 분기 — 사용자 화면 표기]
SUBMITTED  "접수됨 — 조언가 연결을 준비하고 있어요" (액션 없음, 삭제만 가능)
ASSIGNED   "조언가가 고민을 살펴보고 있어요" (※조언가 신원/인원수 비노출 — 18 응답에 배정 정보 없음. 의도된 설계)
ANSWERED   "조언이 도착했어요" + approved_advices 목록 (APPROVED만, §6.2)
CLOSED     "마무리된 고민" (읽기 전용. Phase 2 v1에는 사용자 닫기 API 없음 — 버튼 없음, §7 C-2)

[삭제 분기]
상세 하단 저강조 "이 고민 삭제하기" → 확인 모달(소프트 삭제·기록 보존 고지) → 19 → 목록 복귀

[조언가 되기 분기]
프로필 메뉴 → advisor_status(9) 분기:
  NONE      → 신청 CTA → /advisor/apply(11)
  PENDING/REVIEWING → "검토 중" 대기 화면(12)
  APPROVED  → 역할 스위처 활성화 안내
  REJECTED  → 반려 사유(reject_reason, 12) + 재신청 CTA(11은 종결 상태에서 재신청 허용)
```

### 3.2 ADVISOR 여정

```
1. 헤더 역할 스위처 "조언가로 전환" → PATCH active-role(10)
   → 성공 시 /advisor/assigned로 이동 (advisor 컨텍스트는 시각적으로 구분되되 차분하게)
   → 실패 403: 역할 미보유 → 스위처 숨김 상태로 복귀 + roles 재조회(9)
2. 배정 목록(20): concern_summary(익명 처리 적용) + advice_status 뱃지
   - 배정 알림(ASSIGNMENT_CREATED, 39)이 진입 트리거
3. 배정 상세(21): 고민 내용 + 요청자 표시(익명 원칙, §5.1) + my_advice 유무 분기
   - my_advice 없음 → 조언 작성 폼(28):
     directional_guidance(≤1500자, 필수) + reflective_questions + considerations
     + out_of_scope_flag("내 범위를 벗어난 고민" 체크 — 배정 거절 API가 없으므로 이것이 유일한 이탈 수단)
     + [임시저장 submit=false] / [제출 submit=true] 버튼 분리
   - my_advice 있음 → 상태별 분기:
     PENDING/REVIEWING → 수정(29, version+1 안내)/삭제(30) 가능 + "검토 대기 중" 배너
     APPROVED → 읽기 전용 "승인되어 요청자에게 전달됨" (수정/삭제 불가 — 30은 409)
     REJECTED → 읽기 전용 + 반려 사유(※현재 27 응답에 없음 — §7 C-5)
4. /advisor/advices(31): 전체 이력 (상태·버전) → 상세(27)
5. 결과 통보: ADVICE_REJECTED 알림(39) → 해당 조언으로 이동
[역할 회수 엣지] ADVISOR 회수(43) 시 서버가 active_role을 USER로 강제 전환
   → advisor 라우트 403 수신 시 roles 재조회(9) 후 USER 홈으로 안내
```

### 3.3 ADMIN 여정 (수동 운영이 제품 기능임을 화면으로 설명)

```
0. 부트스트랩: 최초 ADMIN은 createsuperuser (ADR-003 §1 — 화면 밖)
1. 관리 콘솔 홈 = 3개 큐 카운트 요약(13 status=PENDING, 32 status=PENDING, 36 status=SUBMITTED)
2. 신청 심사: 큐(13) → 상세(14 — intended_lane은 이 화면에서만 "신청자 의향(참고용)" 라벨로 표시)
   → [검토 시작 REVIEWING] → [승인/반려](15, 반려 시 사유 필수 — 422)
   → 부수효과 안내 토스트: "ADVISOR 역할 부여 + 신청자 알림 발송됨"
3. 고민 배정: 테이블(22) → 상세(23) → 배정 패널:
   조언가 선택기 = 13을 status=APPROVED로 필터해 display_name 목록으로 재사용
   + triage_decision + match_rationale(선택) + priority → 배정(24)
   → concern_status 전이 결과 표시(SUBMITTED→ASSIGNED) / 해제(25) → 전 배정 해제 시 SUBMITTED 복귀 표시
4. 조언 리뷰: 큐(32, 기본 PENDING) → 상세(27로 본문 로드) → 승인/반려(33)
   → 승인: "요청자 알림 + 고민 ANSWERED 전이" / 반려: 사유 필수 + "조언가 알림"
5. 피드백: 테이블(36) → 상세(37) → 상태 전진(38, SUBMITTED→REVIEWED→ARCHIVED 단방향 — 역방향 버튼 없음)
6. 역할 관리: /admin/roles — user-id(UUID) 직접 입력 + role 선택 → 부여(42)/회수(43)
   가드 표기: 자기 자신 ADMIN 회수·마지막 ADMIN 회수는 409 → 에러 카피로 설명 (ADR-003)
```

---

## 4. API-to-Screen Mapping (43개 전수)

| # | 화면 (액션) | 사용자 역할 | 필요한 API | 주요 표시 필드 | 주의할 접근 제어/민감정보 |
| --- | --- | --- | --- | --- | --- |
| 1 | (화면 소비 없음 — 운영/헬스체크 전용) | — | GET /healthz | — | 프론트에서 호출하지 않음 |
| 2 | 회원가입 (제출) | Anonymous | POST /auth/signup | nickname, email 입력 → 성공 시 홈 | Set-Cookie 자동 로그인. 토큰 표시/저장 UI 없음 |
| 3 | 로그인 (제출) | Anonymous | POST /auth/login | email, password | 403=정지/탈퇴 별도 카피. 실패 시 계정 존재 여부 비암시 |
| 4 | 전역 헤더 (로그아웃) | Authenticated | POST /auth/logout | — | 성공 후 클라이언트 상태 전체 초기화 + 로그인 화면 |
| 5 | 로그인/가입 ("Google로 계속하기") | Anonymous | GET /auth/google/authorize | — | fetch 아님 — 전체 페이지 리다이렉트(302) |
| 6 | (화면 아님 — 콜백 종점, `/`로 302 복귀) | Anonymous | GET /auth/google/callback | — | 409=타 방식 기가입 → 로그인 화면에 안내 카피 |
| 7 | 앱 부트스트랩 + 프로필 조회 | Authenticated | GET /users/me | nickname, email, active_role, roles | `advisor_type` 없음(있어도 표시 금지). 401→로그인 |
| 8 | 프로필 수정 (저장) | Authenticated | PATCH /users/me | nickname, job, interest, profile_image_url | 409=닉네임 중복 인라인 에러 |
| 9 | 부트스트랩 + 역할 스위처 + 신청 상태 배지 | Authenticated | GET /users/me/roles | roles[], active_role, advisor_status | ADMIN은 스위처 항목이 아니라 "관리 콘솔" 진입점으로 |
| 10 | 헤더 역할 스위처 (전환) | Authenticated | PATCH /users/me/active-role | active_role | 403=미보유 역할 → 스위처 자체를 숨겨 사전 차단 |
| 11 | 조언가 신청 폼 (제출) | User | POST /advisor-applications | 폼 8필드 (§5.1 규칙 적용) | intended_lane은 "의향(참고용)"으로만 문구화. 409=진행 중 신청 존재 |
| 12 | 내 신청 상태 | User | GET /advisor-applications/me | status, submitted_at, reject_reason | 404=신청 이력 없음 → empty state 분기. intended_lane 미포함(표시 금지) |
| 13 | [A] 신청 심사 큐 + [A] 배정 화면 조언가 선택기(status=APPROVED 재사용) | Admin | GET /admin/advisor-applications | display_name, status, submitted_at | Admin 전용. 목록엔 intended_lane 없음 |
| 14 | [A] 신청 심사 상세 | Admin | GET /admin/advisor-applications/{id} | 전체 필드 + intended_lane | **intended_lane이 노출되는 유일한 화면**. "최종 판단은 관리자" 문구 병기 |
| 15 | [A] 심사 상세 (검토시작/승인/반려) | Admin | PATCH /admin/advisor-applications/{id} | status, reject_reason | 반려 사유 필수(422). 부수효과(역할 부여+알림) 토스트 고지. 409=종결 상태 재전이 |
| 16 | 고민 작성 인테이크 (제출) | User | POST /users/me/concerns | 단계형 폼 (§3.1) | is_anonymous 기본 ON. 제출 완료 화면에서 기대 설정 |
| 17 | 내 고민 목록 + 홈 현황 카드 | User | GET /users/me/concerns | concern_summary, status, has_approved_advice, created_at | 본인 것만. 소프트 삭제 항목 미표시 |
| 18 | 내 고민 상세 | User | GET /users/me/concerns/{id} | 전체 + approved_advices[] | APPROVED 조언만(§6.2). 배정 조언가 정보 없음(의도). 404=삭제됨 포함 |
| 19 | 고민 상세 (삭제 버튼 → 확인 모달) | User | DELETE /users/me/concerns/{id} | — | 소프트 삭제·기록 보존 고지. 409=이미 삭제 |
| 20 | [V] 배정 고민 목록 (advisor 홈) | Advisor | GET /users/me/assigned-concerns | concern_summary(익명 처리), concern_type, advice_status, assigned_at | active_role=ADVISOR 필수 — 403 시 roles 재조회 |
| 21 | [V] 배정 고민 상세 | Advisor | GET /users/me/assigned-concerns/{id} | 고민 내용, is_anonymous, requester_display_alias, my_advice | 요청자 실명/닉네임 비노출 원칙 (§5.1, §7 C-6) |
| 22 | [A] 전체 고민 테이블 | Admin | GET /admin/concerns | author_user_id, summary, status, is_deleted, assignment_count | include_deleted 토글은 명시적 조작 + 삭제 행 시각 구분 |
| 23 | [A] 고민 상세 (배정 패널 + 조언 현황) | Admin | GET /admin/concerns/{id} | concern 전체, assignments[], advices[](상태 무관) | Admin 전용. 조언 본문은 27로 별도 로드 |
| 24 | [A] 고민 상세 (조언가 배정) | Admin | POST /admin/concerns/{id}/assignments | advisor 선택, triage_decision, priority → concern_status | 409=중복 배정/CLOSED/삭제됨. 배정 알림 발송 고지 |
| 25 | [A] 고민 상세 (배정 해제) | Admin | DELETE …/assignments/{assignment-id} | — | 전 배정 해제 시 SUBMITTED 복귀를 UI에 반영 |
| 26 | 받은 조언함 | User | GET /users/me/advices | concern_summary, advisor_display_name, is_feedback_submitted | APPROVED만 서버 필터 — "검토 중 조언" 노출·암시 금지 |
| 27 | 조언 상세 (User 열람 / [V] 내 조언 / [A] 리뷰 본문) | Mixed | GET /advices/{id} | directional_guidance, reflective_questions, considerations, status, version | 역할별 3중 소비. User에겐 status 뱃지 숨김(항상 APPROVED). 403 처리 필수 |
| 28 | [V] 배정 상세 (조언 작성: 임시저장/제출) | Advisor | POST /concerns/{id}/advices | 폼 3필드 + out_of_scope_flag + submit | 403=미배정. 409=이미 작성 → 기존 조언으로 이동 |
| 29 | [V] 조언 수정 (저장) | Advisor(작성자) | PATCH /advices/{id} | version, updated_at | PENDING/REVIEWING만. version+1 사전 고지 |
| 30 | [V] 조언 삭제 (확인 모달) | Advisor(작성자) | DELETE /advices/{id} | — | 409=APPROVED 후 삭제 불가 → 버튼 자체 숨김 |
| 31 | [V] 내가 작성한 조언 목록 | Advisor | GET /users/me/advices-written | advice_id, concern_id, status, version | 상태 무관 — REJECTED도 본인에게는 표시 |
| 32 | [A] 조언 리뷰 큐 | Admin | GET /admin/advices | advice_id, concern_id, status, version | 기본 필터 PENDING. 본문 없음 — 상세는 27 |
| 33 | [A] 리뷰 상세 (승인/반려) | Admin | PATCH /admin/advices/{id}/review | decision, reason → concern_status | 반려 사유 필수(422). 412=버전 충돌 → 재조회 유도 (§7 C-3) |
| 34 | 조언 상세 (피드백 작성) | User(고민 작성자) | POST /advices/{id}/feedbacks | score 1~5, content | 1회 제한·수정 불가 **사전** 고지. 409=이미 작성 |
| 35 | 내 피드백 목록 | User | GET /users/me/feedbacks | score, content, status, created_at | status는 내부 운영값 — 사용자에겐 뱃지 미표시 권장 |
| 36 | [A] 피드백 테이블 | Admin | GET /admin/feedbacks | score, status, advisor/author id | Admin 전용 |
| 37 | [A] 피드백 상세 | Admin | GET /admin/feedbacks/{id} | content, author_nickname, memo | author_nickname은 Admin 화면 한정 |
| 38 | [A] 피드백 상세 (상태 변경/메모) | Admin | PATCH /admin/feedbacks/{id} | status, memo | 단방향 전이 — 역방향 버튼 미제공 |
| 39 | 알림 목록 + 헤더 벨 배지 | Authenticated | GET /notifications | items[], unread_count | 배지는 이 응답의 unread_count 사용(별도 카운트 API 없음) |
| 40 | 알림 상세 (선택적 — 주 경로는 목록에서 바로 이동) | Authenticated(수신자) | GET /notifications/{id} | title, message, target_url, actor | actor.display_name만 — user_id를 UI에 노출하지 않음 |
| 41 | 알림 클릭 (읽음 처리 후 target_url 이동) | Authenticated(수신자) | PATCH /notifications/{id}/read | is_read, read_at | 개별 처리만 존재 — "모두 읽음" 버튼 불가 (§8-6) |
| 42 | [A] 역할 관리 (부여) | Admin | POST /admin/users/{user-id}/roles | role, reason | user-id 직접 입력(검색 API 없음 — §7 C-9). 409=이미 보유 |
| 43 | [A] 역할 관리 (회수) | Admin | DELETE …/roles/{role} | — | 409 3종(자기 ADMIN/마지막 ADMIN/미보유)을 각각 카피로 구분 |

[V]=Advisor 컨텍스트, [A]=관리 콘솔. **화면에서 소비되지 않는 엔드포인트: #1(/healthz) 1건** — 운영 전용. #6은 브라우저 리다이렉트 종점으로 fetch 소비 없음.

---

## 5. 프라이버시-우선 UI 규칙 + 컴포넌트/상태 설계

### 5.1 민감 필드 비노출 규칙 (CLAUDE.md §6.1 → 화면 규칙 번역)

1. **`advisor_type` — 어떤 화면에도 존재하지 않는다.** API 7 응답에 없으므로 렌더링 근거 자체가 없음. "전문가/시니어" 등급 뱃지를 조언가·조언에 붙이지 않는다.
2. **`intended_lane` — 관리자 심사 상세(#14) 단일 화면 한정.** 신청 폼(#11)에서는 "어느 쪽에 가깝다고 생각하시나요?(참고용)"으로 묻고, "이 선택은 자격 등급이 아니며 다른 사용자에게 공개되지 않습니다" 마이크로카피를 필드 바로 아래 배치. 내 신청 상태(#12)에서도 미표시(응답에 없음).
3. **`real_name` — 신청 폼에 필드 자체가 없다.** 폼에 실명 입력을 추가하지 않는다. 조언가 공개 표시명은 `display_name` 하나뿐.
4. **APPROVED만 사용자 노출(§6.2).** 받은 조언함(#26)·고민 상세(#18)는 서버가 이미 필터하지만, 클라이언트도 "검토 중인 조언 N건" 같은 **존재 암시 카운트를 만들지 않는다**(has_approved_advice bool만 사용). 사용자 화면에서 조언 status 뱃지는 렌더링하지 않는다(항상 APPROVED이므로 무의미 + 검토 파이프라인 노출 방지).
5. **익명 표시.** 조언가 화면(#20, #21)에서 요청자는 `requester_display_alias`로만 표시. alias 공백 시 폴백은 "익명의 요청자"(잠정 — §7 C-7). 요청자 email/nickname/user_id는 조언가 화면에 절대 렌더링하지 않는다. 사용자 화면에서도 배정 전까지 조언가 신원을 보여주지 않으며(#18 응답에 배정 정보 없음 — 의도), 조언 도착 후에야 `advisor_display_name`이 보인다.
6. **관리자 화면 격리.** author_user_id·author_nickname·intended_lane 등은 `/admin/*` 라우트에서만 렌더링하고, 공용 컴포넌트(조언 카드 등)를 admin에 재사용할 때 admin 전용 필드를 props 기본값으로 끄는 계약을 명시한다.

### 5.2 세션/CSRF 프론트 계약 (ADR-002 → 구현 가능한 규칙)

- 모든 fetch는 `credentials: "include"` (HttpOnly `sessionid`는 JS에서 읽지 않고 읽을 수도 없음).
- 상태 변경(POST/PATCH/DELETE)은 `document.cookie`의 `csrftoken`을 읽어 `X-CSRFToken` 헤더로 전송 (csrftoken은 non-HttpOnly — ADR-002 §5).
- 부트스트랩: 앱 로드 시 GET #7 → 200이면 로그인 상태, 401이면 비로그인 분기. **주의: 비로그인 최초 POST(login/signup) 전에 csrftoken 쿠키를 획득할 명세상 경로가 없다 — §7 C-8.**
- 전역 응답 인터셉터: 401 → 클라이언트 상태 초기화 + 로그인 화면(복귀 경로 보존) / 403(advisor 라우트) → #9 재조회 후 역할 컨텍스트 복구 / CSRF 실패(403) → csrftoken 재획득 후 1회 재시도.
- 로그아웃(#4) 성공 시 서버가 쿠키를 만료시키므로 클라이언트는 메모리 상태만 비운다(쿠키 직접 삭제에 의존하지 않음).

### 5.3 공통 컴포넌트/상태

| 컴포넌트 | 계약 |
| --- | --- |
| AppShell + RoleSwitcher | roles[](#9) 기반 조건부 렌더. ADVISOR 미보유 시 스위처 숨김, ADMIN 보유 시 "관리 콘솔" 링크 |
| StatusBadge | 상태 enum → 한국어 라벨 1:1 사전. 상태값 자체(SUBMITTED 등)는 admin 화면에서 병기, 사용자 화면에선 한국어만 |
| StateFrame | 화면당 6상태 필수: loading(스켈레톤) / empty(구조화된 빈 상태 — 다음 행동 1개 제시) / error(재시도) / 401 / 403 / success. 409·422는 인라인 필드/배너로 |
| PendingReviewBanner | "검토 대기" 공통 배너 (조언가 신청 #12, 조언 제출 후 #21) — 기한 약속 없이 절차만 설명 |
| ConfirmModal(destructive) | 삭제(#19, #30)·피드백 제출(#34, 비가역) 전용. 비가역성 명시 카피 필수 |
| NotificationBell | #39 폴링(간격은 구현 시 결정). unread_count 배지. 클릭 항목 → #41 → target_url 라우팅 |
| Paginator | page_info 규격(api.md §1.4) 공통 소비. size 기본 20 |

접근성: 모든 상태 뱃지는 색상 외 텍스트 병기, 폼 에러는 aria-describedby 연결, 모달 포커스 트랩, 키보드로 역할 스위처 조작 가능.

---

## 6. 한국어 마이크로카피 후보 (민감 지점)

| 지점 | 후보 카피 |
| --- | --- |
| 고민 작성 진입 | "이 고민은 회원님과 연결된 조언가, 그리고 검토 담당자만 볼 수 있습니다. 공개 게시판이 아닙니다." |
| 익명 설정(기본 ON) | "기본적으로 익명으로 전달됩니다. 원하시면 별칭을 정할 수 있어요." |
| 고민 제출 완료 | "고민이 안전하게 접수되었습니다. 담당자가 내용을 확인한 뒤 어울리는 조언가를 연결해 드려요. 연결되면 알림으로 알려드립니다." |
| 조언 열람 상단 고지 | "조언은 정답이 아니라 방향을 함께 고민한 기록입니다. 최종 결정은 언제나 회원님의 몫이에요." |
| intended_lane 필드(신청 폼) | "본인의 조언 방향에 가까운 쪽을 골라주세요(참고용). 이 선택은 자격 등급이 아니며, 다른 사용자에게 공개되지 않습니다. 최종 구분은 검토 과정에서 정해집니다." |
| 신청 검토 대기(#12) | "신청서를 검토하고 있어요. 결과는 알림으로 알려드립니다." |
| 신청 반려(#12) | "이번 신청은 함께하지 못하게 되었어요. 사유: {reject_reason}. 보완 후 다시 신청하실 수 있습니다." |
| 조언 제출 후(조언가) | "제출된 조언은 검토를 거쳐 요청자에게 전달됩니다. 검토 중에는 수정할 수 있어요." |
| 조언 반려(조언가) | "이 조언은 전달되지 않았어요. 내용을 다듬어 다시 제출할 수 있습니다." |
| 고민 삭제 모달 | "이 고민을 삭제할까요? 목록에서 사라지지만, 이미 전달된 조언 기록은 시스템에 보존됩니다. 이 작업은 되돌릴 수 없어요." |
| 피드백 제출 모달 | "피드백은 조언 1건당 한 번만 남길 수 있고, 제출 후에는 수정하거나 삭제할 수 없어요. 지금 제출할까요?" |
| 로그인 403(정지/탈퇴) | "이 계정은 현재 이용이 제한된 상태입니다. 문의가 필요하시면 알려주세요." |
| 역할 회수 후 403(조언가 화면) | "조언가 화면에 접근할 수 없는 상태예요. 역할 정보가 갱신되었을 수 있어 확인 중입니다." |

---

## 7. 정합성 검증 — 충돌/미해결 표 (창작으로 메우지 않은 지점)

| # | 위치 | 내용 | 우선순위 판단(CLAUDE.md §2) / 처리 | 태그 |
| --- | --- | --- | --- | --- |
| C-1 | api.md #16/#18/#19/#22 vs CLAUDE.md §6.6·model.md §1.4 | api.md가 `is_deleted` boolean 표현을 사용하나 저장 컨벤션은 `deleted_at` timestamp | CLAUDE.md 우선 — 응답 `is_deleted`는 파생 bool로 해석. api.md 표기 정리 권장 | 문서 drift |
| C-2 | api.md OQ-5, model.md O-3 | Concern `ANSWERED→CLOSED` 사용자 트리거 API 없음 vs CLAUDE.md §6.6 "user closes explicitly" | 화면은 CLOSED를 표시 전용으로 설계(닫기 버튼 없음) → Owner 결정 필요 | Owner 결정 |
| C-3 | api.md #33 | 412(version mismatch)가 명세됐으나 요청에 기대 버전 필드가 없음 | 요청에 `expected_version` 추가 검토 | API 개선 |
| C-4 | api.md #21/#27/#31 | `is_submitted`(draft 여부)가 응답에 없어 "임시저장/제출됨" 구분 표시 불가 | 응답에 is_submitted 노출 필요 | API 개선 |
| C-5 | api.md #27 | `reject_reason`이 응답에 없음 — 조언가가 반려 사유를 알림으로만 확인 | 작성자 한정 조건부 노출 검토 | API 개선 |
| C-6 | api.md #21 | `is_anonymous=false` 고민의 조언가측 요청자 표시명 미정 | 모델 대조로도 해소 안 됨 | **data-modeler 검증 필요** + Owner 결정 |
| C-7 | model.md §3.6 | `display_alias` 기본 "" + 익명일 때 폴백 표시명 미정 | 잠정 폴백 "익명의 요청자" — 서버/클라 책임 확정 필요 | Owner 결정 |
| C-8 | ADR-002 §5, api.md §1.2 | 비로그인 최초 POST 전에 csrftoken 쿠키를 발급받는 명세상 경로 없음 | M4에서 ensure_csrf_cookie 적용 또는 전용 GET — 신규 엔드포인트는 §16 게이트 | API 개선 + Owner 결정 |
| C-9 | api.md #42/#43 | 역할 부여에 user-id(UUID) 필요하나 관리자용 사용자 검색 API 없음 | Phase 2: Django Admin에서 UUID 확인 → UUID 직접 입력 필드로 설계 | 설계로 흡수(개선 후보) |
| C-10 | api.md OQ-6, model.md O-6 | 알림 `target_url` 상대 경로 ↔ 프론트 라우트 규약 미확정 | 본 명세는 "프론트 라우트 키"로 가정 — 규약 확정 필요 | Owner 결정 |
| C-11 | api.md OQ-8 | Google 첫 가입 닉네임 자동 산정 → 온보딩 확인 화면 여부 미정 | 화면 옵션만 제시 | Owner 결정 |
| C-12 | docs/2 mvp-scope_v1.md flow 2 vs api.md #20 | mvp-scope는 "조언가가 고민 목록 확인"으로 읽히나 API는 배정된 고민만 조회 | CLAUDE.md §5 + api.md 우선 — 배정 목록으로 확정 | 문서 drift |
| C-13 | CLAUDE.md §2/§17 파일명 | `docs/2 mvp-scope.md`·`docs/0 README.md` 참조 vs 실제 `docs/2 mvp-scope_v1.md`·`docs/README.md` | 참조 정리만 필요 | 문서 drift |

---

## 8. API 개선 필요점 (M4 구현 전 고치면 싼 것)

우선순위순. §16 승인 게이트 대상 여부 병기.

1. **CSRF 부트스트랩 경로 확정** (C-8) — 없으면 로그인/가입 자체가 막힌다. 기존 GET에 `ensure_csrf_cookie`면 신규 엔드포인트 없이 해결. [게이트: 신규 엔드포인트 선택 시만]
2. **#21/#27/#31 응답에 `is_submitted` 노출** (C-4) — draft 기능이 화면에서 표현 불가능해지는 것 방지. [저비용]
3. **#27 응답에 작성자 한정 `reject_reason` 조건부 노출** (C-5). [저비용]
4. **#33 요청에 `expected_version` 추가** (C-3) — 명세된 412가 실제로 동작하려면 필수. [저비용]
5. **#18 응답에 `display_alias` 포함** — 사용자가 자신의 별칭을 확인할 수단이 전무. [저비용]
6. **알림 일괄 읽음(read-all)** — 개별 처리 루프 호출은 안티패턴. [게이트: 신규 엔드포인트]
7. **api.md `is_deleted` 표기를 `deleted_at` 파생 필드로 명시 정리** (C-1). [문서만]
8. **#12의 404-as-empty 시맨틱 유지 여부 재확인** — 유지 시 에러 모니터링 제외 규칙만 문서화.

---

## 9. Phase 2에서 하지 말아야 할 UI (Phase 경계)

근거 API/필드가 없는 화면 요소는 만들지 않는다.

- **금지**: 공개 조언가 마켓플레이스/디렉터리, 조언가 랭킹·평점 공개, trust score 뱃지/그래프, 조언가 프로필 공개 페이지, 타인 고민 열람 피드, 결제/구독 UI, AI 추천·자동 매칭 UI, advisor_type/등급 뱃지, "검증된 해답" 류 카피, 실명 요구 필드.
- **유예(공간만 예약, "준비 중" 노출 금지)**: outcome tracking — 고민 상세 타임라인이 향후 outcome 이벤트를 수용 가능한 구조로만. trust score — 어떤 집계 UI도 만들지 않음. 신청 철회(WITHDRAWN) — 라벨 사전에만 존재, 버튼 없음. 계정 탈퇴/정지 — 화면 없음.
- 알림 자동 푸시(WebSocket/SSE) 없음 — 벨 배지는 폴링 기반.

---

## 10. Owner 결정 필요 사항 (M4 구현 전 최소 질문)

1. **CLOSED 전이** (C-2): 사용자 "고민 마무리" 버튼용 API를 추가할지, Phase 2는 표시 전용으로 확정할지.
2. **CSRF 부트스트랩 방식** (C-8): 기존 GET에 ensure_csrf_cookie vs 전용 엔드포인트.
3. **비익명 고민의 조언가측 표시명 정책** (C-6) + 익명 alias 공백 폴백의 서버/클라 책임 (C-7).
4. **알림 target_url ↔ 프론트 라우트 규약** (C-10): 본 명세의 라우트 제안(§2)을 규약 기준으로 채택하는가.
5. **Google 첫 가입 닉네임 확인 온보딩** (C-11): 둘지, 자동 부여 후 프로필 수정(#8)으로 갈음할지.
