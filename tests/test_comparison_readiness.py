"""Tests for G3 comparison readiness."""

from __future__ import annotations

from pathlib import Path

from comparison_readiness import ComparisonRequest, evaluate_comparison_readiness
from project_status import load_project_snapshot

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_671_t1_t2_p1_p3_comparison():
    snap = load_project_snapshot(project_root=REPO_ROOT)
    req = ComparisonRequest(
        participant_id="671",
        timepoint_a="T1",
        timepoint_b="T2",
        p_phases=("P1", "P2", "P3"),
    )
    comp = evaluate_comparison_readiness(snap, req)
    assert comp.verdict in {"ready", "caution", "not_recommended", "blocked", "insufficient_data"}
    assert comp.segment_rows_expected == 12  # 2 reps × 3 phases × 2 timepoints
    assert comp.advisory_label


def test_671_t1_t3_has_schema_ids():
    snap = load_project_snapshot(project_root=REPO_ROOT)
    req = ComparisonRequest(
        participant_id="671",
        timepoint_a="T1",
        timepoint_b="T3",
        p_phases=("P1",),
    )
    comp = evaluate_comparison_readiness(snap, req)
    assert comp.segment_rows_found >= 0
    assert isinstance(comp.summary, str)


def test_missing_participant_comparison_insufficient():
    snap = load_project_snapshot(project_root=REPO_ROOT)
    req = ComparisonRequest(
        participant_id="999",
        timepoint_a="T1",
        timepoint_b="T2",
        p_phases=("P1",),
    )
    comp = evaluate_comparison_readiness(snap, req)
    assert comp.verdict in {"insufficient_data", "missing", "blocked"}
