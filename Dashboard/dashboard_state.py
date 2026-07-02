"""Session-state helpers for the Pre-JcvPCA dashboard (testable without Streamlit)."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from pre_jvcpca_review.joint_body_sections import BODY_SECTION_ALL

JointFilterSignature = tuple[bool, bool, str]
DiagnosticsContextSignature = tuple[
    str | None,
    str | None,
    int,
    int,
    str,
    tuple[str, ...],
    tuple[str, ...],
]


def clear_joint_checkbox_widget_keys(session_state: MutableMapping[str, Any]) -> None:
    for key in list(session_state.keys()):
        if str(key).startswith("joint_cb_"):
            del session_state[key]


def diagnostics_context_signature(
    session_state: MutableMapping[str, Any],
) -> DiagnosticsContextSignature:
    return (
        session_state.get("participant_id"),
        session_state.get("session_id"),
        int(session_state.get("frame_start", 0)),
        int(session_state.get("frame_end", 0)),
        str(session_state.get("window_label", "")),
        tuple(session_state.get("selected_joints") or ()),
        tuple(session_state.get("qc_types") or ()),
    )


def invalidate_diagnostics(session_state: MutableMapping[str, Any]) -> None:
    session_state.pop("diagnostics_cache", None)
    session_state.pop("diagnostics_cached_signature", None)
    session_state.pop("diagnostics_error", None)


def set_selected_joints(
    session_state: MutableMapping[str, Any],
    link_ids: list[str],
    *,
    invalidate_warnings: bool = True,
) -> None:
    clear_joint_checkbox_widget_keys(session_state)
    session_state["selected_joints"] = sorted(set(link_ids))
    if invalidate_warnings:
        session_state.pop("warning_summary", None)
    invalidate_diagnostics(session_state)


def joint_filter_signature(
    core_only: bool,
    directly_comparable_only: bool,
    body_section: str,
) -> JointFilterSignature:
    return (core_only, directly_comparable_only, body_section)


def joint_filters_are_restrictive(signature: JointFilterSignature) -> bool:
    core_only, directly_comparable_only, body_section = signature
    return core_only or directly_comparable_only or body_section != BODY_SECTION_ALL


def sync_joint_selection_to_filters(
    session_state: MutableMapping[str, Any],
    matching_link_ids: list[str],
    signature: JointFilterSignature,
) -> bool:
    """Select all joints matching active filters when the filter set changes."""
    previous_signature = session_state.get("joint_filter_signature")
    session_state["joint_filter_signature"] = signature
    if not joint_filters_are_restrictive(signature):
        return False
    if previous_signature == signature:
        return False
    set_selected_joints(session_state, matching_link_ids)
    return True
