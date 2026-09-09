from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler as drf_default_handler


class Conflict(APIException):
    """409 — the request conflicts with the current resource state (api.md §1.8):
    duplicate nickname, already-held role, non-allowed state transition, etc.
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "요청이 현재 상태와 충돌합니다."
    default_code = "conflict"


class UnprocessableEntity(APIException):
    """422 — request is well-formed but semantically invalid (api.md §1.8):
    e.g. a rejection with no reason. Distinct from 400 (malformed syntax).
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "요청을 처리할 수 없습니다."
    default_code = "unprocessable_entity"

# Map HTTP status to the SCREAMING_SNAKE_CASE `code` fixed by api.md §1.5.
_STATUS_TO_CODE = {
    status.HTTP_400_BAD_REQUEST: "INVALID_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHENTICATED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_412_PRECONDITION_FAILED: "PRECONDITION_FAILED",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "UNPROCESSABLE_ENTITY",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
    status.HTTP_502_BAD_GATEWAY: "BAD_GATEWAY",
}


def api_exception_handler(exc, context):
    """Reshape every handled DRF error into {error: {code, message, details}}.

    Unhandled exceptions still return None so Django produces a normal 500 (we
    do not leak internals into the envelope). Validation errors keep their
    field map under `details` so the client can highlight the offending field.
    """
    response = drf_default_handler(exc, context)
    if response is None:
        return None

    code = _STATUS_TO_CODE.get(response.status_code, "ERROR")
    if isinstance(exc, ValidationError):
        message = "입력값을 확인해주세요."
        details = response.data  # {field: [messages]} shape from DRF
    else:
        # Non-validation errors expose a single `detail` string.
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        message = str(detail) if detail is not None else "요청을 처리할 수 없습니다."
        details = None

    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    response.data = body
    return response
