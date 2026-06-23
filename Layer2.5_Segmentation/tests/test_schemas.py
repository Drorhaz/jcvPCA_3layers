"""Tests for schema constants."""

from layer2_motive.segmentation import schemas


def test_recommendation_classes_import():
    assert "candidate_include" in schemas.RECOMMENDATION_CLASSES
    assert len(schemas.RECOMMENDATION_CLASSES) == 6


def test_layer2_parquet_required_columns_non_empty():
    assert "frame" in schemas.LAYER2_PARQUET_REQUIRED_COLUMNS
    assert "link_id" in schemas.LAYER2_PARQUET_REQUIRED_COLUMNS
    assert "stage08_analysis_eligible" in schemas.LAYER2_PARQUET_REQUIRED_COLUMNS


def test_canonical_join_key():
    assert schemas.CANONICAL_JOIN_KEY == "frame"
