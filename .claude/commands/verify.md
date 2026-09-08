---
description: CLAUDE.md §12 검증 배터리를 실행하고 실제 출력과 함께 통과/실패 표를 만든다
allowed-tools: Bash, Read
---

아래를 순서대로 실행하고, **각 항목의 실제 출력**과 함께 통과/실패 표를 만들어라.

```bash
uv run ruff check .
docker compose ps
docker compose exec app python manage.py check
docker compose exec app python manage.py makemigrations --check --dry-run
docker compose exec app python manage.py test --settings=config.settings.test --keepdb -v 2
curl -i http://localhost:8000/healthz
```

규칙:

* **실행하지 않은 명령은 "권장 명령"으로 표기한다.** 완료로 위장하지 마라 (CLAUDE.md §12).
* 컨테이너가 안 떠 있으면 `docker compose ps`에서 드러난다. 그 다음 항목들은 "미실행 — db/app 미기동"으로 표기하고 넘어가라. **`docker compose up`을 임의로 실행하지 마라** (소유 구역).
* `--settings=config.settings.test`를 빠뜨리지 마라.
* 테스트가 0건이면 "테스트 없음"이 아니라 **"판정 장치 부재"**로 표기하라. 이 프로젝트에서 그것은 결함이다.

표 형식:

| # | 검증 | 결과 | 실제 출력(요약) |
| --- | --- | --- | --- |

실패가 있으면 각각에 대해 원인 가설을 **위치 → 현상 → 원인** 순으로 제시하라.
**고치지는 마라.** 이 명령은 진단 전용이다. Owner가 무엇을 고칠지 정한다.

마지막에 활성 SPEC의 `acceptance.md`를 읽고, 지금 체크할 수 있게 된 항목이 있으면 알려줘라. 파일 수정은 Owner 확인 후에 한다.
