# SPEC-006 — tasks

프롬프트 3 루프(**실패 테스트 먼저 → 최소 구현 → 검증 4종 실행 출력 → 변이 검증 → 커밋 → STATUS.md 갱신 → 정지·확인**). 커밋 메시지에 `SPEC-006/TASK-00N`을 포함한다.

검증 4종 = `manage.py check` / `makemigrations --check` / `ruff check` / `manage.py test`.

**선행 조건: spec §7 결정 6건 승인.** ✅ 충족 — 2026-11-04 전건 권고안 승인. 결정 5가 (a)이므로 TASK-002 전에 **ADR-010**을 Accepted로 만들고 CLAUDE.md §5·§7을 헌법 잠금 절차대로 개정한다.

## TASK-001 — 요청 횟수 제한 (#2·#3·#45·#46)

> **완료 (2026-11-04)** — 테스트 15개(전체 **439개**), 선-실패 13개 확인(2개는 회귀 방지용이라 처음부터 통과). 변이 15건 전건 검출. 실제 compose 앱에서 10×401 → 11번째 429(`Retry-After: 3599`) 확인. 상세 [리뷰 노트 09](../../docs/reviews/09-spec-006-hardening.md) §1.

* [x] 같은 IP 로그인 한도 초과 → 429 + `Retry-After` + 봉투 `RATE_LIMITED` — 실패 테스트
* [x] 여러 IP·같은 계정 로그인 한도 초과 → 429 — 실패 테스트
* [x] 요청마다 다른 `X-Forwarded-For` → 그래도 429 (우회 불가) — 실패 테스트. 운영 모양(`NUM_PROXIES=1`, ALB가 붙인 마지막 값)도 함께 고정
* [x] #45 가입·미가입 주소의 429가 **바이트 동일** / 대소문자 변형도 같은 카운터 — 실패 테스트
* [x] 캐시 테이블에 이메일 원문이 없다(키가 해시) — 실패 테스트. 그냥 sha256도 아니고(HMAC) IP 원문도 없다
* [x] 다른 엔드포인트는 영향 없음 / 기존 424개 통과 — **기존 1개의 단언 범위를 좁혔다**: `test_changes_nothing_in_the_database`(#45는 DB를 쓰지 않는다)가 결정 1의 카운터 쓰기에 걸렸다. 목적(토큰·세션·사용자 행을 쓰지 않는다)은 그대로 두고 캐시 테이블 쓰기만 예외로 했다 → **Owner 조건부 승인(2026-11-07)**, 예외를 #45 카운터 2개로 다시 좁힘
* [x] **후속(2026-11-07)**: IP 한도에 막힌 요청도 주소 카운터를 만들던 문제 — 첫 거절에서 멈추는 `StopAtFirstLimit` — 실패 테스트 먼저(행 5개 → 기대 2개). 변이 5건 전건 검출. 리뷰 노트 09 §1-8
* [x] `CACHES = DatabaseCache`(+ `MAX_ENTRIES`), `NUM_PROXIES` 환경변수화(`DRF_NUM_PROXIES`, 기본 0), 한도 표를 settings 한 곳에
* [x] 변이 검증: IP 스로틀·이메일 스로틀·해시·정규화·`NUM_PROXIES`를 하나씩 지운다 — 그 외 10건 포함 15건
* [x] 검증 4종 실행 결과 첨부

## TASK-002 — readiness 분리 (`/readyz`) + 헬스 미들웨어

> **완료 (2026-11-07)** — 테스트 6개(전체 **446개**), 선-실패 3개 확인(3개는 회귀 방지용). 변이 10건 전건 검출(M9는 테스트 보강 후). 실제 compose 앱에서 DB 정지 → `/readyz` 503·`/healthz` 200 → 재기동 → 200. 상세 [리뷰 노트 09](../../docs/reviews/09-spec-006-hardening.md) §2.

* [x] (선행) ADR-010 Accepted + CLAUDE.md §5·§7 개정 (§16 항목 추가 포함, ADR 문구 그대로)
* [x] DB 정상 → `/readyz` 200 / DB 연결 실패(모의) → 503, 본문에 예외 문자열 없음 — 실패 테스트. **질의 단계 실패**(끊긴 영구 연결)도 503 — 변이 M9가 드러낸 보강
* [x] `/healthz`는 DB 실패 중에도 200 — 회귀 방지 테스트(처음부터 통과)
* [x] prod 설정에서 파드 IP Host + HTTP로 두 경로 200(301·400 아님) — 실패 테스트. 같은 설정에서 일반 경로가 400·301인 **전제**도 고정
* [x] 다른 경로(`/healthz/`, `/readyzx`, `/api/...`)는 미들웨어가 건드리지 않는다 — 회귀 방지 테스트(POST·DELETE 포함)
* [x] 검증 4종 + 변이 검증

## TASK-003 — 운영 경로 (prod 가드 · 진입점 · 정적파일 · 실제 이미지 기동)

* [x] prod + 콘솔 메일 → `ImproperlyConfigured` / prod + `http://` 재설정 URL → `ImproperlyConfigured` — 실패 테스트 (`config.tests.ProdStartupGuardTests`, filebased도 거부)
* [x] `wsgi.py`·`asgi.py` 기본값 prod (결정 4) — 테스트 (`EntryPointDefaultTests`, manage.py는 local 유지까지)
* [x] WhiteNoise 6.12.0 (결정 3) — `StaticFilesTests`. 미들웨어·저장소는 **base.py**(plan.md §4 "계획 대비" 표)
* [x] **실제 이미지 기동**: `/healthz`·`/readyz` 200(파드 IP Host), Admin CSS 200, XFP https로 API 200, http → 301 — 출력은 리뷰 노트 09 §3-4
* [x] `manage.py check --deploy` 출력 기록 — `no issues (0 silenced)`
* [x] smoke-test §5 갭 2·3·11 갱신 + 새로 발견한 갭 12(운영 500 원인 미기록)·13(gunicorn 제어 소켓) 추가
* 2026-11-07 완료 — 테스트 453개 OK, 변이 10/10. 갭 12는 Owner 결정 대기(SPEC-006에 넣을지)
* [x] **후속 (2026-11-09, Owner 승인으로 범위 추가)** — 갭 12: `LOGGING`으로 5xx 트레이스백을 stderr에, 4xx WARNING 줄은 끔. `config.tests.ErrorLoggingTests`(prod·local 새 인터프리터) — 테스트 454개 OK, 변이 4/4, 실제 이미지에서 500 원인 확인(리뷰 노트 09 §3-8)

## TASK-004 — 스모크 여정 확장 + 맨바닥 재통과

* [ ] 여정 13 재설정(요청 → 콘솔 링크 → 확정 → 새 비밀번호 로그인) / 14 고민 수정(배정 전 200, 후 409) / 15 로그인 한도 초과 429
* [ ] 볼륨 백업(저장소 밖) → 빈 볼륨 → `migrate` → `createcachetable` → 15단계 전항 통과
* [ ] 읽기 전용 MCP 계정 재생성(`setup-postgres-ro-role.sh`) → `/mcp` ✔
* [ ] smoke-test §2·§3 갱신

## TASK-005 — 마무리

* [ ] api.md(#48 `/readyz`, 429 정책), smoke-test §5(갭 1·7 해소), STATUS, 리뷰 노트 09, AIUSAGE
* [ ] `security-reviewer`(스로틀·헬스 미들웨어) + `devops-local-platform`(운영 경로) 서브에이전트 리뷰
* [ ] PR → 머지(Owner)
