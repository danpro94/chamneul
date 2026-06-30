from django.contrib.auth.base_user import BaseUserManager


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
        # NOTE: granting the ADMIN UserRole row to the first superuser (ADR-003)
        # happens when the UserRole model lands in Milestone 2.
        return self._create_user(email, nickname, password, **extra_fields)
