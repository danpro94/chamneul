from django.conf import settings
from django.db import models

from common.uuid7 import uuid7


class NotificationType(models.TextChoices):
    # CLAUDE.md §6.4 — 5종 고정. ADMIN grant/revoke는 알림을 발송하지 않는다 (ADR-003 §4).
    ADVICE_APPROVED = "ADVICE_APPROVED", "조언 승인됨"
    ADVICE_REJECTED = "ADVICE_REJECTED", "조언 반려됨"
    ADVISOR_APPLICATION_APPROVED = "ADVISOR_APPLICATION_APPROVED", "조언가 신청 승인됨"
    ADVISOR_APPLICATION_REJECTED = "ADVISOR_APPLICATION_REJECTED", "조언가 신청 반려됨"
    ASSIGNMENT_CREATED = "ASSIGNMENT_CREATED", "고민 배정됨"


class Notification(models.Model):
    """수신자별 알림 (model.md §3.11, CLAUDE.md §6.4).

    생성 트리거(조언 승인/반려, 신청 승인/반려, 배정)는 M4 서비스 레이어의
    부수효과다 — 이 모델은 저장 형태만 정의한다.
    recipient CASCADE: 수신자 계정이 삭제되면 알림도 함께 정리 (model.md §4).
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=40, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    target_url = models.CharField(max_length=500, blank=True, default="")  # 상대 경로 (api.md §6)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",  # 유발자가 떠나도 알림은 유지 (SET_NULL)
    )
    payload = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # 내 알림 목록 + unread_count 집계 (model.md §3.11)
            models.Index(
                fields=["recipient", "is_read", "-created_at"],
                name="notif_recipient_read_idx",
            ),
            models.Index(
                fields=["recipient", "-created_at"], name="notif_recipient_created_idx"
            ),
        ]

    def __str__(self):
        return f"[{self.type}] -> {self.recipient}"
