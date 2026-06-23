#!/usr/bin/env python3
"""CLI validator for post-Layer 2 segmentation notebook inputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running without editable install when invoked from repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from layer2_motive.segmentation.load_inputs import (  # noqa: E402
    InputLoadError,
    load_layer1_qc_folder,
    load_layer2_export_folder,
)
from layer2_motive.segmentation.validate_inputs import (  # noqa: E402
    run_all_validations,
    write_validation_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Layer 1 QC + Layer 2 export folders for segmentation notebook."
    )
    parser.add_argument("--layer1-dir", required=True, help="Path to Layer 1 QC folder")
    parser.add_argument("--layer2-dir", required=True, help="Path to Layer 2 export folder")
    parser.add_argument(
        "--out",
        required=True,
        help=(
            "Output directory for validation_report.md, "
            "validation_summary.json, validation_checks.csv"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow session identity mismatch with identity_override logged",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        l1 = load_layer1_qc_folder(args.layer1_dir)
        l2 = load_layer2_export_folder(args.layer2_dir)
    except InputLoadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    result = run_all_validations(l1, l2, force=args.force)
    out_path = write_validation_outputs(result, args.out)

    print(f"Validation written to: {out_path}")
    print(f"Verdict: {'SAFE TO OPEN' if result.safe_to_open else 'BLOCKED'}")
    print(f"Checks: pass={sum(1 for c in result.checks if c.status == 'pass')}, "
          f"warn={sum(1 for c in result.checks if c.status == 'warn')}, "
          f"fail={sum(1 for c in result.checks if c.status == 'fail')}")

    if result.blocking_errors:
        print("\nBlocking errors:", file=sys.stderr)
        for err in result.blocking_errors:
            print(f"  - {err}", file=sys.stderr)

    if result.warnings:
        print("\nWarnings:")
        for warn in result.warnings:
            print(f"  - {warn}")

    return 0 if result.safe_to_open else 2


if __name__ == "__main__":
    raise SystemExit(main())
