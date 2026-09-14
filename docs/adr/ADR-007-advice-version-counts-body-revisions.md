# ADR-007. `advice.version`은 본문 개정만 센다 (CLAUDE.md §6.7 supersede)

## Status

Accepted (2026-09-14)

## Date

2026-09-14

## Context

CLAUDE.md §6.7은 `advice.version`을 이렇게 규정한다:

> * `+1` on **every advice update by the advisor** (only allowed in `PENDING` / `REVIEWING` states).

SPEC-002(M4-6) 구현 중, api.md #29의 요청 필드에 `submit`(초안↔제출 토글)이 있다는 사실이 이 문구와 충돌한다는 점이 드러났다. `submit`만 뒤집는 PATCH도 "advisor의 update"이므로, 문구를 문자 그대로 읽으면 **본문이 한 글자도 바뀌지 않았는데 `version`이 +1되고 `AdviceHistory`에 직전 본문과 동일한 스냅샷이 한 행 더 쌓인다.**

2026-09-11 Owner 결정(SPEC-002 spec.md §7-2)은 "본문 필드가 실제로 바뀔 때만 +1"로 확정했고, 구현·api.md·테스트가 모두 그에 맞춰져 있다.

문제는 **절차**다. CLAUDE.md §16 constitutional lock은 2026-06-26 이후 CLAUDE.md 변경을 "해당 조항을 명시적으로 supersede하는 새 ADR"로만 허용한다. SPEC 결정과 api.md 수정만으로 §6.7의 규범을 바꾼 셈이라, **코드가 헌법을 앞서 있는 상태**가 되었다. 이 충돌은 2026-09-13 `api-architect` 서브에이전트 리뷰가 지적했다.

본 ADR은 그 절차적 공백을 메운다.

## Decision

CLAUDE.md §6.7의 두 번째 항목을 다음으로 **supersede**한다.

| | 문구 |
| --- | --- |
| 기존 (2026-06-22) | `+1` on every advice update by the advisor (only allowed in `PENDING` / `REVIEWING` states). |
| 신규 (본 ADR) | `+1` **when an advice update changes a body field** (`directional_guidance`, `reflective_questions`, `considerations`, `out_of_scope_flag`) — updates that only toggle the `submit`/`is_submitted` workflow flag do not increment it. Updates are still allowed only in `PENDING` / `REVIEWING` states. |

`AdviceHistory` 스냅샷도 같은 조건을 따른다 — 본문이 바뀔 때만 직전 본문이 한 행으로 보존된다.

§6.7의 나머지 세 항목(생성 시 1에서 시작 / API 응답 노출 / audit 테이블 비공개)은 변경 없다.

## Rationale (Why)

* **`version`의 정의가 "본문 이력 카운터"다.** §6.7 스스로 "A separate audit table (advice history) preserves prior body content **per version**"이라고 쓴다. 본문이 동일한 두 버전이 존재하면 이 문장이 성립하지 않는다 — 같은 내용의 스냅샷이 버전 번호만 다르게 중복된다.
* **`submit` 토글은 워크플로 상태 전환이지 개정이 아니다.** 초안을 제출로 바꾸는 행위는 `is_submitted` 플래그 하나가 담당하며(SPEC-002 spec.md §4), 조언가가 쓴 내용은 그대로다. 여기에 버전을 매기면 조언가의 "몇 번 고쳤나"라는 정보가 왜곡된다.
* **낙관적 잠금(#33 `expected_version`)의 신뢰도와 직결된다.** 관리자가 리뷰 중 412를 받는 것은 "내가 본 이후 조언가가 **내용을 고쳤다**"는 신호여야 의미가 있다. 제출 토글만으로 412가 발생하면 관리자는 바뀐 것이 없는 조언을 다시 읽게 되고, 결국 412를 무시하게 된다 — 방어 장치가 소음이 되면 방어가 아니다.
* **원복 비용이 더 크다.** 2026-09-11 결정 이후 구현·api.md #29·테스트(`test_update_submit_only_does_not_bump_version_or_snapshot`)가 일관되게 새 규칙을 따르고 있다. 원복하면 위 세 근거를 그대로 되살리는 대신 얻는 것이 없다.

## Trade-offs

* `version`이 더 이상 "advisor가 PATCH를 호출한 횟수"가 아니므로, 제출/회수를 반복한 이력은 `version`만으로 추적되지 않는다. Phase 2에서 이 정보를 요구하는 요건은 없다(`is_submitted`의 현재 값만 쓰인다).
* 본문 변경 판정은 "제출된 값이 기존 값과 다른가"의 필드 단위 비교다. 공백만 바꾸거나 같은 값을 다시 보내는 요청은 개정으로 세지 않는다 — 의도된 동작이지만, 클라이언트가 전체 폼을 매번 전송하는 구현이라면 사용자가 "수정했는데 버전이 안 올랐다"고 느낄 수 있다. 프론트엔드 착수 시 재확인 대상.

## Consequences

* **CLAUDE.md §6.7 두 번째 항목이 본 ADR의 문구로 교체된다.** §16 constitutional lock이 요구하는 절차를 이 ADR이 충족하며, §16에 본 supersession을 기록한다.
* 구현(`advice/services.py::update_advice`)·명세(api.md #29)·테스트는 이미 본 결정과 일치하므로 **코드 변경이 발생하지 않는다.** 본 ADR은 규범을 구현에 맞추는 문서 작업이다.
* 향후 `version` 의미를 바꾸려면 다시 ADR이 필요하다.

## Validation

* `grep -n "version" CLAUDE.md` — §6.7 문구가 본 ADR과 일치하는지 확인.
* `advice/tests.py::AdviceUpdateTests::test_update_submit_only_does_not_bump_version_or_snapshot` — 제출 토글 시 `version` 불변, `AdviceHistory` 행 미생성.
* `advice/tests.py::AdviceUpdateTests::test_update_body_change_bumps_version_and_snapshots_previous_body` — 본문 변경 시 `version` +1, 직전 본문이 직전 버전 번호로 스냅샷.

## Review Triggers

* 프론트엔드가 전체 폼 전송 방식을 택해 "변경 없는 재전송"이 흔해지면, 본문 비교 기준(공백 정규화 등)을 재검토.
* `AdviceHistory`를 공개 API로 노출하게 되면(현재 §6.7상 Phase 2 비공개), 버전 번호가 사용자에게 보이므로 의미 재확인.

---

**Cross-reference**: `specs/SPEC-002-advice-api/spec.md` §7-2 (2026-09-11 Owner 결정), `docs/api.md` #29, 2026-09-13 `api-architect` 리뷰 Conflict Table 1행.
