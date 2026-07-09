from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from common.exceptions import Conflict

from . import services
from .models import User


class SignupSerializer(serializers.ModelSerializer):
    """Email + password signup. Password is write-only and validated by Django's
    configured validators; the manager hashes it (never stored in plaintext).
    """

    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("email", "nickname", "password")

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            nickname=validated_data["nickname"],
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer):
    """Validates credentials and returns the authenticated user in
    `validated_data["user"]`. Email is lowercased to match the stored form
    (the manager normalizes on create).
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        user = authenticate(
            self.context.get("request"),
            username=attrs["email"].lower(),
            password=attrs["password"],
        )
        if user is None:
            # Do not reveal whether the email exists (CLAUDE.md §10 / api.md #3).
            raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")
        attrs["user"] = user
        return attrs


class UserCardSerializer(serializers.ModelSerializer):
    """Shared identity card. Response key is `user_id` (api.md #2/#3/#7), not the
    raw `id`. Sensitive fields (password, permission flags) never appear here.
    """

    user_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = User
        fields = ("user_id", "email", "nickname", "active_role")
        read_only_fields = fields


class SignupResultSerializer(UserCardSerializer):
    """Signup response (#2): identity card + created_at (flat)."""

    class Meta(UserCardSerializer.Meta):
        fields = ("user_id", "email", "nickname", "active_role", "created_at")
        read_only_fields = fields


class UserMeSerializer(UserCardSerializer):
    """GET /users/me (#7): identity card + held roles + created_at.
    `advisor_type` is deliberately absent (CLAUDE.md §6.1 / api.md Q15).
    """

    roles = serializers.SerializerMethodField()

    class Meta(UserCardSerializer.Meta):
        fields = ("user_id", "email", "nickname", "active_role", "roles", "created_at")
        read_only_fields = fields

    def get_roles(self, obj):
        return services.held_roles(obj)


class UserUpdateSerializer(serializers.ModelSerializer):
    """PATCH /users/me (#8): partial profile update. nickname uniqueness returns
    409 (not DRF's default 400) — the model's auto UniqueValidator is dropped and
    the check is done here so the conflict maps to Conflict/409.
    """

    nickname = serializers.CharField(min_length=2, max_length=20, required=False)

    class Meta:
        model = User
        fields = ("nickname", "job", "interest", "profile_image_url")

    def validate_nickname(self, value):
        if User.objects.filter(nickname=value).exclude(pk=self.instance.pk).exists():
            raise Conflict("이미 사용 중인 닉네임입니다.")
        return value


class UserUpdateResultSerializer(serializers.ModelSerializer):
    """PATCH /users/me response (#8): user_id, email, nickname, updated_at."""

    user_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = User
        fields = ("user_id", "email", "nickname", "updated_at")
        read_only_fields = fields


class ActiveRoleSerializer(serializers.Serializer):
    """PATCH /users/me/active-role (#10). ADMIN is never an active_role — the
    choices exclude it (accounts.models.ActiveRole). Whether the user actually
    holds the target role is enforced in services.set_active_role (403 if not).
    """

    active_role = serializers.ChoiceField(choices=["USER", "ADVISOR"])
