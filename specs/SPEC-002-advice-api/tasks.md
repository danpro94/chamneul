# SPEC-002 — tasks

프롬프트 3 루프(테스트 먼저 → 최소 구현 → 검증 4종 실행 출력 → 커밋 → STATUS.md 갱신 → 정지·확인)로 진행한다. 커밋 메시지에 `SPEC-002/TASK-00N`을 포함한다.

## TASK-001 — 조언 작성 + 내가 쓴 조언 목록 (#28, #31)

* [ ] 배정된 advisor의 정상 작성 → 201, `status=PENDING`, `version=1` — 실패 테스트
* [ ] 미배정 advisor → 403 / 비로그인 → 401 / `active_role≠ADVISOR` → 403 — 실패 테스트
* [ ] 동일 (concern, advisor) 재작성 → 409, 단 직전이 `DELETED`면 201 — 실패 테스트
* [ ] `directional_guidance` 1501자 → 400 — 실패 테스트
* [ ] `submit=false` → `is_submitted=False`로 저장 — 실패 테스트
* [ ] #31 목록: 본인 것만, 상태 무관, `status`/`concern_id` 필터, `page_info` — 실패 테스트
* [ ] `advice/{serializers,services,views,urls}.py` 신설 + `config/urls.py` include
* [ ] 검증 4종 실행 결과 첨부

## TASK-002 — 조언 상세: 3주체 분기 (#27)

* [ ] 작성자: 상태 무관 200 + `is_submitted`·`reject_reason` 노출 — 실패 테스트
* [ ] 고민 작성자 + APPROVED: 200, `reject_reason` **미노출** — 실패 테스트
* [ ] 고민 작성자 + PENDING: 403 (§6.2 핵심) — 실패 테스트
* [ ] ADMIN: 상태 무관 200 + `reject_reason` 노출 — 실패 테스트
* [ ] 제3자: 403 / 없는 advice-id: 404 — 실패 테스트
* [ ] `visible_advice_for` + 역할별 serializer 3종 구현
* [ ] 검증 4종 실행 결과 첨부

## TASK-003 — 조언 수정 + 삭제 (#29, #30)

* [ ] 본문 수정 → 200, `version` 2, `AdviceHistory` 1행에 **직전** 본문 — 실패 테스트
* [ ] `submit`만 토글 → `version` 유지, 히스토리 행 없음 (결정 2) — 실패 테스트
* [ ] APPROVED/REJECTED/DELETED 상태에서 수정 → 409 — 실패 테스트
* [ ] 타인의 advice 수정 → 403 — 실패 테스트
* [ ] 삭제 → 204 + `status=DELETED`, APPROVED 삭제 시도 → 409 — 실패 테스트
* [ ] `update_advice`/`delete_advice` 서비스 구현 (`transaction.atomic`)
* [ ] 검증 4종 실행 결과 첨부

## TASK-004 — admin 리뷰 목록 + 승인/반려 (#32, #33) ★ 핵심

* [ ] #32 기본 조회에 draft 미포함 (결정 1) + `status` 필터 — 실패 테스트
* [ ] 승인 → `APPROVED` + concern `ASSIGNED→ANSWERED` + 고민 작성자에게 `ADVICE_APPROVED` — 실패 테스트
* [ ] 반려 → `REJECTED` + advisor에게 `ADVICE_REJECTED` + concern 상태 불변 — 실패 테스트
* [ ] `reason` 없는 반려 → 422 — 실패 테스트
* [ ] `expected_version` 불일치 → **412** — 실패 테스트
* [ ] 이미 APPROVED인 advice 재리뷰 → 409 / draft 리뷰 시도 → 409 (결정 1) — 실패 테스트
* [ ] CLOSED concern의 advice 승인 시 concern 상태 불변 (결정 3) — 실패 테스트
* [ ] 실패 시 부분 상태 없음(알림·전이 미발생) — 실패 테스트
* [ ] `common/exceptions.py`에 `PreconditionFailed` 추가 + `review_advice` 서비스 구현
* [ ] 검증 4종 실행 결과 첨부

## TASK-005 — 받은 조언 목록 + 피드백 작성/내 목록 (#26, #34, #35)

* [ ] #26: 본인 고민의 **APPROVED만**, 타인·PENDING 미노출 — 실패 테스트
* [ ] #26: `is_feedback_submitted` 파생 필드 정확도 — 실패 테스트
* [ ] #34: 고민 작성자 + APPROVED + 미작성 → 201 — 실패 테스트
* [ ] #34: PENDING advice → 403 / 타인 → 403 / 중복 → 409 / `score=6` → 400 — 실패 테스트
* [ ] #35: 본인 작성분만 — 실패 테스트
* [ ] 목록 2종 `assertNumQueries` 고정
* [ ] 검증 4종 실행 결과 첨부

## TASK-006 — admin 피드백 목록/상세/상태 변경 (#36, #37, #38)

* [ ] #36 목록 + `status`/`score_min`/`score_max` 필터, Admin 아니면 403 — 실패 테스트
* [ ] #37 상세: `author_nickname`·`memo` 등 admin 전용 필드 노출 — 실패 테스트
* [ ] #38 전이: `SUBMITTED→REVIEWED→ARCHIVED` 정상, 역방향/건너뛰기 → 409 — 실패 테스트
* [ ] `assertNumQueries` 고정
* [ ] 검증 4종 실행 결과 첨부

## TASK-007 — 마무리

* [ ] SPEC-002 전체 AC(acceptance.md) 재실행 + 테스트 목록과 1:1 대조 (SPEC-001 TASK-006에서 미커버 2건이 나온 절차)
* [ ] §6.2 노출 규칙 전수 점검 — PENDING advice가 사용자 경로 어디에도 안 보이는지 6개 지점 확인
* [ ] `docs/api.md` 정정 필요분 반영 (결정 1~4 확정 내용)
* [ ] STATUS.md 갱신 (#26~38 구현됨, 39/44) + README_AIUSAGE.md 항목 추가
* [ ] PR 생성 → 리뷰 → 머지
