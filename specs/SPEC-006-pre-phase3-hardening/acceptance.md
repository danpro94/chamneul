# SPEC-006 — acceptance criteria

TEST_CRITERIA.md §2·§3을 SPEC-006에 적용한 판정 기준. AC-1~AC-3은 Django 테스트로 자동 판정, AC-3의 기동 항목과 AC-4는 실제 컨테이너 출력으로 판정한다.

## AC-1. 요청 횟수 제한 (TASK-001)

> 2026-11-04 전항 통과 — `accounts.tests.RateLimitTests` 15개.

- [x] 한도 초과 → **429**, `Retry-After` 헤더, 본문 `error.code == "RATE_LIMITED"`
- [x] 한도 이내 요청은 영향 없음
- [x] 계정 기준 제한이 IP를 바꿔도 걸린다 (#3)
- [x] `X-Forwarded-For`를 바꿔도 IP 기준 제한을 우회할 수 없다 (`NUM_PROXIES=0`)
- [x] #45: 가입·미가입 주소의 429가 **상태 코드·본문 동일**
- [x] #45: 대소문자만 바꾼 주소가 같은 카운터로 센다
- [x] 캐시 테이블에 이메일 원문이 남지 않는다
- [x] 제한 대상이 아닌 엔드포인트는 영향 없음
- [x] 카운터 저장소가 프로세스 간 공유된다 (`CACHES` 백엔드 단언)

## AC-2. readiness (TASK-002)

- [ ] DB 정상 → `/readyz` 200 `{"status": "ok", "checks": {"database": "ok"}}`
- [ ] DB 실패 → `/readyz` **503**, 본문에 예외·호스트 정보 없음
- [ ] DB 실패 중에도 `/healthz` 200
- [ ] prod 설정 + 파드 IP Host + HTTP → 두 경로 200 (301·400 아님)
- [ ] 헬스 경로 판정은 정확히 일치 — 비슷한 경로는 일반 흐름을 탄다

## AC-3. 운영 경로 (TASK-003)

- [ ] prod + 콘솔 메일 백엔드 → 기동 실패
- [ ] prod + `http://` 재설정 URL → 기동 실패
- [ ] 진입점 기본값이 결정 4대로다
- [ ] 실제 이미지(gunicorn + prod): `/healthz`·`/readyz` 200, Admin CSS 200, XFP https로 API 200, http → 301
- [ ] `check --deploy` 출력이 리뷰 노트에 기록됐다

## AC-4. 스모크 (TASK-004)

- [ ] 빈 볼륨에서 여정 **15단계** 전항 통과
- [ ] 백업이 저장소 밖에 있고 복원 절차가 문서와 일치한다

## AC-5. 회귀 없음 (전 TASK)

- [ ] `check` 0 issues / `makemigrations --check` No changes / `ruff check` passed
- [x] 기존 **424개** 테스트가 하나도 깨지지 않는다 — TASK-001 시점: 424개 통과. 단 1개(`PasswordResetRequestTests.test_changes_nothing_in_the_database`)는 결정 1(카운터를 DB 캐시에 쓴다)과 정면으로 부딪혀 **단언 범위를 좁혔다**(캐시 테이블 쓰기만 예외, 나머지 쓰기 0은 유지). **Owner 조건부 승인 2026-11-07**("운영에 치명적 영향이 없으면") — 예외를 #45 카운터 2개(`throttle_password_reset_email`·`_ip`)로 다시 좁혀 사각지대를 없앴다(리뷰 노트 09 §1-8)
- [ ] Dockerfile·docker-compose 변경 없음

## 종료 판정

AC-1~AC-5 전항 통과 + 검증 4종 출력 + 서브에이전트 리뷰 2종 → SPEC-006 완료, PR. 그다음 **프론트엔드 범위 ADR** → **Phase 3 착수**(Owner 승인 순서, 2026-11-02).
