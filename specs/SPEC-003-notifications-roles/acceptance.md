# SPEC-003 — acceptance criteria

TEST_CRITERIA.md §2(핵심 3축)·§3(공통 체크리스트)을 SPEC-003에 적용한 판정 기준. 전항 Django 테스트로 자동 판정한다.

## AC-1. 알림 목록 (#39)

- [ ] 내가 수신자인 알림만 반환, 타인 수신 알림 미노출
- [ ] `unread_count`가 미읽음 개수와 일치
- [ ] `?is_read=false` 필터 시 미읽음만 반환, 그러나 **`unread_count`는 전체 미읽음 수 그대로**
- [ ] `?type=ADVICE_APPROVED` 필터 동작
- [ ] `?is_read=false&type=...` 복합 필터 동작
- [ ] 최신순(`-created_at`) 정렬
- [ ] `page_info` 포함 (`page`/`size`/`total`/`total_pages`)
- [ ] 알림 0건인 사용자 → 200, `items=[]`, `unread_count=0`
- [ ] 비로그인 → 401
- [ ] 목록 쿼리 수가 건수와 무관하게 상수 (`assertNumQueries`)

## AC-2. 알림 상세 (#40)

- [ ] 수신자 본인 → 200
- [ ] 응답에 `read_at` 포함 (미읽음이면 `null`)
- [ ] 응답에 `notification_id`·`type`·`title`·`message`·`target_url`·`is_read`·`created_at` 포함
- [ ] **응답에 관리자 신원(`actor.user_id` 등)이 포함되지 않는다** (결정 1(a))
- [ ] 타인의 알림 → **404** (403 아님 — 결정 2)
- [ ] 존재하지 않는 notification-id → 404
- [ ] 비로그인 → 401

## AC-3. 알림 읽음 처리 (#41)

- [ ] 미읽음 알림 PATCH → 200, `is_read=true`, `read_at`이 null이 아님
- [ ] 이미 읽은 알림 재요청 → **200**, `read_at`이 **최초 값 그대로**(갱신되지 않음)
- [ ] 타인의 알림 → 404
- [ ] 존재하지 않는 id → 404
- [ ] 비로그인 → 401
- [ ] 읽음 처리 후 #39의 `unread_count`가 1 감소
- [ ] 읽음 처리가 다른 알림의 `is_read`를 바꾸지 않는다

## AC-4. 역할 부여 (#42)

- [ ] ADVISOR 부여 → 201, `UserRole(user, ADVISOR)` 1행 생성
- [ ] `RoleGrant(action=GRANT, acted_by=actor)` 1행 생성, `reason` 저장
- [ ] 응답 `roles[]`가 변경 후 보유 역할(`["USER","ADVISOR"]`)
- [ ] 응답에 `user_id`·`granted_role`·`granted_at`·`granted_by` 포함
- [ ] ADMIN 부여 → 201 (동일 규칙)
- [ ] **`Notification` 행이 생성되지 않는다** (ADR-003 §4)
- [ ] 대상의 `active_role`이 변하지 않는다
- [ ] 이미 보유한 역할 → 409, 중복 `RoleGrant` 미생성
- [ ] `role="USER"` → 400
- [ ] 정의되지 않은 role 문자열 → 400
- [ ] 존재하지 않는 user-id → 404
- [ ] Admin 아닌 사용자 → 403 / 비로그인 → 401

## AC-5. 역할 회수 (#43) ★ A-3

- [ ] ADVISOR 회수 → 204, `UserRole` 행 삭제
- [ ] `RoleGrant(action=REVOKE, acted_by=actor)` 1행 생성
- [ ] **대상의 `active_role`이 ADVISOR였다면 USER로 강등된다**
- [ ] 대상의 `active_role`이 USER였다면 그대로 USER
- [ ] ADMIN 회수(다른 관리자, 마지막 아님) → 204
- [ ] ADMIN 회수는 `active_role`을 건드리지 않는다 (ADMIN은 active_role이 될 수 없음)
- [ ] **`Notification` 행이 생성되지 않는다**
- [ ] 자기 자신의 ADMIN 회수 → 409
- [ ] 마지막 ADMIN 회수 → 409
- [ ] superuser 1명 + `UserRole` ADMIN 1명 상태에서 그 ADMIN 회수 → 409 (보수적 판정, plan §2 근거 2)
- [ ] 보유하지 않은 역할 회수 → 409
- [ ] 잘못된 `{role}` 경로값(`USER`, `owner` 등) → 404
- [ ] 존재하지 않는 user-id → 404
- [ ] Admin 아닌 사용자 → 403 / 비로그인 → 401
- [ ] **409로 끝난 요청은 부분 상태를 남기지 않는다** — `RoleGrant` 미생성, `UserRole` 미삭제, `active_role` 불변

## AC-6. 접근 제어 전수 (§10 object-level access control)

- [ ] #39·#40·#41 어디서도 타인의 알림이 노출되지 않는다 (3개 지점 개별 검증)
- [ ] #42·#43은 `IsAdmin`으로 보호된다 (Admin 아님 → 403, 2개 지점)
- [ ] 알림 응답에 수신자·유발자의 이메일이 노출되지 않는다

## AC-7. A-3 end-to-end — 회수가 실제로 권한을 닫는가 ★

- [ ] 배정된 조언가가 조언 작성 → 201
- [ ] 관리자가 그 조언가의 ADVISOR 회수 → 204
- [ ] 같은 조언가가 자기 조언 수정(#29) 시도 → **403**
- [ ] 같은 조언가가 배정 고민 목록(#20) 조회 → **403**
- [ ] 이미 작성된 조언 데이터는 삭제되지 않는다 (회수는 권한 회수지 데이터 삭제가 아님)
- [ ] 회수 후에도 해당 concern의 배정은 남아 있고 concern 상태는 `ASSIGNED` 유지 (결정 3(a) — 의도된 동작)

## AC-8. C-10 `target_url` 왕복 — 알림의 첫 소비자 검증 ★

5개 타입 각각에 대해, 실제 서비스 경로로 알림을 발생시킨 뒤:

- [ ] `ADVICE_APPROVED` → `target_url`을 고민 작성자 세션으로 GET → 200
- [ ] `ADVICE_REJECTED` → `target_url`을 조언가 세션으로 GET → 200
- [ ] `ADVISOR_APPLICATION_APPROVED` → `target_url`을 신청자 세션으로 GET → 200
- [ ] `ADVISOR_APPLICATION_REJECTED` → `target_url`을 신청자 세션으로 GET → 200
- [ ] `ASSIGNMENT_CREATED` → `target_url`을 조언가 세션(active_role=ADVISOR)으로 GET → 200
- [ ] 각 `target_url`이 `/api/v1/`로 시작하고 trailing slash·쿼리스트링이 없다
- [ ] `payload`에 api.md C-10 표의 키가 들어 있다

## AC-9. 도메인 불변식

- [ ] `NotificationType`에 새 값이 추가되지 않았다 (CLAUDE.md §6.4 — 5종 고정)
- [ ] `UserRole`에 `role="USER"` 행이 어떤 경로로도 생기지 않는다 (model.md §3.2)
- [ ] `RoleGrant`는 append-only — 이 SPEC의 어떤 코드도 `RoleGrant`를 update/delete하지 않는다
- [ ] 마이그레이션이 생성되지 않는다 (`makemigrations --check` → No changes)

## AC-10. Mock-Up UI 시각 확인 (Owner 요구사항)

- [ ] 알림 목록 화면에 내 알림과 `unread_count`가 보인다
- [ ] 읽음 처리 후 `unread_count`가 줄어드는 것이 화면으로 확인된다
- [ ] 역할 부여 전/후 `/api/v1/users/me/roles` 응답 차이가 화면으로 확인된다
- [ ] 회수된 조언가의 #29 수정 시도가 403으로 막히는 것이 화면으로 확인된다
- [ ] 각 스크린샷 촬영 전 해당 계정의 보유 역할을 먼저 출력해 확인한다 *(SPEC-001 TASK-002에서 계정에 누적된 ADMIN 역할 때문에 403이 아닌 200이 찍혀 오판했던 절차 개선)*

## 종료 판정

AC-1 ~ AC-10 전항 통과 + TEST_CRITERIA.md §3 공통 체크리스트 + `manage.py check`/`makemigrations --check`/`ruff check`/`manage.py test` 4종 무오류 실행 출력 첨부 → SPEC-003 완료, STATUS.md 갱신(**44/44, M4 종료**), PR 생성 및 서브에이전트 리뷰.

> **AC 전항 통과 ≠ 버그 없음.** SPEC-002는 AC-1~AC-11 전항 녹색 + 168개 테스트 통과 상태에서 서브에이전트 리뷰가 데이터 유실 버그 1건과 500 크래시 1건을 찾아냈다 — 둘 다 개별 기능이 아니라 **기능 사이의 상호작용**에 있었다. SPEC-003은 그 교훈을 AC-7·AC-8(교차 검증)로 선반영했지만, 머지 전 서브에이전트 리뷰는 여전히 필수다.
