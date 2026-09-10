# SPEC-001 — plan

## 1. 파일 계획

| 파일 | 내용 |
| --- | --- |
| `concerns/serializers.py` (신규) | `ConcernCreateSerializer` / `ConcernListSerializer` / `ConcernDetailSerializer` / `AssignedConcernListSerializer` / `AssignedConcernDetailSerializer` / `AdminConcernListSerializer` / `AdminConcernDetailSerializer` / `AssignmentCreateSerializer` — list/detail/create/admin을 분리(CLAUDE.md §8·§9, advisors 앱 기존 패턴 준용) |
| `concerns/services.py` (신규) | `create_concern()` / `soft_delete_concern()` / `assign_advisor()` / `unassign_advisor()` — 상태 전이·부수효과 전담 |
| `concerns/views.py` (신규) | `APIView`/`ListAPIView` 조합, advisors 앱 패턴(`advisors/views.py`) 준용 |
| `concerns/urls.py` (신규) | 10개 path |
| `concerns/managers.py` (기존) | `ConcernManager` — `objects`(alive만) / `with_deleted()` 이미 존재(model.md §1.4 확인 필요, 없으면 본 SPEC에서 추가) |
| `common/permissions.py` (수정) | `IsAssignedAdvisor` 추가 — 객체 수준 검사(해당 concern에 요청자의 active Assignment가 있는지) |
| `config/urls.py` (수정) | `path("api/v1/", include("concerns.urls"))` 추가 |
| `concerns/tests.py` (신규) | TASK별 테스트 (아래 tasks.md) |

## 2. 서비스 레이어 설계

### `create_concern(user, validated_data) -> Concern`

단순 생성. 부수효과 없음(알림·상태 전이 대상 아님 — 최초 상태가 SUBMITTED).

### `soft_delete_concern(concern, user)`

```
if concern.author != user: 403 (view에서 object-level 체크로 선행 처리 권장)
if concern.deleted_at is not None: raise Conflict (409)
concern.deleted_at = timezone.now()
concern.save(update_fields=["deleted_at"])
```

### `assign_advisor(concern, advisor, actor, triage_decision, match_rationale=None, priority=NORMAL) -> Assignment`

`advisors/services.py`의 atomic 패턴을 그대로 따른다:

```
with transaction.atomic():
    if concern.deleted_at is not None or concern.status == CLOSED:
        raise Conflict
    try:
        assignment = Assignment.objects.create(concern=concern, advisor=advisor, assigned_by=actor, ...)
    except IntegrityError:
        raise Conflict("이미 배정된 조언가입니다.")  # 부분 유니크 위반
    if concern.status == SUBMITTED:
        concern.status = ASSIGNED
        concern.save(update_fields=["status"])
    Notification.objects.create(recipient=advisor, type=ASSIGNMENT_CREATED, ...)
return assignment
```

### `unassign_advisor(assignment, actor)`

```
with transaction.atomic():
    if not assignment.is_active: raise Conflict
    assignment.is_active = False
    assignment.deactivated_at = timezone.now()
    assignment.save(update_fields=["is_active", "deactivated_at"])
    if not Assignment.objects.filter(concern=assignment.concern, is_active=True).exists():
        assignment.concern.status = SUBMITTED
        assignment.concern.save(update_fields=["status"])
```

## 3. 권한 설계

* #16~19: `IsAuthenticated`만 (spec.md §3 — active_role 게이트 없음). object-level: `get_object_or_404(Concern.objects.filter(author=request.user), pk=...)` 패턴으로 타인 자원은 자동 404.
* #20~21: `IsAuthenticated` + view 내부에서 `request.user.active_role == Role.ADVISOR`(model.md accounts) 체크 → 아니면 403. #21은 추가로 `IsAssignedAdvisor`(신규 permission, Assignment 존재 여부).
* #22~25: `IsAdmin`(기존, `common/permissions.py`).

## 4. N+1 대비

* #17(목록): `select_related("author")` 불요(author 자신이므로 필드 불필요) — `annotate`로 `has_approved_advice`는 M4-6 Advice 모델 연결 후 `Exists(Advice.objects.filter(concern=OuterRef("pk"), status=APPROVED))`. M4-5 시점엔 advice 앱에 뷰가 없어도 모델은 존재하므로 즉시 구현 가능(model.md 확인).
* #22(admin 목록): `prefetch_related` 불필요(assignment_count는 `annotate(Count("assignments"))`).
* #23(admin 상세): `assignments`/`advices`는 `prefetch_related("assignments__advisor", "advices__advisor")`.

## 5. 마이그레이션 영향

없음 — 본 SPEC은 기존 `concerns.0001_initial`(Concern, Assignment)만 사용한다. 스키마 변경 없음.

## 6. 테스트 전략

`concerns/tests.py`에 `ConcernTestCase(TestCase)` — `setUp`에서 사용자 3종(author, other_user, advisor, admin) 생성. TDD 순서는 tasks.md 참조. 신규 테스트 패키지 도입 안 함(TEST_CRITERIA.md §1).
