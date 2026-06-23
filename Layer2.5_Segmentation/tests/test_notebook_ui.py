"""Tests for pre_jvcpca_review notebook UI helpers and scoped warnings."""

from __future__ import annotations

from pre_jvcpca_review.joint_overlap import (
    classify_links,
    emit_joint_comparability_warnings,
    overlap_dataframe,
)
from pre_jvcpca_review.load_layer2 import LinkRecord
from pre_jvcpca_review.notebook_ui import (
    JointSelector,
    _sort_links,
    canonical_joint_label,
)
from pre_jvcpca_review.warnings import WarningCollector


def _link(link_id: str, parent: str, child: str, scope: str = "core_candidate") -> LinkRecord:
    return LinkRecord(
        link_id=link_id,
        parent_canonical=parent,
        child_canonical=child,
        feature_scope=scope,
        stage07_jump_status="pass",
        display_name=f"{parent}->{child}",
    )


def test_canonical_joint_label_matches_overlap_table_vocabulary():
    link = _link("J005", "LUArm", "LFArm")
    label = canonical_joint_label(link, overlap_classification="directly_comparable")
    assert label.startswith("LUArm->LFArm")
    assert "directly_comparable" in label
    assert "J005" in label


def test_sort_links_follows_canonical_order():
    links = [
        _link("J031", "RFArm", "RHand"),
        _link("J005", "LUArm", "LFArm"),
        _link("J028", "Chest", "Neck"),
    ]
    order = [("Chest", "Neck"), ("LUArm", "LFArm"), ("RFArm", "RHand")]
    sorted_links = _sort_links(links, order)
    assert [link.display_name for link in sorted_links] == [
        "Chest->Neck",
        "LUArm->LFArm",
        "RFArm->RHand",
    ]


def test_joint_selector_reports_canonical_names():
    links = [
        _link("J005", "LUArm", "LFArm"),
        _link("J007", "LFArm", "LHand"),
    ]
    selector = JointSelector.from_links(links, default_link_ids={"J005"})
    assert selector.selected_canonical_names() == ["LUArm->LFArm"]


def test_emit_joint_comparability_silent_for_unselected_bad_links():
    sess = {
        "T1": [_link("J001", "Neck", "Head"), _link("J002", "Chest", "Neck")],
        "T3": [
            _link("J001", "Neck", "Neck2"),
            _link("J002", "Neck2", "Head"),
            _link("J003", "Chest", "Neck"),
        ],
    }
    overlap = overlap_dataframe(classify_links(sess), "671", list(sess))
    collector = WarningCollector()

    emit_joint_comparability_warnings(
        collector,
        overlap,
        [("Chest", "Neck")],
        participant_id="671",
        session_id="671_T1_P1_R1",
    )

    assert collector.to_dataframe().empty
    assert not collector.has_blocking


def test_emit_joint_comparability_blocks_when_selected_link_is_bad():
    sess = {
        "T1": [_link("J001", "Neck", "Head")],
        "T3": [_link("J001", "Neck", "Neck2"), _link("J002", "Neck2", "Head")],
    }
    overlap = overlap_dataframe(
        classify_links(sess, candidate_links=[("Neck", "Head")]),
        "671",
        list(sess),
    )
    collector = WarningCollector()

    emit_joint_comparability_warnings(
        collector,
        overlap,
        [("Neck", "Head")],
        participant_id="671",
        session_id="671_T1_P1_R1",
    )

    df = collector.to_dataframe()
    blocking = df[df["warning_id"] == "joint.not_directly_comparable"]
    assert len(blocking) == 1
    assert blocking.iloc[0]["canonical_link_name"] == "Neck->Head"
    assert collector.has_blocking
