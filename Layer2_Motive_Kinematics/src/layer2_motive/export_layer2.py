"""Per-session Layer 2 export packaging and integrity audit (post–Stage 08)."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd

from layer2_motive.io import write_csv, write_text
from layer2_motive.reporting import timestamp_utc

STAGE08_SUBDIR = "08_filtered_rotvecs"
STAGE08_PARQUET = "filtered_relative_rotation_vectors.parquet"
EXPORT_PARQUET = "layer2_session_filtered_rotvecs.parquet"

NATIVE_FILTERED_COLS = [
    "rx_filtered_native",
    "ry_filtered_native",
    "rz_filtered_native",
    "rotvec_norm_filtered_native",
]
ANALYSIS_CLEAN_COLS = [
    "rx_filtered_analysis",
    "ry_filtered_analysis",
    "rz_filtered_analysis",
    "rotvec_norm_filtered_analysis",
]
REQUIRED_PARQUET_COLUMNS = [
    "session_id",
    "run_label",
    "frame",
    "time_sec",
    "link_id",
    "parent_canonical",
    "child_canonical",
    "feature_scope",
    "included_in_v0",
    "requires_manual_review",
    "stage08_policy",
    "stage08_output_scope",
    "stage08_analysis_eligible",
    *NATIVE_FILTERED_COLS,
    *ANALYSIS_CLEAN_COLS,
]

SEGMENTATION_RECOMMENDATIONS = (
    "candidate_include",
    "include_with_caution",
    "manual_review",
    "excluded_by_policy",
    "blocked_needs_review",
)

HIGH_ELIGIBILITY_FRACTION = 0.90
CAUTION_ELIGIBILITY_FRACTION = 0.75

EXPORT_DOWNSTREAM_USE = "post_layer2_segmentation_notebook_input"

LAYER2_EXPORT_LIMITATIONS = [
    "Relative rotations are parent-child skeleton segment orientations derived from "
    "Motive-solved global bone quaternions.",
    "Stage 08 does not interpolate or repair Stage 07 jump frames.",
    "Jump and branch-cut Stage 07 failures are masked locally (event frame ± context window), "
    "not as whole-link blocks.",
    "Native filtered values (`*_filtered_native`) are archive/review values and may "
    "exist inside QC context windows.",
    "Analysis-clean values (`*_filtered_analysis`) are NaN-masked where policy indicates "
    "ineligibility (`stage08_analysis_eligible=false`).",
    "Excluded distal/toe links are retained for traceability but are not recommended "
    "for analysis.",
    "Review/provisional trunk/spine links remain review status and are not core candidates.",
    "Final frame-window selection and joint/link selection happen later in the "
    "post–Layer 2 segmentation notebook.",
    "Layer 2 does not implement segmentation, PCA, JcvPCA, or JRW.",
]

AuditStatus = Literal["pass", "warning", "fail"]


def _count_unique(values: Any) -> int:
    series = cast(pd.Series, values)
    return int(len(series.unique()))


def _bool_sum(series: Any) -> int:
    values = cast(pd.Series, series)
    return int(values.to_numpy(dtype=bool).sum())


def _mask_sum(mask: Any) -> int:
    values = cast(pd.Series, mask)
    return int(values.to_numpy().sum())


@dataclass(frozen=True)
class AuditCheck:
    check_name: str
    status: AuditStatus
    details: str


def try_get_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        commit = result.stdout.strip()
        return commit or None
    except (OSError, subprocess.SubprocessError):
        return None


def discover_stage08_runs(
    output_root: Path,
    *,
    run_pattern: str | None = None,
) -> list[Path]:
    """Return run directories under *output_root* that contain Stage 08 parquet."""
    if not output_root.is_dir():
        return []

    runs: list[Path] = []
    for child in sorted(output_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name in {"layer2_exports"}:
            continue
        parquet = child / STAGE08_SUBDIR / STAGE08_PARQUET
        if not parquet.exists():
            continue
        if run_pattern is not None and run_pattern not in child.name:
            continue
        runs.append(child)
    return runs


def recommend_segmentation_default(
    *,
    feature_scope: str,
    stage08_policy: str,
    stage08_filter_status: str,
    requires_manual_review: bool,
    n_stage07_fail_frames: int,
    n_stage07_warning_frames: int,
    n_jump_context_frames: int,
    percent_analysis_eligible: float,
) -> tuple[str, str]:
    if (
        feature_scope in {"excluded_distal", "excluded_toe"}
        or stage08_policy == "excluded_from_analysis"
    ):
        return (
            "excluded_by_policy",
            "Distal/toe or policy-excluded link; retained for traceability only.",
        )

    if (
        feature_scope == "review_provisional"
        or requires_manual_review
        or stage08_policy == "manual_review_required"
        or stage08_filter_status == "provisional_manual_review"
    ):
        return (
            "manual_review",
            "Provisional trunk/spine or manual-review link; not a frozen core candidate.",
        )

    if (
        stage08_filter_status == "blocked_needs_review"
        or stage08_policy == "block_filter"
    ):
        return (
            "blocked_needs_review",
            "Link blocked by pipeline-integrity QC (quaternion/sign/reconstruction); "
            "human review required.",
        )

    if (
        feature_scope == "core_candidate"
        and percent_analysis_eligible >= HIGH_ELIGIBILITY_FRACTION
        and n_jump_context_frames == 0
        and n_stage07_warning_frames == 0
        and n_stage07_fail_frames == 0
    ):
        return (
            "candidate_include",
            "Core candidate with high analysis eligibility and no jump-context masking.",
        )

    if (
        feature_scope == "core_candidate"
        and percent_analysis_eligible >= CAUTION_ELIGIBILITY_FRACTION
    ):
        parts: list[str] = ["Core candidate with mostly analysis-eligible frames"]
        if n_jump_context_frames > 0:
            parts.append("localized jump-context masking present")
        if n_stage07_fail_frames > 0:
            parts.append("Stage 07 jump fail with localized masking")
        if n_stage07_warning_frames > 0:
            parts.append("Stage 07 jump warning frames present")
        return ("include_with_caution", "; ".join(parts) + ".")

    if feature_scope == "core_candidate":
        return (
            "include_with_caution",
            "Core candidate with reduced analysis eligibility; review before segmentation.",
        )

    return ("manual_review", "Non-core link scope; review recommended.")


def _load_session_metadata(run_dir: Path) -> dict[str, Any]:
    qc_session = run_dir / "07_rotation_vectors" / "qc_session_manifest.csv"
    if qc_session.exists():
        row = pd.read_csv(qc_session).iloc[0]
        return {
            "session_id": str(row.at["session_id"]),
            "run_label": str(row.at["run_label"]),
            "skeleton_template": str(
                row.get("skeleton_template", row.get("template_name", ""))
            ),
            "frame_count": int(row.at["frame_count"]),
            "sampling_rate_hz": float(row.at["sampling_rate_hz"]),
        }

    parquet = run_dir / STAGE08_SUBDIR / STAGE08_PARQUET
    df = pd.read_parquet(parquet, columns=["session_id", "run_label", "frame", "time_sec"])
    frames = _count_unique(df["frame"])
    time_values = df["time_sec"].to_numpy(dtype=float)
    duration = float(time_values.max() - time_values.min()) if frames else 0.0
    return {
        "session_id": str(df["session_id"].iloc[0]),
        "run_label": str(df["run_label"].iloc[0]),
        "skeleton_template": "",
        "frame_count": frames,
        "sampling_rate_hz": float("nan"),
        "duration_sec": duration,
    }


def _load_filter_params(run_dir: Path) -> dict[str, Any]:
    summary_path = run_dir / STAGE08_SUBDIR / "filtering_summary_by_link.csv"
    if not summary_path.exists():
        return {
            "filter_cutoff_hz": None,
            "filter_order": None,
            "jump_context_window_frames": None,
        }
    summary = pd.read_csv(summary_path)
    if summary.empty:
        return {
            "filter_cutoff_hz": None,
            "filter_order": None,
            "jump_context_window_frames": None,
        }
    first = summary.iloc[0]
    jump_window = None
    assumptions = run_dir / STAGE08_SUBDIR / "assumptions_and_limitations.md"
    if assumptions.exists():
        text = assumptions.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "Jump context window:" in line and "±" in line:
                token = line.split("±", 1)[1].strip().split()[0]
                try:
                    jump_window = int(token)
                except ValueError:
                    pass
    return {
        "filter_cutoff_hz": float(first["cutoff_hz"]),
        "filter_order": int(first["filter_order"]),
        "jump_context_window_frames": jump_window,
    }


def build_link_manifest(
    parquet_df: pd.DataFrame,
    *,
    session_id: str,
    run_label: str,
    skeleton_template: str,
    summary_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouped = parquet_df.groupby("link_id", sort=True)

    for link_id, group in grouped:
        first = group.iloc[0]
        n_total = len(group)
        n_native_finite = int(np.isfinite(group["rx_filtered_native"].to_numpy()).sum())
        n_analysis_eligible = _bool_sum(group["stage08_analysis_eligible"])
        n_analysis_nan = n_total - n_analysis_eligible
        n_jump_context = _bool_sum(group["stage08_within_jump_context_window"])
        n_branch_cut_context = (
            _bool_sum(group["stage08_within_branch_cut_context_window"])
            if "stage08_within_branch_cut_context_window" in group.columns
            else 0
        )
        n_stage07_jump = _bool_sum(group["stage08_stage07_jump_frame"])
        n_stage07_warning = int((group["stage07_jump_status"].to_numpy() == "warning").sum())
        n_stage07_fail = int((group["stage07_jump_status"].to_numpy() == "fail").sum())
        n_layer2_masked = n_analysis_nan
        percent_eligible = (n_analysis_eligible / n_total * 100.0) if n_total else 0.0

        stage08_filter_status = ""
        if summary_df is not None and link_id in summary_df["link_id"].values:
            stage08_filter_status = str(
                summary_df.loc[summary_df["link_id"] == link_id, "stage08_filter_status"].iloc[0]
            )
        else:
            stage08_filter_status = str(first.get("stage08_filter_status", ""))

        recommendation, explanation = recommend_segmentation_default(
            feature_scope=str(first["feature_scope"]),
            stage08_policy=str(first["stage08_policy"]),
            stage08_filter_status=stage08_filter_status,
            requires_manual_review=bool(first["requires_manual_review"]),
            n_stage07_fail_frames=n_stage07_fail,
            n_stage07_warning_frames=n_stage07_warning,
            n_jump_context_frames=n_jump_context,
            percent_analysis_eligible=percent_eligible / 100.0,
        )

        rows.append(
            {
                "session_id": session_id,
                "run_label": run_label,
                "skeleton_template": skeleton_template,
                "link_id": link_id,
                "parent_canonical": str(first["parent_canonical"]),
                "child_canonical": str(first["child_canonical"]),
                "feature_scope": str(first["feature_scope"]),
                "included_in_v0": bool(first["included_in_v0"]),
                "requires_manual_review": bool(first["requires_manual_review"]),
                "stage08_policy": str(first["stage08_policy"]),
                "stage08_output_scope": str(first["stage08_output_scope"]),
                "n_total_frames": n_total,
                "n_native_finite_frames": n_native_finite,
                "n_analysis_eligible_frames": n_analysis_eligible,
                "n_analysis_nan_frames": n_analysis_nan,
                "n_jump_context_frames": n_jump_context,
                "n_branch_cut_context_frames": n_branch_cut_context,
                "n_stage07_jump_frames": n_stage07_jump,
                "n_stage07_warning_frames": n_stage07_warning,
                "n_stage07_fail_frames": n_stage07_fail,
                "n_layer2_masked_frames": n_layer2_masked,
                "percent_analysis_eligible": round(percent_eligible, 4),
                "recommended_segmentation_default": recommendation,
                "short_explanation": explanation,
            }
        )

    return pd.DataFrame(rows)


def run_integrity_audit(
    *,
    run_dir: Path,
    parquet_df: pd.DataFrame,
    link_manifest: pd.DataFrame,
    session_meta: dict[str, Any],
    export_dir: Path,
    summary_json: dict[str, Any],
    report_md: str,
) -> pd.DataFrame:
    checks: list[AuditCheck] = []
    stage08_parquet = run_dir / STAGE08_SUBDIR / STAGE08_PARQUET

    checks.append(
        AuditCheck(
            "stage08_parquet_exists",
            "pass" if stage08_parquet.exists() else "fail",
            str(stage08_parquet),
        )
    )

    missing_cols = [col for col in REQUIRED_PARQUET_COLUMNS if col not in parquet_df.columns]
    checks.append(
        AuditCheck(
            "required_columns_exist",
            "pass" if not missing_cols else "fail",
            "all present" if not missing_cols else f"missing: {missing_cols}",
        )
    )

    if missing_cols:
        return pd.DataFrame(
            {
                "check_name": [c.check_name for c in checks],
                "status": [c.status for c in checks],
                "details": [c.details for c in checks],
            }
        )

    checks.append(
        AuditCheck(
            "row_count_gt_zero",
            "pass" if len(parquet_df) > 0 else "fail",
            f"rows={len(parquet_df)}",
        )
    )

    expected_frames = int(session_meta.get("frame_count", 0))
    actual_frames = _count_unique(parquet_df["frame"])
    frame_match = expected_frames == 0 or actual_frames == expected_frames
    checks.append(
        AuditCheck(
            "frame_count_matches_stage08_report",
            "pass" if frame_match else "warning",
            f"parquet_frames={actual_frames}, session_manifest_frames={expected_frames}",
        )
    )

    run_labels = parquet_df["run_label"].dropna().unique().tolist()
    checks.append(
        AuditCheck(
            "run_label_present_and_unique",
            "pass" if len(run_labels) == 1 and str(run_labels[0]) else "fail",
            f"unique_run_labels={run_labels}",
        )
    )

    missing_link_id = int(parquet_df["link_id"].isna().to_numpy().sum())
    checks.append(
        AuditCheck(
            "link_id_present",
            "pass" if missing_link_id == 0 else "fail",
            f"missing_link_id_rows={missing_link_id}",
        )
    )

    dup_count = int(parquet_df.duplicated(subset=["frame", "link_id"]).to_numpy().sum())
    checks.append(
        AuditCheck(
            "no_duplicate_frame_link_rows",
            "pass" if dup_count == 0 else "fail",
            f"duplicate_rows={dup_count}",
        )
    )

    native_ok = all(col in parquet_df.columns for col in NATIVE_FILTERED_COLS)
    checks.append(
        AuditCheck(
            "native_filtered_columns_exist",
            "pass" if native_ok else "fail",
            "present" if native_ok else f"missing {NATIVE_FILTERED_COLS}",
        )
    )

    analysis_ok = all(col in parquet_df.columns for col in ANALYSIS_CLEAN_COLS)
    checks.append(
        AuditCheck(
            "analysis_clean_columns_exist",
            "pass" if analysis_ok else "fail",
            "present" if analysis_ok else f"missing {ANALYSIS_CLEAN_COLS}",
        )
    )

    ineligible = parquet_df.loc[~parquet_df["stage08_analysis_eligible"]]
    analysis_nan_violations = 0
    for col in ANALYSIS_CLEAN_COLS:
        finite_ineligible = int(ineligible[col].notna().to_numpy().sum()) if not ineligible.empty else 0
        analysis_nan_violations += finite_ineligible
    checks.append(
        AuditCheck(
            "analysis_clean_nan_when_ineligible",
            "pass" if analysis_nan_violations == 0 else "fail",
            f"finite_values_on_ineligible_rows={analysis_nan_violations}",
        )
    )

    excluded_links = link_manifest.loc[
        link_manifest["recommended_segmentation_default"] == "excluded_by_policy", "link_id"
    ]
    excluded_violations = 0
    for link_id in excluded_links:
        link_rows = parquet_df.loc[parquet_df["link_id"] == link_id]
        excluded_violations += _bool_sum(link_rows["stage08_analysis_eligible"])
    checks.append(
        AuditCheck(
            "excluded_links_not_analysis_eligible",
            "pass" if excluded_violations == 0 else "fail",
            f"eligible_rows_on_excluded_links={excluded_violations}",
        )
    )

    review_marked_core = link_manifest.loc[
        (link_manifest["feature_scope"] == "review_provisional")
        & (link_manifest["recommended_segmentation_default"] == "candidate_include"),
        "link_id",
    ]
    checks.append(
        AuditCheck(
            "review_links_not_silently_core",
            "pass" if review_marked_core.empty else "fail",
            f"review_links_marked_candidate_include={list(review_marked_core)}",
        )
    )

    jump_context_rows = parquet_df.loc[parquet_df["stage08_within_jump_context_window"]]
    jump_eligible = (
        _bool_sum(jump_context_rows["stage08_analysis_eligible"])
        if not jump_context_rows.empty
        else 0
    )
    checks.append(
        AuditCheck(
            "jump_context_rows_analysis_ineligible",
            "pass" if jump_eligible == 0 else "fail",
            f"eligible_rows_in_jump_context={jump_eligible}",
        )
    )

    parquet_links = set(parquet_df["link_id"].unique())
    manifest_links = set(link_manifest["link_id"].unique())
    join_ok = parquet_links == manifest_links
    checks.append(
        AuditCheck(
            "link_manifest_joins_to_parquet",
            "pass" if join_ok else "fail",
            f"parquet_only={sorted(parquet_links - manifest_links)}; "
            f"manifest_only={sorted(manifest_links - parquet_links)}",
        )
    )

    forbidden_phrases = [
        "layer 3 ready",
        "layer3 ready",
        "jcvpca ready",
        "final analysis feature set frozen",
    ]
    combined_text = (
        report_md.lower()
        + json.dumps(summary_json).lower()
        + (export_dir / "README.md").read_text(encoding="utf-8").lower()
        if (export_dir / "README.md").exists()
        else report_md.lower() + json.dumps(summary_json).lower()
    )
    found_forbidden = [phrase for phrase in forbidden_phrases if phrase in combined_text]
    checks.append(
        AuditCheck(
            "no_layer3_ready_claim",
            "pass" if not found_forbidden else "fail",
            "no forbidden claims" if not found_forbidden else f"found={found_forbidden}",
        )
    )

    return pd.DataFrame(
        {
            "check_name": [c.check_name for c in checks],
            "status": [c.status for c in checks],
            "details": [c.details for c in checks],
        }
    )


def _integrity_status(audit_df: pd.DataFrame) -> AuditStatus:
    if (audit_df["status"] == "fail").any():
        return "fail"
    if (audit_df["status"] == "warning").any():
        return "warning"
    return "pass"


def _render_session_report(
    *,
    session_meta: dict[str, Any],
    source_stage08_parquet: Path,
    link_manifest: pd.DataFrame,
    parquet_df: pd.DataFrame,
    filter_params: dict[str, Any],
    stage08_report_path: Path | None,
) -> str:
    n_core = _mask_sum(link_manifest["feature_scope"] == "core_candidate")
    n_review = _mask_sum(link_manifest["feature_scope"] == "review_provisional")
    n_excluded = _mask_sum(
        link_manifest["recommended_segmentation_default"].eq("excluded_by_policy")
    )
    n_jump_events = _bool_sum(parquet_df["stage08_stage07_jump_frame"])
    n_jump_context = _bool_sum(parquet_df["stage08_within_jump_context_window"])
    n_eligible = _bool_sum(parquet_df["stage08_analysis_eligible"])
    n_ineligible = len(parquet_df) - n_eligible

    time_values = parquet_df["time_sec"].to_numpy(dtype=float)
    frame_values = parquet_df["frame"].to_numpy(dtype=int)
    time_min = float(time_values.min())
    time_max = float(time_values.max())
    frame_min = int(frame_values.min())
    frame_max = int(frame_values.max())

    lines = [
        "# Layer 2 per-session export report",
        "",
        f"Generated: {timestamp_utc()}",
        "",
        "## Session identity",
        "",
        f"- **Session ID:** {session_meta['session_id']}",
        f"- **Run label:** {session_meta['run_label']}",
        f"- **Skeleton template:** {session_meta.get('skeleton_template', '')}",
        "",
        "## Source",
        "",
        f"- **Stage 08 parquet:** `{source_stage08_parquet}`",
    ]
    if stage08_report_path and stage08_report_path.exists():
        lines.append(f"- **Stage 08 report:** `{stage08_report_path}`")
    lines.extend(
        [
            "",
            "## Frame / time range",
            "",
            f"- Frames: {frame_min}–{frame_max} "
            f"({session_meta.get('frame_count', 'n/a')} expected)",
            f"- Time (sec): {time_min:.3f}–{time_max:.3f}",
            f"- Duration (sec): {session_meta.get('duration_sec', time_max - time_min):.3f}",
            f"- Sampling rate (Hz): {session_meta.get('sampling_rate_hz', 'n/a')}",
            "",
            "## Links",
            "",
            f"- Total links: {len(link_manifest)}",
            f"- Core candidates: {n_core}",
            f"- Review/provisional: {n_review}",
            f"- Excluded by policy: {n_excluded}",
            "",
            "## Stage 07 jump summary",
            "",
            f"- Stage 07 jump event rows: {n_jump_events}",
            "",
            "## Stage 08 masking summary",
            "",
            f"- Jump-context rows: {n_jump_context}",
            f"- Analysis-eligible rows: {n_eligible}",
            f"- Analysis-ineligible rows: {n_ineligible}",
            f"- Filter cutoff/order: {filter_params.get('filter_cutoff_hz')} Hz / "
            f"{filter_params.get('filter_order')}",
            f"- Jump context window: ±{filter_params.get('jump_context_window_frames')} frames",
            "",
            "## Native vs analysis-clean",
            "",
            "- **Native filtered** columns retain Butterworth-filtered values where filtering ran; "
            "they may exist inside jump-context windows for review.",
            "- **Analysis-clean** columns are NaN where `stage08_analysis_eligible=false` "
            "(jump context, excluded links, blocked/review policy).",
            "",
            "## Known limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in LAYER2_EXPORT_LIMITATIONS)
    lines.extend(
        [
            "",
            "## Downstream use",
            "",
            "This export is a Layer 2 per-session candidate input for the post–Layer 2 "
            "segmentation notebook. It is **not** a final Layer 3/JcvPCA input and does "
            "not freeze feature selection.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_assumptions_md() -> str:
    lines = [
        "# Layer 2 session export — assumptions and limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in LAYER2_EXPORT_LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def _render_readme() -> str:
    return "\n".join(
        [
            "# Layer 2 per-session export",
            "",
            "This folder is a per-session Layer 2 export package for the post–Layer 2 "
            "segmentation notebook (`notebooks/post_layer2_segmentation_review.ipynb`).",
            "",
            "## Files",
            "",
            f"- **Main signal parquet:** `{EXPORT_PARQUET}`",
            "- **Link manifest:** `layer2_session_link_manifest.csv`",
            "- **Session summary (JSON):** `layer2_session_summary.json`",
            "- **Human report:** `layer2_session_report.md`",
            "- **Integrity audit:** `layer2_session_integrity_audit.csv`",
            "",
            "## External input",
            "",
            "Provide the matching Layer 1 raw QC mask for this session separately when "
            "running the segmentation notebook.",
            "",
            "This export does not combine sessions and is not Layer 3-ready.",
            "",
        ]
    )


def export_session(
    run_dir: Path,
    export_root: Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Package one Stage 08 run into a per-session Layer 2 export folder."""
    stage08_parquet = run_dir / STAGE08_SUBDIR / STAGE08_PARQUET
    if not stage08_parquet.exists():
        raise FileNotFoundError(f"Stage 08 parquet missing: {stage08_parquet}")

    session_meta = _load_session_metadata(run_dir)
    run_label = str(session_meta["run_label"])
    export_dir = export_root / run_label
    export_parquet_path = export_dir / EXPORT_PARQUET

    if export_dir.exists() and not force:
        marker = export_dir / "layer2_session_summary.json"
        if marker.exists():
            return _load_existing_export_summary(export_dir, run_dir)

    export_dir.mkdir(parents=True, exist_ok=True)

    parquet_df = pd.read_parquet(stage08_parquet)
    source_row_count = len(parquet_df)

    shutil.copy2(stage08_parquet, export_parquet_path)
    copied_df = pd.read_parquet(export_parquet_path)
    if len(copied_df) != source_row_count:
        raise RuntimeError(
            f"Parquet row count changed during copy: {source_row_count} -> {len(copied_df)}"
        )

    summary_path = run_dir / STAGE08_SUBDIR / "filtering_summary_by_link.csv"
    summary_df = pd.read_csv(summary_path) if summary_path.exists() else None

    if "duration_sec" not in session_meta:
        session_meta["duration_sec"] = float(
            parquet_df["time_sec"].max() - parquet_df["time_sec"].min()
        )

    link_manifest = build_link_manifest(
        parquet_df,
        session_id=str(session_meta["session_id"]),
        run_label=run_label,
        skeleton_template=str(session_meta.get("skeleton_template", "")),
        summary_df=summary_df,
    )
    write_csv(link_manifest, export_dir / "layer2_session_link_manifest.csv")

    filter_params = _load_filter_params(run_dir)
    n_core = _mask_sum(link_manifest["feature_scope"] == "core_candidate")
    n_review = _mask_sum(link_manifest["feature_scope"] == "review_provisional")
    n_excluded = _mask_sum(
        link_manifest["recommended_segmentation_default"].eq("excluded_by_policy")
    )

    summary_json: dict[str, Any] = {
        "session_id": session_meta["session_id"],
        "run_label": run_label,
        "source_stage08_parquet": str(stage08_parquet.resolve()),
        "export_path": str(export_dir.resolve()),
        "skeleton_template": session_meta.get("skeleton_template", ""),
        "frame_count": int(session_meta.get("frame_count", _count_unique(parquet_df["frame"]))),
        "duration_sec": float(session_meta.get("duration_sec", 0.0)),
        "sampling_rate_hz": session_meta.get("sampling_rate_hz"),
        "n_links_total": len(link_manifest),
        "n_core_candidate_links": n_core,
        "n_review_provisional_links": n_review,
        "n_excluded_links": n_excluded,
        "n_stage07_jump_frames": _bool_sum(parquet_df["stage08_stage07_jump_frame"]),
        "n_stage08_jump_context_rows": _bool_sum(parquet_df["stage08_within_jump_context_window"]),
        "n_analysis_eligible_rows": _bool_sum(parquet_df["stage08_analysis_eligible"]),
        "n_analysis_ineligible_rows": len(parquet_df)
        - _bool_sum(parquet_df["stage08_analysis_eligible"]),
        "filter_cutoff_hz": filter_params.get("filter_cutoff_hz"),
        "filter_order": filter_params.get("filter_order"),
        "jump_context_window_frames": filter_params.get("jump_context_window_frames"),
        "export_created_at": timestamp_utc(),
        "git_commit": try_get_git_commit(),
        "layer2_status": "complete",
        "downstream_use": EXPORT_DOWNSTREAM_USE,
    }

    report_md = _render_session_report(
        session_meta=session_meta,
        source_stage08_parquet=stage08_parquet,
        link_manifest=link_manifest,
        parquet_df=parquet_df,
        filter_params=filter_params,
        stage08_report_path=run_dir / STAGE08_SUBDIR / "report.md",
    )
    write_text(export_dir / "layer2_session_report.md", report_md)
    write_text(
        export_dir / "layer2_session_assumptions_and_limitations.md",
        _render_assumptions_md(),
    )
    write_text(export_dir / "README.md", _render_readme())

    audit_df = run_integrity_audit(
        run_dir=run_dir,
        parquet_df=parquet_df,
        link_manifest=link_manifest,
        session_meta=session_meta,
        export_dir=export_dir,
        summary_json=summary_json,
        report_md=report_md,
    )
    write_csv(audit_df, export_dir / "layer2_session_integrity_audit.csv")

    integrity_status = _integrity_status(audit_df)
    summary_json["integrity_status"] = integrity_status
    summary_json["ready_for_segmentation_notebook"] = integrity_status != "fail"
    (export_dir / "layer2_session_summary.json").write_text(
        json.dumps(summary_json, indent=2),
        encoding="utf-8",
    )

    return {
        "session_id": session_meta["session_id"],
        "run_label": run_label,
        "export_folder": str(export_dir),
        "skeleton_template": session_meta.get("skeleton_template", ""),
        "frame_count": summary_json["frame_count"],
        "duration_sec": summary_json["duration_sec"],
        "n_links_total": summary_json["n_links_total"],
        "n_core_candidate_links": n_core,
        "n_review_provisional_links": n_review,
        "n_excluded_links": n_excluded,
        "n_stage07_jump_frames": summary_json["n_stage07_jump_frames"],
        "n_stage08_jump_context_rows": summary_json["n_stage08_jump_context_rows"],
        "n_analysis_eligible_rows": summary_json["n_analysis_eligible_rows"],
        "n_analysis_ineligible_rows": summary_json["n_analysis_ineligible_rows"],
        "n_rows": len(parquet_df),
        "integrity_status": integrity_status,
        "ready_for_segmentation_notebook": summary_json["ready_for_segmentation_notebook"],
        "notes": "",
    }


def _load_existing_export_summary(export_dir: Path, run_dir: Path) -> dict[str, Any]:
    summary = json.loads((export_dir / "layer2_session_summary.json").read_text(encoding="utf-8"))
    parquet_df = pd.read_parquet(export_dir / EXPORT_PARQUET)
    return {
        "session_id": summary["session_id"],
        "run_label": summary["run_label"],
        "export_folder": str(export_dir),
        "skeleton_template": summary.get("skeleton_template", ""),
        "frame_count": summary.get("frame_count"),
        "duration_sec": summary.get("duration_sec"),
        "n_links_total": summary.get("n_links_total"),
        "n_core_candidate_links": summary.get("n_core_candidate_links"),
        "n_review_provisional_links": summary.get("n_review_provisional_links"),
        "n_excluded_links": summary.get("n_excluded_links"),
        "n_stage07_jump_frames": summary.get("n_stage07_jump_frames"),
        "n_stage08_jump_context_rows": summary.get("n_stage08_jump_context_rows"),
        "n_analysis_eligible_rows": summary.get("n_analysis_eligible_rows"),
        "n_analysis_ineligible_rows": summary.get("n_analysis_ineligible_rows"),
        "n_rows": len(parquet_df),
        "integrity_status": summary.get("integrity_status", "pass"),
        "ready_for_segmentation_notebook": summary.get("ready_for_segmentation_notebook", True),
        "notes": "skipped (existing export)",
        "source_run_dir": str(run_dir),
    }


def write_export_index(rows: list[dict[str, Any]], export_root: Path) -> None:
    export_root.mkdir(parents=True, exist_ok=True)
    columns = [
        "session_id",
        "run_label",
        "export_folder",
        "skeleton_template",
        "frame_count",
        "duration_sec",
        "n_links_total",
        "n_core_candidate_links",
        "n_review_provisional_links",
        "n_excluded_links",
        "n_stage07_jump_frames",
        "n_stage08_jump_context_rows",
        "n_analysis_eligible_rows",
        "n_analysis_ineligible_rows",
        "integrity_status",
        "ready_for_segmentation_notebook",
        "notes",
    ]
    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    index_df = cast(pd.DataFrame, df.loc[:, columns])
    write_csv(index_df, export_root / "layer2_export_index.csv")

    lines = [
        "# Layer 2 per-session export index",
        "",
        f"Generated: {timestamp_utc()}",
        "",
        "Per-session Layer 2 export packages for the post–Layer 2 segmentation notebook. "
        "**No combined cross-session signal parquet is produced.**",
        "",
        f"Total exported sessions: {len(df)}",
        "",
    ]
    for _, row in df.iterrows():
        lines.extend(
            [
                f"## `{row['run_label']}`",
                "",
                f"- **Session ID:** {row['session_id']}",
                f"- **Export folder:** `{row['export_folder']}`",
                f"- **Frames / duration:** {row['frame_count']} / {row['duration_sec']:.3f} s",
                f"- **Links (core/review/excluded):** {row['n_links_total']} / "
                f"{row['n_core_candidate_links']} / {row['n_review_provisional_links']} / "
                f"{row['n_excluded_links']}",
                f"- **Analysis eligible / ineligible rows:** "
                f"{row['n_analysis_eligible_rows']} / {row['n_analysis_ineligible_rows']}",
                f"- **Integrity:** {row['integrity_status']}",
                f"- **Ready for segmentation notebook:** {row['ready_for_segmentation_notebook']}",
                f"- **Notes:** {row['notes'] or '—'}",
                "",
            ]
        )
    write_text(export_root / "layer2_export_index.md", "\n".join(lines))


def export_layer2_sessions(
    output_root: Path,
    export_root: Path,
    *,
    force: bool = False,
    run_pattern: str | None = None,
) -> list[dict[str, Any]]:
    """Export all discoverable Stage 08 runs as per-session Layer 2 packages."""
    runs = discover_stage08_runs(output_root, run_pattern=run_pattern)
    if not runs:
        raise FileNotFoundError(
            f"No Stage 08 runs found under {output_root} "
            f"(pattern={run_pattern!r})"
        )

    export_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for run_dir in runs:
        rows.append(export_session(run_dir, export_root, force=force))

    write_export_index(rows, export_root)
    return rows
