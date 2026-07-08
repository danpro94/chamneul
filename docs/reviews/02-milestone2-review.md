# M2 리뷰 노트 — 런타임 승격(소유) + accounts 확장(위임)

> §14 리뷰 노트 + learning/02 §6 explain-first. 정의 문서: `02-milestone2-definition.md`.
> 작성일 2026-07-07. 커밋: `156ded9`(트랙 A) · `76b664e`(트랙 B) · `8b2c0f8`(docs).

## Owner 선요약 (AI 노트 읽기 전, 기억만으로 — 원문 그대로 보존)

> 지난 M2에서는 [소유] Dockerfile의 멀티스테이지 분리 구현(builder, runtime)과
> docker-compose.yml(prod)과 docker-compose.override.yml(dev) 분리를 통해
> 각각 gunicorn(wsgi) 로컬 운영 환경으로, dev에서는 manage.py runserver로 로컬 환경을 분기했다.
> 추후 EKS를 고려하여 Worker="3"을 두었고, migrate를 통해 운영 컨테이너를 검증했다.
> 이후 drill 세션을 통해 docker compose stop (-v 제외)를 통한 graceful 정지 과정 장애를 원인/해결/재발방지까지 진행해봤다.
> [위임]은 GoogleIdentity를 포함한 인증과 accounts를 확장 구현했으며, migrate는 직접 진행해봤다 정도로 기억한다.

## 선요약 ↔ 실제 구현 diff (explain-first 채점 포인트)

| # | 선요약 표현 | 실제 기록 | 판정 |
| --- | --- | --- | --- |
| 1 | "compose(prod) / override(dev) 분리" | 방향 맞음. 단 base가 완전한 prod는 아님 — 바인드 마운트·`15432` 포트 등 dev 편의가 base에 남아 있고, 정확히는 "**override 배제 시 이미지 CMD(gunicorn)가 실행되는 운영 형태 경로**" | 근사 |
| 2 | "EKS를 고려하여 Worker=3" | 결정 기록(02-def §8-4)은 "**합리적 기본값, 튜닝은 Phase 3**". EKS 대비 근거가 붙은 결정은 워커 수가 아니라 **비루트(uid 10001)** 쪽 | 어긋남 |
| 3 | "migrate로 운영 컨테이너 검증" | 운영 경로 검증은 **gunicorn 단독 기동 → `/healthz` 200 실측**. migrate는 트랙 B AC 검증 수단 | 혼합 |
| 4 | "stop을 통한 graceful 정지 과정 장애" | 드릴 #1은 **DB 다운**: 핵심 학습은 graceful 자체보다 "정지 컨테이너의 DNS 레코드 제거 → 이름 해석 실패"와 "/healthz의 보증 한계". `-v`는 `stop`이 아닌 `down`의 옵션 | 부분 |
| 5 | "[위임]은 인증 구현" | **인증 API는 M4**. M2는 인증의 **모델 토대**(UserRole·RoleGrant·GoogleIdentity + ADMIN 부트스트랩 훅)까지만 | 어긋남 |
| 6 | 선요약 템플릿 3번(요청 경로)·4번(부서지기 쉬운 지점) 누락 | — | 부채 (WB-2 범위) |

## 무엇이 바뀌었나

* **Dockerfile**: 단일 스테이지 → 멀티스테이지(builder/runtime). 비루트 uid/gid 10001, runtime CMD gunicorn(worker 3), runtime에 uv 미탑재, `ENV PATH`로 venv 노출, uv 이미지 `0.11.26` 고정.
* **docker-compose.override.yml (신규)**: 표준 병합 패턴. 기본 `up` = runserver(dev), `-f docker-compose.yml` 단독 = gunicorn(운영 형태).
* **accounts**: `UserRole`(user·role 일반 유니크, USER row 금지 clean()), `RoleGrant`(append-only 감사, PROTECT), `GoogleIdentity`(OneToOne CASCADE), `create_superuser` atomic ADMIN 부트스트랩(ADR-003), Admin 3종 등록(RoleGrant view-only). 마이그레이션 `accounts.0002` — 적용은 Owner 수행.
* **의존성**: gunicorn 26.0.0 (dependencies 그룹, §16 승인 완료).

## 왜 이 방식인가 (Owner 결정 3건)

1. **dev/prod 분기 = override 병합 패턴** (리스크 #1 결정): 이미지 1개 유지, "override 없음 = 운영 경로"라는 안전한 기본값. 대가: 운영 경로 검증 절차를 M5 문서에 명시해야 함.
2. **runtime에 uv 미탑재**: uv는 빌드 도구 — 실행 단계는 venv+소스로 충분. 검증 명령은 `uv run` 제거로 문서 정합화(02-def §5 주석).
3. **`.claude/agents/` gitignore**: 프로젝트 로컬 에이전트는 커밋하지 않음.

## 핵심 파일

`Dockerfile` · `docker-compose.override.yml` · `accounts/{models,managers,admin}.py` · `accounts/migrations/0002_*.py` · `pyproject.toml`/`uv.lock`

## 어떻게 검증했나

* ops-reviewer 3라운드: 1차 블로커 5 → 2차 블로커 1 → **3차 블로커 0·메이저 0 통과** (운영 경로 gunicorn `/healthz` 200, `id` uid=10001, 시크릿 없음 — 전부 실측).
* `check` 0 issues / `makemigrations --check` No changes / `ruff` 통과 / Owner가 컨테이너에서 migrate·createsuperuser→ADMIN row 확인.

## DevOps 설명 포인트 (§11)

기본 `up` → override의 `command:`(runserver) > base `command:`(없음) > 이미지 `CMD`(gunicorn) 우선순위로 분기. `- .:/app` 바인드 마운트 위에 더 깊은 경로의 익명 볼륨 `- /app/.venv`가 구멍을 내 리눅스 venv를 보호(첫 기동 시 이미지 내용 복사, 재빌드 후엔 `-V`로 갱신). `/healthz`는 liveness 성격이라 의도적으로 DB 비의존 — DB 결합 시 오케스트레이터가 멀쩡한 앱을 재시작하는 오판 루프.

## 보안 노트 (§10)

비루트 실행(uid 10001), 시크릿 하드코딩 없음(3차 리뷰 전수 grep), `.env` gitignore 유지, RoleGrant는 Admin view-only(감사 무결성). 브루트포스 방어는 Phase 3 문서화 대상(§10) — M5 스모크 노트에 갭 명시 예정.

## 학습 게이트 결과

* 드릴 #1 (DB 다운): 이수. 핸즈온 43분(+13 초과). 우수 답변: 딥체크 트레이드오프(cascading failure). 미통과: 원인 인과 확정문.
* 퀴즈: **42/100**. 최우선 부채: 401/403/409(2회 연속 오답)·atomic — **M4 착수 전 재퀴즈 필수**.
* **WB-1: 미실시 — M3 착수 전 이월** (03-def §0).

## 학습 부채 원장 (9건)

① compose 내장 DNS 구조(resolv.conf=리졸버 파일 vs 데몬 DNS 서버=레코드 주체) ② crash/graceful 판독(SIGTERM/SIGKILL·gunicorn 시퀀스·exit 137) ③ DB결합 liveness 재시작 루프 ④ **401/403/409 (최우선)** ⑤ **atomic 부분 커밋 방지 (최우선)** ⑥ FROM 버전 ARG 단일화·gunicorn 정적파일 갭 ⑦ compose 병합 우선순위 ⑧ 익명 볼륨 원리 ⑨ 이름 해석 실패 vs refused → 장애 계층 매핑. (+선요약 템플릿 3·4번 습관화, CONN_HEALTH_CHECKS 도입 검토는 별도 승인 항목)

## 다음 개선

1. WB-1 (부채 ⑦⑧ 자연 검증) → M3 착수
2. M3부터 브랜치+PR 워크플로 전환 검토 (포트폴리오 증거물 + Phase 3 CI 대비)
3. 정적파일 서빙 갭·운영 경로 검증 절차 → M5 smoke-test 문서에 명시
4. 드릴 운영: 시작 타이머 + 단계별 목표 시간 선고지
