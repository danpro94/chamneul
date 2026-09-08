# ADR-005. 문서 체계 AI-Native / Spec-Driven 재정렬

## Status

Accepted

## Date

2026-09-08

## Owner

danpro94

## Supersedes

CLAUDE.md §2 (Source of Truth Order), §3 (Current Known Project Tree), §17 (First Recommended Workflow) — 본 ADR로 대체.
CLAUDE.md §13 (Documentation Rules) — 대체가 아니라 **확장**. 기존 유지 대상은 그대로 두고 신규 배치를 추가한다.
CLAUDE.md §16 (Approval Gates / Constitutional lock) — 대체하지 않는다. **명확화**만 한다 (§4.5 참조).

---

## 1. Context

### 1.1 무엇이 바뀌었나

Owner는 개발 환경을 **Claude Code CLI + Claude App(Notion 연동)** 에서 **VS Code + Claude Code Extension** 으로 전환한다. 목적은 더 빠른 MVP 도출이며, 부수적으로 **Notion DB에 수기로 문서화·정리·내재화하는 작업을 폐지**한다. 해당 작업은 실효가 없었고(§1.3 참조) 현업 수준에 미치지 못한다는 Owner 판단이다.

동시에 "AI-Native / Spec-Driven Engineering Skeleton v1.0"을 도입한다. 그 핵심 명제는 다음 한 줄이다.

> 좋은 AI 개발 환경은 AI가 프로젝트를 많이 기억하게 만드는 환경이 아니라, 새로운 AI가 처음 Repository를 열어도 프로젝트의 목적·현재 상태·의사결정·완료조건·다음 작업을 스스로 복원할 수 있게 만드는 환경이다.

### 1.2 진단 — 맥락은 이미 Git에 있다

전환 시점에 문서는 5,808줄이 커밋되어 있다 (`docs/model.md` 966, `docs/api.md` 926, `CLAUDE.md` 661, ADR 4종, 리뷰·학습·UX 노트). Claude App 채팅 세션에만 존재하는 의사결정은 없다. Owner 결정 Q1~Q22 / M1~M8 / D1~D6 / G1~G5는 전부 AI 사용 대장에 기록되어 있다.

따라서 이 전환은 **맥락을 옮기는 작업이 아니라, 비어 있는 Harness 레이어를 채우는 작업**이다.

실제로 비어 있는 것:

| 없는 것 | 결과 |
| --- | --- |
| 루트 `README.md` | 진입점 부재. §13·§1이 요구하는데 존재하지 않는다 |
| 상태 문서 | 현재 상태가 4개 문서에 흩어져 있어 세션마다 ~2,000줄을 재추론해야 한다 |
| `specs/` | M4(43 엔드포인트)에 정의 문서가 없다 |
| `docs/testing/` + 테스트 | 판정 장치 부재. 테스트 0건, 테스트 러너 실행 이력 0회 |
| `.claude/` · `.vscode/` | Extension 온보딩·권한·슬래시 명령 없음 |
| 결정 색인 | ADR / Q1~Q22 / UX C-1~C-13 / model.md O-1~O-8이 서로 다른 파일에 흩어져 있다 |

### 1.3 CLAUDE.md의 어느 조항이 새 세션을 오도하는가

이것이 본 ADR의 직접적 동기다. VS Code Extension에서 새 세션을 열면 `CLAUDE.md`가 자동 로드되는데, 그 안의 세 조항이 **사실과 다르거나 세션을 정지시킨다.**

| 조항 | 실제 내용 | 문제 |
| --- | --- | --- |
| §2 Source of Truth Order | 6순위에 "Notion-exported API specification", 7순위에 `docs/api.md`, 8순위에 `docs/model.md` | **Notion을 실제 명세보다 상위에 둔다.** `docs/api.md` §7 "Notion Update Plan"은 작성 이후 한 번도 실행되지 않았다. Notion은 v0(41건)에서 멈춰 있고 v1(43건)이 아니다. 순서대로 따르면 낡은 명세가 최신 명세를 이긴다 |
| §2·§17 파일명 | `docs/2 mvp-scope.md`, `docs/0 README.md` 참조 | 두 파일 모두 존재하지 않는다. 실제는 `docs/2 mvp-scope_v1.md`, `docs/README.md`. `docs/ux/01-phase2-screen-flows.md` C-13이 이미 drift로 등재 |
| §3 Current Known Project Tree | 루트에 `docs/`만 있는 트리 | 앱 5개·모델 11종·마이그레이션 6개가 생기기 전 상태. 사실과 다르다 |
| §17 step 6 | "Wait for Notion API export markdown to be added." | **세션이 여기서 정지한다.** 기다릴 대상이 이미 3개월 전에 `docs/api.md`로 흡수되었다 |

§3과 §17 steps 10~12는 3개월 전에 완료된 작업을 미래 시제로 지시한다.

---

## 2. Decision Drivers

1. 새 세션이 저장소만 읽고 스스로 복원 가능해야 한다 (스켈레톤의 핵심 명제).
2. CLAUDE.md §16 헌법 락을 **우회하지 않고 준수**해야 한다. 락은 ADR을 개정 수단으로 명시하고 있으므로, 본 ADR이 그 수단이다.
3. 도메인 규칙(§6)은 손실 없이 보존해야 한다. taxonomy 11종·상태 enum·`deleted_at` 소프트 삭제 규약·advice 버저닝은 코드와 마이그레이션이 이미 의존하는 계약이다.
4. 문서를 삭제하지 않는다. §16이 삭제를 승인 게이트로 지정한다.
5. 최소 변경. 스켈레톤 전체를 지금 만들지 않고 "필요할 때 생성한다" 원칙을 따른다.

---

## 3. Options Considered

### Option A — CLAUDE.md 직접 수정

**설명**: §2·§3·§17을 제자리에서 고친다.

**장점**: 가장 단순. 새 세션이 자동으로 올바른 내용을 읽는다.

**단점**: §16 헌법 락 정면 위반. "미래 Claude 세션은 CLAUDE.md를 직접 수정해서는 안 된다"는 명시적 금지를 어긴다.

**Risk**: 이 저장소의 거버넌스 신뢰성이 무너진다. 락이 한 번 무시되면 다시는 구속력을 갖지 못한다.

### Option B — ADR만 작성하고 끝

**설명**: ADR-005를 쓰고 CLAUDE.md는 그대로 둔다.

**장점**: 규정상 완벽하게 정당하다.

**단점**: **기계적으로 무용하다.** Claude Code는 루트 `CLAUDE.md`를 자동 로드하지만 `docs/adr/*`는 로드하지 않는다. 새 세션은 ADR-005의 존재를 모른 채 낡은 §2·§17을 따른다.

**Risk**: 문서상으로만 해결되고 실제 세션 동작은 그대로다.

### Option C — ADR + 메커니즘 레이어 (채택)

**설명**: ADR-005로 조항을 supersede하고, `.claude/rules/00-source-of-truth.md`에 운용본을 두고, `.claude/settings.json`의 **SessionStart 훅**으로 매 세션 시작 시 주입한다.

**장점**: CLAUDE.md 무수정. 락 준수. 그러면서 새 세션이 실제로 올바른 순서를 받는다. `docs/learning/02`가 이미 같은 선례를 남겼다 — 헌법을 고치지 않고 메커니즘 레이어를 얹었다.

**단점**: 진실의 소재가 두 곳(ADR + rules 파일)이 된다. 동기화 책임이 생긴다.

**Risk**: 훅이 동작하지 않으면 Option B로 퇴화한다. 검증 절차(§9-4)로 방어한다.

---

## 4. Decision

**Option C를 채택한다.** CLAUDE.md 본문은 한 글자도 수정하지 않는다.

### 4.1 §2 Source of Truth Order 대체

```
1. CLAUDE.md                          — 헌법 (동결. ADR로만 개정)
2. docs/adr/                          — 같은 조항에 대해서는 높은 번호가 이긴다
3. docs/00-project/STATUS.md          — 지금 어디까지 왔는가
4. specs/SPEC-NNN/                    — 진행 중 작업 (자기 범위 안에서만 구속력)
5. docs/api.md                        — 43 엔드포인트 계약 (정본)
6. docs/model.md                      — 데이터 모델 (정본)
7. docs/2 mvp-scope_v1.md
   docs/1 서비스기획_v1.md             — 제품 의도
8. code
```

**은퇴**: "Notion-exported API specification". 더 이상 source of truth가 아니다. `docs/api.md` §7 "Notion Update Plan"도 함께 은퇴한다 — 실행되지 않았고, 이제 실행할 이유가 없다.

충돌 발견 시 처리는 §2 기존 규칙을 유지한다: 조용히 해소하지 말고 충돌 표를 만들어 Owner 결정을 받는다.

### 4.2 §3 Current Known Project Tree 대체

`README.md`의 "Repository 구조" 절로 이관한다. CLAUDE.md에 트리를 고정해 두면 필연적으로 낡는다 — 실제로 낡았다. README는 살아 있는 문서이므로 갱신 부담이 낮다.

### 4.3 §13 Documentation Rules 확장

기존 유지 대상(`README.md`, `README_AIUSAGE.md`, `docs/api.md`, `docs/model.md`, `docs/smoke-test.md`, `docs/adr/`, `docs/reviews/`)은 **전부 그대로 유지**한다. 다음을 추가한다.

```
docs/00-project/STATUS.md              현재 상태 (단일 소스)
docs/00-project/PROJECT_CONTEXT.md     변하지 않는 배경
docs/00-project/GLOSSARY.md            한/영 도메인 용어
docs/00-project/DECISION_INDEX.md      결정 색인 (포인터만)
docs/00-project/LEARNING_DEBT.md       학습 부채 원장
docs/testing/TEST_CRITERIA.md          완료 판정 기준
specs/SPEC-NNN-<slug>/                 기능 명세 + 수용 기준 + 증거
```

`README_AIUSAGE.md`는 §13이 이름으로 지정하므로 **루트에 그대로 둔다.**

### 4.4 §17 First Recommended Workflow 대체

```
1. .claude/rules/00-source-of-truth.md   (SessionStart 훅이 자동 주입)
2. README.md
3. docs/00-project/STATUS.md
4. 활성 SPEC의 spec.md + acceptance.md
5. 필요한 ADR / api.md / model.md 해당 절만
```

"Notion export를 기다린다"는 단계는 삭제한다. 기다릴 대상이 없다.

### 4.5 §16 Approval Gates — 명확화 (대체 아님)

§16은 이미 "changes happen only through a new ADR that explicitly supersedes the affected clause"라고 개정 수단을 명시한다. **락은 설계대로 작동하고 있으며, 본 ADR이 그 첫 행사다.** 따라서 §16을 supersede하지 않는다. 다음만 명확히 한다.

* ADR 개정 창구는 상시 개방이다. "2026-06-22와 2026-06-26만이 편집 창구"라는 문구는 **CLAUDE.md 본문 직접 편집**에 대한 제한이며, ADR 발행을 제한하지 않는다.
* "미래 Claude 세션은 CLAUDE.md를 직접 수정해서는 안 된다"는 금지는 **그대로 유효**하다. 본 ADR 이후에도 유효하다.
* 승인 게이트 목록(§16 본문)은 무수정 유지된다. 특히 서드파티 패키지 추가, MVP 범위 변경, 파일 삭제는 계속 Owner 승인 대상이다.

### 4.6 파일 이동 2건 (삭제 아님)

`git mv`로 수행한다. 이력이 보존되고 되돌릴 수 있으므로 §16의 삭제 게이트 대상이 아니다.

| 이동 전 | 이동 후 | 사유 |
| --- | --- | --- |
| `docs/README.md` | `docs/00-project/AWS_ASSIGNMENT_BRIEF.md` | 이 파일은 문서 색인이 아니라 **AWS 과제 브리프**다(컨셉추얼/AWS 아키텍처, Terraform, EKS, 모니터링, 장애 대응, 비용 요구사항 + AI 활용 원칙). `docs/README.md`라는 이름은 열어 본 사람을 오도한다 |
| `docs/README_AIUSAGE.md` | `docs/00-project/DECISION_ARCHIVE_2026-06.md` | 루트에 같은 이름의 현행 대장이 있어 VS Code 빠른 열기에서 두 개가 잡힌다. 에디터 중심 워크플로로 전환하는 시점에 실질적 위험이다. **삭제하지 않는다** — Q1~Q22 / M1~M8 / D1~D6 / G1~G5 결정 표의 유일한 보관처이며, `docs/api.md`·`docs/model.md`가 왜 지금 모습인지의 출처다 |

### 4.7 이동하지 않는 것

| 파일 | 유지 사유 |
| --- | --- |
| `docs/1 서비스기획_v1.md` | **ADR-004 §57-58이 이 경로를 명시적으로 고정**하고, gitignore된 `docs/_private/1 서비스기획_v1_full.md`와 짝을 이룬다. 이름을 바꾸면 공개/비공개 쌍이 어긋나고 승인된 ADR을 supersede해야 한다 |
| `docs/2 mvp-scope_v1.md` | 6개 문서가 참조한다. UX C-13이 이미 "참조 정리만 필요"로 분류했고, 본 ADR §4.1이 올바른 경로를 명시하는 것이 그 정리다 |
| `docs/api.md` | **43개 파일로 쪼개지 않는다.** 10행 표 하나씩 담긴 파일 43개는 탐색 가능한 926줄 계약 문서보다 나쁘다. 엔드포인트별 JSON 스키마는 해당 `specs/SPEC-NNN/spec.md`에 둔다 |
| `docs/reviews/` 명명 규칙 | `NN-milestoneN-{definition,review}`는 2026-07-07 Owner 결정이다 (`03-milestone3-definition.md:5`) |
| `docs/request/`, `docs/learning/`, `docs/ux/`, `docs/_private/` | 이력·운영 모델·사양·전략 IP. 이동 이득 없음 |

### 4.8 `specs/` 도입 승인

`specs/SPEC-NNN-<slug>/`를 M4 구현의 작업 단위로 승인한다. 최소 구성은 `spec.md` · `plan.md` · `tasks.md` · `acceptance.md` · `handoff.md` · `evidence/`.

`docs/learning/02` §2.0의 `[소유]/[위임]/[읽기]` 라우팅 태그는 **소실되지 않는다.** `spec.md` front-matter의 `routing:` 필드와 `tasks.md`의 태스크별 태그로 이관한다. 이 태그는 이 프로젝트의 고유 자산이며 스켈레톤에는 대응물이 없다.

---

## 5. Why

**Option C를 택한 이유는 락을 지키면서 실제로 동작하기 때문이다.**

Option A는 빠르지만, 헌법을 처음 개정하는 순간에 헌법이 정한 절차를 어기는 선택이다. 이 저장소는 포트폴리오이기도 하다 — 규정을 만들고 스스로 어긴 이력은 규정을 만들지 않은 것보다 나쁘다.

Option B는 정당하지만 무용하다. 자동 로드되지 않는 문서에 쓴 규칙은 규칙이 아니다.

Option C는 `docs/learning/02`가 이미 검증한 패턴이다. 그 문서는 CLAUDE.md에 "달성 메커니즘이 없다"는 갭 4개를 식별하고, 헌법을 고치는 대신 메커니즘 레이어(본문 + 에이전트 3종)를 얹어 해결했다. 본 ADR은 같은 수법을 문서 체계에 적용한다.

**§16을 supersede하지 않은 이유**는 더 단순하다. 첫 개정에서 자기 개정 게이트를 무력화하는 것은 자기 편의적이고, 무엇보다 **필요하지 않다.** §16은 이미 ADR을 개정 수단으로 지정했다. 락은 고장 나지 않았다.

---

## 6. Consequences

### Positive

* 새 세션이 `README.md` → `STATUS.md` → 활성 SPEC 순으로 3개 문서만 읽고 작업에 진입할 수 있다. 현재는 4개 문서 ~2,000줄과 git log를 교차 참조해야 한다.
* Notion 수기 동기화가 공식적으로 끝난다. `DECISION_INDEX.md`가 색인만 유지하고 내용은 기존 문서를 가리키므로, 같은 정보를 두 곳에서 관리하지 않는다.
* CLAUDE.md 도메인 규칙(§6)이 무손실 보존된다. taxonomy 11종·상태 enum·`deleted_at` 규약·advice 버저닝은 마이그레이션과 코드가 이미 의존하는 계약이다.
* `[소유]/[위임]/[읽기]` 라우팅이 SPEC 단위로 살아남는다.
* 헌법 락이 설계대로 작동한 첫 사례가 기록된다.

### Negative

* **CLAUDE.md를 편집하지 않으므로 새 라우팅이 자동 로드되지 않는다.** Claude Code는 루트 `CLAUDE.md`만 자동으로 읽고 `.claude/rules/`는 읽지 않는다. SessionStart 훅에 의존한다. **훅이 동작하지 않으면 Option B로 퇴화한다.** 이것이 최소 개정을 택한 대가이며, §9-4가 이를 검증한다.
* CLAUDE.md를 그대로 읽는 사람(사람 독자, 다른 AI 도구)은 §2·§3·§17이 낡았다는 사실을 모른 채 읽게 된다. 선택적 완화책은 §11-2에 둔다.
* 진실의 소재가 ADR-005와 `.claude/rules/00-source-of-truth.md` 두 곳이 된다. 후자는 전자의 운용 요약이며, 불일치 시 ADR이 이긴다.

### Neutral

* `docs/00-project/`, `docs/testing/`, `specs/` 세 디렉터리가 새로 생긴다. `docs/iac/`, `docs/deployment/`, `docs/runbooks/`, `.github/`는 만들지 않는다 — §5 Phase 2 범위 밖이고 §16 게이트 대상이며, 스켈레톤 자신이 "필요할 때 생성한다"를 원칙으로 둔다.

---

## 7. Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| SessionStart 훅 미동작 → 새 세션이 낡은 §2·§17을 따름 | 높음 — 본 ADR의 핵심 전제가 무너진다 | §9-4 왕복 검증을 전환 직후 1회 필수 수행. 실패 시 §11-2 선택안(Owner가 CLAUDE.md에 개정 블록 추가)으로 승격 |
| ADR-005와 `.claude/rules/` 불일치 누적 | 중간 | rules 파일 상단에 "정본은 ADR-005"를 명기. 마일스톤 종료 시 대조 |
| 파일 이동으로 기존 문서의 상호 참조 깨짐 | 낮음 | §9-1 grep 검증. CLAUDE.md 내 참조는 의도적으로 낡은 상태로 두고 본 ADR이 커버 |
| `specs/` 도입이 또 하나의 미유지 디렉터리가 됨 | 중간 | SPEC-001 1개만 먼저 만들고 루프가 실제로 한 바퀴 돈 뒤 나머지를 만든다 (§11-1) |

---

## 8. Rollback / Reversal

**되돌려야 하는 조건**: SPEC 루프가 M4 초반(SPEC-001~002)에 실질적 이득 없이 오버헤드만 만드는 것으로 판명될 때.

**되돌리는 방법**: `specs/` 도입만 철회하고 마일스톤 단위 `docs/reviews/NN-milestoneN-definition.md` 방식으로 복귀한다. `git mv` 2건은 역방향 `git mv`로 되돌린다. ADR-005는 Deprecated로 표시하되 삭제하지 않는다. §4.1 source of truth 순서(Notion 은퇴)는 **되돌리지 않는다** — Notion drift는 되돌릴 이유가 없는 독립적 사실이다.

---

## 9. Verification

| # | 검증 | 기대 결과 |
| --- | --- | --- |
| 9-1 | `git diff main...HEAD -- CLAUDE.md` | **출력이 비어 있어야 한다.** 본 마이그레이션의 핵심 불변식 |
| 9-2 | `git log --diff-filter=D --name-only main...HEAD` | 출력이 비어 있어야 한다 (삭제 0건) |
| 9-3 | `git log --follow --oneline -- docs/00-project/DECISION_ARCHIVE_2026-06.md` | 이동 전 커밋 이력이 보여야 한다 |
| 9-4 | **왕복 검증.** VS Code Extension에서 새 세션을 열고 한국어로 묻는다: *"이 프로젝트의 source of truth 순서가 뭐야? Notion을 봐야 해?"* | ADR-005를 인용하고 Notion이 은퇴했다고 답해야 한다. CLAUDE.md §2를 그대로 읊거나 Notion export를 요구하면 **훅이 동작하지 않는 것이다** |
| 9-5 | `uv run python manage.py check` / `makemigrations --check --dry-run` / `ruff check .` | 코드 무변경이므로 전부 기존과 동일하게 통과 |

---

## 10. Follow-ups

1. **ADR-006 — SPEC 루프 + 소유권 라우팅의 프로세스 승격**: SPEC-001이 **완료된 뒤에** 작성한다. `docs/learning/02` §8-2가 이미 Owner 결정으로 미뤄 둔 항목이다. 실제로 한 바퀴 돈 루프를 문서화한 ADR이 의도만 적은 ADR보다 낫다 — "AI의 '완료했습니다'는 증거가 아니다"를 프로세스 자신에게 적용한 것이다.
2. **`.claude/agents/` 커밋 여부 재결정 (Phase 3)**: 3종(`drill-master`, `chaos-coach`, `ops-reviewer`)은 `.gitignore:34`로 제외되어 Owner의 CLI 머신에만 존재한다. 머신 전환 시 소실된다. 본 전환에서는 `.claude/commands/`가 같은 워크플로를 대체하므로 결정을 미룬다. 드릴이 재개되는 Phase 3에 재검토한다.
3. **Phase 3 부착 지점**: `docs/iac/` ← `AWS_ASSIGNMENT_BRIEF.md`의 Terraform 리소스 목록. `docs/runbooks/RUN-001~006` ← `docs/learning/02` §4.2 장애 드릴 카탈로그 6종 (**드릴 카탈로그는 이미 런북의 초안이다** — 가장 깔끔한 부착점). `docs/deployment/` ← ECR/EKS 파이프라인. `.github/workflows/` ← `.claude/commands/verify.md` 내용을 그대로 승격.
4. **`docs/smoke-test.md`**: §13이 요구하나 M5 산출물이다 (`docs/reviews/02-milestone2-review.md:70`). 지금 빈 파일로 만들지 않는다.
5. **model.md drift 6건 · O-1 DomainCategory 확정**: `DECISION_INDEX.md`에 미결로 등재하고, 해당 SPEC 착수 시 해소한다.

---

## 11. 부록 — 선택 사항 (Owner 결정)

### 11-1. `specs/` 점진 도입

SPEC-001만 먼저 작성하고, 나머지 11개는 `STATUS.md`에 로드맵 표로만 남긴다. 스켈레톤의 "필요할 때 생성한다" 원칙이다. 12개를 미리 만들면 대부분이 빈 껍데기가 되고, 그것이 바로 Owner가 폐지하려는 종류의 작업이다.

### 11-2. CLAUDE.md 개정 블록 (Owner만 수행 가능)

§16의 금지는 **Claude**를 구속한다. Owner는 헌법의 저자이고 본 ADR이 승인 근거이므로, Owner가 직접 다음 6줄을 CLAUDE.md 최상단에 붙여 넣는 것은 락 위반이 아니다.

```markdown
> **개정 고지 (ADR-005, 2026-09-08)**
> §2 Source of Truth Order · §3 Project Tree · §17 First Workflow 는 ADR-005로 대체되었다.
> §13은 확장되었다. §16은 유효하며 대체되지 않았다.
> 그 외 전 조항(§0·§1·§4·§5·§6 도메인 규칙 전체·§7~§12·§14·§15)은 무수정 유효하다.
> 정본: docs/adr/ADR-005-ai-native-spec-driven-migration.md
```

**권장**: 적용. SessionStart 훅은 Claude Code 세션만 커버한다. 이 블록은 사람 독자와 다른 AI 도구까지 커버하며, §9-4 검증이 실패했을 때의 대비책이기도 하다.

---

## 12. References

* CLAUDE.md §2, §3, §13, §16, §17 (대상 조항) / §6 (무수정 보존 대상)
* `docs/adr/ADR-001-local-container-architecture.md` — 기술 스택·로컬 런타임
* `docs/adr/ADR-004-strategy-doc-visibility-split.md` §57-58 — `docs/1 서비스기획_v1.md` 경로 고정
* `docs/learning/02-ai-collaboration-and-ownership-strategy.md` — 메커니즘 레이어 선례, §2.0 라우팅 규칙, §5 프롬프트 템플릿
* `docs/ux/01-phase2-screen-flows.md` §7 C-13 — 파일명 drift 등재
* `docs/api.md` §7 — 은퇴 대상 Notion Update Plan
* AI-Native / Spec-Driven Engineering Skeleton v1.0 (Owner 제공, 2026-09-08)
