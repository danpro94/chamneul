# DECISION_INDEX — 결정 색인

> **이 문서가 Notion DB 수기 관리를 대체한다.**
> 원칙: **내용을 복사하지 않는다.** 결정 ID → 어디에 있는지 → 상태만 담는다. 그래서 유지 비용이 0에 수렴한다.
> 근거: ADR-005 §4.1 (Notion 은퇴)

| 최종 갱신 | 2026-09-08 |
| --- | --- |

---

## 1. Architecture Decision Records

| ID | 제목 | Status | 결정한 것 |
| --- | --- | --- | --- |
| ADR-001 | 로컬 컨테이너 기반 MVP 개발 아키텍처 | Accepted | Django+DRF, PostgreSQL 전용, Docker Compose, `/healthz`, 인증=Session |
| ADR-002 | Session 인증 정책 | Accepted | 쿠키 `sessionid`, HttpOnly+Secure+SameSite=Lax, 14일, 슬라이딩 갱신, 서버 세션 삭제. **ADR-001 Decision 4(JWT 잠정안) supersede** |
| ADR-003 | ADMIN 역할 부여·해제 | Accepted | 첫 ADMIN은 `createsuperuser`, 부여 `POST /admin/users/{user-id}/roles`, 회수 `DELETE .../roles/{role}` |
| ADR-004 | 전략 문서 공개 범위 분할 | Accepted | 3단계 공개 등급. 신뢰 점수 설계·조언자 평가 모델·승인 결정 트리는 `docs/_private/`로 분리 |
| ADR-005 | 문서 체계 AI-Native/Spec-Driven 재정렬 | Accepted | Notion 은퇴, source of truth 재정의, `specs/` 도입. **CLAUDE.md §2·§3·§17 supersede, §13 확장** |

> ADR-004는 **번호가 재사용된 이력**이 있다. 이전 ADR-004(postgres 전용 + 소프트 삭제)는 삭제되고 본문이 CLAUDE.md §4·§6.6으로 흡수되었다.

**대기 중**: ADR-006 — SPEC 루프 + 소유권 라우팅의 프로세스 승격. **SPEC-001 완료 후** 작성한다 (ADR-005 §10-1).

## 2. Owner 결정 아카이브 (2026-06)

`docs/api.md`와 `docs/model.md`를 만든 결정들이다. 전문은 **`docs/00-project/DECISION_ARCHIVE_2026-06.md`** 한 곳에 있다.

| 그룹 | 개수 | 주제 |
| --- | --- | --- |
| Q1 ~ Q22 | 22 | API 명세 정합성 세션 (2026-06-22). URI 규약, 사용자 자원 통일, 응답 필드 노출 범위, 상태 코드 정책 |
| M1 ~ M8 | 8 | 모델 정합성 세션 |
| D1 ~ D6 | 6 | 도메인 규칙 |
| G1 ~ G5 | 5 | 도구·의존성. **G5 = pytest 미도입, Django 기본 test runner 사용** |

자주 참조되는 것:

| ID | 결정 |
| --- | --- |
| Q4 | 사용자 소유 자원을 `/api/v1/users/me/{resource}`로 통일 |
| Q13 | 회원가입 시 자동 로그인 |
| Q15 | `advisor_type`을 응답에 노출하지 않음 |
| G5 | pytest 등 별도 테스트 패키지 미도입 |

## 3. CLAUDE.md 조항 상태

| 조항 | 상태 |
| --- | --- |
| §0 목적, §1 Phase | 유효 |
| **§2 Source of Truth Order** | ⚠️ **ADR-005로 대체.** Notion 은퇴 |
| **§3 Current Known Project Tree** | ⚠️ **ADR-005로 대체.** README.md로 이관 |
| §4 기술 결정 | 유효 — PostgreSQL 전용, 세션 인증 단일 전략 |
| §5 MVP 범위 | 유효 — 43 엔드포인트 |
| **§6 도메인 규칙 전체** | 유효 — **무손실 보존.** taxonomy·상태 enum·소프트 삭제·버저닝 |
| §7~§12 | 유효 |
| **§13 Documentation Rules** | ➕ **ADR-005로 확장.** 기존 유지 대상은 전부 보존 |
| §14 리뷰 노트, §15 인터랙션 | 유효 |
| **§16 Approval Gates** | 유효 — **supersede되지 않았다.** ADR-005 §4.5가 명확화만 함 |
| **§17 First Workflow** | ⚠️ **ADR-005로 대체.** "Notion export 대기" 단계 삭제 |

## 4. 미결 — UX 사양발 (M4 차단)

`docs/ux/01-phase2-screen-flows.md` §7 충돌표 · §8 개선 · §10 Owner 결정.

| ID | 내용 | 상태 | 처리 위치 |
| --- | --- | --- | --- |
| C-1 | `is_deleted` 표기를 `deleted_at` 파생 필드로 정리 | 미결 (문서만) | 문서 부채 |
| C-2 / O-3 | CLOSED 전이를 사용자 API로 열지, 표시 전용으로 둘지 | **미결 — Owner 결정 필요** | SPEC-004 |
| C-3 / §8-4 | `#33` 요청에 `expected_version` 추가 — 없으면 명세된 412가 동작 안 함 | 미결 | SPEC-008 |
| C-4 / §8-2 | `#21/#27/#31` 응답에 `is_submitted` 노출 | 미결 | SPEC-007 |
| C-5 / §8-3 | `#27` 작성자 한정 `reject_reason` 조건부 노출 | 미결 | SPEC-008 |
| C-6 · C-7 | 비익명 고민의 조언가측 표시명 + alias 공백 폴백 책임 | **미결 — Owner 결정 필요** | SPEC-006 |
| C-8 / §8-1 | **CSRF 부트스트랩 경로** — 미해결 시 회원가입 자체가 막힌다 | **미결 — SPEC-001 차단** | SPEC-001 |
| C-9 | 관리자용 사용자 검색 API 부재 | 설계로 흡수 (UUID 직접 입력) | — |
| C-10 / O-6 | 알림 `target_url` ↔ 프론트 라우트 규약 | **미결 — Owner 결정 필요** | SPEC-011 |
| C-11 | Google 첫 가입 닉네임 확인 온보딩 여부 | **미결 — Owner 결정 필요** | SPEC-002 |
| C-12 | mvp-scope와 api.md의 조언가 고민 목록 해석 차이 | ✅ 해소 — 배정 목록으로 확정 | — |
| C-13 | CLAUDE.md §2·§17 파일명 drift | ✅ **해소 — ADR-005** | — |
| §8-5 | `#18` 응답에 `display_alias` 포함 | 미결 | SPEC-004 |
| §8-6 | 알림 일괄 읽음(read-all) | **Phase 3 이월 권고** — 신규 엔드포인트라 §16 게이트 | — |
| §8-8 | `#12`의 404-as-empty 시맨틱 유지 여부 | 미결 | SPEC-009 |

## 5. 미결 — 모델 사양발

`docs/model.md` §11.

| ID | 내용 | 상태 |
| --- | --- | --- |
| O-1 | `domain_category` enum 확정 | ⚠️ **순환 참조** — 코드는 7종(IT/경영/인사/금융/의료/교육/기타)으로 확정됐으나 문서는 model.md §11로 미룸 |
| O-2 | `decision_context` max_length | 코드 4000, 문서 미결 |
| O-3 | → C-2와 동일 | 미결 |
| O-6 | → C-10과 동일 | 미결 |
| O-4·5·7·8 | 기타 | 미결 — 비차단 |

`docs/api.md` §6에 OQ-1~OQ-8이 별도로 있다 (전부 비차단).

## 6. 학습 부채

`docs/00-project/LEARNING_DEBT.md` — 9건. **④(401/403/409)·⑤(atomic)이 M4 차단.**

## 7. 이번 전환의 결정 (2026-09-08)

| # | 결정 | 기록 위치 |
| --- | --- | --- |
| 1 | CLAUDE.md는 ADR-005 최소 개정. 본문 무수정 | ADR-005 §4 |
| 2 | 학습 게이트 속도 우선 축소 — 라우팅 태그만 유지, 드릴·퀴즈·백지재현은 Phase 3 이월 | ADR-005 §10-2, LEARNING_DEBT §3 |
| 3 | 첫 SPEC = 로컬 세션 인증 5개 + 테스트 하네스. Google OAuth는 SPEC-002로 분리 | STATUS.md §5 |
| 4 | Notion 수기 문서화 폐지 | ADR-005 §4.1 |
| 5 | `.claude/agents/` 3종 커밋 여부는 Phase 3에 재결정 | ADR-005 §10-2 |

## 8. 결정을 추가하는 방법

1. **아키텍처 trade-off** → `docs/adr/ADR-NNN-*.md` 신규 작성 후 §1 표에 한 줄 추가
2. **SPEC 범위 안의 선택** → 해당 `specs/SPEC-NNN/spec.md`의 Open Questions에 기록, 해소되면 `handoff.md`로
3. **세션 중 나온 Owner 결정** → `README_AIUSAGE.md`의 "인간 결정" 필드
4. **미결 항목** → 본 문서 §4·§5에 등재하고 처리 위치를 지정

> 어느 경우에도 **채팅에만 남기지 않는다.** 채팅은 저장소가 아니다.
