#!/bin/sh
# (Re)creates the read-only DB role used by the postgres-ro MCP server
# (ADR-009 item 7) in the LOCAL compose DB, and stores a fresh random password
# in the macOS Keychain. Safe to re-run — e.g. after `docker compose down -v`
# wiped the volume, or to rotate the password.
#
#   ./.claude/mcp/setup-postgres-ro-role.sh
#
# What the role can do: SELECT on application tables, except the
# accounts_user.password column and django_session. Writes are refused by
# missing privileges (the real boundary) and, as a second layer, by
# default_transaction_read_only. Each statement is capped at 5 s.
set -eu
cd "$(dirname "$0")/../.."

KEYCHAIN_SERVICE="chamneul-postgres-ro"
PW="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"

psql_admin() {
  docker compose exec -T db sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
}

# 1) Role + password. The password travels only through stdin, never argv.
psql_admin <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'chamneul_ro') THEN
    CREATE ROLE chamneul_ro LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 3;
  END IF;
END \$\$;
ALTER ROLE chamneul_ro PASSWORD '$PW';
SQL

# 2) Privileges (idempotent).
psql_admin <<'SQL'
ALTER ROLE chamneul_ro SET default_transaction_read_only = on;
ALTER ROLE chamneul_ro SET statement_timeout = '5s';
GRANT CONNECT ON DATABASE chamneul TO chamneul_ro;
GRANT USAGE ON SCHEMA public TO chamneul_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chamneul_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE chamneul IN SCHEMA public GRANT SELECT ON TABLES TO chamneul_ro;
REVOKE SELECT ON django_session FROM chamneul_ro;
REVOKE SELECT ON accounts_user FROM chamneul_ro;
DO $$
DECLARE cols text;
BEGIN
  SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position) INTO cols
  FROM information_schema.columns
  WHERE table_schema = 'public' AND table_name = 'accounts_user' AND column_name <> 'password';
  EXECUTE format('GRANT SELECT (%s) ON accounts_user TO chamneul_ro', cols);
END $$;
SQL

# 3) Keychain (-U updates an existing item). Only after the DB accepted it.
security add-generic-password -U -a "$USER" -s "$KEYCHAIN_SERVICE" \
  -l "chamneul local DB read-only (ADR-009)" -w "$PW"
unset PW

echo "chamneul_ro ready. Restart the MCP server: /mcp in Claude Code."
