# ADR-009. AI 도구 체계: MCP 서버 · 에이전트 · Claude Code 기능 선정

## Status

Proposed (Owner 승인 대기)

## Date

2026-10-22 (Proposed)

## Supersedes

없음. CLAUDE.md는 고치지 않는다. 이 ADR은 CLAUDE.md §16(서드파티 패키지 추가, CI/CD, AWS 도입 때 승인 필요)의 승인 게이트를 **항목별로 통과시키기 위한 요청서**다. 아래 표에서 "§16 승인" 칸이 `필요`인 항목은 Owner가 따로 승인해야 도입한다.

---

## Context

* chamneul은 Phase 2(로컬 컨테이너 MVP)를 진행 중이다(SPEC-005, 엔드포인트 47개). Phase 3 목표는 AWS Managed EKS다.
* 이미 갖춘 것: `.claude/agents/` 아래 프로젝트 서브에이전트 8개(api-architect, data-modeler, security-reviewer, devops-local-platform, frontend-ux-architect, ops-reviewer, chaos-coach, drill-master)와 `.claude/rules/*.md`.
* 아직 없는 것: `.mcp.json`, `.claude/settings.json`(hooks), `.github/workflows/`, Dependabot 설정. 자동 검증 장치가 없다. ADR-006 Trade-offs에도 "CI 없는 이 프로젝트에서는 기계적으로 걸러지지 않는다"는 기록이 있다.
* 소유권 정책(`docs/learning/02-ai-collaboration-and-ownership-strategy.md`): 인프라 파일(Dockerfile, compose, k8s, Terraform)은 Owner가 직접 손으로 쓴다. AI는 코치·리뷰어 역할만 한다. 따라서 AI 도구는 **읽고, 검사하고, 경고하는 쪽**으로만 고른다.
* 보안 규칙(`.claude/rules/security.md`): 비밀값은 커밋하지 않는다. 사용자 소유 데이터에는 객체 단위 접근 제어를 건다. MCP 서버는 그 자체로 새 비밀값(토큰)이 생기는 곳이자, 프롬프트 인젝션이 들어오는 입구다.

## Decision

8개 영역(보안 검토, 프로젝트 정리, 개발 보조, DevOps, 취약점 방어·헷지, 리팩터링, 개발 효율, 사후 운영·유지보수)을 아래 **10개 항목**으로 맡는다. 원칙은 세 가지다.

1. **읽기 전용이 기본이다.** 쓰기 권한은 Claude Code의 파일 편집(사람이 diff를 보고 승인하는 경로)에만 둔다. MCP를 통한 원격 쓰기(PR 머지, 이슈 생성, DB 변경, AWS 변경)는 열지 않는다.
2. **공식 또는 벤더가 관리하는 것만 쓴다.** 커뮤니티 포크는 쓰지 않는다.
3. **비밀값이 들어간 MCP 설정은 개인 범위(`local`/`user` scope)에 둔다.** 저장소에 커밋되는 `.mcp.json`에는 비밀값이 없는 서버, 또는 `${VAR}` 확장으로 환경변수만 참조하는 서버만 넣는다.

| # | 항목 | 영역 | 단계 | §16 승인 | 쓰기 범위 |
| --- | --- | --- | --- | --- | --- |
| 1 | Claude Code **hooks**(편집 후 ruff 자동 실행, `.env`·인프라·CLAUDE.md 편집 차단) | 개발 효율, 소유권 정책 강제 | now | 불필요(설정 파일만, 패키지 추가 없음) | 없음(차단만 함) |
| 2 | 내장 **`/security-review` · `/code-review`** + 기존 서브에이전트 8개 | 보안 검토, 리팩터링 | now | 불필요 | 없음(`--fix` 쓰지 않음) |
| 3 | **GitHub 공식 MCP 서버**(`github/github-mcp-server`, 원격, 읽기 전용) | 프로젝트 정리 | now | 불필요(원격 HTTP, 로컬 패키지 없음). 토큰 발급은 Owner가 직접 | 읽기 전용 강제 |
| 4 | **Context7 MCP**(Upstash, 버전별 라이브러리 문서) | 개발 보조 | now | 불필요(원격 HTTP) | 없음 |
| 5 | **Dependabot**(uv · docker · github-actions) + GitHub **secret scanning / push protection** | 취약점 방어·헷지 | now | **필요**(`.github/dependabot.yml`은 자동 PR 봇이라 CI/CD 경계선에 있음) | 봇이 PR만 열고, 머지는 사람이 함 |
| 6 | **Semgrep MCP**(Semgrep 공식, beta) | 보안 검토, 취약점 방어 | now(로컬) | **필요**(`semgrep` 바이너리 설치 = 서드파티 도구) | 없음(스캔만) |
| 7 | **PostgreSQL 읽기 전용 MCP**(로컬 compose DB 전용, SELECT 전용 role) | 개발 보조, 데이터 확인 | now(선택) | **필요**(서드파티 서버) | DB role 수준에서 SELECT만 허용 |
| 8 | **Playwright MCP**(Microsoft 공식) | 개발 보조(MVP UI 스모크) | now(선택) | **필요**(npm 패키지) | 로컬 브라우저만 |
| 9 | **CodeQL default setup**(GitHub code scanning) | 취약점 방어 | Phase 3(CI 도입 시) | **필요**(GitHub Actions에서 돈다 = CI/CD) | 없음(경고만) |
| 10 | **Sentry MCP**(Sentry 공식, 원격, 기본 읽기 전용) | 사후 운영·유지보수 | Phase 3(배포 후) | **필요**(sentry-sdk 앱 의존성 추가가 먼저 필요) | 기본 읽기 전용 |

### 항목별 상세

#### 1. Claude Code hooks

* **하는 일**: `PostToolUse`(Edit/Write 뒤)에 `ruff check`를 돌린다. `Stop` hook에서 테스트를 돌리는 것은 느리고 반복 루프 위험이 있어 1차 도입에서 제외한다(가이드 §1). `PreToolUse`에서 `.env*`, `Dockerfile`, `docker-compose*`, `.dockerignore`, `k8s/`, `*.tf`, `CLAUDE.md` 편집을 막는다(exit 2). CLAUDE.md는 §16 동결 조항이라 함께 막는다.
* **chamneul에 맞는 이유**: CLAUDE.md §17-4("check / makemigrations --check / ruff / test를 돌리고 실제 출력을 보여라")와 §17-5("Dockerfile / compose / .env는 손대지 마라")가 지금은 **AI의 기억력에만** 의존한다. hooks는 이를 하네스가 실행하는 규칙으로 바꾼다. ADR-006이 남긴 "기계적으로 걸러지지 않는다"는 공백을 CI 없이 메운다.
* **리스크**: hooks는 사용자 권한으로 셸 명령을 실행한다. 저장소에 커밋된 hook은 clone한 사람의 기기에서도 돈다.
* **완화**: hook 스크립트는 짧게 쓰고 리뷰한다. 네트워크 호출을 넣지 않는다. 1차 도입에는 테스트 hook을 넣지 않고, 넣게 되면 프로젝트 표준 명령(`uv run python manage.py test --settings=config.settings.test`)만 쓴다.

#### 2. `/security-review`, `/code-review`, 기존 서브에이전트

* **하는 일**: 브랜치 diff를 대상으로 보안 리뷰와 정확성 리뷰를 한다. 도메인 규칙 리뷰는 기존 security-reviewer, api-architect, data-modeler가 맡는다.
* **chamneul에 맞는 이유**: 실제 결함 이력이 있다. coding.md에 기록된 3개 앱의 상태 전이 결함은 서브에이전트 리뷰에서 발견됐다. 범용 리뷰(내장 명령)와 도메인 리뷰(프로젝트 에이전트)를 함께 쓰면 서로의 사각지대를 메운다.
* **리스크**: 리뷰를 통과했다는 사실을 "안전하다"로 오해할 수 있다. `--fix` 같은 자동 수정은 Owner의 이해 없이 코드를 바꾼다.
* **완화**: AI 리뷰는 **두 번째 리뷰어일 뿐 게이트가 아니다.** 자동 수정 옵션은 쓰지 않는다. 결과는 `docs/reviews/`에 기록한다(§14).

#### 3. GitHub 공식 MCP 서버(읽기 전용)

* **하는 일**: Claude Code 안에서 PR, 이슈, Actions 로그, Dependabot 경고, code scanning 경고를 읽는다.
* **chamneul에 맞는 이유**: SPEC/TASK 단위 PR 이력과 리뷰 코멘트를 STATUS.md·README_AIUSAGE.md 정리에 바로 쓸 수 있다. #5와 #9 경고를 한 곳에서 본다.
* **리스크**: 이슈나 PR 본문에 심어진 **프롬프트 인젝션**이 있을 수 있다(공개 저장소이므로 누구나 이슈를 쓸 수 있다). PAT가 새면 저장소가 노출된다.
* **완화**: fine-grained PAT를 `danpro94/chamneul` 하나에만, Read-only 권한으로 발급하고 만료일을 90일 이하로 둔다. 서버도 읽기 전용 모드로 연결한다(원격의 `/readonly` 경로 또는 `X-MCP-Readonly` 헤더). 이 설정은 `local` scope에만 둔다. MCP가 읽어 온 텍스트는 데이터일 뿐 지시가 아니라는 점을 가이드에 명시한다.

#### 4. Context7

* **하는 일**: Django 5.2, DRF, psycopg 3, Playwright 같은 라이브러리의 **버전별 최신 문서**를 컨텍스트에 넣는다.
* **chamneul에 맞는 이유**: 모델의 학습 시점과 Django 5.2 API 사이의 차이(예: 폐기된 API 제안)를 줄인다. Owner가 "이 코드가 맞는 API인가"를 설명할 근거가 생긴다.
* **리스크**: 외부 문서가 컨텍스트에 들어오므로 간접 인젝션 가능성이 있다. 쿼리 내용(라이브러리 이름, 질문)이 외부 서비스로 나간다.
* **완화**: 쿼리에 코드나 비밀값을 붙여 넣지 않는다. API 키는 rate limit용 무료 키로 쓰고 `local` scope에 둔다(키 없이도 작동한다).

#### 5. Dependabot + secret scanning / push protection

* **하는 일**: `pyproject.toml`/`uv.lock`(uv 생태계), Dockerfile 베이스 이미지, (나중에) Actions 버전의 취약점과 업데이트를 PR로 알린다. 커밋에 비밀값이 섞이면 push를 막는다.
* **chamneul에 맞는 이유**: security.md 규칙 1번("Never commit secrets")을 사람의 주의력이 아닌 플랫폼이 강제하게 된다. 버전 고정과 업데이트 PR은 "헷지"(알려진 CVE에 머무르지 않기)의 최소 장치다.
* **리스크**: 업데이트 PR의 자동 머지는 공급망 공격의 경로가 된다.
* **완화**: 자동 머지는 쓰지 않는다. 주간 주기에 PR 수 상한을 둔다. Dockerfile 관련 PR은 Owner가 직접 반영한다(소유권 정책).

#### 6. Semgrep MCP

* **하는 일**: 로컬에서 Django/Python 규칙(SQL 인젝션, `mark_safe`, CSRF 예외, 하드코딩된 비밀값 등)으로 SAST 스캔을 한다.
* **chamneul에 맞는 이유**: LLM 리뷰(#2)는 확률적이고, 규칙 기반 스캐너는 결정적이다. 둘은 서로를 헷지한다. 이 조합은 Django 프로젝트에 특히 잘 맞는다.
* **리스크**: 이 서버는 beta이고 배포 방식이 바뀌었다. 독립 저장소 `semgrep/mcp`는 deprecated(아카이브)되었고, 이후 업데이트는 공식 `semgrep` 바이너리로 나간다고 README에 적혀 있다. 바이너리 내장 MCP의 정확한 실행 명령은 **미검증**이다. `SEMGREP_APP_TOKEN`으로 로그인하면 결과가 Semgrep AppSec Platform과 연동된다.
* **완화**: 버전을 고정한다. 처음에는 로그인 없이(토큰 없이) OSS 규칙으로 시작한다. 아카이브된 `uvx semgrep-mcp`는 쓰지 않는다. 도입 전에 공식 문서로 현재 설치법을 다시 확인한다.

#### 7. PostgreSQL 읽기 전용 MCP(로컬 전용)

* **하는 일**: 로컬 compose DB의 스키마와 행을 조회한다. 마이그레이션 결과, partial unique index, soft delete 행을 확인할 때 쓴다.
* **chamneul에 맞는 이유**: §6.6 soft delete와 partial unique, §6.7 advice history 같은 규칙은 "DB에 실제로 어떻게 들어갔는가"로 검증해야 한다.
* **리스크(중요)**: Anthropic 레퍼런스 Postgres 서버는 "read-only 트랜잭션"으로 읽기 전용을 흉내 냈다. 그런데 다중 문장 입력의 `COMMIT`으로 이를 우회할 수 있었다는 보고가 있다(Datadog Security Labs 사례로 인용됨, 원문 **미검증**). 서버 측 플래그는 신뢰 경계가 아니다.
* **완화**: ① 접속 계정은 **SELECT만 GRANT된 전용 role**(`chamneul_ro`)을 쓴다. 이것만이 실패해도 안전한 경계다. ② 접속 대상은 `localhost` compose DB로만 한정한다. **dev/prod(RDS)에는 절대 연결하지 않는다.** ③ 연결 문자열은 환경변수로만 넘긴다. ④ 1순위 후보는 crystaldba/postgres-mcp의 `--access-mode=restricted`다(read-only 트랜잭션 + `COMMIT`/`ROLLBACK` 파싱 차단). 그래도 ①을 생략하지 않는다. 벤더 공식 서버가 아니라 전문 업체(Crystal DBA) 관리 OSS이므로 원칙 2의 예외이며, Owner 승인 사항이다.

#### 8. Playwright MCP

* **하는 일**: 실제 브라우저로 로컬 UI 프로토타입과 Django Admin을 조작하고 스냅샷을 찍는다.
* **chamneul에 맞는 이유**: ADR-008의 교훈("빈칸은 화면을 만들 때 드러난다")을 반복 가능한 스모크로 만든다. CSRF 쿠키와 `X-CSRFToken` 흐름(#44)을 브라우저 수준에서 확인할 수 있다.
* **리스크**: 브라우저가 외부 사이트를 열면 페이지 내용을 통한 인젝션이 들어올 수 있다. 개인 Chrome 프로필을 쓰면 쿠키가 노출된다.
* **완화**: 격리된 프로필(기본 동작)을 쓰고 `localhost`만 연다. `@latest` 대신 버전을 고정한다.

#### 9. CodeQL(Phase 3)

* **하는 일**: Python 의미 분석 기반 code scanning을 한다.
* **chamneul에 맞는 이유**: #6과 다른 엔진이므로 보완 관계다. Phase 3에서 CI를 도입할 때 함께 켠다.
* **리스크와 완화**: GitHub Actions에서 돌므로 CI/CD 승인(§16)과 묶어서 결정한다. 경고만 내고 머지를 막지 않는 상태로 시작한다.

#### 10. Sentry MCP(Phase 3)

* **하는 일**: 배포 환경의 오류 이슈, 스택트레이스, 릴리스를 Claude Code에서 조회한다.
* **chamneul에 맞는 이유**: 유지보수 단계에서 "운영 오류 → 원인 코드 → SPEC 재현 테스트" 루프를 짧게 만든다. 기본이 읽기 전용이다.
* **리스크**: 이벤트 데이터에 **사용자 고민 원문(민감 개인정보)**이 섞일 수 있다.
* **완화**: sentry-sdk에서 `send_default_pii=False`를 쓰고 요청 본문 스크러빙을 먼저 설정한다. 그다음에 MCP를 연결한다. OAuth는 최소 scope로 받는다.

### 도입하지 않는 것

| 후보 | 결정 | 이유 |
| --- | --- | --- |
| AWS MCP 서버들(awslabs, EKS MCP 등) | 지금은 **도입하지 않음**. Phase 3에서 읽기 전용(EKS MCP `--read-only` + `eks-mcp:CallReadOnlyTool`만 허용하는 IAM)으로 재검토 | 소유권 정책상 Terraform, k8s, IAM은 Owner가 직접 쓴다. 쓰기가 가능한 AWS MCP는 그 학습 자체를 대신해 버린다. 조회 용도도 `aws`/`kubectl`을 직접 치는 것이 학습 목표다 |
| Terraform / k8s 매니페스트를 생성하는 MCP·에이전트 | 도입하지 않음 | 위와 같음. 인프라 리뷰는 기존 ops-reviewer(코멘트만)로 충분하다 |
| `anthropics/claude-code-action`(GitHub Actions의 @claude) | 지금은 **도입하지 않음**. Phase 3 CI 도입 시 재검토 | Contents·PR·Issues에 **쓰기 권한**이 필요하다. API 키를 저장소 시크릿에 둬야 한다. 1인 프로젝트에서 로컬 `/code-review`와 기능이 겹친다. CI/CD는 §16 승인 대상이다 |
| Docker MCP Toolkit / Docker 제어 MCP | 도입하지 않음 | 컨테이너 기동·리셋 진단은 chaos-coach 드릴로 Owner가 직접 익히는 영역이다. 컨테이너 제어 권한을 AI에 주면 소유권 정책과 충돌한다 |
| Snyk / Socket | 보류 | 1인 무료 범위에서는 Dependabot + Semgrep(Supply Chain 포함)과 기능이 겹친다. 외부 계정이 늘어난다. 필요해지면 재평가한다 |
| 커뮤니티 포크 MCP(semgrep, postgres 비공식 등) | 금지 | 관리 주체와 업데이트 경로를 보장할 수 없다 |
| 쓰기 도구 자동 승인(`--dangerously-skip-permissions`, MCP 쓰기 툴 allowlist) | 금지 | 인젝션 한 번이 곧 실행으로 이어진다 |

## Options considered

* **A. 최대 도입**(AWS, Docker, claude-code-action까지 지금 도입): 자동화 이득은 크다. 하지만 소유권 정책, §16, 학습 예산과 정면으로 충돌하므로 기각한다.
* **B. 아무것도 도입하지 않음**: ADR-006의 "기계적 검증 공백"이 그대로 남는다. 반복된 상태 전이 결함 같은 유형을 계속 사람의 기억에 의존하게 되므로 기각한다.
* **C. 읽기 전용·로컬 우선 10개 선정(채택)**: 자동 검증 공백은 hooks, Dependabot, Semgrep으로 메우고, 쓰기·인프라 권한은 주지 않는다.

## Consequences

* 승인되면 Owner가 `docs/00-project/AI-TOOLING-SETUP-GUIDE.md`에 따라 단계적으로 설정한다(신규 `.claude/settings.json`, 필요 시 비밀값이 없는 `.mcp.json`, `.github/dependabot.yml`).
* `.gitignore`에 `.claude/settings.local.json`이 들어 있는지 확인해야 한다.
* README_AIUSAGE.md에 도구 도입 기록을 남긴다.
* 항목 5~10은 각각 §16 승인을 따로 받는다. 이 ADR이 Accepted가 되어도 그것만으로 일괄 승인되지는 않는다.

## Trade-offs

* hooks와 MCP를 추가하면 세션 시작이 느려지고 컨텍스트(툴 정의)를 더 소비한다. 그래서 MCP는 항목마다 `/mcp`에서 끄고 켤 수 있게 둔다.
* 읽기 전용 원칙 때문에 "AI가 PR을 만들고 머지까지" 하는 흐름은 의도적으로 포기한다.
* Semgrep MCP(beta)와 Postgres MCP 선정은 시점에 따라 바뀔 수 있다. 도입 직전에 재검증한다.

## Validation

* Claude Code의 `/mcp`에서 선택한 서버가 모두 ✔이고 쓰기 툴이 노출되지 않는지 확인한다(GitHub은 `create_*`/`merge_*` 툴이 없어야 한다).
* `.env`를 편집하려 하면 hook이 차단 메시지와 함께 거부하는지 확인한다.
* `git grep -nE "ghp_|github_pat_|Bearer [A-Za-z0-9]"` 결과가 0건인지 확인한다(비밀값 미커밋).
* `chamneul_ro` role로 `INSERT`를 시도하면 `permission denied`가 나는지 확인한다.

## Review Trigger

* Phase 3 착수(EKS, CI 도입) 시점에 항목 9와 10, AWS MCP, claude-code-action을 재평가한다.
* MCP 서버 관련 보안 공지가 나오면(예: 읽기 전용 우회) 해당 항목을 즉시 비활성화하고 재검토한다.

## 검증 출처 (접근일 2026-10-22)

* Claude Code MCP 문서: https://code.claude.com/docs/en/mcp (명령 문법, scope, `${VAR}` 확장, GitHub 예시 확인)
* Claude Code GitHub Actions: https://code.claude.com/docs/en/github-actions (`/install-github-app`, 필요 권한 확인)
* GitHub MCP Server: https://github.com/github/github-mcp-server , 원격 서버 문서 https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md (`/readonly` 경로, `X-MCP-Readonly`·`X-MCP-Toolsets` 헤더 확인)
* Context7: https://context7.com/docs/resources/all-clients
* Semgrep MCP: https://github.com/semgrep/mcp (README에 deprecated 명시, 기능은 `semgrep` 바이너리로 이동). 공식 문서 https://docs.semgrep.dev/mcp 는 이번 세션에서 HTTP 405로 열리지 않음 → 바이너리 내장 MCP의 정확한 명령은 **미검증**
* Playwright MCP: https://github.com/microsoft/playwright-mcp
* Sentry MCP: https://github.com/getsentry/sentry-mcp , https://mcp.sentry.dev (기본 읽기 전용은 미러 README로 확인)
* AWS EKS MCP 도구 설정: https://docs.aws.amazon.com/eks/latest/userguide/eks-mcp-tool-configurations.html
* Postgres MCP 읽기 전용 우회 논의: https://www.draxlr.com/blogs/mcp-server-read-only-tenant-aware-sql-access/ (Datadog 원문 **미검증**)
* Dependabot: https://docs.github.com/en/code-security/dependabot , push protection: https://docs.github.com/en/code-security/secret-scanning (이번 세션에서 재조회하지 않음. 일반 지식 기반이며 **재확인 권장**)
* CodeQL default setup: https://docs.github.com/en/code-security/code-scanning (위와 같음)
* Claude Code hooks: https://code.claude.com/docs/en/hooks (`matcher`, stdin JSON, exit 2 차단, `${CLAUDE_PROJECT_DIR}` 확인)
* crystaldba/postgres-mcp: https://github.com/crystaldba/postgres-mcp (`--access-mode=restricted`, COMMIT/ROLLBACK 파싱 차단 확인. 최근 커밋 날짜는 **미확인**)
* Dependabot uv 지원: https://docs.astral.sh/uv/guides/integration/dependency-bots/ (일부 사용 사례 미지원 — astral-sh/uv#2512)
