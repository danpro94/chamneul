# SPEC-004 — tasks

프롬프트 3 루프로 진행한다. 다만 TASK-001·002는 **문서 산출물**이라 "실패 테스트 먼저"가 적용되지 않는다 — 대신 **실행 출력을 먼저 확보하고 그것으로 문서를 쓴다**(추측으로 쓰지 않는다). 커밋 메시지에 `SPEC-004/TASK-00N`을 포함한다.

검증 4종 = `manage.py check` / `makemigrations --check` / `ruff check` / `manage.py test`.

## TASK-001 — 스모크 테스트 실행 + 문서화 ★ — **완료 (2026-09-16)**

* [x] **Owner 승인 후 볼륨 백업**(`pg_dump` 92K, 20테이블, 정상 종료 마커 확인) → `down -v`. 덤프는 프로젝트 밖(scratchpad)에 둠 — CLAUDE.md §10
* [x] `docker compose up -d --build` → `db Waiting → Healthy → app Starting` 순서 확인(`depends_on: service_healthy` 동작 증거)
* [x] `migrate` 25건 적용 → `createsuperuser` → **ADMIN `UserRole` 행 자동 생성 확인**(ADR-003 §1)
* [x] `curl /healthz` → 200 (0.0075s)
* [x] **사용자 여정 12단계 전항 통과** — 세 배우 세션 동시 유지, 실제 출력 수집
* [x] 비정상 경로 3종 — 마이그레이션 미적용 / DB 정지 / DB 재기동
* [x] **DB 재기동 시 앱 재시작 불필요** 확인(`StartedAt` 불변 + 여정 전체 재통과)
* [x] `docs/smoke-test.md` 작성 — 절차 + 실제 출력 + **갭 9건** + 운영 체크리스트
* [x] `README.md`에 스모크 절차 링크 + 문서 지도 2행 추가
* [x] 실행 중 발견한 테스트 픽스처 오류 3곳 정정(`reflective_questions`는 배열이 아니라 `TextField`)
* [x] 검증 4종 — check 0 issues / makemigrations No changes / ruff passed / **283 tests OK**

## TASK-002 — model.md 정합화 — **완료 (2026-09-16)**

* [x] `data-modeler` 재실행 → drift **22건 재측정** (기록된 6건보다 많음 — spec §7 리스크 3 적중). 기록된 4건은 전부 현존 + M4 신규 18건
* [x] 22건 전부 반영 — **문서를 코드에 맞춤**. 스키마(필드·제약·인덱스·on_delete)는 원래 완전 일치했고 drift는 전부 **서술 계층**이었다
* [x] 코드가 약해 보이는 **5건(B-01~B-05)은 반영하지 않고 분리** — 전부 Django Admin이 서비스 레이어를 우회하는 경로. Owner 판단 대기
* [x] model.md §1.1 시각 정책을 UTC로 교체 (결정 2) + `config/settings/base.py`의 **잘못된 주석** 정정(코드는 옳았음)
* [x] §10 체크리스트 12항 전항 `[x]` 처리 (M3·M4·스모크에서 검증 완료)
* [x] §11 Open Question 5건(O-1·2·3·4·6) 종결 처리, 3건(O-5·7·8) 유지
* [x] 검증 4종 — check 0 issues / makemigrations No changes / ruff passed / **283 tests OK**

## TASK-003 — 이월 2건 + 문서 부채 청산 — **완료 (2026-09-17)**

* [x] **B-01~B-05 함께 처리** (Owner 승인) — Admin 우회 경로 5건 차단, `AdminBypassGuardTests` 6개로 고정
* [x] **결정 3**: #21이 미배정 조언가에게 **404** — 실패 테스트 먼저(403≠404 2건 확인 후 착수)
* [x] `get_assigned_concern()`을 쿼리셋 스코프 판정으로 변경. `concern__deleted_at__isnull=True` 명시 — FK 역참조는 base manager를 타서 소프트 삭제를 우회한다(TASK-002에서 문서화한 D-08 함정)
* [x] 배정 해제 시에도 404 / `active_role≠ADVISOR`는 **403 유지**(§1.8 3행) — 대조군 테스트 추가
* [x] api.md #21 정정 + **§1.8 "미해결 예외" 문단 제거** — 404 규칙의 예외가 사라졌다
* [x] **결정 2**: api.md §1.7 전면 교체(3계층 표) + model.md §1.1 + `config/settings/base.py` 주석. 예시 문자열도 UTC로
* [x] **AR-01 잔여**: api.md #11 접근 제어 조건을 신규 규칙으로 정정 (#43과 어긋나 있던 것)
* [x] `README_AIUSAGE.md`에 M4-1~M4-4 소급 — **git 이력 실측**, 근거가 없는 항목은 "미기록"으로 명시
* [x] `docs/reviews/03-milestone3-review.md` 신규 (소급 — 사후에 드러난 것을 구분 표기)
* [x] `docs/reviews/04-milestone4-review.md` 신규 (M4 전체를 가로지르는 관점)
* [x] STATUS.md 문서 부채 3건 종결 + **학습 부채 14건 폐기**(결정 4)
* [x] 검증 4종 — check 0 issues / makemigrations No changes / ruff passed / **291 tests OK**

## TASK-004 — Phase 2 종료 판정 + Phase 3 인수인계 — **완료 (2026-09-17)**

* [x] CLAUDE.md §1의 **9개 조건 전항**을 증거와 함께 대조 — 9/9 충족
* [x] **라우트 44개 실측** — URL 패턴은 37개지만 (경로, 메서드) 쌍은 정확히 44개(6개 경로가 메서드 공유)
* [x] 결정 2·3이 **실행 중인 시스템**에 반영됐는지 실증 — 응답 시각 `…Z`(`+09:00` 0회), #21 미배정 조언가 **404** / `active_role≠ADVISOR` **403**
* [x] Admin 감사 무결성 라이브 확인 — `AssignmentAdmin` add/change/delete 전부 `False`, `AdviceAdmin` 본문 readonly
* [x] STATUS.md §6 학습 부채 종결(결정 4) + §7 문서 부채 3건 종결 (TASK-003)
* [x] STATUS.md에 **Phase 2 완료 판정표** + Phase 3 진입 전 권고 4건
* [x] `docs/reviews/07-phase2-closeout.md` — 조건별 증거표 + 인수인계 + 회고
* [x] README_AIUSAGE.md에 SPEC-004 항목
* [ ] PR 생성 → 서브에이전트 리뷰 → 머지  ← 진행 중
