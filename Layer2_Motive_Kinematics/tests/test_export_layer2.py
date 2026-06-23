"""Tests for per-session Layer 2 export packaging."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from layer2_motive.export_layer2 import (
    ANALYSIS_CLEAN_COLS,
    EXPORT_PARQUET,
    build_link_manifest,
    discover_stage08_runs,
    export_layer2_sessions,
    export_session,
    run_integrity_audit,
)


def _make_stage08_parquet(frames: int = 10, links: list[str] | None = None) -> pd.DataFrame:
    links = links or ["J001", "J002", "J007"]
    rows: list[dict] = []
    for link_id in links:
        if link_id == "J007":
            feature_scope = "excluded_distal"
            policy = "excluded_from_analysis"
            review = False
            jump_status = "warning"
        elif link_id == "J002":
            feature_scope = "review_provisional"
            policy = "manual_review_required"
            review = True
            jump_status = "pass"
        else:
            feature_scope = "core_candidate"
            policy = "allow_filter"
            review = False
            jump_status = "pass"

        for frame in range(frames):
            in_jump_context = link_id == "J001" and frame in {3, 4, 5}
            jump_frame = link_id == "J001" and frame == 4
            eligible = (
                feature_scope == "core_candidate"
                and policy
                not in {
                    "excluded_from_analysis",
                    "block_filter",
                    "manual_review_required",
                }
                and not in_jump_context
            )
            rx_native = 0.1 * frame
            rows.append(
                {
                    "session_id": "671_T1_P1_R1",
                    "run_label": "test_run_label",
                    "frame": frame,
                    "time_sec": frame / 120.0,
                    "link_id": link_id,
                    "parent_canonical": "Parent",
                    "child_canonical": f"Child_{link_id}",
                    "rx_raw": rx_native,
                    "ry_raw": 0.0,
                    "rz_raw": 0.0,
                    "rotvec_norm_raw": abs(rx_native),
                    "feature_scope": feature_scope,
                    "included_in_v0": feature_scope == "core_candidate",
                    "requires_manual_review": review,
                    "stage04_quaternion_valid": True,
                    "stage05_global_sign_continuity_valid": True,
                    "stage06_relative_reconstruction_valid": True,
                    "stage06_relative_sign_continuity_valid": True,
                    "stage07_branch_cut_status": "pass",
                    "stage07_jump_status": jump_status,
                    "stage07_jump_from_previous_frame": False,
                    "stage07_jump_magnitude_rad": 0.0,
                    "stage07_row_qc_status": "pass",
                    "stage07_link_qc_status": "pass",
                    "stage08_policy": policy,
                    "rx_filtered_native": rx_native,
                    "ry_filtered_native": 0.0,
                    "rz_filtered_native": 0.0,
                    "rotvec_norm_filtered_native": abs(rx_native),
                    "rx_filtered_analysis": rx_native,
                    "ry_filtered_analysis": 0.0,
                    "rz_filtered_analysis": 0.0,
                    "rotvec_norm_filtered_analysis": abs(rx_native),
                    "stage08_filter_applied": True,
                    "stage08_filter_status": "pass",
                    "stage08_stage07_jump_frame": jump_frame,
                    "stage08_within_jump_context_window": in_jump_context,
                    "stage08_distance_to_nearest_stage07_jump_frame": 0.0 if jump_frame else 10.0,
                    "stage08_analysis_eligible": eligible,
                    "stage08_mask_reason": "" if eligible else "stage07_jump_context",
                    "stage08_output_scope": (
                        "analysis_clean_core" if eligible else "excluded_from_analysis"
                    ),
                }
            )
    return pd.DataFrame(rows)


def _write_minimal_run(tmp_path: Path, *, run_label: str = "test_run_label") -> Path:
    run_dir = tmp_path / "outputs" / run_label
    stage08 = run_dir / "08_filtered_rotvecs"
    stage08.mkdir(parents=True)
    qc_dir = run_dir / "07_rotation_vectors"
    qc_dir.mkdir(parents=True)

    df = _make_stage08_parquet()
    df["run_label"] = run_label
    df.to_parquet(stage08 / "filtered_relative_rotation_vectors.parquet", index=False)

    summary = pd.DataFrame(
        [
            {
                "link_id": "J001",
                "parent_canonical": "Parent",
                "child_canonical": "Child_J001",
                "feature_scope": "core_candidate",
                "stage08_policy": "allow_filter",
                "stage07_jump_status": "pass",
                "stage07_branch_cut_status": "pass",
                "total_frames": 10,
                "filter_applied_frames": 10,
                "jump_event_frames": 1,
                "jump_context_frames": 3,
                "analysis_eligible_frames": 7,
                "stage08_filter_status": "filtered_but_jump_context_flagged",
                "cutoff_hz": 10.0,
                "filter_order": 4,
                "sampling_rate_hz": 120.0,
                "min_filtfilt_length": 10,
            }
        ]
    )
    summary.to_csv(stage08 / "filtering_summary_by_link.csv", index=False)
    stage08.joinpath("assumptions_and_limitations.md").write_text(
        "Jump context window: ±30 frames around Stage 07 jump\n",
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "session_id": "671_T1_P1_R1",
                "run_label": run_label,
                "skeleton_template": "Test Template",
                "frame_count": 10,
                "sampling_rate_hz": 120.0,
            }
        ]
    ).to_csv(qc_dir / "qc_session_manifest.csv", index=False)
    return run_dir


def test_discover_stage08_runs(tmp_path: Path) -> None:
    _write_minimal_run(tmp_path)
    runs = discover_stage08_runs(tmp_path / "outputs")
    assert len(runs) == 1


def test_export_session_creates_folder_and_copies_parquet(tmp_path: Path) -> None:
    run_dir = _write_minimal_run(tmp_path)
    source_df = pd.read_parquet(
        run_dir / "08_filtered_rotvecs" / "filtered_relative_rotation_vectors.parquet"
    )
    export_root = tmp_path / "layer2_exports"

    export_session(run_dir, export_root, force=True)
    export_dir = export_root / "test_run_label"

    assert export_dir.is_dir()
    assert (export_dir / EXPORT_PARQUET).exists()
    assert (export_dir / "layer2_session_link_manifest.csv").exists()
    assert (export_dir / "layer2_session_summary.json").exists()
    assert (export_dir / "layer2_session_report.md").exists()
    assert (export_dir / "layer2_session_assumptions_and_limitations.md").exists()
    assert (export_dir / "layer2_session_integrity_audit.csv").exists()
    assert (export_dir / "README.md").exists()

    exported_df = pd.read_parquet(export_dir / EXPORT_PARQUET)
    assert len(exported_df) == len(source_df)
    assert list(exported_df.columns) == list(source_df.columns)


def test_link_manifest_joins_to_parquet(tmp_path: Path) -> None:
    run_dir = _write_minimal_run(tmp_path)
    export_root = tmp_path / "layer2_exports"
    export_session(run_dir, export_root, force=True)

    export_dir = export_root / "test_run_label"
    parquet_df = pd.read_parquet(export_dir / EXPORT_PARQUET)
    manifest = pd.read_csv(export_dir / "layer2_session_link_manifest.csv")
    assert set(parquet_df["link_id"]) == set(manifest["link_id"])


def test_excluded_links_not_analysis_eligible(tmp_path: Path) -> None:
    run_dir = _write_minimal_run(tmp_path)
    export_root = tmp_path / "layer2_exports"
    export_session(run_dir, export_root, force=True)

    parquet_df = pd.read_parquet(export_root / "test_run_label" / EXPORT_PARQUET)
    excluded = parquet_df.loc[parquet_df["feature_scope"] == "excluded_distal"]
    assert excluded["stage08_analysis_eligible"].sum() == 0


def test_jump_context_rows_analysis_ineligible(tmp_path: Path) -> None:
    run_dir = _write_minimal_run(tmp_path)
    export_root = tmp_path / "layer2_exports"
    export_session(run_dir, export_root, force=True)

    parquet_df = pd.read_parquet(export_root / "test_run_label" / EXPORT_PARQUET)
    jump_context = parquet_df.loc[parquet_df["stage08_within_jump_context_window"]]
    assert jump_context["stage08_analysis_eligible"].sum() == 0


def test_qc_flagged_rows_keep_numeric_analysis_values(tmp_path: Path) -> None:
    run_dir = _write_minimal_run(tmp_path)
    export_root = tmp_path / "layer2_exports"
    export_session(run_dir, export_root, force=True)

    parquet_df = pd.read_parquet(export_root / "test_run_label" / EXPORT_PARQUET)
    ineligible = parquet_df.loc[~parquet_df["stage08_analysis_eligible"]]
    qc_flagged = ineligible.loc[
        ineligible["stage08_mask_reason"].isin(
            {
                "stage07_jump_context",
                "excluded_feature_scope",
                "manual_review_provisional",
            }
        )
    ]
    for col in ANALYSIS_CLEAN_COLS:
        assert qc_flagged[col].notna().all()


def test_no_combined_signal_parquet(tmp_path: Path) -> None:
    _write_minimal_run(tmp_path, run_label="run_a")
    _write_minimal_run(tmp_path, run_label="run_b")
    export_root = tmp_path / "layer2_exports"
    export_layer2_sessions(tmp_path / "outputs", export_root, force=True)

    combined = list(export_root.glob("*combined*.parquet"))
    assert combined == []
    assert (export_root / "layer2_export_index.csv").exists()


def test_export_index_lists_all_sessions(tmp_path: Path) -> None:
    _write_minimal_run(tmp_path, run_label="run_a")
    _write_minimal_run(tmp_path, run_label="run_b")
    export_root = tmp_path / "layer2_exports"
    rows = export_layer2_sessions(tmp_path / "outputs", export_root, force=True)
    index = pd.read_csv(export_root / "layer2_export_index.csv")
    assert len(rows) == 2
    assert len(index) == 2
    assert set(index["run_label"]) == {"run_a", "run_b"}


def test_session_summary_has_required_fields(tmp_path: Path) -> None:
    run_dir = _write_minimal_run(tmp_path)
    export_root = tmp_path / "layer2_exports"
    export_session(run_dir, export_root, force=True)

    summary = json.loads(
        (export_root / "test_run_label" / "layer2_session_summary.json").read_text(encoding="utf-8")
    )
    required = {
        "session_id",
        "run_label",
        "source_stage08_parquet",
        "export_path",
        "skeleton_template",
        "frame_count",
        "duration_sec",
        "sampling_rate_hz",
        "n_links_total",
        "downstream_use",
        "integrity_status",
        "ready_for_segmentation_notebook",
    }
    assert required.issubset(summary.keys())
    assert summary["downstream_use"] == "post_layer2_segmentation_notebook_input"


def test_integrity_audit_catches_missing_columns(tmp_path: Path) -> None:
    df = _make_stage08_parquet(frames=5, links=["J001"])
    bad_df = df.drop(columns=["stage08_analysis_eligible"])
    manifest = build_link_manifest(
        df,
        session_id="671_T1_P1_R1",
        run_label="test_run_label",
        skeleton_template="Test",
    )
    audit = run_integrity_audit(
        run_dir=Path("."),
        parquet_df=bad_df,
        link_manifest=manifest,
        session_meta={"frame_count": 5},
        export_dir=Path("."),
        summary_json={"downstream_use": "post_layer2_segmentation_notebook_input"},
        report_md="not layer 3 ready",
    )
    required_check = audit.loc[audit["check_name"] == "required_columns_exist"].iloc[0]
    assert required_check["status"] == "fail"


def test_integrity_audit_passes_for_valid_fixture(tmp_path: Path) -> None:
    run_dir = _write_minimal_run(tmp_path)
    export_root = tmp_path / "layer2_exports"
    export_session(run_dir, export_root, force=True)
    audit = pd.read_csv(export_root / "test_run_label" / "layer2_session_integrity_audit.csv")
    assert (audit["status"] == "fail").sum() == 0


def test_export_raises_when_no_runs(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        export_layer2_sessions(tmp_path / "outputs", tmp_path / "layer2_exports")
