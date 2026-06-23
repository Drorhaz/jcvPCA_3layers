#!/usr/bin/env python3
"""Validate pilot Layer 2.5 exports against canonical feature manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pre_jvcpca_review.canonical_manifest import DEFAULT_PILOT_MANIFEST
from pre_jvcpca_review.pilot_export_validation import (
    PilotExportValidationError,
    validate_cross_session_pilot_exports,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate pilot JcvPCA exports share canonical feature identity/order."
    )
    parser.add_argument(
        "export_dirs",
        nargs="+",
        type=Path,
        help="Directories containing window_jvcpca_matrix.parquet exports",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_PILOT_MANIFEST,
        help="Pilot feature manifest CSV",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write validation report JSON on failure",
    )
    args = parser.parse_args()

    report_path = args.report
    if report_path is None:
        report_path = Path("pilot_export_validation_report.json")

    try:
        validate_cross_session_pilot_exports(
            args.export_dirs,
            manifest_path=args.manifest,
            report_path=report_path,
        )
    except PilotExportValidationError as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        if exc.report_path:
            print(f"Report written: {exc.report_path}", file=sys.stderr)
        return 1

    print("Validation passed for all export directories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
