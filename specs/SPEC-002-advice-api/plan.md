# SPEC-002 — plan

## 1. 파일 계획

| 파일 | 내용 |
| --- | --- |
| `advice/serializers.py` (신규) | 작성/수정/상세(주체별 3종)/목록(내 받은 조언·내 작성 조언·admin)/리뷰 요청/피드백 작성·목록·admin — 요청과 응답을 분리 |
| `advice/services.py` (신규) | `create_advice` / `update_advice`(version+history) / `delete_advice` / `review_advice`(부수효과) / `visible_advice_for`(주체 분기) / 피드백 3종 |
| `advice/views.py` (신규) | APIView 조합, SPEC-001 패턴 준용 |
| `advice/urls.py` (신규) | 13개 path (`/advices`, `/concerns/{id}/advices`, `/users/me/advices*`, `/admin/advices*`, `/admin/feedbacks*`) |
| `common/exceptions.py` (수정) | `PreconditionFailed`(412) 추가 — #33 낙관적 잠금 |
| `config/urls.py` (수정) | `advice.urls` include |
| `advice/tests.py` (신규) | TASK별 테스트 |

**마이그레이션 없음** — 모델 3종은 M3에서 이미 확정. 스키마 변경이 필요해지면 그 자체가 설계 재검토 신호다.

## 2. 서비스 레이어 설계

### `create_advice(concern_id, advisor, validated_data)` (#28)

```
concern = get_object_or_404(Concern.objects, pk=concern_id)        # soft-deleted -> 404
if not Assignment.objects.filter(concern, advisor, is_active=True).exists():
    raise PermissionDenied                                          # 403
try:
    Advice.objects.create(..., status=PENDING, is_submitted=validated["submit"])
except IntegrityError:
    raise Conflict("이미 이 고민에 조언을 작성했습니다.")            # 부분 유니크(DELETED 제외)
```

부수효과 없음 — 작성 시점엔 알림도 상태 전이도 없다(§6.4에 ADVICE_CREATED 타입이 없음).

### `update_advice(advice, validated_data)` (#29)

```
if advice.status not in {PENDING, REVIEWING}: raise Conflict        # 409
with transaction.atomic():
    body_changed = any(본문 4필드 중 실제로 값이 바뀐 것)
    if body_changed:
        AdviceHistory.objects.create(advice, version=advice.version, <직전 본문>, edited_by=advisor)
        advice.version += 1
    <필드 반영>
    advice.save()
```

**결정 2**(spec §7)에 따라 본문이 바뀔 때만 버전을 올린다. 히스토리에는 **직전** 본문을 직전 버전 번호로 남긴다(§6.7 "preserves prior body content per version").

### `review_advice(advice, actor, decision, reason, expected_version)` (#33)

```
with transaction.atomic():
    advice = Advice.objects.select_for_update().get(pk=...)          # 리뷰 경합 직렬화
    if not advice.is_submitted: raise Conflict                       # 결정 1 — 초안 리뷰 차단
    if advice.status not in {PENDING, REVIEWING}: raise Conflict      # 409
    if advice.version != expected_version: raise PreconditionFailed   # 412
    if decision == rejected and not reason.strip(): raise UnprocessableEntity  # 422
    advice.status = APPROVED | REJECTED; reviewed_by/at; reject_reason
    advice.save()
    if APPROVED:
        concern = Concern.objects.select_for_update().get(...)
        if concern.status == ASSIGNED: concern.status = ANSWERED      # 결정 3
        Notification(recipient=concern.author, ADVICE_APPROVED)
    else:
        Notification(recipient=advice.advisor, ADVICE_REJECTED)
```

SPEC-001 `assign_advisor`와 같은 형태 — 상태 전이·알림이 한 트랜잭션.

### `visible_advice_for(advice, user)` (#27)

주체를 판정해 `(advice, viewer_role)`을 돌려주고, 직렬화는 역할별 serializer가 담당한다.

| 판정 순서 | 조건 | 결과 |
| --- | --- | --- |
| 1 | `advice.advisor == user` | `author` — 상태 무관, `reject_reason` 노출 |
| 2 | ADMIN 보유 | `admin` — 상태 무관, `reject_reason` 노출 |
| 3 | `advice.concern.author == user` and `status == APPROVED` | `owner` — `reject_reason` 미노출 |
| 4 | 그 외 | 403 |

`DELETED` advice는 작성자·admin에게만(사용자 경로는 3번에서 APPROVED 조건에 걸려 자동 차단).

### 피드백 (#34·#38)

```
create_feedback: advice.status must be APPROVED (403) + concern.author == user (403)
                 + OneToOne 위반 -> 409
transition_feedback: SUBMITTED -> REVIEWED -> ARCHIVED 단방향, 역방향/동일전이 409
```

## 3. 쿼리 설계 (N+1 방지)

| 엔드포인트 | 전략 |
| --- | --- |
| #26 받은 조언 목록 | `Advice.objects.filter(concern__author=user, status=APPROVED).select_related("concern")` + `is_feedback_submitted`는 `Exists(Feedback...)` annotate + `advisor_display_name`은 `concerns.services.display_names_by_advisor` 벌크 |
| #31 내 작성 조언 | `filter(advisor=user).select_related("concern")` — 파생 필드 없음 |
| #32 admin 목록 | `select_related("concern","advisor")`, 기본 `status=PENDING` + `is_submitted=True` |
| #36 admin 피드백 목록 | `select_related("advice","advice__advisor","author")` |

목록 3종은 `assertNumQueries`로 상수 고정(TEST_CRITERIA §3 — SPEC-001 TASK-006에서 확인된 누락 패턴 반복 방지).

## 4. 테스트 전략

`advice/tests.py`에 TASK별 TestCase. 공통 fixture(고민 작성자 / 배정된 advisor / 미배정 advisor / admin / concern + active assignment)가 반복되므로 **`setUp` 헬퍼를 갖춘 베이스 클래스 1개**를 두고 상속한다 — SPEC-001에서 클래스마다 setUp을 복제한 것이 5회 반복되며 길어졌던 부분의 개선.

## 5. 리스크

| # | 리스크 | 대응 |
| --- | --- | --- |
| 1 | §6.2 노출 규칙이 **6개 엔드포인트**에 흩어짐(#26·#27·#18의 approved_advices·#32·#34·#37) | 노출 판정을 서비스 함수 1곳(`visible_advice_for`)과 queryset 헬퍼로 모으고, 각 엔드포인트 테스트에서 "PENDING이 새지 않는다"를 개별 검증 |
| 2 | 낙관적 잠금(412)은 이 프로젝트 첫 사례 | `common/exceptions.py`에 클래스 추가 + 전용 테스트(수정 후 리뷰 시도 → 412) |
| 3 | draft 개념이 상태가 아닌 플래그라 조건 분기가 늘어남 | spec §4 표를 코드 주석으로 옮겨 의도를 남긴다 |
| 4 | 13개 엔드포인트 = SPEC-001(10개)보다 큼 | TASK 7개로 분할, 각 TASK 후 정지·확인 |
