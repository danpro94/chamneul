# SPEC-001 — acceptance criteria

TEST_CRITERIA.md §2(핵심 3축)·§3(공통 체크리스트)을 이 SPEC에 적용한 최종 판정 기준. 전항 Django 테스트로 자동 판정.

## AC-1. 생성 (#16)

- [ ] 유효한 요청 → 201, body에 `concern_id`(uuid)·`status="SUBMITTED"`·`message`
- [ ] `concern_type` taxonomy 밖 값 → 400
- [ ] `concern_summary` 101자 이상 → 400
- [ ] `concern_type_secondary` 3개 이상 → 400
- [ ] 비로그인 → 401
- [ ] DB 확인: 생성된 row의 `deleted_at IS NULL`

## AC-2. 목록 (#17)

- [ ] 본인 것만 노출, 타인 것 미노출
- [ ] soft-delete된 항목 미노출
- [ ] `?status=` 필터 동작
- [ ] 응답에 `page_info`(`page`/`size`/`total`/`total_pages`) 포함
- [ ] 비로그인 → 401

## AC-3. 상세 (#18)

- [ ] 본인 것 200, 전체 필드 포함
- [ ] `approved_advices[]`에 APPROVED 상태 advice만(PENDING/REVIEWING/REJECTED/DELETED 제외) — §6.2 핵심 검증
- [ ] soft-delete된 본인 것 → 404
- [ ] 타인 것 → 404
- [ ] 비로그인 → 401

## AC-4. 소프트 삭제 (#19)

- [ ] 정상 삭제 → 204, 재조회 시 404
- [ ] `deleted_at`이 삭제 시각으로 기록(±수 초 오차 허용)
- [ ] 연결된 Advice/Assignment row가 삭제 전후 개수 동일(보존 확인)
- [ ] 이미 삭제된 것 재삭제 → 409
- [ ] 타인 것 → 404
- [ ] 비로그인 → 401

## AC-5. 배정받은 목록 (#20)

- [ ] `active_role=ADVISOR` + 활성 배정 보유 → 200, 배정된 것만
- [ ] ADVISOR 역할 없음 → 403
- [ ] ADVISOR 역할은 있으나 `active_role=USER` → 403
- [ ] 비로그인 → 401

## AC-6. 배정받은 상세 (#21)

- [ ] 배정된 advisor 본인 → 200
- [ ] `requester_display_name`: `display_alias` 설정 시 그 값
- [ ] `requester_display_name`: `display_alias` 없고 `is_anonymous=True` → "익명의 요청자"
- [ ] `requester_display_name`: `display_alias` 없고 `is_anonymous=False` → 작성자 `nickname`
- [ ] 응답에 `email`·`user_id`(작성자의) 미노출
- [ ] 배정 안 된 advisor → 403
- [ ] 비로그인 → 401

## AC-7. admin 목록 (#22)

- [ ] `include_deleted` 미지정 시 삭제분 제외
- [ ] `include_deleted=true` 시 삭제분 포함, 각 항목 `is_deleted` 필드로 구분 가능
- [ ] `?status=` 필터 동작
- [ ] Admin 아닌 사용자 → 403
- [ ] 비로그인 → 401

## AC-8. admin 상세 (#23)

- [ ] `assignments[]`에 active/inactive 전부 포함
- [ ] `advices[]`에 모든 status 포함(§6.2 제약이 admin에는 적용 안 됨을 확인)
- [ ] Admin 아닌 사용자 → 403
- [ ] 존재하지 않는 concern-id → 404
- [ ] `assertNumQueries`로 쿼리 수 고정(N+1 없음)

## AC-9. 배정 생성 (#24)

- [ ] `SUBMITTED` concern 배정 → 201 + `concern.status == "ASSIGNED"`
- [ ] `ASSIGNED` concern에 추가 배정(다른 advisor) → 201 + status 유지
- [ ] 동일 (concern, advisor) 중복 활성 배정 → 409
- [ ] `CLOSED` concern에 배정 시도 → 409
- [ ] soft-delete concern에 배정 시도 → 409
- [ ] 성공 시 `Notification(type=ASSIGNMENT_CREATED, recipient=advisor)` row 생성 확인
- [ ] Admin 아닌 사용자 → 403

## AC-10. 배정 해제 (#25)

- [ ] 마지막 활성 배정 해제 → 204 + `concern.status`가 `SUBMITTED`로 되돌아감
- [ ] 다른 활성 배정이 남은 상태에서 해제 → 204 + `concern.status` 유지(`ASSIGNED`)
- [ ] 이미 비활성인 배정 재해제 → 409
- [ ] `assignment.deactivated_at` 기록 확인
- [ ] Admin 아닌 사용자 → 403

## 종료 조건

위 10개 그룹 전항 통과 + TEST_CRITERIA.md §3 공통 체크리스트(모든 엔드포인트) + `manage.py check`/`makemigrations --check`/`ruff check`/`manage.py test` 4종 무오류 실행 출력 첨부 → SPEC-001 완료, STATUS.md 갱신.
