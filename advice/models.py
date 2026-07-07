from django.conf import settings
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from common.uuid7 import uuid7


class AdviceStatus(models.TextChoices):
    PENDING = "PENDING", "접수"
    REVIEWING = "REVIEWING", "심사중"
    APPROVED = "APPROVED", "승인"
    REJECTED = "REJECTED", "반려"
    DELETED = "DELETED", "삭제됨"


class Advice(models.Model):
    """조언 (model.md §3.8, CLAUDE.md §6.2).

    사용자는 APPROVED 상태만 볼 수 있다 — 이 노출 규칙은 M4의 queryset/serializer
    가 강제한다. version은 감사용 증가 카운터(§6.7): advisor가 PENDING/REVIEWING
    에서 수정할 때마다 서비스 레이어가 +1 하고 AdviceHistory에 스냅샷을 남긴다.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    concern = models.ForeignKey(
        "concerns.Concern", on_delete=models.PROTECT, related_name="advices"
    )
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="written_advices"
    )
    directional_guidance = models.TextField(validators=[MaxLengthValidator(1500)])
    reflective_questions = models.TextField(blank=True, default="")
    considerations = models.TextField(blank=True, default="")
    out_of_scope_flag = models.BooleanField(default=False)
    is_submitted = models.BooleanField(default=True)  # False = draft (api.md 28)
    status = models.CharField(
        max_length=10, choices=AdviceStatus.choices, default=AdviceStatus.PENDING
    )
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True, default=None)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_advices",
    )
    reject_reason = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            # 동일 (concern, advisor) 활성 advice 1건 — DELETED 후 재작성 허용
            # (model.md §3.8, O-4).
            models.UniqueConstraint(
                fields=["concern", "advisor"],
                condition=~Q(status="DELETED"),
                name="advice_concern_advisor_unique_active",
            ),
        ]
        indexes = [
            models.Index(fields=["advisor", "-created_at"], name="advice_advisor_created_idx"),
            models.Index(fields=["concern", "status"], name="advice_concern_status_idx"),
            models.Index(fields=["status", "-created_at"], name="advice_status_created_idx"),
        ]

    def __str__(self):
        return f"advice v{self.version} ({self.status}) by {self.advisor}"


class AdviceHistory(models.Model):
    """Advice 수정 시점의 본문 전체 스냅샷 (model.md §3.9, CLAUDE.md §6.7).

    Append-only audit — 서비스 레이어(M4)가 수정마다 1행을 추가한다. Phase 2에서
    공개 API로 노출하지 않는다. CASCADE: advice row가 hard delete되는 경우
    (Phase 2에서는 Django Admin에서만 가능)에 한해 history도 함께 삭제.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    advice = models.ForeignKey(Advice, on_delete=models.CASCADE, related_name="history")
    version = models.PositiveIntegerField()
    directional_guidance = models.TextField()
    reflective_questions = models.TextField()
    considerations = models.TextField()
    out_of_scope_flag = models.BooleanField()
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="advice_edits"
    )
    edited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["advice", "version"], name="advicehistory_advice_version_unique"
            ),
        ]

    def __str__(self):
        return f"{self.advice_id} v{self.version}"


class FeedbackStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "제출됨"
    REVIEWED = "REVIEWED", "검토됨"
    ARCHIVED = "ARCHIVED", "보관됨"


class Feedback(models.Model):
    """받은 advice에 대한 사용자 피드백 — advice당 1건 (model.md §3.10, §6.3).

    작성 가능 조건(APPROVED advice + concern 작성자 본인 + 미작성)과
    SUBMITTED→REVIEWED→ARCHIVED 단방향 전이는 서비스 레이어(M4)가 강제한다.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    advice = models.OneToOneField(Advice, on_delete=models.PROTECT, related_name="feedback")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="written_feedbacks"
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    content = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=10, choices=FeedbackStatus.choices, default=FeedbackStatus.SUBMITTED
    )
    memo = models.TextField(blank=True, default="")  # 관리자 전용 메모
    reviewed_at = models.DateTimeField(null=True, blank=True, default=None)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_feedbacks",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "-created_at"], name="feedback_status_created_idx"),
            models.Index(fields=["author", "-created_at"], name="feedback_author_created_idx"),
        ]

    def __str__(self):
        return f"feedback {self.score}/5 on {self.advice_id}"
