# Security Rules

> CLAUDE.md §10에서 원문 그대로 이동 (ADR-006). 내용 변경 없음 — CLAUDE.md와 동등한 효력을 가진다.

Never commit secrets.

Sensitive files:

* .env
* private keys
* credential files
* local database dumps
* token files
* OAuth client secrets

Required:

* .env.example only
* .gitignore must exclude secrets
* DEBUG must not be true in production settings
* ALLOWED_HOSTS must be explicit outside local development
* user-owned data must enforce object-level access control
* only approved advice is visible to concern owners
* admin-only actions must not be exposed as public endpoints

Authentication implementation rules (Session-based, see CLAUDE.md §4 and ADR-002):

* The session cookie must be set with HttpOnly, Secure, and SameSite=Lax. `Secure` is required for all non-localhost environments.
* Logout must invalidate the server-side session record AND clear the client cookie (`Set-Cookie` with `Max-Age=0`). It must not rely on client-side cookie deletion alone.
* Google OAuth callback must reuse the same session model — do not create a parallel auth path. Account linking is by verified email.
* Password storage uses Django's default PBKDF2 hasher with the project default iteration count. Do not store plaintext or reversible-encrypted passwords.
* CSRF protection must be enabled for all state-changing endpoints. SPA clients must read the `csrftoken` cookie and send it back in the `X-CSRFToken` header.
* Brute-force login protection (IP + account based rate limiting) is documented as a Phase 3 follow-up; in Phase 2, document the gap explicitly in the smoke test note.
