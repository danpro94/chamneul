"""Service layer for the advice API (SPEC-002, model.md §5).

Owns the rules a view must not inline: who may write an advice on which
concern, the one-active-advice-per-(concern, advisor) guarantee, and the
queryset shapes the list endpoints need.
"""

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.utils import timezone

from common.exceptions import Conflict, PreconditionFailed, UnprocessableEntity
from concerns.models import Assignment, Concern, ConcernStatus

from .models import Advice, AdviceHistory, AdviceStatus, Feedback, FeedbackStatus

# Decisions #33 accepts (api.md #33 request field `decision`).
DECISION_APPROVED = "approved"
DECISION_REJECTED = "rejected"

# States a submitted advice may still be reviewed from (api.md #33: "허용
# 전이: PENDING|REVIEWING → APPROVED|REJECTED").
_REVIEWABLE_STATUSES = (AdviceStatus.PENDING, AdviceStatus.REVIEWING)

# States in which the author may still change or withdraw an advice
# (api.md #29/#30) — anything else (APPROVED/REJECTED/DELETED) is terminal
# for the author and returns 409.
_EDITABLE_STATUSES = (AdviceStatus.PENDING, AdviceStatus.REVIEWING)

# The body fields that make up an AdviceHistory snapshot (model.md §3.9).
# `is_submitted` is deliberately excluded — spec.md §7-2: it is a workflow
# flag, not part of the advice's body history, so toggling it alone must not
# create a snapshot or bump `version`.
_BODY_FIELDS = (
    "directional_guidance",
    "reflective_questions",
    "considerations",
    "out_of_scope_flag",
)


def create_advice(concern_id, advisor, validated_data) -> Advice:
    """#28 — write an advice on an assigned concern.

    404 for a missing or soft-deleted concern (the default manager hides
    soft-deleted rows), 403 when the advisor has no active assignment on it,
    409 when they already have a live advice there.

    No side effects: §6.4 defines no notification for authoring, and the
    concern only moves to ANSWERED once an advice is *approved* (§6.6).
    """
    concern = get_object_or_404(Concern.objects, pk=concern_id)
    if not Assignment.objects.filter(
        concern=concern, advisor=advisor, is_active=True
    ).exists():
        raise PermissionDenied("배정되지 않은 고민입니다.")

    # draft = PENDING + is_submitted=False (spec.md §4). Draft-ness is a flag,
    # never a status — the admin review queue filters on it (#32/#33).
    try:
        return Advice.objects.create(
            concern=concern,
            advisor=advisor,
            directional_guidance=validated_data["directional_guidance"],
            reflective_questions=validated_data.get("reflective_questions", ""),
            considerations=validated_data.get("considerations", ""),
            out_of_scope_flag=validated_data.get("out_of_scope_flag", False),
            is_submitted=validated_data["submit"],
        )
    except IntegrityError as exc:
        # The only unique constraint here is the (concern, advisor) partial
        # index excluding DELETED (model.md §3.8), so a withdrawn advice does
        # not block a rewrite.
        raise Conflict("이미 이 고민에 작성한 조언이 있습니다.") from exc


def list_advices_written_by(advisor):
    """Queryset for #31 — the advisor's own advices, every status, newest
    first. No derived fields, so no extra query beyond the page itself."""
    return Advice.objects.filter(advisor=advisor).order_by("-created_at")


# Viewer roles for #27 — the caller's relationship to the advice, not a model
# field. The view picks a serializer from this (author/admin see reject_reason,
# owner does not).
VIEWER_AUTHOR = "author"
VIEWER_OWNER = "owner"
VIEWER_ADMIN = "admin"


def _is_admin(user) -> bool:
    # Deliberately duplicates common.permissions.IsAdmin's check rather than
    # reusing the DRF permission class here: this is an object-level branch
    # inside a service function, not a view-level gate, and the two shapes
    # (has_permission(request, view) vs. a plain user) don't fit together
    # cleanly enough to be worth coupling them.
    if user.is_superuser:
        return True
    from accounts.models import Role, UserRole

    return UserRole.objects.filter(user=user, role=Role.ADMIN).exists()


def get_visible_advice(advice_id, user) -> tuple[Advice, str]:
    """#27 — fetch the target advice and decide which of the three shapes the
    caller may see (spec.md §7-4, CLAUDE.md §6.2).

    404 only for a genuinely missing advice. Existence is not hidden from a
    concern owner the way another user's *concern* is (SPEC-001 #18) — a
    non-APPROVED advice is 403 for them, matching api.md #27's own status
    list (Owner decision 2026-09-11).
    """
    advice = get_object_or_404(
        Advice.objects.select_related("concern", "advisor"), pk=advice_id
    )
    if advice.advisor_id == user.id:
        return advice, VIEWER_AUTHOR
    if _is_admin(user):
        return advice, VIEWER_ADMIN
    if advice.concern.author_id == user.id and advice.status == AdviceStatus.APPROVED:
        return advice, VIEWER_OWNER
    raise PermissionDenied("조회 권한이 없습니다.")


def _get_own_editable_advice(advice_id, actor) -> Advice:
    """Shared lookup for #29/#30: 404 if missing (existence is not hidden —
    same reasoning as #27), 403 if the caller didn't write it, 409 if its
    status is no longer editable (api.md #29/#30's own status-code sets)."""
    advice = get_object_or_404(Advice, pk=advice_id)
    if advice.advisor_id != actor.id:
        raise PermissionDenied("작성자만 수정할 수 있습니다.")
    if advice.status not in _EDITABLE_STATUSES:
        raise Conflict("현재 상태에서는 변경할 수 없습니다.")
    return advice


def update_advice(advice_id, actor, validated_data) -> Advice:
    """#29 — partial update. `version` increments, and a history row is
    snapshotted, only when a body field actually changes (Owner decision
    2026-09-11, spec.md §7-2) — a lone `submit` toggle does neither, since
    `version` is the body-history counter (CLAUDE.md §6.7).
    """
    advice = _get_own_editable_advice(advice_id, actor)

    body_changed = any(
        field in validated_data and getattr(advice, field) != validated_data[field]
        for field in _BODY_FIELDS
    )

    with transaction.atomic():
        if body_changed:
            # Snapshot the *pre-update* body under the *current* (soon to be
            # previous) version number (CLAUDE.md §6.7).
            AdviceHistory.objects.create(
                advice=advice,
                version=advice.version,
                edited_by=actor,
                **{field: getattr(advice, field) for field in _BODY_FIELDS},
            )
            advice.version += 1
        for field in _BODY_FIELDS:
            if field in validated_data:
                setattr(advice, field, validated_data[field])
        if "is_submitted" in validated_data:
            advice.is_submitted = validated_data["is_submitted"]
        advice.save()
    return advice


def delete_advice(advice_id, actor) -> None:
    """#30 — soft delete: status -> DELETED, nothing else. The row stays (the
    partial unique on (concern, advisor) excludes DELETED, model.md §3.8, so
    this deliberately does not block the advisor from writing a fresh advice
    on the same concern)."""
    advice = _get_own_editable_advice(advice_id, actor)
    advice.status = AdviceStatus.DELETED
    advice.save(update_fields=["status"])


def list_advices_for_admin_review(status_filter=None):
    """Queryset for #32 — the admin review queue.

    Drafts (is_submitted=False) never appear here, under any status filter
    (Owner decision 2026-09-11, spec.md §7-1) — an advisor who hasn't
    submitted must not be reviewable, and review_advice() enforces the same
    rule again so a direct #33 call cannot bypass it either.
    """
    queryset = Advice.objects.filter(is_submitted=True).order_by("-created_at")
    if status_filter:
        return queryset.filter(status=status_filter)
    return queryset.filter(status=AdviceStatus.PENDING)


def review_advice(advice_id, actor, decision, reason, expected_version) -> tuple[Advice, Concern]:
    """#33 — approve or reject a submitted advice, atomically.

    One transaction covers the advice's own transition, the concern's
    (approval only, and only from ASSIGNED — Owner decision 2026-09-11,
    spec.md §7-3: §6.6 has no CLOSED/ANSWERED->ANSWERED edge), and the
    resulting notification (§6.4), so a failure partway through never leaves
    one without the others.

    Checks run in this order: existence (404) -> draft/state eligibility
    (409) -> optimistic-lock version match (412) -> decision-specific shape
    (422, reject needs a reason) -> apply. 412 sits before 422 because a
    stale read makes the request's own content moot.
    """
    from notifications.models import Notification, NotificationType

    with transaction.atomic():
        advice = get_object_or_404(
            Advice.objects.select_for_update().select_related("advisor"), pk=advice_id
        )
        if not advice.is_submitted:
            raise Conflict("제출되지 않은 초안은 리뷰할 수 없습니다.")
        if advice.status not in _REVIEWABLE_STATUSES:
            raise Conflict(f"{advice.status} 상태의 조언은 리뷰할 수 없습니다.")
        if advice.version != expected_version:
            raise PreconditionFailed()
        if decision == DECISION_REJECTED and not reason.strip():
            raise UnprocessableEntity("반려 시 사유는 필수입니다.")

        concern = Concern.objects.select_for_update().select_related("author").get(
            pk=advice.concern_id
        )

        advice.reviewed_by = actor
        advice.reviewed_at = timezone.now()
        if decision == DECISION_APPROVED:
            advice.status = AdviceStatus.APPROVED
        else:
            advice.status = AdviceStatus.REJECTED
            advice.reject_reason = reason
        advice.save()

        if decision == DECISION_APPROVED:
            if concern.status == ConcernStatus.ASSIGNED:
                concern.status = ConcernStatus.ANSWERED
                concern.save(update_fields=["status"])
            Notification.objects.create(
                recipient=concern.author,
                type=NotificationType.ADVICE_APPROVED,
                title="조언이 승인되었습니다",
                message="회원님의 고민에 새로운 조언이 도착했습니다.",
                target_url=f"/api/v1/advices/{advice.id}",
                actor_user=actor,
                payload={"advice_id": str(advice.id), "concern_id": str(concern.id)},
            )
        else:
            Notification.objects.create(
                recipient=advice.advisor,
                type=NotificationType.ADVICE_REJECTED,
                title="조언이 반려되었습니다",
                message=reason,
                target_url=f"/api/v1/advices/{advice.id}",
                actor_user=actor,
                payload={"advice_id": str(advice.id), "concern_id": str(concern.id)},
            )
    return advice, concern


def list_received_advices(user):
    """Queryset for #26 — APPROVED advices on the caller's own concerns.

    CLAUDE.md §6.2 in its most user-facing form: the filter pair
    (concern__author=user, status=APPROVED) is the whole exposure rule, so
    nothing else in this path needs to re-check it. `is_feedback_submitted`
    is an Exists annotation, not a per-row query.
    """
    return (
        Advice.objects.filter(concern__author=user, status=AdviceStatus.APPROVED)
        .select_related("concern", "advisor")
        .annotate(
            is_feedback_submitted=Exists(Feedback.objects.filter(advice=OuterRef("pk")))
        )
        .order_by("-created_at")
    )


def create_feedback(advice_id, author, validated_data) -> Feedback:
    """#34 — one feedback per advice, by the concern's owner, on an APPROVED
    advice only (api.md #34).

    403 (not 404) for someone else's advice or a non-APPROVED one: api.md
    #34 lists both under the same 403, and the concern owner already knows
    an advice exists on their concern. 409 for a second feedback — the
    OneToOne on Feedback.advice is what actually enforces "1회".
    """
    advice = get_object_or_404(Advice.objects.select_related("concern"), pk=advice_id)
    if advice.concern.author_id != author.id:
        raise PermissionDenied("본인 고민에 달린 조언에만 피드백할 수 있습니다.")
    if advice.status != AdviceStatus.APPROVED:
        raise PermissionDenied("승인된 조언에만 피드백할 수 있습니다.")

    try:
        return Feedback.objects.create(advice=advice, author=author, **validated_data)
    except IntegrityError as exc:
        raise Conflict("이미 이 조언에 피드백을 작성했습니다.") from exc


def list_feedbacks_written_by(author):
    """Queryset for #35 — the caller's own feedbacks, newest first."""
    return Feedback.objects.filter(author=author).order_by("-created_at")


# Feedback's one-way status flow (CLAUDE.md §6.3, api.md #38). Terminal
# states have no outgoing edge, so re-entering or reversing is 409 — the same
# table shape advisors.services uses for applications.
_ALLOWED_FEEDBACK_TRANSITIONS = {
    FeedbackStatus.SUBMITTED: {FeedbackStatus.REVIEWED},
    FeedbackStatus.REVIEWED: {FeedbackStatus.ARCHIVED},
    FeedbackStatus.ARCHIVED: set(),
}


def list_feedbacks_for_admin(filters):
    """Queryset for #36 — every feedback, newest first.

    select_related pulls the advice (for advisor_user_id) and the author in
    one join, so the list stays flat regardless of page size (CLAUDE.md §8).
    """
    queryset = (
        Feedback.objects.select_related("advice", "author").order_by("-created_at")
    )
    if "status" in filters:
        queryset = queryset.filter(status=filters["status"])
    if "score_min" in filters:
        queryset = queryset.filter(score__gte=filters["score_min"])
    if "score_max" in filters:
        queryset = queryset.filter(score__lte=filters["score_max"])
    return queryset


def get_feedback_for_admin(feedback_id) -> Feedback:
    """#37 — admin detail lookup. No ownership branch: ADMIN sees every
    feedback, including `memo`, which is admin-only (model.md §3.10)."""
    return get_object_or_404(
        Feedback.objects.select_related("advice", "author", "reviewed_by"),
        pk=feedback_id,
    )


def transition_feedback(feedback_id, actor, new_status, memo=None) -> Feedback:
    """#38 — move a feedback along SUBMITTED -> REVIEWED -> ARCHIVED.

    One step at a time and never backwards (CLAUDE.md §6.3); anything else,
    including re-entering the current state, is 409.

    `reviewed_by`/`reviewed_at` are stamped only on the transition *into*
    REVIEWED, not on archiving: the fields name the review event, and
    overwriting them when someone later files the feedback away would lose
    who actually reviewed it. No notification — api.md #38 says so
    explicitly.
    """
    feedback = get_object_or_404(Feedback, pk=feedback_id)
    if new_status not in _ALLOWED_FEEDBACK_TRANSITIONS.get(feedback.status, set()):
        raise Conflict(
            f"{feedback.status} 상태에서 {new_status}로 전이할 수 없습니다."
        )

    updated_fields = ["status"]
    feedback.status = new_status
    if new_status == FeedbackStatus.REVIEWED:
        feedback.reviewed_by = actor
        feedback.reviewed_at = timezone.now()
        updated_fields += ["reviewed_by", "reviewed_at"]
    if memo is not None:
        feedback.memo = memo
        updated_fields.append("memo")
    feedback.save(update_fields=updated_fields)
    return feedback
