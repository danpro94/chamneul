#!/bin/sh
# Launches the read-only Postgres MCP server for the LOCAL compose DB
# (ADR-009 item 7). The password is read from the macOS Keychain at launch, so
# it is stored neither in ~/.claude.json nor in this repository.
# Setup / rollback: docs/00-project/AI-TOOLING-SETUP-GUIDE.md §7.
set -eu

if ! POSTGRES_PASSWORD="$(security find-generic-password -a "$USER" -s chamneul-postgres-ro -w 2>/dev/null)"; then
  echo "Keychain item 'chamneul-postgres-ro' not found (AI-TOOLING-SETUP-GUIDE §7)." >&2
  exit 1
fi
export POSTGRES_PASSWORD

# Version pinned on purpose: bump deliberately, like any other dependency.
exec npx -y @toolbox-sdk/server@1.15.0 \
  --tools-file "$(dirname "$0")/postgres-ro.tools.yaml" \
  --stdio --disable-reload --disable-version-check --log-level WARN
