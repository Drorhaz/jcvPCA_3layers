#!/usr/bin/env bash
# Deprecated: dashboard moved to repo-root Dashboard/
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "$REPO_ROOT/Dashboard/run_dashboard.sh" "$@"
