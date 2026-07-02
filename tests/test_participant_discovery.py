"""Tests for dynamic participant discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from participant_discovery import (
    discover_participants,
    discovery_table_rows,
    participants_from_session_rows,
    scan_raw_layer2_participants,
    scan_segmentation_workbooks,
)
from project_paths import load_project_paths
from project_status import load_project_snapshot


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_scan_raw_layer2_finds_671_and_252(repo_root: Path):
    paths = load_project_paths(project_root=repo_root)
    found = scan_raw_layer2_participants(paths.data_raw_layer2)
    assert "671" in found
    assert "252" in found


def test_discover_participants_merges_sources(repo_root: Path):
    paths = load_project_paths(project_root=repo_root)
    discovery = discover_participants(paths)
    assert "671" in discovery.participant_ids
    assert "252" in discovery.participant_ids
    assert discovery.default_participant in discovery.participant_ids
    assert discovery.by_source.get("raw_layer2")


def test_snapshot_participants_use_discovery(repo_root: Path):
    snapshot = load_project_snapshot(project_root=repo_root)
    assert snapshot.participant_discovery is not None
    assert snapshot.participants == list(snapshot.participant_discovery.participant_ids)
    assert snapshot.default_participant


def test_participants_from_session_rows():
    rows = [
        {"participant_id": "399", "session_id": "399_T1_P1_R1"},
        {"participant_id": "", "session_id": "400_T2_P2_R1"},
    ]
    found = participants_from_session_rows(rows)
    assert found == {"399", "400"}


def test_discovery_table_rows(repo_root: Path):
    paths = load_project_paths(project_root=repo_root)
    discovery = discover_participants(paths)
    rows = discovery_table_rows(discovery)
    assert rows
    assert all("participant_id" in row for row in rows)


def test_scan_segmentation_workbooks_on_repo(repo_root: Path):
    paths = load_project_paths(project_root=repo_root)
    seg_dir = paths.get("layer2_5.segmentation_xlsx")
    found = scan_segmentation_workbooks(seg_dir)
    # Repo may or may not have xlsx checked in; at least function runs.
    assert isinstance(found, set)
