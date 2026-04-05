#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
LOG_DIR="$ROOT_DIR/.logs"

"$ROOT_DIR/scripts/dev-stop.sh" || true
rm -f "$BACKEND_DIR/aegis.db"
rm -f "$BACKEND_DIR"/tests/test_aegis.db || true
rm -f "$LOG_DIR"/*.log || true

echo "🧹 Local sqlite database and logs cleared."
"$ROOT_DIR/scripts/dev-up.sh"
