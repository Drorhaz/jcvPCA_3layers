"""Tests for input loading."""

import pytest

from layer2_motive.segmentation.load_inputs import (
    InputLoadError,
    load_layer1_qc_folder,
    load_layer2_export_folder,
)


def test_layer1_fixture_loads(fixture_layer1_dir):
    bundle = load_layer1_qc_folder(fixture_layer1_dir)
    assert bundle.manifest["run_key"] == "671_T1_P1_R1"
    assert "frame" in bundle.qc_mask.columns
    assert len(bundle.qc_mask) == 30604


def test_layer2_fixture_loads(fixture_layer2_dir):
    bundle = load_layer2_export_folder(fixture_layer2_dir)
    assert bundle.summary["session_id"] == "671_T1_P1_R1"
    assert "frame" in bundle.parquet_df.columns
    assert len(bundle.link_manifest) == 50


def test_layer1_missing_required_raises(tmp_path):
    with pytest.raises(InputLoadError, match="Required Layer 1 file missing"):
        load_layer1_qc_folder(tmp_path)
