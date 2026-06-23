"""Generic batch Stage 00–01 runner and report index builder."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from layer2_motive.parsing import parse_motive_header
from layer2_motive.qc_propagation import rebuild_layer2_qc_manifests
from layer2_motive.stages.stage01 import run_stage_01
from layer2_motive.stages.stage02 import run_stage_02
from layer2_motive.stages.stage03 import run_stage_03
from layer2_motive.stages.stage04 import run_stage_04
from layer2_motive.stages.stage05 import run_stage_05
from layer2_motive.stages.stage06 import run_stage_06
from layer2_motive.stages.stage07 import run_stage_07
from layer2_motive.stages.stage08 import run_stage_08
from layer2_motive.validation import HardStopError

STAGE02_LIMITATION_STATEMENT = (
    "Stage 02 component-order success does not imply quaternion norm validity, "
    "temporal continuity, gap safety, relative-rotation correctness, or Layer 3 readiness."
)


def safe_output_name(csv_path: Path) -> str:
    """Build a filesystem-safe output folder name from any CSV path."""
    stem = csv_path.stem
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or "motive_session"


def discover_csv_inputs(
    *,
    inputs: list[Path] | None = None,
    input_dir: Path | None = None,
    pattern: str = "*.csv",
    recursive: bool = True,
) -> list[Path]:
    discovered: list[Path] = []
    if inputs:
        discovered.extend(inputs)
    if input_dir is not None:
        globber = input_dir.rglob if recursive else input_dir.glob
        discovered.extend(sorted(globber(pattern)))
    unique = sorted({path.resolve() for path in discovered if path.suffix.lower() == ".csv"})
    return unique


def summarize_run_output(csv_path: Path, out_dir: Path) -> dict[str, str | int | float]:
    meta = pd.read_csv(out_dir / "00_csv_structure" / "metadata_detected.csv")
    meta_map = dict(zip(meta["field"], meta["value"], strict=False))
    detected = pd.read_csv(out_dir / "00_csv_structure" / "detected_columns.csv")
    inventory = pd.read_csv(out_dir / "01_joint_mapping" / "bone_inventory.csv")
    candidate = pd.read_csv(out_dir / "01_joint_mapping" / "candidate_joint_map.csv")
    selected = pd.read_csv(out_dir / "01_joint_mapping" / "selected_joint_map_v0.csv")
    excluded = pd.read_csv(out_dir / "01_joint_mapping" / "excluded_distal_bones.csv")

    rot_group_series = detected.loc[
        detected["layer2_role"] == "bone_rotation_quaternion", "source_name"
    ]
    rot_groups = int(rot_group_series.nunique())
    stage00_report = (out_dir / "00_csv_structure" / "report.md").read_text(encoding="utf-8")
    if "## Errors\n\n- None" in stage00_report and "PASS" in stage00_report:
        status = "PASS"
    else:
        status = "REVIEW REQUIRED"

    pop_path = out_dir / "01_joint_mapping" / "rotation_population_report.csv"
    pop_status = ""
    if pop_path.exists():
        pop = pd.read_csv(pop_path)
        if (pop["population_status"] == "fail").any():
            pop_status = "population_fail"
        elif (pop["population_status"] == "warning").any():
            pop_status = "population_warning"
        else:
            pop_status = "population_pass"

    return {
        "input_csv_path": str(csv_path),
        "output_folder": str(out_dir),
        "total_frames": meta_map.get("Total Frames", ""),
        "total_columns": len(detected),
        "rotation_type": meta_map.get("Rotation Type", ""),
        "coordinate_space": meta_map.get("Coordinate Space", ""),
        "bone_rotation_quaternion_groups": int(rot_groups),
        "detected_bones": len(inventory),
        "candidate_joints": len(candidate),
        "provisional_selected_joints": int(selected["included_in_v0"].sum()),
        "excluded_distal_finger_toe": len(excluded),
        "uncertain_candidates": int(candidate["requires_manual_review"].sum()),
        "population_check_status": pop_status,
        "hard_stop_pass_status": status,
    }


def write_batch_index(rows: list[dict[str, str | int | float]], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(index_path.with_suffix(".csv"), index=False)

    lines = [
        "# Stage 00–01 batch report index",
        "",
        "Generic index of per-file Layer 2 parser and provisional joint-mapping runs.",
        "Joint sets are **not frozen**; final analysis feature selection is deferred until "
        "after Layer 2 validation and before Layer 3.",
        "",
        "## Cross-file review note",
        "",
        "Cross-file bone and joint counts may differ across captures (e.g. skeleton-version "
        "mismatch). Stage 00–01 does **not** perform canonical alignment. Review per-file "
        "trunk summaries and uncertain candidates before Layer 3 feature selection. See "
        "`docs/FEATURE_SELECTION_BOUNDARY.md` and `docs/DECISION_LOG.md` (D007, D008).",
        "",
        f"Total runs: {len(df)}",
        "",
    ]
    for _, row in df.iterrows():
        lines.extend(
            [
                f"## `{Path(str(row['output_folder'])).name}`",
                "",
                f"- **Input:** `{row['input_csv_path']}`",
                f"- **Output:** `{row['output_folder']}`",
                f"- **Frames:** {row['total_frames']}",
                f"- **Columns:** {row['total_columns']}",
                f"- **Rotation Type:** {row['rotation_type']}",
                f"- **Coordinate Space:** {row['coordinate_space']}",
                f"- **Bone Rotation groups:** {row['bone_rotation_quaternion_groups']}",
                f"- **Bones:** {row['detected_bones']}",
                f"- **Candidate joints:** {row['candidate_joints']}",
                f"- **Provisional selected:** {row['provisional_selected_joints']}",
                f"- **Excluded distal:** {row['excluded_distal_finger_toe']}",
                f"- **Uncertain:** {row['uncertain_candidates']}",
                f"- **Population check:** {row.get('population_check_status', '')}",
                f"- **Status:** {row['hard_stop_pass_status']}",
                "",
            ]
        )
    index_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def batch_run_stage01(
    csv_paths: list[Path],
    output_root: Path,
    *,
    skip_existing: bool = True,
    config_path: Path | None = None,
    index_path: Path | None = None,
) -> list[dict[str, str | int | float]]:
    if not csv_paths:
        raise HardStopError("No CSV inputs provided for batch-run")

    output_root.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str | int | float]] = []

    for csv_path in csv_paths:
        out_dir = output_root / safe_output_name(csv_path)
        stage01_report = out_dir / "01_joint_mapping" / "report.md"
        if skip_existing and stage01_report.exists():
            index_rows.append(summarize_run_output(csv_path, out_dir))
            continue

        run_stage_01(csv_path, out_dir, config_path=config_path)
        index_rows.append(summarize_run_output(csv_path, out_dir))

    if index_path is not None:
        write_batch_index(index_rows, index_path)

    return index_rows


def _stage02_warnings_failures(by_bone: pd.DataFrame, report_text: str) -> str:
    issues: list[str] = []
    fail_count = int((by_bone["constructability_status"] == "fail").sum())
    if fail_count:
        issues.append(f"constructability_fail={fail_count}")
    incomplete = int((~by_bone["has_complete_xyzw_columns"]).sum())
    if incomplete:
        issues.append(f"incomplete_xyzw_groups={incomplete}")
    non_finite = int((by_bone["non_finite_row_count"] > 0).sum())
    if non_finite:
        issues.append(f"bones_with_non_finite_rows={non_finite}")
    if "## Errors\n\n- None" not in report_text:
        issues.append("report_errors_present")
    if "## Warnings\n\n- None" not in report_text:
        issues.append("report_warnings_present")
    return "none" if not issues else "; ".join(issues)


def summarize_stage02_output(csv_path: Path, out_dir: Path) -> dict[str, str | int | float]:
    summary = pd.read_csv(out_dir / "02_component_order" / "component_order_summary.csv")
    by_bone = pd.read_csv(out_dir / "02_component_order" / "component_order_by_bone.csv")
    inventory = pd.read_csv(out_dir / "01_joint_mapping" / "bone_inventory.csv")
    report_text = (out_dir / "02_component_order" / "report.md").read_text(encoding="utf-8")

    summary_map = dict(zip(summary["metric"], summary["value"], strict=False))
    pass_count = int((by_bone["constructability_status"] == "pass").sum())
    fail_count = int((by_bone["constructability_status"] == "fail").sum())
    non_finite_bones = int((by_bone["non_finite_row_count"] > 0).sum())
    stage03_raw = str(summary_map.get("stage03_may_proceed_for_file", "False"))
    stage03_may_proceed = stage03_raw.lower() == "true"
    warnings_failures = _stage02_warnings_failures(by_bone, report_text)

    if "PASS" in report_text and fail_count == 0 and stage03_may_proceed:
        status = "PASS"
    elif fail_count or not stage03_may_proceed:
        status = "FAIL"
    else:
        status = "REVIEW REQUIRED"

    return {
        "input_csv_path": str(csv_path),
        "output_folder": str(out_dir),
        "detected_bones": len(inventory),
        "quaternion_groups_checked": int(
            summary_map.get("bone_rotation_quaternion_groups_checked", 0)
        ),
        "selected_component_order": str(summary_map.get("selected_scipy_component_order", "")),
        "motive_to_scipy_mapping": str(summary_map.get("motive_to_scipy_mapping", "")),
        "constructability_pass_count": pass_count,
        "constructability_fail_count": fail_count,
        "bones_with_non_finite_rows": non_finite_bones,
        "warnings_failures": warnings_failures,
        "stage03_may_proceed": stage03_may_proceed,
        "stage02_status": status,
        "explicit_limitations": STAGE02_LIMITATION_STATEMENT,
    }


def write_stage02_index(rows: list[dict[str, str | int | float]], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(index_path.with_suffix(".csv"), index=False)

    lines = [
        "# Stage 02 component-order batch index",
        "",
        "Batch index of per-file quaternion component-order / SciPy compatibility validation.",
        "",
        "## Explicit limitation",
        "",
        STAGE02_LIMITATION_STATEMENT,
        "",
        f"Total runs: {len(df)}",
        "",
    ]
    for _, row in df.iterrows():
        lines.extend(
            [
                f"## `{Path(str(row['output_folder'])).name}`",
                "",
                f"- **Input:** `{row['input_csv_path']}`",
                f"- **Output:** `{row['output_folder']}`",
                f"- **Bones:** {row['detected_bones']}",
                f"- **Quaternion groups checked:** {row['quaternion_groups_checked']}",
                f"- **Selected component order:** {row['selected_component_order']}",
                f"- **Motive→SciPy mapping:** {row['motive_to_scipy_mapping']}",
                f"- **Constructability pass/fail:** {row['constructability_pass_count']}/"
                f"{row['constructability_fail_count']}",
                f"- **Bones with non-finite rows:** {row['bones_with_non_finite_rows']}",
                f"- **Warnings/failures:** {row['warnings_failures']}",
                f"- **Stage 03 may proceed:** {row['stage03_may_proceed']}",
                f"- **Status:** {row['stage02_status']}",
                f"- **Limitations:** {row['explicit_limitations']}",
                "",
            ]
        )
    index_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def batch_run_stage02(
    csv_paths: list[Path],
    output_root: Path,
    *,
    skip_existing: bool = True,
    index_path: Path | None = None,
) -> list[dict[str, str | int | float]]:
    if not csv_paths:
        raise HardStopError("No CSV inputs provided for batch-run-stage02")

    output_root.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str | int | float]] = []

    for csv_path in csv_paths:
        out_dir = output_root / safe_output_name(csv_path)
        stage01_report = out_dir / "01_joint_mapping" / "report.md"
        stage02_report = out_dir / "02_component_order" / "report.md"

        if not stage01_report.exists():
            raise HardStopError(
                f"Stage 01 outputs missing for {csv_path}; run Stage 00–01 before Stage 02 batch"
            )

        if skip_existing and stage02_report.exists():
            index_rows.append(summarize_stage02_output(csv_path, out_dir))
            continue

        parsed = parse_motive_header(csv_path)
        run_stage_02(csv_path, out_dir, parsed=parsed)
        index_rows.append(summarize_stage02_output(csv_path, out_dir))

    if index_path is not None:
        write_stage02_index(index_rows, index_path)

    return index_rows


STAGE03_LIMITATION_STATEMENT = (
    "Stage 03 timing success does not imply quaternion norm validity, gap repair, "
    "sign continuity, relative-rotation correctness, filtering readiness, or Layer 3 readiness."
)


def summarize_stage03_output(csv_path: Path, out_dir: Path) -> dict[str, str | int | float | bool]:
    summary = pd.read_csv(out_dir / "03_frame_time_validation" / "frame_time_summary.csv")
    row = summary.iloc[0]
    timing_status = str(row["timing_status"])
    stage04_may_proceed = str(row["stage04_may_proceed"]).lower() == "true"

    return {
        "input_csv_path": str(csv_path),
        "output_folder": str(out_dir),
        "observed_unique_frame_count": int(row["observed_unique_frame_count"]),
        "missing_frame_count": int(row["missing_frame_count"]),
        "duplicate_frame_count": int(row["duplicate_frame_count"]),
        "non_monotonic_frame_count": int(row["non_monotonic_frame_count"]),
        "inferred_sampling_rate_hz": row["inferred_sampling_rate_hz"],
        "metadata_sampling_rate_hz": row["metadata_sampling_rate_hz"],
        "timing_status": timing_status,
        "stage04_may_proceed": stage04_may_proceed,
        "explicit_limitations": STAGE03_LIMITATION_STATEMENT,
    }


def write_stage03_index(rows: list[dict[str, str | int | float | bool]], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(index_path.with_suffix(".csv"), index=False)

    lines = [
        "# Stage 03 frame/time batch index",
        "",
        "Batch index of per-file Frame and Time structural validation.",
        "",
        "## Explicit limitation",
        "",
        STAGE03_LIMITATION_STATEMENT,
        "",
        f"Total runs: {len(df)}",
        "",
    ]
    for _, row in df.iterrows():
        lines.extend(
            [
                f"## `{Path(str(row['output_folder'])).name}`",
                "",
                f"- **Input:** `{row['input_csv_path']}`",
                f"- **Output:** `{row['output_folder']}`",
                f"- **Observed frames:** {row['observed_unique_frame_count']}",
                f"- **Missing frames:** {row['missing_frame_count']}",
                f"- **Duplicate frames:** {row['duplicate_frame_count']}",
                f"- **Non-monotonic frames:** {row['non_monotonic_frame_count']}",
                f"- **Inferred rate (Hz):** {row['inferred_sampling_rate_hz']}",
                f"- **Metadata rate (Hz):** {row['metadata_sampling_rate_hz']}",
                f"- **Timing status:** {row['timing_status']}",
                f"- **Stage 04 may proceed:** {row['stage04_may_proceed']}",
                f"- **Limitations:** {row['explicit_limitations']}",
                "",
            ]
        )
    index_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def batch_run_stage03(
    csv_paths: list[Path],
    output_root: Path,
    *,
    skip_existing: bool = True,
    index_path: Path | None = None,
    config_path: Path | None = None,
) -> list[dict[str, str | int | float | bool]]:
    if not csv_paths:
        raise HardStopError("No CSV inputs provided for batch-run-stage03")

    output_root.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str | int | float | bool]] = []

    for csv_path in csv_paths:
        out_dir = output_root / safe_output_name(csv_path)
        stage02_report = out_dir / "02_component_order" / "report.md"
        stage03_report = out_dir / "03_frame_time_validation" / "report.md"

        if not stage02_report.exists():
            raise HardStopError(
                f"Stage 02 outputs missing for {csv_path}; run Stage 00–02 before Stage 03 batch"
            )

        if skip_existing and stage03_report.exists():
            index_rows.append(summarize_stage03_output(csv_path, out_dir))
            continue

        parsed = parse_motive_header(csv_path)
        try:
            run_stage_03(csv_path, out_dir, parsed=parsed, config_path=config_path)
        except HardStopError:
            if not stage03_report.exists():
                raise
        index_rows.append(summarize_stage03_output(csv_path, out_dir))

    if index_path is not None:
        write_stage03_index(index_rows, index_path)

    return index_rows


STAGE04_LIMITATION_STATEMENT = (
    "Stage 04 quaternion QC success does not imply sign continuity, relative-rotation "
    "correctness, filtering readiness, or Layer 3 readiness."
)


def summarize_stage04_output(csv_path: Path, out_dir: Path) -> dict[str, str | int | float | bool]:
    summary = pd.read_csv(out_dir / "04_quaternion_qc" / "quaternion_qc_summary.csv")
    row = summary.iloc[0]
    stage05_may_proceed = str(row["stage05_may_proceed"]).lower() == "true"

    return {
        "input_csv_path": str(csv_path),
        "output_folder": str(out_dir),
        "quaternion_group_count": int(row["quaternion_group_count"]),
        "groups_pass": int(row["groups_pass"]),
        "groups_warning": int(row["groups_warning"]),
        "groups_fail": int(row["groups_fail"]),
        "total_zero_norm_count": int(row["total_zero_norm_count"]),
        "total_non_finite_count": int(row["total_non_finite_count"]),
        "max_abs_norm_error_observed": row["max_abs_norm_error_observed"],
        "longest_invalid_gap_observed": int(row["longest_invalid_gap_observed"]),
        "file_qc_status": str(row["file_qc_status"]),
        "stage05_may_proceed": stage05_may_proceed,
        "explicit_limitations": STAGE04_LIMITATION_STATEMENT,
    }


def write_stage04_index(rows: list[dict[str, str | int | float | bool]], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(index_path.with_suffix(".csv"), index=False)

    total_groups = int(df["quaternion_group_count"].sum()) if not df.empty else 0
    files_51 = int((df["quaternion_group_count"] == 51).sum()) if not df.empty else 0
    files_55 = int((df["quaternion_group_count"] == 55).sum()) if not df.empty else 0

    lines = [
        "# Stage 04 quaternion QC batch index",
        "",
        "Batch index of per-file global bone quaternion numeric QC.",
        "",
        "## Explicit limitation",
        "",
        STAGE04_LIMITATION_STATEMENT,
        "",
        f"Total runs: {len(df)}",
        "",
        "## Batch aggregate",
        "",
        f"- **Total quaternion groups (sum across files):** {total_groups}",
        f"- **Files with 51 groups:** {files_51}",
        f"- **Files with 55 groups:** {files_55}",
        (
            f"- **Expected total for this batch:** "
            f"{files_51}×51 + {files_55}×55 = {files_51 * 51 + files_55 * 55}"
        ),
        (
            "- **Note:** Per-file counts in this index are authoritative. "
            "Any prior narrative total of 318 was a typo; the correct sum is 314 "
            "for four 51-group files and two 55-group files."
        ),
        "",
    ]
    for _, row in df.iterrows():
        lines.extend(
            [
                f"## `{Path(str(row['output_folder'])).name}`",
                "",
                f"- **Input:** `{row['input_csv_path']}`",
                f"- **Output:** `{row['output_folder']}`",
                f"- **Quaternion groups:** {row['quaternion_group_count']}",
                f"- **Groups pass/warning/fail:** {row['groups_pass']}/"
                f"{row['groups_warning']}/{row['groups_fail']}",
                f"- **Zero-norm count:** {row['total_zero_norm_count']}",
                f"- **Non-finite count:** {row['total_non_finite_count']}",
                f"- **Max norm error:** {row['max_abs_norm_error_observed']}",
                f"- **Longest invalid gap:** {row['longest_invalid_gap_observed']}",
                f"- **File QC status:** {row['file_qc_status']}",
                f"- **Stage 05 may proceed:** {row['stage05_may_proceed']}",
                f"- **Limitations:** {row['explicit_limitations']}",
                "",
            ]
        )
    index_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def batch_run_stage04(
    csv_paths: list[Path],
    output_root: Path,
    *,
    skip_existing: bool = True,
    index_path: Path | None = None,
    config_path: Path | None = None,
) -> list[dict[str, str | int | float | bool]]:
    if not csv_paths:
        raise HardStopError("No CSV inputs provided for batch-run-stage04")

    output_root.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str | int | float | bool]] = []

    for csv_path in csv_paths:
        out_dir = output_root / safe_output_name(csv_path)
        stage03_report = out_dir / "03_frame_time_validation" / "report.md"
        stage04_report = out_dir / "04_quaternion_qc" / "report.md"

        if not stage03_report.exists():
            raise HardStopError(
                f"Stage 03 outputs missing for {csv_path}; run Stage 00–03 before Stage 04 batch"
            )

        if skip_existing and stage04_report.exists():
            index_rows.append(summarize_stage04_output(csv_path, out_dir))
            continue

        parsed = parse_motive_header(csv_path)
        try:
            run_stage_04(csv_path, out_dir, parsed=parsed, config_path=config_path)
        except HardStopError:
            if not stage04_report.exists():
                raise
        index_rows.append(summarize_stage04_output(csv_path, out_dir))

    if index_path is not None:
        write_stage04_index(index_rows, index_path)

    return index_rows


STAGE05_LIMITATION_STATEMENT = (
    "Stage 05 sign-continuity success does not imply relative-rotation correctness, "
    "filtering readiness, or Layer 3 readiness."
)


def summarize_stage05_output(csv_path: Path, out_dir: Path) -> dict[str, str | int | float | bool]:
    summary = pd.read_csv(out_dir / "05_sign_continuity" / "sign_continuity_summary.csv")
    row = summary.iloc[0]
    stage06_may_proceed = str(row["stage06_may_proceed"]).lower() == "true"

    return {
        "input_csv_path": str(csv_path),
        "output_folder": str(out_dir),
        "quaternion_group_count": int(row["quaternion_group_count"]),
        "total_frames": int(row["total_frames"]),
        "total_sign_flips": int(row["total_sign_flips"]),
        "max_sign_flips_any_bone": int(row["max_sign_flips_any_bone"]),
        "bones_with_zero_flips": int(row["bones_with_zero_flips"]),
        "min_consecutive_dot_observed": row["min_consecutive_dot_observed"],
        "post_correction_valid": str(row["post_correction_valid"]).lower() == "true",
        "stage06_may_proceed": stage06_may_proceed,
        "explicit_limitations": STAGE05_LIMITATION_STATEMENT,
    }


def write_stage05_index(rows: list[dict[str, str | int | float | bool]], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(index_path.with_suffix(".csv"), index=False)

    total_groups = int(df["quaternion_group_count"].sum()) if not df.empty else 0
    total_flips = int(df["total_sign_flips"].sum()) if not df.empty else 0

    lines = [
        "# Stage 05 sign-continuity batch index",
        "",
        "Batch index of per-file global quaternion sign-continuity correction.",
        "",
        "## Explicit limitation",
        "",
        STAGE05_LIMITATION_STATEMENT,
        "",
        f"Total runs: {len(df)}",
        "",
        "## Batch aggregate",
        "",
        f"- **Total quaternion groups processed (sum across files):** {total_groups}",
        f"- **Total sign flips (sum across files):** {total_flips}",
        "",
    ]
    for _, row in df.iterrows():
        lines.extend(
            [
                f"## `{Path(str(row['output_folder'])).name}`",
                "",
                f"- **Input:** `{row['input_csv_path']}`",
                f"- **Output:** `{row['output_folder']}`",
                f"- **Quaternion groups:** {row['quaternion_group_count']}",
                f"- **Total frames:** {row['total_frames']}",
                f"- **Total sign flips:** {row['total_sign_flips']}",
                f"- **Max flips (any bone):** {row['max_sign_flips_any_bone']}",
                f"- **Bones with zero flips:** {row['bones_with_zero_flips']}",
                f"- **Min consecutive dot:** {row['min_consecutive_dot_observed']}",
                f"- **Post-correction valid:** {row['post_correction_valid']}",
                f"- **Stage 06 may proceed:** {row['stage06_may_proceed']}",
                f"- **Limitations:** {row['explicit_limitations']}",
                "",
            ]
        )
    index_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def batch_run_stage05(
    csv_paths: list[Path],
    output_root: Path,
    *,
    skip_existing: bool = True,
    index_path: Path | None = None,
    config_path: Path | None = None,
) -> list[dict[str, str | int | float | bool]]:
    if not csv_paths:
        raise HardStopError("No CSV inputs provided for batch-run-stage05")

    output_root.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str | int | float | bool]] = []

    for csv_path in csv_paths:
        out_dir = output_root / safe_output_name(csv_path)
        stage04_report = out_dir / "04_quaternion_qc" / "report.md"
        stage05_report = out_dir / "05_sign_continuity" / "report.md"

        if not stage04_report.exists():
            raise HardStopError(
                f"Stage 04 outputs missing for {csv_path}; run Stage 00–04 before Stage 05 batch"
            )

        if skip_existing and stage05_report.exists():
            index_rows.append(summarize_stage05_output(csv_path, out_dir))
            continue

        parsed = parse_motive_header(csv_path)
        try:
            run_stage_05(csv_path, out_dir, parsed=parsed, config_path=config_path)
        except HardStopError:
            if not stage05_report.exists():
                raise
        index_rows.append(summarize_stage05_output(csv_path, out_dir))

    if index_path is not None:
        write_stage05_index(index_rows, index_path)

    return index_rows


STAGE06_LIMITATION_STATEMENT = (
    "Stage 06 relative-quaternion success does not finalize analysis features, "
    "does not convert to rotation vectors, does not filter, and does not make Layer 3 ready."
)


def summarize_stage06_output(csv_path: Path, out_dir: Path) -> dict[str, str | int | float | bool]:
    summary = pd.read_csv(out_dir / "06_relative_quaternions" / "relative_quaternion_summary.csv")
    row = summary.iloc[0]
    stage07_may_proceed = str(row["stage07_may_proceed"]).lower() == "true"

    return {
        "input_csv_path": str(csv_path),
        "output_folder": str(out_dir),
        "parent_child_links_processed": int(row["parent_child_links_processed"]),
        "total_frames": int(row["total_frames"]),
        "global_max_reconstruction_error_deg": float(row["global_max_reconstruction_error_deg"]),
        "links_pass": int(row["links_pass"]),
        "links_warning": int(row["links_warning"]),
        "links_fail": int(row["links_fail"]),
        "total_relative_sign_flips_raw": int(row["total_relative_sign_flips_raw"]),
        "relative_sign_continuity_valid": str(row["relative_sign_continuity_valid"]).lower()
        == "true",
        "stage07_may_proceed": stage07_may_proceed,
        "explicit_limitations": STAGE06_LIMITATION_STATEMENT,
    }


def write_stage06_index(rows: list[dict[str, str | int | float | bool]], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(index_path.with_suffix(".csv"), index=False)

    total_links = int(df["parent_child_links_processed"].sum()) if not df.empty else 0

    lines = [
        "# Stage 06 relative quaternion batch index",
        "",
        "Batch index of per-file parent→child relative quaternion computation.",
        "",
        "## Explicit limitation",
        "",
        STAGE06_LIMITATION_STATEMENT,
        "",
        f"Total runs: {len(df)}",
        "",
        "## Batch aggregate",
        "",
        f"- **Total parent-child links processed (sum across files):** {total_links}",
        "",
    ]
    for _, row in df.iterrows():
        lines.extend(
            [
                f"## `{Path(str(row['output_folder'])).name}`",
                "",
                f"- **Input:** `{row['input_csv_path']}`",
                f"- **Output:** `{row['output_folder']}`",
                f"- **Links processed:** {row['parent_child_links_processed']}",
                f"- **Frames:** {row['total_frames']}",
                f"- **Max reconstruction error (deg):** "
                f"{row['global_max_reconstruction_error_deg']}",
                f"- **Links pass/warning/fail:** "
                f"{row['links_pass']}/{row['links_warning']}/{row['links_fail']}",
                f"- **Raw relative sign flips:** {row['total_relative_sign_flips_raw']}",
                f"- **Relative sign continuity valid:** {row['relative_sign_continuity_valid']}",
                f"- **Stage 07 may proceed:** {row['stage07_may_proceed']}",
                f"- **Limitations:** {row['explicit_limitations']}",
                "",
            ]
        )
    index_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def batch_run_stage06(
    csv_paths: list[Path],
    output_root: Path,
    *,
    skip_existing: bool = True,
    index_path: Path | None = None,
    config_path: Path | None = None,
) -> list[dict[str, str | int | float | bool]]:
    if not csv_paths:
        raise HardStopError("No CSV inputs provided for batch-run-stage06")

    output_root.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str | int | float | bool]] = []

    for csv_path in csv_paths:
        out_dir = output_root / safe_output_name(csv_path)
        stage05_report = out_dir / "05_sign_continuity" / "report.md"
        stage06_report = out_dir / "06_relative_quaternions" / "report.md"

        if not stage05_report.exists():
            raise HardStopError(
                f"Stage 05 outputs missing for {csv_path}; run Stage 00–05 before Stage 06 batch"
            )

        if skip_existing and stage06_report.exists():
            index_rows.append(summarize_stage06_output(csv_path, out_dir))
            continue

        try:
            run_stage_06(csv_path, out_dir, config_path=config_path)
        except HardStopError:
            if not stage06_report.exists():
                raise
        index_rows.append(summarize_stage06_output(csv_path, out_dir))

    if index_path is not None:
        write_stage06_index(index_rows, index_path)

    return index_rows


STAGE07_LIMITATION_STATEMENT = (
    "Stage 07 rotation-vector success does not filter, finalize analysis features, "
    "resolve skeleton-version mismatch, or make Layer 3 ready."
)


def summarize_stage07_output(csv_path: Path, out_dir: Path) -> dict[str, str | int | float | bool]:
    summary_path = out_dir / "07_rotation_vectors" / "rotvec_file_summary.csv"
    if summary_path.exists():
        row = pd.read_csv(summary_path).iloc[0]
        return {
            "input_csv_path": str(csv_path),
            "output_folder": str(out_dir),
            "links_processed": int(row["links_processed"]),
            "core_links_processed": int(row["core_links_processed"]),
            "review_links_processed": int(row["review_links_processed"]),
            "excluded_links_processed": int(row["excluded_links_processed"]),
            "max_rotvec_norm_core": float(row["max_rotvec_norm_core"]),
            "max_rotvec_norm_all": float(row["max_rotvec_norm_all"]),
            "max_jump_core": float(row["max_jump_core"]),
            "max_jump_all": float(row["max_jump_all"]),
            "core_warnings": int(row["core_warnings"]),
            "core_failures": int(row["core_failures"]),
            "review_warnings": int(row["review_warnings"]),
            "review_failures": int(row["review_failures"]),
            "excluded_warnings": int(row["excluded_warnings"]),
            "excluded_failures": int(row["excluded_failures"]),
            "stage08_may_proceed": str(row["stage08_may_proceed"]).lower() == "true",
            "explicit_limitations": STAGE07_LIMITATION_STATEMENT,
        }

    summary = pd.read_csv(out_dir / "07_rotation_vectors" / "rotvec_summary_by_link.csv")
    core = summary[summary["core_candidate"]]
    review = summary[summary["link_group"] == "review_provisional"]
    excluded = summary[summary["excluded_candidate"]]

    def _warn_fail(sub: pd.DataFrame) -> tuple[int, int]:
        if sub.empty:
            return 0, 0
        warn = int(
            ((sub["branch_cut_status"] == "warning") | (sub["jump_status"] == "warning")).sum()
        )
        fail = int(
            ((sub["branch_cut_status"] == "fail") | (sub["jump_status"] == "fail")).sum()
            + sub["non_finite_rotvec_rows"].gt(0).sum()
        )
        return warn, fail

    core_w, core_f = _warn_fail(core)
    review_w, review_f = _warn_fail(review)
    excl_w, excl_f = _warn_fail(excluded)
    core_blocking = int(core["non_finite_rotvec_rows"].gt(0).sum()) if not core.empty else 0

    return {
        "input_csv_path": str(csv_path),
        "output_folder": str(out_dir),
        "links_processed": len(summary),
        "core_links_processed": len(core),
        "review_links_processed": len(review),
        "excluded_links_processed": len(excluded),
        "max_rotvec_norm_core": float(core["max_rotvec_norm"].max()) if not core.empty else 0.0,
        "max_rotvec_norm_all": (
            float(summary["max_rotvec_norm"].max()) if not summary.empty else 0.0
        ),
        "max_jump_core": float(core["max_frame_to_frame_jump"].max()) if not core.empty else 0.0,
        "max_jump_all": float(summary["max_frame_to_frame_jump"].max())
        if not summary.empty
        else 0.0,
        "core_warnings": core_w,
        "core_failures": core_f,
        "review_warnings": review_w,
        "review_failures": review_f,
        "excluded_warnings": excl_w,
        "excluded_failures": excl_f,
        "stage08_may_proceed": core_blocking == 0,
        "explicit_limitations": STAGE07_LIMITATION_STATEMENT,
    }


def write_stage07_index(rows: list[dict[str, str | int | float | bool]], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(index_path.with_suffix(".csv"), index=False)

    lines = [
        "# Stage 07 rotation-vector batch index",
        "",
        "Batch index of per-file relative quaternion → rotation-vector log-map conversion.",
        "",
        "## Explicit limitation",
        "",
        STAGE07_LIMITATION_STATEMENT,
        "",
        "Core and excluded link diagnostics are interpreted separately. "
        "Excluded distal/finger/toe warnings do not block Stage 08 authorization when "
        "core candidate links pass.",
        "",
        f"Total runs: {len(df)}",
        "",
    ]
    for _, row in df.iterrows():
        lines.extend(
            [
                f"## `{Path(str(row['output_folder'])).name}`",
                "",
                f"- **Input:** `{row['input_csv_path']}`",
                f"- **Output:** `{row['output_folder']}`",
                f"- **Links processed:** {row['links_processed']} "
                f"(core/review/excluded: {row['core_links_processed']}/"
                f"{row['review_links_processed']}/{row['excluded_links_processed']})",
                f"- **Max rotvec norm (core / all):** {row['max_rotvec_norm_core']} / "
                f"{row['max_rotvec_norm_all']} rad",
                f"- **Max jump (core / all):** {row['max_jump_core']} / {row['max_jump_all']} rad",
                f"- **Core warnings/failures:** {row['core_warnings']}/{row['core_failures']}",
                f"- **Review warnings/failures:** "
                f"{row['review_warnings']}/{row['review_failures']}",
                f"- **Excluded warnings/failures:** {row['excluded_warnings']}/"
                f"{row['excluded_failures']}",
                f"- **Stage 08 may proceed:** {row['stage08_may_proceed']}",
                f"- **Limitations:** {row['explicit_limitations']}",
                "",
            ]
        )
    index_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def batch_run_stage07(
    csv_paths: list[Path],
    output_root: Path,
    *,
    skip_existing: bool = True,
    index_path: Path | None = None,
    config_path: Path | None = None,
) -> list[dict[str, str | int | float | bool]]:
    if not csv_paths:
        raise HardStopError("No CSV inputs provided for batch-run-stage07")

    output_root.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str | int | float | bool]] = []

    for csv_path in csv_paths:
        out_dir = output_root / safe_output_name(csv_path)
        stage06_report = out_dir / "06_relative_quaternions" / "report.md"
        stage07_report = out_dir / "07_rotation_vectors" / "report.md"

        if not stage06_report.exists():
            raise HardStopError(
                f"Stage 06 outputs missing for {csv_path}; run Stage 00–06 before Stage 07 batch"
            )

        if skip_existing and stage07_report.exists():
            index_rows.append(summarize_stage07_output(csv_path, out_dir))
            continue

        try:
            run_stage_07(csv_path, out_dir, config_path=config_path)
        except HardStopError:
            if not stage07_report.exists():
                raise
        index_rows.append(summarize_stage07_output(csv_path, out_dir))

    if index_path is not None:
        write_stage07_index(index_rows, index_path)

    rebuild_layer2_qc_manifests(output_root)

    return index_rows


STAGE08_LIMITATION_STATEMENT = (
    "Stage 08 filtering success does not finalize analysis features, freeze joint selection, "
    "or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames."
)


def summarize_stage08_output(csv_path: Path, out_dir: Path) -> dict[str, str | int | float | bool]:
    summary_path = out_dir / "08_filtered_rotvecs" / "filtering_summary_by_link.csv"
    report_path = out_dir / "08_filtered_rotvecs" / "report.md"

    summary = pd.read_csv(summary_path)

    links_pass = int(
        summary["stage08_filter_status"].isin(
            ["pass", "pass_with_warning", "filtered_but_jump_context_masked"]
        ).sum()
    )
    links_blocked = int((summary["stage08_filter_status"] == "blocked_needs_review").sum())
    links_excluded = int(
        (summary["stage08_filter_status"] == "excluded_from_analysis").sum()
    )
    links_review = int(
        (summary["stage08_filter_status"] == "provisional_manual_review").sum()
    )

    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    if "PASS" in report_text and links_pass == len(summary):
        status = "PASS"
    elif links_blocked:
        status = "REVIEW REQUIRED"
    else:
        status = "PASS WITH REVIEW"

    return {
        "input_csv_path": str(csv_path),
        "output_folder": str(out_dir),
        "links_processed": len(summary),
        "links_pass": links_pass,
        "links_with_jump_context": int((summary["jump_context_frames"] > 0).sum()),
        "links_blocked": links_blocked,
        "links_excluded": links_excluded,
        "links_review": links_review,
        "total_jump_event_frames": int(summary["jump_event_frames"].sum()),
        "total_jump_context_frames": int(summary["jump_context_frames"].sum()),
        "total_analysis_eligible_frames": int(summary["analysis_eligible_frames"].sum()),
        "interpolation_applied": False,
        "stage08_status": status,
        "explicit_limitations": STAGE08_LIMITATION_STATEMENT,
    }


def write_stage08_index(rows: list[dict[str, str | int | float | bool]], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(index_path.with_suffix(".csv"), index=False)

    lines = [
        "# Stage 08 filtering batch index",
        "",
        "Batch index of per-file Butterworth filtering with jump-context masking (V1).",
        "",
        "## Explicit limitation",
        "",
        STAGE08_LIMITATION_STATEMENT,
        "",
        "Stage 08 V1 does **not** interpolate Stage 07 jump frames. Native filtered columns may "
        "retain values inside jump-context windows; analysis-clean columns are NaN there.",
        "",
        f"Total runs: {len(df)}",
        "",
        "## Batch aggregate",
        "",
        f"- **Total jump event frames (sum across files):** "
        f"{int(df['total_jump_event_frames'].sum()) if not df.empty else 0}",
        f"- **Total jump-context frames (sum across files):** "
        f"{int(df['total_jump_context_frames'].sum()) if not df.empty else 0}",
        "",
    ]
    for _, row in df.iterrows():
        lines.extend(
            [
                f"## `{Path(str(row['output_folder'])).name}`",
                "",
                f"- **Input:** `{row['input_csv_path']}`",
                f"- **Output:** `{row['output_folder']}`",
                f"- **Links processed:** {row['links_processed']} "
                f"(pass/blocked/excluded/review: {row['links_pass']}/"
                f"{row['links_blocked']}/{row['links_excluded']}/{row['links_review']})",
                f"- **Links with jump context:** {row['links_with_jump_context']}",
                f"- **Jump event frames:** {row['total_jump_event_frames']}",
                f"- **Jump-context frames:** {row['total_jump_context_frames']}",
                f"- **Analysis-eligible frames:** {row['total_analysis_eligible_frames']}",
                f"- **Interpolation applied:** {row['interpolation_applied']}",
                f"- **Status:** {row['stage08_status']}",
                f"- **Limitations:** {row['explicit_limitations']}",
                "",
            ]
        )
    index_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def batch_run_stage08(
    csv_paths: list[Path],
    output_root: Path,
    *,
    skip_existing: bool = True,
    index_path: Path | None = None,
    config_path: Path | None = None,
    cutoff_hz: float | None = None,
    filter_order: int | None = None,
) -> list[dict[str, str | int | float | bool]]:
    if not csv_paths:
        raise HardStopError("No CSV inputs provided for batch-run-stage08")

    output_root.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str | int | float | bool]] = []

    for csv_path in csv_paths:
        out_dir = output_root / safe_output_name(csv_path)
        stage07_report = out_dir / "07_rotation_vectors" / "report.md"
        stage08_report = out_dir / "08_filtered_rotvecs" / "report.md"

        if not stage07_report.exists():
            raise HardStopError(
                f"Stage 07 outputs missing for {csv_path}; run Stage 00–07 before Stage 08 batch"
            )

        if skip_existing and stage08_report.exists():
            index_rows.append(summarize_stage08_output(csv_path, out_dir))
            continue

        try:
            run_stage_08(
                csv_path,
                out_dir,
                config_path=config_path,
                cutoff_hz=cutoff_hz,
                filter_order=filter_order,
            )
        except HardStopError:
            if not stage08_report.exists():
                raise
        index_rows.append(summarize_stage08_output(csv_path, out_dir))

    if index_path is not None:
        write_stage08_index(index_rows, index_path)

    return index_rows
