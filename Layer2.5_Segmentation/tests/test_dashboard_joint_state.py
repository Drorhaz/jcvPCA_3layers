"""Tests for dashboard joint selection session-state helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_ROOT = ROOT / "dashboard"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from dashboard_state import (  # noqa: E402
    clear_joint_checkbox_widget_keys,
    joint_filter_signature,
    joint_filters_are_restrictive,
    set_selected_joints,
    sync_joint_selection_to_filters,
)
from pre_jvcpca_review.app_controller import JointOption, PreJcvpcaReviewController  # noqa: E402
from pre_jvcpca_review.joint_body_sections import (  # noqa: E402
    BODY_SECTION_ALL,
    BODY_SECTION_LEFT_ARM,
    BODY_SECTION_PILOT_CORE,
    BODY_SECTION_UPPER,
    link_matches_body_section,
)
from pre_jvcpca_review.joint_overlap import DIRECT  # noqa: E402
from pre_jvcpca_review.load_layer2 import LinkRecord  # noqa: E402


def _link(link_id: str, parent: str, child: str, scope: str = "core_candidate") -> LinkRecord:
    return LinkRecord(
        link_id=link_id,
        parent_canonical=parent,
        child_canonical=child,
        feature_scope=scope,
        stage07_jump_status="pass",
        display_name=f"{parent}->{child}",
    )


def test_clear_joint_checkbox_widget_keys_removes_only_joint_widgets() -> None:
    state = {
        "selected_joints": ["J001"],
        "joint_cb_J001": True,
        "joint_cb_J002": False,
        "participant_id": "671",
    }
    clear_joint_checkbox_widget_keys(state)
    assert "joint_cb_J001" not in state
    assert "joint_cb_J002" not in state
    assert state["selected_joints"] == ["J001"]
    assert state["participant_id"] == "671"


def test_set_selected_joints_sorts_dedupes_and_clears_widgets() -> None:
    state = {
        "selected_joints": [],
        "joint_cb_J001": True,
        "warning_summary": object(),
    }
    set_selected_joints(state, ["J002", "J001", "J002"])
    assert state["selected_joints"] == ["J001", "J002"]
    assert "joint_cb_J001" not in state
    assert "warning_summary" not in state


def test_bulk_select_clears_stale_checkbox_widget_state() -> None:
    """Simulates Streamlit persisting joint_cb_* keys after a bulk select."""
    state = {
        "selected_joints": ["J001"],
        "joint_cb_J001": True,
        "joint_cb_J002": False,
        "joint_cb_J003": False,
        "warning_summary": object(),
    }
    set_selected_joints(state, ["J002", "J003"])
    assert state["selected_joints"] == ["J002", "J003"]
    assert not any(key.startswith("joint_cb_") for key in state)
    assert "warning_summary" not in state

    summary = object()
    state = {"selected_joints": [], "warning_summary": summary}
    set_selected_joints(state, ["J001"], invalidate_warnings=False)
    assert state["warning_summary"] is summary


@pytest.fixture
def controller_with_joints() -> PreJcvpcaReviewController:
    ctrl = PreJcvpcaReviewController(ROOT)
    links = [
        _link("J001", "Chest", "Neck", "core_candidate"),
        _link("J002", "LUArm", "LFArm", "core_candidate"),
        _link("J003", "LFArm", "LHand", "optional"),
        _link("J004", "RFArm", "RHand", "core_candidate"),
    ]
    ctrl._links = links
    ctrl._pilot_link_ids = {"J001", "J002"}
    ctrl.current_overlap = None
    ctrl.joint_options = [
        JointOption(
            link_id=link.link_id,
            label=link.display_name,
            display_name=link.display_name,
            feature_scope=link.feature_scope,
            is_core=link.feature_scope == "core_candidate",
            classification=DIRECT if link.link_id in {"J001", "J002"} else "",
            is_directly_comparable=link.link_id in {"J001", "J002"},
            body_section=BODY_SECTION_LEFT_ARM if link.link_id in {"J002", "J003"} else BODY_SECTION_PILOT_CORE,
        )
        for link in links
    ]
    return ctrl


def test_controller_core_and_comparable_joint_ids(controller_with_joints: PreJcvpcaReviewController) -> None:
    ctrl = controller_with_joints
    assert set(ctrl.core_joint_ids()) == {"J001", "J002", "J004"}
    assert set(ctrl.directly_comparable_joint_ids()) == {"J001", "J002"}


def test_filtered_joint_options_respects_filters(controller_with_joints: PreJcvpcaReviewController) -> None:
    ctrl = controller_with_joints
    core_only = ctrl.filtered_joint_options(core_only=True)
    assert {opt.link_id for opt in core_only} == {"J001", "J002", "J004"}

    comparable_only = ctrl.filtered_joint_options(directly_comparable_only=True)
    assert {opt.link_id for opt in comparable_only} == {"J001", "J002"}

    left_arm = ctrl.filtered_joint_options(body_section=BODY_SECTION_LEFT_ARM)
    assert {opt.link_id for opt in left_arm} == {"J002", "J003"}

    pilot_core = ctrl.filtered_joint_options(body_section=BODY_SECTION_PILOT_CORE)
    assert {opt.link_id for opt in pilot_core} == {"J001", "J002"}


def test_upper_body_filter_includes_trunk_and_arm_links() -> None:
    pilot_links = [
        _link("J001", "Neck", "Head"),
        _link("J002", "Chest", "Neck"),
        _link("J003", "Chest", "LShoulder"),
        _link("J004", "LUArm", "LFArm"),
        _link("J005", "RFArm", "RHand"),
    ]
    for link in pilot_links:
        assert link_matches_body_section(link, BODY_SECTION_UPPER)
    assert not link_matches_body_section(_link("J006", "LThigh", "LShin"), BODY_SECTION_UPPER)


def test_sync_joint_selection_to_filters_selects_matching_ids() -> None:
    signature = joint_filter_signature(False, False, BODY_SECTION_LEFT_ARM)
    state = {
        "selected_joints": ["J001", "J004"],
        "joint_cb_J001": True,
        "joint_cb_J004": True,
    }
    assert sync_joint_selection_to_filters(state, ["J002", "J003"], signature)
    assert state["selected_joints"] == ["J002", "J003"]
    assert not any(key.startswith("joint_cb_") for key in state)


def test_sync_joint_selection_skips_when_filters_are_all() -> None:
    signature = joint_filter_signature(False, False, BODY_SECTION_ALL)
    state = {"selected_joints": ["J001"]}
    assert not sync_joint_selection_to_filters(state, ["J002", "J003"], signature)
    assert state["selected_joints"] == ["J001"]


def test_sync_joint_selection_skips_when_signature_unchanged() -> None:
    signature = joint_filter_signature(True, False, BODY_SECTION_ALL)
    state = {
        "selected_joints": ["J001"],
        "joint_filter_signature": signature,
    }
    assert not sync_joint_selection_to_filters(state, ["J001", "J002"], signature)
    assert state["selected_joints"] == ["J001"]


def test_joint_filters_are_restrictive() -> None:
    assert not joint_filters_are_restrictive(joint_filter_signature(False, False, BODY_SECTION_ALL))
    assert joint_filters_are_restrictive(joint_filter_signature(True, False, BODY_SECTION_ALL))
    assert joint_filters_are_restrictive(joint_filter_signature(False, True, BODY_SECTION_ALL))
    assert joint_filters_are_restrictive(joint_filter_signature(False, False, BODY_SECTION_UPPER))

