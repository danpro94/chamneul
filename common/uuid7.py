"""UUIDv7 primary-key helper.

We generate UUIDv7 at the application layer (not via a PostgreSQL extension such
as pg_uuidv7) so the exact same code path runs identically on local, CI, and
managed databases (RDS/Aurora) where third-party extensions cannot be installed.
This keeps environment drift at zero.

`uuid_utils` is a Rust-backed RFC 9562 implementation. It returns its own UUID
type, so we convert to the stdlib `uuid.UUID` that Django's UUIDField expects,
preserving the exact 128-bit value via `.bytes`.

UUIDv7 is time-ordered, which (unlike random UUIDv4) keeps B-Tree index inserts
mostly sequential and avoids random page flushes — the reason for choosing it
as the PK strategy (model.md §1.2).
"""
import uuid

import uuid_utils


def uuid7() -> uuid.UUID:
    return uuid.UUID(bytes=uuid_utils.uuid7().bytes)
