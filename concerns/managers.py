from django.db import models


class ConcernManager(models.Manager):
    """Soft-delete-aware default manager (model.md §1.4, CLAUDE.md §6.6).

    `Concern.objects` silently excludes soft-deleted rows so no API/queryset
    can leak them by accident. Admin/audit access must opt in explicitly via
    `with_deleted()`.
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def with_deleted(self):
        return super().get_queryset()

    def alive(self):  # 명시적 alias (model.md §1.4)
        return self.get_queryset()
