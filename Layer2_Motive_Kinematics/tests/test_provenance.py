"""Tests for Layer 2 run provenance in exports."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from layer2_motive.export_layer2 import export_session
from layer2_motive.provenance import build_run_provenance, hash_file


def _minimal_run_dir(tmp_path: Path) -> Path:
    run_dir = tmp_path / "test_run"
    stage08 = run_dir / "08_filtered_rotvecs"
    stage08.mkdir(parents=True)
    stage03 = run_dir / "03_frame_time_validation"
    stage03.mkdir(parents=True)

    frames = 5
    rows = []
    for link_id in ["J001"]:
        for frame in range(frames):
            rows.append(
                {
                    "session_id": "671_T1_P1_R1",
                    "run_label": "test_run",
                    "frame": frame,
                    "time_sec": frame / 120.0,
                    "link_id": link_id,
                    "parent_canonical": "Neck",
                    "child_canonical": "Head",
                    "rx_raw": 0.0,
                    "ry_raw": 0.0,
                    "rz_raw": 0.0,
                    "rotvec_norm_raw": 0.0,
                    "feature_scope": "core_candidate",
                    "included_in_v0": True,
                    "requires_manual_review": False,
                    "stage08_policy": "allow_filter",
                    "rx_filtered_native": 0.0,
                    "ry_filtered_native": 0.0,
                    "rz_filtered_native": 0.0,
                    "rotvec_norm_filtered_native": 0.0,
                    "rx_filtered_analysis": 0.0,
                    "ry_filtered_analysis": 0.0,
                    "rz_filtered_analysis": 0.0,
                    "rotvec_norm_filtered_analysis": 0.0,
                    "stage08_filter_applied": True,
                    "stage08_filter_status": "pass",
                    "stage08_stage07_jump_frame": False,
                    "stage08_within_jump_context_window": False,
                    "stage08_distance_to_nearest_stage07_jump_frame": 10.0,
                    "stage07_jump_status": "pass",
                    "stage08_analysis_eligible": True,
                    "stage08_mask_reason": "",
                    "stage08_output_scope": "analysis_clean_core",
                }
            )
    df = pd.DataFrame(rows)
    df.to_parquet(stage08 / "filtered_relative_rotation_vectors.parquet", index=False)

    pd.DataFrame(
        [
            {
                "input_file": str(tmp_path / "input.csv"),
                "total_rows": frames,
                "duration_seconds": 0.04,
                "inferred_sampling_rate_hz": 120.0,
                "timing_status": "pass",
                "stage04_may_proceed": True,
            }
        ]
    ).to_csv(stage03 / "frame_time_summary.csv", index=False)

    (tmp_path / "input.csv").write_text("frame,time\n0,0\n", encoding="utf-8")
    return run_dir


def test_build_run_provenance_includes_hashes(tmp_path):
    run_dir = _minimal_run_dir(tmp_path)
    provenance = build_run_provenance(run_dir=run_dir)
    assert provenance["package_version"]
    assert provenance["source_input_file_sha256"] == hash_file(tmp_path / "input.csv")
    assert provenance["config_hash_sha256"] is not None
    assert "pipeline_stage_versions" in provenance


def test_export_session_writes_provenance(tmp_path):
    run_dir = _minimal_run_dir(tmp_path)
    export_root = tmp_path / "exports"
    export_session(run_dir, export_root, force=True)

    export_dir = export_root / "test_run"
    summary = json.loads((export_dir / "layer2_session_summary.json").read_text(encoding="utf-8"))
    provenance = json.loads((export_dir / "layer2_run_provenance.json").read_text(encoding="utf-8"))

    assert summary["git_commit"] == provenance.get("git_commit")
    assert summary["config_hash_sha256"] == provenance["config_hash_sha256"]
    assert summary["source_input_file_sha256"] == provenance["source_input_file_sha256"]
