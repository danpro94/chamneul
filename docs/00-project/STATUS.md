# STATUS — 프로젝트 현재 상태

> **이 문서가 "지금 어디까지 왔는가"의 단일 소스다.** 마일스톤/SPEC이 닫힐 때마다 갱신한다.
> 근거 순서: `CLAUDE.md` → `docs/adr/` → **본 문서** → 활성 SPEC → `docs/api.md`·`docs/model.md` → 코드 (ADR-005 §4.1)

| 항목 | 값 |
| --- | --- |
| 최종 갱신 | 2026-09-08 |
| Phase | **Phase 2 — 로컬 컨테이너 MVP** (CLAUDE.md §1) |
| 마일스톤 | M3 종료 · **M4 착수 준비** |
| 활성 SPEC | `SPEC-001-local-session-auth` (정의 완료, **구현 미착수**) |
| 개발 환경 | VS Code + Claude Code Extension (2026-09-08 전환, ADR-005) |
| 브랜치 | `claude/chamneul-mvp-migration-ai-native-bixhdu` |

---

## 1. 한 줄 요약

**모델 계층은 완성됐고 API 계층은 비어 있다.** 43개 엔드포인트 중 `/healthz` 1개만 구현되어 있으며, 그것도 DRF를 쓰지 않는다. 다음 최소 작업 단위는 SPEC-001(로컬 세션 인증 + 테스트 하네스)이다.

## 2. 마일스톤 진행

| M | 내용 | 상태 | 근거 |
| --- | --- | --- | --- |
| M1 | Django/DRF 스켈레톤, custom User, `/healthz`, 초기 Docker | ✅ 완료 | `docs/reviews/01-milestone1-skeleton.md` |
| M2 | 런타임 승격 `[소유]` + accounts 도메인 확장 `[위임]` | ✅ 완료 | `docs/reviews/02-milestone2-review.md` |
| M3 | 도메인 앱 4종 · 모델 7종 · 마이그레이션 · Admin | ✅ 완료 | `docs/reviews/03-milestone3-review.md` |
| **M4** | **API 구현 — 43 엔드포인트 (인증 포함)** | 🔜 **착수 준비** | SPEC-001~012 (§5) |
| M5 | 스모크 테스트 · 문서 마감 | ⏸ 대기 | `docs/smoke-test.md`는 M5 산출물 |

## 3. 구현 현황 (실측 2026-09-08)

### 완성된 것

| 계층 | 내용 |
| --- | --- |
| 모델 | **11종** — `User` `UserRole` `RoleGrant` `GoogleIdentity` `AdvisorApplication` `Concern` `Assignment` `Advice` `AdviceHistory` `Feedback` `Notification` |
| 마이그레이션 | 6개, 전부 적용됨. 부분 유니크 3종의 `WHERE` 절 Owner 육안 확인 완료 |
| Admin | 11종 등록. 감사 모델 view-only, 상태 필드 readonly(승인 부수효과 우회 방지) |
| 런타임 | 멀티스테이지 Dockerfile(비루트 uid 10001, gunicorn ×3), compose 2서비스, healthcheck |
| 설정 | `config/settings/` 4분할. **DRF 설정 완료**(SessionAuthentication, IsAuthenticated, PageNumberPagination 20) |
| 공통 | `common/uuid7.py`, `common/taxonomy.py` (11키) |

### 비어 있는 것

| 계층 | 현황 |
| --- | --- |
| **API** | **0 / 42.** 5개 앱 어디에도 `serializers.py` `views.py` `permissions.py` `urls.py` `services.py`가 없다 |
| **라우팅** | `config/urls.py`는 10줄. `healthz`와 `admin/`뿐. `/api/v1/` 프리픽스 자체가 없고 라우터도 `include()`도 없다 |
| **테스트** | **0건.** 테스트 파일 없음, 테스트 러너 실행 이력 0회 |
| DRF 소비 | 설정만 있고 소비하는 코드가 한 줄도 없다 — M1 이후 검증된 적 없는 잠재 리스크 |

> `/healthz`는 43개 중 유일하게 구현된 엔드포인트이며 순수 `JsonResponse`다. DRF를 거치지 않는다.

## 4. M4 진입 차단 항목

착수 **전에** 처리한다. 전부 SPEC-000 없이 각 SPEC의 Open Questions로 분산 처리하되, ✱ 표시는 SPEC-001 안에서 해소해야 한다.

| # | 항목 | 출처 | 처리 위치 |
| --- | --- | --- | --- |
| 1 ✱ | **CSRF 부트스트랩 경로 확정** — 미해결 시 회원가입 자체가 막힌다 | UX C-8 / §8-1 | SPEC-001 |
| 2 ✱ | 재퀴즈 — 학습 부채 ④(401/403/409) ⑤(atomic). **M4 착수 필수 조건** | M2 리뷰 (퀴즈 42/100) | SPEC-001 (실물로 해소) |
| 3 | CLOSED 전이를 사용자 API로 열지, 표시 전용으로 둘지 | UX C-2 / model.md O-3 | SPEC-004 |
| 4 | 비익명 고민의 조언가측 표시명 + alias 공백 폴백 책임 | UX C-6 · C-7 | SPEC-006 |
| 5 | 알림 `target_url` ↔ 프론트 라우트 규약 | UX C-10 / model.md O-6 | SPEC-011 |
| 6 | Google 첫 가입 닉네임 확인 온보딩 여부 | UX C-11 | SPEC-002 |
| 7 | `is_submitted` 응답 노출 (#21/#27/#31) | UX §8-2 | SPEC-007 |
| 8 | 작성자 한정 `reject_reason` 조건부 노출 (#27) | UX §8-3 | SPEC-008 |
| 9 | `expected_version` 요청 필드 (#33) — 없으면 명세된 412가 동작하지 않는다 | UX §8-4 | SPEC-008 |
| 10 | `display_alias` 응답 포함 (#18) | UX §8-5 | SPEC-004 |

**신규 엔드포인트를 만들면 CLAUDE.md §16 승인 게이트 대상이다.** 권고: CSRF는 기존 GET에 `ensure_csrf_cookie`를 적용해 엔드포인트 수를 43으로 유지한다. 알림 일괄 읽음(UX §8-6)은 Phase 3로 미룬다.

## 5. M4 SPEC 로드맵

`docs/api.md` §3 요약표 번호 기준. **SPEC-001만 정의되어 있고 나머지는 로드맵이다** — 스켈레톤 원칙 "필요할 때 생성한다"에 따라 착수 시점에 만든다.

| SPEC | 범위 | api.md # | 개수 | 선행 | 라우팅 |
| --- | --- | --- | --- | --- | --- |
| **001** | **로컬 세션 인증 + CSRF + 테스트 하네스** | 1,2,3,4,7 | 5 | — | `[위임]`+`[읽기]` |
| 002 | Google OAuth 연동 | 5,6 | 2 | 001 | `[위임]` ⚠️ |
| 003 | 사용자 프로필 · 역할 전환 | 8,9,10 | 3 | 001 | `[위임]` |
| 004 | 고민 — 사용자측 (생성/목록/상세/소프트삭제) | 16,17,18,19 | 4 | 003 | `[위임]` |
| 005 | 관리자 고민 조회 · 배정 | 22,23,24,25 | 4 | 004 | `[위임]` |
| 006 | 조언가 배정 고민 조회 | 20,21 | 2 | 005 | `[위임]` |
| 007 | 조언 작성 · 수정 · 삭제 · 내가 쓴 목록 | 28,29,30,31 | 4 | 006 | `[위임]` |
| 008 | 조언 열람 + 관리자 검토 승인/반려 | 26,27,32,33 | 4 | 007 | `[위임]` |
| 009 | 조언가 신청 · 심사 (첫 승인 부수효과) | 11~15 | 5 | 003 | `[위임]`+`[읽기]` |
| 010 | 피드백 | 34~38 | 5 | 008 | `[위임]` |
| 011 | 알림 조회 | 39,40,41 | 3 | 009,008 | `[위임]` |
| 012 | 관리자 역할 부여 · 회수 | 42,43 | 2 | 003 | `[위임]` |
| | | | **43** | | |

⚠️ **SPEC-002 주의**: Google OAuth 토큰 교환에 HTTP 클라이언트가 필요한데 `requests`·`authlib` 모두 미설치다. 표준 라이브러리(`urllib.request` + `json`)로 직접 구현하거나 패키지를 추가해야 하며, **후자는 §16 승인 게이트**다. SPEC-002를 뒤에 둔 이유는 ADR-002상 모든 인증 경로가 같은 세션을 발급하므로 나머지 41개가 이 결정을 기다릴 필요가 없기 때문이다.

## 6. 문서 부채

| # | 항목 | 상태 |
| --- | --- | --- |
| 1 | `model.md` drift 6건 기록 대기 | 미해소 — 해당 SPEC에서 처리 |
| 2 | `model.md` O-1 `domain_category` enum 확정 | 코드는 7종으로 확정됐으나 문서는 미결 (순환 참조) |
| 3 | `api.md`의 `is_deleted` 표기를 `deleted_at` 파생 필드로 정리 | UX C-1 |
| 4 | `docs/smoke-test.md` 부재 | M5 산출물 — 지금 만들지 않는다 |
| 5 | `model.md` O-2 `decision_context` max_length | 코드 4000, 문서 미결 |

## 7. 학습 부채

`docs/00-project/LEARNING_DEBT.md` — 9건, 그중 2건(④⑤)이 **M4 차단**.

드릴 #2(마이그레이션 실패), M3 퀴즈, WB-1(백지 재현)은 2026-09-08 Owner 결정으로 **Phase 3 이월**했다(속도 우선). 부채는 소멸하지 않고 원장에 남는다.

## 8. 다음 최소 작업 단위

> **SPEC-001 TASK-001 — 테스트 하네스 부트스트랩.**
> `tests/` 레이아웃을 만들고, 인증 계약(401 vs 403)에 대한 **실패하는 테스트**를 먼저 작성해 실패를 확인한다. 판정 장치가 먼저 선 뒤에 구현에 들어간다.

시작 방법은 `docs/00-project/VSCODE_MIGRATION_PLAYBOOK.md` Step 5.
