# 리뷰 노트 06 — SPEC-003 (알림 #39~41 + 역할 #42~43)

> 2026-09-16 작성. 대상: `feat/spec-003-notifications-roles`. CLAUDE.md §14.

## 무엇이 바뀌었나

api.md #39~43 다섯 엔드포인트를 구현해 **44/44**에 도달했다. M4의 구현 구간이 끝났다.

| # | 엔드포인트 | 요지 |
| --- | --- | --- |
| 39 | `GET /api/v1/notifications` | 내 알림 목록 + `unread_count` |
| 40 | `GET /api/v1/notifications/{id}` | 알림 상세 |
| 41 | `PATCH /api/v1/notifications/{id}/read` | 읽음 처리(멱등) |
| 42 | `POST /api/v1/admin/users/{id}/roles` | 역할 부여 |
| 43 | `DELETE /api/v1/admin/users/{id}/roles/{role}` | 역할 회수 |

`notifications` 앱은 M3 이후 `models.py`·`admin.py`만 있는 껍데기였고, `accounts` 앱은 테스트가 0건이었다. 둘 다 이번에 채워졌다.

## 왜 이렇게 구현했나

### 1. 접근 제어를 권한 클래스가 아니라 쿼리셋으로

알림 3종은 모든 조회를 `Notification.objects.filter(recipient=user)`에서 시작한다. 타인의 알림은 **로드되지 않으므로** 404가 되고, 그것이 곧 접근 제어다.

객체를 먼저 꺼낸 뒤 소유자를 비교하는 형태를 쓰지 않은 이유는 취향이 아니다. 그 형태는 "꺼냈는데 남의 것"이라는 중간 상태를 만들고, 그 지점에서 403/404 분기를 매번 옳게 판단해야 한다. 쿼리셋에 넣으면 그 중간 상태 자체가 없다.

Owner 결정 근거(원문): *"애초에 이 앱 서비스는 개인화 앱이므로 남의 알림을 열 수 없어야 함. 알림은 나에게만."*

### 2. `actor_user`는 저장하되 직렬화하지 않는다

Phase 2 알림 5종의 actor가 **전부 관리자**다(승인·반려·배정 모두 admin 행위). api.md #40은 `actor?: { user_id?, display_name? }`를 명세했지만 그대로 구현하면 일반 사용자에게 관리자 계정 id가 넘어간다. SPEC-002 보안 리뷰가 "SPEC-003 응답 필드 설계 시 반드시 재검토"로 지목했던 지점이고, Owner가 미노출로 확정했다.

나중에 peer actor가 생기면 **추가**하면 된다. 반대 방향(이미 내보낸 필드를 회수하는 것)은 훨씬 비싸다.

### 3. 멱등성을 응답이 아니라 쓰기에 건다

api.md #41의 상태 집합에 409가 없다 → 이미 읽은 알림에 재요청해도 성공해야 한다. 성공시키는 방법은 둘인데, 그냥 다시 쓰면 `read_at`이 덮어써져 **"사용자가 처음 이 알림을 본 시각"이 조용히 사라진다.** 그래서 `is_read`가 이미 참이면 아무것도 쓰지 않는다. 멱등성이 관용이 아니라 불변식이 된다.

### 4. #43의 판정 순서와 잠금

이 SPEC에서 가장 위험한 함수다. 설계 판단 네 가지:

1. **판정 순서 = 자기회수 → 미보유 → 마지막관리자.** 순서를 바꾸면 관리자가 1명일 때 ADMIN을 갖지도 않은 사용자를 회수 시도했을 때 "마지막 관리자"라는 **사실이 아닌** 오류가 나간다.
2. **`count()`가 아니라 `list()`.** PostgreSQL은 집계 위의 `FOR UPDATE`를 거부한다. 잠기지 않은 count가 바로 이 가드가 막으려는 경합이므로, 행을 실제로 잠그고 파이썬에서 센다.
3. **잠금 순서 고정.** `User` → ADMIN `UserRole`(`order_by("pk")`). `grant_role`·`set_active_role`은 `User`만 잠그므로 순환이 없고, 순서를 고정하지 않으면 두 회수가 반대 순서로 잠가 교착(500)할 수 있다.
4. **"마지막 ADMIN"은 `UserRole` 행 기준, superuser 미포함.** `IsAdmin`은 superuser도 통과시키지만(ADR-003 §1), 잘못 막으면 재시도로 끝나고 **잘못 허용하면 아무도 역할을 되돌릴 수 없다.** 이 비대칭이 보수적 판정의 근거다.

### 5. A-3는 한 방향이 아니었다

STATUS.md §7의 A-3는 `accounts.set_active_role`을 가리키고 있었다. 회수 쪽만 고치면 이 순서로 동일한 위험 상태에 그대로 도달한다:

> 전환(#10)이 "ADVISOR 있네" 확인 → 회수(#43)가 지움(`active_role`은 USER라 강등 대상 아님) → 전환이 `active_role=ADVISOR`를 씀
> → **역할은 없는데 ADVISOR를 입은 상태**

`set_active_role`에도 같은 행 잠금을 넣어 양쪽을 닫았다. 한쪽만 닫고 "A-3 해소"로 보고하면 사실과 다르다.

## 핵심 파일

| 파일 | 내용 |
| --- | --- |
| [notifications/services.py](../../notifications/services.py) | `list_my_notifications` / `unread_count` / `get_my_notification` / `mark_read` |
| [notifications/serializers.py](../../notifications/serializers.py) | 목록·상세·읽음결과 3종. `actor_user`·`payload` 미노출 |
| [accounts/services.py](../../accounts/services.py) | `grant_role` / `revoke_role` 신규, `set_active_role` 잠금 추가 |
| [accounts/urls.py](../../accounts/urls.py) | `GrantableRoleConverter` — `USER`가 라우트에 매칭되지 않게 함 |
| [notifications/tests.py](../../notifications/tests.py) | 34개. `NotificationTargetUrlRoundTripTests`가 C-10 왕복 검증 |
| [accounts/tests.py](../../accounts/tests.py) | 51개. 이 앱 최초. `StateTransitionLockingTests`가 SQL 수준 잠금 검사 |

## 어떻게 테스트하나

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run python manage.py test                       # 272개
uv run python manage.py test notifications accounts  # SPEC-003 범위만 85개
```

Mock-Up UI(DRF Browsable API)는 `docker compose up -d` 후 브라우저로 확인한다. 스크린샷 13장은 이 SPEC의 각 TASK 보고에 첨부했다.

## DevOps 설명 포인트

**"검사하고 나서 바꾸는" 코드는 왜 잠금이 필요한가.** 관리자가 2명이고 두 요청이 동시에 서로를 회수한다고 하자. 둘 다 "관리자가 2명이니 1명 지워도 된다"를 통과하고, 결과는 0명이 된다. 시스템에 관리자가 없으면 **역할을 되돌릴 사람도 없다.**

`SELECT ... FOR UPDATE`는 그 행을 잠가 두 번째 요청을 기다리게 만든다. 기다렸다 깨어난 요청은 PostgreSQL이 갱신된 상태를 다시 보여주므로(READ COMMITTED의 EvalPlanQual) 이번엔 "관리자 1명"을 보고 409로 거절한다.

확인 방법은 SQL을 직접 보는 것이다:

```
SELECT ... FROM accounts_userrole WHERE role = 'ADMIN'
  ORDER BY accounts_userrole.id ASC FOR UPDATE
```

`ORDER BY`가 함께 있는 이유는 교착 방지다. 두 트랜잭션이 같은 행들을 **다른 순서로** 잠그면 서로를 기다리다 PostgreSQL이 한쪽을 죽인다(500).

## 보안 노트

* 알림 응답의 키 집합을 테스트로 고정했다(`test_detail_fields`, `test_list_item_fields`). 이메일·`actor_user`·`payload`가 실릴 수 없다.
* 타인 알림 접근은 3개 지점(#39·#40·#41)에서 **개별로** 검증한다. 한 곳만 막고 다른 곳이 새는 것이 흔한 실패 형태다.
* `RoleGrant`가 append-only인지 정적 확인했다 — 프로덕션 코드에 `create` 3곳뿐, `update`/`delete` 없음.
* 회수는 데이터를 지우지 않는다. 이미 작성된 조언은 남고 작성자 본인은 계속 읽을 수 있다(`test_revoke_does_not_delete_the_advice_the_advisor_wrote`).

## 다음 개선

| # | 항목 | 비고 |
| --- | --- | --- |
| 1 | **실제 경합 재현 테스트** | 현재는 발행 SQL로 잠금의 *존재*만 고정한다. Django `TestCase`가 트랜잭션 안에서 돌아 동시성을 못 만든다. `TransactionTestCase` + 스레드로 "관리자 0명" 시나리오를 실제로 돌려보는 것이 남았다 |
| 2 | **회수 후 `advisor_status`가 `APPROVED`로 남음**(#9) | 신청이 승인됐던 것은 사실이라 거짓은 아니나, 화면에 "역할 없음 + 승인됨"이 함께 보이면 혼동된다. M5 UX 검토 |
| 3 | **회수된 조언가의 배정 잔존** | 결정 3(a)에 따른 의도된 동작. #23에서 식별 가능함을 실증했고 api.md에 명시했다. M5 스모크 항목 |
| 4 | **`grant_role`의 `USER` 차단이 serializer에 있음** | API 밖에서 호출하면 우회된다. 호출부가 늘어나면 서비스 레이어로 옮길 것 |
| 5 | **ADMIN 집합 전체 잠금** | 관리자 수가 한 자리라 무시할 비용이나, 수백 명이 되면 advisory lock 등으로 재검토 |
| 6 | **알림 일괄 읽음 API 부재** | api.md 비범위(UX §8-6). M5 재검토 |

## 이번 SPEC에서 배운 것

**AC 전항 통과가 "검증했다"를 뜻하지 않는다.** TASK-005의 AC 전수 대조에서 AC-8의 `payload` 키 검증이 5종 중 1종에만 적용돼 있던 것을 찾았다. 코드는 이미 옳았고 **검증이 비어 있었다** — AC 문서에는 체크 표시가 가능한 상태였다. 대조를 실제로 하지 않았으면 그대로 넘어갔을 항목이다.

**규칙은 문서보다 테스트에 둘 때 지켜진다.** `.claude/rules/coding.md`의 상태 전이 규칙을 `StateTransitionLockingTests`로 승격했다. 발행 SQL에서 `FOR UPDATE`·잠금 순서·`update_fields` 범위를 직접 검사한다. 문서로만 두면 다음 함수가 추가될 때 조용히 빠진다 — **A-1이 정확히 그렇게 생겼다.**
