# chamneul

> 신뢰할 수 있는 인생 의사결정 가이드 서비스 — Phase 2 로컬 컨테이너 MVP 백엔드

---

## 🤖 AI 세션 시작 규칙

새 Claude Code 세션(VS Code Extension / CLI)은 **거대 프롬프트를 붙여넣지 않는다.** 저장소가 곧 컨텍스트 시스템이다.

읽기 순서:

1. `.claude/rules/00-source-of-truth.md` — SessionStart 훅이 자동 주입한다
2. `README.md` (이 문서)
3. `docs/00-project/STATUS.md` — 지금 어디까지 왔는가
4. 활성 SPEC의 `spec.md` + `acceptance.md`
5. 필요한 ADR / `docs/api.md` / `docs/model.md`의 **해당 절만**

> ⚠️ `CLAUDE.md` §2 · §3 · §17은 **`docs/adr/ADR-005`로 대체되었다.** 특히 §2의 "Notion-exported API specification"은 은퇴했다 — `docs/api.md`가 정본이다. §17 step 6 "Notion export 대기"는 무시한다. 나머지 조항, 특히 **§6 도메인 규칙 전체는 무수정 유효**하다.

첫 세션 온보딩 절차는 `docs/00-project/VSCODE_MIGRATION_PLAYBOOK.md` Step 4에 프롬프트 전문이 있다.

---

## 무엇을 만드는가

사용자가 인생의 중요한 고민을 제출하면, 검토를 거쳐 배정된 조언가가 조언을 작성하고, 관리자 승인을 거쳐 사용자에게 전달되는 백엔드다. 조언의 품질·결과·책임·신뢰 신호를 시간에 걸쳐 기록하는 것이 장기 목표다.

**해결하려는 문제**: "나를 이해하는 현명한 어른"의 부재. 정보가 부족한 것이 아니라, 신뢰할 수 있고 나에게 맞게 압축된 조언(사람)이 부족하다. 레거시 인적 네트워크가 줄어들면서 서민·중산층·주니어가 특히 그렇다.

**차별점**: AI가 아니라 **사람의 조언**이 근간이다. AI는 기록·정리·매칭 브릿지 등 보조 역할에 한정한다. 정답을 제시하지 않고 스스로 생각하는 과정을 돕는다.

배경 전체는 `docs/1 서비스기획_v1.md` (공개 요약본), 전략 IP 분리 근거는 `docs/adr/ADR-004`.

## 누가 사용하는가

| 역할 | 할 수 있는 것 |
| --- | --- |
| **Anonymous** | 회원가입, 로그인, Google OAuth 시작 |
| **User** | 고민 작성·조회·삭제, 받은 조언 조회(승인된 것만), 피드백 작성, 조언가 신청 |
| **Advisor** | `USER` + ADVISOR 역할 보유자. 활성 역할 전환 후 배정된 고민 조회, 조언 작성 |
| **Admin** | 조언가 신청 심사, 고민 배정, 조언 승인, 피드백 관리, 역할 부여·회수 |

사용자는 여러 역할을 동시에 보유할 수 있다. `active_role`(USER ↔ ADVISOR)이 현재 전환 상태를 가리키고, ADMIN은 전환 없이 항상 적용된다.

## 핵심 기능 (Phase 2 범위)

고민 제출·조회·소프트 삭제 · 관리자 배정 · 조언 작성·수정·검토·승인 · 승인된 조언 열람 · 피드백 · 알림 · 조언가 신청·심사 · 세션 인증(로컬 + Google OAuth) · 역할 관리 — **총 43 엔드포인트**.

**Phase 3 이후로 미룬 것**: outcome tracking, 신뢰 점수 알고리즘, 조언가 매칭 알고리즘, 결제, 공개 마켓플레이스, AWS·EKS·Terraform·CI/CD.

## Architecture 요약

```
Browser
  │  HTTP (localhost:8000)
  ▼
docker compose network ("chamneul_default")
  ├── app   : Django 5.2 + DRF  ─┐
  │           dev  = runserver   │  DB_HOST=db, DB_PORT=5432
  │           prod = gunicorn ×3 │  (서비스명 DNS)
  │           non-root uid 10001 │
  └── db    : postgres:16       ◄┘  named volume "pgdata"
              host 15432 → 5432     healthcheck: pg_isready
```

요청 경로: `Browser → gunicorn/runserver → Django 미들웨어 → DRF View → ORM → psycopg → PostgreSQL`.

`/healthz`는 **liveness**만 본다 — DB를 건드리지 않으므로 "앱은 살아 있으나 DB가 죽은" 상태를 잡지 못한다. 이 한계는 의도된 것이고 readiness 엔드포인트는 후속 과제다. 상세는 `docs/adr/ADR-001`.

## Tech Stack

| 계층 | 선택 | 근거 |
| --- | --- | --- |
| 언어 | Python 3.13 | `.python-version` |
| 프레임워크 | Django 5.2 + DRF 3.17 | ADR-001 |
| DB | **PostgreSQL 16 전용** (SQLite 미사용, 전 단계) | CLAUDE.md §4 |
| DB 어댑터 | `psycopg[binary]` ≥ 3.1 | 〃 |
| PK | UUIDv7 (앱 레이어 생성, `common/uuid7.py`) | RDS/Aurora 동작 동일성 |
| 인증 | **Session 단일 전략** (HttpOnly Secure Cookie). JWT·Token·Knox 미사용 | ADR-002 |
| 패키지 관리 | uv (lockfile 커밋) | — |
| 린터 | ruff (line-length 100, `E,F,I,UP,DJ`) | — |
| 테스트 | **Django 기본 test runner + DRF `APITestCase`.** pytest 미도입 | Owner 결정 G5 |
| 런타임 | Docker Compose (app + db) | ADR-001 |

PostgreSQL 전용인 이유: `ArrayField`, JSONB, 부분 유니크 인덱스를 1일차부터 쓴다. SQLite 호환을 유지하면 코드가 분기되고 CI–운영 스키마가 어긋난다.

## Repository 구조

```
chamneul/
├── CLAUDE.md                  AI 행동 규칙 (헌법 · 동결 · ADR로만 개정)
├── README.md                  이 문서 — 지도
├── README_AIUSAGE.md          AI 활용 대장 (현행)
├── manage.py  pyproject.toml  uv.lock  .python-version
├── Dockerfile  docker-compose.yml  docker-compose.override.yml  .env.example
│
├── config/                    settings 4분할(base/local/test/prod), urls, health, wsgi
├── common/                    uuid7, taxonomy — 앱 간 공유 (앱끼리 직접 import 금지)
├── accounts/                  User, UserRole, RoleGrant, GoogleIdentity
├── advisors/                  AdvisorApplication
├── concerns/                  Concern(소프트 삭제), Assignment
├── advice/                    Advice, AdviceHistory, Feedback
├── notifications/             Notification
│
├── specs/                     기능 명세 — 하나의 SPEC = 하나의 작업 단위
│   └── SPEC-NNN-<slug>/       spec · plan · tasks · acceptance · handoff · evidence/
│
└── docs/
    ├── 00-project/            STATUS · PROJECT_CONTEXT · GLOSSARY
    │                          DECISION_INDEX · LEARNING_DEBT
    │                          VSCODE_MIGRATION_PLAYBOOK · AWS_ASSIGNMENT_BRIEF
    │                          DECISION_ARCHIVE_2026-06
    ├── adr/                   ADR-001~005 — 아키텍처 의사결정
    ├── api.md                 43 엔드포인트 계약 (정본)
    ├── model.md               데이터 모델 + ERD (정본)
    ├── testing/               TEST_CRITERIA — 완료 판정 기준
    ├── reviews/               마일스톤 정의 · 리뷰 노트
    ├── learning/              운영 모델 · 개념 노트
    ├── ux/                    화면 흐름 + API-to-screen 매핑
    ├── request/               과거 생성 프롬프트 아카이브
    └── _private/              전략 IP (gitignore · ADR-004)
```

## Quick Start

전제: Docker Desktop, [uv](https://docs.astral.sh/uv/).

```bash
# 1. 환경 변수
cp .env.example .env          # DJANGO_SECRET_KEY 등을 채운다. .env는 절대 커밋하지 않는다

# 2. 기동 (기본 up = dev 경로, override가 runserver로 덮어쓴다)
docker compose up -d
docker compose ps             # db: healthy, app: running 확인

# 3. 헬스 체크
curl -i http://localhost:8000/healthz        # 200 OK

# 4. 마이그레이션 + 관리자 계정
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser   # 첫 ADMIN 부트스트랩 (ADR-003)

# 5. Django Admin
open http://localhost:8000/admin/            # 모델 11종 조회
```

**운영 형태(gunicorn)로 띄우려면** override를 빼고 실행한다. 정적 파일 서빙이 없어 `/admin` CSS가 404가 되는 것은 알려진 제약이다.

```bash
docker compose -f docker-compose.yml up -d
```

**호스트 포트**: 앱 8000, DB **15432**(→ 컨테이너 5432). 5432를 그대로 쓰면 로컬 PostgreSQL과 충돌하므로 의도적으로 옮겼다.

**로컬 DB 초기화**는 `docker compose down -v`로 named volume을 지운다. **데이터가 전부 사라진다** — 실행 전 반드시 확인한다.

## 검증 명령

```bash
uv run ruff check .
docker compose exec app python manage.py check
docker compose exec app python manage.py makemigrations --check --dry-run
docker compose exec app python manage.py showmigrations
docker compose exec app python manage.py test --settings=config.settings.test -v 2
```

Claude Code 세션에서는 `/verify`가 위 배터리를 한 번에 실행하고 실제 출력과 함께 통과/실패 표를 만든다.

## 주요 문서

| 알고 싶은 것 | 문서 |
| --- | --- |
| 지금 어디까지 왔나, 다음에 뭘 하나 | `docs/00-project/STATUS.md` |
| VS Code로 어떻게 옮기고 개발을 이어가나 | `docs/00-project/VSCODE_MIGRATION_PLAYBOOK.md` |
| API 계약 43개 | `docs/api.md` |
| 데이터 모델 · ERD | `docs/model.md` |
| 왜 이렇게 결정했나 | `docs/adr/` · `docs/00-project/DECISION_INDEX.md` |
| 도메인 용어가 무슨 뜻인가 | `docs/00-project/GLOSSARY.md` |
| 언제 "완료"인가 | `docs/testing/TEST_CRITERIA.md` |
| AI를 어떻게 썼나 | `README_AIUSAGE.md` |
| Owner와 AI의 역할 분담 | `docs/learning/02-ai-collaboration-and-ownership-strategy.md` |

## 소유 구역 (AI 수정 금지)

`Dockerfile` · `docker-compose*.yml` · `.env*` 는 Owner가 직접 작성하는 구역이다. AI는 **제안과 리뷰만** 하고 수정하지 않는다. 근거는 `docs/learning/02` §2.1 — 이 산출물들은 DevOps 면접 화이트보드에 나오는 것들이고, Owner가 백지에서 재현할 수 있어야 한다.

## 라이선스 / 상태

Phase 2 진행 중인 개인 포트폴리오 프로젝트다. 공개 저장소지만 전략 IP 상세는 분리되어 있다 (ADR-004).
