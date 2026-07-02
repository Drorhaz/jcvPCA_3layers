"""Tests for G2 project snapshot loading."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def snapshot():
    from project_status import load_project_snapshot

    return load_project_snapshot(project_root=REPO_ROOT)


def test_load_project_snapshot(snapshot):
    assert snapshot.project_root == REPO_ROOT
    assert snapshot.config.science_hash
    assert len(snapshot.config.science_hash) == 64


def test_canonical_batch_metadata(snapshot):
    assert snapshot.canonical_batch_id == "gaga_batch_jcvpca_20260626_193319"
    assert snapshot.canonical_batch_exists


def test_session_index_loaded(snapshot):
    assert len(snapshot.session_index_rows) >= 12


def test_l2_qc_includes_671_and_252(snapshot):
    assert any(s.startswith("671_") for s in snapshot.l2_qc_by_session)
    assert any(s.startswith("252_") for s in snapshot.l2_qc_by_session)


def test_l25_manifest_loaded(snapshot):
    assert len(snapshot.l25_manifest_rows) > 0


def test_pipeline_layer_status(snapshot):
    from project_status import pipeline_layer_status

    rows = pipeline_layer_status(snapshot)
    assert len(rows) == 4
    layers = {r.layer for r in rows}
    assert "Layer 3 — JcvPCA" in layers


def test_participant_coverage(snapshot):
    from project_status import participant_coverage_table

    cov = participant_coverage_table(snapshot)
    assert any(r["participant_id"] == "671" for r in cov)
    assert any(r["p_phase_complete"] for r in cov)


def test_registry_coverage_labels(snapshot):
    assert snapshot.registry_coverage["layer3"]["mirrored"] == "full"
    assert snapshot.registry_coverage["layer1"]["mirrored"] == "curated"
