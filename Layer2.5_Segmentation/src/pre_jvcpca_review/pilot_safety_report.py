"""Upper-body pilot feature safety review report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from pre_jvcpca_review.canonical_manifest import (
    DEFAULT_PILOT_MANIFEST,
    load_pilot_manifest,
    pilot_link_order,
    resolve_session_links_from_manifest,
)
from pre_jvcpca_review.load_layer2 import LinkRecord, load_link_manifest

PILOT_SESSIONS = ("T1_R1", "T1_R2", "T2_R1", "T2_R2")
REPORT_COLUMNS = [
    "session",
    "canonical_link_name",
    "parent_canonical",
    "child_canonical",
    "session_link_id",
    "axis_triplet_present",
    "n_frames",
    "eligible_percent",
    "jump_fail_count",
    "jump_warning_count",
    "masked_frame_count",
    "nan_inf_count_analysis",
    "recommendation",
    "reason",
]


@dataclass(frozen=True)
class LinkSafetyRow:
    session: str
    canonical_link_name: str
    parent_canonical: str
    child_canonical: str
    session_link_id: str
    axis_triplet_present: bool
    n_frames: int
    eligible_percent: float
    jump_fail_count: int
    jump_warning_count: int
    masked_frame_count: int
    nan_inf_count_analysis: int
    recommendation: str
    reason: str


def _find_layer2_export(base_dir: Path, session_key: str) -> Path | None:
    """Locate Layer 2 export folder for a session key like T1_R1."""
    patterns = [
        f"*{session_key}*",
        f"671_{session_key}*",
    ]
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(base_dir.glob(pattern))
    for candidate in sorted(candidates):
        if (candidate / "layer2_session_filtered_rotvecs.parquet").exists():
            return candidate
        if (candidate / "08_filtered_rotvecs" / "filtered_relative_rotation_vectors.parquet").exists():
            return candidate
    return None


def _load_session_parquet(export_dir: Path) -> pd.DataFrame:
    primary = export_dir / "layer2_session_filtered_rotvecs.parquet"
    if primary.exists():
        return pd.read_parquet(primary)
    stage08 = export_dir / "08_filtered_rotvecs" / "filtered_relative_rotation_vectors.parquet"
    if stage08.exists():
        return pd.read_parquet(stage08)
    raise FileNotFoundError(f"No Layer 2 parquet in {export_dir}")


def _recommend_link(
    *,
    eligible_percent: float,
    jump_fail_count: int,
    jump_warning_count: int,
    masked_frame_count: int,
    nan_inf_count: int,
    canonical_link_name: str,
) -> tuple[str, str]:
    if nan_inf_count > 0:
        return (
            "exclude_from_pilot",
            f"NaN/inf in analysis columns for {canonical_link_name}",
        )
    if jump_fail_count > 0:
        return (
            "include_with_caution",
            f"Stage 07 jump fail on {canonical_link_name}; localized masking present",
        )
    if jump_warning_count > 0 or masked_frame_count > 0:
        return (
            "include_with_caution",
            f"Jump warning or masked frames on {canonical_link_name}",
        )
    if eligible_percent < 90.0:
        return (
            "include_with_caution",
            f"Analysis eligibility {eligible_percent:.1f}% below 90% for {canonical_link_name}",
        )
    return ("include", "No Layer 2 jump/mask issues in full session")


def build_pilot_safety_report(
    layer2_base_dir: Path,
    *,
    manifest_path: Path | None = None,
    sessions: tuple[str, ...] = PILOT_SESSIONS,
) -> pd.DataFrame:
    manifest = load_pilot_manifest(manifest_path or DEFAULT_PILOT_MANIFEST)
    rows: list[LinkSafetyRow] = []

    for session_key in sessions:
        export_dir = _find_layer2_export(layer2_base_dir, session_key)
        if export_dir is None:
            continue

        link_manifest_path = export_dir / "layer2_session_link_manifest.csv"
        if link_manifest_path.exists():
            session_links = load_link_manifest(link_manifest_path)
        else:
            qc_manifest = export_dir / "07_rotation_vectors" / "qc_link_manifest.csv"
            session_links = load_link_manifest(qc_manifest)

        _, links_by_canonical = resolve_session_links_from_manifest(manifest, session_links)
        parquet_df = _load_session_parquet(export_dir)

        for parent, child in pilot_link_order(manifest):
            link = links_by_canonical[(parent, child)]
            link_rows = parquet_df.loc[parquet_df["link_id"] == link.link_id]
            n_frames = len(link_rows)
            if n_frames == 0:
                rows.append(
                    LinkSafetyRow(
                        session=session_key,
                        canonical_link_name=f"{parent}->{child}",
                        parent_canonical=parent,
                        child_canonical=child,
                        session_link_id=link.link_id,
                        axis_triplet_present=False,
                        n_frames=0,
                        eligible_percent=0.0,
                        jump_fail_count=0,
                        jump_warning_count=0,
                        masked_frame_count=0,
                        nan_inf_count_analysis=0,
                        recommendation="exclude_from_pilot",
                        reason="Link absent from session parquet",
                    )
                )
                continue

            analysis_cols = ["rx_filtered_analysis", "ry_filtered_analysis", "rz_filtered_analysis"]
            axis_triplet = all(col in link_rows.columns for col in analysis_cols)
            eligible = link_rows["stage08_analysis_eligible"].astype(bool)
            eligible_percent = round(100.0 * eligible.sum() / n_frames, 2)

            jump_status = link_rows["stage07_jump_status"].iloc[0] if "stage07_jump_status" in link_rows.columns else ""
            jump_fail = int((link_rows["stage07_jump_status"] == "fail").sum()) if jump_status else 0
            jump_warn = int((link_rows["stage07_jump_status"] == "warning").sum()) if jump_status else 0

            masked = ~eligible
            masked_count = int(masked.sum())

            values = link_rows[analysis_cols].to_numpy(dtype=float) if axis_triplet else np.array([])
            nan_inf = int(np.isnan(values).sum() + np.isinf(values).sum()) if values.size else n_frames * 3

            recommendation, reason = _recommend_link(
                eligible_percent=eligible_percent,
                jump_fail_count=jump_fail,
                jump_warning_count=jump_warn,
                masked_frame_count=masked_count,
                nan_inf_count=nan_inf,
                canonical_link_name=f"{parent}->{child}",
            )

            rows.append(
                LinkSafetyRow(
                    session=session_key,
                    canonical_link_name=f"{parent}->{child}",
                    parent_canonical=parent,
                    child_canonical=child,
                    session_link_id=link.link_id,
                    axis_triplet_present=axis_triplet,
                    n_frames=n_frames,
                    eligible_percent=eligible_percent,
                    jump_fail_count=jump_fail,
                    jump_warning_count=jump_warn,
                    masked_frame_count=masked_count,
                    nan_inf_count_analysis=nan_inf,
                    recommendation=recommendation,
                    reason=reason,
                )
            )

    return pd.DataFrame([row.__dict__ for row in rows], columns=REPORT_COLUMNS)


def write_pilot_safety_report(
    layer2_base_dir: Path,
    out_path: Path,
    *,
    manifest_path: Path | None = None,
) -> Path:
    report = build_pilot_safety_report(layer2_base_dir, manifest_path=manifest_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(out_path, index=False)
    return out_path
