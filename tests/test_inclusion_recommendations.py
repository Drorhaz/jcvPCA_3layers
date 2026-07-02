"""Tests for G3 inclusion recommendations."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def inclusion_report():
    from inclusion_recommendations import build_inclusion_report
    from project_status import load_project_snapshot

    snap = load_project_snapshot(project_root=REPO_ROOT)
    return build_inclusion_report(snap)


def test_inclusion_report_has_cells(inclusion_report):
    assert len(inclusion_report.recommendations) >= 60
    assert inclusion_report.advisory_label


def test_671_t1_r2_can_be_ready_or_caution(inclusion_report):
    matches = [
        r
        for r in inclusion_report.recommendations
        if r.participant_id == "671"
        and r.timepoint == "T1"
        and r.repetition == "R2"
        and r.p_phase == "P1"
    ]
    assert len(matches) == 1
    assert matches[0].verdict in {"ready", "caution", "not_recommended", "blocked", "missing"}


def test_filter_by_participant(inclusion_report):
    from inclusion_recommendations import filter_inclusion_report

    filtered = filter_inclusion_report(inclusion_report, participant_ids=["671"])
    assert filtered
    assert all(r.participant_id == "671" for r in filtered)


def test_evidence_present(inclusion_report):
    rec = inclusion_report.recommendations[0]
    assert rec.evidence
    assert rec.summary
