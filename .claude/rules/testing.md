# Testing and Validation Rules

> CLAUDE.md §12에서 원문 그대로 이동 (ADR-006). 내용 변경 없음 — CLAUDE.md와 동등한 효력을 가진다.
> 실행 판정 기준의 구체화는 [docs/testing/TEST_CRITERIA.md](../../docs/testing/TEST_CRITERIA.md) 참조.

Every code change must include at least one validation method.

Possible validation:

* python manage.py check
* python manage.py test
* python manage.py makemigrations --check
* python manage.py migrate
* curl /healthz
* curl API create/list/detail
* Django Admin verification
* docker compose up
* docker compose ps
* docker compose logs

When a command is not executed, state it as "recommended command," not as completed work.
