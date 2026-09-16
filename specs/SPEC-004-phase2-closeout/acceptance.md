# SPEC-004 — acceptance criteria

Phase 2 종료 게이트. 이 SPEC의 AC는 **CLAUDE.md §1의 완료 조건을 증거로 바꾸는 것**이라, 다른 SPEC과 달리 상당 부분이 Django 테스트가 아니라 **실행 출력**으로 판정된다.

> 판정 원칙: "됐다"가 아니라 **"이 명령의 이 출력이 근거다"**. CLAUDE.md §12 — 실행하지 않은 명령은 "권장 명령"이라고 적고 완료로 세지 않는다.

## AC-1. 맨바닥 기동 (TASK-001)

- [ ] `docker compose down -v` 후 `up -d --build` → 두 서비스 기동
- [ ] `docker compose ps` → db가 `healthy`, app이 `Up`
- [ ] `migrate` → 전 앱 마이그레이션 적용, 오류 없음
- [ ] `createsuperuser` → User 생성 + **ADMIN `UserRole` 행 자동 생성**(ADR-003 §1 부트스트랩)
- [ ] `curl -i /healthz` → **200**
- [ ] 위 전 과정의 실제 출력이 `docs/smoke-test.md`에 있다

## AC-2. 사용자 여정 11단계 (TASK-001)

각 단계는 **실제 명령과 실제 응답**으로 판정한다.

- [ ] 회원가입(#2) → 201 + `Set-Cookie: sessionid` (HttpOnly)
- [ ] 로그인(#3) → 200, 로그아웃(#4) → 서버 세션 삭제 + 쿠키 만료
- [ ] 고민 작성(#16) → 201, 목록(#17) → 방금 만든 것이 보인다
- [ ] 관리자 고민 목록(#22) → 해당 고민 확인, 배정(#24) → 201 + concern `ASSIGNED`
- [ ] 조언가 역할 전환(#10) → 200, 배정 고민 목록(#20)·상세(#21) → 200
- [ ] 조언 작성(#28) → 201, `status=PENDING`
- [ ] 관리자 리뷰 목록(#32)에 노출, 승인(#33) → 200 + concern `ANSWERED`
- [ ] 사용자 받은 조언(#26) → 방금 승인된 조언이 보인다, 상세(#27) → 200
- [ ] 피드백 작성(#34) → 201
- [ ] 알림 목록(#39) → `unread_count` 확인, 읽음(#41) → 감소, `target_url` GET → 200
- [ ] 역할 회수(#43) → 204, 직후 조언가의 #20 → **403**

## AC-3. 비정상 경로 (TASK-001)

- [ ] `docker compose stop db` 상태에서 `/healthz` 호출 — 응답 코드와 소요 시간 기록
- [ ] 같은 상태에서 API 호출 — 에러 봉투(§1.5) 형태가 유지되는지 기록
- [ ] `start db` 후 **앱 재시작 없이** 정상 응답으로 회복되는지 기록
- [ ] 마이그레이션 미적용 상태로 API 호출 시 나오는 오류 기록
- [ ] 위 4건이 "무엇이 정상인가"와 함께 `docs/smoke-test.md`에 있다

## AC-4. 알려진 갭 명시 (TASK-001)

`docs/smoke-test.md`에 아래 6건이 **갭으로 명시**되어 있다(해결이 아니라 기록이 판정 기준이다).

- [ ] 브루트포스 로그인 방어 부재 (Phase 3)
- [ ] 정적파일 서빙 미구성
- [ ] dev/prod override 운영 경로 검증 절차
- [ ] 고민 종료(`CLOSED`) 사용자 API 부재 + CLAUDE.md §6.6 문구와의 긴장 (결정 5)
- [ ] 회수된 조언가의 배정 잔존 (SPEC-003 결정 3, #23에서 식별 가능)
- [ ] 실제 경합 미재현 (잠금의 존재만 SQL 테스트로 고정됨)

## AC-5. model.md 정합 (TASK-002)

- [ ] `data-modeler` 재실행 결과가 기록되어 있다 (기록된 4건이 아니라 **재측정 목록**)
- [ ] 확정된 drift가 전부 반영됐다
- [ ] 반영하지 않은 항목이 있다면 **이유와 함께** 분리 기록됐다
- [ ] model.md §1.1이 UTC 정책이다
- [ ] model.md의 모델 정의가 실제 `models.py`와 일치한다 (필드명·null 여부·제약)

## AC-6. 시각 정책 UTC (TASK-003, 결정 2)

- [ ] api.md §1.7이 "DB=UTC 저장 / API=ISO 8601 UTC 전송 / 클라이언트=현지 변환"으로 교체됐다
- [ ] api.md의 DateTime **예시 문자열**이 UTC 표기다 (`+09:00` 잔존 없음)
- [ ] model.md §1.1도 동일
- [ ] `config/settings/base.py`의 `TIME_ZONE`은 **변경되지 않았다** (코드가 옳고 문서가 틀렸다)
- [ ] 문서 전체에서 "KST로 직렬화" 문구가 사라졌다

## AC-7. #21 404 전환 (TASK-003, 결정 3)

- [ ] 미배정 조언가의 #21 조회 → **404** (기존 403)
- [ ] 배정된 조언가의 #21 조회 → 200 (회귀 없음)
- [ ] `active_role≠ADVISOR` → 403 유지 (권한 계층 미달은 여전히 403 — §1.8 규칙 3행)
- [ ] 존재하지 않는 concern-id → 404
- [ ] api.md #21의 Status 집합과 접근 제어 조건이 정정됐다
- [ ] api.md §1.8의 "미해결 예외: #21" 문단이 **제거**됐다 (예외가 사라졌으므로)
- [ ] 변경된 테스트의 커밋 메시지에 **결정 변경이 원인**임이 적혀 있다

## AC-8. 문서 부채 청산 (TASK-003)

- [ ] README_AIUSAGE.md에 M4-1~M4-4 4건이 추가됐다 (git log 기준, 추측 아님)
- [ ] `docs/reviews/03-milestone3-review.md` 존재
- [ ] `docs/reviews/04-milestone4-review.md` 존재
- [ ] STATUS.md §7 문서 부채가 전항 종결

## AC-9. Phase 2 종료 판정 (TASK-004)

- [ ] CLAUDE.md §1의 **9개 조건 전항**이 증거(명령+출력)와 함께 대조됐다
- [ ] STATUS.md §6 학습 부채 14건이 **종결 처리**됐다 (결정 4)
- [ ] STATUS.md에 Phase 3 인수인계 목록이 있다
- [ ] `docs/reviews/07-phase2-closeout.md` 존재
- [ ] 서브에이전트 리뷰 2종(`devops-local-platform`·`data-modeler`) 실행 + 결과 반영

## AC-10. 회귀 없음 (전 TASK)

- [ ] `manage.py check` → 0 issues
- [ ] `makemigrations --check --dry-run` → No changes (**모델 변경 없음**)
- [ ] `ruff check .` → passed
- [ ] `manage.py test` → 전항 통과 (#21 변경분 반영 후)

## 종료 판정

AC-1 ~ AC-10 전항 통과 → **Phase 2 종료.** STATUS.md의 Phase를 3으로 넘기고 PR 생성.

> **스모크 테스트는 이 프로젝트에서 유일하게 "맨바닥에서 일어서는가"를 묻는 검증이다.** 283개 테스트는 전부 테스트 DB에서 돌았고, 볼륨을 비운 새 컨테이너로 처음부터 올려본 적이 없다. SPEC-003에서 알림 `target_url` 5종이 전부 옳았지만 **아무도 눌러본 적이 없어** 옳다는 사실 자체가 미확인이었던 것과 같은 종류의 공백이다. 여기서 처음 드러나는 문제가 나오는 것은 실패가 아니라 이 TASK가 제 일을 한 것이다.
