#!/usr/bin/env python3
"""CLI entrypoint for Layer 3 JcvPCA (V1, Group 4 cross-repetition).

Usage:
    python scripts/run_layer3_jcvpca.py --config config/layer3_config.yaml

The run mode (dry_validate / full) is read from the config file.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from a source checkout without installation.
_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from layer3_jcvpca.runner import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
