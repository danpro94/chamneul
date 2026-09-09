# VS Code Claude Code Extension 마이그레이션 플레이북 + AI-Native 스켈레톤 전환

> 작성: 2026-09-09 · 성격: 실행 플레이북 (Owner 실행용) · 상태: 초안, ADR-006 승인 전
> 배경: Claude Code CLI + Claude App(웹)으로 진행하던 개발을 VS Code Claude Code Extension으로 옮기고,
> Notion 수기 문서화를 폐기한 뒤 Git Repository를 단일 Source of Truth로 전환한다.
> 근거/제약: CLAUDE.md §16 Constitutional lock (CLAUDE.md 동결 — 개정은 새 ADR로만).

---

## 0. 전환 시점의 프로젝트 현황 (2026-09-09 실측)

| 항목 | 값 |
| --- | --- |
| 리포지토리 | `danpro94/chamneul` (public), `main` + `feat/m4-api` (둘 다 push 완료) |
| 스택 | Python 3.13 / Django 5.2 / DRF 3.15 / PostgreSQL 16 (compose) / gunicorn / uv / ruff |
| 테스트 러너 | Django 기본 (pytest 미도입 — CLAUDE.md §12) |
| Phase | Phase 2 — 로컬 컨테이너 MVP |

### 마일스톤

| MS | 내용 | 상태 |
| --- | --- | --- |
| M1 | 스켈레톤 (config/accounts/common, custom User+uuid7, /healthz, compose) | 완료 |
| M2 | 런타임 승격 [소유] Dockerfile 멀티스테이지·비루트·gunicorn + [위임] accounts 역할 모델 3종 | 완료 (ops-reviewer 3라운드, 블로커 0) |
| M3 | 도메인 모델 7종 + 마이그레이션 + Admin | 완료 (리뷰 노트 미작성) |
| M4 | api.md v1.1의 44개 엔드포인트 구현 (8모듈) | **진행 중 — 4/8 모듈, 16/44 엔드포인트** |
| M5 | 스모크 테스트 + 문서 정리 → Phase 2 종료 | 미착수 |

### M4 모듈별 상태

| 모듈 | 엔드포인트 | 상태 |
| --- | --- | --- |
| M4-1 인증 | #2~4, #44 | 완료 (`9dc8df1`, `855d1bf`) |
| M4-2 users/me | #7~10 | 완료 (`91ad8ff`) |
| M4-3 Google OAuth | #5, #6 | 완료 (`0d355d2`), 하드닝 (`c89b263`) |
| M4-4 advisor-applications | #11~15 | 완료 (`b2eaf90`) |
| M4-5 concerns | #16~25 | **미착수** |
| M4-6 advice + feedback | #26~38 | **미착수** |
| M4-7 notifications | #39~41 | **미착수** |
| M4-8 admin roles | #42~43 | **미착수** |

`config/urls.py`는 `accounts.urls` + `advisors.urls` 2개만 include.
`concerns/`·`advice/`·`notifications/` 앱은 모델·Admin만 존재하고 views/serializers/urls/services 파일이 아직 없다.

### 갭 / 부채 (전수)

1. **테스트 코드 0건** — D-7에서 권고했으나 테스트 파일 전무. AC 판정이 전부 수기 스모크 의존.
2. **루트 `README.md` 부재** — `docs/README.md`는 과제 스코프 문서, `docs/README_AIUSAGE.md`는 루트본의 구버전 중복.
3. **README_AIUSAGE.md에 M4-1~M4-4 미기록** (마지막 항목 2026-07-08 M3) — CLAUDE.md §13 위반 상태.
4. **리뷰 노트 미작성**: `03-milestone3-review.md`, `04-milestone4-review.md`.
5. **학습 부채 14건**: M2 9건(401/403/409, atomic 최우선) + M3 2건 + 이월 게이트 3건(드릴 #2·#3, WB-1, M3 퀴즈).
6. **model.md 문서 drift 6건** 미반영.
7. **`.claude/agents/`가 .gitignore 처리됨** — 서브에이전트 8종이 로컬에만 존재. 머신 이동 시 유실.
8. 운영 갭(기록됨): gunicorn 경로 정적파일 미서빙, 브루트포스 방어 Phase 3 이월, 기존 superuser ADMIN 소급 없음.
9. 브랜치 전략: `feat/m4-api` 사용 중이나 PR 없이 진행 (M2 리뷰 리스크 #5 미결).

---

## 1. 마이그레이션의 실체 (오해 제거)

CLI와 VS Code 확장은 **같은 엔진·같은 설정·같은 세션 저장소**를 사용한다. 옮길 것이 거의 없다.

| 자산 | 저장 위치 | 확장에서 |
| --- | --- | --- |
| 프로젝트 규칙 | `./CLAUDE.md` | 그대로 읽음 |
| 서브에이전트 | `./.claude/agents/*.md` | 그대로 동작 |
| 권한/설정 | `~/.claude/settings.json`, `./.claude/settings.json` | 공유 |
| 대화 세션 히스토리 | `~/.claude/projects/-Users-dan-projects-personal-chamneul/` | **동일 경로로 열면 `/resume`으로 이어받음** |
| 메모리 | 위 경로의 `memory/` | 공유 |

**손실 위험은 3가지뿐**: (a) Claude App(웹) 채팅에만 존재하는 결정, (b) gitignore된 `.claude/agents/`, (c) 로컬 `.env`.

---

## 2. 즉시 실행 (약 10분)

```bash
# 1) 프로젝트를 VS Code로 연다
code /Users/dan/projects/personal/chamneul
#    마켓플레이스에서 "Claude Code for VS Code" (Anthropic) 설치
#    또는 통합 터미널에서 `claude` 실행 시 자동 설치 제안

# 2) 인터프리터 고정 (.gitignore가 .vscode/를 tracked로 남겨둔 이유)
mkdir -p .vscode && cat > .vscode/settings.json <<'EOF'
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.analysis.extraPaths": ["${workspaceFolder}"],
  "[python]": { "editor.formatOnSave": false },
  "files.exclude": { "**/__pycache__": true, "**/.ruff_cache": true }
}
EOF

# 3) 서브에이전트 유실 방지 — 둘 중 하나 (Owner 결정 필요)
#    (a) 백업만:  cp -r .claude/agents <백업경로>
#    (b) 커밋 전환(권장): .gitignore의 `.claude/agents/` 줄 삭제 후 커밋
```

**확장 조작법(기본값)**: `Cmd+Esc` 채팅 열기 · `Cmd+Option+K` 커서 위치를 `@file#L10-20`으로 삽입 ·
편집은 VS Code 네이티브 diff 뷰로 Accept/Reject · `Shift+Tab` 플랜 모드 · 슬래시 커맨드/서브에이전트 동일 동작.

### 세션 이어받기

```bash
claude --continue   # 직전 세션 재개
claude --resume     # 세션 목록에서 선택
```

단, 이 방식에 **의존하지 않는다**. 목표는 "세션을 옮기는 것"이 아니라 **리포지토리만 열면 맥락이 복원되는 것**이다.

---

## 3. Notion 폐기 → Git이 Source of Truth

Notion은 읽기 전용 아카이브로 강등하고, 신규 기록은 전부 Git에만 남긴다.

| Notion에서 하던 일 | 대체 위치 |
| --- | --- |
| 현재 진행 상황 정리 | `docs/00-project/STATUS.md` (커밋마다 갱신) |
| 요구사항/기획 | `docs/prd/PRD-00N-*.md` |
| API 명세 | 기존 `docs/api.md` 유지 (분할하지 않음) |
| 결정 기록 | 기존 `docs/adr/` 유지 |
| 작업 쪼개기·체크리스트 | `specs/SPEC-00N-*/{spec,plan,tasks,acceptance}.md` |
| 완료 판정 | `docs/testing/TEST_CRITERIA.md` + 실제 테스트 |
| AI 활용 대장 | 기존 `README_AIUSAGE.md` 유지 |

---

## 4. 제약 — CLAUDE.md 동결과 스켈레톤 충돌

CLAUDE.md §16: *"2026-06-26 이후 CLAUDE.md는 동결 — 변경은 해당 조항을 명시적으로 supersede 하는 새 ADR로만."*

스켈레톤 도입은 §2(Source of Truth 순서), §3(트리), §13(문서 규칙), §17(워크플로)을 건드린다.
→ **전환의 첫 작업은 코드가 아니라 `ADR-006-ai-native-spec-driven-skeleton.md`**이며, Owner 승인 후에만 CLAUDE.md를 개정한다.

### 스켈레톤 원본 대비 확정 예외 3건

| # | 충돌 | 결정 |
| --- | --- | --- |
| C-1 | 스켈레톤은 `docs/api/API-00N-*.md` 분할 / 현재는 단일 `docs/api.md` 961줄 | **현행 유지** — 44엔드포인트를 44파일로 쪼개는 것은 순손실 |
| C-2 | 스켈레톤은 `src/` / 현재는 Django 앱이 루트 | **현행 유지** — Django 관용 구조 |
| C-3 | CLAUDE.md가 규칙 전부를 보유 / 스켈레톤은 "CLAUDE.md는 얇게, 규칙은 `.claude/rules/`" | **점진 분할** — §9~§12를 `.claude/rules/{coding,security,testing,infrastructure}.md`로 이동, 본문엔 포인터만 (ADR-006에 포함) |

---

## 5. 프롬프트 3종

### 프롬프트 1 — 부트스트랩 (1회)

```text
이 리포지토리를 AI-Native / Spec-Driven 구조로 전환한다. 아직 코드는 수정하지 마라.

[읽기 순서]
CLAUDE.md → docs/api.md §3 요약표 → docs/model.md §5 → docs/reviews/04-milestone4-definition.md
→ config/urls.py, accounts/, advisors/ (구현 완료분) → README_AIUSAGE.md

[제약]
- CLAUDE.md §16에 의해 CLAUDE.md는 동결 상태다. 직접 수정 금지.
  구조 전환은 반드시 docs/adr/ADR-006-ai-native-spec-driven-skeleton.md 로 제안하고
  Owner 승인 후에만 CLAUDE.md를 개정한다.
- 다음 3건은 스켈레톤 원본과 다르게 간다(확정): api.md 단일 파일 유지 / src/ 미도입(Django 앱 루트 유지)
  / CLAUDE.md의 §9~§12는 .claude/rules/{coding,security,testing,infrastructure}.md 로 분할하고 본문엔 포인터만 남긴다.
- Notion은 더 이상 쓰지 않는다. 모든 신규 기록은 Git에만 남긴다.

[이번 작업 산출물 — 이것만 생성한다]
1. docs/adr/ADR-006-ai-native-spec-driven-skeleton.md  (Status: Proposed, 표준 ADR 템플릿)
2. docs/00-project/STATUS.md
   - 현재 Phase / 마일스톤 / 구현된 엔드포인트 번호 목록 / 미구현 번호 목록
   - Active SPEC / 다음 최소 작업 단위 / 미결 Owner 결정 / 학습 부채 요약
   - 반드시 실제 코드(urls.py, views.py)를 읽고 사실로만 채운다. 추측 금지.
3. README.md (루트) — "지도" 원칙: 개요/목적/스택/구조/Quick Start/문서 링크만. 규칙·명세 본문 금지.
4. docs/testing/TEST_CRITERIA.md — 현재 테스트 0건인 현실을 명시하고, M4 AC를 자동화 가능한 판정 기준으로 번역
5. specs/SPEC-001-concerns-api/{spec.md,plan.md,tasks.md,acceptance.md}
   - 대상: api.md #16~25 (M4-5 concerns). GIVEN/WHEN/THEN + AC + Non-Goals까지.
6. .claude/rules/*.md 4종 (CLAUDE.md에서 발췌 이동, 내용 변경 없이)

[보고]
생성 전에 (a) 파일 목록 (b) STATUS.md 초안 요약 (c) CLAUDE.md 개정 diff 미리보기 (d) 발견한 문서 모순
을 먼저 보고하고 내 승인을 받아라.
```

### 프롬프트 2 — 매 세션 시작

```text
CLAUDE.md → README.md → docs/00-project/STATUS.md 를 읽고,
Active SPEC과 관련 ADR/API 절만 추가로 읽어라. 아직 코드는 수정하지 마라.

다음을 보고하라:
1) 프로젝트 목적  2) 현재 Active SPEC  3) 그 SPEC의 완료 조건
4) 관련 Architecture Decision  5) 현재 구현 상태(실제 코드 기준)
6) 불확실하거나 서로 충돌하는 내용  7) 다음 최소 작업 단위 1개
```

### 프롬프트 3 — SPEC 단위 구현 루프 (M4-5부터 반복)

```text
SPEC-001의 TASK-001만 구현한다. 순서 엄수:
1. acceptance.md의 AC를 Django 테스트로 먼저 작성하고, 실패하는 것을 실행 결과로 보여라.
2. 그 다음 최소 구현. 상태 전이·부수효과는 services.py, 접근 제어는 common/permissions.py + 객체 수준 검사.
3. manage.py check / makemigrations --check / ruff / manage.py test 를 실제 실행하고 출력을 붙여라.
   "완료했습니다"는 증거가 아니다. 실행 출력만 증거다.
4. 통과하면 커밋 (메시지에 SPEC-001/TASK-001 포함) → STATUS.md 갱신 → README_AIUSAGE.md 1항목 추가.
5. TASK-002로 넘어가기 전 멈추고 내 확인을 받아라.
Dockerfile / docker-compose* / .env* 는 불가침이다. 테스트를 통과시키려고 테스트나 AC를 수정하지 마라.
```

---

## 6. Pro Tips (이 프로젝트 특화)

1. **테스트 0건이 최대 리스크.** 스켈레톤 원칙 5("Test는 AI의 판정 장치")가 지금 완전히 비어 있다. M4-5부터 TDD로 전환해야 남은 28개 엔드포인트를 위임하고도 수기 스모크 없이 판정된다. MVP 도출 속도를 가장 크게 올리는 항목.
2. **`.claude/agents/`를 커밋으로 전환.** 서브에이전트 8종은 이 프로젝트의 리뷰 하네스 자체인데 Git에 없다. 원칙 6("Git이 장기 기억")과 정면 충돌.
3. **`.claude/commands/` 슬래시 커맨드 3개 생성** — `/status`(프롬프트 2), `/spec-next`(프롬프트 3), `/gate`(check+ruff+test+makemigrations 일괄). 확장에서 `/` 자동완성으로 뜨므로 긴 프롬프트 재입력이 사라진다.
4. **PR 전환 확정**(M2 리뷰 리스크 #5). 확장 diff 뷰 + `gh pr create` + `.github/pull_request_template.md`(SPEC ID / AC 체크박스 / 실행 출력 첨부란) 조합이면 리뷰 노트 부담이 PR 본문으로 흡수된다 — Notion 폐기와 같은 효과.
5. **STATUS.md 갱신을 커밋 규칙으로 못 박기.** "구현 커밋에는 STATUS.md 변경이 반드시 동반된다"를 `.claude/rules/git.md`에 명시하면 세션이 끊겨도 다음 AI가 즉시 복원된다.
6. **문서 부채 4건(AIUSAGE M4 미기록, 리뷰 노트 2건, model.md drift 6건)은 부트스트랩과 함께 일괄 청산.** 이월할수록 STATUS.md 신뢰도가 떨어지고 그것이 곧 AI 컨텍스트 품질 저하다.
7. **학습 게이트(드릴·퀴즈·WB)는 스켈레톤 Gate 8(Learn)에 매핑.** `docs/learning/`을 유지하되 STATUS.md에 "학습 부채 N건" 카운터를 노출하면 학습 목표와 개발 속도가 한 화면에서 보인다.
