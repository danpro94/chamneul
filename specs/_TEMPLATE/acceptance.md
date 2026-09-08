# SPEC-NNN — Acceptance Criteria

> **이 파일이 커버리지 리포트다** (`docs/testing/TEST_CRITERIA.md` §8).
> 각 항목에 검증하는 테스트 경로를 적는다. 경로가 없는 체크는 체크가 아니다.

- [ ] **AC-001** <조건>
      `tests/integration/test_xxx.py::Class::test_name`
- [ ] **AC-002**
- [ ] **AC-003**

## 검증 명령

```bash
docker compose exec app python manage.py test --settings=config.settings.test --keepdb -v 2
uv run ruff check .
docker compose exec app python manage.py check
docker compose exec app python manage.py makemigrations --check --dry-run
```

실측 출력은 `evidence/`에 남긴다.
