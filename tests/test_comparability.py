"""Tests for G2 comparability helpers."""

from __future__ import annotations

from pathlib import Path

from comparability import ComparabilityStatus, comparability_status, load_artifact_science_hash
from project_status import load_project_snapshot


def test_canonical_batch_pre_registry():
    snap = load_project_snapshot(
        project_root=Path(__file__).resolve().parents[1]
    )
    assert snap.canonical_comparability == ComparabilityStatus.PRE_REGISTRY_CANONICAL


def test_comparable_when_hashes_match():
    h = "abc123"
    assert comparability_status(h, h) == ComparabilityStatus.COMPARABLE


def test_not_comparable_when_hashes_differ():
    assert (
        comparability_status("aaa", "bbb")
        == ComparabilityStatus.NOT_DIRECTLY_COMPARABLE
    )


def test_unknown_without_snapshot():
    assert comparability_status(None, "current") == ComparabilityStatus.UNKNOWN


def test_load_artifact_science_hash_missing(tmp_path):
    assert load_artifact_science_hash(tmp_path) is None
