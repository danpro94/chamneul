# SPEC-001 — Tasks

각 TASK = 검증 가능한 최소 단위 = 커밋 하나. 한 번에 하나씩 (CLAUDE.md §9).
라우팅 태그는 `docs/learning/02` §2.0.

| # | 라우팅 | 내용 | 검증 |
| --- | --- | --- | --- |
| **T-01** | `[위임]` | **테스트 하네스 부트스트랩.** `tests/{__init__,base,factories}.py` + `unit/` `integration/` 패키지. `/healthz` 테스트 1개로 하네스가 PostgreSQL에 붙는 것 증명 | AC-001 |
| **T-02** | `[위임]` | **실패하는 계약 테스트를 먼저 쓴다.** 비로그인 `users/me` → 401(404 아님), 권한 클래스 403. **실행해서 실패를 눈으로 확인** | AC-002 · AC-011 (🔴 실패해야 정상) |
| T-03 | `[위임]` | `common/exceptions.py` — api.md §1.5 에러 봉투 handler + `REST_FRAMEWORK`에 등록 | AC-014 |
| T-04 | `[위임]` | `common/permissions.py` — 권한 클래스 3종. **역할 보유 ≠ `active_role`** | AC-011 (T-02가 초록으로) |
| T-05 | `[위임]` | `common/pagination.py` + `config/api_urls.py` + `config/urls.py` 한 줄. `/api/v1/` 마운트 | AC-002 (T-02가 초록으로) |
| T-06 | `[소유]` | **OQ-1 결정** — CSRF 부트스트랩 방식. 권고 A안(`ensure_csrf_cookie`, 신규 엔드포인트 0개) | — |
| T-07 | `[위임]` | 가입 — serializer + service(`transaction.atomic`) + view. 중복 409 | AC-003 · AC-004 · AC-005 |
| T-08 | `[위임]` | **원자성 테스트** — 중간 실패 주입 시 `User` row 미잔존 | AC-012 (부채 ⑤) |
| T-09 | `[위임]` | 로그인 — 401/403 구분. **존재하지 않는 이메일도 동일 401** | AC-006 · AC-007 · AC-008 |
| T-10 | `[위임]` | 로그아웃 — **서버 세션 레코드 삭제 확인** + `Max-Age=0` | AC-009 |
| T-11 | `[위임]` | `users/me` — 응답 키 집합 전체 비교. 민감 필드 부재 assert | AC-010 |
| T-12 | `[위임]` | CSRF 테스트 — `APIClient(enforce_csrf_checks=True)` | AC-013 |
| T-13 | `[소유]` | **전체 검증 배터리 실행.** `/verify`. 실측 출력을 `evidence/`에 저장 | 전체 |
| T-14 | `[읽기]` | **설명 확인** — 요청이 미들웨어부터 ORM까지 흐르는 경로, 401과 403이 각각 어느 계층에서 결정되는지, 세션 조회·갱신 쿼리가 언제 발생하는지 | 부채 ④ 해소 근거 |

## 순서 규칙

**T-01 → T-02가 먼저다.** 판정 장치가 서고, 실패하는 것을 눈으로 본 뒤에 구현에 들어간다.

T-02는 **실패한 채로 커밋한다.** 이것이 red-green의 red 절반이고, T-04·T-05가 초록으로 바꾸는 것이 증거다. 커밋 본문에 "의도적으로 실패하는 상태"라고 명시한다.

T-06(OQ-1)은 T-07 전에 끝나야 한다. CSRF 경로가 정해지지 않으면 가입 자체를 테스트할 수 없다.

## 라우팅 주의

* `[소유]` T-06 · T-13은 **AI가 실행하지 않는다.** 체크리스트와 힌트만 제공하고 Owner가 수행한다.
* `[읽기]` T-14는 코드가 아니라 설명이다. 답하지 못한 항목은 `LEARNING_DEBT.md`에 남는다.
* **소유 구역 불가침**: `Dockerfile` · `docker-compose*.yml` · `.env*`. 이 SPEC은 건드릴 이유가 없다.
* **마이그레이션 없음.** `makemigrations --check --dry-run`이 계속 "No changes"여야 한다.

## 커밋 트레일러

```
Spec: SPEC-001
Task: SPEC-001/T-07
```
