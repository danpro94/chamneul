# CLAUDE.md

## 0. Purpose

This repository is the local MVP backend project for `chamneul`.

The service is a trusted life decision guidance platform where users submit important personal concerns, advisors provide advice, and the system records advice quality, outcomes, responsibility, and trust signals over time.

This project is not just a toy app. It is also a DevOps/Cloud/Platform portfolio project. Code must be simple enough for the Owner to understand and explain, but structured enough to be maintainable and extensible.

The Owner may not be a professional backend developer. Therefore, Claude must optimize for:

* correctness
* maintainability
* explicit reasoning
* operational explainability
* security
* clean local container execution
* useful documentation
* minimal but meaningful MVP scope

---

## 1. Current Phase

Current phase: Phase 2 — Local Container MVP

Goal:
Build and verify the minimum local backend unit before AWS.

Phase 2 completion means:

* Django app runs locally.
* PostgreSQL runs through Docker Compose.
* `/healthz` returns 200 OK.
* Core concern APIs work.
* Django Admin can inspect data.
* Dockerfile exists.
* docker-compose.yml exists.
* README and smoke test docs exist.
* API and model docs are coherent.

Do not jump to AWS, Kubernetes, CI/CD, Terraform, or production architecture unless explicitly requested.

---

## 2. Source of Truth Order

When documents conflict, follow this priority:

1. CLAUDE.md
2. .claude/rules/*.md (§9-§12 split-out detail rules — equal authority to CLAUDE.md; see ADR-006)
3. docs/adr/ (highest-numbered ADR wins on its subject; includes ADR-006)
4. docs/00-project/STATUS.md (sole source of truth for actual implementation status)
5. specs/SPEC-00N-*/ (the Active SPEC's spec/plan/tasks/acceptance)
6. docs/2 mvp-scope_v1.md
7. docs/1 서비스기획_v1.md
8. docs/README.md
9. Notion-exported API specification (read-only archive as of ADR-006 — no longer updated)
10. docs/api.md
11. docs/model.md
12. code

If there is a conflict, do not silently resolve it. Create a short conflict table and ask the Owner for a decision.

> Order revised by ADR-006 (2026-09-10): items 2-5 added, path typos in items 6-8 corrected (`mvp-scope.md`→`mvp-scope_v1.md`, `0 README.md`→`README.md`), Notion demoted to read-only archive.

---

## 3. Current Known Project Tree

> The actual, up-to-date implementation state lives in `docs/00-project/STATUS.md` (ADR-006) — the trees below are the historical 2026-06-22 snapshot and the originally expected layout, kept for context only.

Current root:

```text
chamneul/
└── docs
    ├── 0 README.md
    ├── 1 서비스기획_v1.md
    ├── 2 mvp-scope.md
    ├── adr
    │   └── ADR-001-local-container-architecture.md
    ├── dns-chamneul.com
    │   └── receipt_namecheap-order-domain_260611.pdf
    └── 컨셉추얼 아키텍처_초안.drawio
```

Expected future files:

```text
chamneul/
├── CLAUDE.md
├── README.md
├── README_AIUSAGE.md
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── config/
├── accounts/
├── concerns/
├── advisors/
├── advice/
├── notifications/
├── .claude/rules/           # §9-§12 detail rules (ADR-006)
├── specs/                   # SPEC-00N-*/ work breakdown (ADR-006)
└── docs/
    ├── api.md
    ├── model.md
    ├── smoke-test.md
    ├── reviews/
    ├── adr/
    ├── 00-project/STATUS.md  # implementation status (ADR-006)
    └── testing/TEST_CRITERIA.md
```

Do not create all apps at once unless the Owner requests it. Prefer incremental MVP implementation.

---

## 4. Technology Decisions

Backend:

* Django
* Django REST Framework

Initial API implementation:

* ModelSerializer
* ModelViewSet
* Router-based CRUD where appropriate

Refactoring trigger:

* Use explicit Serializer + APIView + Service Layer when business logic becomes complex.

Database:

* **PostgreSQL 16+ is the only database engine** used at every stage (local, dev, test, prod). SQLite is not used at any stage.
* Rationale: model definitions use PostgreSQL-specific features (`ArrayField`, `JSONB`, UUIDv7, partial unique indexes) from day 1. Maintaining SQLite compatibility would force branching code and risk production-vs-CI schema drift.
* DB adapter: `psycopg[binary] >= 3.1`. The Django test runner must use a PostgreSQL test database (no SQLite in-memory fallback).
* `DATABASES['default']` settings are split per environment (`config/settings/{local,test,prod}.py`) but all point to PostgreSQL.
* Approved PostgreSQL-specific features (use without compatibility excuses):
  * `django.contrib.postgres.fields.ArrayField` — single-type multi-value columns.
  * `models.JSONField` (PostgreSQL JSONB) — unstructured payload.
  * GIN indexes for ArrayField / JSONField search.
  * Partial unique indexes (`UniqueConstraint(..., condition=Q(...))`) — required by the soft-delete pattern in §6.6.
  * App-level UUIDv7 helper for PK generation (1차안). PostgreSQL native `uuidv7()` extension migration is a future option.
  * `select_for_update()` and explicit transaction isolation when concurrency matters.

Local runtime:

* Docker Compose
* app + postgres

Health check:

* `/healthz`

Authentication:

* Session-based (SSR) authentication with HttpOnly Secure Cookie. **Single strategy. JWT / DRF Token / Knox are not used.**
* Local email + password signup/login issues a session and returns Set-Cookie. Signup auto-logs in.
* Google OAuth callback also issues the same session cookie — there is one session model regardless of login method.
* Session cookie policy is defined in ADR-002 (cookie name `sessionid`, HttpOnly, Secure, SameSite=Lax, 14 day expiry, sliding renewal on every request, server-side deletion on logout).
* Do not introduce additional auth packages (JWT, OAuth providers other than Google, SAML, etc.) without a new ADR.

---

## 5. MVP Scope Boundaries

Owner decision (2026-06-22): Phase 2 v1 implements the **full API surface** derived from Notion v0 (41 original − 1 refresh-token removed + `/healthz` + admin-role grant/revoke = 43), **extended to 44 endpoints on 2026-07-08 (D-1)** with the CSRF-bootstrap endpoint (`GET /api/v1/csrf`) — see docs/api.md §3 for the authoritative count (corrected here by ADR-006). Outcome tracking and trust score are the only domain capabilities deferred to a later phase.

In scope for Phase 2:

* `/healthz`
* local account signup / login / logout (Session-based, see §4)
* Google OAuth login (callback issues the same session)
* user profile read / update, role list, active-role switch
* advisor application: submit, my-status, admin list / detail / approve-reject
* concern model: user create / list / detail / delete (under `/users/me/concerns`), advisor assigned list / detail, admin list / detail / assign / unassign
* advice model: create (advisor), update, delete, detail, list (advisor own), received list (concern owner), admin review list, admin approve / reject
* feedback: user submit (1 per advice), my list, admin list / detail / status-change
* notification: user list, detail, mark-read
* admin role: grant (`POST /api/v1/admin/users/{user-id}/roles`) and revoke (`DELETE /api/v1/admin/users/{user-id}/roles/{role}`)
* Django Admin registration for all core models
* PostgreSQL via Docker Compose
* Dockerfile, docker-compose.yml, .env.example
* README, smoke test documentation
* docs/api.md, docs/model.md

Deferred to a later phase (Phase 3+):

* outcome tracking (long-term advice result follow-up)
* trust score algorithm and trust score calculation
* advisor matching algorithm (manual admin assignment is in Phase 2)
* user-driven advisor application withdrawal API (`WITHDRAWN` exists in the model only)

Out of scope for Phase 2 unless explicitly requested:

* AWS
* Kubernetes
* Terraform
* CI/CD
* payment
* production-grade monitoring
* frontend implementation
* AI recommendation engine
* trust score algorithm
* public marketplace

---

## 6. Domain Rules

### 6.1 Advisor Application

`advisor_type` must not be included in the public request form.

Reason:
A user self-reporting “I am an expert” or “I am a wise senior” is not verifiable in the MVP. It creates self-inflation and product trust issues.

`real_name` must not be included in the public request form.

Reason:
In an MVP without audience, revenue, or clear advisor incentives, requiring real-name exposure adds signup friction without clear product benefit.

Advisor application statuses:

* PENDING
* REVIEWING
* APPROVED
* REJECTED
* WITHDRAWN

`WITHDRAWN` may exist in the model even if the cancellation API is deferred.

`intended_lane` policy (Owner decision 2026-06-22):

* `intended_lane` (values: `expert` | `senior`) is kept on the application Request as **applicant-stated intent**, not as a self-assigned grade.
* It is **never** returned in public responses, never displayed to other users, never used as an authorization key.
* It is visible only to admin review tooling and to internal systems for matching telemetry. The admin makes the final lane decision; the applicant's `intended_lane` is reference input only.

### 6.2 Advice

Advice statuses:

* PENDING
* REVIEWING
* APPROVED
* REJECTED
* DELETED

Users can see only APPROVED advice.

### 6.3 Feedback

Feedback statuses:

* SUBMITTED
* REVIEWED
* ARCHIVED

### 6.4 Notifications

Notification creation rules:

* advice approved → notify concern owner
* advice rejected → notify advisor
* advisor application approved → notify applicant
* advisor application rejected → notify applicant
* assignment created → notify advisor

Notification types:

* ADVICE_APPROVED
* ADVICE_REJECTED
* ADVISOR_APPLICATION_APPROVED
* ADVISOR_APPLICATION_REJECTED
* ASSIGNMENT_CREATED

Before implementing notifications, verify whether the notification target described in the API spec matches this section. If there is a conflict, ask the Owner.

### 6.5 Concern Taxonomy v0

Allowed taxonomy keys:

* career_transition
* job_change
* burnout
* startup_failure
* leadership
* relationship
* life_direction
* major_life_decision
* education_choice
* relocation
* finance_major_decision

Korean labels:

* career_transition: 경력 전환
* job_change: 직종 전환
* burnout: 번아웃
* startup_failure: 사업 실패
* leadership: 리더십
* relationship: 관계
* life_direction: 인생 방향성(설계)
* major_life_decision: 인생의 중요한 의사결정
* education_choice: 학업 선택
* relocation: 이사
* finance_major_decision: 중요한 재무 의사결정

Do not invent additional taxonomy values without approval.

### 6.6 Concern Status

Concern statuses (Owner decision 2026-06-22):

* SUBMITTED
* ASSIGNED
* ANSWERED
* CLOSED

Transitions:

* SUBMITTED: user created the concern; no advisor assigned yet.
* SUBMITTED → ASSIGNED: admin attaches one or more advisors via `POST /api/v1/admin/concerns/{concern-id}/assignments`.
* ASSIGNED → ANSWERED: at least one `APPROVED` advice is attached.
* ANSWERED → CLOSED: user closes the concern explicitly (or admin closes after a policy timeout).
* ASSIGNED → SUBMITTED: every assignment for the concern has been removed (unassign returns the concern to the pre-assignment state).

Soft delete (project-wide convention):

* The user's "delete my concern" action is a **soft delete** recorded as `deleted_at = timezone.now()`, not a status transition. Column definition: `deleted_at = models.DateTimeField(null=True, blank=True, default=None)`. Active record predicate: `deleted_at IS NULL`.
* Soft-deleted concerns are excluded from all non-admin queries via the default manager (`Concern.objects` filters `deleted_at__isnull=True`). Admin/audit access uses `Concern.objects.with_deleted()`. Existing advice / assignment rows are preserved.
* `deleted_at` (not boolean `is_deleted`) is the project-wide convention so the audit timestamp is preserved in the same column. Any future model that adopts soft delete must use the same column name and type.
* **Soft delete + unique constraint must always be a partial unique index** with `WHERE deleted_at IS NULL`. A plain `unique=True` on a column of a soft-delete model is forbidden — code review rejects it. Example failure mode: a withdrawn user's email blocking a new signup with the same address.
  ```python
  class Meta:
      constraints = [
          models.UniqueConstraint(
              fields=["<unique_field>"],
              condition=Q(deleted_at__isnull=True),
              name="<table>_<field>_unique_active",
          ),
      ]
  ```
* In Phase 2 v1, only `Concern` uses soft delete. Other models (`User`, `Advice`, etc.) express lifecycle via dedicated `status` or `is_active` columns.

### 6.7 Advice Versioning

`advice.version` is an audit-only integer (Owner decision 2026-06-22):

* Starts at 1 on create.
* `+1` on every advice update by the advisor (only allowed in `PENDING` / `REVIEWING` states).
* Exposed in API responses so the advisor can see their iteration history.
* A separate audit table (advice history) preserves prior body content per version. The audit table is not exposed as a public API in Phase 2.

---

## 7. API Design Rules

URI rules:

* All versioned APIs use the `/api/v1/` prefix. `/healthz` is the only unversioned endpoint.
* Do not include trailing slash.
* Use hyphen instead of underscore in URI segments and in path-parameter placeholder names.
* Use nouns, not verbs.
* Use lowercase.
* Do not include file extensions.
* User-owned resources are addressed under `/api/v1/users/me/{resource}` for both list and detail (Owner decision 2026-06-22). Admin views of the same resource live under `/api/v1/admin/{resource}`.

Examples:

Good:

* `/healthz`
* `/api/v1/users/me/concerns`
* `/api/v1/users/me/concerns/{concern-id}`
* `/api/v1/admin/concerns/{concern-id}/assignments`
* `/api/v1/advisor-applications`
* `/api/v1/notifications`

Bad:

* `/api/createConcern`
* `/api/concern_list`
* `/api/concerns/`
* `/api/get-advice`
* `/api/concerns.json`
* `/api/v1/concerns/{concern_id}` (path-parameter placeholder uses underscore — write as `{concern-id}`)

API review must check:

* REST resource naming
* method correctness
* status code correctness
* permission model
* access control
* request field necessity
* response field exposure
* state transition validity
* MVP scope fit
* duplicate endpoint responsibility
* hidden business logic contradiction

---

## 8. Response Design Rules

Do not expose sensitive fields.

Do not blindly return all model fields through ModelSerializer.

For each API, response fields must be intentionally chosen.

For list APIs:

* return only fields needed for list display
* avoid large text fields unless required
* consider pagination

For detail APIs:

* include full resource details as needed
* apply access control before serialization

For nested relationships:

* check N+1 query risk
* use select_related or prefetch_related when appropriate
* avoid uncontrolled nested serialization

---

## 9. Coding Rules

See [.claude/rules/coding.md](.claude/rules/coding.md) (moved verbatim by ADR-006 — equal authority to this document; no rule changed).

---

## 10. Security Rules

See [.claude/rules/security.md](.claude/rules/security.md) (moved verbatim by ADR-006 — equal authority to this document; no rule changed).

---

## 11. DevOps and Local Runtime Rules

See [.claude/rules/infrastructure.md](.claude/rules/infrastructure.md) (moved verbatim by ADR-006 — equal authority to this document; no rule changed).

---

## 12. Testing and Validation Rules

See [.claude/rules/testing.md](.claude/rules/testing.md) (moved verbatim by ADR-006 — equal authority to this document; no rule changed). Automated judgment criteria: [docs/testing/TEST_CRITERIA.md](docs/testing/TEST_CRITERIA.md).

---

## 13. Documentation Rules

Documentation is part of the deliverable.

Maintain:

* README.md
* README_AIUSAGE.md
* docs/api.md
* docs/model.md
* docs/smoke-test.md
* docs/adr/
* docs/reviews/
* docs/00-project/STATUS.md (ADR-006) — every implementation commit must update this file
* specs/SPEC-00N-*/ (ADR-006) — the Active SPEC's spec/plan/tasks/acceptance

After meaningful AI-assisted work, update or remind the Owner to update README_AIUSAGE.md.

README_AIUSAGE.md should include:

* date
* task
* AI tool used
* human decision
* generated artifact
* verification result
* remaining risk

---

## 14. Review Session Rule

For each meaningful module or code task, create a short review note under docs/reviews/.

Review note should include:

* what changed
* why it was implemented this way
* key files
* how to test
* DevOps explanation point
* security note
* next improvement

Keep each review concise. Avoid excessive token use.

---

## 15. Interaction Protocol

Before editing:

1. read relevant files
2. summarize current state
3. propose a short plan
4. identify required decisions
5. ask only necessary questions

During editing:

1. work in small steps
2. avoid broad unrelated changes
3. preserve existing project intent
4. explain non-obvious decisions

After editing:

1. list changed files
2. summarize behavior change
3. provide validation commands
4. state what was verified and what was not
5. note risks or follow-up tasks

---

## 16. Approval Gates

Ask for Owner confirmation before:

* changing API resource names
* changing status values
* changing authentication strategy
* adding third-party packages
* changing database choice
* deleting files
* overwriting exported Notion content
* introducing AWS, Kubernetes, Terraform, or CI/CD
* changing MVP scope
* exposing personal data fields

No confirmation is needed for:

* formatting markdown
* adding missing documentation sections
* minor typo fixes
* adding validation checklists
* adding safe TODOs

Constitutional lock (Owner directive):

* This CLAUDE.md is the project constitution. The 2026-06-22 alignment session and the 2026-06-26 model alignment session are the only authorized in-place edit windows. After 2026-06-26 ends, **CLAUDE.md is frozen** — changes happen only through a new ADR that explicitly supersedes the affected clause. A future Claude session must never edit CLAUDE.md directly; it must read it as ground truth and propose an ADR if it disagrees.
* The 2026-06-26 edit explicitly absorbed the SQLite-exclusion rule (§4) and the `deleted_at` soft-delete convention with partial-unique enforcement (§6.6) directly into CLAUDE.md, so no separate supersession ADR is required for these clauses.
* ADR-006 (AI-Native / Spec-Driven skeleton, Accepted 2026-09-10) explicitly supersedes §2 (Source of Truth Order), §3 (Current Known Project Tree), §5 (endpoint count 43→44), §9-§12 (split into `.claude/rules/*.md`), §13 (STATUS.md/specs maintenance added), and §17 (workflow replaced) per the process this section requires. The edits are applied verbatim from ADR-006's Consequences section.

---

## 17. Session Workflow

> Replaced by ADR-006 (2026-09-10). The original bootstrap workflow (read docs → reconcile Notion v0 → produce api.md/model.md) is complete history — see README_AIUSAGE.md 2026-06-22/06-26 entries. It no longer applies to new sessions.

Every session start:

1. Read CLAUDE.md → README.md → docs/00-project/STATUS.md.
2. Read the Active SPEC (specs/SPEC-00N-*/) and its related ADR/api.md sections only.
3. Do not modify code yet. Report: (1) project purpose (2) current Active SPEC (3) that SPEC's completion criteria (4) related Architecture Decisions (5) actual implementation state, from code (6) anything uncertain or conflicting (7) the next minimum unit of work.
4. Implement one SPEC TASK at a time, test-first: write the acceptance.md AC as a failing Django test → minimal implementation (state transitions/side effects in services.py, access control in common/permissions.py + object-level checks) → run check/makemigrations --check/ruff/test and show the actual output → commit (message includes the SPEC/TASK id) → update STATUS.md → add one README_AIUSAGE.md entry → stop for Owner confirmation before the next TASK.
5. Dockerfile / docker-compose* / .env* remain untouchable without explicit Owner approval (§16). Never edit a test or its AC just to make it pass.
