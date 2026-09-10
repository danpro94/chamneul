# STATUS — chamneul 프로젝트 현황판

> 이 파일은 **Git이 유일한 source of truth**라는 원칙(ADR-006)의 실행판이다. 실제 코드(`config/urls.py`, 각 앱 `views.py`)를 읽고 사실로만 채운다 — 추측·계획 값은 적지 않는다. **구현 커밋에는 이 파일 갱신이 반드시 동반된다.**
> 마지막 실측: 2026-09-09 (커밋 `b2eaf90` 기준)

---

## 1. Phase / 마일스톤

| 항목 | 값 |
| --- | --- |
| Phase | Phase 2 — 로컬 컨테이너 MVP |
| 현재 마일스톤 | M4 — api.md v1.1의 44개 엔드포인트 구현 (8모듈) |
| M4 진행률 | 4/8 모듈, **16/44 엔드포인트** |
| 다음 마일스톤 | M5 — 스모크 테스트 + 문서 정리 → Phase 2 종료 |

| MS | 내용 | 상태 |
| --- | --- | --- |
| M1 | 스켈레톤 (config/accounts/common, custom User+uuid7, /healthz, compose) | 완료 |
| M2 | 런타임 승격 [소유] Dockerfile 멀티스테이지·비루트·gunicorn + [위임] accounts 역할 모델 3종 | 완료 |
| M3 | 도메인 모델 7종 + 마이그레이션 + Admin | 완료 (리뷰 노트 미작성 — 부채 #4) |
| M4 | api.md v1.1의 44개 엔드포인트 구현 (8모듈) | 진행 중 |
| M5 | 스모크 테스트 + 문서 정리 | 미착수 |

---

## 2. 구현된 엔드포인트 (16 / 44)

실측 근거: [config/urls.py](../../config/urls.py) — `accounts.urls`, `advisors.urls` 2개만 include.

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
| 44 | GET | `/api/v1/csrf` | [accounts/views.py](../../accounts/views.py) `CsrfView` |

## 3. 미구현 엔드포인트 (28 / 44)

`concerns/`·`advice/`·`notifications/` 앱은 `models.py`·`admin.py`·마이그레이션만 존재하고 **views/serializers/urls/services 파일이 아직 없다** (실측: `git ls-files`).

| 모듈 | 엔드포인트 | api.md 절 |
| --- | --- | --- |
| M4-5 concerns | #16~25 (10개) | §4-16~25 |
| M4-6 advice + feedback | #26~38 (13개) | §4-26~38 |
| M4-7 notifications | #39~41 (3개) | §4-39~41 |
| M4-8 admin roles | #42~43 (2개) | §4-42~43 |

## 4. Active SPEC

**SPEC-001-concerns-api** (`specs/SPEC-001-concerns-api/`) — api.md #16~25 (M4-5 concerns 모듈) 대상.

**다음 최소 작업 단위**: TASK-001 — `POST /api/v1/users/me/concerns` (#16) + `GET /api/v1/users/me/concerns` (#17). 순서: 실패하는 Django 테스트 작성 → 최소 구현 → `check`/`makemigrations --check`/`ruff`/`test` 실행 → 커밋 → STATUS.md 갱신.

## 5. 미결 Owner 결정

| # | 항목 | 상태 |
| --- | --- | --- |
| D-4 | Concern `ANSWERED → CLOSED` 사용자 API 도입 여부 | 미결 (권고: Phase 2는 Admin으로만 종료 처리, 신규 API 없음) |
| D-6 | `domain_category`(advisor) 11종 확정 여부 | 확정됨(2026-07-08 D-6) — model.md §11에서 재확인 필요 |
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
