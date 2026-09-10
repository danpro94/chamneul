# chamneul

신뢰 기반 인생 의사결정 조언 플랫폼의 로컬 MVP 백엔드. 사용자가 중요한 고민을 등록하면 조언가가 답하고, 시스템은 조언 품질·결과·책임·신뢰 신호를 시간에 걸쳐 기록한다.

이 저장소는 서비스 코드인 동시에 DevOps/Cloud/Platform 학습 포트폴리오다 — Owner가 직접 설명할 수 있는 수준의 단순함과, 유지보수 가능한 구조를 함께 목표로 한다.

## 목적

* 개발: Django + DRF로 세션 인증 기반 REST API를 로컬 컨테이너에서 완결시킨다 (Phase 2).
* 학습: 요청이 Django에 닿는 경로, 컨테이너 간 통신, 마이그레이션, 장애 대응을 직접 설명할 수 있는 상태를 만든다.

## 스택

Python 3.13 · Django 5.2 · DRF 3.15 · PostgreSQL 16 (Docker Compose) · gunicorn · uv · ruff. 세션 기반 인증(HttpOnly Cookie) 단일 전략 — JWT/Token 미사용. 자세한 기술 결정은 [CLAUDE.md](CLAUDE.md) §4 참조.

## 구조

```text
chamneul/
├── CLAUDE.md              # 프로젝트 헌법 — 스코프·도메인 규칙·승인 게이트
├── .claude/rules/         # CLAUDE.md §9~§12 세부 체크리스트 (coding/security/testing/infrastructure)
├── accounts/ advisors/ concerns/ advice/ notifications/  # 도메인 앱 (Django 관용 구조, src/ 미도입)
├── common/                # 앱 간 공유 유틸 (permissions, pagination, uuid7, taxonomy)
├── config/                # settings(local/test/prod 분리), urls, /healthz
├── docs/
│   ├── api.md             # API 계약 (44 엔드포인트, 단일 파일 유지)
│   ├── model.md            # 데이터 모델 / ERD / 제약
│   ├── adr/                # Architecture Decision Records
│   ├── 00-project/STATUS.md  # 현재 구현 상태 — 세션 시작 시 먼저 읽을 곳
│   ├── testing/TEST_CRITERIA.md
│   └── reviews/             # 마일스톤별 리뷰 노트
├── specs/                  # SPEC 단위 작업 분해 (spec/plan/tasks/acceptance)
└── docker-compose.yml       # app + postgres 로컬 런타임
```

## Quick Start

```bash
cp .env.example .env   # 값 채우기 (CLAUDE.md §10 — .env는 절대 커밋하지 않는다)
docker compose up -d
curl http://localhost:8000/healthz   # {"status": "ok"} 기대
```

리셋: `docker compose down -v` (named volume `pgdata` 포함 삭제 — DB 초기화).

## 문서 지도

| 알고 싶은 것 | 여기로 |
| --- | --- |
| 지금 뭐가 구현돼 있는가 | [docs/00-project/STATUS.md](docs/00-project/STATUS.md) |
| 프로젝트 규칙(스코프·도메인·보안) | [CLAUDE.md](CLAUDE.md) |
| API 계약 | [docs/api.md](docs/api.md) |
| 데이터 모델 | [docs/model.md](docs/model.md) |
| 왜 이렇게 결정했는가 | [docs/adr/](docs/adr/) |
| 완료 판정 기준 | [docs/testing/TEST_CRITERIA.md](docs/testing/TEST_CRITERIA.md) |
| AI 활용 이력 | [README_AIUSAGE.md](README_AIUSAGE.md) |
| 지금 진행 중인 작업 단위 | [specs/](specs/) |

이 파일은 지도다 — 규칙·명세 본문은 위 링크로 이동한다.
