"""Account service layer (model.md §5).

Role logic lives here (not in serializers/views) because it is a business rule
shared across M4-2 (active-role switch), M4-4 (advisor approval grants ADVISOR),
and M4-8 (admin grant/revoke). USER is the implicit default every account holds;
only ADVISOR/ADMIN are stored as UserRole rows (model.md §3.2).
"""

import re
import secrets

from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied

from common.exceptions import Conflict
from common.uuid7 import uuid7

from .models import Role, UserRole

# advisor_status exposes only these (api.md #9). WITHDRAWN is unreachable in
# Phase 2 and maps to NONE if it somehow appears.
_ADVISOR_STATUSES = {"PENDING", "REVIEWING", "APPROVED", "REJECTED"}


def held_roles(user) -> list[str]:
    """Roles the user holds, USER first. USER is implicit (no row); ADVISOR/ADMIN
    come from UserRole. Order is stable (USER, ADVISOR, ADMIN) for UI rendering.
    """
    stored = set(UserRole.objects.filter(user=user).values_list("role", flat=True))
    roles = ["USER"]
    for role in (Role.ADVISOR, Role.ADMIN):
        if role in stored:
            roles.append(role)
    return roles


def advisor_status(user) -> str:
    """Latest advisor application status, or NONE (api.md #9)."""
    # Local import avoids an accounts -> advisors module dependency at load time.
    from advisors.models import AdvisorApplication

    app = (
        AdvisorApplication.objects.filter(applicant=user)
        .order_by("-submitted_at")
        .first()
    )
    if app is None or app.status not in _ADVISOR_STATUSES:
        return "NONE"
    return app.status


def set_active_role(user, target: str) -> None:
    """Switch active_role to a role the user actually holds (model.md §5).

    Raises PermissionDenied (403) if the target is not held. ADMIN is rejected
    upstream by the serializer's choices, so only USER/ADVISOR reach here.
    """
    if target not in held_roles(user):
        raise PermissionDenied("보유하지 않은 역할로는 전환할 수 없습니다.")
    user.active_role = target
    user.save(update_fields=["active_role", "updated_at"])


# --- Google OAuth account linking / creation (C-11, ADR-002 §7) -----------


def _derive_nickname_base(name: str, email: str) -> str:
    """C-11 base value: Google name -> email local part -> "user".
    Trim, collapse internal whitespace, truncate to 15 chars (leaves room for a
    5-char `_NNNN` suffix under nickname's max_length=20). Falls through until a
    candidate is >= 2 chars (nickname's MinLengthValidator)."""
    for candidate in (name or "", (email or "").split("@")[0], "user"):
        cleaned = re.sub(r"\s+", " ", candidate.strip())[:15]
        if len(cleaned) >= 2:
            return cleaned
    return "user"


def _create_with_nickname(email: str, google_sub: str, base: str):
    """Create User + GoogleIdentity atomically, resolving nickname collisions by
    INSERT-then-retry (C-11): the DB unique constraint is the final arbiter, no
    check-then-insert race. base -> base_NNNN (random) x5 -> user_{uuid7 hex8}."""
    from .models import GoogleIdentity, User

    candidates = [base] + [f"{base}_{secrets.randbelow(10000):04d}" for _ in range(5)]
    candidates.append(f"user_{uuid7().hex[:8]}")  # effectively collision-proof
    last_error = None
    for nickname in candidates:
        try:
            with transaction.atomic():
                user = User.objects.create_user(email=email, nickname=nickname, password=None)
                GoogleIdentity.objects.create(user=user, google_sub=google_sub, email=email)
            return user
        except IntegrityError as exc:
            last_error = exc
            continue
    raise last_error


def link_or_create_google_user(google_sub: str, email: str, name: str = ""):
    """Resolve a verified Google identity to a local User (ADR-002 §7, CLAUDE.md
    §10 — link by verified email, never fork the account).

    1. Known google_sub -> that user.
    2. Same verified email as an existing account -> link identity to it,
       unless that account is already linked to a *different* Google account
       (409, api.md #6 — one local account maps to at most one Google account).
    3. Otherwise -> new account with a derived nickname (C-11).
    """
    from .models import GoogleIdentity, User

    email = email.lower()

    identity = GoogleIdentity.objects.filter(google_sub=google_sub).select_related("user").first()
    if identity is not None:
        return identity.user

    existing = User.objects.filter(email=email).first()
    if existing is not None:
        # Reaching here means this google_sub is NOT yet linked (step 1 missed).
        # If the matched account already has a Google link, it is a different
        # account — refuse rather than silently overwrite or violate the
        # OneToOne (which would surface as an opaque 500).
        if GoogleIdentity.objects.filter(user=existing).exists():
            raise Conflict("이 계정은 이미 다른 Google 계정과 연결되어 있습니다.")
        GoogleIdentity.objects.create(user=existing, google_sub=google_sub, email=email)
        return existing

    return _create_with_nickname(email, google_sub, _derive_nickname_base(name, email))
