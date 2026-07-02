"""Tests for session discovery / run planning helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from session_pipeline import (
    plan_layer1_commands,
    plan_layer2_commands,
    rebuild_session_index,
    resolve_raw_layer2_csv,
    session_id_to_l1_filter,
)


def test_session_id_to_l1_filter():
    assert session_id_to_l1_filter("252_T1_P1_R1") == "T1_P1_R1"


def test_rebuild_session_index_writes_processed(repo_root: Path):
    summary = rebuild_session_index(project_root=repo_root)
    assert summary.n_sessions >= 12
    assert summary.index_path.name == "session_index.csv"
    assert summary.index_path.parent.name == "processed"
    row671 = summary.session_index[summary.session_index["session_id"] == "671_T1_P1_R1"]
    assert len(row671) == 1
    assert str(row671.iloc[0]["layer1_run_dir"]).strip() != ""


def test_plan_layer1_groups_by_participant(repo_root: Path):
    rows = [
        {"session_id": "252_T1_P1_R1", "participant_id": "252"},
        {"session_id": "252_T1_P1_R2", "participant_id": "252"},
        {"session_id": "671_T1_P1_R1", "participant_id": "671"},
    ]
    planned = plan_layer1_commands(rows, repo_root=repo_root)
    assert len(planned) == 2
    argv_252 = next(p.argv for p in planned if p.session_ids[0].startswith("252"))
    assert "--subject" in argv_252
    assert "252" in argv_252
    assert "T1_P1_R1" in " ".join(argv_252)


def test_resolve_raw_layer2_csv(repo_root: Path):
    raw = repo_root / "data" / "raw_layer2"
    row = {
        "session_id": "252_T1_P1_R1",
        "participant_id": "252",
        "timepoint": "T1",
        "layer1_source_file": "252_T1_P1_R1_Take 2026-04-28 04.15.00 PM_000.csv",
    }
    path = resolve_raw_layer2_csv(row, raw)
    assert path is not None
    assert path.name.startswith("252_T1_P1_R1")


def test_plan_layer2_includes_run_and_export(repo_root: Path):
    raw = repo_root / "data" / "raw_layer2"
    row = {
        "session_id": "252_T1_P1_R1",
        "participant_id": "252",
        "timepoint": "T1",
        "layer1_source_file": "252_T1_P1_R1_Take 2026-04-28 04.15.00 PM_000.csv",
    }
    planned = plan_layer2_commands([row], repo_root=repo_root, raw_layer2_root=raw)
    assert len(planned) == 2
    assert all(p.argv for p in planned)
    assert "run-until" in " ".join(planned[0].argv)
    assert "export-layer2-sessions" in " ".join(planned[1].argv)


def test_plan_layer25_export(repo_root: Path):
    from project_paths import load_project_paths
    from session_pipeline import default_layer25_output_root, plan_layer25_commands

    paths = load_project_paths(project_root=repo_root)
    rows = [
        {"session_id": "252_T1_P1_R1", "participant_id": "252"},
        {"session_id": "252_T1_P1_R2", "participant_id": "252"},
        {"session_id": "671_T1_P1_R1", "participant_id": "671"},
    ]
    planned = plan_layer25_commands(
        rows,
        repo_root=repo_root,
        output_root=default_layer25_output_root(paths),
    )
    assert len(planned) == 1
    cmd = planned[0]
    assert cmd.layer == "layer2_5"
    assert "run_layer2_5_export.py" in cmd.argv[0]
    assert "--participant" in cmd.argv
    assert "252" in cmd.argv and "671" in cmd.argv


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]
