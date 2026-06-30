from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import MinLengthValidator
from django.db import models

from common.uuid7 import uuid7

from .managers import UserManager


class ActiveRole(models.TextChoices):
    USER = "USER", "사용자"
    ADVISOR = "ADVISOR", "조언가"
    # ADMIN is never an active_role: admin authority is checked separately, not
    # "worn" as the active context (api.md §2).


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
