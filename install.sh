#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v uv >/dev/null 2>&1; then
    uv tool install --editable "$SCRIPT_DIR" --force
elif command -v pipx >/dev/null 2>&1; then
    pipx install --editable "$SCRIPT_DIR" --force
else
    echo "error: neither 'uv' nor 'pipx' found on PATH" >&2
    exit 1
fi

echo "apmw installed — run 'apmw --help' to verify."
