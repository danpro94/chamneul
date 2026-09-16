# SPEC-003 — plan

## 1. 파일 계획

| 파일 | 내용 |
| --- | --- |
| `notifications/serializers.py` (신규) | 목록용 / 상세용 2종 (상세만 `read_at` 추가). `actor`는 결정 1에 따름 |
| `notifications/services.py` (신규) | `list_my_notifications` / `get_my_notification` / `mark_read` |
| `notifications/views.py` (신규) | `NotificationListView`(ListAPIView) / `NotificationDetailView` / `NotificationReadView` |
| `notifications/urls.py` (신규) | 3개 path |
| `notifications/tests.py` (신규) | TASK-001~002 + TASK-005 통합 |
| `accounts/services.py` (수정) | `grant_role` / `revoke_role` 추가 — 기존 `held_roles`·`set_active_role`와 같은 모듈 |
| `accounts/serializers.py` (수정) | `RoleGrantSerializer`(요청 `role`/`reason`) + 부여 결과 serializer |
| `accounts/views.py` (수정) | `AdminUserRolesView`(POST) / `AdminUserRoleDetailView`(DELETE) |
| `accounts/urls.py` (수정) | 2개 path 추가 |
| `accounts/tests.py` (신규) | **이 앱 최초 테스트** — #42/#43 경로 |
| `config/urls.py` (수정) | `notifications.urls` include |
| `docs/api.md` (수정) | 결정 1~3 확정 내용 반영 |

**마이그레이션 없음** — `Notification`·`UserRole`·`RoleGrant` 전부 M2/M3 확정. 스키마 변경이 필요해지면 그 자체가 설계 재검토 신호다(SPEC-002와 동일 원칙).

`notifications` 앱은 현재 `models.py`·`admin.py`만 있는 **껍데기 상태**다. SPEC-001·002가 이 모델에 행을 써왔을 뿐 읽는 코드가 없었다.

## 2. 서비스 레이어 설계

### `list_my_notifications(user, is_read=None, type=None)` (#39)

```
qs = Notification.objects.filter(recipient=user).order_by("-created_at")
if is_read is not None: qs = qs.filter(is_read=is_read)
if type: qs = qs.filter(type=type)
return qs
```

`unread_count`는 **필터와 무관한 전체 미읽음 수**다(뱃지 숫자가 필터에 따라 흔들리면 안 된다). 따라서 목록 쿼리와 분리된 집계 1회:

```
Notification.objects.filter(recipient=user, is_read=False).count()
```

뷰에서 `get_paginated_response`를 오버라이드해 `{items, page_info}` 봉투(`common/pagination.StandardPagination`)에 `unread_count`를 더한다 — 페이지네이션 클래스 자체는 건드리지 않는다(다른 10개 목록 API가 공유 중).

### `get_my_notification(user, notification_id)` (#40)

```
get_object_or_404(Notification.objects.filter(recipient=user), pk=notification_id)
```

**수신자 스코프를 쿼리셋에 넣는 것이 접근 제어 그 자체다**(결정 2 → 404). 객체를 먼저 꺼낸 뒤 소유자를 비교하는 형태로 쓰지 않는다 — 그 형태는 403/404 분기 실수가 나기 쉽다.

### `mark_read(user, notification_id)` (#41)

```
with transaction.atomic():
    n = get_object_or_404(
        Notification.objects.select_for_update(of=("self",)).filter(recipient=user),
        pk=notification_id,
    )
    if not n.is_read:                       # 멱등: 이미 읽었으면 read_at 보존
        n.is_read = True
        n.read_at = timezone.now()
        n.save(update_fields=["is_read", "read_at"])
    return n
```

### `grant_role(target_user_id, role, actor, reason="")` (#42)

```
if role not in (ADVISOR, ADMIN): -> serializer choices가 이미 400으로 막음
with transaction.atomic():
    target = get_object_or_404(User.objects.select_for_update(of=("self",)), pk=target_user_id)
    try:
        UserRole.objects.create(user=target, role=role)
    except IntegrityError:
        raise Conflict("이미 보유한 역할입니다.")        # 409 (동시 부여 경합 포함)
    grant = RoleGrant.objects.create(user=target, role=role,
                                     action=GRANT, acted_by=actor, reason=reason)
return target, grant
```

`active_role`은 건드리지 않는다 — ADVISOR를 받아도 전환은 사용자가 #10으로 직접 한다. ADMIN은 애초에 `active_role`이 될 수 없다(`ActiveRole` choices에 없음).

### `revoke_role(target_user_id, role, actor, reason="")` (#43) ★ 이 SPEC의 핵심

```
with transaction.atomic():
    # 잠금 순서 고정: User 먼저, 그다음 ADMIN UserRole 집합 (교착 방지)
    target = get_object_or_404(User.objects.select_for_update(of=("self",)), pk=target_user_id)

    if role == ADMIN:
        if target.id == actor.id:
            raise Conflict("자기 자신의 ADMIN 역할은 회수할 수 없습니다.")
        admins = list(UserRole.objects.select_for_update().filter(role=ADMIN))
        if len(admins) <= 1:
            raise Conflict("마지막 관리자는 회수할 수 없습니다.")

    deleted, _ = UserRole.objects.filter(user=target, role=role).delete()
    if not deleted:
        raise Conflict("보유하지 않은 역할입니다.")

    RoleGrant.objects.create(user=target, role=role, action=REVOKE,
                             acted_by=actor, reason=reason)

    # A-3 — 회수된 역할을 계속 "입고" 있으면 #20·#21·#28~#30이 계속 열린다.
    if role == ADVISOR and target.active_role == ActiveRole.ADVISOR:
        target.active_role = ActiveRole.USER
        target.save(update_fields=["active_role", "updated_at"])
```

설계 근거 3가지:

1. **`.count()`가 아니라 `list(...)`로 materialize한다.** PostgreSQL은 `SELECT COUNT(*) ... FOR UPDATE`를 거부한다(`FOR UPDATE is not allowed with aggregate functions`). 집계 위에 잠금을 걸 수 없으므로 행을 실제로 잠그고 파이썬에서 센다.
2. **"마지막 ADMIN" 판정은 `UserRole` 행 기준이고, `is_superuser`만 가진 계정은 세지 않는다.** `IsAdmin`은 superuser도 통과시키지만(ADR-003 §1), 회수 가드는 **더 보수적인 쪽**으로 둔다 — 잘못 막으면 관리자가 한 번 더 호출하면 되지만, 잘못 허용하면 시스템이 잠긴다. 이 비대칭이 판정 기준을 정한다.
3. **삭제 성공 여부로 "보유하지 않은 역할"을 판정한다.** `exists()` 후 `delete()`로 나누면 그 사이가 경합 구간이다. `delete()`의 반환값이 곧 잠금 없는 원자적 판정이다.

## 3. 쿼리 설계 (N+1 방지)

| 엔드포인트 | 전략 |
| --- | --- |
| #39 목록 | 응답 필드(`notification_id`·`type`·`title`·`message`·`target_url`·`is_read`·`created_at`)가 전부 자기 컬럼 — **`select_related` 불필요**. 인덱스 `notif_recipient_created_idx`/`notif_recipient_read_idx`가 이미 정렬·필터를 받는다 |
| #40 상세 | 결정 1이 (a)면 관계 조인 0건. (b)/(c)면 `select_related("actor_user")` 필수 |
| #42/#43 | 단건. `held_roles()`가 응답의 `roles[]`를 만들며 쿼리 1회 |

`assertNumQueries` 수치는 **먼저 `CaptureQueriesContext`로 측정한 뒤** 적는다. SPEC-001·002에서 추정으로 쓴 3번이 전부 틀렸고(원인: `IsAdmin`이 `UserRole` 조회 1건을 더 쓰는데 `IsActiveAdvisor`는 안 쓴다), 측정 후 작성으로 바꾼 뒤 2회 연속 한 번에 맞았다.

## 4. 테스트 전략

* `notifications/tests.py` — 알림 3종. 공통 fixture(수신자 / 제3자 / 읽음·미읽음 알림)를 베이스 클래스로 (SPEC-002에서 효과 확인된 형태).
* `accounts/tests.py` — **이 앱의 첫 테스트 파일**. 범위는 #42/#43으로 한정한다. M4-1~M4-3(회원가입·로그인·OAuth·프로필)의 소급 테스트는 이 SPEC의 범위가 아니다(문서 부채 항목으로 유지).
* **교차 검증 2종**(TASK-005) — 이 SPEC의 실질적 가치가 여기 있다:
  * **A-3 end-to-end**: 조언가가 조언 작성 → 관리자가 ADVISOR 회수 → 같은 조언가가 #29 수정 시도 → **403**. 강등이 실제로 권한을 닫는지 확인.
  * **C-10 `target_url` 왕복**: 5개 타입 알림을 실제 서비스 경로로 발생시키고, 각 `target_url`을 **수신자 본인 세션으로 GET → 200**. 지금까지 이 문자열들은 아무도 호출해본 적이 없다.

## 5. 리스크

| # | 리스크 | 대응 |
| --- | --- | --- |
| 1 | **A-1 수정(PR #5)이 이 브랜치에 없다.** 이 브랜치는 `main` 기준이고 PR #5는 OPEN 상태 | 구현 착수 전 PR #5 머지 → 리베이스. 문서 작성 단계에는 영향 없음 |
| 2 | `accounts/services.py`는 M4-2·M4-4가 이미 쓰는 공용 모듈인데 테스트가 0건 | 추가 함수는 기존 함수를 수정하지 않고 **덧붙이기만** 한다. `held_roles`·`set_active_role` 시그니처 불변 |
| 3 | `target_url` 왕복 테스트가 4개 앱(concerns·advice·advisors·notifications)을 가로지름 | `notifications/tests.py`에 통합 테스트로 두고, 실패 시 어느 타입인지 `subTest`로 구분 |
| 4 | 마지막 ADMIN 가드가 `UserRole` 기준이라 superuser-only 계정을 세지 않음 | §2 설계 근거 2로 의도를 명시하고, 판정 기준을 테스트에 고정(superuser 1 + UserRole ADMIN 1 상태에서 회수 → 409) |
| 5 | 결정 1이 (b)/(c)로 뒤집히면 serializer·쿼리 계획이 바뀜 | 착수 전 승인받는다. 구현 후 변경은 응답 필드 축소/확대라 API 계약 변경이 된다 |
