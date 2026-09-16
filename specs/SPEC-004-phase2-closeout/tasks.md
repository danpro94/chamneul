# SPEC-004 — tasks

프롬프트 3 루프로 진행한다. 다만 TASK-001·002는 **문서 산출물**이라 "실패 테스트 먼저"가 적용되지 않는다 — 대신 **실행 출력을 먼저 확보하고 그것으로 문서를 쓴다**(추측으로 쓰지 않는다). 커밋 메시지에 `SPEC-004/TASK-00N`을 포함한다.

검증 4종 = `manage.py check` / `makemigrations --check` / `ruff check` / `manage.py test`.

## TASK-001 — 스모크 테스트 실행 + 문서화 ★

* [ ] **Owner 고지 후** `docker compose down -v` — 로컬 볼륨(합성 데모 데이터) 삭제
* [ ] `docker compose up -d --build` → `ps`로 두 서비스 상태 확인
* [ ] `migrate` → `createsuperuser` → ADMIN `UserRole` 행 생성 확인
* [ ] `curl /healthz` → 200
* [ ] 사용자 여정 11단계를 `curl`로 통과 (spec §3) — **실제 출력 수집**
* [ ] 비정상 경로 4종 (plan §2-3) — DB 정지/회복, 마이그레이션 미적용
* [ ] `docs/smoke-test.md` 작성 — 절차 + 실제 출력 + 갭 6건 + 운영 체크리스트
* [ ] `README.md`에 스모크 절차 링크
* [ ] 검증 4종 실행 결과 첨부

## TASK-002 — model.md 정합화

* [ ] `data-modeler` 서브에이전트 재실행 → drift 목록 **재측정**(기록된 4건은 M3 시점)
* [ ] 확정된 drift 반영 — **문서를 코드에 맞춘다**
* [ ] 코드가 틀려 보이는 항목은 반영하지 말고 **분리해 보고**
* [ ] model.md §1.1 시각 정책을 UTC로 교체 (결정 2)
* [ ] 검증 4종 실행 결과 첨부

## TASK-003 — 이월 2건 + 문서 부채 청산

* [ ] **결정 3**: #21이 미배정 조언가에게 **404** — 실패 테스트 먼저
* [ ] `get_assigned_concern()`을 쿼리셋 스코프 판정으로 변경 (알림 3종과 같은 형태)
* [ ] 기존 403 단언을 404로 수정 — 커밋 메시지에 **"결정 변경이 원인"** 명시
* [ ] api.md #21 Status 집합·접근 제어 조건 정정 + §1.8 "미해결 예외" 문단 제거
* [ ] **결정 2**: api.md §1.7 + model.md §1.1을 UTC 정책으로 교체, 예시 문자열도 함께
* [ ] `README_AIUSAGE.md`에 M4-1~M4-4 소급 4건 (git log 기준, 추측 금지)
* [ ] `docs/reviews/03-milestone3-review.md` 신규
* [ ] `docs/reviews/04-milestone4-review.md` 신규
* [ ] 검증 4종 실행 결과 첨부

## TASK-004 — Phase 2 종료 판정 + Phase 3 인수인계

* [ ] CLAUDE.md §1의 **9개 조건을 증거와 함께** 대조 (명령 + 출력)
* [ ] STATUS.md §6 학습 부채 **종결 처리** (결정 4)
* [ ] STATUS.md §7 문서 부채 종결 처리
* [ ] STATUS.md에 Phase 2 종료 판정표 + Phase 3 인수인계 목록
* [ ] `docs/reviews/07-phase2-closeout.md` — Phase 2 전체 회고
* [ ] README_AIUSAGE.md에 SPEC-004 항목
* [ ] PR 생성 → 서브에이전트 리뷰(`devops-local-platform` + `data-modeler`) → 머지
