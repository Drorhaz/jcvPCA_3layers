"""Tests for within-participant core feature manifests (671 / 252)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_jvcpca_review.canonical_manifest import (
    CANONICAL_LINK_ALIASES,
    CORE_MANIFEST_671,
    CORE_MANIFEST_252,
    core_manifest_path_for_participant,
    load_pilot_manifest,
    pilot_feature_order,
    pilot_link_names,
    pilot_link_order,
    resolve_session_links_from_manifest,
)
from pre_jvcpca_review.layer3_export_manifest import feature_schema_id_from_order
from pre_jvcpca_review.load_layer2 import LinkRecord

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def manifest_671():
    return load_pilot_manifest(CORE_MANIFEST_671)


@pytest.fixture(scope="module")
def manifest_252():
    return load_pilot_manifest(CORE_MANIFEST_252)


def test_core_manifest_paths():
    assert core_manifest_path_for_participant("671") == CORE_MANIFEST_671
    assert core_manifest_path_for_participant("252") == CORE_MANIFEST_252


def test_671_manifest_shape_and_exclusions(manifest_671):
    assert len(pilot_link_order(manifest_671)) == 14
    assert len(pilot_feature_order(manifest_671)) == 42
    names = set(pilot_link_names(manifest_671))
    assert "Neck->Head" in names
    assert "671->LThigh" not in names
    assert "671->RThigh" not in names
    assert "T3_671->LThigh" not in names
    assert "T3_671->RThigh" not in names


def test_252_manifest_includes_pelvis_roots(manifest_252):
    assert len(pilot_link_order(manifest_252)) == 16
    assert len(pilot_feature_order(manifest_252)) == 48
    names = set(pilot_link_names(manifest_252))
    assert "252->LThigh" in names
    assert "252->RThigh" in names
    assert "671->LThigh" not in names


def test_671_and_252_feature_schemas_differ(manifest_671, manifest_252):
    id_671 = feature_schema_id_from_order(pilot_feature_order(manifest_671))
    id_252 = feature_schema_id_from_order(pilot_feature_order(manifest_252))
    assert id_671 != id_252


def test_neck2_head_alias_resolves_for_671_manifest(manifest_671):
    session_links = [
        LinkRecord("J003", "Neck2", "Head", "core_candidate", "pass", "Neck2->Head"),
        LinkRecord("J028", "Chest", "Neck", "core_candidate", "pass", "Chest->Neck"),
        LinkRecord("J021", "Chest", "LShoulder", "core_candidate", "pass", "Chest->LShoulder"),
        LinkRecord("J027", "LShoulder", "LUArm", "core_candidate", "pass", "LShoulder->LUArm"),
        LinkRecord("J005", "LUArm", "LFArm", "core_candidate", "pass", "LUArm->LFArm"),
        LinkRecord("J007", "LFArm", "LHand", "core_candidate", "pass", "LFArm->LHand"),
        LinkRecord("J045", "Chest", "RShoulder", "core_candidate", "pass", "Chest->RShoulder"),
        LinkRecord("J051", "RShoulder", "RUArm", "core_candidate", "pass", "RShoulder->RUArm"),
        LinkRecord("J029", "RUArm", "RFArm", "core_candidate", "pass", "RUArm->RFArm"),
        LinkRecord("J031", "RFArm", "RHand", "core_candidate", "pass", "RFArm->RHand"),
        LinkRecord("J020", "LThigh", "LShin", "core_candidate", "pass", "LThigh->LShin"),
        LinkRecord("J006", "LShin", "LFoot", "core_candidate", "pass", "LShin->LFoot"),
        LinkRecord("J044", "RThigh", "RShin", "core_candidate", "pass", "RThigh->RShin"),
        LinkRecord("J030", "RShin", "RFoot", "core_candidate", "pass", "RShin->RFoot"),
    ]
    _, resolved = resolve_session_links_from_manifest(manifest_671, session_links)
    assert resolved[("Neck", "Head")].parent_canonical == "Neck2"
    assert pilot_feature_order(manifest_671)[0] == "Neck_to_Head_rx"


def test_neck_alias_policy_documented():
    assert ("Neck", "Head") in CANONICAL_LINK_ALIASES
    assert ("Neck2", "Head") in CANONICAL_LINK_ALIASES[("Neck", "Head")]
