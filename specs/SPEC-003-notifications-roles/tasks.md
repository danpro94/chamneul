# SPEC-003 — tasks

프롬프트 3 루프(**실패 테스트 먼저 → 최소 구현 → 검증 4종 실행 출력 → 커밋 → STATUS.md 갱신 → 정지·확인**)로 진행한다. 커밋 메시지에 `SPEC-003/TASK-00N`을 포함한다.

검증 4종 = `manage.py check` / `makemigrations --check` / `ruff check` / `manage.py test`.

**TASK마다 Mock-Up UI 확인을 포함한다** — Owner 요구사항(2026-09-10): 백엔드 테스트 통과만으로 끝내지 않고, DRF Browsable API로 데이터 흐름·사용자 흐름을 눈으로 확인할 수 있는 스크린샷을 남긴다. 화려할 필요 없고 흐름이 맞는지만 보이면 된다. *(이 요구사항이 SPEC-001·002 tasks.md에는 문서화되지 않은 채 구두로만 지켜졌다 — 여기서 명문화한다.)*

**착수 전제**: PR #5(`fix/audit-state-transition-locking`, A-1 수정 + 상태 전이 규칙)가 머지되고 이 브랜치가 리베이스되어야 한다. 이 브랜치는 `main` 기준이라 아직 A-1 수정을 포함하지 않는다.

## TASK-001 — 알림 목록 + 상세 (#39, #40) — **완료 (2026-09-15)**

* [x] 내 알림만 조회, 타인 알림 미노출 — 실패 테스트
* [x] `unread_count`가 **필터와 무관하게** 전체 미읽음 수 — 실패 테스트
* [x] `?is_read=false` / `?type=` 필터 동작 + `page_info` — 실패 테스트
* [x] #40 타인의 알림 → **404**(결정 2) / 없는 id → 404 / 비로그인 → 401 — 실패 테스트
* [x] #40 응답에 `actor` 관련 필드가 **없다**(결정 1) — 실패 테스트
* [x] `notifications/{serializers,services,views,urls}.py` 신설 + `config/urls.py` include
* [x] `assertNumQueries` — **실측 3건**(페이지 COUNT + 페이지 행 + unread_count 집계)
* [x] Mock-Up UI: 목록 / 읽음필터 / 상세 / 타인 알림 404 — 4장
* [x] 검증 4종 실행 결과 첨부 — check 0 issues / makemigrations No changes / ruff passed / **207 tests OK**

## TASK-002 — 알림 읽음 처리 (#41) — **완료 (2026-09-15)**

* [x] 미읽음 → PATCH → 200, `is_read=true`, `read_at` 기록 — 실패 테스트
* [x] 이미 읽은 알림 재요청 → **200(멱등)**, `read_at` 최초 값 유지 — 실패 테스트
* [x] 타인의 알림 → 404(행 불변 확인) / 없는 id → 404 / 비로그인 → 401 — 실패 테스트
* [x] 읽음 처리 후 #39의 `unread_count` 감소 + 다른 알림 불변 — 실패 테스트
* [x] `mark_read` 서비스 구현 (`atomic` + `select_for_update(of=("self",))` + `update_fields`)
* [x] **발행 SQL 실측 확인** — `FOR UPDATE OF "notifications_notification"` 실재, UPDATE는 `is_read`·`read_at` 2개 컬럼만
* [x] Mock-Up UI: 읽음 전(3) / 후(2) / 상세 `read_at` — 3장. 실제 브라우저 CSRF PATCH로 왕복
* [x] 검증 4종 실행 결과 첨부 — check 0 issues / makemigrations No changes / ruff passed / **215 tests OK**

## TASK-003 — 역할 부여 (#42) — **완료 (2026-09-15)**

* [x] ADVISOR/ADMIN 부여 → 201, `UserRole` 1행 + `RoleGrant(GRANT)` 1행(`reason` 포함) — 실패 테스트
* [x] 응답 `roles[]`가 **변경 후** 보유 역할 (`USER`, `ADVISOR`) + 응답 필드 5종 고정 — 실패 테스트
* [x] **알림이 생성되지 않는다**(ADR-003 §4) — 실패 테스트
* [x] 이미 보유한 역할 → 409, **그리고 감사행 미생성** / `role="USER"`·미지정·미정의값 → 400 / 없는 user-id → 404 — 실패 테스트
* [x] Admin 아닌 사용자 → 403 / 비로그인 → 401 — 실패 테스트
* [x] 부여가 `active_role`을 바꾸지 않는다 — 실패 테스트
* [x] `accounts/tests.py` 신설(**이 앱 첫 테스트, 16개**) + `grant_role` 서비스 + 뷰·URL
* [x] **발행 SQL 실측** — `FOR UPDATE OF "accounts_user"`가 `exists()` 검사보다 **먼저** 걸림(check-then-create 직렬화)
* [x] Mock-Up UI: 부여 전/후 `/api/v1/users/me/roles` 비교 2장 + 409·400·403 실왕복 확인
* [x] 검증 4종 실행 결과 첨부 — check 0 issues / makemigrations No changes / ruff passed / **231 tests OK**

## TASK-004 — 역할 회수 (#43) ★ 핵심 · A-3 — **완료 (2026-09-15)**

* [x] ADVISOR 회수 + `active_role=ADVISOR` → 204, **`active_role`이 USER로 강등** — 실패 테스트
* [x] ADVISOR 회수 + `active_role=USER` → 204, `active_role` 불변 — 실패 테스트
* [x] ADMIN 회수는 `active_role`을 건드리지 않는다(ADVISOR 착용 중이어도) — 실패 테스트
* [x] `UserRole` 삭제 + `RoleGrant(REVOKE)` 1행(`?reason=` 저장), 알림 없음 — 실패 테스트
* [x] 한 역할만 회수되고 다른 보유 역할은 남는다 — 실패 테스트
* [x] 자기 자신의 ADMIN 회수 → 409 — 실패 테스트
* [x] 마지막 ADMIN 회수 → 409 (superuser 1 + UserRole ADMIN 1 상태 포함) — 실패 테스트
* [x] **미보유 판정이 마지막-관리자 판정보다 먼저다** — 관리자 1명일 때 ADMIN 미보유자 회수 시도가 "보유하지 않은 역할"로 응답 — 실패 테스트
* [x] **트랜잭션 안에서 상태를 다시 읽는다**(A-1 회귀 방지) — 서비스가 객체가 아닌 `user_id`를 받음 — 실패 테스트
* [x] 잘못된 `{role}` 경로값(`USER`·`SUPERADMIN`·소문자) → 404 — 실패 테스트
* [x] 409로 끝난 요청이 **부분 상태를 남기지 않는다**(RoleGrant·active_role 무변화) — 실패 테스트
* [x] `revoke_role` 서비스 구현 — 잠금 순서 User → UserRole(`order_by("pk")`), `list()` materialize(`count()` 금지), 삭제 반환값으로 미보유 판정
* [x] `GrantableRoleConverter` URL 컨버터 — `USER`가 라우트에 매칭되지 않게 함
* [x] **발행 SQL 실측** — `FOR UPDATE OF "accounts_user"` → `role='ADMIN' ORDER BY id ASC FOR UPDATE` → DELETE → INSERT → `UPDATE accounts_user SET active_role='USER', updated_at=...`
* [x] **AC-7(A-3 end-to-end)을 앞당겨 실증** — 회수 전 #20·#29 = 200 → 회수 → #20·#29 = 403, 조언 데이터 보존(#27=200), concern은 `ASSIGNED` 유지(결정 3)
* [x] Mock-Up UI 4장 + 실왕복 `USER` 경로 404 · 재회수 409 확인
* [x] **A-3의 나머지 절반** — `set_active_role`(#10)도 같은 행 잠금으로 보호. 회수 쪽만 고치면 "전환이 역할을 읽음 → 회수가 지움 → 전환이 씀" 순서로 같은 상태에 도달한다 (STATUS.md §7 A-3의 원래 정의)
* [x] `ActiveRoleSwitchTests`(#10 최초 테스트) + `StateTransitionLockingTests`(상태 전이 규칙을 SQL 수준에서 강제) 신설
* [x] 검증 4종 실행 결과 첨부 — check 0 issues / makemigrations No changes / ruff passed / **260 tests OK**

## TASK-005 — 교차 검증 + 마무리 — **완료 (2026-09-16)**

* [x] **A-3 end-to-end**: `RoleRevokeEndToEndTests` 6개 — 회수 전 #20·#29=200(대조군) → 회수 → 403, 조언 데이터 보존, concern `ASSIGNED` 유지, 알림 미발생
* [x] **C-10 `target_url` 왕복**: `NotificationTargetUrlRoundTripTests` 6개 — 5종을 실제 서비스 경로로 발생시켜 수신자 세션으로 GET → 전부 200. 경로 형식(`/api/v1/` 시작, 쿼리·trailing slash 없음)과 `payload` 키까지 검증. 타입이 늘면 알려주는 커버리지 테스트 1개 포함
* [x] SPEC-003 전체 AC 재실행 + 테스트 1:1 대조 — **미커버 1건 발견·보완**(AC-8 `payload` 키 검증이 5종 중 1종에만 적용돼 있었음. 코드는 옳았고 검증이 비어 있었다)
* [x] `RoleGrant` append-only 정적 확인 (프로덕션 코드에 `create` 3곳뿐, `update`/`delete` 없음)
* [x] `docs/api.md` 갱신 — #40 `actor` 삭제, #40·#41 Status에서 403 제거 + 멱등 명시, #43 배정 잔존 명시, 개정 이력 추가
* [x] STATUS.md 갱신 (**44/44, M4 구현 종료**) + README_AIUSAGE.md 항목 추가
* [x] `docs/reviews/06-spec003-notifications-roles.md` 작성
* [x] Mock-Up UI 총 13장 (TASK-001~004에 걸쳐 첨부)
* [ ] PR 생성 → 서브에이전트 리뷰(security-reviewer + api-architect) → 머지  ← 진행 중
