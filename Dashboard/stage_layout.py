"""Shared stage header, gate strip, and roadmap boundary banners."""

from __future__ import annotations

import streamlit as st

from g2_components import render_verdict_card
from g6_controls import g6_is_enabled
from stage_gates import StageGateSummary, gate_for_stage
from project_status import ProjectSnapshot


def render_roadmap_boundary(*, stage: int) -> None:
    enabled = g6_is_enabled()
    if stage in {2, 3, 4}:
        if enabled:
            st.success(
                f"**Stage {stage} — G6 active:** guarded run panel enabled below. "
                "Canonical batch remains read-only."
            )
        else:
            st.info(
                f"**Stage {stage} — G1–G5:** read-only planning and dry-run previews. "
                "Pipeline execution is disabled until **G6** guarded triggers."
            )
    elif stage == 5:
        if enabled:
            st.success(
                "**Stage 5 — G6 active:** sign-off persists to "
                "`processed/pre_jvcpca_review/verification_snapshot.yaml`."
            )
        else:
            st.info(
                "**Stage 5 — G1–G5:** verification review only. Sign-off persistence unlocks Stage 6 in **G6+**."
            )
    elif stage == 6:
        if enabled:
            st.success(
                "**Stage 6 — G6 active:** timestamped Layer 3 batch runs available when Stage 5 sign-off exists."
            )
        else:
            st.info(
                "**Stage 6 — G1–G5:** analysis intent and dry-run execution plan only. "
                "JcvPCA batch runs require **G6** and Stage 5 sign-off."
            )
    elif stage == 7:
        if enabled:
            st.success(
                "**Stage 7 — G6 active:** edit `gui_editable` thresholds (audited). Scope-locked keys stay read-only."
            )
        else:
            st.info(
                "**Stage 7 — G1–G5:** read-only threshold registry. Editing arrives when G6 is enabled."
            )


def render_stage_gate_strip(gate: StageGateSummary) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Exists", gate.exists)
    c2.metric("Missing", gate.missing)
    c3.metric("Ready", gate.ready)
    c4.metric("Risky", gate.risky)
    c5.metric("Blocked", gate.blocked)
    st.caption(f"**Next action:** {gate.next_action}")
    with st.expander("Roadmap permissions for this stage"):
        st.write(f"**G1–G5 allowed:** {gate.allowed_g1_g5}")
        st.write(f"**G6+ allowed:** {gate.allowed_g6}")


def render_stage_header(
    snapshot: ProjectSnapshot,
    *,
    stage: int,
    title: str,
    caption: str,
) -> StageGateSummary:
    st.title(f"Stage {stage} — {title}")
    st.caption(caption)
    gate = gate_for_stage(snapshot, stage)
    render_stage_gate_strip(gate)
    render_roadmap_boundary(stage=stage)
    return gate


def render_verdict_cards(cards: list, *, max_visible: int = 5) -> None:
    if not cards:
        st.caption("No verdict cards for current selection.")
        return
    for card in cards[:max_visible]:
        render_verdict_card(card)
    if len(cards) > max_visible:
        st.caption(f"… and {len(cards) - max_visible} more verdict cards (narrow filters).")
