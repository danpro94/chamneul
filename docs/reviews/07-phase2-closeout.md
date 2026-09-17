# 리뷰 노트 07 — Phase 2 종료 판정

> 2026-09-17 작성 (SPEC-004/TASK-004). CLAUDE.md §1의 완료 조건 9개를 **증거와 함께** 대조한다.
> 판정 원칙: "됐다"가 아니라 **"이 명령의 이 출력이 근거다"**. 실행하지 않은 명령은 완료로 세지 않는다(§12).

---

## 1. Phase 2 완료 조건 대조 — 9/9

| # | CLAUDE.md §1 조건 | 판정 | 증거 |
| --- | --- | --- | --- |
| 1 | Django app runs locally | ✅ | `docker compose ps` → `chamneul-app-1 / app / Up` |
| 2 | PostgreSQL runs through Docker Compose | ✅ | `chamneul-db-1 / db / Up (healthy)` · `select version()` → `PostgreSQL 16.14 (Debian …)` |
| 3 | `/healthz` returns 200 OK | ✅ | `curl` → `HTTP 200 (0.034s)` `{"status": "ok"}` |
| 4 | Core concern APIs work | ✅ | **44/44** — (경로, 메서드) 쌍 실측 44개. 라이브 호출: #3·#7·#9·#22·#32·#36·#39 전부 200. 전체 사용자 여정 12단계는 맨바닥에서 통과([smoke-test.md](../smoke-test.md) §3) |
| 5 | Django Admin can inspect data | ✅ | `/admin/` → 302(로그인 유도), 등록 모델 **12종**. 감사 무결성 반영 확인: `AssignmentAdmin` add/change/delete = `False/False/False`, `AdviceAdmin` 본문 readonly = `True` |
| 6 | Dockerfile exists | ✅ | `Dockerfile`, `.dockerignore` 존재 |
| 7 | docker-compose.yml exists | ✅ | `docker-compose.yml`, `.env.example` 존재 |
| 8 | README and smoke test docs exist | ✅ | `README.md` · **`docs/smoke-test.md`**(2026-09-16 신규) |
| 9 | API and model docs are coherent | ✅ | `makemigrations --check` → `No changes detected`. model.md drift **22건 전량 반영**(TASK-002), api.md 개정 이력 6차 |

### 라우트 수 실측 (조건 4)

URL 패턴은 37개지만 **(경로, 메서드) 쌍은 정확히 44개**다. 6개 경로가 메서드를 공유한다:

```
api/v1/users/me                                   -> GET, PATCH
api/v1/users/me/concerns                          -> GET, POST
api/v1/users/me/concerns/<uuid:concern_id>        -> DELETE, GET
api/v1/advices/<uuid:advice_id>                   -> DELETE, GET, PATCH
api/v1/admin/advisor-applications/<uuid:...>      -> GET, PATCH
api/v1/admin/feedbacks/<uuid:feedback_id>         -> GET, PATCH
```

### SPEC-004 결정 2·3이 실행 중인 시스템에 반영됐는가

| 결정 | 실증 |
| --- | --- |
| **2. 백엔드 전 구간 UTC** | `GET /users/me` → `"created_at": "2026-09-17T01:58:40.136967Z"`. 응답 전체에서 `+09:00` 출현 **0회** |
| **3. #21 미배정 → 404** | `active_role=ADVISOR`이면서 배정되지 않은 계정으로 호출 → **HTTP 404**. `active_role=USER`인 계정은 **403**(§1.8 3행, 권한 계층 미달) |

### 자동 검증

```
manage.py check                      → 0 issues
makemigrations --check --dry-run     → No changes detected
ruff check .                         → All checks passed
manage.py test                       → 291 tests OK
```

---

## 2. Phase 2에서 만든 것

| 구분 | 결과 |
| --- | --- |
| 엔드포인트 | 44 / 44 |
| 자동 테스트 | 291 |
| 앱 | `accounts` · `advisors` · `concerns` · `advice` · `notifications` + `common` · `config` |
| 도메인 모델 | 12종 |
| ADR | 6건 (001·002·003·004·006·007) |
| SPEC | 4건 (001 concerns · 002 advice · 003 notifications+roles · 004 phase2-closeout) |
| 서브에이전트 리뷰 | 5회 (security-reviewer ×2, api-architect ×2, data-modeler ×1) |
| 리뷰 노트 | 7건 |

마일스톤: M1 스켈레톤 → M2 런타임 승격 → M3 모델 → M4 API 44개 → **M5 스모크 + 문서 정리**.

---

## 3. Phase 3 인수인계

### 3-1. 반드시 먼저 할 것

| # | 항목 | 왜 먼저인가 |
| --- | --- | --- |
| **1** | **운영 설정(`DEBUG=False`) 경로로 한 번 띄워보기** | Phase 2 내내 **한 번도 실행하지 않았다.** "override 없음 = 운영 경로"가 기본값인데 그 경로가 실제로 뜨는지 미확인이다. 정적파일 미구성(아래 2)도 여기서 드러난다 |
| **2** | 정적파일 서빙 구성(`collectstatic`/WhiteNoise) | `DEBUG=False`에서 Django Admin CSS가 깨진다. API에는 영향 없으나 운영 진입 시 즉시 체감 |
| **3** | 브루트포스 로그인 방어(IP·계정 레이트 리밋) | `.claude/rules/security.md`가 Phase 3 과제로 명시. 외부 노출 시점에 **필수**로 승격 |
| **4** | M4-1~M4-3 자동 테스트 | `accounts`의 회원가입·로그인·OAuth·프로필이 테스트 0건이다. 스모크가 실환경에서 한 번 덮었을 뿐 회귀 방어가 없다 |

### 3-2. 설계상 열어둔 것 (버그 아님)

| 항목 | 현재 동작 | 재검토 시점 |
| --- | --- | --- |
| `/healthz`가 DB 장애 중에도 200 | liveness 프로브이지 readiness가 아니다. **로드밸런서가 이것만 보면 DB 없는 인스턴스에도 트래픽을 보낸다** | 로드밸런서 도입 시 `/healthz/db` 추가 |
| 역할 회수해도 활성 배정 유지 | 관리자가 #25로 명시 해제. #23에서 식별 가능 | 운영 데이터가 쌓인 뒤 |
| 회수 후 `advisor_status`가 `APPROVED` | 사실 관계상 맞다(승인됐던 것은 사실). 기능 차단은 해소됨 — 재신청 가능 | UX 검토 |
| 고민 종료(`CLOSED`) 사용자 API 없음 | Django Admin의 CLOSED 전용 action으로만. CLAUDE.md §6.6 문구와 긴장 | Phase 3 |
| 알림 일괄 읽음 없음 | api.md 비범위 | 알림량이 늘면 |

### 3-3. 검증 공백

| 항목 | 현재 | 필요한 것 |
| --- | --- | --- |
| **실제 경합** | 잠금의 *존재*만 SQL 검사로 고정(`StateTransitionLockingTests`) | `TransactionTestCase` + 스레드로 "관리자 0명" 시나리오 실제 재현 |
| `Feedback.score` 범위 | `validators`만 | DB `CheckConstraint` |
| 에러 메시지의 모델명 노출 | `"No Assignment matches the given query."` — Django 기본 메시지가 모델명을 드러낸다 | 에러 메시지 정책 수립 시 일괄 처리(전 엔드포인트 동일 패턴이라 개별 수정은 부적절) |

### 3-4. Phase 3 범위 (CLAUDE.md §5)

아웃컴 추적 · 신뢰 점수 알고리즘 · 조언가 매칭 알고리즘 · 사용자 신청 철회 API · AWS · Kubernetes · Terraform · CI/CD · 결제 · 운영 모니터링 · 프론트엔드.

**프론트엔드 인수인계 사항 하나**: 결정 2에 따라 **백엔드는 UTC만 내보낸다.** 현지 시각 변환은 전적으로 클라이언트 책임이다(api.md §1.7).

---

## 4. Phase 2를 돌아보며

### 결함은 기능 안이 아니라 기능 사이에 있었다

M4에서 나온 중대 결함 7건 중 **단일 함수의 로직 오류는 하나도 없다.** 전부 (a) 두 요청이 겹칠 때, (b) 한 기능이 만든 데이터를 다른 기능이 읽을 때, (c) 서비스 레이어를 우회하는 경로에서 나왔다.

특히 **"검사하고 나서 바꾸는" 모양이 네 번 반복됐다**(M-1 · A-1 · A-3 · 마지막 관리자). 대응이 세 단계로 진화했다 — 개별 수정 → 규칙 신설 → **규칙을 테스트로 승격**. 두 번째에서 멈췄다면 다섯 번째가 나왔을 것이다. A-1이 정확히 그렇게 생겼다(규칙은 있었는데 새 함수가 조용히 빠졌다).

### 검증에는 층이 있고, 어느 층도 다음 층을 대신하지 못한다

| 층 | 답하는 질문 | 여기서 처음 잡힌 것 |
| --- | --- | --- |
| 단위 테스트 | 함수가 의도대로 동작하는가 | 대부분의 로직 |
| 교차 검증 AC | 기능 **사이**가 맞는가 | A-3가 실제로 권한을 닫는가, `target_url`이 열리는가 |
| 발행 SQL 검사 | 잠금·`update_fields`가 **장식이 아닌가** | 규칙의 기계적 강제 |
| 서브에이전트 리뷰 | 설계가 약한 곳은 어디인가 | 데이터 유실, 500 크래시, Admin 우회, 재신청 막다른 길 |
| **맨바닥 스모크** | **시스템이 일어서는가** | DB 장애 거동, 마이그레이션 미적용 판별법 |

AC 전항 통과 + 168개 테스트 상태에서 서브에이전트가 데이터 유실 1건과 500 크래시 1건을 찾은 것이 이 층위를 가장 잘 보여준다.

### 문서는 "무엇을 저장하는가"보다 "그것으로 무엇을 하는가"가 먼저 낡는다

model.md 정합성 점검에서 나온 drift 22건은 **전부 서술 계층**이었다. 스키마 — 필드·제약·인덱스·`on_delete` — 는 M3 이후 한 번도 어긋나지 않았고, 마이그레이션도 `advisors.0002` 하나뿐이었다.

낡은 것은 상태 전이 서술, 서비스 규칙, Admin 운영 시나리오였다. **문서가 "Django Admin으로 승인하라"고 안내하는데 따라 하면 막히는** 상태가 두 달간 유지됐다.

### 소비자가 없는 코드는 옳은지 알 수 없다

`Notification` 모델은 M3에 확정됐지만 읽는 코드가 SPEC-003까지 없었다. 다섯 개 서비스가 `target_url`을 문자열로 박아 넣었고 **전부 옳았지만, 옳다는 사실 자체가 미확인**이었다.

같은 일이 시스템 규모로도 있었다. 291개 테스트가 녹색이어도 "맨바닥에서 일어서는가"는 별개의 질문이었고, 볼륨을 비우고 돌려보기 전까지 답할 수 없었다.

---

## 판정

**Phase 2 완료.** CLAUDE.md §1의 9개 조건 전항이 증거와 함께 충족됐다.

다만 §3-1의 네 항목 — 특히 **운영 설정으로 한 번도 띄워보지 않았다**는 것 — 은 Phase 3 진입 전에 닫는 편이 낫다. Phase 2가 답한 것은 "로컬에서 일어서는가"이고, "운영 설정으로도 일어서는가"는 아직 열린 질문이다.
