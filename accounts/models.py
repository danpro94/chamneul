from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models

from common.uuid7 import uuid7

from .managers import UserManager


class ActiveRole(models.TextChoices):
    USER = "USER", "사용자"
    ADVISOR = "ADVISOR", "조언가"
    # ADMIN is never an active_role: admin authority is checked separately, not
    # "worn" as the active context (api.md §2).


# Columns that decide who can log in, with what authority, and what a password
# reset token is computed from (password, last_login, email). See User.save().
STALE_WRITE_GUARDED = (
    "password",
    "last_login",
    "email",
    "is_active",
    "is_staff",
    "is_superuser",
    "active_role",
)


def _guarded_among(field_names):
    """Guarded columns among `field_names` (all of them when None = every field)."""
    if field_names is None:
        return STALE_WRITE_GUARDED
    return [name for name in STALE_WRITE_GUARDED if name in field_names]


class User(AbstractBaseUser, PermissionsMixin):
    """Authentication subject. Email is the single login identifier.

    Multiple roles are modelled separately (UserRole, Milestone 2); this model
    only carries the currently-active role for UX context.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=20, unique=True, validators=[MinLengthValidator(2)])
    active_role = models.CharField(
        max_length=8, choices=ActiveRole.choices, default=ActiveRole.USER
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Django Admin access

    # Optional profile fields (api.md 8).
    job = models.CharField(max_length=50, blank=True, default="")
    interest = models.CharField(max_length=200, blank=True, default="")
    profile_image_url = models.URLField(max_length=500, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]  # prompted by createsuperuser
    EMAIL_FIELD = "email"

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return f"{self.nickname} <{self.email}>"

    # --- stale-write safety net (SPEC-005 final review H-1) ----------------
    # save() without update_fields writes every column, so an instance loaded
    # before someone else changed one of the guarded columns would silently put
    # the old value back. #8 did exactly that: a slow profile PATCH could undo
    # F-5's password disable, #46's lock-out and a role revocation. #8 itself
    # now writes only what it was sent; this net covers every other full save
    # (Django Admin, future code) by leaving out guarded columns that this
    # instance did not change. Inserts and explicit update_fields are untouched.

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._remember_guarded(STALE_WRITE_GUARDED)
        return instance

    def _remember_guarded(self, names):
        baseline = getattr(self, "_guarded_baseline", {})
        for name in names:
            if name in self.__dict__:  # deferred columns are not loaded
                baseline[name] = self.__dict__[name]
        self._guarded_baseline = baseline

    def refresh_from_db(self, using=None, fields=None, from_queryset=None):
        super().refresh_from_db(using=using, fields=fields, from_queryset=from_queryset)
        self._remember_guarded(_guarded_among(fields))

    def save(self, *args, **kwargs):
        baseline = getattr(self, "_guarded_baseline", None)
        if baseline and not args and not self._state.adding and kwargs.get("update_fields") is None:
            untouched = {n for n, v in baseline.items() if self.__dict__.get(n) == v}
            if untouched:
                kwargs["update_fields"] = [
                    f.name
                    for f in self._meta.concrete_fields
                    if not f.primary_key and f.attname in self.__dict__ and f.name not in untouched
                ]
        super().save(*args, **kwargs)
        self._remember_guarded(_guarded_among(kwargs.get("update_fields")))


class Role(models.TextChoices):
    """Grantable roles (model.md §3.2).

    USER is the logical default every account has implicitly — it is never
    stored as a UserRole row. It stays in this enum so RoleGrant history and
    future validation share one vocabulary.
    """

    USER = "USER", "사용자"
    ADVISOR = "ADVISOR", "조언가"
    ADMIN = "ADMIN", "관리자"


class RoleGrantAction(models.TextChoices):
    GRANT = "GRANT", "부여"
    REVOKE = "REVOKE", "회수"


class UserRole(models.Model):
    """A role held by a user (User ↔ Role M:N, model.md §3.2).

    Only ADVISOR/ADMIN rows exist; possession of a row is the authorization
    fact. `User.active_role` is separate UX context and must be one of the
    held roles — enforced in the service layer (M4), not by the DB.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="role_assignments")
    role = models.CharField(max_length=8, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Plain unique (not partial): this model has no soft delete, so
            # CLAUDE.md §6.6 partial-unique enforcement does not apply here.
            models.UniqueConstraint(
                fields=["user", "role"], name="accounts_userrole_user_role_unique"
            ),
        ]

    def __str__(self):
        return f"{self.user}:{self.role}"

    def clean(self):
        # USER must never be stored (model.md §3.2). Admin forms hit this via
        # full_clean(); API paths get the same rule in the service layer (M4).
        if self.role == Role.USER:
            raise ValidationError({"role": "USER는 암묵적 기본 역할이며 row로 저장하지 않는다."})


class RoleGrant(models.Model):
    """Append-only audit trail of role grants/revocations (ADR-003 §3).

    Rows are written by service code (role grant/revoke APIs and advisor
    application approval, both M4); they are never updated or deleted, and
    Phase 2 exposes them through Django Admin read-only views only.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="received_role_events"
    )
    role = models.CharField(max_length=8, choices=Role.choices)
    action = models.CharField(max_length=8, choices=RoleGrantAction.choices)
    acted_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="performed_role_events"
    )
    acted_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            # Per-target history and the global audit view (model.md §3.3).
            models.Index(fields=["user", "-acted_at"], name="rolegrant_user_acted_idx"),
            models.Index(fields=["-acted_at"], name="rolegrant_acted_idx"),
        ]

    def __str__(self):
        return f"{self.action} {self.role} -> {self.user}"


class GoogleIdentity(models.Model):
    """Link between a Google account and a local User (model.md §3.4).

    The OAuth flow itself is M4; this model only fixes the storage shape.
    `email` is what Google asserted at link time and may drift from
    User.email afterwards, so both are kept.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="google_identity")
    google_sub = models.CharField(max_length=255, unique=True)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "google identities"

    def __str__(self):
        return f"{self.user} ↔ google:{self.google_sub}"
