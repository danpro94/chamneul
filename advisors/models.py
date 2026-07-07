from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models
from django.db.models import Q

from common.taxonomy import ConcernType
from common.uuid7 import uuid7


class AdvisorApplicationStatus(models.TextChoices):
    PENDING = "PENDING", "접수"
    REVIEWING = "REVIEWING", "심사중"
    APPROVED = "APPROVED", "승인"
    REJECTED = "REJECTED", "반려"
    # WITHDRAWN is model-only in Phase 2: no public withdrawal API (CLAUDE.md §6.1).
    WITHDRAWN = "WITHDRAWN", "철회"


class DomainCategory(models.TextChoices):
    # O-1 잠정안 (model.md §11) — 사업 도메인 확정 시 재검토. 한국어 저장값은
    # api.md 11의 표기를 그대로 따른 것.
    IT = "IT", "IT"
    BUSINESS = "경영", "경영"
    HR = "인사", "인사"
    FINANCE = "금융", "금융"
    MEDICAL = "의료", "의료"
    EDUCATION = "교육", "교육"
    ETC = "기타", "기타"


class ExperienceBand(models.TextChoices):
    BAND_5_7 = "5-7", "5~7년"
    BAND_8_12 = "8-12", "8~12년"
    BAND_13_PLUS = "13+", "13년 이상"


class CurrentStatus(models.TextChoices):
    EMPLOYED = "재직", "재직"
    FREELANCER = "프리랜서", "프리랜서"
    ON_LEAVE = "휴직", "휴직"
    RESTING = "휴식", "휴식"
    RETIRED = "은퇴", "은퇴"


class IntendedLane(models.TextChoices):
    EXPERT = "expert", "전문가"
    SENIOR = "senior", "인생 선배"


class AdvisorApplication(models.Model):
    """조언가 신청서 (model.md §3.5).

    intended_lane is applicant-stated intent only — never exposed in public
    responses, never used as an authorization key (CLAUDE.md §6.1).
    Status transitions (PENDING → REVIEWING → APPROVED/REJECTED) are enforced
    in the service layer (M4); the model stores state only.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="advisor_applications",
    )
    display_name = models.CharField(max_length=20, validators=[MinLengthValidator(2)])
    domain_category = models.CharField(max_length=20, choices=DomainCategory.choices)
    experience_band = models.CharField(max_length=8, choices=ExperienceBand.choices)
    current_status = models.CharField(max_length=10, choices=CurrentStatus.choices)
    intended_lane = models.CharField(max_length=8, choices=IntendedLane.choices)
    career_narrative = models.TextField()
    advisable_concern_types = ArrayField(
        models.CharField(max_length=40, choices=ConcernType.choices),
        default=list,
        # 1개 이상 필수 (model.md §3.5) — 리스트 길이에 대한 검증.
        validators=[MinLengthValidator(1)],
    )
    sample_advice_response = models.TextField(
        validators=[MinLengthValidator(200), MaxLengthValidator(400)]
    )
    status = models.CharField(
        max_length=12,
        choices=AdvisorApplicationStatus.choices,
        default=AdvisorApplicationStatus.PENDING,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True, default=None)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_advisor_applications",
    )
    reject_reason = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            # 활성(접수·심사중·승인) 신청서 사이에서만 display_name 유일 —
            # REJECTED/WITHDRAWN 의 이름은 재사용 가능 (model.md §3.5, §6.6 패턴).
            models.UniqueConstraint(
                fields=["display_name"],
                condition=Q(status__in=["PENDING", "REVIEWING", "APPROVED"]),
                name="advisor_app_display_name_unique_active",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-submitted_at"], name="advapp_status_sub_idx"),
            models.Index(fields=["applicant", "-submitted_at"], name="advapp_applicant_sub_idx"),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.status})"
