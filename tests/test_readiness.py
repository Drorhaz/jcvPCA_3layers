"""Tests for G2 readiness matrix derivation."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def matrix():
    from project_status import load_project_snapshot
    from readiness import build_readiness_matrix

    snap = load_project_snapshot(project_root=REPO_ROOT)
    return build_readiness_matrix(snap)


def test_matrix_has_p_phase_rows(matrix):
    assert len(matrix.cells) >= 60  # 12 sessions × 5 P phases minimum
    phases = {c.p_phase for c in matrix.cells}
    assert phases == {"P1", "P2", "P3", "P4", "P5"}


def test_threshold_legend_populated(matrix):
    assert len(matrix.threshold_legend) >= 10
    keys = {row["registry_key"] for row in matrix.threshold_legend}
    assert "layer2.rotvec_jump_fail_rad" in keys
    assert "layer1.max_missing_percent_caution" in keys


def test_671_t1_r2_l2_pass(matrix):
    cells = [
        c
        for c in matrix.cells
        if c.participant_id == "671"
        and c.timepoint == "T1"
        and c.repetition == "R2"
        and c.p_phase == "P1"
    ]
    assert len(cells) == 1
    assert cells[0].l2.status == "pass"


def test_671_t1_r1_l2_fail(matrix):
    cells = [
        c
        for c in matrix.cells
        if c.participant_id == "671"
        and c.timepoint == "T1"
        and c.repetition == "R1"
    ]
    assert cells
    assert all(c.l2.status == "fail" for c in cells)


def test_l1_missing_for_cohort(matrix):
    cells = [c for c in matrix.cells if c.l1.status == "missing"]
    assert len(cells) > 0
    assert "layer1.min_marker_coverage_pct" in cells[0].l1.threshold_keys


def test_overall_not_missing_when_l25_export_and_l1_missing(matrix):
    cells = [
        c
        for c in matrix.cells
        if c.l1.status == "missing" and c.l2_5.status in {"pass", "warn", "strong_warning"}
    ]
    assert cells, "expected L2.5 export rows with missing L1 index"
    for cell in cells:
        assert cell.overall != "missing", (
            f"{cell.session_id} {cell.p_phase}: overall should reflect L2/L2.5, not L1 gap"
        )


def test_readiness_rows_export(matrix):
    from readiness import readiness_matrix_as_rows

    rows = readiness_matrix_as_rows(matrix)
    assert rows[0]["L1"] in {"pass", "warn", "missing", "unknown", "fail", "block"}
