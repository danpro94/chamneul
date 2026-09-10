# README_AIUSAGE — AI 활용 기록

> CLAUDE.md §13에 따른 AI 사용 대장. 각 항목: 날짜 / 작업 / AI 도구 / 인간(Owner) 결정 / 생성 산출물 / 검증 결과 / 잔여 리스크.
> 이 프로젝트의 AI 협업 원칙(소유/위임/읽기 라우팅)은 `docs/learning/02-ai-collaboration-and-ownership-strategy.md` 참조.
> 2026-09-09: 과거 `docs/README_AIUSAGE.md`(2026-06-22~06-30, 4개 세션)를 이 파일로 병합하고 원본은 삭제했다(ADR-006 부트스트랩, Owner 결정). 기존 "~2026-07-01 — M1 스켈레톤 (소급 기록)" 압축 요약 항목은 병합된 06-29·06-30의 상세 기록으로 대체한다.

---

## 2026-09-09 — VS Code 마이그레이션 부트스트랩: AI-Native/Spec-Driven 구조 전환 [위임]

### 작업

`docs/request/3-vscode-migration_prompt.md` §5 "프롬프트 1 — 부트스트랩" 지시를 실행:

1. 지정된 순서로 통독: CLAUDE.md → api.md §3 → model.md §5 → `docs/reviews/04-milestone4-definition.md` → `config/urls.py`/`accounts`/`advisors`(구현 완료분) → README_AIUSAGE.md.
2. 실제 코드(`urls.py`, `views.py`, `git ls-files`)를 근거로 생성 전 사전 보고(파일 목록/STATUS 초안/CLAUDE.md diff 미리보기/문서 모순 11건) 제시 → Owner 승인 수신.
3. `docs/adr/ADR-006-ai-native-spec-driven-skeleton.md` 작성(Status: Proposed) — CLAUDE.md §16 Constitutional lock에 따라 CLAUDE.md 직접 수정 없이 개정 diff만 제안.
4. `docs/00-project/STATUS.md` 신설 — 코드 실측 기준(16/44 엔드포인트 구현) 현황판.
5. 루트 `README.md` 신설 — "지도" 원칙(개요/스택/구조/Quick Start/문서 링크만).
6. `docs/testing/TEST_CRITERIA.md` 신설 — 테스트 0건 현실 명시 + M4 AC를 자동화 판정 기준으로 번역.
7. `specs/SPEC-001-concerns-api/{spec,plan,tasks,acceptance}.md` 신설 — api.md #16~25(M4-5 concerns) 대상.
8. `.claude/rules/{coding,security,testing,infrastructure}.md` 4종 신설 — CLAUDE.md §9~§12 원문을 내용 변경 없이 이동.
9. Owner 승인 결정 3건 실행: (a) SPEC-001 해석 2건(`is_deleted`=파생 필드, #16~19 active_role 게이트 없음) (b) 본 병합 작업 (c) `.claude/commands/` 슬래시 커맨드는 이번 범위에서 제외.

### 사용 도구

* Claude Code (VS Code Extension으로 마이그레이션 직후 첫 세션)

### 인간 결정 (Owner, 2026-09-09)

| 결정 | 내용 |
| --- | --- |
| 결정 1 | SPEC-001 해석 승인: api.md #16·#19·#22의 `is_deleted`는 DB 컬럼이 아니라 `deleted_at` 기반 파생 응답 필드로 해석 / #16~19(사용자 concern CRUD)는 `active_role` 게이팅 없음 |
| 결정 2 | `docs/README_AIUSAGE.md`(06-22~06-30 4항목)를 이 파일로 병합 후 원본 삭제 |
| 결정 3 | `.claude/commands/`(Pro Tip 3의 `/status`·`/spec-next`·`/gate`)는 이번 부트스트랩 범위에서 생성하지 않음 |

### 생성된 산출물

신규 12파일: `docs/adr/ADR-006-ai-native-spec-driven-skeleton.md`, `docs/00-project/STATUS.md`, `README.md`(루트), `docs/testing/TEST_CRITERIA.md`, `specs/SPEC-001-concerns-api/{spec,plan,tasks,acceptance}.md`(4), `.claude/rules/{coding,security,testing,infrastructure}.md`(4).

병합/삭제: `docs/README_AIUSAGE.md` 내용을 이 파일로 병합 후 삭제.

CLAUDE.md는 **수정하지 않음** — ADR-006이 Owner 승인으로 Accepted 전환된 뒤에만 개정 diff(사전 보고에서 제시한 초안)를 적용한다.

### 검증 결과

* 코드 변경 없음(문서/구조 전환만) — `manage.py check` 등 코드 검증 대상 없음.
* STATUS.md의 "구현됨 16개/미구현 28개"는 `config/urls.py`, `accounts/urls.py`, `advisors/urls.py` 실측으로 교차 확인.
* 문서 모순 11건을 발견 시점에 사전 보고로 전부 제시 → Owner가 그중 핵심 2건(SPEC-001 해석)만 명시 승인, 나머지(경로 drift, 43→44 등)는 ADR-006 Consequences에 반영해 승인 후 CLAUDE.md 개정과 함께 정정 예정.
* `.claude/agents/`가 이미 커밋되어 있음을 실측(요청 문서의 갭 #7 기술과 불일치 — 이미 해소된 상태였음), `.github/pull_request_template.md`도 기존재 확인.

### 잔여 리스크

1. **CLAUDE.md 미개정 상태**: ADR-006이 Proposed인 동안 CLAUDE.md §2/§3/§5/§16/§17은 여전히 옛 내용(43개 엔드포인트, 옛 경로명)이다. Owner가 ADR-006을 Accepted로 전환하기 전까지 CLAUDE.md와 STATUS.md/ADR-006 사이의 의도적 불일치가 존재한다.
2. **테스트 0건은 여전히 미해소** — TEST_CRITERIA.md는 판정 기준만 마련했을 뿐, 실제 테스트 코드는 SPEC-001 TASK-001부터 작성된다.
3. **M4-1~M4-4 AIUSAGE 미기록 갭 지속**(STATUS.md §7 문서 부채 #1) — 이번 세션은 이 갭을 메우지 않았다. 다음 세션에서 M4-1~M4-4(커밋 `855d1bf`~`b2eaf90`)를 소급 기록해야 한다.
4. **리뷰 노트 미작성**(`03-milestone3-review.md`, `04-milestone4-review.md`) 갭도 지속.
5. **SPEC 구조의 비용 재평가 필요**: ADR-006 Review Triggers에 명시된 대로, SPEC-001(M4-5) 완료 후 이 4파일 구조가 남은 M4-6~M4-8에도 유효한지 재평가해야 한다.

### 다음 단계 권장

1. Owner: ADR-006 승인(Accepted) 여부 결정 → 승인 시 CLAUDE.md 개정 diff 적용.
2. SPEC-001/TASK-001(concern 생성+목록, #16·#17) test-first 착수.
3. M4-1~M4-4 AIUSAGE 소급 기록(문서 부채 #1) — 별도 세션 권장(코드 검증 없이 로그만 재구성하는 작업이라 리스크 낮음).

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

## 2026-07-03 — M2 정의 및 승인

* **작업**: 마일스톤 번호 충돌 해소(reviews/01 vs learning/02), M2 통합 정의 문서 작성
* **AI 도구**: Claude Code
* **인간 결정**: 통합형 M2 승인(트랙 A [소유] + 트랙 B [위임]), gunicorn 서드파티 추가 승인(dependencies 그룹), 43개 엔드포인트 로드맵 유지
* **생성 산출물**: `docs/reviews/02-milestone2-definition.md` — 커밋 `8b2c0f8`
* **검증 결과**: 문서 작업 — Owner 승인으로 확정
* **잔여 리스크**: —

## 2026-06-30 — 독립 git 저장소 초기화 + 전략 IP 공개범위 분할 + ruff 도입

### 작업

1. 비밀정보 교차검증: chamneul이 상위 `personal` 저장소에 추적된 적 없음, `.env`/자격증명/하드코딩 비밀값 부재 확인.
2. Public 공개 전략 분석(Data-Driven): 코드/기술 문서는 공개 안전, 사업전략·평가 알고리즘 설계는 별도 IP 범주임을 분석.
3. `docs/1 서비스기획_v1.md` 전략 IP(ELO 점수 설계·조언자 평가 모델·승인 트리)를 공개 요약본 / 비공개 상세본으로 분할 (ADR-004).
4. ruff(lint+format) dev 의존성 도입. 운영 이미지 제외 구조 검증. 코드베이스 check/format 적용.
5. README_AIUSAGE 갱신 후 GitHub Public 저장소 생성·push.

### 사용 도구

* Claude Opus 4.8 (claude-opus-4-8)
* Claude Code CLI

### 인간 결정 (Owner, 2026-06-30)

| ID | 결정 |
| --- | --- |
| G1 | chamneul을 상위 `personal` 저장소에서 분리해 독립 git 저장소로 초기화 |
| G2 | 저장소는 Public 공개. 단 핵심 전략 IP는 비공개 처리 |
| G3 | 전략 문서 처리 = 옵션 B(분할 발행: 공개 요약본 + 비공개 상세본) + ADR-004 기록 |
| G4 | ruff(lint/format)는 dev 의존성으로 먼저 도입 |
| G5 | pytest 등 운영 불필요한 개발자 전용 테스트 패키지는 설치 제외 (테스트는 Django 기본 test runner 사용) |

### 생성된 산출물

신규:

* `docs/adr/ADR-004-strategy-doc-visibility-split.md` — 공개범위 3단계 분류 + 분할 발행 결정
* `docs/_private/1 서비스기획_v1_full.md` — 전략 IP 원본 보존 (gitignored, 비추적)
* `pyproject.toml` `[dependency-groups].dev` + `[tool.ruff]` 설정 블록

수정:

* `docs/1 서비스기획_v1.md` — 공개 요약본으로 교체 (ELO/평가/승인 로직 제거, ADR-004 참조 명시)
* `.gitignore` — `docs/_private/` 추가
* `pyproject.toml`/`uv.lock` — ruff dev 그룹 추가
* ruff format 적용: `accounts/models.py`, `common/uuid7.py`, `config/settings/{base,local,test,prod}.py`, `manage.py` (7개)

### 검증 결과 (전부 실행 완료)

* `git ls-files` → 추적 45→갱신, `.env`/`docs/_private` 추적 0건 ✅
* `git check-ignore` → `.env`·`docs/_private/`·`.venv` 모두 무시됨 ✅
* `uv export --no-dev` → 운영 의존성에 ruff 없음 (dev 그룹 격리 확인) ✅
* `uv run ruff check .` → All checks passed ✅
* `uv run ruff format .` → 7 files reformatted ✅
* `manage.py check` → 0 issues ✅
* `makemigrations --check --dry-run` → No changes detected ✅
* 공개 요약본 IP 누출 grep → ELO/Layer/점수설계/승인트리 키워드 부재 ✅

### 잔여 리스크

1. **`docs/_private/`는 git 백업 부재** — 별도 백업(private Notion/암호화) 권장 (ADR-004 trade-off 명시).
2. **중첩 저장소** — chamneul/.git이 상위 `personal` 저장소 디렉터리 내부에 위치. 상위가 chamneul을 커밋하지 않으므로 동작엔 무해하나, 장기적으로 chamneul을 별도 경로로 분리 이전하는 것이 깔끔.
3. **이전 리스크 해소**: 직전 Milestone 1의 "ruff 미도입"(§16 패키지 게이트) 리스크는 본 세션 G4로 해소됨.
4. **Notion drift 유지** — api.md §7 패치 미반영 상태 지속.

### 다음 단계 권장

1. Milestone 2 — `accounts`의 `UserRole` / `RoleGrant` / `GoogleIdentity` + createsuperuser→ADMIN 훅.
2. CI에 ruff check 게이트 추가 (Phase 3 CI/CD 진입 시).

## 2026-06-29 — Milestone 1: 실행 가능한 Django+PG 골격 + 커스텀 User

### 작업

1. 직전 두 세션(api.md/model.md) 통독 후 다음 단계 보고.
2. 런타임/툴링 결정 수신 및 적용 (아래 인간 결정).
3. uv 가상환경 셋업 가이드 제공 → Owner가 직접 `.venv`(Python 3.13) 생성·검증.
4. 의존성 `django-environ → python-dotenv` 교체 (`uv remove/add`).
5. Milestone 1 코드 작성: 프로젝트 골격(`manage.py`, `config/`), 설정 4분할(`base/local/test/prod`), `common/uuid7.py`, `accounts.User`(+ `UserManager`, admin), `/healthz`, Docker(`Dockerfile`, `docker-compose.yml`, `.dockerignore`), `.env.example`, `.gitignore` 보강.
6. 검증 실행 (아래 검증 결과).
7. `docs/reviews/01-milestone1-skeleton.md` 작성 (§14, 임베디드 학습 포함) + 본 로그 갱신.

### 사용 도구

* Claude Opus 4.8 (claude-opus-4-8)
* Claude Code CLI

### 인간 결정 (Owner, 2026-06-29)

| ID | 결정 |
| --- | --- |
| D1 | UUIDv7 구현 = `uuid_utils.uuid7` (Rust, 앱 레벨 생성; 관리형 RDS/Aurora의 `pg_uuidv7` 설치 차단 회피, 환경 drift 0) |
| D2 | 런타임 = Python 3.13 + Django 5.2 LTS |
| D3 | 의존성 관리 = `pyproject.toml` + uv (lockfile `uv.lock`) |
| D4 | 시스템 Python(`/usr/bin/python3`) 절대 호출 금지 — uv-managed venv 안에서만 작업 |
| D5 | `.env` 로딩 = `python-dotenv` (MVP 경량/직관 우선, 추후 `pydantic-settings` 전환 여지) |
| D6 | 코드 세션마다 `docs/reviews/`에 초급→고급 + DevOps 임베디드 학습 노트 작성 |

### 생성된 산출물

신규: `manage.py`, `config/{__init__,urls,health,wsgi,asgi}.py`, `config/settings/{__init__,base,local,test,prod}.py`, `common/{__init__,uuid7}.py`, `accounts/{__init__,apps,managers,models,admin}.py` + `accounts/migrations/0001_initial.py`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`, `docs/reviews/01-milestone1-skeleton.md`.

수정: `pyproject.toml`/`uv.lock`(django-environ→python-dotenv), `.gitignore`(보강).

### 검증 결과 (전부 실행 완료)

* `uv run` uuid7 → `uuid.UUID` version 7 ✅
* `manage.py check` → 0 issues ✅
* `makemigrations --check --dry-run` → No changes ✅
* `docker compose build` / `up` → db healthcheck healthy, app up ✅
* `migrate`(컨테이너 PG) → `accounts.0001_initial` 포함 전부 OK ✅
* `GET /healthz` → **HTTP 200** `{"status":"ok"}` ✅
* `createsuperuser`(email+nickname, noinput) → 성공, User PK UUIDv7, PBKDF2 해시 ✅

### 잔여 리스크

1. **createsuperuser ADMIN 역할 훅 미구현** — `UserRole` 모델이 없는 단계라 ADR-003의 "첫 superuser=ADMIN row" 훅은 Milestone 2로 이연(코드에 NOTE 명시).
2. **인증 로직 미구현** — login/logout/Google OAuth는 Milestone 3. 현재는 ADR-002 쿠키 정책 baseline만 설정.
3. **운영 서버** — Dockerfile CMD가 `runserver`(로컬 전용). gunicorn 전환 후속.
4. **ruff 미도입** — §16 패키지 게이트로 Owner 확인 후 도입 예정.
5. **Notion drift 유지** — api.md §7 패치 미반영(Owner 직접 작업 권장).
6. **로컬 `.env` 실파일 존재** — dev 값으로 생성됨(gitignore 제외). 운영 값과 무관.

### 다음 단계 권장

1. Milestone 2 — `accounts`의 `UserRole` / `RoleGrant` / `GoogleIdentity` + createsuperuser→ADMIN UserRole 훅.
2. 이후 Milestone 3 — 인증(signup/login/logout/OAuth) + DRF serializer/viewset/permission.

## 2026-06-26 — model.md v1 작성 + CLAUDE.md 헌법 갱신 (2차)

### 작업

1. 6/22 세션 종료 이후 docs 변경분 재확인: `2 mvp-scope.md` → `2 mvp-scope_v1.md` 파일명 변경, `docs/learning/01-api-to-model-and-docker.md` (Owner 학습 세션) 신설, `docs/api.md` 부분 수정 확인.
2. Owner의 model.md 작성 전 8가지 핵심 결정(M1~M8) 및 4가지 production-grade 보완사항(UUIDv7 / soft-delete + 부분 unique / 3단계 expand-contract 마이그레이션 / Read Replica + 인덱스 튜닝) 수신.
3. ADR-001 Decision 2 (SQLite 제거) 갱신.
4. `docs/model.md` v1 작성 — 12 섹션, 10 엔티티 + 1 audit 테이블, Mermaid ERD, DB / 서비스 제약, 인덱스 요약, EKS 인지 마이그레이션 가이드, Read Replica 라우팅, Django Admin 등록 패턴, 검증 체크리스트, 8건 Open Questions.
5. 초기 설계 ADR(ADR-004)를 별도로 도출했다가 Owner 지시에 따라 본문을 CLAUDE.md에 직접 흡수:
   * CLAUDE.md §4 — PG 16+ 전용 + 허용 PG 전용 기능 목록(ArrayField, JSONB, GIN, 부분 unique, UUIDv7, select_for_update) 추가.
   * CLAUDE.md §6.6 — soft-delete 컬럼을 `deleted_at` 로 명시 + partial unique 강제 패턴 코드 예시.
   * CLAUDE.md §16 — 헌법 잠금 허용 세션에 2026-06-26 추가, 해당 두 조항이 본문에 흡수되어 별도 supersession ADR 불요임을 명시.
6. ADR-004 파일 및 모든 참조 제거 (CLAUDE.md / model.md / ADR-001 에서 정리).
7. 본 항목 README_AIUSAGE.md 작성.

### 사용 도구

* Claude Opus 4.7 (claude-opus-4-7)
* Claude Code CLI

### 인간 결정 (Owner)

Owner가 직접 확정한 결정 (2026-06-26):

| ID | 결정 |
| --- | --- |
| M1 | 앱 레이아웃 = CLAUDE.md §3 5개 도메인 앱(`accounts`, `advisors`, `concerns`, `advice`, `notifications`) + `config` + `common`. Feedback은 `advice` 안에, Google OAuth/RoleGrant는 `accounts` 안에. |
| M2 | User 모델 = `AbstractBaseUser + PermissionsMixin` 완전 커스텀. 이메일 단일 로그인. |
| M3 | Soft delete = manager `objects` 가 자동 alive 필터 + `with_deleted()` 명시. |
| M4 | PG 전용 채택, `ArrayField`(고정 타입 배열) + `JSONField`(비정형). SQLite 비사용. ADR-001 수정 + CLAUDE.md §4 흡수 승인. |
| M5 | Enum = `TextChoices` 단일. |
| M6 | PK = UUID (EKS 분산 환경 / 스테이징↔프로덕션 이관 / 멀티 리전 대비). |
| M7 | AdviceHistory = 본문 필드 전체 snapshot per version. |
| M8 | ERD = Mermaid `erDiagram`. |
| 보완 #1 | PostgreSQL 16+ 환경의 **UUIDv7** 시계열 정렬 PK 채택 (B-Tree 페이지 무작위 플러시 회피). |
| 보완 #2 | Soft delete 모델의 unique 제약은 반드시 `WHERE deleted_at IS NULL` partial unique index 로 설계. |
| 보완 #3 | EKS 무중단 배포를 위한 3단계 expand-contract 마이그레이션 원칙을 model.md 마이그레이션 노트에 명시. |
| 보완 #4 | DB 라우팅 / Read Replica / Connection Pooling / 인덱스 튜닝 가이드를 model.md 에 명시. |

CLAUDE.md 직접 수정도 이번 세션에 한해 추가 승인(헌법 잠금 1회 추가 개방). ADR-004 본문은 CLAUDE.md 본문으로 흡수 + ADR-004 파일 및 모든 참조 제거 지시.

### 생성된 산출물

수정:

* `CLAUDE.md` — §4 (PG 16+ 전용 + 허용 PG 기능 목록 추가) / §6.6 (soft-delete `deleted_at` 컨벤션 + partial unique 강제 패턴 코드 예시) / §16 (헌법 잠금에 2026-06-26 세션 추가)
* `docs/adr/ADR-001-local-container-architecture.md` — Decision 2 본문 + Alternative §2 SQLite 항목 (PG 전용 + CLAUDE.md §4 단일 진실원천 명시)
* `docs/model.md` — ADR-004 참조 → CLAUDE.md §4/§6.6 로 치환, §12 References 정리 (이전 단계)

신규:

* `docs/model.md` v1 (이 세션 산출 — 12 섹션, 10 엔티티 + AdviceHistory, Mermaid ERD 포함)

삭제:

* `docs/adr/ADR-004-postgres-only-and-soft-delete-convention.md` (본문이 CLAUDE.md 에 흡수됨)

### 검증 결과

* 코드 변경 없음 — 본 세션은 명세/헌법 정렬.
* `grep -rn "ADR-004"` 잔존 참조 0건 확인.
* 문서 정합성은 M1~M8 + 보완 #1~#4 ↔ CLAUDE.md ↔ model.md 본문 매핑 표(직전 응답 §결정 반영 매트릭스)로 자체 교차 검증.
* 미수행 (다음 코드 세션에서 검증):
  * `python manage.py makemigrations --check --dry-run`
  * `python manage.py migrate` (빈 PG DB 대상)
  * `python manage.py createsuperuser` 후 첫 ADMIN UserRole row 생성 hook 확인
  * `docker compose up -d` + `curl /healthz`

### 잔여 리스크

1. **헌법 잠금 누적 변경**: 6/22 잠금 → 6/26 1회 추가 개방. 누적 형태로 lock-window가 늘어나면 헌법 잠금의 신뢰도가 떨어진다. 다음 변경은 반드시 새 ADR 절차로 가야 한다 (§16 갱신문 명시).
2. **UUIDv7 구현 의존성**: 앱 레벨 헬퍼(`common/uuid7.py`)가 RFC 9562 정확성/스레드 안전성을 보장해야 한다. `uuid_utils` 등 외부 패키지 채택 시 ADR 없이 진입 가능한지 경계가 모호 — 코드 세션 진입 전 1차 결정 필요.
3. **PG 전용 결정의 CI 영향**: 테스트 시 PG 컨테이너 부팅 시간이 CI 빌드를 늘릴 수 있다. testcontainer 최적화는 별도 ADR로 분리.
4. **Open Questions 8건** (model.md §11): `domain_category` enum 값 / `decision_context` 길이 / `ANSWERED → CLOSED` Public API / DELETED advice 재작성 / GIN 인덱스 / Notification URL 정책 / User 정지 흐름 / `pg_uuidv7` 채택 시점. 코드 세션 중 결정.
5. **Notion 원본 drift**: api.md §7 패치 + model 결정(특히 URI 변경, intended_lane 노출 정책) 미반영 상태. Owner 직접 갱신 권장.
6. **검증 미실행**: 모든 결정은 첫 마이그레이션/smoke test 단계에서 실 검증.

### 다음 단계 권장

1. Owner: Notion DB 갱신 (api.md §7 패치 + model.md 결정 반영).
2. UUIDv7 구현 패키지 결정 (자체 구현 vs `uuid_utils` 등).
3. Django scaffolding 세션 진입 — `config/settings/` 분리 + `accounts.User` 첫 마이그레이션부터.

## 2026-06-22 — Notion API v0 정합성 검토 + api.md v1 생성

### 작업

`docs/request/1-onboarding_prompt.md` 와 `docs/request/2-Notion-first_API 명세 검토_prompt.md` 의 지시에 따라:

1. 프로젝트 docs 전체 통독 (CLAUDE.md, ADR-001, mvp-scope.md, 서비스기획 v1, README).
2. Notion DB에서 export된 v0 API 명세 27개 markdown + 엔드포인트 CSV 통독.
3. CLAUDE.md / ADR-001 / MVP scope 기준으로 정합성 검토 (32개 이슈 식별).
4. Owner Decision Questions Q1~Q22 분리 제시 후 답변 수신.
5. 결정 반영을 위한 헌법 문서(CLAUDE.md) + ADR-001 + mvp-scope.md 패치를 항목별 승인 후 적용.
6. ADR-002 (Session 인증 정책), ADR-003 (ADMIN 역할 부여/회수) 신규 작성.
7. `docs/api.md` v1 작성 — 총 43 엔드포인트 (Notion v0 41건 − 토큰재발급 + `/healthz` + 관리자 역할 부여/회수 2건).
8. Notion 원본 갱신을 위한 패치 테이블을 `docs/api.md §7`에 동봉 (Notion DB는 직접 수정하지 않음).
9. `docs/model.md` 작성에 필요한 준비 요약(앱 목록, 모델 후보, FK, enum, 인덱스, unique, soft delete, transaction.atomic) 인라인으로 회신.

### 사용 도구

* Claude Opus 4.7 (claude-opus-4-7)
* Claude Code CLI

### 인간 결정 (Owner)

Owner가 직접 확정한 결정 (2026-06-22):

| ID | 결정 |
| --- | --- |
| Q1 | 인증 = Session(SSR) + HttpOnly Cookie 단일안. JWT/Token 미사용 |
| Q2 | Phase 2 v1 = 명세 전체(43건) 구현 |
| Q3 | `/api/v1/` prefix 유지, CLAUDE.md를 본 세션 한정 갱신 |
| Q4 | 사용자 소유 자원 URI를 `/users/me/{resource}` 로 통일 |
| Q5 | `intended_lane` 필드 유지하되 Public 응답 비노출 (관리자/시스템 참고용) |
| Q6 | 상태값을 CLAUDE.md §6.1/§6.2 5값으로 통일 (PENDING_REVIEW/published/draft/answered/REVIEWED 등 제거) |
| Q7 | 별도 ADMIN 부여 API 정의, grant + revoke 양쪽 |
| Q8 | 조언가의 `advisable_concern_types`는 taxonomy 영문 enum |
| Q9 | 배정 카디널리티 = 1 concern ↔ N advisor |
| Q10 | advisor 1명당 concern 1건은 advice 1개. version은 audit |
| Q11 | 내 고민 상세 조회 = 인증 필요 (본인만) |
| Q12 | 토큰 재발급 API 명세에서 제외 |
| Q13 | 회원가입 = 자동 로그인 (Set-Cookie sessionid) |
| Q14 | 가입 시 nickname 필수 (unique) |
| Q15 | 내 정보 조회 응답에서 `advisor_type` 제거 |
| Q16 | 조언가 신청 거부 사유는 신청자에게 노출 |
| Q17 | grant=POST `/admin/users/{user-id}/roles`, revoke=DELETE `/admin/users/{user-id}/roles/{role}` |
| Q18 | 최초 ADMIN = `python manage.py createsuperuser` |
| Q19 | concern_status = SUBMITTED → ASSIGNED → ANSWERED → CLOSED, soft delete는 별도 flag |
| Q20 | 세션 정책: cookie `sessionid`, HttpOnly + Secure + SameSite=Lax, 만료 14일, 매 요청 슬라이딩 갱신, 로그아웃 시 서버 세션 삭제 |
| Q21 | advice.version = 수정마다 +1, 응답 노출, 별도 audit 테이블 |
| Q22 | advisor `display_name` = nickname과 별개, 신청 시 입력, unique |

문서 수정도 항목별(A-1~A-8 / B-1~B-5 / C-1 / E-1 / E-2)로 Owner가 명시 승인.

### 생성된 산출물

수정:

* `CLAUDE.md` — §4 Auth / §5 MVP Scope / §6.1 intended_lane policy / §6.6 신설 Concern Status / §6.7 신설 Advice Versioning / §7 URI examples / §10 Auth security rules / §16 constitutional lock
* `docs/adr/ADR-001-local-container-architecture.md` — Decision Summary Auth 행 / Decision 4 본문 재작성 / DRF Token 한계 단락 제거 / Auth 구현 원칙 / Final Decision 블록
* `docs/2 mvp-scope.md` — Phase 2 v1 범위 = 43 엔드포인트 명시 한 줄 추가

신규:

* `docs/adr/ADR-002-session-authentication-policy.md`
* `docs/adr/ADR-003-admin-role-grant.md`
* `docs/api.md` v1 — 43 엔드포인트 전체 명세 + URI 변경 매핑 + Notion 갱신 패치 테이블

### 검증 결과

* 코드 변경 없음. 따라서 `python manage.py check` 등 코드 검증은 수행하지 않았다.
* 문서 정합성은 결정 매핑 표로 자체 교차 검증 (Q1~Q22 ↔ CLAUDE.md ↔ ADR-001/002/003 ↔ api.md).
* 미수행 항목(추후 단계에서 검증 필요):
  * `docker compose up -d` 기반 healthz 200 확인
  * `curl /api/v1/users/me/concerns` 흐름 검증
  * Django Admin 데이터 확인
  * Notion 원본 갱신(별도 작업)

### 잔여 리스크

1. **Notion 원본과의 drift**: `docs/api.md §7` 패치 테이블을 Notion에 반영하지 않은 상태로 코드 작업이 시작되면, 명세 source of truth가 분기될 수 있다. 코드 진입 전 Owner의 Notion 갱신이 권장된다.
2. **헌법 문서 잠금**: CLAUDE.md §16에 추가된 constitutional lock 조항에 따라, 이번 세션 이후 CLAUDE.md를 추가 수정하려면 새로운 ADR을 작성해야 한다. 향후 Claude 세션은 이 규칙을 인지하지 못할 수 있으므로, 매 세션 시작 시 CLAUDE.md 통독이 필수.
3. **Open Questions 8건**: `docs/api.md §6` 에 명시된 8개 비-차단 결정 (글자 수 상한, draft 모델링, CLOSED 전이 API, 페이지네이션 size 상한, OAuth nickname 산정 규칙 등)은 코드 작업 중 확정될 필요가 있다.
4. **세션 저장소**: ADR-002는 DB 세션을 Phase 2 기본으로 정함. 트래픽 발생 시 Redis 전환이 필요할 수 있으나 현 시점에서는 의도된 trade-off.
5. **계정 정지/탈퇴 흐름 부재**: 명세 v1은 가입/로그인/로그아웃까지만 다룸. 정지·탈퇴는 Phase 3+ 결정 사항.
6. **자동 알림 채널 없음**: 알림 model + 조회 API 만 v1에 포함. push/email/web socket은 명시적으로 제외.
7. **검증 미실행**: 코드 베이스가 아직 없어 실행 검증을 못함. `docs/model.md` 및 Django scaffolding 이후의 smoke test 단계에서 본 명세의 실현 가능성이 처음으로 검증된다.

### 다음 단계 권장

1. Owner: Notion DB 패치(`docs/api.md §7`) 반영.
2. 별도 세션에서 `docs/model.md` 작성 (본 세션의 model preparation summary를 입력으로 사용).
3. 모델 확정 후 Django scaffolding 시작 (앱 분리 → 모델 → 마이그레이션 → 권한/Serializer/ViewSet → URLConf → Admin 등록 → `/healthz` → smoke test).
