from django.contrib import admin

from .models import AdvisorApplication


@admin.register(AdvisorApplication)
class AdvisorApplicationAdmin(admin.ModelAdmin):
    # Approve/reject review action은 M4에서 서비스 레이어와 함께 구현한다 —
    # 승인 부수효과(UserRole+RoleGrant+Notification)를 모델 단계에서 흉내내지 않는다.
    list_display = ("applicant", "display_name", "status", "submitted_at")
    list_filter = ("status", "domain_category")
    search_fields = ("display_name", "applicant__email")
    list_select_related = ("applicant", "reviewed_by")
    # status/reviewed_*는 M4 review action이 생기기 전까지 readonly — 직접 편집하면
    # 승인 부수효과(UserRole+RoleGrant+Notification)가 우회된다 (data-modeler I-1).
    readonly_fields = ("id", "status", "reviewed_at", "reviewed_by", "submitted_at")
