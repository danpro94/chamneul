---
spec: SPEC-NNN
title:
prd: docs/2 mvp-scope_v1.md
endpoints: []          # docs/api.md §3 요약표 번호
routing: 위임           # 소유 | 위임 | 읽기 — docs/learning/02 §2.0
adr: []
status: draft          # draft | approved | in-progress | done
---

# SPEC-NNN: <기능명>

## 1. Intent

이 기능은 정확히 무엇을 해결하는가? 한 문단.

## 2. Preconditions

* 사전조건 1
* 사전조건 2

## 3. Functional Behavior

### 시나리오 1 — <이름>

**GIVEN** …
**WHEN** …
**THEN** …
**AND** …

## 4. Inputs

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |

## 5. Outputs

| 필드 | 타입 | 설명 |
| --- | --- | --- |

**응답에 포함하지 않는 것**: (민감 필드를 명시적으로 나열)

## 6. Error Behavior

| 조건 | 상태 | `error.code` |
| --- | --- | --- |

## 7. Invariants

절대 깨져서는 안 되는 조건.

## 8. Security Requirements

`.claude/rules/30-security.md` 기준. 이 SPEC에 특히 걸리는 항목만.

## 9. Acceptance Criteria

자동 테스트로 판정 가능한 형태로 쓴다. "잘 동작한다"는 AC가 아니다.

* **AC-001** …
* **AC-002** …

## 10. Non-Goals

이번 SPEC에서 **하지 않는 것**. 범위를 지키는 장치다.

## 11. Open Questions

| # | 질문 | 출처 | 상태 |
| --- | --- | --- | --- |

## 12. Definition of Done

- [ ] Acceptance Criteria 전부 충족 (`acceptance.md` 체크박스)
- [ ] 테스트 통과 (실측 출력이 `evidence/`에 있음)
- [ ] `ruff check` · `manage.py check` · `makemigrations --check` 통과
- [ ] 관련 문서 갱신 (`docs/api.md` 변경 시)
- [ ] 필요한 ADR 반영
- [ ] `handoff.md` 작성 (explain-first 순서)
- [ ] `docs/00-project/STATUS.md` 갱신
