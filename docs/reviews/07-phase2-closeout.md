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
manage.py test                       → 292 tests OK
```

---

## 2. Phase 2에서 만든 것

| 구분 | 결과 |
| --- | --- |
| 엔드포인트 | 44 / 44 |
| 자동 테스트 | **292** |
| 앱 | `accounts` · `advisors` · `concerns` · `advice` · `notifications` + `common` · `config` |
| 도메인 모델 | 12종 |
| ADR | 6건 (001·002·003·004·006·007) |
| SPEC | 4건 (001 concerns · 002 advice · 003 notifications+roles · 004 phase2-closeout) |
| 서브에이전트 리뷰 | **6회** (security-reviewer ×2, api-architect ×2, data-modeler ×1, devops-local-platform ×1) |
| 리뷰 노트 | 7건 |

마일스톤: M1 스켈레톤 → M2 런타임 승격 → M3 모델 → M4 API 44개 → **M5 스모크 + 문서 정리**.

---

## 3. Phase 3 인수인계

### 3-1. 반드시 먼저 할 것

| # | 항목 | 왜 먼저인가 |
| --- | --- | --- |
| **1** | **`accounts` 자동 테스트** (#2·#3·#4·#7·#8·#9 + **#5·#6 OAuth**) | 인증은 보안 경계 전체이고, Phase 3의 모든 변경이 그 위를 지나간다. 특히 **OAuth(#5·#6)와 프로필 수정(#8)은 자동 테스트도 스모크도 없는 유일한 무검증 영역**이다. *(2026-09-17 `devops-local-platform` 권고로 4번에서 승격)* |
| **2** | **운영 경로 1회 기동 + 정적파일** | `docker compose -f docker-compose.yml up -d` **와** `DJANGO_SETTINGS_MODULE=config.settings.prod` 주입이 **둘 다** 필요하다(override만 빼면 gunicorn + local settings). 정적파일은 여기서 반드시 부딪히므로 한 항목으로 묶는다. **예상되는 것은 이미 실측됐다** — 아래 §3-2 참조 |
| **3** | 브루트포스 로그인 방어(IP·계정 레이트 리밋) | `.claude/rules/security.md`가 Phase 3 과제로 명시. **외부 노출 전까지는 실효 위험이 0**이므로 1·2 뒤로 내린다. 노출 시점에 **필수**로 승격 |
| **4** | 실제 경합 재현 + `Feedback.score` DB 제약 | §3-3 참조 |

### 3-2. 운영 경로에서 만날 것 — 이미 실측됨

`devops-local-platform` 리뷰가 기존 컨테이너 안에서 `config.settings.prod`를 로드해 확인한 결과다. **"안 띄워봤지만 무엇이 나올지는 안다"** 상태다.

| 확인 | 결과 |
| --- | --- |
| 평문 HTTP `/healthz` | **301** (`SECURE_SSL_REDIRECT=True`) — **로드밸런서 헬스체크 기본값(2xx만 정상)에서 즉시 unhealthy가 된다** |
| `X-Forwarded-Proto: https` 동반 | 200 |
| Host가 컨테이너 IP·서비스명 | **400** (`ALLOWED_HOSTS=localhost,127.0.0.1`) |
| `STATIC_ROOT` 존재 | **False** (bind mount가 가림) |

### 3-3. 설계상 열어둔 것 (버그 아님)

| 항목 | 현재 동작 | 재검토 시점 |
| --- | --- | --- |
| `/healthz`가 DB 장애 중에도 200 | liveness 프로브이지 readiness가 아니다. **로드밸런서가 이것만 보면 DB 없는 인스턴스에도 트래픽을 보낸다** | 로드밸런서 도입 시 `/healthz/db` 추가 |
| 역할 회수해도 활성 배정 유지 | 관리자가 #25로 명시 해제. #23에서 식별 가능 | 운영 데이터가 쌓인 뒤 |
| 회수 후 `advisor_status`가 `APPROVED` | 사실 관계상 맞다(승인됐던 것은 사실). 기능 차단은 해소됨 — 재신청 가능 | UX 검토 |
| 고민 종료(`CLOSED`) 사용자 API 없음 | Django Admin의 CLOSED 전용 action으로만. CLAUDE.md §6.6 문구와 긴장 | Phase 3 |
| 알림 일괄 읽음 없음 | api.md 비범위 | 알림량이 늘면 |

### 3-4. 검증 공백

| 항목 | 현재 | 필요한 것 |
| --- | --- | --- |
| **실제 경합** | 잠금의 *존재*만 SQL 검사로 고정(`StateTransitionLockingTests`) | `TransactionTestCase` + 스레드로 "관리자 0명" 시나리오 실제 재현 |
| `Feedback.score` 범위 | `validators`만 | DB `CheckConstraint` |
| 에러 메시지의 모델명 노출 | `"No Assignment matches the given query."` — Django 기본 메시지가 모델명을 드러낸다 | 에러 메시지 정책 수립 시 일괄 처리(전 엔드포인트 동일 패턴이라 개별 수정은 부적절) |

### 3-5. `devops-local-platform` 리뷰 결과 (2026-09-17)

Phase 2 판정 자체는 유효하다는 확인을 받았다 — **코드·인프라 결함 0건**, 조건 9개 중 6개는 리뷰어가 독립 재실측했다(`ps` / healthz 200 / `migrate --check` / 마이그레이션 25건 / **라우트 44개** / `check` 0 issues).

문제는 **문서의 기술 서술**에 있었고, 전부 정정했다:

| 무엇이 틀렸나 | 실제 |
| --- | --- |
| "`CONN_MAX_AGE` 기본값 0이라 회복된다" | **60**이다. 회복 기전은 요청 종료 시 오류 난 연결을 폐기하는 것(`close_if_unusable_or_obsolete`) |
| "`collectstatic` 없음" | `Dockerfile:31`이 **빌드 때 수행한다.** 진짜 원인은 bind mount가 `/app/staticfiles`를 가리는 것 + 서빙 주체 부재 |
| "override 없음 = 운영 경로" | `docker-compose.yml`이 `settings.local`을 고정하므로, override만 빼면 **gunicorn + local**이라는 어느 쪽도 아닌 조합이 된다 |
| (누락) 측정 조건 | **전 구간 `runserver`에서 측정했다.** `docker-compose.override.yml`이 커밋돼 있어 `docker compose up`은 항상 개발 서버로 뜬다 — 이 사실을 몰랐다 |

마지막 항목이 가장 무겁다. §4-3의 "앱 재시작 불필요"라는 결론이 **서버에 의존**한다 — gunicorn 3워커에서는 워커마다 연결을 쥐고 있어 DB 재기동 직후 워커 수만큼 실패가 먼저 날 수 있다. 문서에 명시했다.

**함께 드러난 것 2건:**

* **`#5·#6`(Google OAuth)과 `#8`(프로필 수정)은 자동 테스트도 스모크도 없다** — 이 프로젝트에서 **검증 수단이 0개인 유일한 영역**이다. "44/44"가 "존재"와 "동작 검증"을 섞어 읽히게 하고 있었다.
* `README.md` Quick Start에 `migrate`가 없어 **문서대로 따라가면 첫 쓰기 API가 500**이었다. 아이러니하게도 스모크 문서 §4-1이 바로 그 증상의 진단법을 적고 있다.

코드 결함 1건(D-14)도 고쳤다 — Admin의 CLOSED action이 `with_deleted()` 쿼리셋 위에서 돌아 **소프트 삭제된 고민까지 종료**할 수 있었고, `.update()`가 `updated_at`을 갱신하지 않았다.

**Owner 결정 5건 — 2026-09-17 전건 승인·처리.** `docker-compose.yml`·`Dockerfile`·`.env.example`은 CLAUDE.md §16 불가침이라 **Owner 승인 후에만** 손댔다.

| # | 항목 | 처리 |
| --- | --- | --- |
| 1 | **Google OAuth client secret 회전** | **Owner 작업 항목** — Google Cloud Console에서 수행해야 한다. 절차는 아래 §3-5-1. Git 이력에 없음은 재확인했다(`.env` 미추적, `.gitignore`가 `.env`·`.env.*` 커버) |
| 2 | compose에 app healthcheck | **완료** — `/healthz` 10초 간격, 기동 유예 20초. 실측: `Up 10 seconds (healthy)` |
| 3 | Dockerfile gunicorn 액세스 로그 | **완료** — `--access-logfile -`·`--error-logfile -`. 이미지 `Config.Cmd`로 확인 |
| 4 | compose `db`의 `env_file` 제거 | **완료** — `docker compose config` 기준 db에 남은 키는 `POSTGRES_DB`·`POSTGRES_USER`·`POSTGRES_PASSWORD` **3개뿐**. `${...}` 치환은 Compose가 `.env`를 자동으로 읽으므로 그대로 동작한다 |
| 5 | `.env.example` 누락 키 3개 | **완료** — `GOOGLE_OAUTH_REDIRECT_URI`·`GOOGLE_OAUTH_SUCCESS_REDIRECT`·`DB_CONN_MAX_AGE` |

부수적으로 `restart: unless-stopped`도 추가했다(D-15) — Docker Desktop 재시작 후 스택이 내려가 있던 문제.

**검증**: 재빌드·재기동 후 두 서비스 모두 `healthy`, 볼륨 데이터 보존(사용자 14·고민 6), **스모크 여정 12단계 재통과**. 설정 변경이 기능을 깨지 않았다.

#### 3-5-1. Google OAuth client secret 회전 절차 (Owner 작업)

리뷰 중 `docker compose config`가 `.env`의 값을 평문 출력했고, 그 출력이 세션 로그에 남았다. **Git 이력에는 없지만** 로그가 남은 이상 회전이 안전하다.

1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → 해당 OAuth 2.0 클라이언트 ID 선택
2. **client secret 추가** (기존 것을 먼저 지우지 말 것 — 지우면 그 즉시 로그인이 끊긴다)
3. 로컬 `.env`의 `GOOGLE_OAUTH_CLIENT_SECRET`을 새 값으로 교체
4. `docker compose up -d` (env_file은 재기동 시 다시 읽힌다)
5. `#5` authorize → `#6` callback 로그인 1회 확인
6. 확인 후 **Console에서 기존 secret 폐기**

> `docker compose config`는 병합된 설정을 출력하면서 `.env` 값을 **평문으로 찍는다.** 앞으로 설정 구조만 볼 때는 `docker compose config --services` 또는 `docker compose config --quiet`(문법 검증만)를 쓴다. 이 경고는 [smoke-test.md](../smoke-test.md) §6에도 넣었다.

**Phase 3 우선순위 재배열 권고도 받았다**: 브루트포스 방어(현 3번)는 외부 노출 전까지 실효 위험이 0이므로 뒤로, **`accounts` 자동 테스트(현 4번)를 1번으로** — 인증은 보안 경계 전체이고 OAuth는 무검증 영역이다. 이 권고를 §3-1에 반영했다.

### 3-5-2. ADR-008로 추가된 Phase 3 항목 (2026-09-22)

| 항목 | 내용 |
| --- | --- |
| **비밀번호 재설정 메일 발송** | 엔드포인트(#45·#46)는 SPEC-005에서 구현하되, 실제 발송은 **인프라**다(발송 서비스 계정·도메인 인증). 로컬은 콘솔 출력으로 검증. **이것 없이는 실사용자가 비밀번호를 되찾을 수 없다** |
| **재설정 요청 레이트 리밋** | 같은 주소로 메일을 반복 발송시킬 수 있다. 브루트포스 방어(§3-1 항목 3)와 함께 처리 |
| **고민 덧붙이기** | 배정 이후 원문 수정 대신 "추가로 드리고 싶은 말"을 덧붙이는 방식. 모델 추가가 필요하고 **실사용 수요를 확인한 뒤**가 적절하다 |

### 3-6. Phase 3 범위 (CLAUDE.md §5)

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

같은 일이 시스템 규모로도 있었다. 292개 테스트가 녹색이어도 "맨바닥에서 일어서는가"는 별개의 질문이었고, 볼륨을 비우고 돌려보기 전까지 답할 수 없었다.

---

## 판정

**Phase 2 완료.** CLAUDE.md §1의 9개 조건 전항이 증거와 함께 충족됐다.

다만 §3-1의 네 항목 — 특히 **운영 설정으로 한 번도 띄워보지 않았다**는 것 — 은 Phase 3 진입 전에 닫는 편이 낫다. Phase 2가 답한 것은 "로컬에서 일어서는가"이고, "운영 설정으로도 일어서는가"는 아직 열린 질문이다.
