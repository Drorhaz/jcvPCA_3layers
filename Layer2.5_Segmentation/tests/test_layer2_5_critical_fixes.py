"""Tests for the critical Layer 2.5 audit fixes (R1-R5).

Covers: default roots, participant/session discovery, Layer 1/Layer 2 pairing
gate, canonical-only Layer 3 export naming, legacy layer3_safe=false, joint
overlap/comparability, and structured warnings that block unsafe export.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from pre_jvcpca_review import session_index as si
from pre_jvcpca_review.export_window import (
    export_layer3_window,
    export_pilot_window_for_jvcpca,
    export_window_for_jvcpca,
)
from pre_jvcpca_review.joint_overlap import (
    DIRECT,
    classify_links,
    non_comparable_required_features,
    overlap_dataframe,
)
from pre_jvcpca_review.load_layer2 import LinkRecord, load_link_manifest
from pre_jvcpca_review.pairing import run_pairing_gate
from pre_jvcpca_review.warnings import SEVERITY_BLOCKING, WarningCollector

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_L1 = ROOT / "input" / "Layer1_QC" / "QC_671_T1_P1_R1"
FIXTURE_L2 = ROOT / "input" / "Layer2_Kinematics" / "671_T1_P1_R1"


# --------------------------------------------------------------------------
# Mocked output-root builders
# --------------------------------------------------------------------------
def _make_l1_run(root: Path, key: str, ts: str, n_frames: int = 100) -> Path:
    run = root / "runs" / f"{key}_{ts}"
    (run / "tables").mkdir(parents=True, exist_ok=True)
    subject, t, p, r = key.split("_")
    (run / "layer1_segmentation_notebook_manifest.json").write_text(
        json.dumps(
            {
                "subject_id": subject,
                "session_id": f"{t}_{p}_{r}",
                "run_key": key,
                "input_csv": f"data/{subject}/{key}_Take.csv",
                "frame_rate_hz": 120.0,
                "n_frames": n_frames,
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame({"frame": range(n_frames), "flag_gap_0p2": False}).to_csv(
        run / "tables" / "qc_mask.csv", index=False
    )
    pd.DataFrame([{"marker_set_id_or_hash": "abc123"}]).to_csv(
        run / "tables" / "layer1_marker_set.csv", index=False
    )
    return run


def _make_l2_session(root: Path, key: str, take: str, n_frames: int = 100) -> Path:
    sess = root / f"{key}_Take_{take}"
    (sess / "07_rotation_vectors").mkdir(parents=True, exist_ok=True)
    (sess / "08_filtered_rotvecs").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"frame": range(n_frames)}).to_parquet(
        sess / "08_filtered_rotvecs" / "filtered_relative_rotation_vectors.parquet"
    )
    pd.DataFrame(
        [{"session_id": key, "run_label": f"{key}_Take_{take}",
          "frame_count": n_frames, "sampling_rate_hz": 120.0}]
    ).to_csv(sess / "07_rotation_vectors" / "qc_session_manifest.csv", index=False)
    pd.DataFrame(
        [{"link_id": "J004", "parent_canonical": "Neck", "child_canonical": "Head",
          "feature_scope": "core_candidate", "stage07_jump_status": "pass"}]
    ).to_csv(sess / "07_rotation_vectors" / "qc_link_manifest.csv", index=False)
    return sess


# --------------------------------------------------------------------------
# 1. Default roots
# --------------------------------------------------------------------------
def test_default_roots_point_to_layer1_and_layer2_outputs():
    assert si.DEFAULT_LAYER1_ROOT.as_posix().endswith(
        "Layer1_motive_qc/motive_qc/outputs"
    )
    assert si.DEFAULT_LAYER2_ROOT.as_posix().endswith(
        "Layer2_Motive_Kinematics/outputs"
    )


# --------------------------------------------------------------------------
# 2 & 3. Discovery: participants and multiple sessions
# --------------------------------------------------------------------------
def test_discovery_finds_participants_and_multiple_sessions(tmp_path):
    l1_root = tmp_path / "l1"
    l2_root = tmp_path / "l2"
    _make_l1_run(l1_root, "671_T1_P1_R1", "20260101_000001")
    _make_l1_run(l1_root, "671_T1_P1_R2", "20260101_000002")
    _make_l1_run(l1_root, "671_T2_P1_R1", "20260101_000003")
    _make_l2_session(l2_root, "671_T1_P1_R1", "a")
    _make_l2_session(l2_root, "671_T1_P1_R2", "b")
    _make_l2_session(l2_root, "671_T2_P1_R1", "c")

    idx = si.build_session_index(l1_root, l2_root)
    assert si.participants(idx) == ["671"]
    sessions = si.sessions_for(idx, "671")["session_id"].tolist()
    assert {"671_T1_P1_R1", "671_T1_P1_R2", "671_T2_P1_R1"} <= set(sessions)
    assert len(sessions) >= 3
    # All three are matched (L1 + L2 present, equal frames).
    assert idx["is_matched"].all()


def test_discovery_flags_unmatched_when_layer2_missing(tmp_path):
    l1_root = tmp_path / "l1"
    l2_root = tmp_path / "l2"
    _make_l1_run(l1_root, "671_T1_P1_R1", "20260101_000001")
    idx = si.build_session_index(l1_root, l2_root)
    row = si.session_row(idx, "671_T1_P1_R1")
    assert not row["is_matched"]
    assert "missing_layer2_output" in row["match_warning"]


# --------------------------------------------------------------------------
# 4, 5, 6. Pairing gate warnings
# --------------------------------------------------------------------------
def _base_row(**over) -> pd.Series:
    base = {
        "participant_id": "671", "session_id": "671_T1_P1_R1",
        "timepoint": "T1", "part_id": "P1", "repetition_id": "R1",
        "layer1_run_dir": "/x/671_T1_P1_R1_ts",
        "layer2_run_dir": "/y/671_T1_P1_R1_Take",
        "layer1_source_file": "671_T1_P1_R1_Take.csv",
        "layer2_source_file": "671_T1_P1_R1_Take",
        "layer2_provenance_path": "/y/qc_session_manifest.csv",
        "n_frames_layer1": 100, "n_frames_layer2": 100,
        "marker_set_id": "abc", "layer2_git_commit": "deadbeef",
    }
    base.update(over)
    return pd.Series(base)


def test_pairing_source_mismatch_blocks():
    coll = WarningCollector()
    row = _base_row(
        layer1_run_dir="/x/671_T1_P1_R1_ts",
        layer2_run_dir="/y/671_T2_P1_R1_Take",
        layer2_source_file="671_T2_P1_R1_Take",
    )
    ok = run_pairing_gate(row, coll)
    assert not ok and coll.has_blocking
    ids = {r.warning_id for r in coll.records}
    assert {"pairing.identity_mismatch", "pairing.source_file_mismatch"} & ids


def test_pairing_frame_mismatch_blocks():
    coll = WarningCollector()
    row = _base_row(n_frames_layer1=100, n_frames_layer2=120)
    ok = run_pairing_gate(row, coll)
    assert not ok and coll.has_blocking
    assert any(r.warning_id == "pairing.frame_count_mismatch" for r in coll.records)


def test_pairing_missing_provenance_warns_non_blocking():
    coll = WarningCollector()
    row = _base_row(layer2_provenance_path="")
    ok = run_pairing_gate(row, coll)
    assert ok  # strong warning, not blocking
    rec = next(r for r in coll.records if r.warning_id == "pairing.missing_layer2_provenance")
    assert rec.severity != SEVERITY_BLOCKING and rec.requires_user_approval


# --------------------------------------------------------------------------
# 7 & 15. Canonical default export naming + warnings files
# --------------------------------------------------------------------------
@pytest.mark.skipif(not FIXTURE_L2.is_dir(), reason="fixtures unavailable")
def test_canonical_export_uses_canonical_names_not_j00x(tmp_path):
    res = export_layer3_window(
        FIXTURE_L1, FIXTURE_L2, tmp_path, 50, 99,
        session_row=_base_row(session_id="671_T1_P1_R1"),
        window_label="t",
    )
    assert res["status"] == "exported"
    matrix = pd.read_parquet(tmp_path / "window_jvcpca_matrix.parquet")
    feats = [c for c in matrix.columns if c not in ("session_id", "run_label", "frame", "time_sec")]
    assert feats[0] == "Neck_to_Head_rx"
    assert not any(c[:1] == "J" and c[1:4].isdigit() for c in feats)
    # warnings written to both csv and manifest
    assert (tmp_path / "window_warnings.csv").is_file()
    manifest = json.loads((tmp_path / "window_export_manifest.json").read_text())
    assert manifest["layer3_safe"] is True
    assert manifest["feature_naming_policy"] == "canonical_parent_child_axis"
    assert "warnings_summary" in manifest and "warnings" in manifest


# --------------------------------------------------------------------------
# 8. Legacy export marks layer3_safe=false
# --------------------------------------------------------------------------
@pytest.mark.skipif(not FIXTURE_L2.is_dir(), reason="fixtures unavailable")
def test_legacy_export_marks_layer3_unsafe(tmp_path):
    links = load_link_manifest(FIXTURE_L2 / "layer2_session_link_manifest.csv")
    one = links[0].link_id
    export_window_for_jvcpca(
        FIXTURE_L1, FIXTURE_L2, tmp_path, 50, 59, [one], allow_nan_matrix=True
    )
    manifest = json.loads((tmp_path / "window_export_manifest.json").read_text())
    assert manifest["layer3_safe"] is False
    assert "legacy" in manifest["feature_naming_policy"].lower() or manifest[
        "feature_naming_policy"
    ] == "link_id_parent_to_child_axis"
    assert "legacy_layer3_warning" in manifest


# --------------------------------------------------------------------------
# 9 & 10. Canonical export blocks missing feature / incomplete triplet
# --------------------------------------------------------------------------
def _write_manifest(path: Path, rows: list[dict]) -> Path:
    cols = [
        "feature_name", "canonical_link_name", "parent_canonical", "child_canonical",
        "axis", "source_layer2_column", "include_in_pilot", "feature_scope", "notes",
    ]
    pd.DataFrame(rows, columns=cols).to_csv(path, index=False)
    return path


@pytest.mark.skipif(not FIXTURE_L2.is_dir(), reason="fixtures unavailable")
def test_canonical_export_blocks_missing_required_feature(tmp_path):
    manifest = _write_manifest(
        tmp_path / "bad_manifest.csv",
        [
            {"feature_name": f"Zzz_to_Yyy_{ax}", "canonical_link_name": "Zzz->Yyy",
             "parent_canonical": "Zzz", "child_canonical": "Yyy", "axis": ax,
             "source_layer2_column": f"{ax}_filtered_analysis", "include_in_pilot": True,
             "feature_scope": "core_candidate", "notes": ""}
            for ax in ("rx", "ry", "rz")
        ],
    )
    res = export_layer3_window(
        FIXTURE_L1, FIXTURE_L2, tmp_path / "out", 50, 59,
        pilot_manifest_path=manifest, require_pairing=False,
    )
    assert res["blocked"] is True
    assert not (tmp_path / "out" / "window_jvcpca_matrix.parquet").is_file()


@pytest.mark.skipif(not FIXTURE_L2.is_dir(), reason="fixtures unavailable")
def test_canonical_export_blocks_incomplete_triplet(tmp_path):
    manifest = _write_manifest(
        tmp_path / "triplet.csv",
        [
            {"feature_name": f"Neck_to_Head_{ax}", "canonical_link_name": "Neck->Head",
             "parent_canonical": "Neck", "child_canonical": "Head", "axis": ax,
             "source_layer2_column": f"{ax}_filtered_analysis", "include_in_pilot": True,
             "feature_scope": "core_candidate", "notes": ""}
            for ax in ("rx", "ry")  # missing rz
        ],
    )
    res = export_layer3_window(
        FIXTURE_L1, FIXTURE_L2, tmp_path / "out", 50, 59,
        pilot_manifest_path=manifest, require_pairing=False,
    )
    assert res["blocked"] is True
    warned = pd.read_csv(tmp_path / "out" / "window_warnings.csv")
    assert "feature.incomplete_triplet" in set(warned["warning_id"])


# --------------------------------------------------------------------------
# 11, 12, 13. Joint overlap classification
# --------------------------------------------------------------------------
def _links(pairs: list[tuple[str, str]]) -> list[LinkRecord]:
    return [
        LinkRecord(f"J{i:03d}", p, c, "core_candidate", "pass", f"{p}->{c}")
        for i, (p, c) in enumerate(pairs)
    ]


def test_joint_overlap_direct_missing_and_composite():
    sess = {
        "T1": _links([("Neck", "Head"), ("Ab", "Chest"), ("Chest", "LShoulder")]),
        "T2": _links([("Neck", "Head"), ("Ab", "Chest"), ("Chest", "LShoulder")]),
        # T3: spine split (Ab->Spine2->Chest), no direct Ab->Chest; no LShoulder
        "T3": _links([("Neck", "Head"), ("Ab", "Spine2"), ("Spine2", "Chest")]),
    }
    rows = classify_links(sess)
    by_name = {r.canonical_link_name: r for r in rows}
    assert by_name["Neck->Head"].classification == DIRECT
    assert by_name["Chest->LShoulder"].classification == "missing_in_some_sessions"
    assert by_name["Ab->Chest"].classification == "requires_composite_mapping"
    # Ab->Chest is present in T1/T2 only
    assert set(by_name["Ab->Chest"].present_in_sessions) == {"T1", "T2"}


# --------------------------------------------------------------------------
# 14. Non-comparable required feature blocks Layer 3 export
# --------------------------------------------------------------------------
@pytest.mark.skipif(not FIXTURE_L2.is_dir(), reason="fixtures unavailable")
def test_scoped_comparability_does_not_block_unselected_bad_link(tmp_path):
    sess = {
        "671_T1_P1_R1": _links([("Neck", "Head"), ("Chest", "Neck")]),
        "671_T3_P1_R1": _links([("Neck", "Neck2"), ("Neck2", "Head"), ("Chest", "Neck")]),
    }
    overlap = overlap_dataframe(
        classify_links(sess, candidate_links=[("Neck", "Head"), ("Chest", "Neck")]),
        "671",
        list(sess),
    )

    blocked = export_layer3_window(
        FIXTURE_L1,
        FIXTURE_L2,
        tmp_path / "scoped_out",
        50,
        59,
        require_pairing=False,
        overlap_df=overlap,
        harmonization_manifest_exists=False,
        scope_required_links=[("Chest", "Neck")],
    )
    warnings = pd.read_csv(blocked["warnings_csv"])
    assert warnings[warnings["warning_id"] == "joint.not_directly_comparable"].empty
    assert warnings[warnings["warning_id"] == "joint.not_comparable_not_selected"].empty


@pytest.mark.skipif(not FIXTURE_L2.is_dir(), reason="fixtures unavailable")
def test_non_comparable_required_feature_blocks_export(tmp_path):
    # Build an overlap table flagging a required link as composite.
    sess = {
        "671_T1_P1_R1": _links([("Neck", "Head")]),
        "671_T3_P1_R1": _links([("Neck", "Neck2"), ("Neck2", "Head")]),
    }
    rows = classify_links(sess, candidate_links=[("Neck", "Head")])
    overlap = overlap_dataframe(rows, "671", list(sess))
    assert non_comparable_required_features(overlap, [("Neck", "Head")]) == ["Neck->Head"]

    res = export_layer3_window(
        FIXTURE_L1, FIXTURE_L2, tmp_path / "out", 50, 59,
        require_pairing=False, overlap_df=overlap,
        harmonization_manifest_exists=False,
    )
    assert res["blocked"] is True
    assert not (tmp_path / "out" / "window_jvcpca_matrix.parquet").is_file()


# --------------------------------------------------------------------------
# 16. Blocking warning prevents export (frame mismatch via session_row)
# --------------------------------------------------------------------------
@pytest.mark.skipif(not FIXTURE_L2.is_dir(), reason="fixtures unavailable")
def test_blocking_warning_prevents_export(tmp_path):
    row = _base_row(n_frames_layer1=100, n_frames_layer2=120)
    res = export_layer3_window(
        FIXTURE_L1, FIXTURE_L2, tmp_path / "out", 50, 59, session_row=row,
    )
    assert res["status"] == "blocked"
    assert not (tmp_path / "out" / "window_jvcpca_matrix.parquet").is_file()
    assert (tmp_path / "out" / "window_warnings.csv").is_file()
