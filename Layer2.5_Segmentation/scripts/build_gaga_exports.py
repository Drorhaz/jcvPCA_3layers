#!/usr/bin/env python3
"""CLI: batch Gaga P1–P5 + combined Group4 exports and central manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from pre_jvcpca_review.app_controller import PreJcvpcaReviewController


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Layer 2.5 review output root (default: outputs/pre_jvcpca_review)",
    )
    parser.add_argument(
        "--exercise-segments",
        type=Path,
        default=None,
        help="Exercise segmentation xlsx (default: 671_ex_segmentatios_frames.xlsx)",
    )
    parser.add_argument(
        "--participant",
        action="append",
        dest="participants",
        help="Limit to participant id(s); repeatable",
    )
    parser.add_argument("--no-combined", action="store_true", help="Skip combined_group4 export")
    parser.add_argument(
        "--no-per-exercise",
        action="store_true",
        help="Skip per-exercise P1–P5 exports",
    )
    parser.add_argument(
        "--allow-nan-matrix",
        action="store_true",
        help="Allow NaN values in export matrix",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    controller = PreJcvpcaReviewController(project_root)
    output_root = args.output_root or controller.default_output_root

    summary = controller.run_gaga_batch_export(
        output_root=output_root,
        exercise_segments_path=args.exercise_segments,
        participant_ids=args.participants,
        allow_nan_matrix=args.allow_nan_matrix,
        export_combined=not args.no_combined,
        export_per_exercise=not args.no_per_exercise,
    )

    print(f"Central manifest: {summary.central_manifest_path}")
    print(f"Export rows: {len(summary.manifest_rows)}")
    for result in summary.results:
        print(
            f"  {result.session_id}: exported={len(result.exported)} "
            f"skipped={len(result.skipped)} errors={len(result.errors)}"
        )
    for name, path in summary.readiness_paths.items():
        print(f"Readiness {name}: {path}")


if __name__ == "__main__":
    main()
