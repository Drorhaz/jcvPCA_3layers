"""Stage 5 — Segment / Link / Frame QC Verification (gate before Layer 3)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis_request import AnalysisRequestInput, comparison_spec_from_preset
from g2_components import (
    cache_load_snapshot,
    inject_g2_css,
    participant_selectbox,
    render_advisory_banner,
    render_curated_registry_banner,
    render_discovered_participants_banner,
    render_verdict_card,
)
from g6_controls import g6_is_enabled, init_g6_sidebar
from g6_execution import verification_snapshot_path
from inclusion_recommendations import build_inclusion_report, filter_inclusion_report, summarize_inclusion
from joint_link_qc import build_joint_link_qc_report, link_recommendations_as_rows
from readiness import build_readiness_matrix
from segmentation_coverage import EXERCISE_SELECTION_ALL_IN_SHEET, build_segmentation_coverage_rows
from stage_layout import render_stage_header
from ui_bootstrap import REPO_ROOT, configure_python_paths
from verdict import verdict_from_coverage_row, verdict_from_inclusion, verdict_from_readiness_cell
from verification_gate import (
    VerificationState,
    clear_verification_snapshot,
    load_verification_snapshot,
    reset_sign_off,
    save_verification_snapshot,
    sign_off,
    stage6_unlocked,
    toggle_segment,
)

configure_python_paths()

st.set_page_config(page_title="QC Verification", page_icon="✅", layout="wide")
inject_g2_css()
render_curated_registry_banner()
render_advisory_banner()
init_g6_sidebar()

snapshot = cache_load_snapshot()
render_discovered_participants_banner(snapshot)
render_stage_header(
    snapshot,
    stage=5,
    title="Segment / Link / Frame QC Verification",
    caption="Review evidence-rich verdicts. Stage 6 unlocks after verification sign-off.",
)

disk_state = load_verification_snapshot(REPO_ROOT)
if "verification_state" not in st.session_state:
    st.session_state.verification_state = disk_state or VerificationState()

state: VerificationState = st.session_state.verification_state
if disk_state and disk_state.signed_off:
    st.success(
        f"Persisted sign-off on disk ({len(disk_state.verified_segment_ids)} segments): "
        f"`{verification_snapshot_path(REPO_ROOT)}`"
    )

f1, f2, f3 = st.columns(3)
with f1:
    participant = participant_selectbox(snapshot, label="Participant", key="qc_participant")
timepoints = f2.multiselect("Timepoints", ["T1", "T2", "T3"], default=["T1", "T2", "T3"])
repetitions = f3.multiselect("Repetitions", ["R1", "R2"], default=["R1", "R2"])
if participant is None:
    st.stop()

tab_seg, tab_readiness, tab_links = st.tabs(
    ["Segment xlsx coverage", "Session readiness", "Link / body region"]
)

with tab_seg:
    inp = AnalysisRequestInput(
        participant_id=participant,
        repetitions=tuple(repetitions or ("R1", "R2")),
        comparisons=[comparison_spec_from_preset("L2_T1_vs_T3", tuple(repetitions or ("R1", "R2")))],
        exercise_selection_mode=EXERCISE_SELECTION_ALL_IN_SHEET,
    )
    rows, _ = build_segmentation_coverage_rows(snapshot, inp)
    requested = [r for r in rows if r.get("requested") and str(r.get("participant_id")) == participant]
    st.caption(f"{len(requested)} requested segment rows (all xlsx exercises).")
    for row in requested[:12]:
        seg_id = f"{row['session_id']}::{row['exercise_export_label']}"
        card = verdict_from_coverage_row(row)
        render_verdict_card(card)
        verified = st.checkbox(
            f"Verify {seg_id}",
            value=seg_id in state.verified_segment_ids,
            key=f"verify_{seg_id}",
        )
        toggle_segment(state, seg_id, verified=verified)

with tab_readiness:
    matrix = build_readiness_matrix(snapshot)
    cells = [
        c for c in matrix.cells
        if c.participant_id == participant
        and c.timepoint in (timepoints or ["T1", "T2", "T3"])
        and c.repetition in (repetitions or ["R1", "R2"])
    ][:15]
    for cell in cells:
        render_verdict_card(verdict_from_readiness_cell(cell))

with tab_links:
    report = build_joint_link_qc_report(snapshot, participant_ids=[participant])
    link_rows = link_recommendations_as_rows(report)
    if link_rows:
        st.dataframe(pd.DataFrame(link_rows).head(40), use_container_width=True, hide_index=True)
    inclusion = filter_inclusion_report(
        build_inclusion_report(snapshot),
        participant_ids=[participant],
        timepoints=timepoints or None,
        repetitions=repetitions or None,
    )
    for rec in inclusion[:10]:
        render_verdict_card(verdict_from_inclusion(rec))

st.divider()
st.subheader("Verification gate")
counts = summarize_inclusion(build_inclusion_report(snapshot))
st.caption(f"Cohort inclusion summary: {counts}")
st.write(f"**Verified segments selected:** {len(state.verified_segment_ids)}")
st.write(f"**Stage 6 unlocked:** {'Yes' if stage6_unlocked(state, disk_state=disk_state) else 'No'}")

notes = st.text_input("Sign-off notes", value=state.notes)
c1, c2, c3 = st.columns(3)
if c1.button("Sign off verified segments"):
    try:
        sign_off(state, notes=notes, science_hash=snapshot.config.science_hash)
        if g6_is_enabled():
            path = save_verification_snapshot(REPO_ROOT, state)
            st.success(f"Sign-off saved to `{path}`. Stage 6 unlocked.")
        else:
            st.success("Stage 6 unlocked for this browser session (enable G6 to persist sign-off).")
    except ValueError as exc:
        st.error(str(exc))
if c2.button("Reset sign-off"):
    reset_sign_off(state)
    if g6_is_enabled():
        clear_verification_snapshot(REPO_ROOT)
    st.info("Sign-off cleared.")
if c3.button("Reload sign-off from disk") and g6_is_enabled():
    loaded = load_verification_snapshot(REPO_ROOT)
    if loaded:
        st.session_state.verification_state = loaded
        st.success("Reloaded verification snapshot from disk.")
    else:
        st.warning("No verification snapshot on disk.")
