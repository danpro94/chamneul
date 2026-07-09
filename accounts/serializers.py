from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

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


class UserMeSerializer(serializers.ModelSerializer):
    """Response body for the authenticated subject. Intentionally omits sensitive
    fields (password, permission flags) — only what a signup/login response and
    /users/me need to render (api.md §8, response fields chosen deliberately).
    """

    class Meta:
        model = User
        fields = ("id", "email", "nickname", "active_role")
        read_only_fields = fields
