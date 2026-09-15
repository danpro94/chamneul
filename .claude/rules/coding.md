# Coding Rules

> CLAUDE.md §9에서 원문 그대로 이동 (ADR-006). 내용 변경 없음 — CLAUDE.md와 동등한 효력을 가진다.
> 2026-09-14: §상태 전이 함수 규칙 추가 (CLAUDE.md 본문 조항이 아닌 이 파일 고유 규칙 — §16 잠금 대상 아님).

## 상태 전이 함수 규칙 (2026-09-14 신설)

**리소스의 상태나 소유권을 바꾸는 서비스 함수는 예외 없이 다음 셋을 갖춘다.**

1. **`transaction.atomic()`** — 상태 전이와 그 부수효과(알림·감사행·연쇄 전이)를 한 단위로 묶는다.
2. **`select_for_update()`로 대상 행을 다시 읽는다** — 호출자가 건네준 객체를 믿지 않는다. 조인된 행까지 잠그지 않도록 `of=("self",)`를 쓴다.
3. **`save(update_fields=[...])`** — 그 함수가 바꿀 권한이 있는 컬럼만 명시한다.

### 왜 (실제로 일어난 일)

이 규칙은 2026-09-13 서브에이전트 리뷰와 2026-09-14 후속 점검에서 **같은 결함이 3개 앱에서 반복된 뒤** 만들어졌다.

* `advice.update_advice` — 잠금 없이 읽고 `save()`에 `update_fields`가 없어, 조언가의 수정이 **관리자의 반려를 통째로 되돌렸다**(반려 사실·사유·반려자 소멸). 데이터 손실.
* `advisors.review_application` — 호출자가 건넨 스냅샷으로 전이를 검사해, 동시 승인 시 **`RoleGrant` 감사 행과 알림이 2건씩** 생겼다. ADR-003 §3이 세운 감사 추적이 오염.
* `concerns.soft_delete_concern` — 잠금 없는 검사-후-쓰기. 결과는 멱등이라 피해는 없으나 409 가드가 신뢰할 수 없다(기록만, 미수정).

### 자주 틀리는 지점

* **낙관적 잠금(`expected_version`)은 한쪽만 지킨다.** 관리자를 오래된 *읽기*로부터 지켜도, 관리자의 *결정*을 다른 주체의 오래된 *쓰기*로부터는 지키지 못한다. 두 방향을 각각 따져라.
* **`save()`의 기본 동작은 전 컬럼 UPDATE다.** 인스턴스가 오래됐다면 그 오래된 값 전부를 쓴다. `update_fields`는 성능 최적화이기 이전에 **권한 경계**다.
* **soft delete는 FK 역방향 조회에 자동 적용되지 않는다.** `Concern.objects`가 삭제 행을 감춰도 `Advice.objects.filter(concern__author=...)`는 base manager를 타 그대로 통과한다.

---

Code must be clean, boring, maintainable, and explainable.

Follow these rules:

* Prefer small, cohesive modules.
* Avoid spaghetti code.
* Avoid magic numbers.
* Avoid premature abstraction.
* Avoid unnecessary cleverness.
* Use meaningful names.
* Keep comments sparse and useful.
* Add comments only for intent, side effects, security concerns, non-obvious logic, TODO, or FIXME.
* Do not hide business rules deep inside serializers without explanation.
* Do not implement broad features in one huge patch.
* Do not create files unrelated to the current task.

When using DRF:

* ModelViewSet is allowed for simple CRUD.
* Use custom permissions for access control.
* Use explicit serializers for different actions when list/detail/create responses differ.
* Consider service functions for business actions.
* Consider database transactions for multi-write operations.
* Avoid N+1 queries.
