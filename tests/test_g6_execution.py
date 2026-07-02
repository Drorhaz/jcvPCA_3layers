"""Tests for G6 guarded execution helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from analysis_config import ConfigValidationError, load_analysis_config
from g6_execution import (
    append_change_audit_log,
    assert_non_canonical_batch_path,
    build_layer3_argv,
    change_audit_log_path,
    execute_layer3_batch,
    prepare_plan_for_g6_execution,
    verification_snapshot_path,
)
from project_status import load_project_snapshot
from verification_gate import (
    VerificationState,
    load_verification_snapshot,
    save_verification_snapshot,
    sign_off,
    stage6_unlocked,
    verification_state_from_dict,
    verification_state_to_dict,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def snapshot(repo_root: Path):
    return load_project_snapshot(project_root=repo_root)


def test_assert_non_canonical_blocks_canonical_path(snapshot, tmp_path: Path):
    canonical = snapshot.canonical_batch_path
    if canonical is None:
        pytest.skip("No canonical batch configured")
    with pytest.raises(Exception, match="canonical"):
        assert_non_canonical_batch_path(canonical, snapshot)


def test_assert_non_canonical_blocks_canonical_id(snapshot, tmp_path: Path):
    if not snapshot.canonical_batch_id:
        pytest.skip("No canonical batch id")
    bad = tmp_path / snapshot.canonical_batch_id
    with pytest.raises(Exception, match="canonical"):
        assert_non_canonical_batch_path(bad, snapshot)


def test_append_change_audit_log(repo_root: Path, tmp_path: Path):
    log_path = change_audit_log_path(tmp_path)
    append_change_audit_log(tmp_path, {"action": "test", "key": "demo"})
    assert log_path.is_file()
    line = log_path.read_text(encoding="utf-8").strip()
    record = json.loads(line)
    assert record["action"] == "test"
    assert record["key"] == "demo"
    assert "timestamp" in record


def test_prepare_plan_for_g6_execution():
    blocked = {
        "preflight": {"blockers": [{"code": "x"}]},
        "execution": {"allowed": False},
    }
    ready = {"preflight": {"blockers": []}, "execution": {"allowed": False}}
    assert prepare_plan_for_g6_execution(blocked)["execution"]["allowed"] is False
    assert prepare_plan_for_g6_execution(ready)["execution"]["allowed"] is True


def test_build_layer3_argv(repo_root: Path, snapshot):
    runner_plan = {
        "proposed_batch_root": str(tmp_safe_batch(snapshot)),
        "layer25_root": str(repo_root / "processed" / "pre_jvcpca_review"),
        "participant_ids": ["671"],
    }
    argv = build_layer3_argv(repo_root, runner_plan)
    assert "run_layer3_batch.py" in argv[0]
    assert "--output-dir" in argv
    assert "--participant" in argv
    assert "671" in argv


def tmp_safe_batch(snapshot):
    root = snapshot.paths.get("layer3.outputs_root")
    return root / "gaga_batch_jcvpca_test_g6_only"


def test_execute_layer3_batch_dry_run(repo_root: Path, snapshot):
    batch_root = tmp_safe_batch(snapshot)
    runner_plan = {
        "proposed_batch_root": str(batch_root),
        "layer25_root": str(repo_root / "processed" / "pre_jvcpca_review"),
        "participant_ids": ["671"],
    }
    result = execute_layer3_batch(
        repo_root,
        snapshot,
        runner_plan,
        batch_root=batch_root,
        dry_run=True,
    )
    assert result["returncode"] == 0
    assert "run_layer3_batch.py" in result["argv"][0]


def test_verification_snapshot_roundtrip(repo_root: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "g6_execution.verification_snapshot_path",
        lambda root: tmp_path / "verification_snapshot.yaml",
    )
    state = VerificationState()
    state.verified_segment_ids.add("671_T1_P1_R1::ex01")
    sign_off(state, notes="pytest", science_hash="abc")
    path = save_verification_snapshot(repo_root, state)
    assert path.is_file()
    loaded = load_verification_snapshot(repo_root)
    assert loaded is not None
    assert loaded.signed_off
    assert "671_T1_P1_R1::ex01" in loaded.verified_segment_ids
    assert stage6_unlocked(None, disk_state=loaded)


def test_verification_state_dict_roundtrip():
    state = VerificationState()
    state.verified_segment_ids.add("a::ex01")
    state.signed_off = True
    state.notes = "n"
    data = verification_state_to_dict(state)
    restored = verification_state_from_dict(data)
    assert restored.signed_off
    assert restored.notes == "n"
    assert "a::ex01" in restored.verified_segment_ids


def test_apply_threshold_update_gui_setting(tmp_path: Path, repo_root: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    for fname in ("analysis_params.yaml", "qc_rules.yaml", "segment_selection.yaml"):
        (cfg_dir / fname).write_text("version: 1\n", encoding="utf-8")
    (cfg_dir / "gui_settings.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "results_effect_display_floor": {
                    "value": 0.0,
                    "default": 0.0,
                    "allowed_range": [0.0, 1.0],
                    "gui_editable": True,
                    "locked_by_scope": False,
                    "requires_approval": False,
                    "invalidates": [],
                },
            }
        ),
        encoding="utf-8",
    )
    cfg = load_analysis_config(config_dir=cfg_dir, project_root=tmp_path)
    updated, audit = cfg.apply_threshold_update(
        "results_effect_display_floor",
        0.05,
        reason="pytest",
    )
    assert updated.value == 0.05
    assert audit["old_value"] == 0.0
    assert audit["new_value"] == 0.05
    log_path = change_audit_log_path(tmp_path)
    assert log_path.is_file()


def test_apply_threshold_update_rejects_non_editable(tmp_path: Path, repo_root: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "analysis_params.yaml").write_text(
        "version: 1\npca:\n  centering:\n    value: true\n    gui_editable: false\n    locked_by_scope: true\n",
        encoding="utf-8",
    )
    for other in ("qc_rules.yaml", "segment_selection.yaml", "gui_settings.yaml"):
        (cfg_dir / other).write_text("version: 1\n", encoding="utf-8")
    cfg = load_analysis_config(config_dir=cfg_dir, project_root=repo_root)
    with pytest.raises(ConfigValidationError, match="not gui_editable"):
        cfg.apply_threshold_update("pca.centering", False, reason="nope")
