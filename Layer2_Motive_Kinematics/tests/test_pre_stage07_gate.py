"""Tests for pre–Stage 07 gate classification (documentation gate only)."""

from __future__ import annotations

from layer2_motive.pre_stage07_gate import (
    classify_link_for_gate,
    compute_gate_status,
)


def test_core_candidate_head_neck_shoulder_limb() -> None:
    head = classify_link_for_gate(
        parent_bone="Neck",
        child_bone="Head",
        is_root_anchor_link=False,
        exclusion_reason="",
    )
    assert head.core_candidate is True
    assert head.link_classification == "head_neck"

    thigh = classify_link_for_gate(
        parent_bone="671",
        child_bone="LThigh",
        is_root_anchor_link=False,
        exclusion_reason="",
    )
    assert thigh.core_candidate is True
    assert thigh.link_classification == "hip_top_segment_to_thigh"

    t3_thigh = classify_link_for_gate(
        parent_bone="T3_671",
        child_bone="RThigh",
        is_root_anchor_link=False,
        exclusion_reason="",
    )
    assert t3_thigh.core_candidate is True
    assert t3_thigh.link_classification == "hip_top_segment_to_thigh"


def test_excluded_finger_toe_root() -> None:
    finger = classify_link_for_gate(
        parent_bone="LHand",
        child_bone="LIndex3",
        is_root_anchor_link=False,
        exclusion_reason="distal_keyword:Index",
    )
    assert finger.core_candidate is False
    assert finger.excluded_candidate is True

    root = classify_link_for_gate(
        parent_bone="Root",
        child_bone="671",
        is_root_anchor_link=True,
        exclusion_reason="parent_is_root",
    )
    assert root.excluded_candidate is True
    assert root.link_classification == "virtual_root_parent_skip"

    trunk = classify_link_for_gate(
        parent_bone="671",
        child_bone="Ab",
        is_root_anchor_link=False,
        exclusion_reason="",
    )
    assert trunk.core_candidate is False
    assert trunk.link_classification == "trunk_spine"


def test_gate_status_core_pass_and_fail() -> None:
    assert (
        compute_gate_status(
            core_candidate=True,
            excluded_candidate=False,
            reconstruction_status="pass",
            post_correction_valid=True,
            requires_manual_review=False,
        )
        == "core_pass"
    )
    assert (
        compute_gate_status(
            core_candidate=True,
            excluded_candidate=False,
            reconstruction_status="fail",
            post_correction_valid=True,
            requires_manual_review=False,
        )
        == "fail"
    )
    assert (
        compute_gate_status(
            core_candidate=False,
            excluded_candidate=True,
            reconstruction_status="pass",
            post_correction_valid=True,
            requires_manual_review=False,
        )
        == "excluded_pass"
    )
