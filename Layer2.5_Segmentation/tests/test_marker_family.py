"""Tests for marker-family mapping and optional DataDescriptions enrichment."""

from pathlib import Path

import pytest

from layer2_motive.segmentation.marker_family import (
    MarkerFamilyMapper,
    build_mapper_from_datadescriptions,
    canonicalize_bone_name,
    infer_side,
    load_session_datadescriptions_marker_map,
    normalize_marker_name,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
T1_DATADESC = (
    REPO_ROOT
    / "data_description"
    / "671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001_DataDescriptions.csv"
)


def test_normalize_marker_name_three_forms():
    assert normalize_marker_name("671:LHandIn") == "LHandIn"
    assert normalize_marker_name("671_LHandIn") == "LHandIn"
    assert normalize_marker_name("LHandIn") == "LHandIn"
    assert normalize_marker_name("671:LWristOut") == "LWristOut"


def test_infer_side():
    assert infer_side("LHandIn") == "left"
    assert infer_side("RWristOut") == "right"
    assert infer_side("ChestTop") is None


def test_heuristic_lwristout_family_and_adjacency():
    mapper = MarkerFamilyMapper()
    result = mapper.map_marker_to_family("LWristOut")
    assert result.joint_family == "left_elbow_forearm"
    assert result.adjacent_joint_family == "left_wrist_hand"
    assert result.mapping_source == "marker_name_heuristic"
    assert result.attached_bone == "LFArm"


def test_heuristic_waist_template_uncertain():
    mapper = MarkerFamilyMapper()
    result = mapper.map_marker_to_family("WaistCBack")
    assert result.joint_family == "pelvis_hip"
    assert result.mapping_confidence == "template_uncertain"


def test_heuristic_finger_toe_excluded():
    mapper = MarkerFamilyMapper()
    assert mapper.map_marker_to_family("LThumb").joint_family == "fingers_excluded"
    assert mapper.map_marker_to_family("LToeTip").joint_family == "toes_excluded"


def test_unknown_marker_unmapped():
    mapper = MarkerFamilyMapper()
    result = mapper.map_marker_to_family("TotallyUnknownMarker")
    assert result.joint_family == "unknown"
    assert result.mapping_source == "unmapped"
    assert result.mapping_confidence == "unmapped"


def test_body_region_fallback():
    mapper = MarkerFamilyMapper()
    result = mapper.map_marker_to_family(body_region_group="left_forearm")
    assert result.joint_family == "left_elbow_forearm"
    assert result.mapping_source == "body_region_group"


def test_no_link_id_in_result():
    mapper = MarkerFamilyMapper()
    result = mapper.map_marker_to_family("671:LHandIn")
    assert not hasattr(result, "link_id")
    assert not hasattr(result, "parent_canonical")
    assert not hasattr(result, "child_canonical")


@pytest.mark.skipif(not T1_DATADESC.exists(), reason="T1 DataDescriptions fixture missing")
def test_datadescriptions_loads_bone_markers():
    marker_map, meta = load_session_datadescriptions_marker_map(T1_DATADESC)
    assert len(marker_map) > 0
    assert meta["n_bone_markers"] > 0
    assert "LHandIn" in marker_map
    assert "LWristOut" in marker_map


@pytest.mark.skipif(not T1_DATADESC.exists(), reason="T1 DataDescriptions fixture missing")
def test_datadescriptions_lhandin_maps_to_lhand():
    mapper = build_mapper_from_datadescriptions(T1_DATADESC)
    result = mapper.map_marker_to_family("671:LHandIn")
    assert result.attached_bone_canonical == "LHand"
    assert result.mapping_source == "session_datadescriptions_optional"
    assert result.mapping_confidence == "attached_bone_observed_but_template_unverified"
    assert result.template_mapping_status == "session_datadescriptions_used_unverified"


@pytest.mark.skipif(not T1_DATADESC.exists(), reason="T1 DataDescriptions fixture missing")
def test_datadescriptions_lwristout_maps_to_lfarm():
    mapper = build_mapper_from_datadescriptions(T1_DATADESC)
    result = mapper.map_marker_to_family("LWristOut")
    assert result.attached_bone_canonical == "LFArm"
    assert result.joint_family == "left_elbow_forearm"


@pytest.mark.skipif(not T1_DATADESC.exists(), reason="T1 DataDescriptions fixture missing")
def test_waistcback_template_uncertain_with_datadescriptions():
    mapper = build_mapper_from_datadescriptions(T1_DATADESC)
    result = mapper.map_marker_to_family("WaistCBack")
    assert result.joint_family == "pelvis_hip"
    # Bone is observed but exact link mapping stays uncertain
    assert result.mapping_confidence == "attached_bone_observed_but_template_unverified"


def test_datadescriptions_absent_uses_heuristic():
    mapper = MarkerFamilyMapper()
    result = mapper.map_marker_to_family("LHandIn")
    assert result.mapping_source == "marker_name_heuristic"
    assert result.template_mapping_status == "missing_datadescriptions_fallback_to_heuristic"
    assert result.attached_bone == "LHand"


@pytest.mark.skipif(not T1_DATADESC.exists(), reason="T1 DataDescriptions fixture missing")
def test_marker_missing_from_datadescriptions_falls_back():
    mapper = build_mapper_from_datadescriptions(T1_DATADESC)
    result = mapper.map_marker_to_family("TotallyUnknownMarker")
    assert result.mapping_source == "unmapped"
    assert result.joint_family == "unknown"


def test_build_mapper_absent_path():
    mapper = build_mapper_from_datadescriptions(None)
    assert not mapper.datadescriptions_used
    assert mapper.mapping_version == "heuristic_v0"


def test_canonicalize_bone_name():
    assert canonicalize_bone_name("671_LHand") == "LHand"
    assert canonicalize_bone_name("671_Chest") == "Chest"
