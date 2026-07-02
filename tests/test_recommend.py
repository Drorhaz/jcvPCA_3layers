"""Tests for G2 read-only recommendations."""

from __future__ import annotations

from pathlib import Path

from project_status import load_project_snapshot
from recommend import all_recommendations, recommend_pre_checks


def test_pre_checks_ready_when_paths_ok():
    snap = load_project_snapshot(project_root=Path(__file__).resolve().parents[1])
    rec = recommend_pre_checks(snap)
    assert rec.verdict in {"ready", "review_required"}


def test_all_recommendations_returns_gates():
    snap = load_project_snapshot(project_root=Path(__file__).resolve().parents[1])
    recs = all_recommendations(snap)
    gates = {r.gate for r in recs}
    assert "pre_checks" in gates
    assert "data_readiness" in gates
    assert "inclusion_summary" in gates
    assert "joint_link_qc" in gates
