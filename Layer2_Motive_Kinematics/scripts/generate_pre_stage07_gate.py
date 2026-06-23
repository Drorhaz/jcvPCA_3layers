#!/usr/bin/env python3
"""Generate pre–Stage 07 gate reports from existing Stage 04–06 batch outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from layer2_motive.pre_stage07_gate import write_pre_stage07_gate_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate pre–Stage 07 gate artifacts")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs"),
        help="Layer 2 outputs root containing stage04–06 batch indexes",
    )
    parser.add_argument("--config", type=Path, default=None, help="Layer 2 YAML config")
    args = parser.parse_args()

    paths = write_pre_stage07_gate_artifacts(args.output_root, config_path=args.config)
    for name, path in paths.items():
        print(f"Wrote {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
