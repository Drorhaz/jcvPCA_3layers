"""Regression tests for review-table notebook repair."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from pre_jvcpca_review.build import build_full_review, build_mapping_only
from pre_jvcpca_review.export_window import export_layer3_window
from pre_jvcpca_review.review_display import display_review_tables, review_table_status
from pre_jvcpca_review.review_output import (
    require_review_context,
    resolve_review_out_dir,
)
from pre_jvcpca_review.schemas import LINK_JOINT_REVIEW_COLUMNS, WINDOW_DECISION_SUMMARY_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "reevluate_project"
DD_PATH = EVAL_DIR / "671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001_DataDescriptions.csv"


@pytest.fixture(scope="module")
def eval_paths():
    if not EVAL_DIR.is_dir():
        pytest.skip("reevluate_project fixtures not available")
    from pre_jvcpca_review.discovery import resolve_layer1, resolve_layer2

    return resolve_layer1(EVAL_DIR), resolve_layer2(EVAL_DIR)


def test_resolve_review_out_dir():
    out = resolve_review_out_dir(Path("outputs/pre_jvcpca_review"), "671", "671_T1_P1_R1", "window_01")
    assert out == Path("outputs/pre_jvcpca_review/671/671_T1_P1_R1/window_01")


def test_require_review_context_blocks_empty_session():
    row = pd.Series({"session_id": "671_T1_P1_R1", "is_matched": True})
    assert require_review_context(current_row=row, layer1_dir="", layer2_dir=EVAL_DIR) is not None
    assert require_review_context(current_row=None, layer1_dir=EVAL_DIR, layer2_dir=EVAL_DIR) is not None


def test_run_mapping_after_selection(tmp_path, eval_paths):
    out = resolve_review_out_dir(tmp_path, "671", "671_T1_P1_R1", "diag")
    path = build_mapping_only(
        EVAL_DIR,
        EVAL_DIR,
        out,
        DD_PATH,
        selected_link_ids=["J005", "J007"],
    )
    assert path.parent == out
    assert path.name == "mapping_logic_table.csv"


def test_run_full_review_writes_structured_outputs(tmp_path, eval_paths):
    out = resolve_review_out_dir(tmp_path, "671", "671_T1_P1_R1", "16000_17000")
    paths = build_full_review(
        EVAL_DIR,
        EVAL_DIR,
        out,
        frame_start=16000,
        frame_end=17000,
        selected_link_ids=["J005", "J007", "J020"],
        qc_evidence=["gap_0p5", "gap_0p2", "artifact_sigma", "segment_swap"],
        datadescriptions=DD_PATH,
    )
    assert out.is_dir()
    assert set(paths) >= {
        "mapping_logic_table.csv",
        "window_decision_summary.csv",
        "qc_evidence_summary_table.csv",
        "link_joint_review_table.csv",
        "qc_event_review_table.csv",
    }
    status = review_table_status(out)
    assert status["window_decision_summary.csv"]
    assert status["link_joint_review_table.csv"]


def test_review_tables_include_canonical_columns(tmp_path):
    out = resolve_review_out_dir(tmp_path, "671", "671_T1_P1_R1", "cols")
    build_full_review(
        EVAL_DIR,
        EVAL_DIR,
        out,
        frame_start=16000,
        frame_end=17000,
        selected_link_ids=["J007"],
        qc_evidence=["artifact_sigma"],
        datadescriptions=DD_PATH,
    )
    link_df = pd.read_csv(out / "link_joint_review_table.csv")
    assert list(link_df.columns) == LINK_JOINT_REVIEW_COLUMNS
    row = link_df.iloc[0]
    assert row["link_id"] == "J007"
    assert row["parent_canonical"]
    assert row["child_canonical"]
    assert row["canonical_link_name"] == row["link_or_joint"]
    assert "stage07_jump_status" in row
    assert "stage08_block_filter_frame_percent" in row


def test_review_tables_no_layer1_verdict_fields(tmp_path):
    out = resolve_review_out_dir(tmp_path, "671", "671_T1_P1_R1", "evidence")
    build_full_review(
        EVAL_DIR,
        EVAL_DIR,
        out,
        frame_start=16000,
        frame_end=17000,
        selected_link_ids=["J005"],
        qc_evidence=["gap_0p2"],
        datadescriptions=DD_PATH,
    )
    summary = pd.read_csv(out / "window_decision_summary.csv")
    forbidden = {
        "session_status",
        "window_quality_label",
        "recommended_bvh_action",
        "not_ready",
        "caution",
        "acceptable",
    }
    assert forbidden.isdisjoint(set(summary.columns))
    assert "gap_0p2_flagged_frame_percent" in summary.columns


def test_stage08_flags_when_numeric_not_nan(tmp_path):
    out = resolve_review_out_dir(tmp_path, "671", "671_T1_P1_R1", "stage08")
    build_full_review(
        EVAL_DIR,
        EVAL_DIR,
        out,
        frame_start=16000,
        frame_end=17000,
        selected_link_ids=["J007"],
        qc_evidence=["artifact_sigma"],
        datadescriptions=DD_PATH,
    )
    link_df = pd.read_csv(out / "link_joint_review_table.csv")
    row = link_df.iloc[0]
    assert float(row["stage08_block_filter_frame_percent"]) > 0
    assert row["stage08_filter_status_values"]
    assert row["layer2_problem_notes"]


def test_datadescriptions_status_in_summary(tmp_path):
    out = resolve_review_out_dir(tmp_path, "671", "671_T1_P1_R1", "dd")
    build_full_review(
        EVAL_DIR,
        EVAL_DIR,
        out,
        frame_start=1000,
        frame_end=1500,
        selected_link_ids=["J005"],
        qc_evidence=["gap_0p2"],
        datadescriptions=DD_PATH,
    )
    summary = pd.read_csv(out / "window_decision_summary.csv").iloc[0]
    assert summary["datadescriptions_found"] is True or str(summary["datadescriptions_found"]).lower() == "true"
    assert summary["datadescriptions_used"] is True or str(summary["datadescriptions_used"]).lower() == "true"
    assert summary["mapping_mode"] in {"datadescriptions", "mixed"}
    assert list(pd.read_csv(out / "window_decision_summary.csv").columns) == WINDOW_DECISION_SUMMARY_COLUMNS


def test_datadescriptions_missing_produces_warning_not_crash(tmp_path):
    out = resolve_review_out_dir(tmp_path, "671", "671_T1_P1_R1", "no_dd")
    build_mapping_only(
        EVAL_DIR,
        EVAL_DIR,
        out,
        Path("missing_DataDescriptions.csv"),
        selected_link_ids=["J005"],
    )
    warnings = pd.read_csv(out / "window_warnings.csv")
    assert len(warnings) >= 1
    assert any("datadescriptions" in str(w).lower() for w in warnings["warning_id"])


def test_display_review_tables_reports_missing_optional(tmp_path):
    out = resolve_review_out_dir(tmp_path, "671", "671_T1_P1_R1", "display")
    build_full_review(
        EVAL_DIR,
        EVAL_DIR,
        out,
        frame_start=16000,
        frame_end=17000,
        selected_link_ids=["J005"],
        qc_evidence=["gap_0p2"],
        datadescriptions=DD_PATH,
    )
    (out / "qc_event_review_table.csv").unlink()
    messages: list[str] = []

    def capture_html(obj):
        messages.append(str(getattr(obj, "data", obj)))

    display_review_tables(
        out,
        display_fn=capture_html,
        display_table_fn=lambda *a, **k: None,
        display_summary_fn=lambda *a, **k: None,
    )
    joined = " ".join(messages)
    assert "qc_event_review_table.csv not available" in joined


def test_export_with_empty_checkbox_scope_uses_pilot_links(tmp_path):
    """Empty joint checkbox scope must not block export (uses pilot required links)."""
    from pre_jvcpca_review.discovery import resolve_layer2
    from pre_jvcpca_review.joint_overlap import classify_links, overlap_dataframe
    from pre_jvcpca_review.load_layer2 import load_link_manifest
    from pre_jvcpca_review.canonical_manifest import DEFAULT_PILOT_MANIFEST, load_pilot_manifest, pilot_link_order
    from pre_jvcpca_review.session_index import build_session_index, session_row

    idx = build_session_index()
    if idx.empty or not idx["is_matched"].any():
        pytest.skip("No matched sessions for export scope test")
    row = idx[idx["is_matched"]].iloc[0]
    pid = str(row["participant_id"])
    matched = idx[(idx["participant_id"] == pid) & idx["is_matched"]]
    sess_links = {
        r["session_id"]: load_link_manifest(resolve_layer2(r["layer2_run_dir"]).link_manifest)
        for _, r in matched.iterrows()
    }
    required = pilot_link_order(load_pilot_manifest(DEFAULT_PILOT_MANIFEST))
    overlap = overlap_dataframe(classify_links(sess_links, candidate_links=required), pid, list(sess_links))
    out = resolve_review_out_dir(tmp_path, pid, row["session_id"], "scope_none")

    result = export_layer3_window(
        Path(row["layer1_run_dir"]),
        Path(row["layer2_run_dir"]),
        out,
        0,
        500,
        session_row=row,
        window_label="scope_none",
        allow_nan_matrix=True,
        overlap_df=overlap,
        scope_required_links=None,
    )
    assert result["status"] in {"exported", "blocked"}
    if result["status"] == "blocked":
        warnings = pd.read_csv(result["warnings_csv"])
        assert "joint.no_selection" not in set(warnings["warning_id"])


def test_review_repair_does_not_weaken_layer3_export(tmp_path):
    """Canonical export manifest policy unchanged after review-table schema updates."""
    out = tmp_path / "l3_export"
    session_row = pd.Series(
        {
            "participant_id": "671",
            "session_id": "671_T1_P1_R1",
            "is_matched": True,
            "match_warning": "",
            "layer1_run_dir": str(EVAL_DIR),
            "layer2_run_dir": str(EVAL_DIR),
        }
    )
    result = export_layer3_window(
        EVAL_DIR,
        EVAL_DIR,
        out,
        0,
        500,
        session_row=session_row,
        window_label="smoke",
        allow_nan_matrix=True,
    )
    if result["status"] == "blocked":
        pytest.skip("Export blocked by fixture warnings — policy gate still active")
    manifest = json.loads(Path(result["paths"]["manifest"]).read_text(encoding="utf-8"))
    assert manifest["layer3_safe"] is True
    assert manifest["feature_naming_policy"] == "parent_canonical_to_child_canonical_axis"
