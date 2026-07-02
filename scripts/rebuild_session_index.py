#!/usr/bin/env python3
"""Rebuild processed/session_index.csv from existing Layer 1 / Layer 2 outputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
L25_SRC = ROOT / "Layer2.5_Segmentation" / "src"
if str(L25_SRC) not in sys.path:
    sys.path.insert(0, str(L25_SRC))

from session_pipeline import rebuild_session_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--layer1-root",
        type=Path,
        default=None,
        help="Layer 1 outputs root (default: motive_qc/outputs)",
    )
    parser.add_argument(
        "--layer2-root",
        type=Path,
        default=None,
        help="Layer 2 outputs root (default: processed/layer2 or L2 outputs/)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output CSV path (default: processed/session_index.csv)",
    )
    args = parser.parse_args()

    try:
        summary = rebuild_session_index(
            layer1_root=args.layer1_root,
            layer2_root=args.layer2_root,
            index_path=args.out,
            project_root=ROOT,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Wrote {summary.index_path}")
    print(f"Sessions: {summary.n_sessions} ({summary.n_matched} matched)")
    print(f"Participants: {', '.join(summary.participant_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
