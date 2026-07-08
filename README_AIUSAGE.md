# README_AIUSAGE — AI 활용 기록

> CLAUDE.md §13에 따른 AI 사용 대장. 각 항목: 날짜 / 작업 / AI 도구 / 인간(Owner) 결정 / 생성 산출물 / 검증 결과 / 잔여 리스크.
> 이 프로젝트의 AI 협업 원칙(소유/위임/읽기 라우팅)은 `docs/learning/02-ai-collaboration-and-ownership-strategy.md` 참조.

---

## 2026-07-08 — M3: 도메인 앱 모델 4종 [위임] + UX 사양

* **작업**: advisors/concerns/advice/notifications 4개 앱 모델 7종 + Admin 등록 + 마이그레이션 생성(앱 단위 커밋 분할). 병렬로 Phase 2 화면 흐름·API-to-screen 매핑 UX 사양 작성
* **AI 도구**: Claude Code (코드+설명 동시) + 서브에이전트 `data-modeler`(모델 정합 리뷰), `frontend-ux-architect`(UX 사양)
* **인간 결정**: M3 정의 승인, taxonomy 공유 배치 수용, 마이그레이션 적용·AC 검증 전부 Owner 직접 수행(showmigrations·sqlmigrate WHERE 절 3종·Admin 7종 조회·soft delete shell 검증), 이해 질문 3개 답변(1·2 부분, 3 통과), 드릴#2·M3 퀴즈·리뷰 노트는 M4 이후로 이월
* **생성 산출물**: `common/taxonomy.py`, `advisors/`·`concerns/`·`advice/`·`notifications/` 앱, 마이그레이션 4종, `docs/ux/01-phase2-screen-flows.md` — 커밋 `e3db9c1`·`de2e3a7`·`7d5e2f0`·`82d5e6c`·`a3823d1`·`05f60b2`
* **검증 결과**: check 0 issues, makemigrations --check No changes, ruff 통과, 부분 유니크 3종 WHERE 절 확인, data-modeler 리뷰 블로커 0(메이저 1건 I-1은 admin status readonly로 즉시 해소), Owner migrate·shell 검증 성공(soft delete 기본 감춤 실측)
* **잔여 리스크**: Owner 결정 대기 — 비익명 표시명 정책(C-6/C-7)·O-1 DomainCategory 확정·UX발 API 개선 4건(M4 전 처리 권고). model.md 문서 drift 6건 기록 대기. 학습 부채 누적(드릴#2·M3 퀴즈 이월 포함)

## 2026-07-07 — M2 마감 문서화

* **작업**: M2 리뷰 노트 작성(explain-first: Owner 선요약 → AI diff 분석), README_AIUSAGE 신설, M3 정의 문서 번호 정리
* **AI 도구**: Claude Code (Fable 5)
* **인간 결정**: 문서 번호 체계 = 마일스톤 번호(`NN-milestoneN-{definition,review}`), M3 승인 보류, WB-1은 M3 착수 전 이월
* **생성 산출물**: `docs/reviews/02-milestone2-review.md`, `README_AIUSAGE.md`, `docs/reviews/03-milestone3-definition.md`(초안, 승인 대기)
* **검증 결과**: 문서 작업 — 코드 변경 없음
* **잔여 리스크**: M2 학습 부채 9건 (리뷰 노트 원장 참조), WB-1 미실시

## 2026-07-05~06 — M2 학습 게이트 (드릴 #1 + 퀴즈)

* **작업**: 장애 드릴 #1 "DB 다운"(chaos-coach 주입·힌트, 진단·복구는 Owner) / 이해 퀴즈 5문(drill-master 출제·채점)
* **AI 도구**: Claude Code 서브에이전트 `chaos-coach`, `drill-master`
* **인간 결정**: 복구 명령 선택(`docker compose up -d db`), 포스트모템 작성, WB-1 다음 세션 이월
* **생성 산출물**: 드릴 채점표·포스트모템, 퀴즈 채점표(42/100), 학습 부채 원장 9건
* **검증 결과**: 드릴 이수(핸즈온 43분, 예산 +13분), db 복구 실측(healthy, /healthz 200)
* **잔여 리스크**: 부채 ④(401/403/409)·⑤(atomic)는 M4 착수 전 재퀴즈 필수

## 2026-07-05 — M2 트랙 B: accounts 도메인 확장 [위임]

* **작업**: `UserRole`/`RoleGrant`/`GoogleIdentity` 모델, `create_superuser` ADMIN 부트스트랩 훅(ADR-003), Django Admin 3종 등록, 마이그레이션 `accounts.0002` 생성
* **AI 도구**: Claude Code (코드+설명 동시 생성, 이해 확인 질문 3개 출제·채점)
* **인간 결정**: 마이그레이션 적용은 Owner 직접 수행, AC 검증(showmigrations·createsuperuser→ADMIN row·Admin 조회) Owner 수행, 이해 질문 답변
* **생성 산출물**: `accounts/{models,managers,admin}.py` 확장, `accounts/migrations/0002_*.py` — 커밋 `76b664e`
* **검증 결과**: `manage.py check` 0 issues, `makemigrations --check` No changes, ruff 통과, sqlmigrate로 제약·인덱스 확인, Owner가 컨테이너에서 migrate 적용 성공
* **잔여 리스크**: M1 시절 생성된 기존 superuser에는 ADMIN UserRole이 소급 생성되지 않음(수동 추가 필요). `active_role`↔`UserRole` 정합은 M4 서비스 레이어에서 강제 예정

## 2026-07-03~05 — M2 트랙 A: 런타임 승격 [소유]

* **작업**: Dockerfile 멀티스테이지(builder/runtime)·비루트(uid 10001)·gunicorn 전환, docker-compose.override.yml dev 경로 분리 — **전량 Owner 손코딩**
* **AI 도구**: Claude Code — 코치 모드(시작 전 체크리스트, 막힘 시 단계적 힌트만) + `ops-reviewer` 서브에이전트 리뷰 3라운드 + gunicorn 버전/보안 사실 검증(PyPI·OSV 실측)
* **인간 결정**: dev/prod 분기 = override 병합 패턴(리스크 #1), runtime에 uv 미탑재, gunicorn 26.0.0 dependencies 추가(§16 승인), `.claude/agents/` 미커밋
* **생성 산출물**: (AI 생성 아님 — Owner 작성) `Dockerfile`, `docker-compose.override.yml`; AI는 리뷰 코멘트만. 커밋 `156ded9`
* **검증 결과**: 1차 블로커 5 → 2차 블로커 1 → 3차 **블로커 0·메이저 0 통과**. 운영 경로 gunicorn `/healthz` 200, `exec app id` uid=10001, 시크릿 전수 grep 무검출 (전부 실측)
* **잔여 리스크**: gunicorn 경로 정적파일 서빙 부재(/admin 정적 404 — M5 문서 명시 예정), FROM 버전 2곳 독립 표기, 브루트포스 방어 Phase 3 이월

## 2026-07-02~03 — M2 정의 및 승인

* **작업**: 마일스톤 번호 충돌 해소(reviews/01 vs learning/02), M2 통합 정의 문서 작성
* **AI 도구**: Claude Code
* **인간 결정**: 통합형 M2 승인(트랙 A [소유] + 트랙 B [위임]), gunicorn 서드파티 추가 승인(dependencies 그룹), 43개 엔드포인트 로드맵 유지
* **생성 산출물**: `docs/reviews/02-milestone2-definition.md` — 커밋 `8b2c0f8`
* **검증 결과**: 문서 작업 — Owner 승인으로 확정
* **잔여 리스크**: —

## ~2026-07-01 — M1 스켈레톤 (소급 기록)

* **작업**: Django/DRF 스켈레톤, custom User(email 로그인·uuid7 PK), /healthz, 초기 Dockerfile·docker-compose.yml, ruff 도입
* **AI 도구**: Claude Code (상세는 `docs/reviews/01-milestone1-skeleton.md`)
* **인간 결정**: PostgreSQL 단일 엔진(SQLite 배제), 세션 인증 단일 전략, uuid7 앱 레이어 생성
* **생성 산출물**: `config/`·`accounts/`·`common/` 스켈레톤, `accounts.0001` — 커밋 `a3ffab2`, `06c47a5`
* **검증 결과**: /healthz 200, compose 기동, Admin 접속 (reviews/01 참조)
* **잔여 리스크**: → M2에서 런타임 승격으로 해소됨
