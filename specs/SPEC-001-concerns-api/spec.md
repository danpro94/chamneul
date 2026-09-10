# SPEC-001 — concerns API (M4-5)

> 대상: [docs/api.md](../../docs/api.md) #16~25 (10 엔드포인트). 근거: CLAUDE.md §6.6(Concern Status), model.md §3.6~§3.7(Concern·Assignment), model.md §5(Service-Layer Constraints), `docs/reviews/04-milestone4-definition.md` M4-5 행.
> Status: Draft — Owner 승인 대기 (ADR-006과 함께 승인)

## 1. 배경

`concerns` 앱은 모델·Admin만 존재하고 views/serializers/urls/services 파일이 없다(STATUS.md §3 실측). Concern은 상태 머신(`SUBMITTED → ASSIGNED → ANSWERED → CLOSED`)과 soft delete(`deleted_at`)를 동시에 갖는 이 프로젝트에서 가장 상태 전이가 복잡한 자원이다 — M4 8모듈 중 상태 전이 로직의 첫 실전 구현이므로, 여기서 세운 서비스 레이어 패턴(예: `advisors/services.py`의 atomic 부수효과 패턴)이 이후 M4-6(advice)에도 재사용된다.

## 2. 대상 엔드포인트

| # | Method | Endpoint | Permission |
| --- | --- | --- | --- |
| 16 | POST | `/api/v1/users/me/concerns` | User |
| 17 | GET | `/api/v1/users/me/concerns` | User |
| 18 | GET | `/api/v1/users/me/concerns/{concern-id}` | User |
| 19 | DELETE | `/api/v1/users/me/concerns/{concern-id}` | User |
| 20 | GET | `/api/v1/users/me/assigned-concerns` | Advisor |
| 21 | GET | `/api/v1/users/me/assigned-concerns/{concern-id}` | Advisor |
| 22 | GET | `/api/v1/admin/concerns` | Admin |
| 23 | GET | `/api/v1/admin/concerns/{concern-id}` | Admin |
| 24 | POST | `/api/v1/admin/concerns/{concern-id}/assignments` | Admin |
| 25 | DELETE | `/api/v1/admin/concerns/{concern-id}/assignments/{assignment-id}` | Admin |

## 3. 확정된 해석 (2026-09-09 부트스트랩 Owner 승인)

* **#16~19에 `active_role` 게이팅 없음**: 자기 고민의 생성/목록/상세/삭제는 로그인 사용자면 누구나 가능하다(역할 무관). `active_role=ADVISOR` 컨텍스트를 요구하는 것은 #20·#21뿐이다.
* **`is_deleted`는 파생 응답 필드**: api.md #16·#19·#22 본문이 쓰는 `is_deleted`는 DB 컬럼이 아니라 `deleted_at is not None`의 직렬화 결과다. DB 컬럼은 model.md §3.6·CLAUDE.md §6.6대로 `deleted_at`(nullable datetime)만 존재한다.

## 4. GIVEN/WHEN/THEN

### #16 POST /api/v1/users/me/concerns

* GIVEN 로그인한 사용자
  WHEN `concern_summary`(≤100자) + `concern_type`(taxonomy enum) + 선택 필드로 POST
  THEN 201, `Concern(status=SUBMITTED, deleted_at=None)` 생성, 응답에 `concern_id`·`status`·`message`
* GIVEN `concern_type`이 taxonomy 11종에 없는 값
  WHEN POST
  THEN 400
* GIVEN `concern_type_secondary`가 3개 이상
  WHEN POST
  THEN 400 (model.md §3.6: `size=2` ArrayField)
* GIVEN 비로그인
  WHEN POST
  THEN 401

### #17 GET /api/v1/users/me/concerns

* GIVEN 로그인 사용자가 concern 3건(자기 것 2건 + soft-delete 1건) 보유
  WHEN GET (쿼리 없음)
  THEN 200, `items`에 삭제되지 않은 2건만, `page_info` 포함
* GIVEN `?status=ANSWERED` 쿼리
  WHEN GET
  THEN 해당 상태만 필터
* GIVEN 타인의 concern이 존재
  WHEN GET
  THEN 응답에 포함되지 않음(본인 것만)

### #18 GET /api/v1/users/me/concerns/{concern-id}

* GIVEN 본인 concern, APPROVED advice 1건 + PENDING advice 1건 연결
  WHEN GET
  THEN 200, `approved_advices[]`에 APPROVED 1건만 노출(CLAUDE.md §6.2 — PENDING 비노출)
* GIVEN soft-delete된 본인 concern
  WHEN GET
  THEN 404
* GIVEN 타인의 concern-id
  WHEN GET
  THEN 403 또는 404 (SPEC 결정 필요 — acceptance.md에서 404로 확정: 존재 자체를 숨겨 타인 자원 존재 유무를 노출하지 않음)

### #19 DELETE /api/v1/users/me/concerns/{concern-id}

* GIVEN 본인의 활성 concern
  WHEN DELETE
  THEN 204, `deleted_at`이 현재 시각으로 기록, 연결된 advice/assignment row는 그대로 보존
* GIVEN 이미 soft-delete된 concern
  WHEN DELETE
  THEN 409
* GIVEN 타인의 concern
  WHEN DELETE
  THEN 404

### #20 GET /api/v1/users/me/assigned-concerns

* GIVEN `active_role=ADVISOR`인 사용자에게 활성 배정 2건
  WHEN GET
  THEN 200, 2건 노출(익명 처리 적용된 `concern_summary`)
* GIVEN ADVISOR 역할은 있으나 `active_role=USER`
  WHEN GET
  THEN 403
* GIVEN ADVISOR 역할 자체가 없는 사용자
  WHEN GET
  THEN 403

### #21 GET /api/v1/users/me/assigned-concerns/{concern-id}

* GIVEN 배정받은 advisor 본인
  WHEN GET
  THEN 200, `requester_display_name` 파생 규칙 적용(`display_alias` 우선 → 익명이면 "익명의 요청자" → 비익명이면 계정 `nickname`), `email`·`user_id` 미노출
* GIVEN 배정받지 않은 advisor
  WHEN GET
  THEN 403

### #22 GET /api/v1/admin/concerns

* GIVEN concern 5건(그 중 2건 soft-delete)
  WHEN `?include_deleted=false`(기본값)로 GET
  THEN 3건만
  WHEN `?include_deleted=true`로 GET
  THEN 5건 전부, 각 항목 `is_deleted` 파생 필드 포함

### #23 GET /api/v1/admin/concerns/{concern-id}

* GIVEN concern에 활성 배정 1건 + 비활성 배정 1건 + advice 2건(상태 무관)
  WHEN GET
  THEN 200, `assignments[]` 2건 전부(active 여부 무관), `advices[]` 2건 전부(status 무관 — admin은 §6.2 제약 없음)

### #24 POST /api/v1/admin/concerns/{concern-id}/assignments

* GIVEN `SUBMITTED` 상태 concern + APPROVED ADVISOR 역할 보유 사용자
  WHEN POST `{advisor_user_id, triage_decision}`
  THEN 201, `Assignment` 생성, `concern.status`가 `ASSIGNED`로 전이, `ASSIGNMENT_CREATED` 알림 발송(수신자: advisor)
* GIVEN 이미 `ASSIGNED` 상태 concern에 추가 advisor 배정(1 concern ↔ N advisor 허용, api.md Q9)
  WHEN POST
  THEN 201, concern.status는 `ASSIGNED` 유지(이미 전이됨 — 재전이 아님)
* GIVEN 동일 (concern, advisor)에 이미 활성 배정 존재
  WHEN POST
  THEN 409 (model.md 부분 유니크 `assignment_concern_advisor_unique_active`)
* GIVEN concern이 `CLOSED` 또는 soft-delete
  WHEN POST
  THEN 409

### #25 DELETE /api/v1/admin/concerns/{concern-id}/assignments/{assignment-id}

* GIVEN concern에 활성 배정이 이 1건뿐
  WHEN DELETE
  THEN 204, `assignment.is_active=False`, `concern.status`가 `ASSIGNED → SUBMITTED`로 되돌아감
* GIVEN concern에 활성 배정이 2건 중 1건 해제
  WHEN DELETE
  THEN 204, concern.status는 `ASSIGNED` 유지(다른 활성 배정이 남아있음)
* GIVEN 이미 비활성인 assignment
  WHEN DELETE
  THEN 409

## 5. Non-Goals (Phase 2 v1 명시적 비범위)

* `ANSWERED → CLOSED` 사용자 API — D-4 미결, 권고안은 Admin 전용 처리(신규 API 없음). 본 SPEC은 CLOSED 전이 API를 구현하지 않는다.
* Advice 생성/조회(#26~33) — SPEC-002(M4-6) 대상. 본 SPEC은 #18의 `approved_advices[]` 서브 필드만 (기존 Advice row를 읽기만 하고 쓰지 않음 — 단, M4-5 시점에 Advice 모델·row가 아직 없을 수 있으므로 빈 배열 반환으로 시작 가능).
* 알림 생성 자체(#24의 `ASSIGNMENT_CREATED`)는 `notifications.Notification` row를 쓰지만, 알림 조회 API(#39~41)는 SPEC 밖.
* 배정 매칭 알고리즘 — CLAUDE.md §5 Deferred, Admin이 수동으로 `advisor_user_id`를 지정.
* concern 수정(PATCH) API — api.md에 정의되지 않음(생성 후 불변, 삭제만 가능).

## 6. 의존성

* `AdvisorApplication.status=APPROVED` 사용자만 #24의 `advisor_user_id`로 지정 가능해야 하는지 여부 — model.md §5는 "APPROVED ADVISOR 역할 보유"라고만 하므로, `UserRole(role=ADVISOR)` 존재 여부로 검사(승인된 신청을 거쳐야만 이 role이 생기므로 간접 충족).
* `common/permissions.py`의 `IsAdmin`을 재사용(신규 permission 클래스는 advisor 배정 확인용 `IsAssignedAdvisor` 1종만 추가 — plan.md 참조).
