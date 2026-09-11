# README_AIUSAGE — AI 활용 기록

> CLAUDE.md §13에 따른 AI 사용 대장. 각 항목: 날짜 / 작업 / AI 도구 / 인간(Owner) 결정 / 생성 산출물 / 검증 결과 / 잔여 리스크.
> 이 프로젝트의 AI 협업 원칙(소유/위임/읽기 라우팅)은 `docs/learning/02-ai-collaboration-and-ownership-strategy.md` 참조.
> 2026-09-09: 과거 `docs/README_AIUSAGE.md`(2026-06-22~06-30, 4개 세션)를 이 파일로 병합하고 원본은 삭제했다(ADR-006 부트스트랩, Owner 결정). 기존 "~2026-07-01 — M1 스켈레톤 (소급 기록)" 압축 요약 항목은 병합된 06-29·06-30의 상세 기록으로 대체한다.

---

## 2026-09-11 — SPEC-002/TASK-003: 조언 수정+삭제 (api.md #29·#30) [위임]

### 작업

1. `advice/tests.py`에 `AdviceUpdateTests`(10) + `AdviceDeleteTests`(7) 총 17케이스 추가(본문 수정 시 version+히스토리, `submit` 단독 토글은 무변화, REVIEWING 허용, APPROVED/DELETED 409, 타인 403, 없는 advice 404, 삭제 204+상태전이, 삭제 후 재작성 가능(엔드포인트 경유)) → 실행해 15개 실패 확인(PATCH/DELETE 라우트 없음 → 405/404 혼재).
2. 최소 구현: `advice/services.py`에 `_get_own_editable_advice()`(조회+소유권 403+편집가능상태 409 공용 검사) / `update_advice()`(본문 변경 시에만 `AdviceHistory` 스냅샷 + `version` 증가, `transaction.atomic`) / `delete_advice()`. `advice/serializers.py`에 `AdviceUpdateSerializer`(`submit`→`is_submitted` source 매핑) + `AdviceUpdateResultSerializer`. `AdviceDetailView`에 `patch`/`delete` 추가, `get_permissions()`로 GET은 `IsAuthenticated`만·PATCH/DELETE는 `IsActiveAdvisor` 추가.
3. 4종 검증 — 전체 108/108 통과.
4. 시각 확인: **TASK-002의 계정 오염 교훈을 반영**해, 사용 전 역할을 명시적으로 조회·출력(`roles held: ['ADVISOR']`, `is_superuser: False`)한 신규 계정으로 재현. 본문 수정 → `version` 2 스크린샷, 삭제 → `status=DELETED` 스크린샷, 그리고 `AdviceHistory` row를 DB에서 직접 조회해 수정 **전** 본문이 정확히 `version=1`로 스냅샷됐음을 확인.

### 사용 도구

* Claude Code (VS Code Extension)

### 인간 결정 (Owner, 2026-09-11)

TASK-003 진행 승인.

### 생성된 산출물

수정: `advice/{services,serializers,views,tests}.py`, `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test advice.tests.AdviceUpdateTests advice.tests.AdviceDeleteTests` → 구현 전 15 fail → 구현 후 **17/17 OK**
* `manage.py test` (전체) → **108/108 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 시각 확인: PATCH 200(version 2) / DELETE 204 / 재조회 시 status=DELETED, `AdviceHistory.directional_guidance`가 수정 전 문구와 일치함을 DB에서 직접 확인 — 스크린샷 2장 Owner 전송

### 잔여 리스크

1. **없음 (이번 TASK 한정)** — TASK-002의 계정 오염 교훈을 실제로 적용해 재발 방지.
2. TASK-004(리뷰 승인/반려)부터는 `AdviceHistory`가 아니라 `Notification`·`Concern.status`가 얽히므로, 여기서 검증한 "본문 변경 여부로 트리거 분기" 패턴이 그대로 재사용되지는 않음 — 별도 판정 로직 필요.

### 다음 단계 권장

1. Owner 확인 후 TASK-004(#32 admin 리뷰 목록 + #33 승인/반려, 낙관적 잠금 412 최초 도입) 착수.

---

## 2026-09-11 — SPEC-002/TASK-002: 조언 상세 3주체 분기 (api.md #27) [위임]

### 작업

1. `advice/tests.py`에 `AdviceDetailTests` 11케이스 추가(작성자 전상태 200+`reject_reason`, 고민 작성자 APPROVED만 200/`reject_reason` 없음, 고민 작성자 PENDING·REJECTED 403, ADMIN 전상태 200, 무관 사용자·조언가 403, 없는 advice 404, advisor 신원 최소 노출) → 실행해 10개 실패 확인.
2. 최소 구현: `advice/services.py`에 `get_visible_advice()` — (작성자 → 관리자 → 고민 작성자+APPROVED) 우선순위 판정, 그 외 403. `_is_admin()` 헬퍼는 `common.permissions.IsAdmin`과 동일 로직을 의도적으로 별도 구현(객체 수준 판정과 DRF permission 클래스의 시그니처가 안 맞아 억지로 묶지 않음, 코드 주석에 사유 명시). `advice/serializers.py`에 `AdviceDetailSerializer`(고민 작성자용) + 상속받은 `AdviceDetailWithReasonSerializer`(작성자/관리자용, `reject_reason` 추가) — 필드 목록 중복을 상속으로 제거. `AdviceDetailView` + URL 1개 추가.
3. 4종 검증 — 전체 91/91 통과.
4. 시각 확인 중 **데모 계정 재사용 문제를 발견·정정**(아래).

### 데모 재현 중 발견한 것 (버그 아님, 데모 설계 실수)

첫 스크린샷 시도에서 `demo@example.com`(고민 작성자)이 심사중(PENDING) 조언을 열람했는데 403이 아니라 200이 나왔다. 원인은 코드가 아니라 데모 계정: `demo`는 **TASK-004에서 이미 ADMIN 역할을 부여받은 채로 영구 보존된 계정**이었다. `get_visible_advice()`의 판정 순서가 (작성자→관리자→고민 작성자) 이므로, admin이기도 한 고민 작성자는 관리자 시야로 응답받는다 — 이것 자체는 설계대로다. 다만 "순수 고민 작성자"를 보여주려던 데모가 실은 "관리자"를 보여주고 있었던 것. `plain.owner@example.com`(어떤 역할도 없는 신규 계정)을 새로 만들어 재현해 올바른 스크린샷 3장을 얻었다.

**교훈**: Docker Compose를 세션 간 재사용하면서 데모 계정에 역할을 누적 부여해 왔다(`demo`는 이제 ADVISOR는 아니지만 ADMIN). 앞으로 권한 분기를 시각 확인할 때는 매번 신선한 계정을 만들거나, 계정별 역할을 먼저 조회해 전제를 확인해야 한다.

### 사용 도구

* Claude Code (VS Code Extension)

### 인간 결정 (Owner, 2026-09-11)

TASK-002 진행 승인.

### 생성된 산출물

수정: `advice/{services,serializers,views,urls,tests}.py`, `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test advice.tests.AdviceDetailTests` → 구현 전 10 fail → 구현 후 **11/11 OK**
* `manage.py test` (전체) → **91/91 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 시각 확인(정정 후, 권한 없는 신규 계정 기준): 승인된 조언 200(`reject_reason` 필드 자체 없음) / 심사중 조언 403 / 작성자 본인은 심사중 조언도 200(`is_submitted`·`reject_reason` 노출) — 스크린샷 3장 Owner 전송

### 잔여 리스크

1. **판정 우선순위(작성자>관리자>고민 작성자)가 명시적 결정이 아니라 구현 중 자연스럽게 정해짐** — 세 조건이 동시에 참인 경우(예: 관리자가 자기 자신에게 조언을 배정하는 기형적 케이스)는 스펙에 없다. Phase 2 실사용에서 발생 가능성은 낮으나 기록해 둔다.
2. **개발용 Docker 컨테이너의 역할 오염** — `demo` 계정은 이제 ADMIN을 보유해 "평범한 사용자" 데모에 더 이상 적합하지 않다. 다음 세션에서 역할별 데모 계정을 명확히 분리(예: `owner.demo@`, `admin.demo@`, `advisor.demo@`)하는 것을 권고.

### 다음 단계 권장

1. Owner 확인 후 TASK-003(#29 조언 수정 + #30 삭제) 착수.

---

## 2026-09-10 — SPEC-001/TASK-006: 마무리 — SPEC-001 종료 [위임]

### 작업

1. **#20 `status` 필터 구현** — Owner 승인안(concern.status 기준)대로 실패 테스트 작성 → 구현 → 통과.
2. **api.md 문구 정정 2건**: (a) #20의 "(assignment 상태)"를 "(concern 상태 — SUBMITTED/ASSIGNED/ANSWERED/CLOSED)"로 교체. (b) #16·#18·#19·#24의 상태 서술에서 `is_deleted=true/false`를 실제 저장 컬럼 `deleted_at`으로 교체(#22의 **응답 필드** `is_deleted`는 C-1 규약대로 유지). 문서 상단에 2026-09-10 개정 이력 추가(기존 관례 준수).
3. **AC 전항 재검증** — acceptance.md의 AC-1~AC-10을 테스트 62개와 1:1 대조. **미커버 2건을 발견해 보강**(아래).
4. SPEC 문서 종료 처리: `tasks.md` 전 항목 체크, `acceptance.md`에 종료 판정 절 추가(실행 출력 포함), STATUS.md의 미결 항목 2건을 "종결됨"으로 전환.

### AC 대조에서 발견한 미커버 2건 (이번에 보강)

| # | 미커버였던 AC | 조치 |
| --- | --- | --- |
| 1 | AC-4 "연결된 Advice/**Assignment** 보존" — Advice만 검증하고 있었음 | 기존 테스트에 Assignment 보존 단언 추가 |
| 2 | TEST_CRITERIA §3 "**목록** API N+1 없음(assertNumQueries)" — 상세(#23)에만 있었음 | `test_list_query_count_is_bounded` 추가 — #20에 배정 6건이 있어도 쿼리 **2개 고정** 실증 |

두 번째 항목이 특히 의미가 있다: 목록 API의 N+1은 "구현할 때 신경 썼다"는 주장만 있었고 **판정 장치가 없었다**. 이제 쿼리 수가 상수로 고정돼 있어, 이후 누군가 `select_related`/`Subquery`를 걷어내면 테스트가 즉시 깨진다.

### 사용 도구

* Claude Code (VS Code Extension)

### 인간 결정 (Owner, 2026-09-10)

| 결정 | 내용 |
| --- | --- |
| 진행 순서 | M4-6 착수보다 **TASK-006 마무리 → PR → 그다음 M4-6** 순서 채택(브랜치에 미머지 커밋이 쌓인 상태에서 13개짜리 모듈을 얹지 않는다) |

### 생성된 산출물

수정: `concerns/{views,tests}.py`, `docs/api.md`, `docs/00-project/STATUS.md`, `specs/SPEC-001-concerns-api/{tasks,acceptance}.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test` → **62/62 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* AC-1~AC-10 전항 통과 (acceptance.md 종료 판정 절에 실행 출력 첨부)

### 잔여 리스크

1. **SPEC-001은 종료됐지만 M4 전체 문서 부채는 남음** — M4-1~M4-4 AIUSAGE 소급 기록, 리뷰 노트 2건, model.md drift 6건(STATUS.md §7).
2. **코드 리뷰 미수행** — 서브에이전트(`security-reviewer`, `api-architect`) 리뷰는 PR 단계에서 수행 예정.
3. **M4-6은 SPEC-002를 먼저 작성한 뒤 착수 권장** — advice는 §6.2 노출 규칙 + 버전 관리 + AdviceHistory 스냅샷이 얽힌 이 서비스의 핵심 도메인.

### 다음 단계 권장

1. PR 생성 → 리뷰 → main 머지.
2. SPEC-002 작성 후 M4-6 착수.

---

## 2026-09-10 — SPEC-001/TASK-005: 배정 생성+해제 (api.md #24·#25) — M4-5 완료 [위임]

### 작업

프롬프트 3 루프로 SPEC-001의 TASK-005 구현. SPEC-001에서 상태 전이·부수효과가 함께 걸리는 유일한 구간:

1. `concerns/tests.py`에 `AssignmentTests` 18케이스 추가(권한 401/403, SUBMITTED→ASSIGNED 전이+알림, 2번째 advisor 배정 시 상태 유지, 중복 활성 배정 409, 해제 후 재배정 허용(부분 유니크), CLOSED/삭제 concern 409, 비-advisor 422, 실패 시 부분 상태 없음, 마지막 해제 시 SUBMITTED 복귀, 잔여 배정 있으면 유지, ANSWERED는 되돌리지 않음, 이미 해제 409, 타 concern의 assignment 404) → 실행해 14개 실패 확인.
2. 최소 구현: `concerns/services.py`에 `assign_advisor`/`unassign_advisor` 추가 — 둘 다 `with transaction.atomic()` 안에서 concern row를 `select_for_update()`로 잠그고(동시 배정/해제 직렬화) Assignment 생성·상태 전이·알림 생성을 함께 수행. `AssignmentCreateSerializer`/`AssignmentCreateResultSerializer`, `AdminAssignmentCreateView`/`AdminAssignmentDetailView`, URL 2개 추가.
3. 4종 검증 — **전체 60/60** 통과.
4. 시각 확인: Playwright로 배정 전(SUBMITTED) → 배정 201(`concern_status: ASSIGNED`) → **조언가 계정으로 로그인해 본인 큐(#20)에 실제로 뜨는 것 확인** → 해제 후 SUBMITTED 복귀(배정 행은 `is_active=false` 보존) 스크린샷 4장 전송. 컨테이너 shell로 `Notification` row(type=ASSIGNMENT_CREATED, recipient=조언가, target_url, payload) 실측.

### 사용 도구

* Claude Code (VS Code Extension) / Playwright(1.48, 데모 전용 임시 설치)

### 인간 결정 (Owner, 2026-09-10)

| 결정 | 내용 |
| --- | --- |
| 학습 세션 | **종료** — 이해 확인 질문·퀴즈 없이 구현만 진행 |
| TASK-005 | 진행 승인 |

### 판단 기록 (AI가 정한 것)

* **비-advisor 지정은 422**(400/404 아님) — 형식은 맞으나 값이 부적합한 경우(api.md §1.8). 대상 사용자가 없는 경우와 advisor가 아닌 경우를 **같은 응답**으로 통일해, admin 도구가 사용자 존재 여부를 알아내는 수단이 되지 않게 했다.
* **`select_for_update()` 도입** — 배정/해제는 `concern.status`에 대한 read-modify-write라, 두 관리자가 동시에 마지막 배정을 해제하면 상태가 되돌아가지 않는 경합이 가능하다. CLAUDE.md §4가 허용한 범위 내에서 concern row를 잠가 직렬화.
* **ANSWERED 고민은 배정 전부 해제해도 SUBMITTED로 되돌리지 않음** — §6.6의 되돌림 규칙은 ASSIGNED에만 적용된다. 승인된 조언이 이미 붙은 고민을 "미배정"으로 표시하면 사실과 어긋난다.

### 생성된 산출물

수정: `concerns/{services,serializers,views,urls,tests}.py`, `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test concerns.tests.AssignmentTests` → 구현 전 14 fail → 구현 후 **18/18 OK**
* `manage.py test` (전체) → **60/60 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 실환경 실측: 상태 SUBMITTED→ASSIGNED→SUBMITTED 왕복, `Notification` row 1건 생성(ASSIGNMENT_CREATED, 수신자=배정된 조언가), 조언가 큐(#20)에 반영 — 스크린샷 4장 Owner 전송

### 잔여 리스크

1. **동시성은 코드로만 방어, 부하 테스트 미수행** — `select_for_update()`의 실제 경합 동작은 Phase 2 스코프 밖(테스트는 단일 스레드).
2. **알림 `target_url`이 API 경로 형태** — C-10 결정상 "프론트 라우트 키"가 되어야 하나 프론트가 없어 잠정적으로 API 경로를 넣었다(기존 advisors 승인 알림과 동일 관행). 프론트 착수 시 일괄 정정 필요.
3. **M4-5 완료 = SPEC-001의 코드 부분 완료**. 남은 TASK-006(문서 정정 2건 + #20 status 필터 구현 + 전체 AC 재실행)은 미착수.

### 다음 단계 권장

1. TASK-006(SPEC-001 마무리) 또는 곧바로 M4-6(advice+feedback, #26~38) 착수 — Owner 선택.

---

## 2026-09-10 — SPEC-001/TASK-004: admin 고민 목록+상세 (api.md #22·#23) [위임]

### 작업

프롬프트 3 루프로 SPEC-001의 TASK-004만 구현:

1. `concerns/tests.py`에 `AdminConcernTests` 12케이스 추가(권한 401/403, `include_deleted` 기본/명시, `status`·`keyword` 필터, `assignment_count`(비활성 제외), soft-deleted 상세 조회, assignments·advices 전량 노출, `assertNumQueries`로 N+1 부재) → 실행해 11개 실패 확인.
2. 최소 구현: `concerns/services.py`에 `display_names_by_advisor`(TASK-002의 벌크 조회를 재사용 가능한 헬퍼로 추출) / `list_concerns_for_admin` / `get_concern_for_admin` / `admin_concern_detail_view_data` 추가. `AdminConcernListSerializer` 추가. `AdminConcernListView`·`AdminConcernDetailView` + URL 2개 추가.
3. 4종 검증 실행 — 전체 concerns 42/42 통과.
4. 시각 확인: demo 계정에 ADMIN 역할 부여 + 삭제된 고민 fixture 생성 후 Playwright로 기본 목록/`include_deleted=true`/상세 스크린샷 3장 전송.

### 사용 도구

* Claude Code (VS Code Extension) / Playwright(1.48, 데모 전용 임시 설치)

### 인간 결정 (Owner, 2026-09-10)

| 결정 | 내용 |
| --- | --- |
| 모순 해결 | api.md #20의 `status?` 쿼리 파라미터를 **`concern.status` 필터로 재해석**(후보 B) 승인. 구현·api.md 문구 정정은 TASK-006에서 일괄 반영하도록 tasks.md에 명시 |
| TASK-004 | 진행 승인 |

### 판단 기록 (AI가 정한 것, 이견 시 저비용 수정 가능)

* `assignment_count`는 **활성 배정만** 집계(비활성 이력 제외) — 운영자가 "지금 몇 명이 붙어 있나"를 보는 숫자가 더 유용하다고 판단. 비활성 이력은 #23 상세에서 `is_active=false`로 전량 확인 가능.
* #23은 **soft-deleted concern도 200으로 조회**되게 구현 — #22의 `include_deleted=true`가 노출한 행이 상세에서 404가 되면 모순이므로.
* `assertNumQueries` 기대값은 처음 6으로 잡았다가 실측 5로 정정(`force_authenticate`가 세션 조회를 건너뜀). AC("쿼리 수 고정")는 그대로이며 상수만 실측값으로 맞춘 것.

### 생성된 산출물

수정: `concerns/{services,serializers,views,urls,tests}.py`, `docs/00-project/STATUS.md`, `specs/SPEC-001-concerns-api/tasks.md`(TASK-006에 #20 필터 항목 추가).

### 검증 결과 (전부 실행 완료)

* `manage.py test concerns.tests.AdminConcernTests` → 구현 전 11 fail → 구현 후 **12/12 OK**
* `manage.py test concerns` (전체) → **42/42 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed(E501 1건 즉시 수정)
* 시각 확인: admin 목록(기본/include_deleted)/상세 스크린샷 3장 Owner에게 전송

### 잔여 리스크

1. **`keyword` 필터는 `concern_summary`만 대상** — `decision_context` 본문 검색은 미포함(api.md가 대상 범위를 명시하지 않음). 실사용 시 범위 확장 필요할 수 있음.
2. **admin 목록에 본문(decision_context) 미노출** — 의도적(§8 목록 응답 최소화). 상세(#23)에서만 노출.
3. TASK-005는 상태 전이 + 알림 부수효과가 함께 걸리는 구간이라 `@transaction.atomic` 적용이 필수 — M2 학습 부채 ⑤(atomic)와 직결되므로 구현 후 이해 확인 권장.

### 다음 단계 권장

1. Owner 확인 후 TASK-005(#24 배정 생성 + #25 해제) 착수.

---

## 2026-09-10 — SPEC-001/TASK-003: advisor 배정 목록+상세 (api.md #20·#21) [위임]

### 작업

프롬프트 3 루프로 SPEC-001의 TASK-003만 구현:

1. `concerns/tests.py`에 `AssignedConcernTests` 14케이스 추가(role 게이트 401/403 3종, 목록 스코핑, `advice_status` 반영, 배정 안 됨/미존재/`requester_display_name` 3분기/이메일·user_id 미노출/`my_advice` 유무 등) → 실행해 7 fail + 6 error 확인(라우트 없음).
2. 최소 구현: `common/permissions.py`에 `IsActiveAdvisor`(active_role=ADVISOR 게이트, `IsAdmin`과 동일한 지연 import 패턴) 신설. `concerns/services.py`에 `list_assigned_concerns`(advisor 본인 활성 배정 + 본인 advice_status를 상관 서브쿼리로 annotate, N+1 없음) / `get_assigned_concern`(미존재 404, 미배정 403 — `django.core.exceptions.PermissionDenied`를 DRF가 자동 403 변환) / `requester_display_name` / `my_advice_view_data` / `assigned_concern_detail_view_data` 추가. `concerns/serializers.py`에 `AssignedConcernListSerializer`(plain Serializer — Assignment+Concern 혼합 소스) 추가. `concerns/views.py`에 `AssignedConcernListView`/`AssignedConcernDetailView` 추가. `concerns/urls.py`에 `/assigned-concerns`, `/assigned-concerns/<uuid:concern_id>` 추가.
3. 4종 검증 실행 — 테스트 14/14 한 번에 통과(구현 재시도 없음), 전체 concerns 30/30, check/migrations/ruff 전부 통과.
4. 시각 확인: `docker compose exec app python manage.py shell`로 advisor 계정+배정 fixture 생성 → Playwright로 advisor 로그인 → 배정 목록(#20) → 배정 상세(#21, `requester_display_name`="익명의 요청자", `my_advice`=null) → 존재하지 않는 concern-id 조회 시 404까지 스크린샷 3장 전송.

### 사용 도구

* Claude Code (VS Code Extension)
* Playwright(1.48, npx 임시 설치 — 데모 전용, 저장소 의존성 아님)

### 인간 결정 (Owner, 2026-09-10)

TASK-001에서 승인된 방식(테스트 + Mock-up 시각 확인)을 동일 적용 — 이번 턴은 TASK-003 진행 승인만.

### 발견한 문서 모순 (신규 1건, Owner 결정 대기)

api.md #20의 쿼리 파라미터 `status?`가 "(assignment 상태)"라고 되어 있으나, `Assignment` 모델(model.md §3.7, concerns/models.py)에는 상태 enum이 없고 `is_active`(bool)만 존재한다. tasks.md TASK-003 체크리스트에 이 필터에 대한 테스트가 없어 **구현하지 않고 미해결로 남김**(파라미터는 받되 무시) — STATUS.md §5에 후보안 3가지와 함께 기록.

### 생성된 산출물

수정: `common/permissions.py`(`IsActiveAdvisor` 추가), `concerns/{services,serializers,views,urls,tests}.py`(각 확장).

### 검증 결과 (전부 실행 완료)

* `manage.py test concerns.tests.AssignedConcernTests` → 구현 전 7 fail + 6 error → 구현 후 **14/14 OK**(재시도 없이 1차 구현으로 전부 통과)
* `manage.py test concerns` (전체) → **30/30 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 시각 확인: 배정 목록/상세/404 스크린샷 3장 Owner에게 전송

### 잔여 리스크

1. **api.md #20 `status?` 쿼리 필터 미구현** (위 모순 참조) — Owner 결정 후 TASK-006(SPEC-001 마무리)에서 일괄 반영 권장.
2. **`#21`의 403 vs 404 정책이 `#18`과 다름**(존재 자체를 숨기지 않음)을 코드 주석으로 명시했으나, 이 비대칭성 자체가 향후 보안 리뷰(security-reviewer) 대상으로 재확인 필요.
3. plan.md가 제안했던 `IsAssignedAdvisor`(객체 수준 배정 확인까지 포함한 단일 permission 클래스) 대신, role 게이트만 permission 클래스(`IsActiveAdvisor`)로 분리하고 배정 여부(403)는 서비스 함수 안에서 직접 판정하도록 설계를 변경했다 — 404/403 구분을 명확히 제어하기 위함(plan.md 대비 구현상 조정, 기능은 AC와 100% 일치).

### 다음 단계 권장

1. Owner 확인 후 TASK-004(#22 admin 전체 목록 + #23 admin 상세) 착수.

---

## 2026-09-10 — SPEC-001/TASK-002: concern 상세+소프트 삭제 (api.md #18·#19) [위임]

### 작업

프롬프트 3 루프로 SPEC-001의 TASK-002만 구현:

1. `concerns/tests.py`에 `ConcernDetailDeleteTests` 8케이스 추가(상세 APPROVED-only 노출, soft-delete/타인 자원 404, 삭제 204+자식 row 보존, 재삭제 409, 비로그인 401) → 실행해 5개 실패(라우트 없음) 확인.
2. 최소 구현: `concerns/services.py`에 `get_own_concern`(soft-deleted 제외 404) / `get_own_concern_including_deleted`(삭제 판정용) / `soft_delete_concern`(409 가드) / `approved_advices_view_data`(APPROVED만, N+1 없이 advisor_display_name 벌크 조회 — advisor의 최신 APPROVED `AdvisorApplication.display_name`, 없으면 `nickname` 폴백) 추가. `concerns/serializers.py`에 `ConcernDetailSerializer` 추가. `concerns/views.py`에 `ConcernDetailView`(GET/DELETE) 추가. `concerns/urls.py`에 `<uuid:concern_id>` 경로 추가.
3. 4종 검증 실행 — 전부 통과(테스트 16/16).
4. Owner 요청에 따른 시각 확인 지속: 앱 재빌드 후 Playwright로 (a) 상세 조회 화면(approved_advices 포함) (b) 삭제 버튼→확인 모달→204 (c) 재조회 시 404(우리 커스텀 에러 포맷 `{error:{code,message}}` 노출까지 확인) 스크린샷 3장 전송.

### 사용 도구

* Claude Code (VS Code Extension)
* Playwright(1.48, npx 임시 설치 — TASK-001과 동일하게 데모 전용, 저장소 의존성 아님)

### 인간 결정 (Owner, 2026-09-10)

TASK-001에서 승인된 방식(테스트 + Mock-up 시각 확인)을 동일하게 적용 — 이번 턴은 TASK-002 진행 승인만.

### 생성된 산출물

수정: `concerns/{services,serializers,views,urls,tests}.py`(각 확장).

### 검증 결과 (전부 실행 완료)

* `manage.py test concerns` → 구현 전 5 fail(3케이스는 라우트 부재로 우연히 404 일치) → 1차 구현 후 15/16(advice_id가 UUID 객체로 직렬화되어 문자열 비교 실패) → `str()` 캐스팅 수정 후 **16/16 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 시각 확인: 상세/삭제/재조회 스크린샷 3장 Owner에게 전송

### 잔여 리스크

1. **`advisor_display_name` 폴백 로직 미검증 상태(코드 리뷰 대상)**: 한 advisor가 여러 APPROVED 신청 이력을 가질 수 있는 실제 케이스는 Phase 2 도메인 규칙상 발생하지 않아야 하지만(승인 후 재신청 경로 없음), 서비스 함수는 `-submitted_at` 최신 것을 택하도록만 방어했다.
2. **TASK-003(#20·#21)부터 `active_role=ADVISOR` 게이트 등장** — accounts 모듈의 `active_role` 검사 패턴을 그대로 재사용할 예정.

### 다음 단계 권장

1. Owner 확인 후 TASK-003(#20 배정 목록 + #21 배정 상세) 착수.

---

## 2026-09-10 — SPEC-001/TASK-001: concern 생성+목록 (api.md #16·#17) [위임]

### 작업

프롬프트 3(SPEC 단위 구현 루프)로 SPEC-001의 TASK-001만 구현:

1. `concerns/tests.py` 작성(8개 케이스: 인증 필요, 생성 성공/실패 3종, 목록 필터링·soft-delete/타인 배제) → `manage.py test concerns` 실행해 전부 404로 실패하는 것을 먼저 확인(라우팅 자체가 없었으므로).
2. 최소 구현: `concerns/serializers.py`(Create/CreateResult/List 분리) + `concerns/services.py`(`create_concern`, `has_approved_advice` annotation 포함 `list_my_concerns`) + `concerns/views.py`(`ConcernListCreateView`, GET/POST 한 경로) + `concerns/urls.py` + `config/urls.py`에 include.
3. `check`/`makemigrations --check`/`ruff check`/`manage.py test` 4종 실행 — 전부 통과 확인(테스트 8/8 OK).
4. Owner 요청에 따라 추가로 시각적 확인: `docker compose up`으로 앱+DB 기동, Playwright(임시 설치)로 DRF Browsable API를 헤드리스 브라우저로 조작 — 로그인 → 빈 목록+POST 폼 스크린샷 → 고민 1건 제출(201) 스크린샷 → 재조회 시 목록에 반영됨 스크린샷. 3장을 Owner에게 전송.

### 사용 도구

* Claude Code (VS Code Extension)
* Playwright(1.48, npx로 임시 설치·실행 — 프로젝트 의존성에는 추가하지 않음, 데모 전용)

### 인간 결정 (Owner, 2026-09-10)

| 결정 | 내용 |
| --- | --- |
| 결정 1 | 착수 전 12살 눈높이 브리핑 요구 → 브리핑 제시 후 승인 |
| 결정 2 | 백엔드 테스트만으로는 부족, 가벼운 Mock-up 수준 UI/UX로 데이터/사용자 흐름을 시각적으로 확인 요청(화려함 불필요, 최소 구현 허용) |

### 생성된 산출물

신규: `concerns/{serializers,services,views,urls,tests}.py`. 수정: `config/urls.py`(concerns.urls include, `DEBUG`에서만 `api-auth/`(DRF 로그인) 추가).

### 검증 결과 (전부 실행 완료)

* `manage.py test concerns` → 구현 전 7 failures + 1 error(전부 404) → 구현 후 **8/8 OK**
* `manage.py check` → 0 issues
* `makemigrations --check --dry-run` → No changes detected
* `ruff check .` → All checks passed(신규 파일 전량; 기존 파일 7종의 `ruff format` drift는 이번 작업과 무관 — 미변경)
* 시각 확인: Playwright 스크린샷 3장(로그인+빈 목록 → POST 201 → 목록에 반영) Owner에게 전송, 육안 확인 요청

### 잔여 리스크

1. **DRF Browsable API 데모용 `api-auth/` 경로**: `settings.DEBUG`에서만 노출되도록 가드했으나, prod 설정(`config/settings/prod.py`)에서 `DEBUG=False`가 실제로 강제되는지는 이번 작업에서 재확인하지 않음(M2/M1에서 이미 설정된 것으로 추정 — M5 스모크에서 재검증 권장).
2. **Playwright는 프로젝트 의존성이 아님** — `pyproject.toml`/`uv.lock`에 추가하지 않았고, 데모 스크립트는 스크래치패드(`/private/tmp/...`)에만 존재해 저장소에 남지 않음. 다음 시각 확인이 필요하면 재설치 필요.
3. **TASK-002부터는 approved_advices 등 advice 연동이 등장** — `advice` 앱은 아직 views 없음(모델만 존재), #18 구현 시 빈 배열로 시작 가능(spec.md §5 Non-Goals에 이미 명시).

### 다음 단계 권장

1. Owner 확인 후 TASK-002(#18 상세 + #19 소프트 삭제) 착수.

---

## 2026-09-09 — VS Code 마이그레이션 부트스트랩: AI-Native/Spec-Driven 구조 전환 [위임]

### 작업

`docs/request/3-vscode-migration_prompt.md` §5 "프롬프트 1 — 부트스트랩" 지시를 실행:

1. 지정된 순서로 통독: CLAUDE.md → api.md §3 → model.md §5 → `docs/reviews/04-milestone4-definition.md` → `config/urls.py`/`accounts`/`advisors`(구현 완료분) → README_AIUSAGE.md.
2. 실제 코드(`urls.py`, `views.py`, `git ls-files`)를 근거로 생성 전 사전 보고(파일 목록/STATUS 초안/CLAUDE.md diff 미리보기/문서 모순 11건) 제시 → Owner 승인 수신.
3. `docs/adr/ADR-006-ai-native-spec-driven-skeleton.md` 작성(Status: Proposed) — CLAUDE.md §16 Constitutional lock에 따라 CLAUDE.md 직접 수정 없이 개정 diff만 제안.
4. `docs/00-project/STATUS.md` 신설 — 코드 실측 기준(16/44 엔드포인트 구현) 현황판.
5. 루트 `README.md` 신설 — "지도" 원칙(개요/스택/구조/Quick Start/문서 링크만).
6. `docs/testing/TEST_CRITERIA.md` 신설 — 테스트 0건 현실 명시 + M4 AC를 자동화 판정 기준으로 번역.
7. `specs/SPEC-001-concerns-api/{spec,plan,tasks,acceptance}.md` 신설 — api.md #16~25(M4-5 concerns) 대상.
8. `.claude/rules/{coding,security,testing,infrastructure}.md` 4종 신설 — CLAUDE.md §9~§12 원문을 내용 변경 없이 이동.
9. Owner 승인 결정 3건 실행: (a) SPEC-001 해석 2건(`is_deleted`=파생 필드, #16~19 active_role 게이트 없음) (b) 본 병합 작업 (c) `.claude/commands/` 슬래시 커맨드는 이번 범위에서 제외.

### 사용 도구

* Claude Code (VS Code Extension으로 마이그레이션 직후 첫 세션)

### 인간 결정 (Owner, 2026-09-09)

| 결정 | 내용 |
| --- | --- |
| 결정 1 | SPEC-001 해석 승인: api.md #16·#19·#22의 `is_deleted`는 DB 컬럼이 아니라 `deleted_at` 기반 파생 응답 필드로 해석 / #16~19(사용자 concern CRUD)는 `active_role` 게이팅 없음 |
| 결정 2 | `docs/README_AIUSAGE.md`(06-22~06-30 4항목)를 이 파일로 병합 후 원본 삭제 |
| 결정 3 | `.claude/commands/`(Pro Tip 3의 `/status`·`/spec-next`·`/gate`)는 이번 부트스트랩 범위에서 생성하지 않음 |

### 생성된 산출물

신규 12파일: `docs/adr/ADR-006-ai-native-spec-driven-skeleton.md`, `docs/00-project/STATUS.md`, `README.md`(루트), `docs/testing/TEST_CRITERIA.md`, `specs/SPEC-001-concerns-api/{spec,plan,tasks,acceptance}.md`(4), `.claude/rules/{coding,security,testing,infrastructure}.md`(4).

병합/삭제: `docs/README_AIUSAGE.md` 내용을 이 파일로 병합 후 삭제.

CLAUDE.md는 **수정하지 않음** — ADR-006이 Owner 승인으로 Accepted 전환된 뒤에만 개정 diff(사전 보고에서 제시한 초안)를 적용한다.

### 검증 결과

* 코드 변경 없음(문서/구조 전환만) — `manage.py check` 등 코드 검증 대상 없음.
* STATUS.md의 "구현됨 16개/미구현 28개"는 `config/urls.py`, `accounts/urls.py`, `advisors/urls.py` 실측으로 교차 확인.
* 문서 모순 11건을 발견 시점에 사전 보고로 전부 제시 → Owner가 그중 핵심 2건(SPEC-001 해석)만 명시 승인, 나머지(경로 drift, 43→44 등)는 ADR-006 Consequences에 반영해 승인 후 CLAUDE.md 개정과 함께 정정 예정.
* `.claude/agents/`가 이미 커밋되어 있음을 실측(요청 문서의 갭 #7 기술과 불일치 — 이미 해소된 상태였음), `.github/pull_request_template.md`도 기존재 확인.

### 잔여 리스크

1. **CLAUDE.md 미개정 상태**: ADR-006이 Proposed인 동안 CLAUDE.md §2/§3/§5/§16/§17은 여전히 옛 내용(43개 엔드포인트, 옛 경로명)이다. Owner가 ADR-006을 Accepted로 전환하기 전까지 CLAUDE.md와 STATUS.md/ADR-006 사이의 의도적 불일치가 존재한다.
2. **테스트 0건은 여전히 미해소** — TEST_CRITERIA.md는 판정 기준만 마련했을 뿐, 실제 테스트 코드는 SPEC-001 TASK-001부터 작성된다.
3. **M4-1~M4-4 AIUSAGE 미기록 갭 지속**(STATUS.md §7 문서 부채 #1) — 이번 세션은 이 갭을 메우지 않았다. 다음 세션에서 M4-1~M4-4(커밋 `855d1bf`~`b2eaf90`)를 소급 기록해야 한다.
4. **리뷰 노트 미작성**(`03-milestone3-review.md`, `04-milestone4-review.md`) 갭도 지속.
5. **SPEC 구조의 비용 재평가 필요**: ADR-006 Review Triggers에 명시된 대로, SPEC-001(M4-5) 완료 후 이 4파일 구조가 남은 M4-6~M4-8에도 유효한지 재평가해야 한다.

### 다음 단계 권장

1. Owner: ADR-006 승인(Accepted) 여부 결정 → 승인 시 CLAUDE.md 개정 diff 적용.
2. SPEC-001/TASK-001(concern 생성+목록, #16·#17) test-first 착수.
3. M4-1~M4-4 AIUSAGE 소급 기록(문서 부채 #1) — 별도 세션 권장(코드 검증 없이 로그만 재구성하는 작업이라 리스크 낮음).

---

## 2026-07-08 — M3: 도메인 앱 모델 4종 [위임] + UX 사양

* **작업**: advisors/concerns/advice/notifications 4개 앱 모델 7종 + Admin 등록 + 마이그레이션 생성(앱 단위 커밋 분할). 병렬로 Phase 2 화면 흐름·API-to-screen 매핑 UX 사양 작성
* **AI 도구**: Claude Code (코드+설명 동시) + 서브에이전트 `data-modeler`(모델 정합 리뷰), `frontend-ux-architect`(UX 사양)
* **인간 결정**: M3 정의 승인, taxonomy 공유 배치 수용, 마이그레이션 적용·AC 검증 전부 Owner 직접 수행(showmigrations·sqlmigrate WHERE 절 3종·Admin 7종 조회·soft delete shell 검증), 이해 질문 3개 답변(1·2 부분, 3 통과), 드릴#2·M3 퀴즈·리뷰 노트는 M4 이후로 이월
* **생성 산출물**: `common/taxonomy.py`, `advisors/`·`concerns/`·`advice/`·`notifications/` 앱, 마이그레이션 4종, `docs/ux/01-phase2-screen-flows.md` — 커밋 `e3db9c1`·`de2e3a7`·`7d5e2f0`·`82d5e6c`·`a3823d1`·`05f60b2`
* **검증 결과**: check 0 issues, makemigrations --check No changes, ruff 통과, 부분 유니크 3종 WHERE 절 확인, data-modeler 리뷰 블로커 0(메이저 1건 I-1은 admin status readonly로 즉시 해소), Owner migrate·shell 검증 성공(soft delete 기본 감춤 실측)
* **잔여 리스크**: Owner 결정 대기 — 비익명 표시명 정책(C-6/C-7)·O-1 DomainCategory 확정·UX발 API 개선 4건(M4 전 처리 권고). model.md 문서 drift 6건 기록 대기. 학습 부채 누적(드릴#2·M3 퀴즈 이월 포함)

## 2026-07-07 — M2 마감 문서화

* **작업**: M2 리뷰 노트 작성(explain-first: Owner 선요약 → AI diff 분석), README_AIUSAGE 신설, M3 정의 문서 번호 정리
* **AI 도구**: Claude Code (Fable 5)
* **인간 결정**: 문서 번호 체계 = 마일스톤 번호(`NN-milestoneN-{definition,review}`), M3 승인 보류, WB-1은 M3 착수 전 이월
* **생성 산출물**: `docs/reviews/02-milestone2-review.md`, `README_AIUSAGE.md`, `docs/reviews/03-milestone3-definition.md`(초안, 승인 대기)
* **검증 결과**: 문서 작업 — 코드 변경 없음
* **잔여 리스크**: M2 학습 부채 9건 (리뷰 노트 원장 참조), WB-1 미실시

## 2026-07-05~06 — M2 학습 게이트 (드릴 #1 + 퀴즈)

* **작업**: 장애 드릴 #1 "DB 다운"(chaos-coach 주입·힌트, 진단·복구는 Owner) / 이해 퀴즈 5문(drill-master 출제·채점)
* **AI 도구**: Claude Code 서브에이전트 `chaos-coach`, `drill-master`
* **인간 결정**: 복구 명령 선택(`docker compose up -d db`), 포스트모템 작성, WB-1 다음 세션 이월
* **생성 산출물**: 드릴 채점표·포스트모템, 퀴즈 채점표(42/100), 학습 부채 원장 9건
* **검증 결과**: 드릴 이수(핸즈온 43분, 예산 +13분), db 복구 실측(healthy, /healthz 200)
* **잔여 리스크**: 부채 ④(401/403/409)·⑤(atomic)는 M4 착수 전 재퀴즈 필수

## 2026-07-05 — M2 트랙 B: accounts 도메인 확장 [위임]

* **작업**: `UserRole`/`RoleGrant`/`GoogleIdentity` 모델, `create_superuser` ADMIN 부트스트랩 훅(ADR-003), Django Admin 3종 등록, 마이그레이션 `accounts.0002` 생성
* **AI 도구**: Claude Code (코드+설명 동시 생성, 이해 확인 질문 3개 출제·채점)
* **인간 결정**: 마이그레이션 적용은 Owner 직접 수행, AC 검증(showmigrations·createsuperuser→ADMIN row·Admin 조회) Owner 수행, 이해 질문 답변
* **생성 산출물**: `accounts/{models,managers,admin}.py` 확장, `accounts/migrations/0002_*.py` — 커밋 `76b664e`
* **검증 결과**: `manage.py check` 0 issues, `makemigrations --check` No changes, ruff 통과, sqlmigrate로 제약·인덱스 확인, Owner가 컨테이너에서 migrate 적용 성공
* **잔여 리스크**: M1 시절 생성된 기존 superuser에는 ADMIN UserRole이 소급 생성되지 않음(수동 추가 필요). `active_role`↔`UserRole` 정합은 M4 서비스 레이어에서 강제 예정

## 2026-07-03~05 — M2 트랙 A: 런타임 승격 [소유]

* **작업**: Dockerfile 멀티스테이지(builder/runtime)·비루트(uid 10001)·gunicorn 전환, docker-compose.override.yml dev 경로 분리 — **전량 Owner 손코딩**
* **AI 도구**: Claude Code — 코치 모드(시작 전 체크리스트, 막힘 시 단계적 힌트만) + `ops-reviewer` 서브에이전트 리뷰 3라운드 + gunicorn 버전/보안 사실 검증(PyPI·OSV 실측)
* **인간 결정**: dev/prod 분기 = override 병합 패턴(리스크 #1), runtime에 uv 미탑재, gunicorn 26.0.0 dependencies 추가(§16 승인), `.claude/agents/` 미커밋
* **생성 산출물**: (AI 생성 아님 — Owner 작성) `Dockerfile`, `docker-compose.override.yml`; AI는 리뷰 코멘트만. 커밋 `156ded9`
* **검증 결과**: 1차 블로커 5 → 2차 블로커 1 → 3차 **블로커 0·메이저 0 통과**. 운영 경로 gunicorn `/healthz` 200, `exec app id` uid=10001, 시크릿 전수 grep 무검출 (전부 실측)
* **잔여 리스크**: gunicorn 경로 정적파일 서빙 부재(/admin 정적 404 — M5 문서 명시 예정), FROM 버전 2곳 독립 표기, 브루트포스 방어 Phase 3 이월

## 2026-07-03 — M2 정의 및 승인

* **작업**: 마일스톤 번호 충돌 해소(reviews/01 vs learning/02), M2 통합 정의 문서 작성
* **AI 도구**: Claude Code
* **인간 결정**: 통합형 M2 승인(트랙 A [소유] + 트랙 B [위임]), gunicorn 서드파티 추가 승인(dependencies 그룹), 43개 엔드포인트 로드맵 유지
* **생성 산출물**: `docs/reviews/02-milestone2-definition.md` — 커밋 `8b2c0f8`
* **검증 결과**: 문서 작업 — Owner 승인으로 확정
* **잔여 리스크**: —

## 2026-06-30 — 독립 git 저장소 초기화 + 전략 IP 공개범위 분할 + ruff 도입

### 작업

1. 비밀정보 교차검증: chamneul이 상위 `personal` 저장소에 추적된 적 없음, `.env`/자격증명/하드코딩 비밀값 부재 확인.
2. Public 공개 전략 분석(Data-Driven): 코드/기술 문서는 공개 안전, 사업전략·평가 알고리즘 설계는 별도 IP 범주임을 분석.
3. `docs/1 서비스기획_v1.md` 전략 IP(ELO 점수 설계·조언자 평가 모델·승인 트리)를 공개 요약본 / 비공개 상세본으로 분할 (ADR-004).
4. ruff(lint+format) dev 의존성 도입. 운영 이미지 제외 구조 검증. 코드베이스 check/format 적용.
5. README_AIUSAGE 갱신 후 GitHub Public 저장소 생성·push.

### 사용 도구

* Claude Opus 4.8 (claude-opus-4-8)
* Claude Code CLI

### 인간 결정 (Owner, 2026-06-30)

| ID | 결정 |
| --- | --- |
| G1 | chamneul을 상위 `personal` 저장소에서 분리해 독립 git 저장소로 초기화 |
| G2 | 저장소는 Public 공개. 단 핵심 전략 IP는 비공개 처리 |
| G3 | 전략 문서 처리 = 옵션 B(분할 발행: 공개 요약본 + 비공개 상세본) + ADR-004 기록 |
| G4 | ruff(lint/format)는 dev 의존성으로 먼저 도입 |
| G5 | pytest 등 운영 불필요한 개발자 전용 테스트 패키지는 설치 제외 (테스트는 Django 기본 test runner 사용) |

### 생성된 산출물

신규:

* `docs/adr/ADR-004-strategy-doc-visibility-split.md` — 공개범위 3단계 분류 + 분할 발행 결정
* `docs/_private/1 서비스기획_v1_full.md` — 전략 IP 원본 보존 (gitignored, 비추적)
* `pyproject.toml` `[dependency-groups].dev` + `[tool.ruff]` 설정 블록

수정:

* `docs/1 서비스기획_v1.md` — 공개 요약본으로 교체 (ELO/평가/승인 로직 제거, ADR-004 참조 명시)
* `.gitignore` — `docs/_private/` 추가
* `pyproject.toml`/`uv.lock` — ruff dev 그룹 추가
* ruff format 적용: `accounts/models.py`, `common/uuid7.py`, `config/settings/{base,local,test,prod}.py`, `manage.py` (7개)

### 검증 결과 (전부 실행 완료)

* `git ls-files` → 추적 45→갱신, `.env`/`docs/_private` 추적 0건 ✅
* `git check-ignore` → `.env`·`docs/_private/`·`.venv` 모두 무시됨 ✅
* `uv export --no-dev` → 운영 의존성에 ruff 없음 (dev 그룹 격리 확인) ✅
* `uv run ruff check .` → All checks passed ✅
* `uv run ruff format .` → 7 files reformatted ✅
* `manage.py check` → 0 issues ✅
* `makemigrations --check --dry-run` → No changes detected ✅
* 공개 요약본 IP 누출 grep → ELO/Layer/점수설계/승인트리 키워드 부재 ✅

### 잔여 리스크

1. **`docs/_private/`는 git 백업 부재** — 별도 백업(private Notion/암호화) 권장 (ADR-004 trade-off 명시).
2. **중첩 저장소** — chamneul/.git이 상위 `personal` 저장소 디렉터리 내부에 위치. 상위가 chamneul을 커밋하지 않으므로 동작엔 무해하나, 장기적으로 chamneul을 별도 경로로 분리 이전하는 것이 깔끔.
3. **이전 리스크 해소**: 직전 Milestone 1의 "ruff 미도입"(§16 패키지 게이트) 리스크는 본 세션 G4로 해소됨.
4. **Notion drift 유지** — api.md §7 패치 미반영 상태 지속.

### 다음 단계 권장

1. Milestone 2 — `accounts`의 `UserRole` / `RoleGrant` / `GoogleIdentity` + createsuperuser→ADMIN 훅.
2. CI에 ruff check 게이트 추가 (Phase 3 CI/CD 진입 시).

## 2026-06-29 — Milestone 1: 실행 가능한 Django+PG 골격 + 커스텀 User

### 작업

1. 직전 두 세션(api.md/model.md) 통독 후 다음 단계 보고.
2. 런타임/툴링 결정 수신 및 적용 (아래 인간 결정).
3. uv 가상환경 셋업 가이드 제공 → Owner가 직접 `.venv`(Python 3.13) 생성·검증.
4. 의존성 `django-environ → python-dotenv` 교체 (`uv remove/add`).
5. Milestone 1 코드 작성: 프로젝트 골격(`manage.py`, `config/`), 설정 4분할(`base/local/test/prod`), `common/uuid7.py`, `accounts.User`(+ `UserManager`, admin), `/healthz`, Docker(`Dockerfile`, `docker-compose.yml`, `.dockerignore`), `.env.example`, `.gitignore` 보강.
6. 검증 실행 (아래 검증 결과).
7. `docs/reviews/01-milestone1-skeleton.md` 작성 (§14, 임베디드 학습 포함) + 본 로그 갱신.

### 사용 도구

* Claude Opus 4.8 (claude-opus-4-8)
* Claude Code CLI

### 인간 결정 (Owner, 2026-06-29)

| ID | 결정 |
| --- | --- |
| D1 | UUIDv7 구현 = `uuid_utils.uuid7` (Rust, 앱 레벨 생성; 관리형 RDS/Aurora의 `pg_uuidv7` 설치 차단 회피, 환경 drift 0) |
| D2 | 런타임 = Python 3.13 + Django 5.2 LTS |
| D3 | 의존성 관리 = `pyproject.toml` + uv (lockfile `uv.lock`) |
| D4 | 시스템 Python(`/usr/bin/python3`) 절대 호출 금지 — uv-managed venv 안에서만 작업 |
| D5 | `.env` 로딩 = `python-dotenv` (MVP 경량/직관 우선, 추후 `pydantic-settings` 전환 여지) |
| D6 | 코드 세션마다 `docs/reviews/`에 초급→고급 + DevOps 임베디드 학습 노트 작성 |

### 생성된 산출물

신규: `manage.py`, `config/{__init__,urls,health,wsgi,asgi}.py`, `config/settings/{__init__,base,local,test,prod}.py`, `common/{__init__,uuid7}.py`, `accounts/{__init__,apps,managers,models,admin}.py` + `accounts/migrations/0001_initial.py`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`, `docs/reviews/01-milestone1-skeleton.md`.

수정: `pyproject.toml`/`uv.lock`(django-environ→python-dotenv), `.gitignore`(보강).

### 검증 결과 (전부 실행 완료)

* `uv run` uuid7 → `uuid.UUID` version 7 ✅
* `manage.py check` → 0 issues ✅
* `makemigrations --check --dry-run` → No changes ✅
* `docker compose build` / `up` → db healthcheck healthy, app up ✅
* `migrate`(컨테이너 PG) → `accounts.0001_initial` 포함 전부 OK ✅
* `GET /healthz` → **HTTP 200** `{"status":"ok"}` ✅
* `createsuperuser`(email+nickname, noinput) → 성공, User PK UUIDv7, PBKDF2 해시 ✅

### 잔여 리스크

1. **createsuperuser ADMIN 역할 훅 미구현** — `UserRole` 모델이 없는 단계라 ADR-003의 "첫 superuser=ADMIN row" 훅은 Milestone 2로 이연(코드에 NOTE 명시).
2. **인증 로직 미구현** — login/logout/Google OAuth는 Milestone 3. 현재는 ADR-002 쿠키 정책 baseline만 설정.
3. **운영 서버** — Dockerfile CMD가 `runserver`(로컬 전용). gunicorn 전환 후속.
4. **ruff 미도입** — §16 패키지 게이트로 Owner 확인 후 도입 예정.
5. **Notion drift 유지** — api.md §7 패치 미반영(Owner 직접 작업 권장).
6. **로컬 `.env` 실파일 존재** — dev 값으로 생성됨(gitignore 제외). 운영 값과 무관.

### 다음 단계 권장

1. Milestone 2 — `accounts`의 `UserRole` / `RoleGrant` / `GoogleIdentity` + createsuperuser→ADMIN UserRole 훅.
2. 이후 Milestone 3 — 인증(signup/login/logout/OAuth) + DRF serializer/viewset/permission.

## 2026-06-26 — model.md v1 작성 + CLAUDE.md 헌법 갱신 (2차)

### 작업

1. 6/22 세션 종료 이후 docs 변경분 재확인: `2 mvp-scope.md` → `2 mvp-scope_v1.md` 파일명 변경, `docs/learning/01-api-to-model-and-docker.md` (Owner 학습 세션) 신설, `docs/api.md` 부분 수정 확인.
2. Owner의 model.md 작성 전 8가지 핵심 결정(M1~M8) 및 4가지 production-grade 보완사항(UUIDv7 / soft-delete + 부분 unique / 3단계 expand-contract 마이그레이션 / Read Replica + 인덱스 튜닝) 수신.
3. ADR-001 Decision 2 (SQLite 제거) 갱신.
4. `docs/model.md` v1 작성 — 12 섹션, 10 엔티티 + 1 audit 테이블, Mermaid ERD, DB / 서비스 제약, 인덱스 요약, EKS 인지 마이그레이션 가이드, Read Replica 라우팅, Django Admin 등록 패턴, 검증 체크리스트, 8건 Open Questions.
5. 초기 설계 ADR(ADR-004)를 별도로 도출했다가 Owner 지시에 따라 본문을 CLAUDE.md에 직접 흡수:
   * CLAUDE.md §4 — PG 16+ 전용 + 허용 PG 전용 기능 목록(ArrayField, JSONB, GIN, 부분 unique, UUIDv7, select_for_update) 추가.
   * CLAUDE.md §6.6 — soft-delete 컬럼을 `deleted_at` 로 명시 + partial unique 강제 패턴 코드 예시.
   * CLAUDE.md §16 — 헌법 잠금 허용 세션에 2026-06-26 추가, 해당 두 조항이 본문에 흡수되어 별도 supersession ADR 불요임을 명시.
6. ADR-004 파일 및 모든 참조 제거 (CLAUDE.md / model.md / ADR-001 에서 정리).
7. 본 항목 README_AIUSAGE.md 작성.

### 사용 도구

* Claude Opus 4.7 (claude-opus-4-7)
* Claude Code CLI

### 인간 결정 (Owner)

Owner가 직접 확정한 결정 (2026-06-26):

| ID | 결정 |
| --- | --- |
| M1 | 앱 레이아웃 = CLAUDE.md §3 5개 도메인 앱(`accounts`, `advisors`, `concerns`, `advice`, `notifications`) + `config` + `common`. Feedback은 `advice` 안에, Google OAuth/RoleGrant는 `accounts` 안에. |
| M2 | User 모델 = `AbstractBaseUser + PermissionsMixin` 완전 커스텀. 이메일 단일 로그인. |
| M3 | Soft delete = manager `objects` 가 자동 alive 필터 + `with_deleted()` 명시. |
| M4 | PG 전용 채택, `ArrayField`(고정 타입 배열) + `JSONField`(비정형). SQLite 비사용. ADR-001 수정 + CLAUDE.md §4 흡수 승인. |
| M5 | Enum = `TextChoices` 단일. |
| M6 | PK = UUID (EKS 분산 환경 / 스테이징↔프로덕션 이관 / 멀티 리전 대비). |
| M7 | AdviceHistory = 본문 필드 전체 snapshot per version. |
| M8 | ERD = Mermaid `erDiagram`. |
| 보완 #1 | PostgreSQL 16+ 환경의 **UUIDv7** 시계열 정렬 PK 채택 (B-Tree 페이지 무작위 플러시 회피). |
| 보완 #2 | Soft delete 모델의 unique 제약은 반드시 `WHERE deleted_at IS NULL` partial unique index 로 설계. |
| 보완 #3 | EKS 무중단 배포를 위한 3단계 expand-contract 마이그레이션 원칙을 model.md 마이그레이션 노트에 명시. |
| 보완 #4 | DB 라우팅 / Read Replica / Connection Pooling / 인덱스 튜닝 가이드를 model.md 에 명시. |

CLAUDE.md 직접 수정도 이번 세션에 한해 추가 승인(헌법 잠금 1회 추가 개방). ADR-004 본문은 CLAUDE.md 본문으로 흡수 + ADR-004 파일 및 모든 참조 제거 지시.

### 생성된 산출물

수정:

* `CLAUDE.md` — §4 (PG 16+ 전용 + 허용 PG 기능 목록 추가) / §6.6 (soft-delete `deleted_at` 컨벤션 + partial unique 강제 패턴 코드 예시) / §16 (헌법 잠금에 2026-06-26 세션 추가)
* `docs/adr/ADR-001-local-container-architecture.md` — Decision 2 본문 + Alternative §2 SQLite 항목 (PG 전용 + CLAUDE.md §4 단일 진실원천 명시)
* `docs/model.md` — ADR-004 참조 → CLAUDE.md §4/§6.6 로 치환, §12 References 정리 (이전 단계)

신규:

* `docs/model.md` v1 (이 세션 산출 — 12 섹션, 10 엔티티 + AdviceHistory, Mermaid ERD 포함)

삭제:

* `docs/adr/ADR-004-postgres-only-and-soft-delete-convention.md` (본문이 CLAUDE.md 에 흡수됨)

### 검증 결과

* 코드 변경 없음 — 본 세션은 명세/헌법 정렬.
* `grep -rn "ADR-004"` 잔존 참조 0건 확인.
* 문서 정합성은 M1~M8 + 보완 #1~#4 ↔ CLAUDE.md ↔ model.md 본문 매핑 표(직전 응답 §결정 반영 매트릭스)로 자체 교차 검증.
* 미수행 (다음 코드 세션에서 검증):
  * `python manage.py makemigrations --check --dry-run`
  * `python manage.py migrate` (빈 PG DB 대상)
  * `python manage.py createsuperuser` 후 첫 ADMIN UserRole row 생성 hook 확인
  * `docker compose up -d` + `curl /healthz`

### 잔여 리스크

1. **헌법 잠금 누적 변경**: 6/22 잠금 → 6/26 1회 추가 개방. 누적 형태로 lock-window가 늘어나면 헌법 잠금의 신뢰도가 떨어진다. 다음 변경은 반드시 새 ADR 절차로 가야 한다 (§16 갱신문 명시).
2. **UUIDv7 구현 의존성**: 앱 레벨 헬퍼(`common/uuid7.py`)가 RFC 9562 정확성/스레드 안전성을 보장해야 한다. `uuid_utils` 등 외부 패키지 채택 시 ADR 없이 진입 가능한지 경계가 모호 — 코드 세션 진입 전 1차 결정 필요.
3. **PG 전용 결정의 CI 영향**: 테스트 시 PG 컨테이너 부팅 시간이 CI 빌드를 늘릴 수 있다. testcontainer 최적화는 별도 ADR로 분리.
4. **Open Questions 8건** (model.md §11): `domain_category` enum 값 / `decision_context` 길이 / `ANSWERED → CLOSED` Public API / DELETED advice 재작성 / GIN 인덱스 / Notification URL 정책 / User 정지 흐름 / `pg_uuidv7` 채택 시점. 코드 세션 중 결정.
5. **Notion 원본 drift**: api.md §7 패치 + model 결정(특히 URI 변경, intended_lane 노출 정책) 미반영 상태. Owner 직접 갱신 권장.
6. **검증 미실행**: 모든 결정은 첫 마이그레이션/smoke test 단계에서 실 검증.

### 다음 단계 권장

1. Owner: Notion DB 갱신 (api.md §7 패치 + model.md 결정 반영).
2. UUIDv7 구현 패키지 결정 (자체 구현 vs `uuid_utils` 등).
3. Django scaffolding 세션 진입 — `config/settings/` 분리 + `accounts.User` 첫 마이그레이션부터.

## 2026-06-22 — Notion API v0 정합성 검토 + api.md v1 생성

### 작업

`docs/request/1-onboarding_prompt.md` 와 `docs/request/2-Notion-first_API 명세 검토_prompt.md` 의 지시에 따라:

1. 프로젝트 docs 전체 통독 (CLAUDE.md, ADR-001, mvp-scope.md, 서비스기획 v1, README).
2. Notion DB에서 export된 v0 API 명세 27개 markdown + 엔드포인트 CSV 통독.
3. CLAUDE.md / ADR-001 / MVP scope 기준으로 정합성 검토 (32개 이슈 식별).
4. Owner Decision Questions Q1~Q22 분리 제시 후 답변 수신.
5. 결정 반영을 위한 헌법 문서(CLAUDE.md) + ADR-001 + mvp-scope.md 패치를 항목별 승인 후 적용.
6. ADR-002 (Session 인증 정책), ADR-003 (ADMIN 역할 부여/회수) 신규 작성.
7. `docs/api.md` v1 작성 — 총 43 엔드포인트 (Notion v0 41건 − 토큰재발급 + `/healthz` + 관리자 역할 부여/회수 2건).
8. Notion 원본 갱신을 위한 패치 테이블을 `docs/api.md §7`에 동봉 (Notion DB는 직접 수정하지 않음).
9. `docs/model.md` 작성에 필요한 준비 요약(앱 목록, 모델 후보, FK, enum, 인덱스, unique, soft delete, transaction.atomic) 인라인으로 회신.

### 사용 도구

* Claude Opus 4.7 (claude-opus-4-7)
* Claude Code CLI

### 인간 결정 (Owner)

Owner가 직접 확정한 결정 (2026-06-22):

| ID | 결정 |
| --- | --- |
| Q1 | 인증 = Session(SSR) + HttpOnly Cookie 단일안. JWT/Token 미사용 |
| Q2 | Phase 2 v1 = 명세 전체(43건) 구현 |
| Q3 | `/api/v1/` prefix 유지, CLAUDE.md를 본 세션 한정 갱신 |
| Q4 | 사용자 소유 자원 URI를 `/users/me/{resource}` 로 통일 |
| Q5 | `intended_lane` 필드 유지하되 Public 응답 비노출 (관리자/시스템 참고용) |
| Q6 | 상태값을 CLAUDE.md §6.1/§6.2 5값으로 통일 (PENDING_REVIEW/published/draft/answered/REVIEWED 등 제거) |
| Q7 | 별도 ADMIN 부여 API 정의, grant + revoke 양쪽 |
| Q8 | 조언가의 `advisable_concern_types`는 taxonomy 영문 enum |
| Q9 | 배정 카디널리티 = 1 concern ↔ N advisor |
| Q10 | advisor 1명당 concern 1건은 advice 1개. version은 audit |
| Q11 | 내 고민 상세 조회 = 인증 필요 (본인만) |
| Q12 | 토큰 재발급 API 명세에서 제외 |
| Q13 | 회원가입 = 자동 로그인 (Set-Cookie sessionid) |
| Q14 | 가입 시 nickname 필수 (unique) |
| Q15 | 내 정보 조회 응답에서 `advisor_type` 제거 |
| Q16 | 조언가 신청 거부 사유는 신청자에게 노출 |
| Q17 | grant=POST `/admin/users/{user-id}/roles`, revoke=DELETE `/admin/users/{user-id}/roles/{role}` |
| Q18 | 최초 ADMIN = `python manage.py createsuperuser` |
| Q19 | concern_status = SUBMITTED → ASSIGNED → ANSWERED → CLOSED, soft delete는 별도 flag |
| Q20 | 세션 정책: cookie `sessionid`, HttpOnly + Secure + SameSite=Lax, 만료 14일, 매 요청 슬라이딩 갱신, 로그아웃 시 서버 세션 삭제 |
| Q21 | advice.version = 수정마다 +1, 응답 노출, 별도 audit 테이블 |
| Q22 | advisor `display_name` = nickname과 별개, 신청 시 입력, unique |

문서 수정도 항목별(A-1~A-8 / B-1~B-5 / C-1 / E-1 / E-2)로 Owner가 명시 승인.

### 생성된 산출물

수정:

* `CLAUDE.md` — §4 Auth / §5 MVP Scope / §6.1 intended_lane policy / §6.6 신설 Concern Status / §6.7 신설 Advice Versioning / §7 URI examples / §10 Auth security rules / §16 constitutional lock
* `docs/adr/ADR-001-local-container-architecture.md` — Decision Summary Auth 행 / Decision 4 본문 재작성 / DRF Token 한계 단락 제거 / Auth 구현 원칙 / Final Decision 블록
* `docs/2 mvp-scope.md` — Phase 2 v1 범위 = 43 엔드포인트 명시 한 줄 추가

신규:

* `docs/adr/ADR-002-session-authentication-policy.md`
* `docs/adr/ADR-003-admin-role-grant.md`
* `docs/api.md` v1 — 43 엔드포인트 전체 명세 + URI 변경 매핑 + Notion 갱신 패치 테이블

### 검증 결과

* 코드 변경 없음. 따라서 `python manage.py check` 등 코드 검증은 수행하지 않았다.
* 문서 정합성은 결정 매핑 표로 자체 교차 검증 (Q1~Q22 ↔ CLAUDE.md ↔ ADR-001/002/003 ↔ api.md).
* 미수행 항목(추후 단계에서 검증 필요):
  * `docker compose up -d` 기반 healthz 200 확인
  * `curl /api/v1/users/me/concerns` 흐름 검증
  * Django Admin 데이터 확인
  * Notion 원본 갱신(별도 작업)

### 잔여 리스크

1. **Notion 원본과의 drift**: `docs/api.md §7` 패치 테이블을 Notion에 반영하지 않은 상태로 코드 작업이 시작되면, 명세 source of truth가 분기될 수 있다. 코드 진입 전 Owner의 Notion 갱신이 권장된다.
2. **헌법 문서 잠금**: CLAUDE.md §16에 추가된 constitutional lock 조항에 따라, 이번 세션 이후 CLAUDE.md를 추가 수정하려면 새로운 ADR을 작성해야 한다. 향후 Claude 세션은 이 규칙을 인지하지 못할 수 있으므로, 매 세션 시작 시 CLAUDE.md 통독이 필수.
3. **Open Questions 8건**: `docs/api.md §6` 에 명시된 8개 비-차단 결정 (글자 수 상한, draft 모델링, CLOSED 전이 API, 페이지네이션 size 상한, OAuth nickname 산정 규칙 등)은 코드 작업 중 확정될 필요가 있다.
4. **세션 저장소**: ADR-002는 DB 세션을 Phase 2 기본으로 정함. 트래픽 발생 시 Redis 전환이 필요할 수 있으나 현 시점에서는 의도된 trade-off.
5. **계정 정지/탈퇴 흐름 부재**: 명세 v1은 가입/로그인/로그아웃까지만 다룸. 정지·탈퇴는 Phase 3+ 결정 사항.
6. **자동 알림 채널 없음**: 알림 model + 조회 API 만 v1에 포함. push/email/web socket은 명시적으로 제외.
7. **검증 미실행**: 코드 베이스가 아직 없어 실행 검증을 못함. `docs/model.md` 및 Django scaffolding 이후의 smoke test 단계에서 본 명세의 실현 가능성이 처음으로 검증된다.

### 다음 단계 권장

1. Owner: Notion DB 패치(`docs/api.md §7`) 반영.
2. 별도 세션에서 `docs/model.md` 작성 (본 세션의 model preparation summary를 입력으로 사용).
3. 모델 확정 후 Django scaffolding 시작 (앱 분리 → 모델 → 마이그레이션 → 권한/Serializer/ViewSet → URLConf → Admin 등록 → `/healthz` → smoke test).
