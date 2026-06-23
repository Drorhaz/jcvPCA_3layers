#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if ! python -c "import streamlit, matplotlib, sklearn" >/dev/null 2>&1; then
  echo "Installing dashboard dependencies (streamlit, matplotlib, scikit-learn, ...)..."
  python -m pip install -r requirements-dashboard.txt
  python -m pip install -e .
fi

L3_ROOT="$(cd "$ROOT/../Layer3_JcvPCA" && pwd)"
if [[ -d "$L3_ROOT" ]] && ! python -c "import layer3_jcvpca" >/dev/null 2>&1; then
  echo "Installing Layer 3 JcvPCA package..."
  python -m pip install -e "$L3_ROOT"
fi

exec streamlit run dashboard/pre_jvcpca_dashboard.py --server.headless true
