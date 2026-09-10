# SPEC-002 — advice + feedback API (M4-6)

> 대상: [docs/api.md](../../docs/api.md) #26~38 (13 엔드포인트). 근거: CLAUDE.md §6.2(Advice 상태)·§6.3(Feedback 상태)·§6.4(알림)·§6.6(Concern 전이)·§6.7(Advice 버전), model.md §3.8~§3.10·§5, `docs/reviews/04-milestone4-definition.md` M4-6 행.
> Status: Draft — Owner 승인 대기 (§7의 결정 4건 포함)

## 1. 배경

`advice` 앱은 모델 3종(`Advice`, `AdviceHistory`, `Feedback`)과 Admin만 있고 views/serializers/urls/services가 없다. SPEC-001(concerns)이 "자원 소유와 배정"을 다뤘다면, SPEC-002는 **이 서비스의 본체**를 다룬다:

* **다주체 가시성** — 같은 advice 한 건을 조언 작성자 / 고민 작성자 / 관리자가 서로 다른 필드로 본다(§6.2: 사용자에겐 APPROVED만).
* **버전 관리** — 수정마다 `version` +1 및 `AdviceHistory` 스냅샷(§6.7).
* **낙관적 잠금** — 관리자 리뷰 중 조언가가 수정하면 412(D-3).
* **연쇄 부수효과** — 승인 한 번이 `Advice.status` + `Concern.status` + `Notification` 세 곳을 건드린다.

SPEC-001에서 확립한 패턴(서비스 레이어가 상태 전이·부수효과 소유, `transaction.atomic` + `select_for_update`, 벌크 조회로 N+1 회피, `assertNumQueries`로 고정)을 그대로 재사용한다.

## 2. 대상 엔드포인트

| # | Method | Endpoint | Permission |
| --- | --- | --- | --- |
| 26 | GET | `/api/v1/users/me/advices` | User (고민 작성자) |
| 27 | GET | `/api/v1/advices/{advice-id}` | Mixed (작성자 / 고민 작성자 / Admin) |
| 28 | POST | `/api/v1/concerns/{concern-id}/advices` | Advisor (배정된 경우만) |
| 29 | PATCH | `/api/v1/advices/{advice-id}` | Advisor (작성자) |
| 30 | DELETE | `/api/v1/advices/{advice-id}` | Advisor (작성자) |
| 31 | GET | `/api/v1/users/me/advices-written` | Advisor |
| 32 | GET | `/api/v1/admin/advices` | Admin |
| 33 | PATCH | `/api/v1/admin/advices/{advice-id}/review` | Admin |
| 34 | POST | `/api/v1/advices/{advice-id}/feedbacks` | User (고민 작성자) |
| 35 | GET | `/api/v1/users/me/feedbacks` | User |
| 36 | GET | `/api/v1/admin/feedbacks` | Admin |
| 37 | GET | `/api/v1/admin/feedbacks/{feedback-id}` | Admin |
| 38 | PATCH | `/api/v1/admin/feedbacks/{feedback-id}` | Admin |

## 3. 핵심 도메인 규칙 (구현이 반드시 강제할 것)

| 규칙 | 출처 |
| --- | --- |
| 사용자(고민 작성자)에게는 **APPROVED advice만** 노출 — 목록·상세·카운트 어디에도 다른 상태가 새지 않는다 | CLAUDE.md §6.2 |
| advisor 1명당 concern 1건은 **advice 1개** (DELETED 제외 부분 유니크) | Q10, model.md §3.8 |
| 작성 권한: 해당 concern에 **active 배정**을 가진 advisor만 | model.md §5 |
| 수정/삭제 권한: **작성자 본인 + status ∈ {PENDING, REVIEWING}** | api.md #29·#30 |
| 수정 시 `version` +1 + `AdviceHistory`에 **직전 본문** 스냅샷 | CLAUDE.md §6.7 |
| 리뷰 전이: `PENDING\|REVIEWING → APPROVED\|REJECTED` | api.md #33 |
| 승인 부수효과: `ADVICE_APPROVED` 알림(→고민 작성자) + concern `→ ANSWERED` | §6.4, §6.6 |
| 반려 부수효과: `ADVICE_REJECTED` 알림(→advisor), 사유 필수(422) | §6.4, api.md #33 |
| 피드백: advice가 APPROVED + 본인이 고민 작성자 + 미작성(1회) | api.md #34 |
| 피드백 전이: `SUBMITTED → REVIEWED → ARCHIVED` (역방향 불가) | §6.3, api.md #38 |

## 4. draft 모델 (D-3 해석 확정 필요 — §7 결정 1)

api.md #28은 draft를 **별도 상태가 아니라 플래그**로 정의한다: `submit=false`면 `status=PENDING`을 유지한 채 `is_submitted=False`. 따라서 `PENDING`은 두 가지를 뜻한다.

| 조합 | 의미 |
| --- | --- |
| `status=PENDING`, `is_submitted=False` | 조언가가 작성 중인 초안. **관리자에게 보이면 안 된다.** |
| `status=PENDING`, `is_submitted=True` | 제출됨. 관리자 리뷰 대기열. |

## 5. GIVEN/WHEN/THEN (요약)

### #28 조언 작성

* GIVEN active 배정을 가진 advisor / WHEN `directional_guidance`로 POST / THEN 201, `status=PENDING`, `version=1`, `is_submitted`는 `submit` 값
* GIVEN 배정되지 않은 advisor / WHEN POST / THEN 403
* GIVEN 이미 (concern, advisor) advice 존재 / WHEN POST / THEN 409
* GIVEN 직전 advice가 `DELETED` / WHEN POST / THEN 201 (부분 유니크가 DELETED를 제외하므로 재작성 허용)
* GIVEN `directional_guidance` 1501자 / WHEN POST / THEN 400

### #27 조언 상세 (3주체 분기)

* GIVEN 작성자 본인 / THEN 200, 상태 무관, `is_submitted`·`reject_reason` 노출
* GIVEN 고민 작성자 + advice가 APPROVED / THEN 200, `reject_reason` **미노출**
* GIVEN 고민 작성자 + advice가 PENDING / THEN **403** (§6.2 — 존재를 알려도 내용은 못 본다)
* GIVEN ADMIN / THEN 200, 상태 무관 + `reject_reason` 노출
* GIVEN 제3자 / THEN 403

### #29 수정 / #30 삭제

* GIVEN 작성자 + PENDING / WHEN 본문 PATCH / THEN 200, `version` 2, `AdviceHistory`에 v1 본문 1행
* GIVEN 작성자 + APPROVED / WHEN PATCH / THEN 409
* GIVEN 작성자 + PENDING / WHEN DELETE / THEN 204, `status=DELETED`
* GIVEN APPROVED / WHEN DELETE / THEN 409

### #33 리뷰 (핵심)

* GIVEN PENDING·제출됨 advice, `expected_version`이 현재와 일치 / WHEN `decision=approved` / THEN 200, `status=APPROVED`, concern `→ANSWERED`, 고민 작성자에게 `ADVICE_APPROVED` 알림
* GIVEN `expected_version` 불일치 / WHEN 리뷰 / THEN **412** (리뷰 중 조언가가 수정함)
* GIVEN `decision=rejected`, `reason` 없음 / THEN 422
* GIVEN 이미 APPROVED / THEN 409
* GIVEN `decision=rejected` / THEN advisor에게 `ADVICE_REJECTED` 알림, concern 상태 불변

### #34 피드백 작성

* GIVEN 고민 작성자 + advice APPROVED + 미작성 / WHEN `score=5` / THEN 201
* GIVEN advice가 PENDING / THEN 403
* GIVEN 고민 작성자가 아님 / THEN 403
* GIVEN 이미 피드백 존재 / THEN 409
* GIVEN `score=6` / THEN 400

## 6. Non-Goals

* **APPROVED advice의 삭제·수정 흐름** — api.md #30이 Phase 2 미제공으로 명시(Django Admin 처리).
* **AdviceHistory 조회 API** — CLAUDE.md §6.7: Phase 2에서 공개 API로 노출하지 않는다.
* **피드백 수정/삭제** — api.md #34: "제출 후 수정/삭제 불가".
* **trust score / outcome tracking** — Phase 3 (CLAUDE.md §5).
* **알림 조회 API(#39~41)** — SPEC-003(M4-7). 본 SPEC은 `Notification` row를 **쓰기만** 한다.
* **Concern `CLOSED` 전이** — D-4 미결, 본 SPEC 범위 밖.

## 7. Owner 결정 필요 (착수 전 확인 요망)

api.md를 코드로 옮기는 과정에서 **명세가 답하지 않는** 지점 4건이 나왔다. 전부 실제 동작이 갈리는 지점이라 추측으로 넘기지 않는다.

| # | 쟁점 | 후보 | 권고 |
| --- | --- | --- | --- |
| **1** | **#32 관리자 리뷰 목록에 draft(`is_submitted=False`)가 포함되는가?** api.md #32는 `status?` 기본값을 `PENDING`이라고만 하고 `is_submitted`를 언급하지 않는다. 그대로 두면 조언가가 **제출한 적 없는 초안이 관리자 리뷰 대기열에 뜨고, 승인까지 가능**하다. | (a) 항상 제외 (b) 기본 제외 + `include_drafts=true`로 조회 (c) 명세대로 포함 | **(a) 항상 제외.** 초안은 정의상 리뷰 대상이 아니다. #33도 `is_submitted=False`면 거부(409)해 직접 호출 우회를 막는다 |
| **2** | **#29에서 `submit=false→true`만 바꿀 때도 `version`이 +1 되는가?** api.md #29는 "수정 시 version +1"이라고만 한다. | (a) 본문이 바뀔 때만 +1 (b) 모든 PATCH에 +1 | **(a).** `version`은 §6.7상 "본문 이력" 카운터다. 제출 토글은 본문 변경이 아니므로 히스토리 행을 만들 이유가 없다 |
| **3** | **#33 승인 시 concern이 `CLOSED`면 `ANSWERED`로 되돌리는가?** api.md는 "아직 ANSWERED가 아닌 경우" 전이라고만 쓴다. 문자 그대로면 CLOSED→ANSWERED 역행이 발생한다. | (a) `ASSIGNED`일 때만 전이 (b) 문자 그대로 | **(a).** §6.6의 상태 머신에 CLOSED→ANSWERED 간선이 없다. CLOSED는 종결 상태 |
| **4** | **#27에서 고민 작성자가 APPROVED 아닌 advice를 조회하면 403인가 404인가?** api.md #27은 403만 나열한다. | (a) 403 (b) 404 | **(a) 403 — 명세 문언 유지.** 단 SPEC-001 #18(타인 고민=404)과 비대칭이라는 점은 인지하고 간다. 근거: 고민 작성자는 자기 고민에 조언이 달렸다는 사실 자체는 알 수 있는 위치(#18의 `approved_advices`가 개수를 드러냄) |

## 8. 의존성

* `common/permissions.py`의 `IsAdmin`·`IsActiveAdvisor` 재사용. 신규 permission 클래스는 만들지 않는다(주체 분기가 3갈래라 객체 수준 판정은 서비스에서 처리 — SPEC-001 #21에서 검증된 방식).
* `concerns.services.display_names_by_advisor()` 재사용 — #26·#27의 `advisor_display_name`.
* `common/exceptions.py`에 **412용 예외 클래스 추가 필요** (현재 `Conflict`/`UnprocessableEntity`만 존재. `_STATUS_TO_CODE`에는 412가 이미 매핑되어 있음).
