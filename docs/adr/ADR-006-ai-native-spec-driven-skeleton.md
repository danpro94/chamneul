# ADR-006. AI-Native / Spec-Driven 스켈레톤 전환

## Status

Accepted (2026-09-10)

## Date

2026-09-09 (Proposed) / 2026-09-10 (Accepted)

## Context

개발 환경이 Claude Code CLI + Claude App(웹)에서 VS Code Claude Code Extension으로 이동한다(`docs/request/3-vscode-migration_prompt.md`). 확장은 CLI와 같은 엔진·설정·세션 저장소를 쓰므로 마이그레이션 자체는 손실이 거의 없지만, 이 전환을 계기로 두 가지 별개 문제를 함께 해소한다.

1. **Notion 폐기**: 수기 문서화를 Notion에 의존해 왔고, 이는 이미 사실상 방치되어 있다(README_AIUSAGE.md 각 세션 잔여 리스크에 "Notion drift" 반복 기록). Git을 유일한 source of truth로 승격한다.
2. **AI 컨텍스트 복원 문제**: 세션이 끊길 때마다 "지금 뭘 하고 있었는지"를 CLAUDE.md + api.md + model.md + 최근 커밋을 수동으로 종합해 복원해야 했다. M4가 8모듈 중 4모듈째에서 세션이 끊긴 현재 시점이 전형적 사례다. 실제 구현 상태(코드)와 계획 문서(reviews/04-milestone4-definition.md는 "43개"로 고정, 실제 api.md는 44개)가 이미 어긋나 있다.

CLAUDE.md §16 Constitutional lock에 따라 2026-06-26 이후 CLAUDE.md는 동결 상태이며, 개정은 해당 조항을 명시적으로 supersede하는 새 ADR로만 가능하다. 본 ADR이 그 절차다.

---

## Decision

리포지토리에 다음 3개 계층을 추가한다. 코드는 변경하지 않는다 — 순수 구조/문서 전환이다.

### 1. `docs/00-project/STATUS.md` — 살아있는 현황판

Phase / 마일스톤 / 구현된 엔드포인트 번호 목록 / 미구현 번호 목록 / Active SPEC / 학습 부채 요약을 담는다. 실제 코드(`urls.py`, `views.py`)를 읽고 사실로만 채우며, 구현 커밋에는 이 파일 갱신이 반드시 동반된다(§9 참조).

### 2. `specs/SPEC-00N-*/` — SPEC 단위 작업 분해

API 모듈 하나(M4-5 concerns 같은 단위)를 `spec.md`(GIVEN/WHEN/THEN) / `plan.md` / `tasks.md` / `acceptance.md` 4파일로 쪼갠다. api.md는 "무엇을"(계약)을 정의하고, SPEC은 "어떤 순서로, 어떻게 검증하며 구현하는가"를 정의한다 — 서로 대체하지 않는다.

### 3. `.claude/rules/*.md` — CLAUDE.md 세부 규칙 분할

CLAUDE.md §9(Coding)~§12(Testing)를 원문 그대로 `.claude/rules/{coding,security,testing,infrastructure}.md`로 옮기고, 본문엔 포인터만 남긴다. CLAUDE.md는 "무엇을 지킬 것인가"(헌법)로 얇아지고, 세부 체크리스트는 `.claude/rules/`가 담당한다.

### 4. 스켈레톤 원본 대비 확정 예외 3건

| # | 원본 스켈레톤 관행 | 이 프로젝트 결정 | 사유 |
| --- | --- | --- | --- |
| C-1 | `docs/api/API-00N-*.md`로 엔드포인트별 분할 | **현행 유지** — 단일 `docs/api.md` | 44 엔드포인트를 44개 파일로 쪼개는 것은 상호참조·URI 변경 매핑표(§3)의 정합성만 해치는 순손실 |
| C-2 | `src/` 하위에 애플리케이션 코드 배치 | **현행 유지** — Django 앱이 리포지토리 루트 | Django 관용 구조(`manage.py` 옆에 앱)를 벗어나는 것은 얻는 게 없다 |
| C-3 | 규칙 전부를 최상위 헌법 문서 하나에 보유 | **점진 분할** — §9~§12만 `.claude/rules/`로, 나머지(§0~§8, §13~§17)는 CLAUDE.md에 유지 | 도메인 규칙(§6)·API 설계 규칙(§7)은 이 프로젝트 정체성 그 자체라 헌법에 남기고, 범용 코딩/보안/테스트/인프라 체크리스트만 분리 |

### 5. 문서 정합 부수 정리 (본 ADR에 흡수, 별도 ADR 불요)

STATUS.md·specs 작성 과정에서 발견된 아래 문서 drift는 본 ADR의 CLAUDE.md 개정 승인과 함께 정리한다:

* CLAUDE.md §5가 "43개 엔드포인트"로 고정되어 있으나 api.md v1.1은 44개(#44 CSRF 부트스트랩, 2026-07-08 D-1). §5 문구를 44로 정정.
* CLAUDE.md §2 Source of Truth 순서가 가리키는 경로 `docs/2 mvp-scope.md` / `docs/0 README.md`는 실제로 `docs/2 mvp-scope_v1.md` / `docs/README.md`다. 경로를 정정하고, `.claude/rules/*.md` / `docs/00-project/STATUS.md` / `specs/`를 순서에 추가한다.
* CLAUDE.md §2의 "Notion-exported API specification" 항목은 삭제하지 않고 *읽기 전용 아카이브*로 강등 표기한다(과거 결정의 출처이므로 삭제하지 않는다).

---

## Rationale (Why)

* **STATUS.md가 필요한 이유**: 세션이 끊긴 뒤 다음 AI(또는 다음 세션의 Owner)가 "지금 무엇이 진짜로 구현되어 있는가"를 코드 재독해 없이 알 수 있어야 한다. reviews/04-milestone4-definition.md 같은 계획 문서는 착수 시점 스냅샷이라 구현이 진행될수록 낡는다 — 계획 문서와 현황판의 역할을 분리한다.
* **SPEC이 필요한 이유**: api.md의 "GET /api/v1/users/me/concerns" 같은 계약 서술은 구현 순서·테스트 우선순위·Non-Goals를 담지 않는다. 44개 엔드포인트를 8개 모듈로만 나누는 현재 단위(reviews/04)는 "모듈 하나 = 커밋 하나"에는 맞지만 TDD 루프("이 AC를 먼저 실패하는 테스트로 쓴다")를 걸기엔 크다. SPEC은 그 사이의 작업 단위다.
* **`.claude/rules/` 분할이 필요한 이유**: CLAUDE.md §16 Constitutional lock 때문에 §9~§12 같은 실무 체크리스트조차 앞으로 바꾸려면 매번 ADR이 필요하다. 도메인 규칙(무엇이 이 서비스인가)과 코딩 스타일 체크리스트(어떻게 짜는가)는 변경 빈도와 승인 무게가 다르므로 계층을 분리하는 편이 헌법 잠금의 취지(§16 — "함부로 안 바뀐다")를 domain 규칙에 더 정확히 겨냥한다.
* **Notion 폐기가 필요한 이유**: README_AIUSAGE.md 로그 5개 세션 전부가 "Notion drift" 또는 "Notion 원본 갱신 권장"을 잔여 리스크로 반복 기록했다. 실제로 한 번도 반영되지 않은 것으로 보인다(코드베이스에 Notion 갱신 커밋 흔적 없음). 쓰이지 않는 source of truth는 source of truth가 아니다.

## Trade-offs

* SPEC 4파일(spec/plan/tasks/acceptance) 구조는 44개 엔드포인트를 8개 모듈 단위로만 쪼갤 때보다 파일 수가 늘어난다 — 남은 3모듈(M4-6·M4-7·M4-8)에도 이 구조를 쓸지는 M4-5 완료 후 재평가한다(Review Trigger 참조).
* `.claude/rules/`로의 분할은 CLAUDE.md 단일 열람으로 전체 규칙을 볼 수 없게 만든다 — CLAUDE.md 서두(§2 Source of Truth)에 포인터를 명시해 완화한다.
* STATUS.md 갱신을 커밋 규칙으로 못 박으면(§9) 갱신을 잊은 커밋이 CI 없는 이 프로젝트에서는 기계적으로 걸러지지 않는다 — 당분간은 리뷰 시점 수동 확인에 의존한다.

## Consequences

* CLAUDE.md §2(Source of Truth 순서) / §3(트리) / §5(43→44 정정) / §13(문서 규칙에 STATUS.md·specs 언급 추가) / §16(본 ADR이 §2·§3·§5·§9~§13·§17을 supersede함을 명시) / §17(워크플로를 "프롬프트 2 → Active SPEC → TDD 루프"로 교체)이 개정된다. 개정은 본 ADR이 **Accepted**로 전환된 뒤에만 적용한다.
* `docs/00-project/STATUS.md`가 신설되고, 이후 모든 구현 커밋은 이 파일 갱신을 동반해야 한다.
* `specs/SPEC-001-concerns-api/`가 M4-5(api.md #16~25)의 작업 단위로 신설된다.
* `.claude/rules/{coding,security,testing,infrastructure}.md` 4종이 신설되고 CLAUDE.md §9~§12는 포인터로 축약된다.
* Notion은 읽기 전용 아카이브로 강등된다. 신규 결정·기록은 Git(STATUS.md, specs/, ADR, README_AIUSAGE.md)에만 남긴다.

## Validation

* `grep -c "^### [0-9]" docs/api.md`와 STATUS.md의 "구현됨" 목록 항목 수를 대조해 STATUS.md가 실제 `urls.py`를 반영했는지 확인.
* CLAUDE.md 개정 후 `git diff CLAUDE.md`에서 §9~§12 삭제분과 `.claude/rules/*.md` 신규분의 텍스트가 바이트 단위로 동일한지 확인(내용 무변경 원칙).
* SPEC-001의 `tasks.md` 순서대로 M4-5를 구현하면서, 각 TASK 완료 시 STATUS.md의 "구현됨" 번호가 실제로 늘어나는지 확인.

## Review Triggers

* M4-5(SPEC-001) 완료 후: SPEC 4파일 구조가 남은 M4-6~M4-8에도 비용 대비 유효한지 재평가.
* `.claude/rules/` 분할 이후 실제로 그 파일들이 CLAUDE.md 없이 단독 참조되는 빈도가 낮으면 재통합 검토.
* Notion을 다시 쓸 필요(예: 비개발 이해관계자 공유)가 생기면 별도 ADR로 재도입 범위를 정의.

---

**Cross-reference**: `docs/request/3-vscode-migration_prompt.md` §4~§5 (본 ADR의 근거가 된 마이그레이션 플레이북).
