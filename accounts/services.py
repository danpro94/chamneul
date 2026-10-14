"""Account service layer (model.md §5).

Role logic lives here (not in serializers/views) because it is a business rule
shared across M4-2 (active-role switch), M4-4 (advisor approval grants ADVISOR),
and M4-8 (admin grant/revoke). USER is the implicit default every account holds;
only ADVISOR/ADMIN are stored as UserRole rows (model.md §3.2).
"""

import re
import secrets
import uuid

from django.contrib.auth import SESSION_KEY
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.exceptions import Conflict
from common.uuid7 import uuid7

from .emails import send_reset_mail
from .models import ActiveRole, Role, RoleGrant, RoleGrantAction, User, UserRole

# advisor_status exposes only these (api.md #9). WITHDRAWN is unreachable in
# Phase 2 and maps to NONE if it somehow appears.
_ADVISOR_STATUSES = {"PENDING", "REVIEWING", "APPROVED", "REJECTED"}

# Roles that may be granted or revoked (ADR-003 §2). USER is the implicit
# default every account holds and is never stored as a row (model.md §3.2).
# The API already blocks it twice (serializer choices for #42, URL converter
# for #43); this is the service-layer copy, so a management command or a future
# admin action cannot write a row the whole authorization model ignores.
_GRANTABLE_ROLES = frozenset({Role.ADVISOR, Role.ADMIN})


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

    The row lock closes A-3 (2026-09-14 점검). This function and `revoke_role`
    move the same two facts in opposite directions — one writes `active_role`,
    the other deletes the `UserRole` that justifies it. Unguarded, a switch that
    read ADVISOR before a concurrent revoke deleted it would still write it,
    leaving a user wearing a role they no longer hold and passing
    IsActiveAdvisor. Reading the roles under the target's own `User` row forces
    the two into an order: the revoke either lands first (and this raises 403)
    or waits (and then sees ADVISOR worn, so it demotes).
    """
    with transaction.atomic():
        locked = User.objects.select_for_update(of=("self",)).get(pk=user.pk)
        if target not in held_roles(locked):
            raise PermissionDenied("보유하지 않은 역할로는 전환할 수 없습니다.")
        locked.active_role = target
        locked.save(update_fields=["active_role", "updated_at"])
    # Keep the caller's in-memory instance (request.user) consistent with the
    # row we just wrote — the view serializes from it.
    user.active_role = target


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


# --- admin role grant / revoke (ADR-003, api.md #42-#43) ------------------


def grant_role(target_user_id, role, actor, reason=""):
    """Grant ADMIN/ADVISOR to a user, writing one audit row (#42).

    Returns `(target, grant)`. Raises 404 for an unknown user, 409 for a role
    the target already holds.

    The target's `User` row is locked first, which is what makes the
    check-then-create below safe: two concurrent grants of the same role to the
    same user serialize on that row, so the duplicate loses the race and gets a
    409 instead of tripping the unique constraint. Locking `User` (not
    `UserRole`) is deliberate — the row we must serialize on is the one that
    exists before the decision, and it is the same row `revoke_role` takes, so
    the two never deadlock against each other.

    No notification is sent, by decision (ADR-003 §4).
    """
    if role not in _GRANTABLE_ROLES:
        raise ValidationError({"role": "부여할 수 없는 역할입니다."})

    with transaction.atomic():
        target = get_object_or_404(
            User.objects.select_for_update(of=("self",)), pk=target_user_id
        )
        if UserRole.objects.filter(user=target, role=role).exists():
            raise Conflict("이미 보유한 역할입니다.", reason="ALREADY_HELD")

        UserRole.objects.create(user=target, role=role)
        grant = RoleGrant.objects.create(
            user=target,
            role=role,
            action=RoleGrantAction.GRANT,
            acted_by=actor,
            reason=reason,
        )
    # active_role is untouched on purpose: holding a role and wearing it are
    # different facts (model.md §3.2). The user switches with #10.
    return target, grant


def revoke_role(target_user_id, role, actor, reason=""):
    """Revoke ADMIN/ADVISOR from a user, writing one audit row (#43).

    Takes an id, not an object, so the decision is made on state re-read inside
    this transaction — the caller's view of the world may already be stale.
    (Same regression shape as A-1 in advisors.services, 2026-09-14.)

    Guard order matters and is not arbitrary:
      1. self-revoke of ADMIN — an admin must not be able to lock themselves out;
      2. does the target actually hold the role — checked before the "last
         admin" rule, otherwise revoking ADMIN from someone who never had it
         would be reported as "마지막 관리자" while only one admin exists, which
         is simply untrue;
      3. last remaining ADMIN — the system must never reach zero administrators,
         because there is then no one left who can grant the role back.

    Locking: the target `User` row first, then the ADMIN `UserRole` rows in pk
    order. `grant_role` locks only `User`, so the two never deadlock; ordering
    the role rows keeps two concurrent revokes from locking the same set in
    opposite orders. The count is taken from materialised rows rather than
    `.count()` because PostgreSQL rejects `FOR UPDATE` on an aggregate, and an
    unlocked count is exactly the race this guard exists to prevent.
    """
    if role not in _GRANTABLE_ROLES:
        raise ValidationError({"role": "회수할 수 없는 역할입니다."})

    with transaction.atomic():
        target = get_object_or_404(
            User.objects.select_for_update(of=("self",)), pk=target_user_id
        )

        if role == Role.ADMIN:
            if target.id == actor.id:
                raise Conflict(
                    "자기 자신의 ADMIN 역할은 회수할 수 없습니다.",
                    reason="SELF_REVOKE",
                )

            # `user__is_active=True`: a deactivated account cannot authenticate
            # (Django's ModelBackend refuses it), so counting it as a surviving
            # administrator would leave nobody able to log in and grant the role
            # back. The filter only ever makes the guard refuse more, which is
            # the safe direction.
            admin_roles = list(
                UserRole.objects.select_for_update()
                .filter(role=Role.ADMIN, user__is_active=True)
                .order_by("pk")
            )
            if not any(row.user_id == target.id for row in admin_roles):
                raise Conflict("보유하지 않은 역할입니다.", reason="NOT_HELD")
            # Counted from UserRole rows only: IsAdmin also accepts a superuser
            # (ADR-003 §1), but blocking one revoke too many costs a retry while
            # allowing one too few locks everyone out. The asymmetry decides.
            if len(admin_roles) <= 1:
                raise Conflict(
                    "마지막 관리자는 회수할 수 없습니다.", reason="LAST_ADMIN"
                )

        # The delete's own return value is the not-held check for ADVISOR:
        # splitting it into exists() + delete() would reopen the race the User
        # row lock just closed.
        deleted, _ = UserRole.objects.filter(user=target, role=role).delete()
        if not deleted:
            raise Conflict("보유하지 않은 역할입니다.", reason="NOT_HELD")

        RoleGrant.objects.create(
            user=target,
            role=role,
            action=RoleGrantAction.REVOKE,
            acted_by=actor,
            reason=reason,
        )

        # A-3 (2026-09-14 점검). IsActiveAdvisor checks active_role alone, so a
        # revoked advisor still wearing ADVISOR would keep passing #20/#21 and
        # #28-#30. Revoking the role has to take the costume off too.
        # ADMIN needs no equivalent: it is never an active_role (ActiveRole).
        if role == Role.ADVISOR and target.active_role == ActiveRole.ADVISOR:
            target.active_role = ActiveRole.USER
            target.save(update_fields=["active_role", "updated_at"])

    return target


def request_password_reset(email: str) -> None:
    """#45 — mail a reset link if the address belongs to an active account.

    Returns nothing on purpose: the caller cannot tell whether a mail went out,
    so the view has no way to let it leak into the response (ADR-008 §2).
    Inactive accounts are skipped, as Django's own reset form does — they could
    not log in with the new password anyway (#3).

    Nothing is written: the token is computed from the password hash and
    last_login, so changing the password is what invalidates it (#46).
    """
    user = User.objects.filter(email=email.lower(), is_active=True).first()
    if user is None:
        return
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    send_reset_mail(user, uid, token)


# One message for every way a link can be bad (expired, used, forged, unknown
# account). Telling them apart would reveal that a token or account existed.
_INVALID_RESET_LINK = "링크가 만료됐거나 올바르지 않습니다. 비밀번호 재설정을 다시 요청해 주세요."


def _user_id_from_uid(uidb64: str):
    try:
        return uuid.UUID(urlsafe_base64_decode(uidb64).decode())
    except (TypeError, ValueError, OverflowError):
        return None


def _purge_sessions_of(user) -> None:
    """Delete every server-side session row of `user`.

    Django already logs those sessions out on their next request (the session
    carries a hash derived from the password), but the rows would linger until
    expiry. Deleting them follows the logout rule (ADR-002 §4): invalidation is
    a server-side fact, not something we wait for.

    Full scan because the DB session table has no user column — acceptable at
    Phase 2 size; a user index is the next step if it grows (SPEC-005 plan §2).
    """
    user_id = str(user.pk)
    stale = [
        session.session_key
        for session in Session.objects.iterator()
        if session.get_decoded().get(SESSION_KEY) == user_id
    ]
    Session.objects.filter(session_key__in=stale).delete()


def confirm_password_reset(uidb64: str, token: str, new_password: str) -> None:
    """#46 — set a new password from a mailed link, then end every session.

    The user row is locked and re-read before the token check: two requests
    with the same link would otherwise both see the old password and both pass.
    The token needs no explicit revocation — it is derived from the password
    hash, so changing the password is what makes it fail next time.
    """
    with transaction.atomic():
        # A malformed uid becomes None, which matches no row — same path as an
        # unknown account, so the two cannot be told apart.
        user_id = _user_id_from_uid(uidb64)
        user = (
            User.objects.select_for_update(of=("self",)).filter(pk=user_id, is_active=True).first()
        )
        if user is None or not default_token_generator.check_token(user, token):
            raise ValidationError({"token": [_INVALID_RESET_LINK]})

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            raise ValidationError({"new_password": list(exc.messages)}) from exc

        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])

        # Recovering a password = the account may have been taken over. A
        # surviving session would leave the intruder logged in (api.md #46).
        _purge_sessions_of(user)
