# SPEC-002 — acceptance criteria

TEST_CRITERIA.md §2(핵심 3축)·§3(공통 체크리스트)을 SPEC-002에 적용한 판정 기준. 전항 Django 테스트로 자동 판정한다.

## AC-1. 조언 작성 (#28)

- [ ] 배정된 advisor의 정상 작성 → 201, `status="PENDING"`, `version=1`
- [ ] `submit=true`(기본) → `is_submitted=True` / `submit=false` → `is_submitted=False`
- [ ] 미배정 advisor → 403
- [ ] `active_role≠ADVISOR` → 403
- [ ] 비로그인 → 401
- [ ] soft-deleted concern → 404
- [ ] 동일 (concern, advisor) 재작성 → 409
- [ ] 직전 advice가 `DELETED`면 재작성 → 201 (부분 유니크가 DELETED 제외)
- [ ] `directional_guidance` 1501자 → 400

## AC-2. 내가 쓴 조언 목록 (#31)

- [ ] 본인 작성분만, 타인 것 미노출
- [ ] 상태 무관 전량(DELETED 포함 여부는 구현 시 명시)
- [ ] `status`·`concern_id` 필터 동작
- [ ] `page_info` 포함
- [ ] `active_role≠ADVISOR` → 403 / 비로그인 → 401

## AC-3. 조언 상세 — 주체별 분기 (#27) ★ §6.2 핵심

- [ ] 작성자: PENDING/REVIEWING/APPROVED/REJECTED/DELETED 전부 200
- [ ] 작성자: 응답에 `is_submitted`, `reject_reason` 포함
- [ ] 고민 작성자 + APPROVED → 200, 응답에 `reject_reason` **없음**
- [ ] 고민 작성자 + PENDING → 403
- [ ] 고민 작성자 + REJECTED → 403
- [ ] ADMIN → 상태 무관 200 + `reject_reason` 포함
- [ ] 무관한 제3자 → 403
- [ ] 존재하지 않는 advice-id → 404
- [ ] 비로그인 → 401

## AC-4. 조언 수정 (#29)

- [ ] 본문 수정 → 200, `version` 1→2
- [ ] `AdviceHistory` 1행 생성, 그 행의 본문은 **수정 전** 내용이고 `version=1`
- [ ] `submit`만 변경 → `version` 유지, `AdviceHistory` 행 미생성 (결정 2)
- [ ] `REVIEWING` 상태에서도 수정 가능 → 200
- [ ] `APPROVED`/`REJECTED`/`DELETED` 상태 수정 → 409
- [ ] 작성자 아닌 advisor → 403
- [ ] 비로그인 → 401

## AC-5. 조언 삭제 (#30)

- [ ] `PENDING` 삭제 → 204, `status="DELETED"`
- [ ] `REVIEWING` 삭제 → 204
- [ ] `APPROVED` 삭제 → 409
- [ ] 이미 `DELETED` → 409
- [ ] 작성자 아닌 advisor → 403
- [ ] 삭제 후 동일 concern에 재작성 가능 → 201 (AC-1과 연계)

## AC-6. admin 리뷰 목록 (#32)

- [ ] 기본 조회: `status=PENDING` **그리고 `is_submitted=True`만** (결정 1 — 초안 미노출)
- [ ] `status` 필터 동작
- [ ] Admin 아닌 사용자 → 403 / 비로그인 → 401
- [ ] `assertNumQueries`로 쿼리 수 고정

## AC-7. 조언 승인/반려 (#33) ★ 부수효과 핵심

- [ ] 승인 → 200, `status="APPROVED"`, 응답에 `concern_status` 포함
- [ ] 승인 시 concern `ASSIGNED → ANSWERED` 전이
- [ ] 승인 시 `Notification(type=ADVICE_APPROVED, recipient=고민 작성자)` 생성
- [ ] 승인 시 concern이 `CLOSED`면 상태 불변 (결정 3)
- [ ] 승인 시 concern이 이미 `ANSWERED`면 상태 불변
- [ ] 반려 → 200, `status="REJECTED"`, `reject_reason` 저장
- [ ] 반려 시 `Notification(type=ADVICE_REJECTED, recipient=advisor)` 생성
- [ ] 반려 시 concern 상태 불변
- [ ] `reason` 없는 반려 → 422
- [ ] `expected_version` ≠ 현재 `version` → **412**
- [ ] 이미 `APPROVED`/`REJECTED`인 advice 재리뷰 → 409
- [ ] `is_submitted=False`(초안) 리뷰 시도 → 409 (결정 1)
- [ ] 실패 경로에서 알림·concern 전이 모두 미발생 (부분 상태 없음)
- [ ] Admin 아닌 사용자 → 403

## AC-8. 받은 조언 목록 (#26)

- [ ] 본인 고민에 달린 **APPROVED만** 노출
- [ ] PENDING/REVIEWING/REJECTED/DELETED는 미노출 (§6.2)
- [ ] 타인 고민의 advice 미노출
- [ ] `is_feedback_submitted`가 피드백 유무와 일치
- [ ] `advisor_display_name` 노출, advisor의 email·user_id 미노출
- [ ] `page_info` 포함 + `assertNumQueries` 고정
- [ ] 비로그인 → 401

## AC-9. 피드백 작성 / 내 목록 (#34, #35)

- [ ] 고민 작성자 + APPROVED advice + 미작성 → 201, `status="SUBMITTED"`
- [ ] advice가 APPROVED 아님 → 403
- [ ] 고민 작성자가 아님 → 403
- [ ] 동일 advice에 두 번째 피드백 → 409
- [ ] `score=0` 또는 `score=6` → 400
- [ ] #35: 본인 작성분만, `page_info` 포함
- [ ] 비로그인 → 401

## AC-10. admin 피드백 (#36, #37, #38)

- [ ] #36 목록: `status`·`score_min`·`score_max` 필터 동작
- [ ] #37 상세: `author_nickname`·`memo`·`reviewed_by` 등 admin 전용 필드 노출
- [ ] #38 `SUBMITTED → REVIEWED` → 200, `reviewed_at`/`reviewed_by` 기록
- [ ] #38 `REVIEWED → ARCHIVED` → 200
- [ ] #38 역방향(`ARCHIVED → REVIEWED`) → 409
- [ ] #38 건너뛰기(`SUBMITTED → ARCHIVED`) → 409
- [ ] Admin 아닌 사용자 → 전 엔드포인트 403

## AC-11. §6.2 노출 규칙 전수 (TASK-007)

CLAUDE.md §6.2는 이 SPEC의 6개 지점에 걸린다. **PENDING advice 1건을 만들어 놓고** 다음 전부에서 안 보이는지 확인한다:

- [ ] #26 받은 조언 목록에 없음
- [ ] #27 상세를 고민 작성자가 조회 → 403
- [ ] #18(SPEC-001) 고민 상세의 `approved_advices[]`에 없음
- [ ] #34 피드백 작성 시도 → 403
- [ ] #35 내 피드백 목록에 흔적 없음
- [ ] #22/#23 admin 경로에서는 **보임**(§6.2는 사용자 보호용이지 admin 제한이 아님)

## 종료 조건

AC-1 ~ AC-11 전항 통과 + TEST_CRITERIA.md §3 공통 체크리스트 + `manage.py check`/`makemigrations --check`/`ruff check`/`manage.py test` 4종 무오류 실행 출력 첨부 → SPEC-002 완료, STATUS.md 갱신, PR 생성.
