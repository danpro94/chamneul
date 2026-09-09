# Milestone 4 정의 — API 구현: 인증 포함 43개 엔드포인트 (위임 + 검증 소유)

> 성격: **마일스톤 계획 문서** (초안 — Owner 승인 대기).
> 근거: CLAUDE.md §4·§5·§7·§8·§10, docs/api.md v1, docs/model.md §5(Service-Layer Constraints), ADR-002·ADR-003, docs/reviews/02 §0 로드맵, docs/ux/01-phase2-screen-flows.md §7~§10.

| 항목 | 값 |
| --- | --- |
| 날짜 | 2026-07-08 (초안) |
| 선행 완료 | M3 모델 7종 + 마이그레이션 적용·AC 검증 (`15317cb`까지 push 완료) |
| 라우팅 | 코드 [위임] / **스모크 검증·운영 확인 [소유]** |
| 다음 | M5 — 스모크 테스트 + 문서 정리 (Phase 2 종료) |

---

## 0. 이월 항목 (Owner 결정 2026-07-08: M4 완료 후 일괄 처리)

| # | 항목 | 처리 시점 |
| --- | --- | --- |
| 1 | 드릴 #2 (마이그레이션 실패 — showmigrations 판독·롤백) | M4 완료 후 |
| 2 | M3 퀴즈 + M3 리뷰 노트(`03-milestone3-review.md`) | M4 완료 후 (M4 퀴즈와 통합 가능) |
| 3 | WB-1 백지 재현 (M2부터 2회 이월) | M4 완료 후 |
| 4 | model.md 문서 drift 6건 반영 (taxonomy 위치, reject_reason Null 표기, §9 search_fields, §10 created_at 문구 등 — data-modeler 리뷰) | M3 리뷰 노트와 함께 |

**학습 부채 원장(누적)**: M2 9건(최우선: 401/403/409 — M4 권한 구현이 실전 재학습 기회, atomic) + M3 2건(부분 유니크 "종결 ≠ 비활성" 경계, `with_deleted()` 호출 vs 제약 문법) + 이월 게이트 3건. M4 퀴즈에서 일괄 재검증.

---

## 1. M4 목표 (한 줄)

**"api.md v1의 43개 엔드포인트 전부를 세션 인증 단일 전략(ADR-002) 위에서 구현하고, 상태 전이·부수효과를 서비스 레이어로 강제하여 Phase 2 기능 표면을 완성한다."**

## 2. 착수 전 Owner 결정 필요 (블로킹 — 코드 생성 전 확정)

| # | 결정 | 선택지 / 권고 | 출처 |
| --- | --- | --- | --- |
| D-1 | CSRF 부트스트랩 경로 | (권고) 기존 GET(`/users/me` 401 응답 포함)에 `ensure_csrf_cookie` — 신규 엔드포인트 없이 해결 | UX C-8 |
| D-2 | 비익명 고민의 조언가측 표시명 | serializer 파생 필드(컬럼 불요). 정책만: `is_anonymous=false ∧ alias=""`일 때 nickname 노출 vs 폴백 문구 | UX C-6/C-7, data-modeler I-2 |
| D-3 | UX발 API 응답 보강 3건 수용 여부 | `is_submitted` 노출(#21/#27/#31) · 작성자 한정 `reject_reason`(#27) · `expected_version`(#33) — 전부 저비용, api.md 갱신 동반 | UX §8 |
| D-4 | Concern CLOSED 전이 | (권고) Phase 2는 Django Admin으로만 닫기(표시 전용) — 신규 API 없음. CLAUDE.md §6.6 문구와의 긴장은 M5 문서에 기록 | UX C-2 |
| D-5 | Google OAuth 구현 수단 | **확정(Owner 2026-07-09): A — 표준 라이브러리(urllib) 직접 호출 + Google tokeninfo 검증. 신규 패키지 없음, 신규 ADR 없음.** 2026-07-08에 잠정 채택했던 C(google-auth)는 **폐기**(ADR-005 삭제) — ADR-002 세션 단일 전략 유지, 서드파티 인증 패키지 미도입. `requests` 전이 의존을 피하고 §4/§16 게이트 없이 진행 | CLAUDE.md §4 |
| D-6 | O-1 DomainCategory 확정 | 잠정안(한국어 값) 유지 여부 — 실데이터 축적 전 확정 권고 | model.md §11 |
| D-7 | 테스트 범위 | **확정(Owner 2026-09-09): 도입.** Django test runner + PostgreSQL 테스트 DB(`config/settings/test.py`)로 핵심 3축(인증 플로우, 권한 매트릭스 401/403/404/409, 상태 전이+부수효과)을 커버한다. 신규 테스트 패키지 미도입(pytest 등 §16 게이트 회피). M4-5부터는 **AC를 실패하는 테스트로 먼저 작성한 뒤 구현**한다(test-first). 기 구현분 M4-1~M4-4의 소급 테스트는 M4-5 진행과 병행해 채운다 | CLAUDE.md §12 |
| D-8 | 알림 target_url 규약 / Google 첫 가입 온보딩 | UX C-10·C-11 — 프론트 구현 전까지 유예 가능(target_url은 API 경로 아닌 "프론트 라우트 키"로 잠정) | UX §10 |

## 3. 범위 — 코드 `[위임]` (모듈 단위 커밋 8개)

**작성 주체: AI 생성 + 코드+설명 동시 + 모듈별 이해 확인 질문.** Dockerfile/docker-compose*/.env* 불가침. 상태 전이·부수효과는 전부 `services.py`(model.md §5 표), 접근 제어는 `common/permissions.py` + 객체 수준 검사(§10).

| # | 모듈 (커밋 단위) | 내용 | api.md |
| --- | --- | --- | --- |
| M4-1 | 인증 기반 | signup(자동 로그인)/login/logout, 세션 정책(ADR-002: sessionid·HttpOnly·SameSite=Lax·14일 슬라이딩), CSRF(D-1), DRF 공통 설정(페이지네이션·예외 핸들러) | 1~4 |
| M4-2 | users/me | 프로필 조회/수정, 역할 목록, active-role 전환(보유 UserRole 검증 — model.md §5) | 7~10 |
| M4-3 | Google OAuth | authorize 리다이렉트 + callback(검증 이메일 링크, GoogleIdentity, 동일 세션 발급) | 5~6 |
| M4-4 | advisor-applications | 제출/내 상태 + admin 목록/상세/심사. **승인 부수효과 서비스**: UserRole(ADVISOR)+RoleGrant+Notification, atomic | 11~15 |
| M4-5 | concerns | user CRUD(소프트 삭제) + advisor 배정 목록/상세 + admin 목록/상세/배정/해제. **상태 전이 서비스**: SUBMITTED↔ASSIGNED, 배정 알림 | 16~25 |
| M4-6 | advice + feedback | 작성(draft/제출)/수정(version+1, AdviceHistory 스냅샷)/삭제/조회(APPROVED만 사용자 노출 §6.2) + admin 리뷰(ANSWERED 전이+알림) + feedback CRUD/admin | 26~38 |
| M4-7 | notifications | 목록(unread_count)/상세/읽음 — 수신자 객체 수준 검사 | 39~41 |
| M4-8 | admin roles | grant/revoke + RoleGrant 기록 + 가드 3종(자기 ADMIN 회수·마지막 ADMIN·미보유 → 409, ADR-003) | 42~43 |

공통 규칙: 명시적 Serializer 분리(list/detail/admin — §8, intended_lane은 admin 상세만), N+1 점검(select_related/prefetch_related — §8·ADR-001), 매 모듈 `check`+`ruff`+`manage.py test`(D-7 확정).

## 4. 명시적 비범위

* 프론트엔드 구현 (docs/ux/01은 사양 문서로만 소비)
* outcome tracking / trust score / 매칭 알고리즘 (Phase 3)
* 사용자 신청 철회 API(WITHDRAWN), 사용자 CLOSED 전이 API(D-4 채택 시), 알림 일괄 읽음(UX §8-6 — M5 재검토)
* 브루트포스 로그인 방어 (Phase 3 — §10, M5 스모크 노트에 갭 명시)
* Redis 세션 (ADR-002 후속)

## 5. 수용 기준 (AC)

- [ ] 43개 엔드포인트가 api.md와 URI(§7)·메서드·상태 코드 일치 — Owner가 스모크 시나리오로 실측
- [ ] 세션 쿠키 실측: HttpOnly·SameSite=Lax 확인, 로그아웃 시 서버 세션 삭제+`Max-Age=0` (Secure는 로컬 예외 — 문서화)
- [ ] CSRF: 토큰 없는 상태 변경 요청 → 403 실측
- [ ] 권한 매트릭스 실측: 비로그인 401 / 역할 없음 403 / 타인 자원 404 or 403 / 상태 충돌 409 (부채 ④ 실전 재검증)
- [ ] §6.2: 사용자에게 APPROVED 외 advice 비노출 실측 (PENDING advice가 목록·상세·카운트 어디에도 안 보임)
- [ ] 부수효과 3종 실측: 신청 승인→역할+감사+알림 / 조언 승인→ANSWERED+알림 / 배정→ASSIGNED+알림
- [ ] 소프트 삭제: 삭제된 concern이 사용자 API에서 404, admin `include_deleted`로만 조회
- [ ] 목록 API N+1 없음 (쿼리 로그로 확인)
- [ ] `check` 0 issues / `makemigrations --check` No changes / `ruff` 통과 / `manage.py test` 통과(D-7 확정)

## 6. 학습 게이트 (Owner 결정에 따라 M4 완료 후 일괄)

| 게이트 | 내용 | 예산 |
| --- | --- | --- |
| 드릴 #2+#3 | 마이그레이션 실패(이월) + 잘못된 env(DB 비밀번호 오타 → 부팅 로그 인증 실패 추적) | 각 ≤30분 |
| 통합 퀴즈 | M3+M4 + 부채 원장 일괄 재검증 (401/403/409는 M4 구현 경험 후 재출제) | 15분 |
| WB-1 | 이월분 | 45분 |
| 리뷰 노트 | 03-milestone3-review + 04-milestone4-review (Owner 선요약 5줄 형식 준수) | 각 10분+ |

## 7. 진행 순서

```
1) Owner: §2 결정 D-1~D-8 확정 (특히 D-1~D-5는 블로킹)
2) [위임] api.md 갱신 (D-3 수용분 + C-1 is_deleted 표기 정리) → Owner 확인
3) [위임] M4-1 → M4-8 모듈 순차 구현 (모듈별 커밋 + 설명 + 검증)
4) Owner: AC 스모크 실측 (§5)
5) 게이트 일괄 (§6) → 리뷰 노트 → M5 착수
```

## 8. 리스크 & 열린 결정

| # | 리스크 | 처리 |
| --- | --- | --- |
| 1 | Google OAuth는 외부 의존(콘솔 설정·redirect URI) — 로컬 검증에 GOOGLE_CLIENT_ID/SECRET 필요 | .env.example에 키 이름만 추가(§10), 미설정 시 OAuth 경로만 비활성화되는 구조로 구현. 실검증은 Owner 콘솔 준비 후 |
| 2 | 43개 일괄 구현은 §9 "큰 패치 금지"와 긴장 | 모듈 8커밋 분할 + 모듈마다 검증 (M3 방식 검증됨) |
| 3 | active_role↔UserRole 정합(M2 리스크 #3) | M4-2 역할 전환 서비스에서 강제 — 구현 시 M2 갭 해소 기록 |
| 4 | 세션·CSRF 구현 후 보안 리뷰 필요 | M4-1·M4-3 완료 시점에 `security-reviewer` 서브에이전트 리뷰 1라운드 |
| 5 | 브랜치+PR 전환(M2 리뷰 노트 제안) | M4부터 적용할지 Owner 결정 — 미적용 시 main 직커밋 유지 |

## 9. 완료 정의 (DoD)

§5 AC 전부 실측 통과 + 모듈 커밋 8개 + security-reviewer 리뷰(블로커 0) + api.md 갱신분 정합 → **M4 종료.** (§6 게이트는 M4 종료 직후 일괄 수행 — Owner 결정 2026-07-08)
