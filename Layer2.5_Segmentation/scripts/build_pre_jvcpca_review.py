#!/usr/bin/env python3
"""Build pre-JcvPCA segment/joint review CSV tables or window export files."""

from __future__ import annotations

import argparse
from pathlib import Path

from pre_jvcpca_review.build import build_full_review, build_mapping_only
from pre_jvcpca_review.export_window import export_window_for_jvcpca
from pre_jvcpca_review.schemas import QC_TYPES


def _parse_list(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build pre-JcvPCA review tables or window exports.")
    parser.add_argument("--layer1-dir", required=True, type=Path)
    parser.add_argument("--layer2-dir", required=True, type=Path)
    parser.add_argument("--datadescriptions", type=Path, default=None)
    parser.add_argument("--out", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mapping-only", action="store_true")
    mode.add_argument("--export-window-only", action="store_true")
    parser.add_argument("--start-frame", type=int, default=None)
    parser.add_argument("--end-frame", type=int, default=None)
    parser.add_argument("--selected-links", default="", help="Comma-separated link IDs, e.g. J005,J007")
    parser.add_argument(
        "--preserve-selected-link-order",
        action="store_true",
        help="Keep --selected-links list order instead of manifest order",
    )
    parser.add_argument(
        "--include-full-l2-audit-columns",
        action="store_true",
        help="Include all non-rotvec L2 audit columns in flag log CSV",
    )
    parser.add_argument(
        "--allow-nan-matrix",
        action="store_true",
        help="Allow NaNs in JcvPCA matrix feature columns",
    )
    parser.add_argument(
        "--qc-evidence",
        default=",".join(QC_TYPES),
        help="Comma-separated QC types (full review only)",
    )
    parser.add_argument("--joint-selection-preset", default=None)
    args = parser.parse_args()

    if args.mapping_only:
        selected = _parse_list(args.selected_links)
        path = build_mapping_only(
            layer1_dir=args.layer1_dir,
            layer2_dir=args.layer2_dir,
            out_dir=args.out,
            datadescriptions=args.datadescriptions,
            selected_link_ids=selected or None,
        )
        print(f"Wrote {path}")
        if selected:
            print(f"  (scoped to {len(selected)} selected links)")
        else:
            print("  (full session inventory: all labeled markers + segment pairs)")
        return

    if args.start_frame is None or args.end_frame is None:
        parser.error("--start-frame and --end-frame are required unless --mapping-only")
    selected = _parse_list(args.selected_links)
    if not selected:
        parser.error("--selected-links is required unless --mapping-only")

    if args.export_window_only:
        paths = export_window_for_jvcpca(
            layer1_dir=args.layer1_dir,
            layer2_dir=args.layer2_dir,
            out_dir=args.out,
            frame_start=args.start_frame,
            frame_end=args.end_frame,
            selected_link_ids=selected,
            preserve_input_link_order=args.preserve_selected_link_order,
            include_full_l2_audit_columns=args.include_full_l2_audit_columns,
            allow_nan_matrix=args.allow_nan_matrix,
        )
        for name, path in paths.items():
            print(f"Wrote {path} ({name})")
        return

    qc = _parse_list(args.qc_evidence)
    paths = build_full_review(
        layer1_dir=args.layer1_dir,
        layer2_dir=args.layer2_dir,
        out_dir=args.out,
        frame_start=args.start_frame,
        frame_end=args.end_frame,
        selected_link_ids=selected,
        qc_evidence=qc,
        datadescriptions=args.datadescriptions,
        joint_selection_preset=args.joint_selection_preset,
    )
    for name, path in paths.items():
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
