#!/usr/bin/env python3
"""Run full Gaga JcvPCA batch validation and workbench pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from layer3_jcvpca.gaga_batch_runner import (
    TARGET_PARTICIPANTS,
    default_layer25_root,
    run_gaga_batch_jcvpca,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--layer25-root",
        type=Path,
        default=None,
        help="Layer 2.5 pre_jvcpca_review output root",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Batch output directory (default: outputs/gaga_batch_jcvpca_<timestamp>)",
    )
    parser.add_argument(
        "--participant",
        action="append",
        dest="participants",
        help=f"Participant id(s); default {TARGET_PARTICIPANTS}",
    )
    parser.add_argument(
        "--request",
        type=Path,
        default=None,
        help="Validated analysis_request.yaml (overrides participant/comparison selection)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Repository root for analysis_config loading",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run a single small comparison for G6 smoke validation",
    )
    args = parser.parse_args()

    batch_root = run_gaga_batch_jcvpca(
        layer25_root=args.layer25_root or default_layer25_root(),
        output_dir=args.output_dir,
        participants=args.participants,
        analysis_request_path=args.request,
        project_root=args.project_root,
        smoke=args.smoke,
    )
    print(f"Batch complete: {batch_root}")
    print(f"Summary: {batch_root / 'batch_summary.md'}")


if __name__ == "__main__":
    main()
