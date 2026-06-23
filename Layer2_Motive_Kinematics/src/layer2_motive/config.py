"""Load and validate Layer 2 configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load YAML config; defaults to packaged ``configs/default_layer2_config.yaml``."""
    if path is None:
        path = Path(__file__).resolve().parents[2] / "configs" / "default_layer2_config.yaml"
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Config at {path} must be a mapping")
    return data
