# SPEC-003 — notifications + admin roles (M4-7 + M4-8)

> 대상: [docs/api.md](../../docs/api.md) #39~43 (5 엔드포인트). 근거: CLAUDE.md §6.4(알림 타입), ADR-003(역할 부여/회수), model.md §3.2~§3.3·§3.11, api.md #39의 `target_url` 규약(C-10).
> Status: Draft — Owner 승인 대기 (§7의 결정 3건 포함)

## 1. 배경 — 왜 두 모듈을 하나로 묶는가

M4-7(알림 3개)과 M4-8(역할 2개)은 각각 SPEC 하나를 세우기엔 작다. SPEC-001은 10개, SPEC-002는 13개였다. 둘을 묶는 실질적 이유는 크기만이 아니다.

* **역할 회수(#43)가 `active_role`을 강등한다.** 이는 2026-09-14 점검의 **A-3**이자 SPEC-002 보안 리뷰의 관찰 o-2였다 — 회수 시 강등이 없으면 회수된 조언가가 #29~#31을 계속 통과한다. api.md #43 Side Effect에 이미 명시돼 있으므로 **새 결정이 아니라 구현·검증 대상**이며, 이 SPEC이 그 부채를 닫는다.
* **알림은 이 프로젝트에서 유일하게 "쓰기만 하고 읽지 않던" 데이터다.** SPEC-001(`ASSIGNMENT_CREATED`)과 SPEC-002(`ADVICE_APPROVED`/`ADVICE_REJECTED`), M4-4(`ADVISOR_APPLICATION_*`)가 행을 쌓아왔고, 읽는 쪽이 없어 **필드 설계가 한 번도 검증되지 않았다.** #39~41이 그 첫 소비자다.

이 SPEC이 끝나면 **44/44 엔드포인트**가 되어 M4가 종료되고 M5(스모크 + 문서 정리)로 넘어간다.

## 2. 대상 엔드포인트

| # | Method | Endpoint | Permission |
| --- | --- | --- | --- |
| 39 | GET | `/api/v1/notifications` | Authenticated (수신자) |
| 40 | GET | `/api/v1/notifications/{notification-id}` | Authenticated (수신자) |
| 41 | PATCH | `/api/v1/notifications/{notification-id}/read` | Authenticated (수신자) |
| 42 | POST | `/api/v1/admin/users/{user-id}/roles` | Admin |
| 43 | DELETE | `/api/v1/admin/users/{user-id}/roles/{role}` | Admin |

## 3. 핵심 도메인 규칙 (구현이 반드시 강제할 것)

| 규칙 | 출처 |
| --- | --- |
| 알림은 **수신자 본인만** 조회·읽음 처리 가능 | api.md #39~41 |
| 알림 타입은 **5종 고정** — 이 SPEC은 새 타입을 만들지 않는다 | CLAUDE.md §6.4 |
| 역할 부여/회수 대상은 `ADMIN`/`ADVISOR`뿐 — **`USER`는 대상이 아니다** | ADR-003 §2 |
| **자기 자신의 ADMIN 회수 금지** → 409 | ADR-003 §2 |
| **마지막 ADMIN 회수 금지** → 409 (시스템 잠금 방지) | ADR-003 §2 |
| 부여·회수마다 **`RoleGrant` 감사 행** 1건 | ADR-003 §3 |
| 역할 부여/회수는 **알림을 보내지 않는다** | ADR-003 §4, api.md #42 |
| **ADVISOR 회수 시 `active_role`이 ADVISOR였다면 USER로 강등** | api.md #43, 점검 A-3 |

## 4. GIVEN/WHEN/THEN (요약)

### #39 알림 목록

* GIVEN 내 알림 3건(읽음 1, 미읽음 2) + 타인 알림 1건 / WHEN GET / THEN 200, 내 것 3건만, `unread_count=2`
* GIVEN `?is_read=false` / THEN 미읽음 2건만 (단 `unread_count`는 필터와 무관하게 **전체 미읽음 수**)
* GIVEN `?type=ADVICE_APPROVED` / THEN 해당 타입만
* GIVEN 비로그인 / THEN 401

### #40 알림 상세

* GIVEN 수신자 본인 / THEN 200, `read_at` 포함
* GIVEN 타인의 알림 / THEN **404** (§7 결정 2 — 존재를 숨긴다)
* GIVEN 없는 id / THEN 404

### #41 읽음 처리

* GIVEN 미읽음 알림 / WHEN PATCH / THEN 200, `is_read=true`, `read_at` 기록
* GIVEN 이미 읽은 알림 / WHEN PATCH / THEN **200 (멱등)** — api.md 상태 집합에 409가 없다. `read_at`은 최초 값 유지
* GIVEN 타인의 알림 / THEN 404

### #42 역할 부여

* GIVEN ADVISOR 미보유 사용자 / WHEN `{"role":"ADVISOR"}` / THEN 201, `UserRole` 생성 + `RoleGrant(GRANT)` 1건, **알림 없음**
* GIVEN 이미 보유한 역할 / THEN 409
* GIVEN `role="USER"` / THEN 400 (serializer choices)
* GIVEN 없는 user-id / THEN 404
* GIVEN Admin 아닌 사용자 / THEN 403

### #43 역할 회수 (이 SPEC의 핵심)

* GIVEN ADVISOR 보유 + `active_role=ADVISOR` / WHEN 회수 / THEN 204, `UserRole` 삭제 + `RoleGrant(REVOKE)` 1건, **`active_role`이 USER로 강등** ← A-3
* GIVEN ADVISOR 보유 + `active_role=USER` / WHEN 회수 / THEN 204, `active_role` 불변
* GIVEN 자기 자신의 ADMIN 회수 / THEN 409
* GIVEN 마지막 ADMIN 회수 / THEN 409
* GIVEN 보유하지 않은 역할 회수 / THEN 409
* GIVEN 회수 직후 조언가가 #29(조언 수정) 호출 / THEN **403** — 강등이 실제로 권한을 닫는지 end-to-end 확인

## 5. 이번 SPEC이 닫는 부채

| 부채 | 출처 | 이 SPEC에서 |
| --- | --- | --- |
| A-3 / o-2 — 역할 회수 시 `active_role` 강등 부재 | 2026-09-14 점검, SPEC-002 보안 리뷰 | #43 구현 + end-to-end 테스트 |
| 알림 필드 설계가 소비자 없이 검증되지 않음 | SPEC-001·002가 쓰기만 함 | #39~41이 첫 소비자 — `target_url` 규약(C-10)이 실제로 동작하는지 확인 |
| `accounts` 앱 테스트 0건 | M4-1~M4-3이 test-first 이전 구현 | #42/#43이 `accounts.services`를 건드리므로 그 경로만이라도 커버 |

## 6. Non-Goals

* **알림 일괄 읽음** — api.md 비범위(UX §8-6, M5 재검토).
* **알림 생성 API** — 알림은 서비스 레이어 부수효과로만 생성된다(§6.4). 공개 생성 엔드포인트 없음.
* **새 알림 타입** — 5종 고정. 역할 부여/회수도 알림을 보내지 않는다(ADR-003 §4).
* **사용자 계정 정지/탈퇴** — Phase 3+.
* **역할 회수 시 활성 배정 자동 해제** — §7 결정 3 참조(관리자가 #25로 명시 해제).
* **알림 푸시/이메일 채널** — Phase 2는 조회 API만.

## 7. Owner 결정 필요 (착수 전 확인 요망)

| # | 쟁점 | 후보 | 권고 |
| --- | --- | --- | --- |
| **1** | **#40의 `actor` 필드를 노출하는가?** api.md #40은 `actor?: { user_id?, display_name? }`를 명세한다. 그런데 **5개 알림 타입 전부 actor가 관리자다**(승인·반려·배정 모두 admin 행위). 그대로 구현하면 **고민 작성자·조언가에게 관리자 계정 id가 노출된다.** SPEC-002 보안 리뷰가 "SPEC-003 응답 필드 설계 시 반드시 재검토"로 지목한 지점 | (a) **`actor` 미노출** — Phase 2의 5개 타입 중 의미 있는 peer actor가 없다 (b) `display_name`만 노출, `user_id` 제외 (c) api.md 그대로 | **(a).** "관리자가 승인했습니다"에 관리자 신원이 필요하지 않다. 노출하지 않는 편이 §8(의도적 필드 선별)에도 맞고, 나중에 필요해지면 추가가 제거보다 쉽다 |
| **2** | **타인의 알림 조회 시 403인가 404인가?** api.md #40/#41 Status 집합에 둘 다 있다 | (a) **404** — 쿼리셋을 `recipient=user`로 좁혀 존재 자체를 숨김 (SPEC-001 #18과 같은 패턴) (b) 403 | **(a).** 알림은 전적으로 사적인 자원이라 id의 존재조차 알려줄 이유가 없다. #27이 403인 것은 "고민 작성자는 자기 고민에 조언이 달린 걸 안다"는 근거가 있었으나, 알림엔 그런 근거가 없다 |
| **3** | **ADVISOR 회수 시 활성 배정(Assignment)을 어떻게 하는가?** api.md #43은 `active_role` 강등만 명시하고 배정은 언급하지 않는다. 강등 후 그 조언가는 #20·#21·#28~#30을 통과하지 못하므로 **배정은 남되 아무것도 할 수 없는 상태**가 된다. 해당 concern은 `ASSIGNED`로 유지된다 | (a) **그대로 둔다** — 관리자가 #25로 명시 해제. 배정 이력은 감사 기록(model.md §3.7) (b) 자동 해제 + concern 상태 되돌림 + 알림 | **(a).** 역할 회수 한 번이 배정 해제·상태 전이·알림까지 연쇄하면 부수효과가 과도하게 숨는다. 다만 "배정은 있는데 활동 불가"인 조언가가 생기므로, **#23 admin 상세에서 식별 가능하다는 점을 api.md에 명시**하고 M5 스모크 항목에 넣는다 |

## 8. 의존성

* `common/permissions.py`의 `IsAdmin` 재사용(#42/#43). #39~41은 `IsAuthenticated`만 — 수신자 판정은 쿼리셋 스코프로 처리(결정 2).
* `accounts.models`의 `UserRole`·`RoleGrant`·`RoleGrantAction`·`ActiveRole`, `accounts.services.held_roles()` 재사용.
* **`.claude/rules/coding.md`의 상태 전이 규칙 적용 대상**: #41(읽음 처리), #42/#43(역할 변경)은 전부 상태를 바꾸므로 `atomic` + `select_for_update(of=("self",))` + `update_fields` 3종을 갖춘다. 특히 **#43은 "마지막 ADMIN" 검사와 삭제 사이에 경합이 있으면 마지막 관리자가 사라질 수 있다** — 이 SPEC에서 가장 잠금이 중요한 지점이다.
* 마이그레이션 없음 — `Notification`·`UserRole`·`RoleGrant` 모두 M2/M3에서 확정.
