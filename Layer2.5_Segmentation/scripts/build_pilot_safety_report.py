#!/usr/bin/env python3
"""Build upper-body pilot feature safety review report."""

from __future__ import annotations

import argparse
from pathlib import Path

from pre_jvcpca_review.canonical_manifest import DEFAULT_PILOT_MANIFEST
from pre_jvcpca_review.pilot_safety_report import write_pilot_safety_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate upper-body pilot feature safety report for T1/T2 sessions."
    )
    parser.add_argument(
        "--layer2-base-dir",
        type=Path,
        required=True,
        help="Directory containing Layer 2 run or export folders",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/pilot_review/group4_upper_body_pilot_safety_report.csv"),
        help="Output CSV path",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_PILOT_MANIFEST,
        help="Pilot feature manifest CSV",
    )
    args = parser.parse_args()

    out = write_pilot_safety_report(
        args.layer2_base_dir,
        args.out,
        manifest_path=args.manifest,
    )
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
