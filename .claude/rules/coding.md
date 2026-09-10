# Coding Rules

> CLAUDE.md §9에서 원문 그대로 이동 (ADR-006). 내용 변경 없음 — CLAUDE.md와 동등한 효력을 가진다.

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
