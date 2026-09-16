# 리뷰 노트 04 — M4 (api.md 44개 엔드포인트 전량 구현)

> 2026-09-17 작성. 계획 문서: [04-milestone4-definition.md](04-milestone4-definition.md) (착수 시점 스냅샷).
> 모듈별 상세는 [05-spec002-subagent-review.md](05-spec002-subagent-review.md), [06-spec003-notifications-roles.md](06-spec003-notifications-roles.md) 참조. 이 노트는 **M4 전체를 가로질러 본 것**을 담는다.

## 무엇이 바뀌었나

api.md v1.1의 **44개 엔드포인트 전량**이 구현됐다. 8개 모듈, 약 2개월(2026-07-09 ~ 09-16), 자동 테스트 **291개**.

| 모듈 | 엔드포인트 | 작업 단위 | 테스트 |
| --- | --- | --- | --- |
| M4-1 auth | #2·#3·#4·#44 | (SPEC 이전) | 0 → 스모크로 실환경 1회 |
| M4-2 users/me | #7·#8·#9·#10 | (SPEC 이전) | #10만 4개 |
| M4-3 Google OAuth | #5·#6 | (SPEC 이전) | 0 |
| M4-4 advisor applications | #11~#15 | (SPEC 이전) | 10 |
| M4-5 concerns | #16~#25 | SPEC-001 | 70 |
| M4-6 advice + feedback | #26~#38 | SPEC-002 | 118 |
| M4-7 notifications | #39~#41 | SPEC-003 | 38 |
| M4-8 admin roles | #42·#43 | SPEC-003 | 51(accounts 전체) |

**M4 중간에 작업 방식이 바뀌었다.** M4-1~M4-4는 "모듈 하나 = 커밋 하나"였고, ADR-006(2026-09-10) 이후 M4-5부터는 SPEC 단위 + TDD 루프(실패 테스트 먼저 → 최소 구현 → 검증 4종 → 커밋 → STATUS.md)로 전환했다. 테스트 수의 차이가 그 경계를 그대로 보여준다.

## M4를 가로질러 반복된 결함 유형 3가지

개별 SPEC 리뷰에는 각각 적혀 있으나, **같은 모양이 반복됐다는 사실**은 여기서만 보인다.

### 1. 검사하고 나서 바꾸는 코드 (TOCTOU)

| | 어디서 | 결과 |
| --- | --- | --- |
| M-1 | `advice.update_advice` | 데이터 유실 (SPEC-002 리뷰) |
| A-1 | `advisors.review_application` | 감사 행 2개 + 알림 2건 |
| A-3 | `accounts.set_active_role` ↔ `revoke_role` | 역할 없이 ADVISOR를 입은 상태 |
| — | `accounts.revoke_role`(마지막 관리자) | 관리자 0명 (선제 차단) |

**네 번 같은 모양이 나왔다.** 처음 두 번은 사고 후 수정이었고, 세 번째부터는 전수 점검으로 찾았으며, 네 번째는 설계 단계에서 막았다.

대응이 세 단계로 진화했다: ① 개별 수정 → ② `.claude/rules/coding.md`에 규칙 신설(2026-09-14) → ③ **규칙을 테스트로 승격**(2026-09-15, `StateTransitionLockingTests`가 발행 SQL에서 `FOR UPDATE`·잠금 순서·`update_fields` 범위를 직접 검사).

②에서 멈췄다면 다섯 번째가 나왔을 것이다. **A-1이 정확히 그렇게 생겼다** — 규칙은 있었는데 새 함수가 조용히 빠졌다.

### 2. 사본이 원본의 접근 규칙을 상속하지 않는다

알림 `message`에 고민 요약을 복사해 뒀고, #39가 그 사본을 읽는 첫 경로를 열자 **고민을 삭제해도 전 조언가가 계속 읽는** 상태가 됐다. CLAUDE.md §6.6의 "소프트 삭제는 모든 non-admin 쿼리에서 제외"가 **다른 테이블의 사본에는 닿지 않는다.**

같은 부류로 `base_manager_name = "all_objects"`가 있다 — FK 역참조는 소프트 삭제 필터를 우회한다. 둘 다 "규칙이 걸리는 범위"를 잘못 가정한 경우다.

### 3. Django Admin이 서비스 레이어를 우회한다

M3에서 Admin을 등록할 땐 서비스 레이어가 없었으므로 "Admin으로 운영한다"가 자연스러웠다. M4에서 서비스 레이어가 생기면서 그 화면들이 **부수효과를 건너뛰는 지름길**이 됐다.

2026-09-16에 5건을 한 번에 닫았다(B-01~B-05). 판단 기준 하나로 정리됐다: **가장 빠른 길에 기록이 없으면 감사 기록이 아니다.**

## 검증 방식에서 배운 것

### AC 전항 통과 ≠ 검증됨

SPEC-002는 AC-1~AC-11 전항 녹색 + 168개 테스트 상태에서 서브에이전트 리뷰에 **데이터 유실 1건과 500 크래시 1건**을 들켰다. 둘 다 개별 기능이 아니라 **기능 사이**에 있었다.

SPEC-003은 그 교훈을 AC에 선반영했고(AC-7 end-to-end, AC-8 왕복), 그럼에도 TASK-005의 AC 전수 대조에서 **미커버 1건**이 더 나왔다 — AC-8의 `payload` 키 검증이 5종 중 1종에만 적용돼 있었다. 코드는 옳았고 **검증이 비어 있었다.**

### 테스트 DB ≠ 실제 시스템

291개 테스트는 전부 테스트 전용 DB에서 돈다. "맨바닥에서 일어서는가"는 M5 스모크 테스트 전까지 미확인이었다. 같은 공백이 작은 규모로 이미 있었다 — 알림 `target_url` 5종은 **아무도 눌러본 적이 없어서** 옳다는 사실 자체가 미확인이었다.

### 추측한 수치는 틀린다

`assertNumQueries`를 추정으로 쓴 3번이 **전부 틀렸다**(원인: `IsAdmin`은 `UserRole` 조회를 한 번 더 한다). 측정 후 작성으로 바꾼 뒤로는 틀리지 않았다.

## 거버넌스에서 있었던 일

**SPEC 결정이 CLAUDE.md 조항을 ADR 없이 바꾼 사건이 한 번 있었다.** 2026-09-11의 SPEC-002 결정이 §6.7(`advice.version` 증가 규칙)을 실질적으로 변경했고, 2026-09-13 `api-architect` 리뷰가 잡아냈다. ADR-007로 사후 정리하면서 §16에 교훈을 명문화했다 — **"SPEC 결정이 CLAUDE.md 조항과 충돌하면 리뷰 시점이 아니라 결정 시점에 ADR이 필요하다."**

이후 SPEC-003·004의 결정 8건은 전부 착수 전에 CLAUDE.md 충돌 여부를 확인했고, ADR이 필요한 건은 없었다.

## 핵심 파일

| 영역 | 파일 |
| --- | --- |
| 권한 | [common/permissions.py](../../common/permissions.py) — `IsAdmin` / `IsActiveAdvisor` |
| 예외·응답 봉투 | [common/exceptions.py](../../common/exceptions.py) |
| 상태 전이 규칙 | [.claude/rules/coding.md](../../.claude/rules/coding.md) + `accounts.tests.StateTransitionLockingTests` |
| 작업 단위 | [specs/](../../specs/) SPEC-001~004 |
| 현황판 | [docs/00-project/STATUS.md](../00-project/STATUS.md) |

## 어떻게 테스트하나

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run python manage.py test                 # 291개
```

실환경 통과는 [docs/smoke-test.md](../smoke-test.md).

## DevOps 설명 포인트

**서비스 레이어가 왜 필요한가 — M4가 준 답.** 배정 하나를 만드는 일은 세 가지가 함께 일어나야 성립한다: `Assignment` 행, concern의 `SUBMITTED → ASSIGNED` 전이, 조언가에게 가는 알림. 이 셋이 흩어져 있으면 **어느 하나가 빠진 반쪽 상태**가 만들어지고, 그게 실제로 Django Admin 경로에서 일어나고 있었다.

서비스 함수 하나가 트랜잭션 하나를 감싸면 "전부 되거나 전부 안 되거나"가 보장된다. 그리고 **그 함수가 유일한 입구여야** 보장이 유지된다 — Admin을 view-only로 만든 이유다.

## 보안 노트

* 서브에이전트 리뷰 4회 실행(SPEC-002 2종, SPEC-003 2종, SPEC-004 1종). 블로커 1건·메이저 7건 전부 반영.
* 응답 필드 노출은 테스트로 키 집합을 고정했다 — `actor_user`·`payload`·이메일이 실릴 수 없다.
* 감사 기록(`RoleGrant`) append-only를 정적 확인했고, Admin 물리 삭제 경로도 닫았다.
* **남은 갭**: 브루트포스 방어 부재, 실제 경합 미재현, M4-1~M4-3 자동 테스트 0건 — 전부 [smoke-test.md](../smoke-test.md) §5에 기록.

## 다음 개선

| # | 항목 | 이동 |
| --- | --- | --- |
| 1 | M4-1~M4-3 자동 테스트 0건 | Phase 3 |
| 2 | 실제 경합 재현(`TransactionTestCase` + 스레드) | Phase 3 |
| 3 | 브루트포스 로그인 방어 | Phase 3 |
| 4 | 운영 설정(`DEBUG=False`) 경로를 한 번도 띄워보지 않음 | **Phase 3 최우선** |
| 5 | `Feedback.score` DB 체크 제약 | Phase 3 후보 |
| 6 | `advisor_status`가 회수 후에도 APPROVED로 표시 | M5 UX 검토 |

## 이 마일스톤에서 배운 것

**결함은 기능 안이 아니라 기능 사이에 있었다.** M4에서 나온 중대 결함 7건 중 단일 함수의 로직 오류는 **하나도 없다**. 전부 (a) 두 요청이 겹칠 때, (b) 한 기능이 만든 데이터를 다른 기능이 읽을 때, (c) 서비스 레이어를 우회하는 경로에서 나왔다.

그래서 검증도 그 방향으로 진화했다 — 단위 테스트 → 교차 검증 AC(AC-7·AC-8) → 발행 SQL 검사 → 맨바닥 스모크. 각 단계는 앞 단계가 못 보던 층을 본다.

**그리고 어느 단계도 다음 단계를 대신하지 못한다.** 291개가 녹색이어도 "실제로 일어서는가"는 별개의 질문이었고, 스모크 테스트를 돌리기 전까지 답할 수 없었다.
