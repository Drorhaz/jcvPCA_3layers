"""Tests for pre-JcvPCA review backend."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pre_jvcpca_review.build import build_full_review, build_mapping_only
from pre_jvcpca_review.discovery import resolve_layer1, resolve_layer2
from pre_jvcpca_review.events import events_in_window, expand_gap_events, load_artifact_events
from pre_jvcpca_review.export_window import (
    MATRIX_IDENTITY_COLUMNS,
    WindowExportError,
    expected_feature_order,
    export_window_for_jvcpca,
    validate_feature_column_names,
)
from pre_jvcpca_review.layer2_flags import block_filter_mask, jump_fail_rad_mask
from pre_jvcpca_review.load_layer2 import load_link_manifest, load_rotvecs_window, resolve_selected_link_order
from pre_jvcpca_review.mapping import build_mapping_entry, is_labeled_marker, parse_datadescriptions
from pre_jvcpca_review.schemas import (
    LINK_JOINT_REVIEW_COLUMNS,
    MAPPING_LOGIC_COLUMNS,
    QC_EVENT_REVIEW_COLUMNS,
    QC_EVIDENCE_SUMMARY_COLUMNS,
    WINDOW_DECISION_SUMMARY_COLUMNS,
)

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "reevluate_project"
DD_PATH = EVAL_DIR / "671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001_DataDescriptions.csv"


@pytest.fixture(scope="module")
def eval_paths():
    if not EVAL_DIR.is_dir():
        pytest.skip("reevluate_project fixtures not available")
    return resolve_layer1(EVAL_DIR), resolve_layer2(EVAL_DIR)


def test_discovery_aliases(eval_paths):
    layer1, layer2 = eval_paths
    assert layer1.manifest.name == "layer1_segmentation_notebook_manifest.json"
    assert layer2.link_manifest.name == "layer2_qc_link_manifest.csv"
    assert layer2.rotvecs_parquet.name == "layer2_session_filtered_rotvecs.parquet"


def test_labeled_only_and_unmapped_retained():
    dd = parse_datadescriptions(DD_PATH)
    assert dd is not None
    assert is_labeled_marker("671:LWristOut", dd)
    assert not is_labeled_marker("Unlabeled 1340", dd)
    assert is_labeled_marker("ChestTop__WaistCBack", dd)


def test_candidate_link_mapping(eval_paths):
    _, layer2 = eval_paths
    links = load_link_manifest(layer2.link_manifest)
    dd = parse_datadescriptions(DD_PATH)
    entry = build_mapping_entry("671:LWristOut", "elbow_forearm", dd, links)
    assert entry.mapping_status == "mapped"
    assert "J005" in entry.candidate_layer2_link_ids
    assert "J007" in entry.candidate_layer2_link_ids

    regional = build_mapping_entry("ChestTop__WaistCBack", "torso_chest_back", dd, links)
    assert regional.candidate_mapping_level == "segment_pair_regional"
    assert "J002" in regional.candidate_layer2_link_ids or "J003" in regional.candidate_layer2_link_ids


def test_gap_expansion(eval_paths):
    layer1, _ = eval_paths
    assert layer1.gaps_over_0p2s is not None
    events = expand_gap_events(layer1.gaps_over_0p2s, "gap_0p2", 120.0)
    assert events
    assert all(ev.duration_frames >= 1 for ev in events)


def test_artifact_qc_types(eval_paths):
    layer1, _ = eval_paths
    assert layer1.artifact_events is not None
    events = load_artifact_events(layer1.artifact_events)
    assert any(ev.qc_type == "artifact_sigma" for ev in events)
    assert any(ev.qc_type == "segment_swap" for ev in events)


def test_window_filter(eval_paths):
    layer1, _ = eval_paths
    assert layer1.artifact_events is not None
    events = load_artifact_events(layer1.artifact_events)
    dd = parse_datadescriptions(DD_PATH)
    from pre_jvcpca_review.events import filter_labeled_events

    labeled = filter_labeled_events(events, dd)
    windowed = events_in_window(labeled, 16000, 17000, {"artifact_sigma", "segment_swap"})
    assert windowed
    assert all(16000 <= ev.frame_start <= 17000 for ev in windowed)
    assert all(ev.frame_end <= 17000 for ev in windowed)


def test_layer2_jump_fail_percent(eval_paths):
    _, layer2 = eval_paths
    links = {link.link_id: link for link in load_link_manifest(layer2.link_manifest)}
    df = load_rotvecs_window(layer2.rotvecs_parquet, ["J007"], 16000, 17000)
    mask = jump_fail_rad_mask(df, links["J007"])
    pct = round(100.0 * mask.sum() / 1001, 1)
    assert pct == 6.1


def test_joint_scoped_mapping_excludes_fingers(tmp_path, eval_paths):
    out = tmp_path / "scoped"
    build_mapping_only(
        EVAL_DIR, EVAL_DIR, out, DD_PATH, selected_link_ids=["J005", "J007", "J020"]
    )
    mapping = pd.read_csv(out / "mapping_logic_table.csv")
    names = set(mapping["normalized_marker_or_region"].str.lower())
    assert "lindex" not in names
    assert "rindex" not in names
    assert "lpinky" not in names
    assert any("lwrist" in n or "lfarm" in n or "lelbow" in n for n in names)


def test_output_schema_and_build(tmp_path, eval_paths):
    out = tmp_path / "review"
    mapping_path = build_mapping_only(EVAL_DIR, EVAL_DIR, out, DD_PATH)
    mapping = pd.read_csv(mapping_path)
    assert list(mapping.columns) == MAPPING_LOGIC_COLUMNS
    assert len(mapping) == 62  # 54 bone markers + 8 labeled segment pairs

    paths = build_full_review(
        layer1_dir=EVAL_DIR,
        layer2_dir=EVAL_DIR,
        out_dir=out,
        frame_start=16000,
        frame_end=17000,
        selected_link_ids=["J005", "J007", "J020"],
        qc_evidence=["gap_0p5", "gap_0p2", "artifact_sigma", "segment_swap"],
        datadescriptions=DD_PATH,
    )
    assert list(pd.read_csv(paths["window_decision_summary.csv"]).columns) == WINDOW_DECISION_SUMMARY_COLUMNS
    assert list(pd.read_csv(paths["qc_evidence_summary_table.csv"]).columns) == QC_EVIDENCE_SUMMARY_COLUMNS
    assert list(pd.read_csv(paths["link_joint_review_table.csv"]).columns) == LINK_JOINT_REVIEW_COLUMNS
    assert list(pd.read_csv(paths["qc_event_review_table.csv"]).columns) == QC_EVENT_REVIEW_COLUMNS
    summary = pd.read_csv(paths["window_decision_summary.csv"]).iloc[0]
    assert summary["layer1_total_labeled_markers"] < 62
    scoped_mapping = pd.read_csv(paths["mapping_logic_table.csv"])
    assert "LIndex" not in set(scoped_mapping["normalized_marker_or_region"])
    events = pd.read_csv(paths["qc_event_review_table.csv"])
    assert not events["raw_marker_or_region"].str.contains("RIndex|LIndex|LPinky", regex=True).any()


def test_window_export_for_jvcpca(tmp_path):
    out = tmp_path / "export"
    selected = ["J020", "J005", "J007"]
    frame_start, frame_end = 16000, 17000
    duration = frame_end - frame_start + 1

    with pytest.raises(WindowExportError, match="NaNs in JcvPCA matrix"):
        export_window_for_jvcpca(
            EVAL_DIR,
            EVAL_DIR,
            out / "fail_fast",
            frame_start,
            frame_end,
            selected,
            allow_nan_matrix=False,
        )
    assert not (out / "fail_fast" / "window_jvcpca_matrix.parquet").exists()

    paths = export_window_for_jvcpca(
        EVAL_DIR,
        EVAL_DIR,
        out,
        frame_start,
        frame_end,
        selected,
        allow_nan_matrix=True,
    )
    assert set(paths) == {"long_rotvec", "jvcpca_matrix", "flag_log", "manifest"}
    for key in paths:
        assert paths[key].is_file(), key

    import json

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    links = {link.link_id: link for link in load_link_manifest(EVAL_DIR / "layer2_qc_link_manifest.csv")}
    manifest_order, _ = resolve_selected_link_order(selected, list(links.values()))
    assert manifest["selected_link_order"] == manifest_order
    assert manifest["selected_link_order_source"] == "manifest_order"

    long_df = pd.read_parquet(paths["long_rotvec"])
    flag_log = pd.read_csv(paths["flag_log"])
    matrix_df = pd.read_parquet(paths["jvcpca_matrix"])

    assert len(long_df) == duration * 3
    assert len(flag_log) == duration * 3
    assert len(matrix_df) == duration

    feature_cols = [c for c in matrix_df.columns if c not in MATRIX_IDENTITY_COLUMNS]
    assert len(feature_cols) == 9
    assert feature_cols == manifest["feature_order"]
    assert manifest["feature_naming_policy"] == "link_id_parent_to_child_axis"

    assert "stage08_filter_status" not in long_df.columns
    assert "rx_raw" in long_df.columns
    assert "rx_raw" not in flag_log.columns
    assert "rx_filtered_analysis" not in flag_log.columns
    assert "l1_frame_flag_gap_0p2" in flag_log.columns
    assert "stage07_jump_status" in flag_log.columns

    assert long_df["frame"].min() >= frame_start
    assert long_df["frame"].max() <= frame_end
    assert set(long_df["link_id"].unique()) == set(manifest_order)
    assert set(flag_log["link_id"].unique()) == set(manifest_order)
    assert not long_df[["session_id", "frame", "link_id"]].isna().any().any()
    assert not matrix_df[["session_id", "frame"]].isna().any().any()

    link_rank = {lid: idx for idx, lid in enumerate(manifest_order)}
    long_pairs = list(zip(long_df["frame"], long_df["link_id"].map(link_rank)))
    assert long_pairs == sorted(long_pairs)
    flag_pairs = list(zip(flag_log["frame"], flag_log["link_id"].map(link_rank)))
    assert flag_pairs == sorted(flag_pairs)

    assert manifest["primary_rotvec_columns"] == [
        "rx_filtered_analysis",
        "ry_filtered_analysis",
        "rz_filtered_analysis",
    ]
    assert manifest["centering_scaling_status"] == "not_centered_not_scaled"
    assert manifest["pca_status"] == "not_fitted"
    assert manifest["jvcpca_status"] == "not_run"
    assert manifest["nan_policy"] == "allow_nan_matrix"
    assert manifest["long_rotvec_row_count"] == len(long_df)
    assert manifest["jvcpca_matrix_row_count"] == len(matrix_df)

    sample_frame = int(long_df["frame"].iloc[0])
    frame_flags = flag_log.loc[flag_log["frame"] == sample_frame, "l1_frame_status"]
    assert frame_flags.nunique() == 1

    rotvecs = load_rotvecs_window(
        EVAL_DIR / "layer2_session_filtered_rotvecs.parquet",
        ["J007"],
        frame_start,
        frame_end,
    )
    expected_jump = jump_fail_rad_mask(rotvecs, links["J007"])
    exported_jump = flag_log.loc[flag_log["link_id"] == "J007", "jump_fail_rad_frame"].reset_index(drop=True)
    assert exported_jump.equals(expected_jump.reset_index(drop=True))
    expected_block = block_filter_mask(rotvecs, links["J007"])
    exported_block = flag_log.loc[flag_log["link_id"] == "J007", "block_filter_frame"].reset_index(drop=True)
    assert exported_block.equals(expected_block.reset_index(drop=True))

    with pytest.raises(ValueError, match="Unknown link IDs"):
        export_window_for_jvcpca(
            EVAL_DIR,
            EVAL_DIR,
            tmp_path / "bad_link",
            frame_start,
            frame_end,
            ["J999"],
        )


def test_window_export_feature_naming_policy(tmp_path):
    links = load_link_manifest(EVAL_DIR / "layer2_qc_link_manifest.csv")
    links_by_id = {link.link_id: link for link in links}
    order = ["J005", "J007", "J020"]
    feature_order = expected_feature_order(links_by_id, order)

    clean_out = tmp_path / "clean"
    export_window_for_jvcpca(
        EVAL_DIR,
        EVAL_DIR,
        clean_out,
        0,
        1000,
        order,
    )
    matrix_df = pd.read_parquet(clean_out / "window_jvcpca_matrix.parquet")
    validate_feature_column_names(matrix_df, feature_order)

    bad = matrix_df.rename(columns={feature_order[0]: "bad_feature_name"})
    with pytest.raises(WindowExportError, match="Feature column names do not match"):
        validate_feature_column_names(bad, feature_order)

