# STATUS — chamneul 프로젝트 현황판

> 이 파일은 **Git이 유일한 source of truth**라는 원칙(ADR-006)의 실행판이다. 실제 코드(`config/urls.py`, 각 앱 `views.py`)를 읽고 사실로만 채운다 — 추측·계획 값은 적지 않는다. **구현 커밋에는 이 파일 갱신이 반드시 동반된다.**
> 마지막 실측: 2026-09-12 (SPEC-002/TASK-005 커밋 기준. 이전 실측 2026-09-11 TASK-001~004 / 2026-09-10 SPEC-001 종료)

---

## 1. Phase / 마일스톤

| 항목 | 값 |
| --- | --- |
| Phase | Phase 2 — 로컬 컨테이너 MVP |
| 현재 마일스톤 | M4 — api.md v1.1의 44개 엔드포인트 구현 (8모듈) |
| M4 진행률 | M4-5 완료 + M4-6 진행 중(advice 10/13), **36/44 엔드포인트** |
| 다음 마일스톤 | M5 — 스모크 테스트 + 문서 정리 → Phase 2 종료 |

| MS | 내용 | 상태 |
| --- | --- | --- |
| M1 | 스켈레톤 (config/accounts/common, custom User+uuid7, /healthz, compose) | 완료 |
| M2 | 런타임 승격 [소유] Dockerfile 멀티스테이지·비루트·gunicorn + [위임] accounts 역할 모델 3종 | 완료 |
| M3 | 도메인 모델 7종 + 마이그레이션 + Admin | 완료 (리뷰 노트 미작성 — 부채 #4) |
| M4 | api.md v1.1의 44개 엔드포인트 구현 (8모듈) | 진행 중 |
| M5 | 스모크 테스트 + 문서 정리 | 미착수 |

---

## 2. 구현된 엔드포인트 (36 / 44)

실측 근거: [config/urls.py](../../config/urls.py) — `accounts.urls`, `advisors.urls`, `concerns.urls`, `advice.urls` 4개 include.

| # | Method | Endpoint | 구현 파일 |
| --- | --- | --- | --- |
| 1 | GET | `/healthz` | [config/health.py](../../config/health.py) |
| 2 | POST | `/api/v1/auth/signup` | [accounts/views.py](../../accounts/views.py) `SignupView` |
| 3 | POST | `/api/v1/auth/login` | `LoginView` |
| 4 | POST | `/api/v1/auth/logout` | `LogoutView` |
| 5 | GET | `/api/v1/auth/google/authorize` | `GoogleAuthorizeView` |
| 6 | GET | `/api/v1/auth/google/callback` | `GoogleCallbackView` |
| 7 | GET | `/api/v1/users/me` | `UserMeView` |
| 8 | PATCH | `/api/v1/users/me` | `UserMeView` |
| 9 | GET | `/api/v1/users/me/roles` | `UserRolesView` |
| 10 | PATCH | `/api/v1/users/me/active-role` | `ActiveRoleView` |
| 11 | POST | `/api/v1/advisor-applications` | [advisors/views.py](../../advisors/views.py) `AdvisorApplicationView` |
| 12 | GET | `/api/v1/advisor-applications/me` | `AdvisorApplicationMeView` |
| 13 | GET | `/api/v1/admin/advisor-applications` | `AdminAdvisorApplicationListView` |
| 14 | GET | `/api/v1/admin/advisor-applications/{application-id}` | `AdminAdvisorApplicationDetailView.get` |
| 15 | PATCH | `/api/v1/admin/advisor-applications/{application-id}` | `AdminAdvisorApplicationDetailView.patch` |
| 16 | POST | `/api/v1/users/me/concerns` | [concerns/views.py](../../concerns/views.py) `ConcernListCreateView.post` (SPEC-001/TASK-001) |
| 17 | GET | `/api/v1/users/me/concerns` | `ConcernListCreateView.get` (SPEC-001/TASK-001) |
| 18 | GET | `/api/v1/users/me/concerns/{concern-id}` | `ConcernDetailView.get` (SPEC-001/TASK-002) |
| 19 | DELETE | `/api/v1/users/me/concerns/{concern-id}` | `ConcernDetailView.delete` (SPEC-001/TASK-002) |
| 20 | GET | `/api/v1/users/me/assigned-concerns` | `AssignedConcernListView.get` (SPEC-001/TASK-003) |
| 21 | GET | `/api/v1/users/me/assigned-concerns/{concern-id}` | `AssignedConcernDetailView.get` (SPEC-001/TASK-003) |
| 22 | GET | `/api/v1/admin/concerns` | `AdminConcernListView.get` (SPEC-001/TASK-004) |
| 23 | GET | `/api/v1/admin/concerns/{concern-id}` | `AdminConcernDetailView.get` (SPEC-001/TASK-004) |
| 24 | POST | `/api/v1/admin/concerns/{concern-id}/assignments` | `AdminAssignmentCreateView.post` (SPEC-001/TASK-005) |
| 25 | DELETE | `/api/v1/admin/concerns/{concern-id}/assignments/{assignment-id}` | `AdminAssignmentDetailView.delete` (SPEC-001/TASK-005) |
| 28 | POST | `/api/v1/concerns/{concern-id}/advices` | [advice/views.py](../../advice/views.py) `AdviceCreateView.post` (SPEC-002/TASK-001) |
| 31 | GET | `/api/v1/users/me/advices-written` | `AdvicesWrittenView.get` (SPEC-002/TASK-001) |
| 27 | GET | `/api/v1/advices/{advice-id}` | `AdviceDetailView.get` (SPEC-002/TASK-002) |
| 29 | PATCH | `/api/v1/advices/{advice-id}` | `AdviceDetailView.patch` (SPEC-002/TASK-003) |
| 30 | DELETE | `/api/v1/advices/{advice-id}` | `AdviceDetailView.delete` (SPEC-002/TASK-003) |
| 32 | GET | `/api/v1/admin/advices` | `AdminAdviceListView.get` (SPEC-002/TASK-004) |
| 33 | PATCH | `/api/v1/admin/advices/{advice-id}/review` | `AdminAdviceReviewView.patch` (SPEC-002/TASK-004) |
| 26 | GET | `/api/v1/users/me/advices` | `ReceivedAdviceListView.get` (SPEC-002/TASK-005) |
| 34 | POST | `/api/v1/advices/{advice-id}/feedbacks` | `FeedbackCreateView.post` (SPEC-002/TASK-005) |
| 35 | GET | `/api/v1/users/me/feedbacks` | `MyFeedbackListView.get` (SPEC-002/TASK-005) |
| 44 | GET | `/api/v1/csrf` | [accounts/views.py](../../accounts/views.py) `CsrfView` |

## 3. 미구현 엔드포인트 (8 / 44)

`notifications` 앱은 `models.py`·`admin.py`·마이그레이션만 존재하고 views/serializers/urls/services 파일이 아직 없다. `concerns`(#16~25)는 전량 구현 완료, `advice`는 #28·#31만 구현됨(실측: `git ls-files`, `config/urls.py`).

| 모듈 | 엔드포인트 | api.md 절 |
| --- | --- | --- |
| M4-6 advice + feedback (남은 3개) | #36·#37·#38 (전부 admin 피드백) | §4-36~38 |
| M4-7 notifications | #39~41 (3개) | §4-39~41 |
| M4-8 admin roles | #42~43 (2개) | §4-42~43 |

## 4. Active SPEC

**SPEC-002-advice-api** (`specs/SPEC-002-advice-api/`) — api.md #26~38 (M4-6 advice + feedback) 13개 엔드포인트. **Status: Approved** — spec.md §7의 Owner 결정 4건 확정(2026-09-11, 전부 권고안 채택). 브랜치 `feat/spec-002-advice-api`.

확정된 §7 결정:

1. 관리자 리뷰 목록(#32)에서 **초안(`is_submitted=False`) 항상 제외**, #33도 초안 리뷰를 409로 거부.
2. `submit` 토글만 바뀌면 `version` **증가하지 않음**(본문 변경 시에만 +1, §6.7).
3. 승인 시 concern 전이는 **`ASSIGNED`일 때만** — `CLOSED`/`ANSWERED`는 불변(§6.6에 CLOSED→ANSWERED 간선 없음).
4. #27에서 고민 작성자가 비-APPROVED advice 조회 시 **403**(api.md 문언 유지, #18의 404와 비대칭임을 인지).

* [x] TASK-001 — 조언 작성(#28) + 내가 쓴 조언 목록(#31). 공용 `AdviceTestBase`로 fixture 1곳 집약, `IsActiveAdvisor` 재사용, 부분 유니크(DELETED 제외) 덕에 삭제 후 재작성 허용 확인. 테스트 18종(선-실패 16개 확인) → 검증 4종 통과(**80/80**) → 스크린샷 3장 확인 → 커밋.
* [x] TASK-002 — 조언 상세(#27) 3주체 분기. `get_visible_advice()`가 (작성자/관리자/고민 작성자) 우선순위로 판정 — ADMIN이 판정 순서상 고민 작성자보다 먼저 걸린다는 점을 데모 중 실측(같은 계정이 admin+owner를 겸하면 admin 시야로 응답됨, 버그 아님). `AdviceDetailSerializer`/`AdviceDetailWithReasonSerializer` 2종(상속)으로 `reject_reason` 유무만 분리. 테스트 11종(선-실패 10개 확인) → 검증 4종 통과(**91/91**) → 순수 사용자 계정으로 재현한 스크린샷 3장 확인 → 커밋.
* [x] TASK-003 — 조언 수정(#29) + 삭제(#30). `_get_own_editable_advice()`로 조회·소유권(403)·편집가능상태(409, PENDING/REVIEWING만) 공용 검사. `version`·`AdviceHistory`는 본문 필드 변경 시에만 갱신(§7-2 결정) — `submit` 단독 토글은 건드리지 않음. PATCH/DELETE만 `IsActiveAdvisor` 추가 게이트(GET은 제외, `get_permissions()`로 메서드별 분기). 테스트 17종(선-실패 15개 확인) → 검증 4종 통과(**108/108**) → 스크린샷 2장 + `AdviceHistory` DB 직접 확인(수정 전 본문이 정확히 v1로 보존) → 커밋.
* [x] TASK-004 — admin 리뷰 목록(#32) + 승인/반려(#33) ★ 핵심. `list_advices_for_admin_review()`가 `is_submitted=True`를 무조건 강제(§7-1 결정, status 필터 유무와 무관). `review_advice()`가 **한 트랜잭션**으로 advice 전이 + concern 전이(ASSIGNED일 때만, §7-3) + `Notification` 처리 — advice·concern 모두 `select_for_update()`. 체크 순서: 404→409(초안/상태)→412(버전 불일치)→422(반려 사유). `common/exceptions.py`에 `PreconditionFailed`(412) 신규 추가. 테스트 17종(선-실패 14개 확인, 1건은 `assertNumQueries` 기대값 실측 보정) → 검증 4종 통과(**125/125**) → 스크린샷 3장(대기열/412/승인+ANSWERED 전이) + DB로 알림 확인 → 커밋.
* [x] TASK-005 — 받은 조언 목록(#26) + 피드백 작성(#34)/내 목록(#35). §6.2 노출 규칙이 `filter(concern__author=user, status=APPROVED)` 한 쌍으로 끝나도록 서비스에 집약. `advisor_display_name`은 페이지 단위 벌크 조회를 serializer context로 주입(단건 경로인 #27과 달리 목록이라 N+1 방지 필요). 피드백 1회 제한은 `Feedback.advice` OneToOne이 실제 강제 → IntegrityError를 409로 변환. 테스트 18종(선-실패 15개 확인) → 검증 4종 통과(**143/143**) → 스크린샷 5장 확인 → 커밋.
* [ ] **다음 최소 작업 단위**: TASK-006 — admin 피드백 목록/상세/상태 변경(#36·#37·#38).

<details>
<summary>SPEC-001-concerns-api — 완료 (2026-09-10, PR #2 머지)</summary>

api.md #16~25 (M4-5 concerns) 10개 엔드포인트 전량 구현, AC-1~AC-10 전항 통과, 테스트 62개.

* [x] TASK-001 — `POST /api/v1/users/me/concerns` (#16) + `GET /api/v1/users/me/concerns` (#17). 테스트 8종 작성(선-실패 확인) → 구현(`concerns/{serializers,services,views,urls}.py`) → `check`/`makemigrations --check`/`ruff`/`test` 전부 통과 → DRF Browsable API로 로그인→생성→목록 확인(스크린샷) → 커밋.
* [x] TASK-002 — `GET /api/v1/users/me/concerns/{concern-id}` (#18, `approved_advices[]` 포함) + `DELETE .../{concern-id}` (#19, soft delete). 테스트 8종 추가(선-실패 확인) → 구현(`ConcernDetailSerializer`, `ConcernDetailView`, `get_own_concern`/`get_own_concern_including_deleted`/`soft_delete_concern`/`approved_advices_view_data` 서비스) → 검증 4종 통과 → 스크린샷으로 상세/삭제/재조회 404 확인 → 커밋.
* [x] TASK-003 — `GET /api/v1/users/me/assigned-concerns` (#20) + `GET .../assigned-concerns/{concern-id}` (#21). `IsActiveAdvisor` 권한 클래스(`common/permissions.py`) 신설: `active_role=ADVISOR`일 때만 통과 — 역할 보유만으로는 403. #21은 존재 자체를 숨기지 않음(배정 안 됨=403, 미존재=404 — #18과 다른 정책, api.md 문언 그대로). 테스트 14종 추가(선-실패 확인, 한 번에 전부 통과) → 검증 4종 통과 → 스크린샷 3장(목록/상세/404) 확인 → 커밋.
* [x] TASK-004 — admin 조회 `GET /api/v1/admin/concerns` (#22) + `GET .../concerns/{concern-id}` (#23). `include_deleted`/`status`/`keyword` 필터, `assignment_count`(활성 배정만), `is_deleted` 파생 필드. #23은 soft-deleted concern도 조회 가능(감사 경로) + assignments/advices 상태 무관 전량 노출(§6.2는 고민 작성자 보호용이지 admin 제한이 아님). 테스트 12종 추가(선-실패 11개 확인) → 검증 4종 통과(`assertNumQueries(5)`로 N+1 부재 고정) → 스크린샷 3장 확인 → 커밋.
* [x] TASK-005 — 배정 생성 `POST .../concerns/{concern-id}/assignments` (#24) + 해제 `DELETE .../assignments/{assignment-id}` (#25). `assign_advisor`/`unassign_advisor` 서비스가 **한 트랜잭션**으로 Assignment row + 상태 전이(SUBMITTED→ASSIGNED / 마지막 해제 시 ASSIGNED→SUBMITTED) + `ASSIGNMENT_CREATED` 알림을 함께 처리(§6.4/§6.6). concern row에 `select_for_update()`로 동시 배정/해제 직렬화. 비-advisor 지정은 422, 중복 활성 배정·CLOSED/삭제 concern·이미 해제된 배정은 409. 테스트 18종 추가(선-실패 14개 확인) → 검증 4종 통과(전체 60/60) → 스크린샷 4장(배정 전/201/조언가 큐/해제 후 복귀) 확인 → 커밋.
* [x] TASK-006 마무리 — #20 `status` 필터 구현(Owner 승인안: `concern.status` 기준), api.md 문구 정정 2건(#20 "assignment 상태"→"concern 상태", #16·#18·#19·#24의 `is_deleted` 상태 서술→`deleted_at`), AC-1~AC-10 전항 대조 후 미커버 2건 보강(AC-4 Assignment 보존 단언, #20 목록 `assertNumQueries`), 검증 4종 통과(**62/62**).

</details>

## 5. 미결 Owner 결정

| # | 항목 | 상태 |
| --- | --- | --- |
| D-4 | Concern `ANSWERED → CLOSED` 사용자 API 도입 여부 | 미결 (권고: Phase 2는 Admin으로만 종료 처리, 신규 API 없음) |
| D-6 | `domain_category`(advisor) 11종 확정 여부 | 확정됨(2026-07-08 D-6) — model.md §11에서 재확인 필요 |
| 신규 (2026-09-10 TASK-003) | api.md #20의 query param `status?`("assignment 상태")가 `Assignment` 모델의 실제 필드와 불일치 | **종결됨** — Owner 승인(후보 B: `concern.status` 필터로 재해석) 후 TASK-006에서 구현 + api.md 문구 정정 완료. |
| ADR-006 | AI-Native/Spec-Driven 스켈레톤 전환 | **Accepted (2026-09-10)** — CLAUDE.md §2/§3/§5/§9~§13/§16/§17 개정 적용 완료 |
| 모순 #6 (2026-09-09 부트스트랩) | api.md #16·#19·#22가 여전히 `is_deleted` 표기, 모델은 `deleted_at` | **종결됨** — 해석 승인(파생 응답 필드) 후 TASK-006에서 api.md 정정 완료: 상태 서술은 `deleted_at`, `is_deleted`는 #22 응답 필드로만 사용 |
| 모순 #7 (2026-09-09 부트스트랩) | #16~19(사용자 concern CRUD)에 `active_role` 게이팅 여부 불명확 | 해석 승인됨(2026-09-09): 게이트 없음(자기 고민은 역할 무관) |

## 6. 학습 부채 (14건, 누적)

| 구분 | 건수 | 내용 |
| --- | --- | --- |
| M2 | 9건 | 401/403/409, `@transaction.atomic` 최우선 재검증 |
| M3 | 2건 | 부분 유니크 "종결 ≠ 비활성" 경계, `with_deleted()` 호출 vs 제약 문법 |
| 이월 게이트 | 3건 | 드릴 #2(마이그레이션 실패)·#3(env 오타), WB-1 백지 재현, M3 퀴즈 |

처리 시점: M4 완료 후 일괄 (`docs/reviews/04-milestone4-definition.md` §0).

## 7. 문서 부채

| # | 항목 | 상태 |
| --- | --- | --- |
| 1 | README_AIUSAGE.md에 M4-1~M4-4 미기록 | 미해소 |
| 2 | 리뷰 노트 미작성: `03-milestone3-review.md`, `04-milestone4-review.md` | 미해소 |
| 3 | model.md 문서 drift 6건 미반영 | 미해소 |
| 4 | root/docs 이중 `README_AIUSAGE.md` | **2026-09-09 부트스트랩에서 병합·정리** |

## 8. 참조

* 계획 문서(착수 시점 스냅샷, 낡을 수 있음): [docs/reviews/04-milestone4-definition.md](../reviews/04-milestone4-definition.md)
* API 계약: [docs/api.md](../api.md)
* 도메인 규칙: [CLAUDE.md](../../CLAUDE.md) §6
* 구조 전환 근거: [docs/adr/ADR-006-ai-native-spec-driven-skeleton.md](../adr/ADR-006-ai-native-spec-driven-skeleton.md)
