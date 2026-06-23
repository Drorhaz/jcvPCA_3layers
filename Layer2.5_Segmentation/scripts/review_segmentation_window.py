#!/usr/bin/env python3
"""CLI: review QC evidence for a selected frame window."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from layer2_motive.segmentation.load_inputs import InputLoadError  # noqa: E402
from layer2_motive.segmentation.notebook_review import run_window_review  # noqa: E402
from layer2_motive.segmentation.schemas import EXPORT_SCOPES, GAP_POLICIES  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review Layer 1 + Layer 2 QC for a selected frame window."
    )
    parser.add_argument("--layer1-dir", required=True)
    parser.add_argument("--layer2-dir", required=True)
    parser.add_argument("--start-frame", type=int, required=True)
    parser.add_argument("--end-frame", type=int, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--force-session-match",
        action="store_true",
        default=False,
        help="Allow session identity mismatch (logged in validation summary)",
    )
    parser.add_argument(
        "--gap-policy",
        choices=sorted(GAP_POLICIES),
        default="strict",
        help="Gap policy: strict counts gap_0p2; relaxed shows but does not count gap_0p2",
    )
    parser.add_argument(
        "--export-scope",
        choices=sorted(EXPORT_SCOPES),
        default="core_candidate",
        help="Link/joint export scope for display table filtering",
    )
    parser.add_argument(
        "--l1-evidence",
        default=None,
        help="Comma-separated Layer 1 QC evidence types to include in review",
    )
    parser.add_argument(
        "--l2-evidence",
        default=None,
        help="Comma-separated Layer 2 QC evidence types to include in review",
    )
    parser.add_argument(
        "--mapping-version",
        default=None,
        help="Mapping version label (auto-set when DataDescriptions is provided)",
    )
    parser.add_argument(
        "--datadescriptions",
        default=None,
        help="Optional session DataDescriptions CSV for marker->bone enrichment",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.end_frame < args.start_frame:
        print("ERROR: end-frame must be >= start-frame", file=sys.stderr)
        return 2

    try:
        result = run_window_review(
            args.layer1_dir,
            args.layer2_dir,
            args.start_frame,
            args.end_frame,
            gap_policy=args.gap_policy,
            export_scope=args.export_scope,
            l1_evidence=args.l1_evidence,
            l2_evidence=args.l2_evidence,
            datadescriptions=args.datadescriptions,
            mapping_version=args.mapping_version,
            out=args.out,
            force_session_match=args.force_session_match,
        )
    except InputLoadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Window review written to: {result.out_dir}")
    print(f"Frames: {result.start_frame}..{result.end_frame}")
    print(f"Gap policy: {result.gap_policy}")
    print(f"Export scope: {result.export_scope}")
    print(f"DataDescriptions used: {result.datadescriptions_used}")
    print(f"Combined QC events (audit): {result.n_combined_events}")
    print(f"  Layer 1: {result.n_layer1_events}")
    print(f"  Layer 2: {result.n_layer2_events}")
    for warning in result.mapper_warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
