# VS Code 전환 플레이북

> Claude Code CLI + Claude App(Notion) → **VS Code + Claude Code Extension**
> 작성 2026-09-08 · 근거 `docs/adr/ADR-005-ai-native-spec-driven-migration.md`

---

## 먼저 알아야 할 것

**맥락은 이미 Git에 있다.** 문서 5,800줄 + ADR 5개 + 커밋 이력 전부가 저장소에 커밋되어 있고, Claude App 채팅에만 남은 결정은 없다. 그래서 이 전환은 "대화를 옮기는 일"이 아니다.

실제로 옮겨야 하는 것은 **딱 하나**뿐이다 → Step 0.

나머지는 저장소를 열기만 하면 따라온다.

**소요 시간**: Step 0~4까지 약 40분. Step 5부터가 실제 개발이다.

---

## Step 0 — 🔴 CLI 머신에서 먼저 백업 (유일한 손실 지점)

**VS Code를 열기 전에 한다.** 나중에 하면 늦는다.

`.gitignore:34`가 `.claude/agents/`를 제외하고 있어서, 학습용 서브에이전트 3종이 **저장소에 없고 기존 CLI 머신에만 있다.** 머신을 바꾸면 사라진다.

기존 CLI를 쓰던 머신의 터미널에서:

```bash
cd <기존 chamneul 경로>
ls -la .claude/agents/
# drill-master.md  chaos-coach.md  ops-reviewer.md 가 보여야 한다

# 저장소 밖 안전한 곳으로 복사
mkdir -p ~/chamneul-backup
cp -a .claude/agents ~/chamneul-backup/
ls -la ~/chamneul-backup/agents/
```

**이 3개가 안 보이면** 이미 없는 것이다. 그래도 진행에 지장은 없다 — `.claude/commands/` 4종이 같은 워크플로를 대체한다. `docs/learning/02` §7에 3종의 역할·호출법·제약이 문서화되어 있어 필요하면 재작성할 수 있다.

> 커밋 여부는 Phase 3에서 다시 정한다 (ADR-005 §10-2). 드릴·퀴즈가 Phase 3로 이월됐으므로 지금은 필요하지 않다.

**그 외에 CLI/Claude App에서 빼낼 것은 없다.** Owner 결정 Q1~Q22 / M1~M8 / D1~D6 / G1~G5는 전부 `docs/00-project/DECISION_ARCHIVE_2026-06.md`에 있다.

---

## Step 1 — VS Code + 확장 설치

1. VS Code 설치 — https://code.visualstudio.com
2. VS Code에서 저장소를 열면 (Step 2 이후) 오른쪽 아래에 **"권장 확장을 설치하시겠습니까?"** 알림이 뜬다. **설치**를 누른다. `.vscode/extensions.json`에 다음이 등록되어 있다.

| 확장 | 용도 |
| --- | --- |
| `anthropic.claude-code` | **Claude Code Extension** — 본체 |
| `charliermarsh.ruff` | 저장 시 포맷 + import 정렬 (프로젝트 린터와 동일 기준) |
| `ms-python.python` | 인터프리터 인식 |
| `batisteo.vscode-django` | Django 템플릿·모델 지원 |
| `ms-azuretools.vscode-docker` | 컨테이너 상태·로그 GUI |

알림이 안 뜨면: `Cmd+Shift+X` → 검색창에 `@recommended` 입력.

3. Claude Code Extension에 로그인한다. 사이드바 Claude 아이콘 → 계정 연결.

---

## Step 2 — 저장소 열기

```bash
# 새 머신이면 클론, 기존 머신이면 이 단계 생략
git clone https://github.com/danpro94/chamneul.git
cd chamneul

# 이번 전환 작업이 올라간 브랜치
git fetch origin
git checkout claude/chamneul-mvp-migration-ai-native-bixhdu

# 환경변수 파일 생성 (.env는 절대 커밋되지 않는다)
cp .env.example .env
```

`.env`를 열어 값을 채운다. `DJANGO_SECRET_KEY`는 아무 긴 랜덤 문자열이면 된다.

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(50))"
```

VS Code로 연다:

```bash
code .
```

### 인터프리터 확인

`Cmd+Shift+P` → `Python: Select Interpreter` → `./.venv/bin/python`이 선택돼 있는지 확인한다. 하단 상태바에도 표시된다.

> `.vscode/settings.json`은 macOS·Linux 기준(`.venv/bin/python`)이다. 이 한 줄이 조용히 깨지는 유일한 설정이다.

### [권장] CLAUDE.md 개정 고지 붙여넣기

`CLAUDE.md` §16 헌법 락은 **Claude의 편집을 금지**한다. Owner는 헌법의 저자이고 ADR-005가 승인 근거이므로 직접 붙여 넣는 것은 위반이 아니다.

`CLAUDE.md` **최상단**(첫 줄 `# CLAUDE.md` 바로 위)에 다음 6줄을 넣는다.

```markdown
> **개정 고지 (ADR-005, 2026-09-08)**
> §2 Source of Truth Order · §3 Project Tree · §17 First Workflow 는 ADR-005로 대체되었다.
> §13은 확장되었다. §16은 유효하며 대체되지 않았다.
> 그 외 전 조항(§0·§1·§4·§5·§6 도메인 규칙 전체·§7~§12·§14·§15)은 무수정 유효하다.
> 정본: docs/adr/ADR-005-ai-native-spec-driven-migration.md
```

**왜 권장인가**: SessionStart 훅은 Claude Code 세션만 커버한다. 이 블록은 사람 독자와 다른 AI 도구까지 커버하고, **훅이 안 뜰 때의 대비책**이 된다.

---

## Step 3 — 기동 확인

```bash
uv sync

docker compose up -d
docker compose ps
# db: healthy, app: running 이어야 한다
```

`db`가 `healthy`가 될 때까지 몇 초 걸린다. `starting`이면 기다린다.

```bash
curl -i http://localhost:8000/healthz
# HTTP/1.1 200 OK
```

마이그레이션 적용 — **Owner가 직접 한다** (`[소유]` 구역):

```bash
docker compose exec app python manage.py migrate
docker compose exec app python manage.py showmigrations
# accounts 0001,0002 / advisors 0001 / concerns 0001 / advice 0001 / notifications 0001 → 전부 [X]
```

관리자 계정 + Admin 확인:

```bash
docker compose exec app python manage.py createsuperuser
open http://localhost:8000/admin/
# 모델 11종이 보이면 성공
```

### 막혔을 때

| 증상 | 확인 |
| --- | --- |
| `port is already allocated` | 호스트 8000 또는 15432 선점. `lsof -i :8000` |
| `connection refused` (앱→DB) | `docker compose ps`로 db healthy 확인. `DB_HOST=db`인지 확인 |
| `password authentication failed` | `.env`의 `POSTGRES_PASSWORD`와 볼륨에 남은 초기 비밀번호 불일치 |
| `/admin` CSS 깨짐 | gunicorn 경로의 알려진 제약. dev 경로(`docker compose up`)에서는 정상 |

`docker compose down -v`는 **DB 볼륨을 삭제한다.** 데이터가 전부 사라지므로 실행 전 반드시 의도를 확인한다.

---

## Step 4 — 첫 Claude 세션 (온보딩 검증)

여기가 전환의 **판정 지점**이다.

### 4-1. 훅이 뜨는지 확인

Claude Code 패널을 열고 새 세션을 시작한다. 세션 시작 시 `.claude/rules/00-source-of-truth.md`의 내용이 주입된다.

`/hooks`를 입력해 `SessionStart` 항목이 보이는지 확인한다. `/permissions`에는 allow 34개·deny 14개가 보여야 한다.

**안 보이면**: `/hooks`를 한 번 열었다 닫으면 설정이 다시 읽힌다. 그래도 안 되면 VS Code를 재시작한다. 그래도 안 되면 Step 2의 CLAUDE.md 개정 고지 블록이 대비책이므로 반드시 붙여 넣는다.

### 4-2. 왕복 검증 — 이것만 통과하면 전환 성공

새 세션에 **이 한 줄만** 붙여넣는다.

```
이 프로젝트의 source of truth 순서가 뭐야? Notion을 봐야 해?
```

**성공**: ADR-005를 인용하고, Notion이 은퇴했으며 `docs/api.md`가 정본이라고 답한다.
**실패**: `CLAUDE.md` §2를 그대로 읊거나 "Notion export를 기다려야 한다"고 답한다 → 훅이 안 뜬 것이다. 4-1로 돌아간다.

### 4-3. 온보딩 보고 받기

```
/onboard
```

이 슬래시 명령이 읽기 순서를 정하고, 코드 수정 없이 7항목을 보고하게 한다.

1. 현재 프로젝트의 목적 2. 작업 중인 SPEC 3. 완료 조건 4. 관련 ADR 5. 현재 구현 상태 6. 충돌 사항 7. 다음 최소 작업 단위

**여기서 매 세션 거대 프롬프트를 붙여넣는 습관을 버린다.** 저장소가 컨텍스트 시스템이다.

### 4-4. 검증 배터리

```
/verify
```

`ruff` → `compose ps` → `manage.py check` → `makemigrations --check` → `test` → `curl /healthz`를 실행하고 **실제 출력과 함께** 통과/실패 표를 만든다.

지금은 테스트가 0건이므로 "판정 장치 부재"로 보고될 것이다. **그것이 정확한 현재 상태다.** SPEC-001 TASK-001이 이것을 해결한다.

---

## Step 5 — 반복 개발 루프

여기부터가 실제 개발이다. **하나의 SPEC = 하나의 브랜치 = 하나의 닫히는 루프.**

```
Gate 1 SPEC 확정 → Gate 2 계획 → Gate 3 실패 테스트 → Gate 4 구현 → Gate 5 리뷰 → Gate 6 종료
```

### Gate 1 — SPEC 확정 (아직 코딩하지 않는다)

SPEC-001은 이미 작성되어 있다. 새 SPEC이 필요하면:

```
/spec-new 002 google-oauth
```

이 명령은 **이전 SPEC의 `acceptance.md`에 미체크가 남아 있으면 거부한다.** 루프를 겹치지 않게 하는 장치다.

SPEC 내용을 검토할 때 붙여넣을 프롬프트:

```
specs/SPEC-001-local-session-auth/spec.md 를 읽고, 이 명세의 약점을 공격하라 (pre-mortem).

특히:
- Acceptance Criteria가 자동 테스트로 판정 가능한가? 애매한 항목을 지적하라
- 빠진 에러 케이스는 무엇인가
- 기존 ADR·api.md와 충돌하는 지점이 있는가
- 이 SPEC이 한 루프에 닫히기에 너무 큰가

아직 코드를 쓰지 마라. 지적만 하라.
```

### Gate 2 — 기술 계획

```
specs/SPEC-001-local-session-auth/plan.md 를 채워라.

- 어떤 파일이 새로 생기고 어떤 파일이 바뀌는가
- 요청이 어디를 거쳐 흐르는가 (미들웨어 → view → service → ORM)
- DB 변경이 필요한가 (없으면 없다고 명시)
- 기존 Architecture Decision과 충돌하는가

Dockerfile·docker-compose·.env는 건드리지 마라. Owner 소유 구역이다.
```

Owner가 trade-off를 검토하고 승인한다.

### Gate 3 — 실패하는 테스트 먼저 🔴

**이 게이트를 건너뛰지 않는다.** 이것이 이 시스템의 판정 장치다.

```
specs/SPEC-001-local-session-auth/acceptance.md 의 AC-001~AC-003을 테스트 코드로 옮겨라.

- docs/testing/TEST_CRITERIA.md 규칙을 따른다
- 구현은 아직 하지 마라. 테스트만 쓴다
- 작성 후 실행해서 실패하는 것을 보여줘라. 실패 출력을 그대로 붙여라
- 실패 이유가 "라우트가 없어서 404"인지 확인하라 (그것이 맞다)
```

**실패를 눈으로 본 뒤에** 구현에 들어간다. 실패를 확인하지 않은 테스트는 항상 통과하는 가짜일 수 있다.

### Gate 4 — TASK 단위 구현

한 번에 하나씩. `tasks.md`의 TASK 하나 = 커밋 하나.

```
specs/SPEC-001-local-session-auth/tasks.md 의 TASK-002를 구현하라.

규칙:
- 코드와 함께 "무엇을/왜"를 설명하라
- 최소 변경. 이 TASK가 요구하는 것만
- 끝나면 테스트를 실행하고 실제 출력을 보여줘라
- 통과하면 커밋 메시지 초안을 제시하라 (Spec:/Task: 트레일러 포함)
```

여러 TASK를 한꺼번에 시키지 않는다. 큰 패치는 리뷰가 불가능해진다 (CLAUDE.md §9).

### Gate 5 — 리뷰

```
방금 구현한 TASK-002를 리뷰하라. 내 편을 들지 마라.

- SPEC과 Acceptance Criteria를 충족했는가
- 기존 Architecture를 위반하지 않았는가
- 보안 문제 (.claude/rules/30-security.md 기준)
- 응답에 초과 노출된 필드가 있는가
- 불필요한 추상화나 과설계가 있는가
- 회귀 위험
```

`/verify`로 전체 배터리를 다시 돌린다.

### Gate 6 — 세션 종료

```
/handoff
```

이 명령은 **먼저 Owner에게 선요약 5줄을 요구하고 기다린다.** AI 요약을 먼저 보면 재인(recognition)이 인출(recall)을 대체해버려서 학습 장치가 무의미해진다.

Owner 5줄 → AI가 실제 구현과의 **차이(diff)**를 짚음 → 학습 부채 갱신 → `README_AIUSAGE.md` 항목 → `STATUS.md` 갱신.

---

## Step 6 — 세션 종료 체크리스트

떠나기 전에 이 4개를 확인한다. **다음 세션이 스스로 복원할 수 있는 상태**로 두는 것이 목적이다.

- [ ] `docs/00-project/STATUS.md`의 "다음 최소 작업 단위"가 실제 다음 작업을 가리키는가
- [ ] `acceptance.md`의 체크박스가 실제 상태와 맞는가 (통과한 테스트 경로가 적혀 있는가)
- [ ] 이번 세션에서 나온 **Owner 결정이 파일에 적혔는가** — 채팅에만 있으면 사라진다
- [ ] 커밋됐는가

```bash
git add -A
git commit    # Spec:/Task: 트레일러 포함
git push -u origin <branch>
```

---

## 부록 A — 하지 말 것

| 하지 말 것 | 왜 |
| --- | --- |
| **매 세션 거대 프롬프트 붙여넣기** | 저장소가 컨텍스트 시스템이다. `/onboard` 한 줄이면 된다 |
| **결정을 채팅에만 남기기** | 채팅은 저장소가 아니다. ADR / SPEC Open Questions / `README_AIUSAGE.md` 중 하나에 적는다 |
| **"완료했습니다"를 증거로 수용** | 증거는 통과한 테스트·실측 출력이다. 실행 안 한 명령은 "권장 명령"으로 표기하게 한다 |
| **Notion에 수기 동기화** | 폐지됐다 (ADR-005). `docs/api.md`가 정본이다 |
| **에러를 AI에게 "해결시키기"** | 대신 가설 검증 질문을 던진다. 반복 디버깅 의존은 이해도 저하 패턴이다 |
| **설명 못 하는 코드 merge** | CLAUDE.md §0 위반 |
| **큰 기능을 한 번에 시키기** | TASK 단위로 자른다. 리뷰 가능한 크기가 아니면 리뷰가 아니다 |
| **`docker compose down -v`를 무심코** | DB 볼륨이 사라진다. deny 목록에 넣어 뒀지만 터미널에서는 막지 못한다 |

## 부록 B — 슬래시 명령

| 명령 | 언제 |
| --- | --- |
| `/onboard` | 세션 시작. 7항목 보고, 코드 수정 없음 |
| `/verify` | 검증 배터리 + 실측 출력 표. 진단 전용, 고치지 않음 |
| `/spec-new <번호> <슬러그>` | 새 SPEC. 이전 SPEC 미완료 시 거부 |
| `/handoff` | 세션 종료. explain-first 순서 강제 |

## 부록 C — 무엇이 어디 있나

| 알고 싶은 것 | 파일 |
| --- | --- |
| 지금 어디까지 왔나 / 다음 작업 | `docs/00-project/STATUS.md` |
| 왜 이렇게 결정했나 | `docs/adr/` · `docs/00-project/DECISION_INDEX.md` |
| API 계약 43개 | `docs/api.md` |
| 데이터 모델 | `docs/model.md` |
| 용어 뜻 | `docs/00-project/GLOSSARY.md` |
| 언제 "완료"인가 | `docs/testing/TEST_CRITERIA.md` |
| 못 푼 것들 | `docs/00-project/LEARNING_DEBT.md` |
| 옛날 Owner 결정 (Q1~Q22 등) | `docs/00-project/DECISION_ARCHIVE_2026-06.md` |
| Owner/AI 역할 분담 | `docs/learning/02-ai-collaboration-and-ownership-strategy.md` |

## 부록 D — 전환이 성공했다는 판정

한 문장으로:

> **새 세션이 저장소만 열고도 목적·현재 상태·의사결정·완료조건·다음 작업을 스스로 복원할 수 있다.**

Step 4-2와 4-3이 그 판정이다. 복원하지 못하면 AI가 부족한 게 아니라 **`STATUS.md`나 훅이 부족한 것**이다. 그 문서를 고친다.
