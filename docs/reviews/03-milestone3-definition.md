# Milestone 3 정의 — 도메인 앱 모델/마이그레이션 4종 (위임 + 마이그레이션 운영 소유)

> 성격: **마일스톤 계획 문서** (완료 후 리뷰 노트는 별도 작성).
> 근거: CLAUDE.md §1·§5·§6, docs/model.md §3.5~3.11·§7, docs/reviews/02 §0 로드맵, docs/learning/02 §4.1.
> 문서 번호 주 (Owner 결정 2026-07-07): 번호는 마일스톤 번호를 따른다 — 정의 문서는 `NN-milestoneN-definition`, 리뷰 노트는 `NN-milestoneN-review`. M2 리뷰 노트는 `02-milestone2-review.md`.

| 항목 | 값 |
| --- | --- |
| 날짜 | 2026-07-06 (초안 — Owner 승인 대기) |
| 선행 완료 | M2 트랙 A+B (`156ded9`, `76b664e`) — 단 M2 DoD 잔여 3건 이월 (아래 §0) |
| 라우팅 | 코드 [위임] / **마이그레이션 적용·운영 [소유]** (learning/02 §4.1) |
| 다음 | M4 — API 구현 (인증 포함 43개 엔드포인트) |

---

## 0. M2 이월 항목 (M3 착수 전/중 처리)

| # | 항목 | 처리 시점 (권장) |
| --- | --- | --- |
| 1 | **WB-1** 백지 재현 (Dockerfile+compose+settings, 45분) | M3 코드 착수 **전** — 학습 부채 ⑦⑧(compose 병합 우선순위, 익명 볼륨 원리)의 자연 검증 수단 |
| 2 | M2 리뷰 노트(`02-milestone2-review.md`) — Owner 선요약 → AI 본문 → 커밋 | ✅ 2026-07-07 작성 완료 |
| 3 | README_AIUSAGE.md 갱신 (M2 분) | ✅ 2026-07-07 작성 완료 |

M2는 위 3건을 전제로 **조건부 종료** 상태다 (reviews/02 §9 DoD 기준).

---

## 1. M3 목표 (한 줄)

**"나머지 4개 도메인 앱(advisors·concerns·advice·notifications)의 모델 7종과 마이그레이션을 model.md 명세대로 완성하고, Owner가 마이그레이션 운영(적용·판독·롤백)을 직접 수행할 수 있게 한다."**

## 2. 범위 — 코드 `[위임]`

**작성 주체: AI 생성 + "코드+설명 동시" + 이해 확인 질문 3개** (learning/02 §5 위임 세션 프롬프트). Dockerfile/docker-compose*/.env* 는 Owner 소유 구역 — 불가침.

| # | 앱 | 모델 | 핵심 명세 |
| --- | --- | --- | --- |
| C-1 | advisors | `AdvisorApplication` | model.md §3.5. 상태 5종(§6.1), `intended_lane` 비공개 원칙, **부분 유니크** `display_name WHERE status IN (PENDING, REVIEWING, APPROVED)` |
| C-2 | concerns | `Concern` | model.md §3.6. **소프트 삭제**(`deleted_at` + 기본 매니저 제외 + `with_deleted()`, §6.6), 상태 4종, taxonomy v0(§6.5) |
| C-3 | concerns | `Assignment` | model.md §3.7. **부분 유니크** `(concern, advisor) WHERE is_active` |
| C-4 | advice | `Advice` | model.md §3.8. 상태 5종(§6.2), `version` 감사 정수(§6.7), **부분 유니크** `(concern, advisor) WHERE status != DELETED` |
| C-5 | advice | `AdviceHistory` | model.md §3.9. append-only 감사, `(advice, version)` 유니크, FK CASCADE |
| C-6 | advice | `Feedback` | model.md §3.10. 상태 3종(§6.3), `advice` OneToOne |
| C-7 | notifications | `Notification` | model.md §3.11. 타입 5종(§6.4), `actor_user` SET_NULL |
| C-8 | 공통 | Django Admin 등록 7종 | model.md §9 표 준수 (audit 모델 view-only, Concern soft-delete 토글 action) |
| C-9 | 공통 | 마이그레이션 생성 | 앱별 0001 — **적용은 Owner** (§3). 교차 앱 FK 의존 순서는 model.md §7.1 |

공통 규칙: PK는 `common.uuid7`(§1.2), enum은 TextChoices(§1.3), `created_at`/`updated_at` 패턴(§1.9), 앱 간 FK는 문자열 참조(§1.8), 부분 유니크는 마이그레이션 SQL에 `WHERE` 절로 등장해야 함(§10 Validation Checklist).

## 3. 범위 — 마이그레이션 운영 `[소유]`

Owner가 직접 수행하고 설명할 수 있어야 한다 (CLAUDE.md §11 "how migration is applied"):

* 컨테이너 안에서 `migrate` 적용, `showmigrations` 판독
* `sqlmigrate`로 부분 유니크 `WHERE` 절 확인 (모델 3종: C-1·C-3·C-4)
* 드릴 #2에서 마이그레이션 충돌·롤백 절차 수행 (§6)

## 4. 명시적 비범위 (Out of Scope)

* Serializer / ViewSet / Router / 권한 / 서비스 레이어 전부 → **M4**
* 알림 **발송 로직**(§6.4 생성 규칙의 구현) → M4 서비스 부수효과 (M3는 Notification 모델·타입만)
* Advice version 증가·AdviceHistory 스냅샷 **로직** → M4 (`AdviceService.update()`)
* outcome tracking / trust score / 매칭 알고리즘 → Phase 3 (CLAUDE.md §5)
* 새 서드파티 패키지 없음 (§16 게이트 해당 없음 — `django.contrib.postgres`는 §4 승인 목록)

## 5. 수용 기준 (Acceptance Criteria)

- [ ] `uv run python manage.py check` → 0 issues
- [ ] `uv run python manage.py makemigrations --check --dry-run` → No changes (마이그레이션 커밋 후)
- [ ] `uv run ruff check .` → 통과
- [ ] Owner가 컨테이너에서 직접 `migrate` 적용 성공, `showmigrations`로 4개 앱 확인
- [ ] `sqlmigrate` 출력에서 부분 유니크 3종의 `WHERE` 절을 Owner가 직접 확인 (model.md §10 체크리스트 항목)
- [ ] `Concern.objects`가 soft-deleted 제외 / `with_deleted()`가 포함 — shell에서 검증
- [ ] Django Admin에서 7종 모델 조회 가능 (audit 모델은 view-only 동작 확인)
- [ ] 이해 확인 질문 3개 답변 완료 (미답은 학습 부채 등록)

### 검증 명령 모음 (§12)

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
docker compose exec -T app python manage.py migrate
docker compose exec -T app python manage.py showmigrations
docker compose exec -T app python manage.py sqlmigrate advisors 0001   # WHERE 절 확인 (concerns/advice도 동일)
```

## 6. 학습 게이트 (learning/02 §4 예산: ≤55분)

| 게이트 | 내용 | 예산 |
| --- | --- | --- |
| Owner 선요약 | 리뷰 노트 전 5줄 (explain-first) | 10분 |
| 드릴 #2 | `chaos-coach` — **마이그레이션 실패**: 충돌 시나리오 주입 → `showmigrations` 판독 → 롤백 절차 (§4.2 카탈로그) | ≤30분 |
| 퀴즈 | `drill-master` 3~5문 — **M2 부채 ④(401/403/409)·⑤(atomic) 재출제 필수** + M3 신규(소프트 삭제 매니저, 부분 유니크, FK on_delete 정책) | 15분 |

드릴 #1 운영 개선 반영: 시작 시 타이머 가동 + 단계별 목표 시간 선고지.

## 7. 진행 순서 (세션 플랜)

```
0) [이월]      WB-1 백지 재현 + 채점 (M2 리뷰 노트·README_AIUSAGE는 2026-07-07 완료)
1) [위임 세션]  C-1~C-9 생성 — 코드+설명 동시, 이해 질문 3개
2) [소유]      Owner가 migrate 적용 + AC 검증 (§5)
3) [드릴 세션]  chaos-coach 드릴 #2 (마이그레이션 실패)
4) [채점 세션]  drill-master 퀴즈 → 학습 부채 갱신
5)             리뷰 노트(03-milestone3-review) + README_AIUSAGE 갱신 → M3 종료, M4 착수 가능
```

## 8. 리스크 & 열린 결정

| # | 리스크/결정 | 처리 |
| --- | --- | --- |
| 1 | 교차 앱 FK로 인한 마이그레이션 의존 순서 (advice→concerns 등) | model.md §7.1 순서 준수, 드릴 #2 소재로 활용 가능 |
| 2 | Concern 기본 매니저 교체가 Admin·향후 쿼리에 미치는 영향 (`with_deleted` 필요 지점) | 위임 세션에서 설명 필수 항목으로 지정 |
| 3 | 7모델 일괄 생성은 §9 "한 번에 큰 패치 금지"와 긴장 | 앱 단위 4커밋으로 분할 (advisors → concerns → advice → notifications) |
| 4 | M2 학습 부채 9건 누적 상태에서 신규 부채 추가 | 퀴즈에서 최우선 부채 ④⑤ 재검증, WB-1로 ⑦⑧ 해소 후 착수 권장 |

## 9. 완료 정의 (DoD)

§5 AC 전부 체크 + §6 게이트 통과 + 앱 단위 커밋 4개 + 리뷰 노트(03-milestone3-review) + README_AIUSAGE 갱신 → **M3 종료.**
