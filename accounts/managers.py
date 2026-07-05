from django.contrib.auth.base_user import BaseUserManager
from django.db import transaction


class UserManager(BaseUserManager):
    """Manager for the email-as-username custom User.

    `use_in_migrations` lets migrations refer to this manager (e.g. data
    migrations that create users) without importing it directly.
    """

    use_in_migrations = True

    def _create_user(self, email, nickname, password, **extra_fields):
        if not email:
            raise ValueError("email is required")
        if not nickname:
            raise ValueError("nickname is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, nickname=nickname, **extra_fields)
        user.set_password(password)  # PBKDF2 hashing (CLAUDE.md §10)
        user.save(using=self._db)
        return user

    def create_user(self, email, nickname, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, nickname, password, **extra_fields)

    def create_superuser(self, email, nickname, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("superuser must have is_superuser=True")
        # Local import: models.py imports this module, so a top-level import
        # would be circular.
        from .models import Role, UserRole

        # Bootstrap (ADR-003 §1): the superuser is the first ADMIN. Atomic so
        # a failed role insert cannot leave a superuser without the ADMIN role.
        # No RoleGrant audit row here: audit starts with API-driven grants (M4);
        # before the first admin exists there is no meaningful acted_by.
        with transaction.atomic():
            user = self._create_user(email, nickname, password, **extra_fields)
            UserRole.objects.create(user=user, role=Role.ADMIN)
        return user
