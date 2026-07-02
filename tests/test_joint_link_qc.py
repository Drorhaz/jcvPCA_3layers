"""Tests for G3 joint/link QC recommendations."""

from __future__ import annotations

from pathlib import Path

from joint_link_qc import LINK_CAUTION, LINK_NOT_RECOMMENDED, build_joint_link_qc_report
from project_status import load_project_snapshot

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_joint_link_report_for_252_p1():
    snap = load_project_snapshot(project_root=REPO_ROOT)
    report = build_joint_link_qc_report(
        snap,
        participant_ids=["252"],
        p_phases=["P1"],
        repetitions=["R1"],
        timepoints=["T1"],
        max_exports=1,
    )
    assert report.link_recommendations
    assert report.body_region_summaries
    assert report.advisory_label


def test_671_t1_r1_has_not_recommended_links():
    snap = load_project_snapshot(project_root=REPO_ROOT)
    report = build_joint_link_qc_report(
        snap,
        participant_ids=["671"],
        timepoints=["T1"],
        repetitions=["R1"],
        p_phases=["P1"],
        max_exports=1,
    )
    verdicts = {r.verdict for r in report.link_recommendations}
    assert LINK_NOT_RECOMMENDED in verdicts or LINK_CAUTION in verdicts


def test_link_evidence_cites_registry_or_source():
    snap = load_project_snapshot(project_root=REPO_ROOT)
    report = build_joint_link_qc_report(
        snap,
        participant_ids=["252"],
        max_exports=1,
    )
    rec = report.link_recommendations[0]
    assert rec.evidence
    assert rec.jcvpca_note
