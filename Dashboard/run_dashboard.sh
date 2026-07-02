#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

L25_ROOT="$REPO_ROOT/Layer2.5_Segmentation"
L3_ROOT="$REPO_ROOT/Layer3_JcvPCA"
DASHBOARD_ROOT="$REPO_ROOT/Dashboard"

if [[ -d "$L25_ROOT/.venv" ]]; then
  # shellcheck disable=SC1091
  source "$L25_ROOT/.venv/bin/activate"
fi

if ! python -c "import streamlit, matplotlib, sklearn" >/dev/null 2>&1; then
  echo "Installing dashboard dependencies (streamlit, matplotlib, scikit-learn, ...)..."
  python -m pip install -r "$DASHBOARD_ROOT/requirements-dashboard.txt"
fi

if ! python -c "import pre_jvcpca_review" >/dev/null 2>&1; then
  echo "Installing Layer 2.5 package..."
  python -m pip install -e "$L25_ROOT"
fi

if [[ -d "$L3_ROOT" ]] && ! python -c "import layer3_jcvpca" >/dev/null 2>&1; then
  echo "Installing Layer 3 JcvPCA package..."
  python -m pip install -e "$L3_ROOT"
fi

exec streamlit run "$DASHBOARD_ROOT/status_dashboard.py" --server.headless true "$@"
