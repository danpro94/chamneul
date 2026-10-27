"""Password-reset mail (SPEC-005 #45, ADR-008).

Built here instead of with Django's PasswordResetForm because that form skips
accounts without a usable password — and SPEC-005 decision 2 lets a
Google-only account set a password through this flow.

Delivery itself is Phase 3: local prints to the console (settings/local.py),
tests capture into `django.core.mail.outbox`.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

SUBJECT = "[참늘] 비밀번호 재설정 안내"

_LOCAL_BODY = """\
{nickname}님, 비밀번호 재설정을 요청하셨어요.

아래 링크에서 새 비밀번호를 정해 주세요.
링크는 {minutes}분 동안, 한 번만 쓸 수 있어요.

{link}

요청한 적이 없다면 이 메일은 무시하셔도 됩니다. 비밀번호는 바뀌지 않아요.
"""

_GOOGLE_BODY = """\
{nickname}님, 이 계정은 Google 로그인을 쓰고 있어요.
평소처럼 'Google로 계속하기'를 누르면 바로 들어올 수 있어요.

이메일과 비밀번호로도 로그인하고 싶다면 아래 링크에서 비밀번호를 만들 수 있어요.
링크는 {minutes}분 동안, 한 번만 쓸 수 있어요.

{link}

요청한 적이 없다면 이 메일은 무시하셔도 됩니다. 계정에는 아무 변화가 없어요.
"""


def send_reset_mail(user, uid: str, token: str) -> None:
    template = _LOCAL_BODY if user.has_usable_password() else _GOOGLE_BODY
    body = template.format(
        nickname=user.nickname,
        minutes=settings.PASSWORD_RESET_TIMEOUT // 60,
        # Fragment (#), not query (?): browsers never send it to the frontend
        # server, so the token stays out of its access logs (security review S-5).
        link=f"{settings.PASSWORD_RESET_URL}#uid={uid}&token={token}",
    )
    try:
        send_mail(SUBJECT, body, None, [user.email])
    except Exception as exc:
        # Must not reach the response: a 500 only for registered addresses
        # would reveal which ones exist (ADR-008 §2). Django's own reset form
        # makes the same choice. Log the pk and the exception type only — no
        # traceback, because SMTP exceptions embed the recipient address.
        # Semgrep python-logger-credential-disclosure is a false positive here
        # (triaged 2026-10-27): only the pk and the exception class name are logged.
        # nosemgrep: python-logger-credential-disclosure
        logger.error("Password reset mail failed for user %s (%s)", user.pk, type(exc).__name__)
