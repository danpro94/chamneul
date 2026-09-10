# SPEC-001 — tasks

> **완료 (2026-09-10).** TASK-001~006 전부 이수, AC-1~AC-10 전항 통과(acceptance.md 종료 판정 참조), 테스트 62개.

각 TASK는 프롬프트 3 루프(spec §5 참조: 테스트 먼저 → 최소 구현 → 실행 검증 → 커밋 → STATUS.md 갱신 → 다음 TASK 전 확인)로 진행한다. 커밋 메시지에 `SPEC-001/TASK-00N`을 포함한다.

## TASK-001 — concern 생성 + 목록 (#16, #17)

* [x] `concern_type`이 taxonomy 밖 값이면 400 — 실패 테스트 작성
* [x] `concern_type_secondary` 3개 이상이면 400 — 실패 테스트 작성
* [x] 정상 생성 → 201, `status=SUBMITTED` — 실패 테스트 작성
* [x] 목록에서 soft-delete 항목 제외, 타인 것 제외, `page_info` 포함 — 실패 테스트 작성
* [x] `concerns/serializers.py`(Create/List) + `concerns/services.py::create_concern` + `concerns/views.py`(POST/GET) 최소 구현
* [x] `concerns/urls.py` 신설 + `config/urls.py`에 include
* [x] `check` / `makemigrations --check` / `ruff` / `test` 실행 결과 첨부

## TASK-002 — concern 상세 + 소프트 삭제 (#18, #19)

* [x] 본인 상세 조회 시 `approved_advices[]`에 APPROVED만 노출(§6.2) — 실패 테스트
* [x] soft-delete된 concern 상세 조회 → 404 — 실패 테스트
* [x] 타인 concern 조회/삭제 → 404 — 실패 테스트
* [x] 정상 삭제 → 204, `deleted_at` 기록, advice/assignment 보존 — 실패 테스트
* [x] 이미 삭제된 concern 재삭제 → 409 — 실패 테스트
* [x] Detail 시리얼라이저 + `soft_delete_concern` 서비스 + view 구현
* [x] 검증 4종 실행 결과 첨부

## TASK-003 — advisor 배정 목록/상세 (#20, #21)

* [x] `active_role != ADVISOR` → 403 — 실패 테스트
* [x] 배정받은 목록에 익명 처리된 `concern_summary` 노출 — 실패 테스트
* [x] 배정 안 된 advisor의 상세 접근 → 403 — 실패 테스트
* [x] `requester_display_name` 파생 규칙 3분기(별칭/익명/비익명 nickname) — 실패 테스트 3종
* [x] `IsAssignedAdvisor` permission + serializer + view 구현
* [x] 검증 4종 실행 결과 첨부

## TASK-004 — admin 조회 (#22, #23)

* [x] `include_deleted` 기본 false — 실패 테스트
* [x] `include_deleted=true` 시 삭제분 포함 + `is_deleted` 파생 필드 — 실패 테스트
* [x] 상세에서 `assignments[]`·`advices[]`가 상태 무관 전체 노출 — 실패 테스트
* [x] N+1 없음 — `assertNumQueries`로 고정
* [x] serializer + view 구현
* [x] 검증 4종 실행 결과 첨부

## TASK-005 — 배정 생성/해제 + 상태 전이 (#24, #25)

* [x] `SUBMITTED → ASSIGNED` 전이 + `ASSIGNMENT_CREATED` 알림 — 실패 테스트
* [x] 이미 ASSIGNED인 concern에 추가 배정 시 상태 유지 — 실패 테스트
* [x] 중복 활성 배정 → 409 — 실패 테스트
* [x] CLOSED/soft-delete concern에 배정 시도 → 409 — 실패 테스트
* [x] 마지막 활성 배정 해제 시 `ASSIGNED → SUBMITTED` 되돌림 — 실패 테스트
* [x] 남은 활성 배정이 있으면 상태 유지 — 실패 테스트
* [x] 이미 비활성인 배정 재해제 → 409 — 실패 테스트
* [x] `assign_advisor`/`unassign_advisor` 서비스 + view 구현
* [x] 검증 4종 실행 결과 첨부

## TASK-006 — 마무리

* [x] SPEC-001 전체 AC(acceptance.md) 재실행 — 전항 통과 확인
* [x] `docs/api.md` #16·#19·#22의 `is_deleted` 표기를 실제 구현(파생 필드)과 대조해 문구 정정(필요 시)
* [x] **#20 `status` 필터 구현 + api.md 문구 정정** — Owner 승인(2026-09-10, STATUS.md §5): `status`는 `concern.status` 필터로 재해석하고, api.md #20의 "(assignment 상태)"를 "(concern 상태)"로 고친다
* [x] STATUS.md §2/§3 갱신 (concerns 10개 항목을 "구현됨"으로 이동)
* [x] README_AIUSAGE.md에 SPEC-001 항목 1건 추가
* [ ] Owner 확인 후 SPEC-002(M4-6 advice+feedback) 착수 여부 결정  ← 유일한 미완 항목
