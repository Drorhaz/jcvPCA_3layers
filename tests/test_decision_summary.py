"""Tests for batch decision summary reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from decision_summary import compare_batch_summaries, load_batch_decision_summary
from project_status import load_project_snapshot


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_canonical_batch_summary_loads(repo_root: Path):
    snapshot = load_project_snapshot(project_root=repo_root)
    if not snapshot.canonical_batch_exists or snapshot.canonical_batch_path is None:
        pytest.skip("Canonical batch not on disk")
    summary = load_batch_decision_summary(
        snapshot.canonical_batch_path,
        current_science_hash=snapshot.config.science_hash,
        is_canonical=True,
    )
    assert summary["is_canonical"] is True
    assert summary["comparison_status"]["total"] >= 0


def test_compare_batch_summaries_diff_keys():
    baseline = {
        "batch_id": "canonical",
        "config_hash": "abc",
        "comparison_status": {
            "completed": 1,
            "rows": [
                {
                    "participant_id": "671",
                    "block_id": "B",
                    "comparison_id": "L1_T1_vs_T2",
                    "status": "completed",
                    "n_pca_features": 42,
                    "n_analysis_links": 14,
                    "link_focus_mode": "full_body_comparable",
                }
            ],
        },
        "link_focus": [],
    }
    candidate = {
        "batch_id": "new_batch",
        "config_hash": "abc",
        "comparison_status": {
            "completed": 1,
            "rows": [
                {
                    "participant_id": "671",
                    "block_id": "B",
                    "comparison_id": "L1_T1_vs_T2",
                    "status": "completed",
                    "n_pca_features": 6,
                    "n_analysis_links": 2,
                    "link_focus_mode": "analysis_feature_filter",
                }
            ],
        },
        "link_focus": [{"link_focus_mode": "analysis_feature_filter"}],
    }
    diff = compare_batch_summaries(baseline, candidate)
    assert diff["config_hash_match"] is True
    assert diff["comparison_diff"][0]["candidate_n_pca_features"] == 6
    assert diff["comparison_diff"][0]["candidate_link_focus_mode"] == "analysis_feature_filter"

