# STATUS — chamneul 프로젝트 현황판

> 이 파일은 **Git이 유일한 source of truth**라는 원칙(ADR-006)의 실행판이다. 실제 코드(`config/urls.py`, 각 앱 `views.py`)를 읽고 사실로만 채운다 — 추측·계획 값은 적지 않는다. **구현 커밋에는 이 파일 갱신이 반드시 동반된다.**
> 마지막 실측: 2026-09-10 (SPEC-001/TASK-004 커밋 기준, 이전 실측 2026-09-10 TASK-001~003 / 2026-09-09 `b2eaf90`)

---

## 1. Phase / 마일스톤

| 항목 | 값 |
| --- | --- |
| Phase | Phase 2 — 로컬 컨테이너 MVP |
| 현재 마일스톤 | M4 — api.md v1.1의 44개 엔드포인트 구현 (8모듈) |
| M4 진행률 | 4/8 모듈 진행 중(M4-5 concerns 8/10), **24/44 엔드포인트** |
| 다음 마일스톤 | M5 — 스모크 테스트 + 문서 정리 → Phase 2 종료 |

| MS | 내용 | 상태 |
| --- | --- | --- |
| M1 | 스켈레톤 (config/accounts/common, custom User+uuid7, /healthz, compose) | 완료 |
| M2 | 런타임 승격 [소유] Dockerfile 멀티스테이지·비루트·gunicorn + [위임] accounts 역할 모델 3종 | 완료 |
| M3 | 도메인 모델 7종 + 마이그레이션 + Admin | 완료 (리뷰 노트 미작성 — 부채 #4) |
| M4 | api.md v1.1의 44개 엔드포인트 구현 (8모듈) | 진행 중 |
| M5 | 스모크 테스트 + 문서 정리 | 미착수 |

---

## 2. 구현된 엔드포인트 (24 / 44)

실측 근거: [config/urls.py](../../config/urls.py) — `accounts.urls`, `advisors.urls`, `concerns.urls` 3개 include.

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
| 44 | GET | `/api/v1/csrf` | [accounts/views.py](../../accounts/views.py) `CsrfView` |

## 3. 미구현 엔드포인트 (20 / 44)

`advice`·`notifications` 앱은 `models.py`·`admin.py`·마이그레이션만 존재하고 views/serializers/urls/services 파일이 아직 없다. `concerns`는 #16~23까지 구현됨(실측: `git ls-files`, `config/urls.py`).

| 모듈 | 엔드포인트 | api.md 절 |
| --- | --- | --- |
| M4-5 concerns (남은 2개) | #24·#25 (배정 생성/해제) | §4-24~25 |
| M4-6 advice + feedback | #26~38 (13개) | §4-26~38 |
| M4-7 notifications | #39~41 (3개) | §4-39~41 |
| M4-8 admin roles | #42~43 (2개) | §4-42~43 |

## 4. Active SPEC

**SPEC-001-concerns-api** (`specs/SPEC-001-concerns-api/`) — api.md #16~25 (M4-5 concerns 모듈) 대상.

* [x] TASK-001 — `POST /api/v1/users/me/concerns` (#16) + `GET /api/v1/users/me/concerns` (#17). 테스트 8종 작성(선-실패 확인) → 구현(`concerns/{serializers,services,views,urls}.py`) → `check`/`makemigrations --check`/`ruff`/`test` 전부 통과 → DRF Browsable API로 로그인→생성→목록 확인(스크린샷) → 커밋.
* [x] TASK-002 — `GET /api/v1/users/me/concerns/{concern-id}` (#18, `approved_advices[]` 포함) + `DELETE .../{concern-id}` (#19, soft delete). 테스트 8종 추가(선-실패 확인) → 구현(`ConcernDetailSerializer`, `ConcernDetailView`, `get_own_concern`/`get_own_concern_including_deleted`/`soft_delete_concern`/`approved_advices_view_data` 서비스) → 검증 4종 통과 → 스크린샷으로 상세/삭제/재조회 404 확인 → 커밋.
* [x] TASK-003 — `GET /api/v1/users/me/assigned-concerns` (#20) + `GET .../assigned-concerns/{concern-id}` (#21). `IsActiveAdvisor` 권한 클래스(`common/permissions.py`) 신설: `active_role=ADVISOR`일 때만 통과 — 역할 보유만으로는 403. #21은 존재 자체를 숨기지 않음(배정 안 됨=403, 미존재=404 — #18과 다른 정책, api.md 문언 그대로). 테스트 14종 추가(선-실패 확인, 한 번에 전부 통과) → 검증 4종 통과 → 스크린샷 3장(목록/상세/404) 확인 → 커밋.
* [x] TASK-004 — admin 조회 `GET /api/v1/admin/concerns` (#22) + `GET .../concerns/{concern-id}` (#23). `include_deleted`/`status`/`keyword` 필터, `assignment_count`(활성 배정만), `is_deleted` 파생 필드. #23은 soft-deleted concern도 조회 가능(감사 경로) + assignments/advices 상태 무관 전량 노출(§6.2는 고민 작성자 보호용이지 admin 제한이 아님). 테스트 12종 추가(선-실패 11개 확인) → 검증 4종 통과(`assertNumQueries(5)`로 N+1 부재 고정) → 스크린샷 3장 확인 → 커밋.
* [ ] **다음 최소 작업 단위**: TASK-005 — 배정 생성(#24) + 해제(#25). 상태 전이(SUBMITTED↔ASSIGNED)와 `ASSIGNMENT_CREATED` 알림 부수효과가 포함된 SPEC-001의 핵심 구간.

## 5. 미결 Owner 결정

| # | 항목 | 상태 |
| --- | --- | --- |
| D-4 | Concern `ANSWERED → CLOSED` 사용자 API 도입 여부 | 미결 (권고: Phase 2는 Admin으로만 종료 처리, 신규 API 없음) |
| D-6 | `domain_category`(advisor) 11종 확정 여부 | 확정됨(2026-07-08 D-6) — model.md §11에서 재확인 필요 |
| 신규 (2026-09-10 TASK-003) | api.md #20의 query param `status?`("assignment 상태")가 `Assignment` 모델의 실제 필드와 불일치 — 모델에는 상태 enum이 없고 `is_active`(bool)만 존재 | **해결됨 (Owner 승인 2026-09-10): 후보 B 채택** — `status`는 `concern.status`(SUBMITTED/ASSIGNED/ANSWERED/CLOSED) 필터로 재해석한다. `is_active`는 이미 목록의 전제 조건(활성 배정만 노출)이라 필터 대상이 아니다. **구현·api.md 문구 정정("assignment 상태"→"concern 상태")은 TASK-006에서 일괄 반영.** |
| ADR-006 | AI-Native/Spec-Driven 스켈레톤 전환 | **Accepted (2026-09-10)** — CLAUDE.md §2/§3/§5/§9~§13/§16/§17 개정 적용 완료 |
| 모순 #6 (2026-09-09 부트스트랩) | api.md #16·#19·#22가 여전히 `is_deleted` 표기, 모델은 `deleted_at` | 해석 승인됨(2026-09-09): 파생 응답 필드로 간주. api.md 원문 정정은 SPEC-001 구현 시 동반 |
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
