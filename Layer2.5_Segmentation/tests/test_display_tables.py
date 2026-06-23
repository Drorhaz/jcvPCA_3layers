"""Tests for Phase A+ display tables and policies."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from layer2_motive.segmentation.load_inputs import load_layer1_qc_folder, load_layer2_export_folder
from layer2_motive.segmentation.marker_family import build_mapper_from_datadescriptions
from layer2_motive.segmentation.qc_events import build_layer1_event_table
from layer2_motive.segmentation.schemas import (
    COMBINED_QC_EVENT_SUMMARY_COLUMNS,
    LAYER1_MARKER_FAMILY_RISK_COLUMNS,
    LAYER2_LINK_SCOPE_DISPLAY_COLUMNS,
    QC_EVENT_DISPLAY_COLUMNS,
    WINDOW_QC_SUMMARY_DISPLAY_COLUMNS,
    ExportScopePolicy,
    GapPolicy,
    QCEvidencePolicy,
)
from layer2_motive.segmentation.validate_inputs import run_all_validations
from layer2_motive.segmentation.window_summary import (
    build_combined_qc_event_table,
    build_layer2_link_scope_display,
    build_qc_event_display,
    subset_layer1_events_to_window,
    subset_layer2_to_window,
    summarize_layer1_window,
    summarize_layer2_window,
    write_window_review_outputs,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
T1_DATADESC = (
    REPO_ROOT
    / "data_description"
    / "671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001_DataDescriptions.csv"
)


def _run_window_pipeline(
    fixture_layer1_dir,
    fixture_layer2_dir,
    start: int = 16000,
    end: int = 17000,
    *,
    gap_policy: GapPolicy = GapPolicy("strict"),
    export_scope: str = "core_candidate",
    datadescriptions: str | None = None,
):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    warnings: list[str] = []
    mapper = build_mapper_from_datadescriptions(datadescriptions, warnings)
    events = build_layer1_event_table(l1, "671_T1_P1_R1", mapper=mapper)
    l1_win = subset_layer1_events_to_window(events, start, end)
    l2_win = subset_layer2_to_window(l2.parquet_df, start, end)
    l1_summary = summarize_layer1_window(
        l1.qc_mask, l1_win, start, end, gap_policy=gap_policy
    )
    l2_summary = summarize_layer2_window(l2.parquet_df, l2.link_manifest, start, end)
    combined = build_combined_qc_event_table(
        l1_win, l2_win, l2.link_manifest, mapper=mapper
    )
    return {
        "l1": l1,
        "l2": l2,
        "l1_win": l1_win,
        "l2_win": l2_win,
        "l1_summary": l1_summary,
        "l2_summary": l2_summary,
        "combined": combined,
        "mapper": mapper,
        "gap_policy": gap_policy,
        "export_scope_policy": ExportScopePolicy(export_scope),
        "evidence_policy": QCEvidencePolicy(),
    }


def test_strict_vs_relaxed_gap_0p2_counted(fixture_layer1_dir, fixture_layer2_dir):
    strict = _run_window_pipeline(
        fixture_layer1_dir, fixture_layer2_dir, gap_policy=GapPolicy("strict")
    )
    relaxed = _run_window_pipeline(
        fixture_layer1_dir, fixture_layer2_dir, gap_policy=GapPolicy("relaxed")
    )
    assert strict["l1_summary"]["gap_0p2_counted_in_burden"] is True
    assert relaxed["l1_summary"]["gap_0p2_counted_in_burden"] is False
    # gap_0p2 still visible in both
    assert strict["l1_summary"]["gap_0p2_percent"] == relaxed["l1_summary"]["gap_0p2_percent"]
    assert strict["l1_summary"]["gap_0p2_percent"] >= 0


def test_display_table_columns(fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    data = _run_window_pipeline(fixture_layer1_dir, fixture_layer2_dir)
    validation = run_all_validations(data["l1"], data["l2"])
    out = write_window_review_outputs(
        tmp_path / "display_out",
        validation_result=validation,
        identity=validation.identity,
        layer1_bundle=data["l1"],
        layer2_bundle=data["l2"],
        start_frame=16000,
        end_frame=17000,
        layer1_summary=data["l1_summary"],
        layer2_summary=data["l2_summary"],
        combined_events=data["combined"],
        gap_policy=data["gap_policy"],
        export_scope_policy=data["export_scope_policy"],
        mapper=data["mapper"],
        layer1_window_events=data["l1_win"],
    )

    window_df = pd.read_csv(out / "window_qc_summary_display.csv")
    qc_df = pd.read_csv(out / "qc_event_display.csv")
    link_df = pd.read_csv(out / "layer2_link_scope_display.csv")
    risk_df = pd.read_csv(out / "layer1_marker_family_risk.csv")
    summary_df = pd.read_csv(out / "combined_qc_event_summary.csv")

    assert list(window_df.columns) == list(WINDOW_QC_SUMMARY_DISPLAY_COLUMNS)
    assert list(qc_df.columns) == list(QC_EVENT_DISPLAY_COLUMNS)
    assert list(link_df.columns) == list(LAYER2_LINK_SCOPE_DISPLAY_COLUMNS)
    assert list(risk_df.columns) == list(LAYER1_MARKER_FAMILY_RISK_COLUMNS)
    assert "export_scope" in window_df.columns
    assert list(summary_df.columns) == list(COMBINED_QC_EVENT_SUMMARY_COLUMNS)


def test_export_scope_core_default_filters_links(fixture_layer1_dir, fixture_layer2_dir):
    data = _run_window_pipeline(
        fixture_layer1_dir, fixture_layer2_dir, export_scope="core_candidate"
    )
    link_display = build_layer2_link_scope_display(
        data["l2_summary"]["per_link_summary"],
        data["l1_win"],
        data["l1"].qc_mask[data["l1"].qc_mask["frame"].between(16000, 17000)],
        export_scope_policy=data["export_scope_policy"],
        gap_policy=data["gap_policy"],
        mapping_version="heuristic_v0",
        template_mapping_status="missing_datadescriptions_fallback_to_heuristic",
        n_window_frames=data["l1_summary"]["n_window_frames"],
    )
    assert link_display["feature_scope"].eq("core_candidate").all()
    assert link_display["included_by_export_scope"].all()
    assert link_display["selection_default"].equals(link_display["included_by_export_scope"])


def test_all_links_audit_shows_excluded(fixture_layer1_dir, fixture_layer2_dir):
    data = _run_window_pipeline(
        fixture_layer1_dir, fixture_layer2_dir, export_scope="all_links_audit"
    )
    link_display = build_layer2_link_scope_display(
        data["l2_summary"]["per_link_summary"],
        data["l1_win"],
        data["l1"].qc_mask[data["l1"].qc_mask["frame"].between(16000, 17000)],
        export_scope_policy=data["export_scope_policy"],
        gap_policy=data["gap_policy"],
        mapping_version="heuristic_v0",
        template_mapping_status="missing_datadescriptions_fallback_to_heuristic",
        n_window_frames=data["l1_summary"]["n_window_frames"],
    )
    assert len(link_display) == 50
    assert link_display["feature_scope"].isin(["excluded_distal", "excluded_toe"]).any()


def test_display_smaller_than_audit(fixture_layer1_dir, fixture_layer2_dir):
    data = _run_window_pipeline(fixture_layer1_dir, fixture_layer2_dir)
    qc_display = build_qc_event_display(
        data["combined"],
        evidence_policy=QCEvidencePolicy(),
        gap_policy=data["gap_policy"],
    )
    assert len(qc_display) <= len(data["combined"])


def test_l1_events_no_link_id(fixture_layer1_dir, fixture_layer2_dir):
    data = _run_window_pipeline(fixture_layer1_dir, fixture_layer2_dir)
    l1 = data["combined"][data["combined"]["source_layer"] == "layer1"]
    assert l1["link_id"].isna().all()
    assert l1["parent_canonical"].isna().all()


def test_pipeline_without_datadescriptions(fixture_layer1_dir, fixture_layer2_dir):
    data = _run_window_pipeline(fixture_layer1_dir, fixture_layer2_dir)
    assert not data["mapper"].datadescriptions_used
    l1_events = data["l1_win"]
    if not l1_events.empty:
        marker_rows = l1_events[l1_events["marker_raw_name"].notna()]
        if not marker_rows.empty:
            assert marker_rows["mapping_source"].isin(
                ["marker_name_heuristic", "body_region_group", "unmapped"]
            ).any()


@pytest.mark.skipif(not T1_DATADESC.exists(), reason="T1 DataDescriptions fixture missing")
def test_pipeline_with_datadescriptions(fixture_layer1_dir, fixture_layer2_dir):
    data = _run_window_pipeline(
        fixture_layer1_dir, fixture_layer2_dir, datadescriptions=str(T1_DATADESC)
    )
    assert data["mapper"].datadescriptions_used
    l1_events = data["l1_win"]
    lhandin = l1_events[l1_events["normalized_marker_name"] == "LHandIn"]
    if not lhandin.empty:
        assert lhandin.iloc[0]["attached_bone_canonical"] == "LHand"
        assert lhandin.iloc[0]["mapping_source"] == "session_datadescriptions_optional"


def test_cli_writes_phase_a_plus_outputs(
    repo_root, fixture_layer1_dir, fixture_layer2_dir, tmp_path
):
    out_dir = tmp_path / "cli_phase_a_plus"
    script = repo_root / "scripts" / "review_segmentation_window.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--layer1-dir",
            str(fixture_layer1_dir),
            "--layer2-dir",
            str(fixture_layer2_dir),
            "--start-frame",
            "16000",
            "--end-frame",
            "17000",
            "--gap-policy",
            "strict",
            "--export-scope",
            "core_candidate",
            "--out",
            str(out_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    expected = [
        "window_qc_summary_display.csv",
        "qc_event_display.csv",
        "layer2_link_scope_display.csv",
        "layer1_marker_family_risk.csv",
        "combined_qc_event_summary.csv",
        "combined_qc_events.csv",
        "window_review_report.md",
        "window_validation_summary.json",
    ]
    for name in expected:
        assert (out_dir / name).exists(), f"missing {name}"

    summary = json.loads((out_dir / "window_validation_summary.json").read_text())
    assert summary["gap_policy"] == "strict"
    assert summary["export_scope"] == "core_candidate"
    assert summary["datadescriptions_used"] is False


@pytest.mark.skipif(not T1_DATADESC.exists(), reason="T1 DataDescriptions fixture missing")
def test_cli_with_datadescriptions(repo_root, fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    out_dir = tmp_path / "cli_with_dd"
    script = repo_root / "scripts" / "review_segmentation_window.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--layer1-dir",
            str(fixture_layer1_dir),
            "--layer2-dir",
            str(fixture_layer2_dir),
            "--datadescriptions",
            str(T1_DATADESC),
            "--start-frame",
            "16000",
            "--end-frame",
            "17000",
            "--gap-policy",
            "strict",
            "--export-scope",
            "core_candidate",
            "--out",
            str(out_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads((out_dir / "window_validation_summary.json").read_text())
    assert summary["datadescriptions_used"] is True
    assert summary["mapping_source"] == "session_datadescriptions_optional"

    risk = pd.read_csv(out_dir / "layer1_marker_family_risk.csv")
    lhandin = risk[risk["normalized_marker_name"] == "LHandIn"]
    if not lhandin.empty:
        assert lhandin.iloc[0]["attached_bone_canonical"] == "LHand"
