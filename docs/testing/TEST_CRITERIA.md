# TEST_CRITERIA — 자동화 판정 기준

> CLAUDE.md §12 (Testing and Validation Rules) 실행판. api.md 각 엔드포인트와 model.md 각 상태 전이의 AC를 Django test runner로 자동 판정 가능한 형태로 번역한다.

## 0. 현재 상태 — 테스트 0건

**2026-09-09 실측**: `git ls-files`에 `tests.py` / `tests/` 파일이 하나도 없다. `config/settings/test.py`는 테스트 *설정*(PostgreSQL 테스트 DB, 빠른 해셔)이지 테스트 *코드*가 아니다. M4-1~M4-4(16개 엔드포인트, `accounts`·`advisors` 앱)의 AC 판정은 전부 Owner의 수기 스모크(curl/Admin 조회)에 의존해 왔다.

이 갭은 `docs/reviews/04-milestone4-definition.md` D-7(2026-09-09 확정)에서 이미 인지·결정되었다: **M4-5부터 test-first**로 전환하고, 신규 테스트 패키지는 도입하지 않는다(pytest 등 §16 게이트 회피 — Django 기본 test runner만 사용). 기 구현분(M4-1~M4-4)의 소급 테스트는 M4-5 진행과 병행해 채운다.

## 1. 런타임 정책

* 러너: `python manage.py test` (Django 기본, `unittest` 기반).
* DB: `config/settings/test.py` — PostgreSQL 테스트 DB. **SQLite in-memory 폴백 금지**(CLAUDE.md §4).
* 패스워드 해셔: `MD5PasswordHasher`(테스트 전용, 속도 최적화 — 테스트 DB는 폐기 가능하므로 강도는 무의미).
* 신규 테스트 패키지(pytest, factory_boy, faker 등) 도입 안 함 — Django `TestCase` + `django.test.Client` 또는 DRF `APIClient`(기 의존성인 `djangorestframework`에 포함, 별도 설치 불요)로 충분.
* 파일 배치: 각 앱 `<app>/tests.py` (단일 파일이 비대해지면 `<app>/tests/test_<module>.py`로 분할 — 스켈레톤 원칙과 무관하게 Django 표준 관행).

## 2. 핵심 3축 (D-7 확정)

모든 SPEC의 `acceptance.md`는 이 3축 중 해당하는 것으로 AC를 분류한다.

### 축 1 — 인증 플로우

* 세션 쿠키 발급/삭제: signup 자동 로그인 → `Set-Cookie: sessionid` 존재, logout → 서버 세션 삭제 + `Max-Age=0`.
* CSRF: 토큰 없는 상태 변경 요청 → 403.
* 비로그인 요청 → 401 (인증 필요 엔드포인트 전부).

### 축 2 — 권한 매트릭스

각 엔드포인트마다 다음 4가지를 최소 커버:

| 케이스 | 기대 |
| --- | --- |
| 비로그인 | 401 |
| 로그인했으나 필요 역할 없음(예: `active_role=USER`인데 ADVISOR 전용 API) | 403 |
| 로그인 + 역할 있으나 타인 자원 접근 | 403 또는 404(자원별 정책에 따름 — SPEC에서 명시) |
| 존재하지 않는 리소스 | 404 |
| 상태 충돌(중복 배정, 잘못된 상태 전이 등) | 409 |

### 축 3 — 상태 전이 + 부수효과

model.md §5(Service-Layer Constraints)에 명시된 전이마다 "전이 후 상태" + "부수효과(알림/감사 row)"를 한 테스트에서 함께 검증한다. 예: 조언 승인 → `Advice.status=APPROVED` **그리고** `Concern.status`가 `ANSWERED`로 전이 **그리고** `Notification` row 생성 — 셋 중 하나만 확인하는 테스트는 불충분.

## 3. 공통 AC 체크리스트 (모든 엔드포인트에 적용)

* [ ] 성공 케이스: 응답 status code가 api.md §1.8과 일치
* [ ] 응답 필드가 api.md "Response 주요 필드"와 일치 (초과 노출 없음 — CLAUDE.md §8)
* [ ] 인증 필요 API는 비로그인 401 실측
* [ ] 접근 제어 조건(api.md 각 절)의 실패 케이스 최소 1개
* [ ] 목록 API는 `page_info` 포함 + N+1 없음(assertNumQueries로 쿼리 수 고정)
* [ ] 소프트 삭제 대상 자원은 삭제 후 일반 API에서 404 실측

## 4. M4 완료(DoD) 판정과의 관계

`docs/reviews/04-milestone4-definition.md` §5의 AC는 "Owner가 스모크 시나리오로 실측"을 전제로 쓰여 있다. D-7 확정 이후에는 각 항목이 **자동화된 테스트로 우선 커버되고, 남은 것만 Owner 수기 스모크로 보완**하는 순서로 바뀐다:

| §5 AC 원문 | 자동화 방식 |
| --- | --- |
| 44개 엔드포인트가 api.md와 URI·메서드·상태 코드 일치 | 각 엔드포인트 최소 1 happy-path 테스트 |
| 세션 쿠키 HttpOnly·SameSite=Lax, 로그아웃 시 서버 세션 삭제+Max-Age=0 | `accounts/tests.py` — 이미 M4-1 소급 대상 |
| CSRF 403 | `accounts/tests.py` |
| 권한 매트릭스 401/403/404/409 | 각 앱 `tests.py` — 축 2 |
| §6.2 APPROVED 외 advice 비노출 | `advice/tests.py` |
| 부수효과 3종(신청 승인/조언 승인/배정) | 각 서비스 레이어 테스트 — 축 3 |
| 소프트 삭제 404 + admin `include_deleted` | `concerns/tests.py` |
| N+1 없음 | `assertNumQueries` |
| `check`/`makemigrations --check`/`ruff`/`test` 통과 | CI 없음 — 매 모듈 커밋 전 로컬 실행, 실행 출력을 커밋 설명/PR에 첨부 |

Owner 수기 스모크는 자동화가 표현하기 어려운 것(실제 Docker Compose 기동, Google OAuth 콘솔 왕복, Admin UI 육안 확인)에 한정한다.

## 5. 알려진 갭

* 브루트포스 로그인 방어 테스트 없음 — 방어 자체가 Phase 3 이월(CLAUDE.md §10)이므로 테스트도 함께 이월.
* 부하/동시성 테스트(`select_for_update()` 경합 등) 없음 — Phase 2 스코프 밖.
* 기 구현분(M4-1~M4-4) 소급 테스트는 SPEC-001(M4-5) 진행과 **병행**하되, SPEC-001을 막지 않는다 — 소급 테스트가 밀리면 STATUS.md 문서 부채 항목에 기록한다.
