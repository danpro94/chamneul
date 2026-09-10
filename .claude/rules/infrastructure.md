# DevOps and Local Runtime Rules

> CLAUDE.md §11에서 원문 그대로 이동 (ADR-006). 내용 변경 없음 — CLAUDE.md와 동등한 효력을 가진다.

The Owner must be able to explain:

* how a request reaches Django
* how Django connects to PostgreSQL
* how environment variables are loaded
* how containers communicate
* what happens when DB is unavailable
* how /healthz is used
* how migration is applied
* how logs are checked
* how to reset local DB safely

Docker rules:

* app and db must be separate services
* postgres data must use named volume
* host port conflicts must be documented
* .dockerignore must exist
* Dockerfile must be minimal and readable
* docker-compose.yml must be understandable by a junior DevOps learner

Do not introduce Kubernetes before local Compose is stable.
