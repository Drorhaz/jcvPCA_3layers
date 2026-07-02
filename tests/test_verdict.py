"""Tests for explanation-first VerdictCard model."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def snapshot():
    from project_status import load_project_snapshot

    return load_project_snapshot(project_root=REPO_ROOT)


def test_verdict_from_readiness_has_five_parts(snapshot):
    from readiness import build_readiness_matrix
    from verdict import verdict_from_readiness_cell

    matrix = build_readiness_matrix(snapshot)
    assert matrix.cells
    card = verdict_from_readiness_cell(matrix.cells[0])
    assert card.headline
    assert card.explanation
    assert len(card.evidence) >= 1
    assert card.consequence
    assert card.action


def test_verdict_from_coverage_exported(snapshot):
    from segmentation_coverage import EXERCISE_SELECTION_ALL_IN_SHEET, build_segmentation_coverage_rows
    from analysis_request import AnalysisRequestInput, comparison_spec_from_preset
    from verdict import HEADLINE_READY, verdict_from_coverage_row

    inp = AnalysisRequestInput(
        participant_id=snapshot.participants[0],
        repetitions=("R1",),
        comparisons=[comparison_spec_from_preset("L2_T1_vs_T3", ("R1",))],
        exercise_selection_mode=EXERCISE_SELECTION_ALL_IN_SHEET,
    )
    rows, _ = build_segmentation_coverage_rows(snapshot, inp)
    exported = [r for r in rows if r.get("coverage_status") == "exported"]
    if not exported:
        pytest.skip("no exported segments in fixture")
    card = verdict_from_coverage_row(exported[0])
    assert card.headline in {HEADLINE_READY, "Usable with caution", "Blocked"}


def test_stage_gates_cover_eight_stages(snapshot):
    from stage_gates import build_stage_gate_summaries

    gates = build_stage_gate_summaries(snapshot)
    assert len(gates) == 8
    assert gates[0].stage == 0
    assert gates[5].title.startswith("QC Verification")


def test_verification_gate_unlock():
    from verification_gate import VerificationState, sign_off, stage6_unlocked

    state = VerificationState()
    assert not stage6_unlocked(state)
    state.verified_segment_ids.add("671_T1_P1_R1::ex01")
    sign_off(state, notes="test")
    assert stage6_unlocked(state)
