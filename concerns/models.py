from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models import Q

from common.taxonomy import ConcernType
from common.uuid7 import uuid7

from .managers import ConcernManager


class ConcernStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "제출됨"
    ASSIGNED = "ASSIGNED", "배정됨"
    ANSWERED = "ANSWERED", "답변됨"
    CLOSED = "CLOSED", "종료됨"


class PreferredAdvisorLane(models.TextChoices):
    EXPERT = "expert", "전문가"
    SENIOR = "senior", "인생 선배"
    NO_PREFERENCE = "no_preference", "무관"


class Concern(models.Model):
    """사용자의 의사결정 고민 (model.md §3.6). 상태 머신 + soft delete.

    상태 전이(SUBMITTED→ASSIGNED→ANSWERED→CLOSED, 배정 전부 해제 시
    ASSIGNED→SUBMITTED)는 서비스 레이어가 강제한다 (CLAUDE.md §6.6, M4).
    사용자의 삭제는 상태 전이가 아니라 deleted_at 기록이다 (soft delete).
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="concerns"
    )
    concern_summary = models.CharField(max_length=100)
    concern_type = models.CharField(max_length=40, choices=ConcernType.choices)
    concern_type_secondary = ArrayField(
        models.CharField(max_length=40, choices=ConcernType.choices),
        size=2,  # 보조 분류는 최대 2개 (model.md §3.6)
        default=list,
        blank=True,
    )
    preferred_advisor_lane = models.CharField(
        max_length=16,
        choices=PreferredAdvisorLane.choices,
        default=PreferredAdvisorLane.NO_PREFERENCE,
    )
    decision_context = models.TextField(
        blank=True, default="", validators=[MaxLengthValidator(4000)]  # O-2
    )
    display_alias = models.CharField(max_length=50, blank=True, default="")
    is_anonymous = models.BooleanField(default=True)
    status = models.CharField(
        max_length=12, choices=ConcernStatus.choices, default=ConcernStatus.SUBMITTED
    )
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ConcernManager()
    # Unfiltered manager: FK traversal(advice.concern 등)과 Django 내부 동작은
    # soft-deleted row에도 닿아야 한다(감사 기록 보존, §6.6). base_manager를
    # 필터된 objects로 두면 삭제된 고민에 딸린 advice에서 DoesNotExist가 터진다.
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        indexes = [
            models.Index(
                fields=["author", "deleted_at", "-created_at"],
                name="concern_author_del_created_idx",
            ),
            models.Index(fields=["status", "-created_at"], name="concern_status_created_idx"),
            models.Index(
                fields=["concern_type", "-created_at"], name="concern_type_created_idx"
            ),
        ]

    def __str__(self):
        return f"{self.concern_summary} ({self.status})"


class TriageDecision(models.TextChoices):
    SUITABLE = "suitable", "적합"
    NEEDS_MORE_INFO = "needs_more_info", "추가 정보 필요"
    OUT_OF_SCOPE = "out_of_scope", "범위 밖"


class AssignmentPriority(models.TextChoices):
    LOW = "low", "낮음"
    NORMAL = "normal", "보통"
    HIGH = "high", "높음"


class Assignment(models.Model):
    """Concern ↔ Advisor 배정 (model.md §3.7).

    비활성(is_active=False) row는 삭제하지 않고 보존한다 — 배정 이력 자체가
    감사 기록이다. 같은 (concern, advisor)의 활성 배정은 1개만 허용.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    concern = models.ForeignKey(Concern, on_delete=models.PROTECT, related_name="assignments")
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="advisor_assignments"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="performed_assignments",
    )
    triage_decision = models.CharField(max_length=20, choices=TriageDecision.choices)
    match_rationale = models.JSONField(default=dict, blank=True)
    priority = models.CharField(
        max_length=8, choices=AssignmentPriority.choices, default=AssignmentPriority.NORMAL
    )
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        constraints = [
            # 활성 배정 중복 차단 — 비활성 이력은 다수 허용 (model.md §3.7).
            models.UniqueConstraint(
                fields=["concern", "advisor"],
                condition=Q(is_active=True),
                name="assignment_concern_advisor_unique_active",
            ),
        ]
        indexes = [
            models.Index(fields=["advisor", "is_active"], name="assign_advisor_active_idx"),
            models.Index(fields=["concern", "is_active"], name="assign_concern_active_idx"),
        ]

    def __str__(self):
        return f"{self.concern_id} -> {self.advisor} ({'active' if self.is_active else 'inactive'})"
