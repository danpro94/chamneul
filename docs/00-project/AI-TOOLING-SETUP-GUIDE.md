# AI 도구 설정 가이드 (ADR-009 실행 절차)

> 상태: **ADR-009가 Proposed인 동안에는 참고용이다.** Owner가 ADR-009를 승인하고, §16 승인이 필요한 항목(5~10)을 개별 승인한 뒤에만 이 절차를 실행한다.
> 환경: macOS + Chrome + VS Code(Claude Code 확장) + 터미널(zsh). 작성일 2026-10-22.
> 표기: **[미검증]** = 이번 조사에서 공식 문서로 확인하지 못한 내용. 실행 전에 해당 출처를 다시 확인한다.

---

## 0. 공통 준비 (한 번만)

### 0.1 도구 확인

```bash
claude --version          # Claude Code CLI. VS Code 확장도 같은 설정과 MCP 구성을 쓴다
jq --version              # hook 스크립트용. 없으면 brew install jq
node --version            # Playwright MCP용. 20 이상을 권장한다
uv --version              # 이 프로젝트의 파이썬 패키지 관리자
docker compose ps         # db, app 서비스가 떠 있는지 확인
```

### 0.2 MCP 설정이 저장되는 곳 (scope)

| scope | 저장 위치 | 공유 여부 | 이 프로젝트의 용도 |
| --- | --- | --- | --- |
| `local`(기본값) | `~/.claude.json`(이 프로젝트 항목) | 나만, 이 프로젝트에서만 | 비밀값이 평문으로 들어가는 서버(Postgres, Semgrep 토큰 등) |
| `project` | 저장소 루트의 `.mcp.json`(커밋됨) | 저장소를 받는 모두 | **비밀값이 없는** 서버, 또는 `${VAR}`로 환경변수만 참조하는 서버 |
| `user` | `~/.claude.json`(전역) | 나만, 모든 프로젝트 | 이 프로젝트에서는 쓰지 않는다 |

* `.mcp.json`은 `${VAR}`, `${VAR:-default}` 확장을 지원한다(`command`, `args`, `env`, `url`, `headers`). 그래서 **토큰은 환경변수에 두고, 파일에는 변수 이름만 쓴다.**
* `claude mcp add`의 인자를 **작은따옴표**로 감싸야 셸이 `${VAR}`를 먼저 펼치지 않는다. 큰따옴표를 쓰면 토큰 평문이 파일에 기록된다.
* project scope 서버는 처음 쓸 때 Claude Code가 승인 여부를 묻는다.

### 0.3 비밀값 보관: macOS 키체인 → 환경변수

토큰은 키체인에 넣고, 셸이 시작될 때 환경변수로 꺼내 쓴다. 파일에 평문 토큰을 남기지 않는다.

```bash
# 저장 (-w 뒤 값을 비워 두면 프롬프트로 입력받으므로 셸 히스토리에 남지 않는다)
security add-generic-password -a "$USER" -s chamneul-github-mcp -w
security add-generic-password -a "$USER" -s chamneul-context7 -w

# ~/.zshrc 에 추가 (값이 아니라 꺼내는 명령을 적는다)
export GITHUB_MCP_PAT="$(security find-generic-password -a "$USER" -s chamneul-github-mcp -w 2>/dev/null)"
export CONTEXT7_API_KEY="$(security find-generic-password -a "$USER" -s chamneul-context7 -w 2>/dev/null)"
```

* 적용: `source ~/.zshrc`. 확인할 때는 값이 화면에 찍히지 않도록 `[ -n "$GITHUB_MCP_PAT" ] && echo set`만 쓴다.
* **VS Code 주의**: Dock에서 띄운 VS Code가 `~/.zshrc` 환경변수를 상속하는지는 상황에 따라 다르다 **[미검증]**. 가장 확실한 방법은 터미널에서 `cd ~/projects/personal/chamneul && code .`로 여는 것이다. `/mcp`에서 변수 미설정 경고가 보이면 이 문제다.
* 이름을 정할 때 `ANTHROPIC_API_KEY`처럼 Anthropic 자격증명과 같은 이름을 쓰지 않는다. 원격 서버의 `url`/`headers`에서는 이런 변수가 일부러 빈 값으로 읽힌다.

### 0.4 커밋 전 안전망

```bash
git check-ignore -v .claude/settings.local.json   # .gitignore 37행에서 무시되는지 확인
git grep -nE "ghp_|github_pat_|ctx7sk|Bearer [A-Za-z0-9]{20,}" -- . ':!docs' || echo "no secrets"
```

---

## 1. Claude Code hooks: ruff 자동 실행 + 소유권 파일 편집 차단 (now)

**목적**: CLAUDE.md §17-4(ruff·check 결과 확인)와 §17-5(Dockerfile/compose/.env는 손대지 않음)를 AI의 기억이 아니라 하네스가 강제하게 만든다.

### 1.1 설정 (Owner가 직접 작성한다. 아래는 참고 예시)

`.claude/hooks/guard-owner-files.sh`:

```bash
#!/bin/bash
# PreToolUse: Owner 소유 파일과 비밀값 파일은 AI가 편집하지 못하게 막는다.
file=$(jq -r '.tool_input.file_path // empty')
case "$file" in
  */.env|*/.env.*|*/Dockerfile|*/docker-compose*.yml|*/.dockerignore|*/k8s/*|*.tf|*/CLAUDE.md)
    echo "Blocked: $file 는 Owner 소유 파일입니다(ADR-009, CLAUDE.md §16·§17-5). 변경 제안만 텍스트로 하세요." >&2
    exit 2 ;;
esac
exit 0
```

`.claude/hooks/ruff-on-edit.sh`:

```bash
#!/bin/bash
# PostToolUse: 방금 수정한 .py 파일을 ruff로 검사하고, 실패하면 결과를 Claude에게 돌려준다.
file=$(jq -r '.tool_input.file_path // empty')
[[ "$file" == *.py ]] || exit 0
cd "$CLAUDE_PROJECT_DIR" || exit 0
out=$(uv run ruff check "$file" 2>&1) || { echo "$out" >&2; exit 2; }
exit 0
```

`.claude/settings.json`(커밋 대상. 비밀값이 없다):

```json
{
  "permissions": {
    "deny": ["Read(./.env)", "Read(./.env.*)"]
  },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/guard-owner-files.sh", "args": [] }] }
    ],
    "PostToolUse": [
      { "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/ruff-on-edit.sh", "args": [] }] }
    ]
  }
}
```

```bash
chmod +x .claude/hooks/*.sh
```

* **exit 2만 차단한다.** exit 1은 경고만 남기고 그대로 진행되므로 흔히 하는 실수다.
* `PostToolUse`의 exit 2는 편집을 되돌리지 않는다. 오류를 Claude에게 보여 줘 스스로 고치게 할 뿐이다.
* **Owner가 특정 소유 파일 수정을 AI에게 명시적으로 승인한 경우**(예: 과거 compose healthcheck 추가)에도 이 hook은 막는다. 그때는 Owner가 직접 편집하거나, 그 작업 동안만 `.claude/settings.json`의 해당 hook을 잠시 빼고 끝나면 되돌린다 — 되돌렸는지 `/hooks`로 확인한다.
* `Read(./.env)` deny 규칙의 문법은 Claude Code settings 문서 기준이다. `.env.example`까지 막히는지는 실행하며 확인한다 **[미검증: glob 매칭 세부]**.
* 전체 테스트(`uv run python manage.py test --settings=config.settings.test` — 이 프로젝트의 표준 실행법, 호스트에서 테스트 설정으로)를 `Stop` hook에 거는 방법도 있다. 다만 느리고, 실패 시 반복 루프가 생길 수 있어 **처음에는 넣지 않는다.** 테스트는 §17 흐름대로 명시적으로 돌린다.

### 1.2 검증

* Claude Code에서 `/hooks`를 실행하면 등록된 hook 2개가 보여야 한다.
* "docker-compose.yml에 주석 한 줄 추가해 줘"라고 요청 → `Blocked: ... Owner 소유 파일입니다`가 나오고 파일은 그대로여야 한다.
* 일부러 import 하나를 미사용으로 남기는 수정을 요청 → ruff 오류가 Claude에게 전달되고 Claude가 고쳐야 한다.

### 1.3 롤백

`.claude/settings.json`에서 `hooks` 블록을 지운다(또는 파일을 삭제한다). 세션 재시작 후 `/hooks`에서 사라졌는지 확인한다.

---

## 2. `/security-review` · `/code-review` + 프로젝트 서브에이전트 (now)

**설정 없음.** 내장 명령과 `.claude/agents/` 8종은 이미 사용할 수 있다.

### 일상 사용 예시 (chamneul 맥락)

```text
/security-review
→ 현재 브랜치(feat/spec-005-api-gaps)의 diff를 보안 관점으로 리뷰

/code-review high
→ 정확성 버그 위주 리뷰. --fix 는 쓰지 않는다(Owner가 이해한 뒤 직접 반영)

security-reviewer 에이전트로 accounts/ 의 비밀번호 재설정(#45·#46) 변경을 리뷰해 줘.
계정 존재 여부 노출(§10)과 토큰 재사용 가능성을 중점으로.

data-modeler 에이전트로 concerns 수정(#47)이 SUBMITTED 외 상태에서 409를 내는지,
select_for_update + update_fields 규칙(coding.md)을 지키는지 확인해 줘.

ops-reviewer 로 내가 손으로 쓴 docker-compose.yml 을 리뷰해 줘. 재작성 말고 코멘트만.
```

* 결과는 `docs/reviews/`에 남긴다(§14). **AI 리뷰는 두 번째 리뷰어이지 머지 게이트가 아니다.**
* 롤백: 해당 없음(쓰지 않으면 된다).

---

## 3. GitHub 공식 MCP 서버, 읽기 전용 (now)

### 3.1 토큰 발급 (Chrome)

1. github.com 로그인 → 오른쪽 위 아바타 → **Settings**
2. 왼쪽 맨 아래 **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
3. Token name: `chamneul-claude-mcp-ro`, Expiration: **90일 이하**, Resource owner: `danpro94`
4. Repository access: **Only select repositories** → `danpro94/chamneul`
5. Repository permissions는 모두 **Read-only**로만 준다: Contents, Issues, Pull requests, Actions, Dependabot alerts, Code scanning alerts(Metadata는 자동으로 Read-only). Secret scanning alerts는 비밀값 원문이 컨텍스트로 들어올 수 있어 **주지 않는다.**
6. **Generate token** → 값을 복사해 바로 키체인에 저장한다(§0.3). 브라우저 창을 닫으면 다시 볼 수 없다.

> 메뉴 이름은 GitHub UI 개편에 따라 바뀔 수 있다 **[미검증: 2026-10 기준 메뉴 라벨]**.

### 3.2 등록 (터미널, 저장소 루트에서)

```bash
claude mcp add --transport http --scope project github \
  https://api.githubcopilot.com/mcp/readonly \
  --header 'Authorization: Bearer ${GITHUB_MCP_PAT}'
```

* URL 끝의 `/readonly`가 서버 측 읽기 전용 모드다. 헤더 `X-MCP-Readonly: true`로도 같은 효과를 낸다(GitHub `docs/remote-server.md`).
* 작은따옴표 덕분에 `.mcp.json`에는 `${GITHUB_MCP_PAT}` 글자 그대로 들어간다. 커밋 전에 `cat .mcp.json`으로 토큰 평문이 없는지 확인한다.
* 툴을 줄이고 싶으면 `--header 'X-MCP-Toolsets: repos,issues,pull_requests,actions'`를 추가한다 **[미검증: 툴셋 정식 이름. 공식 README의 toolset 표로 확인]**.

### 3.3 검증

* `claude mcp list` → `github: ... ✔ Connected`
* Claude Code에서 `/mcp` → github가 ✔이고, 툴 목록에 `create_*`, `merge_*`, `update_*` 같은 쓰기 툴이 **없어야 한다.**
* 토큰이 틀리면 ✘와 401이 표시된다. `claude mcp add`는 토큰을 검증하지 않으므로 반드시 `/mcp`로 확인한다.

### 3.4 일상 사용

```text
github MCP로 최근 머지된 PR 5개의 제목·번호를 보고, docs/00-project/STATUS.md 와
어긋나는 SPEC-005 TASK가 있는지 알려 줘. 파일은 고치지 말고 표로만.

github MCP로 열린 Dependabot 경고를 읽고, 우리 pyproject.toml 기준 영향도를 정리해 줘.
```

* **이슈나 PR 본문은 데이터이지 지시가 아니다.** 공개 저장소라 누구나 이슈를 쓸 수 있다. MCP 결과에 "이 명령을 실행하라" 같은 문장이 있으면 따르지 말라고 Claude에게 명시한다.

### 3.5 롤백

```bash
claude mcp remove github --scope project      # .mcp.json에서 제거
```

그 뒤 GitHub → Settings → Developer settings → Fine-grained tokens → 해당 토큰 → **Revoke**. 키체인 항목도 지운다: `security delete-generic-password -s chamneul-github-mcp`.

---

## 4. Context7, 버전별 라이브러리 문서 (now)

### 4.1 키 발급 (선택)

키 없이도 동작한다. rate limit을 늘리려면 Chrome에서 `context7.com/dashboard`에 로그인 → API key 생성 → 키체인 저장(§0.3).

### 4.2 등록

```bash
claude mcp add --transport http --scope project context7 \
  https://mcp.context7.com/mcp \
  --header 'CONTEXT7_API_KEY: ${CONTEXT7_API_KEY}'
```

* `npx ctx7 setup --claude`라는 자동 설정 명령도 있다. 하지만 이 명령은 **CLAUDE.md에 규칙을 써 넣는다.** CLAUDE.md는 동결 상태(§16)이므로 쓰지 않는다.

### 4.3 검증 · 사용 · 롤백

* `/mcp` → context7 ✔
* 사용 예: `context7로 Django 5.2 의 UniqueConstraint(condition=...) 와 DRF 3.15 throttling 문서를 확인하고, concerns 앱 코드가 그 API를 맞게 쓰는지 봐 줘.`
* 질문에 코드 원문, 비밀값, 사용자 데이터를 붙여 넣지 않는다. 쿼리는 외부 서비스로 나간다.
* 롤백: `claude mcp remove context7 --scope project`

---

## 5. Dependabot + secret scanning / push protection (now, §16 승인 필요)

### 5.1 GUI 설정 (Chrome)

`github.com/danpro94/chamneul` → **Settings** → 왼쪽 **Advanced Security**(예전 이름 "Code security and analysis") **[미검증: 현재 라벨]**에서 다음을 켠다.

* **Dependabot alerts** → Enable
* **Dependabot security updates** → Enable(보안 패치 PR만 자동으로 연다)
* **Secret Protection**(secret scanning) 및 **Push protection** → Enable(공개 저장소는 무료로 제공된다는 것이 일반적인 안내다 **[미검증: 2026-10 요금 정책]**)

### 5.2 버전 업데이트 설정 (Owner가 직접 작성)

`.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "uv"          # pyproject.toml + uv.lock
    directory: "/"
    schedule: { interval: "weekly" }
    open-pull-requests-limit: 3
  - package-ecosystem: "docker"      # Dockerfile 베이스 이미지
    directory: "/"
    schedule: { interval: "weekly" }
    open-pull-requests-limit: 2
  # Phase 3에서 .github/workflows/ 가 생기면 github-actions 생태계를 추가한다
```

* Dependabot의 uv 지원은 2025년에 시작됐고, 일부 사용 사례는 아직 지원되지 않는다(astral-sh/uv#2512).
* **자동 머지는 설정하지 않는다.** Dockerfile 관련 PR은 Owner가 내용을 읽고 직접 반영한다(소유권 정책).

### 5.3 검증 · 사용 · 롤백

* 검증: Insights → Dependency graph → **Dependabot** 탭에 마지막 체크 시각이 보이면 된다. push protection은 테스트용 가짜 토큰 형식 커밋으로 확인할 수 있지만, **실제 토큰으로는 절대 시험하지 않는다.**
* 사용: `github MCP로 Dependabot PR #N 의 changelog 요약하고, uv.lock 변경이 Django/psycopg 메이저 버전을 건드리는지 알려 줘.`
* 롤백: 같은 Settings 화면에서 Disable, `.github/dependabot.yml` 삭제(파일 삭제는 §16 승인 사항이다).

---

## 6. Semgrep MCP, 로컬 SAST (now, §16 승인 필요)

> 현황: 독립 저장소 `semgrep/mcp`는 **deprecated(아카이브)**이고, 기능은 공식 `semgrep` 바이너리로 옮겨졌다. 바이너리 내장 MCP의 정확한 명령은 이번 조사에서 확인하지 못했다 **[미검증]**.

### 6.1 설치 및 확인

```bash
brew install semgrep
semgrep --version
semgrep mcp --help          # [미검증] 이 하위 명령이 존재하는지 먼저 확인
```

### 6.2 등록 (6.1에서 하위 명령이 확인된 경우에만)

```bash
claude mcp add --scope local --transport stdio semgrep -- semgrep mcp     # [미검증]
```

* 아카이브된 `uvx semgrep-mcp`는 쓰지 않는다(업데이트되지 않는다).
* 처음에는 `SEMGREP_APP_TOKEN` 없이(로그인 없이) 쓴다. 토큰은 Semgrep 클라우드 findings를 조회할 때만 필요하다.
* **MCP 없이도 같은 효과를 낼 수 있다.** 터미널에서 `semgrep scan --config p/django --config p/python --error`를 직접 돌리면 된다. MCP 등록이 막히면 이 방법을 쓴다.

### 6.3 검증 · 사용 · 롤백

* `/mcp` → semgrep ✔, 툴 목록에 scan 계열 툴이 보여야 한다.
* 사용 예: `semgrep MCP로 accounts/ 와 concerns/ 를 스캔하고, 결과 중 security-reviewer 관점에서 실제로 위험한 것만 추려 줘. 오탐은 사유와 함께 분리해.`
* 롤백: `claude mcp remove semgrep`, 필요하면 `brew uninstall semgrep`

---

## 7. PostgreSQL 읽기 전용 MCP, 로컬 compose DB 전용 (now·선택, §16 승인 필요)

> **절대 규칙**: 접속 대상은 `localhost:15432`(compose `db` 서비스)뿐이다. dev/prod(RDS) 연결 문자열은 이 도구에 절대 넣지 않는다. 서버의 "restricted" 플래그는 보조 수단일 뿐이고, **진짜 경계는 DB role 권한**이다.

### 7.1 SELECT 전용 role 만들기 (Owner가 직접 입력)

```bash
docker compose exec db psql -U chamneul -d chamneul
```

```sql
CREATE ROLE chamneul_ro LOGIN PASSWORD '로컬전용-임의값';
GRANT CONNECT ON DATABASE chamneul TO chamneul_ro;
GRANT USAGE ON SCHEMA public TO chamneul_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chamneul_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE chamneul IN SCHEMA public GRANT SELECT ON TABLES TO chamneul_ro;
ALTER ROLE chamneul_ro SET default_transaction_read_only = on;
-- 민감 테이블 제외: 세션 키와 비밀번호 해시
REVOKE SELECT ON django_session FROM chamneul_ro;
-- \dt 로 사용자 테이블 이름을 확인한 뒤, password 컬럼을 뺀 컬럼 단위 GRANT로 바꾼다
```

* `docker compose down -v`로 볼륨을 지우면 role도 사라진다. 그때마다 다시 만든다.
* 검증: `psql`에서 `SET ROLE chamneul_ro; INSERT INTO django_migrations(app,name,applied) VALUES ('x','x',now());` → `permission denied`가 나와야 한다. 확인 후 `RESET ROLE;`

### 7.2 등록

```bash
claude mcp add --scope local \
  -e DATABASE_URI='postgresql://chamneul_ro:로컬전용-임의값@localhost:15432/chamneul' \
  --transport stdio postgres-ro -- uvx postgres-mcp==<고정버전> --access-mode=restricted
```

* 후보 서버는 crystaldba/postgres-mcp다. restricted 모드는 read-only 트랜잭션을 쓰고 `COMMIT`/`ROLLBACK`이 들어간 문장을 파싱 단계에서 거부한다. `<고정버전>`은 PyPI에서 확인한 버전으로 고정한다.
* `-e` 바로 뒤에 서버 이름이 오면 CLI가 이름을 env 쌍으로 잘못 읽는다. 그래서 `--transport stdio`를 사이에 둔다(공식 문서의 주의 사항).
* 이 비밀번호는 `~/.claude.json`에 평문으로 저장된다. local scope(커밋 안 됨)이고 로컬 전용 DB라서 허용하는 것이다.

### 7.3 사용 · 롤백

* 사용 예: `postgres-ro로 concerns 테이블의 partial unique index 정의와 deleted_at 이 채워진 행 수를 보여 줘. 결과를 docs/model.md §soft delete 설명과 대조해 줘.`
* 롤백: `claude mcp remove postgres-ro`, 그 뒤 psql에서 `DROP OWNED BY chamneul_ro; DROP ROLE chamneul_ro;`

---

## 8. Playwright MCP, 로컬 UI 스모크 (now·선택, §16 승인 필요)

```bash
npm view @playwright/mcp version                  # 현재 버전 확인 후 아래에 고정
claude mcp add --scope local --transport stdio playwright -- npx -y @playwright/mcp@<고정버전>
npx -y @playwright/mcp@<고정버전> --help           # --isolated, --allowed-origins 등 옵션 확인 [미검증: 옵션명]
```

* 검증: `/mcp` → playwright ✔. 처음 쓸 때는 "playwright mcp로"라고 명시해야 Bash로 우회하지 않는다.
* 사용 예: `playwright mcp로 http://localhost:8000/admin 에 접속해 로그인 화면이 뜨는지, GET /api/v1/csrf 응답 뒤 csrftoken 쿠키가 생기는지 확인해 줘. localhost 외 사이트는 열지 마.`
* 개인 Chrome 프로필(쿠키·로그인 세션)을 연결하지 않는다.
* 롤백: `claude mcp remove playwright`

---

## 9. CodeQL default setup (Phase 3, CI/CD 승인과 함께)

Phase 3에서 CI를 도입할 때 진행한다. 저장소 Settings → Advanced Security → **Code scanning** → CodeQL analysis → **Set up** → **Default** → 언어 Python 확인 → Enable. 처음에는 경고만 내게 두고, 머지 차단(branch protection 연동)은 결과가 안정된 뒤에 결정한다. 결과는 3번 GitHub MCP(Code scanning alerts 읽기 권한)로 조회한다.
롤백: 같은 화면에서 Disable CodeQL.

---

## 10. Sentry MCP (Phase 3, 배포 후)

전제: 앱에 sentry-sdk가 들어가 있어야 하고(§16 승인), `send_default_pii=False`와 요청 본문 스크러빙(고민 원문은 민감 정보다)이 **먼저** 설정되어 있어야 한다.

```bash
claude mcp add --transport http --scope local sentry https://mcp.sentry.dev/mcp   # [미검증: 경로 /mcp]
```

* `/mcp` → sentry 선택 → **Authenticate** → Chrome에서 Sentry OAuth 승인. 기본은 읽기 전용 scope이므로 추가 scope는 주지 않는다.
* 사용 예: `sentry MCP로 지난 24시간 상위 오류 3개를 보고, 원인 코드와 그걸 재현할 실패 테스트(acceptance AC 형식) 초안을 제안해 줘. 코드는 아직 고치지 마.`
* 롤백: `claude mcp remove sentry`(저장된 OAuth 토큰도 함께 삭제된다). Sentry 조직 설정에서도 인증된 앱을 해제한다.

---

## 11. 하루 작업 흐름 예시 (§17 TDD 루프와 연결)

1. 세션 시작: `/mcp`로 연결 상태를 확인한다. 쓰지 않을 서버는 `/mcp`에서 끈다(컨텍스트 절약).
2. 맥락 복원: "CLAUDE.md → README → STATUS.md를 읽고 Active SPEC 보고(§17-3)". GitHub MCP로 최근 PR과 경고를 함께 본다.
3. 구현: AC 실패 테스트 → 최소 구현. hooks가 ruff를 자동으로 돌리고 소유권 파일 편집을 막는다. 라이브러리 API는 Context7로 확인한다.
4. 검증: `uv run python manage.py test --settings=config.settings.test`, `makemigrations --check` 결과를 직접 본다. 필요하면 postgres-ro로 DB 상태를 확인한다.
5. 리뷰: `/security-review` → 도메인 서브에이전트(security-reviewer, data-modeler) → Semgrep 스캔 → `docs/reviews/`에 기록.
6. 마무리: 커밋(SPEC/TASK id), STATUS.md, README_AIUSAGE.md 갱신. Owner 확인 전에는 다음 TASK로 넘어가지 않는다.

## 12. 전체 롤백 (한 번에 원상 복구)

```bash
claude mcp list                                   # 등록된 서버 확인
claude mcp remove github --scope project
claude mcp remove context7 --scope project
claude mcp remove semgrep ; claude mcp remove postgres-ro ; claude mcp remove playwright ; claude mcp remove sentry
git status                                        # .mcp.json / .claude/settings.json 변경 확인 후 되돌리기
```

토큰 폐기(GitHub fine-grained PAT Revoke, Context7 키 삭제)와 키체인 항목 삭제(`security delete-generic-password -s <이름>`)까지 마쳐야 롤백이 끝난다.

---

## 13. 프로 팁 / 현업 관행

출처가 있는 것만 적었다. 출처를 찾지 못한 일반론은 **[관행·미검증]**으로 표시했다.

1. **PR은 작게, 하나의 목적만 담는다.** 리뷰 품질은 변경 크기에 반비례한다. 이 프로젝트의 "SPEC TASK 1개 = 커밋 1개" 규칙(§17-4)이 바로 이것이다. (Google Engineering Practices, "Small CLs")
2. **AI 리뷰는 두 번째 리뷰어이지 게이트가 아니다.** AI 도구가 숙련 개발자를 오히려 느리게 만든 연구 결과가 있다. 이해와 최종 승인은 사람이 한다. 이 프로젝트의 drill-master/WB 장치가 이를 보완한다. (METR 2025 RCT. 이 프로젝트 `docs/learning/02`에서도 근거로 인용)
3. **결정적 검사는 hooks/CI에, 판단은 LLM에 맡긴다.** 포매터, 린터, 테스트처럼 매번 반드시 돌아야 하는 것은 프롬프트("ruff 돌려줘")가 아니라 hooks로 강제한다. (Claude Code hooks 문서, Anthropic "Claude Code best practices")
4. **CLAUDE.md는 짧고 사실만 담게 유지한다(hygiene).** 자주 바뀌는 세부 규칙은 하위 파일로 분리한다. 이 프로젝트는 ADR-006으로 이미 실천하고 있다. 자동 설정 도구가 CLAUDE.md에 규칙을 써 넣게 두지 않는다(§4.2의 ctx7 setup 사례). (Anthropic "Claude Code best practices")
5. **컨텍스트를 관리한다.** 작업 단위가 바뀌면 `/clear`, 긴 세션은 `/compact`를 쓴다. 넓은 탐색은 서브에이전트에 맡겨 메인 컨텍스트를 아낀다. MCP 툴 정의도 컨텍스트를 차지하므로 쓰지 않는 서버는 `/mcp`에서 끈다. (Anthropic "Claude Code best practices", Claude Code MCP 문서)
6. **쓰기 툴은 절대 자동 승인하지 않는다.** 프롬프트 인젝션은 LLM 앱의 1순위 위험이고, MCP는 외부 텍스트(이슈, 웹페이지, DB 행)를 컨텍스트로 끌어오는 경로다. 읽기 전용 + 최소 권한 토큰 + 사람 승인의 3중 방어를 쓴다. `--dangerously-skip-permissions`는 쓰지 않는다. (OWASP Top 10 for LLM Applications, LLM01 Prompt Injection, MCP Security Best Practices)
7. **"읽기 전용"은 서버 플래그가 아니라 자격증명 권한으로 보장한다.** Postgres MCP의 read-only 트랜잭션 우회 사례가 대표적이다. GitHub도 PAT 자체를 Read-only로 발급한다. (draxlr 블로그. 인용된 Datadog 원문 **[미검증]**)
8. **버전을 고정한다.** `npx ...@latest`와 `uvx` 무버전 실행은 공급망 위험이자 "어제는 됐는데" 장애의 원인이다. MCP 서버도 의존성으로 취급해 버전을 고정하고, 갱신은 Dependabot처럼 의도적으로 한다. (Playwright MCP 사용 가이드의 버전 고정 권고, uv/Dependabot 문서)
9. **비밀값은 코드 밖, 그리고 커밋 전에 기계로 막는다.** 키체인과 환경변수로 보관하고, `.mcp.json`에는 `${VAR}`만 쓴다. push protection으로 마지막 방어선을 둔다. (Claude Code MCP 문서의 env 확장, GitHub secret scanning 문서)
10. **한국 맥락: 개인정보를 외부 AI로 보내는 일에 주의한다.** chamneul의 고민 원문은 민감한 개인 데이터다. 외부 MCP(Context7, Sentry, 원격 GitHub)에 실제 사용자 데이터를 붙여 넣지 않는 것을 팀 규칙으로 둔다. 개인정보보호법(PIPA)상 국외 이전이나 처리 위탁 논점이 생길 수 있다 **[관행·미검증: 구체 조항 해석은 법무 확인 필요]**.
11. **실리콘밸리·한국 공통 관행으로 자주 언급되는 것들 [관행·미검증: 정량 출처 없음]**: AI가 만든 PR에 "AI-assisted" 표기(이 프로젝트는 `Co-Authored-By`와 README_AIUSAGE.md로 실천), 사람이 설명할 수 없는 코드는 머지하지 않기, 도입한 AI 도구 목록을 ADR로 관리하고 분기마다 재검토하기.

---

## 검증 출처 (접근일 2026-10-22)

* Claude Code MCP: https://code.claude.com/docs/en/mcp — `claude mcp add/remove/list`, scope 3종, `--` 구분자, `-e` 주의 사항, `${VAR}` 확장, GitHub 예시, `/mcp` 확인
* Claude Code hooks: https://code.claude.com/docs/en/hooks — `matcher: "Edit|Write"`, stdin JSON(`tool_input.file_path`), exit 2 차단, `${CLAUDE_PROJECT_DIR}`, `args: []`
* Claude Code GitHub Actions: https://code.claude.com/docs/en/github-actions — `/install-github-app`, 쓰기 권한 요구(ADR-009에서 미도입 근거)
* GitHub MCP 원격 서버: https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md — `/readonly`, `X-MCP-Readonly`, `X-MCP-Toolsets`
* GitHub MCP 서버 저장소: https://github.com/github/github-mcp-server
* Context7: https://context7.com/docs/resources/all-clients — 원격 HTTP URL, `CONTEXT7_API_KEY` 헤더, `npx ctx7 setup --claude`
* Semgrep MCP(아카이브): https://github.com/semgrep/mcp — deprecated 공지. 공식 문서 https://docs.semgrep.dev/mcp 는 HTTP 405로 열리지 않음 **[미검증]**
* crystaldba/postgres-mcp: https://github.com/crystaldba/postgres-mcp — restricted 모드, `DATABASE_URI`
* Postgres MCP 읽기 전용 우회 논의: https://www.draxlr.com/blogs/mcp-server-read-only-tenant-aware-sql-access/
* Playwright MCP: https://github.com/microsoft/playwright-mcp , 사용 사례 https://til.simonwillison.net/claude-code/playwright-mcp-claude-code
* Sentry MCP: https://github.com/getsentry/sentry-mcp — 원격 서비스 권장, 기본 읽기 전용(미러 README로 확인)
* AWS EKS MCP(Phase 3 재검토용): https://docs.aws.amazon.com/eks/latest/userguide/eks-mcp-tool-configurations.html
* Dependabot uv 지원: https://docs.astral.sh/uv/guides/integration/dependency-bots/
* Dependabot / secret scanning / code scanning: https://docs.github.com/en/code-security — 메뉴 라벨과 요금 정책은 이번 세션에서 재조회하지 않음 **[미검증]**
* Anthropic, Claude Code best practices: https://www.anthropic.com/engineering/claude-code-best-practices — 이번 세션에서 재조회하지 않음 **[재확인 권장]**
* Google Engineering Practices, Small CLs: https://google.github.io/eng-practices/review/developer/small-cls.html — 재조회하지 않음 **[재확인 권장]**
* METR 2025 RCT: https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ — 재조회하지 않음 **[재확인 권장]**
* OWASP LLM01 Prompt Injection: https://genai.owasp.org/llmrisk/llm01-prompt-injection/ — 재조회하지 않음 **[재확인 권장]**
* MCP Security Best Practices: https://modelcontextprotocol.io/specification/draft/basic/security_best_practices — 재조회하지 않음 **[재확인 권장: 경로]**
