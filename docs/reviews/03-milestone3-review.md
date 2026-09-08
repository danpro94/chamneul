# M3 리뷰 노트 — 도메인 앱 모델 4종 (위임 + 마이그레이션 운영 소유)

> §14 리뷰 노트 + learning/02 §6 explain-first. 정의 문서: `03-milestone3-definition.md`.
> 작성일 2026-09-08 (**소급**). 커밋: `e3db9c1` `de2e3a7` `7d5e2f0` `82d5e6c` `a3823d1` `05f60b2` · `15317cb`(UX)

## 0. 이 노트가 늦은 이유

M3 코드는 2026-07-08에 끝났으나 리뷰 노트가 작성되지 않아 **M3가 형식상 미종료 상태**로 두 달 남아 있었다 (`03-milestone3-definition.md` §9 DoD가 이 문서를 요구한다).

2026-09-08 VS Code 전환 작업 중에 이 사실이 드러나 소급 작성한다. 검증 실측치는 `README_AIUSAGE.md` 2026-07-08 항목에 이미 기록되어 있으므로 **짧게 쓴다.**

**Owner 선요약은 없다.** explain-first는 작업 직후 기억으로 쓰는 장치인데 두 달이 지나 그 조건이 성립하지 않는다. 없는 것을 있는 척 채우지 않는다 — 이것 자체가 학습 부채로 남는다 (`LEARNING_DEBT.md` 부가 항목: 선요약 습관화).

## 1. 무엇이 바뀌었나

모델 **7종** + Admin 7종 + 마이그레이션 4개. 앱 단위 4커밋으로 분할했다 (정의 §8 리스크 3 대응 — "7모델 일괄 생성은 §9 큰 패치 금지와 긴장").

| 앱 | 모델 | 핵심 |
| --- | --- | --- |
| `advisors` | `AdvisorApplication` | 상태 5종. `advisable_concern_types`는 `ArrayField`. **부분 유니크** `display_name WHERE status IN (PENDING, REVIEWING, APPROVED)` |
| `concerns` | `Concern` | **소프트 삭제** `deleted_at` + 매니저 분리. `default_manager_name="objects"` / `base_manager_name="all_objects"` |
| `concerns` | `Assignment` | **부분 유니크** `(concern, advisor) WHERE is_active` |
| `advice` | `Advice` | 상태 5종, `version` 감사 정수. **부분 유니크** `(concern, advisor) WHERE status != DELETED` |
| `advice` | `AdviceHistory` | append-only 스냅샷, `(advice, version)` 유니크 |
| `advice` | `Feedback` | `advice` OneToOne, score 1~5 |
| `notifications` | `Notification` | 타입 5종, `actor_user` SET_NULL |

병렬로 `docs/ux/01-phase2-screen-flows.md`(317줄) — 43개 엔드포인트 API-to-screen 매핑 + 충돌 13건.

## 2. 왜 이렇게 했나

* **`base_manager_name = "all_objects"`** — 기본 매니저를 소프트 삭제 제외로 바꾸면 `Advice → Concern` FK 역참조가 삭제된 고민에 닿지 못해 조언 레코드가 고아가 된다. 감사 목적상 조언은 보존해야 하므로 base manager는 전체를 봐야 한다. **M3에서 가장 미묘한 결정이다.**
* **`common/taxonomy.py`** — `advisors`가 `concerns`를 import하지 않게 하려는 배치. 앱 간 결합을 끊는다.
* **Admin에서 status·version·review 필드 readonly** — 직접 편집하면 승인 부수효과(역할 부여·감사 row·알림·고민 상태 전이)를 우회한다. 부수효과가 M4 서비스 레이어에 생길 때까지 잠가 둔다 (data-modeler 리뷰 I-1, 커밋 `05f60b2`).
* **`RoleGrant` add/change/delete 전부 `False`** — 감사 무결성 (ADR-003 §3).

## 3. 검증 결과 (실측 — 2026-07-08)

`manage.py check` 0 issues · `makemigrations --check` No changes · `ruff check` 통과.
`sqlmigrate` 출력에서 **부분 유니크 3종의 `WHERE` 절을 Owner가 직접 확인**.
Owner가 컨테이너에서 `migrate` 적용 성공, `showmigrations`로 4개 앱 확인, Admin 7종 조회, shell에서 소프트 삭제 기본 감춤 실측.
`data-modeler` 서브에이전트 리뷰: 블로커 0, 메이저 1건(I-1)은 즉시 해소.

## 4. DevOps 설명 포인트

* **부분 유니크 인덱스가 왜 필요한가** — 소프트 삭제 모델에 평범한 `unique=True`를 걸면 탈퇴한 사용자의 이메일이 신규 가입을 영구히 막는다. `WHERE deleted_at IS NULL`이 그것을 푼다.
* **마이그레이션 의존 순서** — 교차 앱 FK(`advice → concerns` 등)가 있어 생성 순서가 강제된다. 앱 간 FK를 문자열 참조로 쓰는 이유이기도 하다.
* **`on_delete` 선택이 곧 데이터 보존 정책** — `CASCADE`(알림 수신자), `SET_NULL`(알림 행위자 — 행위자가 사라져도 알림은 남아야 한다), `PROTECT`(감사 row).

## 5. 보안 노트

`intended_lane`은 모델에만 존재하고 공개 응답 노출 금지 (§6.1). M4 serializer에서 강제된다.
`RoleGrant` Admin view-only. 고민 본문(`decision_context`, 최대 4000자)은 목록 API에 넣지 않는다 (§8).

## 6. 학습 게이트 — **미이수, Phase 3 이월**

| 항목 | 상태 |
| --- | --- |
| 드릴 #2 (마이그레이션 실패) | ❌ 미실시 — Phase 3 이월 |
| M3 퀴즈 | ❌ 미실시 — Phase 3 이월 |
| WB-1 백지 재현 | ❌ 미실시 — Phase 3 이월 |
| 이해 확인 질문 3개 | ⚠️ 부분 (1·2 부분, 3 통과) |

**2026-09-08 Owner 결정 (속도 우선 축소)**에 따른 이월이다. 폐지가 아니다 — `docs/00-project/LEARNING_DEBT.md` §3에 등재되어 있다.

정의 §9 DoD 기준으로 **M3는 조건부 종료**다: AC 전부 통과 + 앱 단위 4커밋 + 본 리뷰 노트는 충족, 학습 게이트는 미충족·이월.

## 7. M4로 넘어가는 것

| # | 항목 | 처리 위치 |
| --- | --- | --- |
| 1 | 부채 ④(401/403/409)·⑤(atomic) — **M4 착수 조건이었던 재퀴즈** | **SPEC-001**이 AC-011·AC-012로 실물 해소 |
| 2 | `model.md` drift 6건 기록 대기 | `STATUS.md` §6 문서 부채 |
| 3 | O-1 `DomainCategory` 확정 (코드 7종 확정 vs 문서 미결 — 순환 참조) | `DECISION_INDEX.md` §5 |
| 4 | UX 발 Owner 결정 5건 + API 개선 4건 | 각 SPEC의 Open Questions로 분산 |
| 5 | 비익명 표시명 정책 (C-6/C-7) | SPEC-006 |

## 8. 다음 개선

1. **리뷰 노트를 마일스톤 종료 시점에 쓴다.** 두 달 지나면 explain-first가 성립하지 않는다 — 이 노트가 그 증거다.
2. SPEC 단위 `handoff.md`로 옮겨 주기를 짧게 한다 (M3의 실패를 구조로 방지).
3. 정적 파일 서빙 갭 → M5 `docs/smoke-test.md`에 명시.
