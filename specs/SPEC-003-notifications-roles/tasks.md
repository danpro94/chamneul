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

## TASK-004 — 역할 회수 (#43) ★ 핵심 · A-3

* [ ] ADVISOR 회수 + `active_role=ADVISOR` → 204, **`active_role`이 USER로 강등** — 실패 테스트
* [ ] ADVISOR 회수 + `active_role=USER` → 204, `active_role` 불변 — 실패 테스트
* [ ] `UserRole` 삭제 + `RoleGrant(REVOKE)` 1행, 알림 없음 — 실패 테스트
* [ ] 자기 자신의 ADMIN 회수 → 409 — 실패 테스트
* [ ] 마지막 ADMIN 회수 → 409 (superuser 1 + UserRole ADMIN 1 상태 포함) — 실패 테스트
* [ ] 보유하지 않은 역할 회수 → 409 — 실패 테스트
* [ ] 잘못된 `{role}` 경로값 → 404 (URL 패턴이 `ADMIN|ADVISOR`만 매칭) — 실패 테스트
* [ ] 409로 끝난 요청이 **부분 상태를 남기지 않는다**(RoleGrant·active_role 무변화) — 실패 테스트
* [ ] `revoke_role` 서비스 구현 — 잠금 순서 User → UserRole, `list()` materialize(`count()` 금지)
* [ ] Mock-Up UI: 회수 후 조언가 계정의 역할 목록 스크린샷
* [ ] 검증 4종 실행 결과 첨부

## TASK-005 — 교차 검증 + 마무리

* [ ] **A-3 end-to-end**: 조언 작성 → ADVISOR 회수 → 같은 조언가가 #29 수정 시도 → **403** — 실패 테스트
* [ ] **C-10 `target_url` 왕복**: 5개 타입 알림을 실제 서비스 경로로 발생시키고 각 `target_url`을 수신자 세션으로 GET → 200 (`subTest`로 타입 구분) — 실패 테스트
* [ ] SPEC-003 전체 AC(acceptance.md) 재실행 + 테스트 목록과 1:1 대조
* [ ] `docs/api.md` 갱신 — 결정 1~3 확정 내용, #43의 "배정 잔존" 명시(결정 3(a))
* [ ] STATUS.md 갱신 (**44/44 엔드포인트, M4 종료**) + README_AIUSAGE.md 항목 추가
* [ ] `docs/reviews/`에 SPEC-003 리뷰 노트 1건
* [ ] Mock-Up UI: 회수된 조언가의 수정 시도 403 화면 스크린샷 (A-3의 시각적 증거)
* [ ] PR 생성 → 서브에이전트 리뷰(security-reviewer + api-architect) → 머지
