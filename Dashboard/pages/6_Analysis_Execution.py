"""Stage 6 — Analysis intent, execution plan, and JcvPCA (read-only until G6)."""

from __future__ import annotations

import streamlit as st

from g2_components import cache_load_snapshot, inject_g2_css, render_curated_registry_banner
from g6_controls import init_g6_sidebar
from renderers.decision_summary import render_decision_summary_reader
from renderers.analysis_request import render_analysis_request
from renderers.execution_plan import render_execution_plan
from stage_layout import render_stage_header
from ui_bootstrap import REPO_ROOT, configure_python_paths
from verification_gate import load_verification_snapshot, stage6_unlocked

configure_python_paths()

st.set_page_config(page_title="Analysis & JcvPCA", page_icon="📊", layout="wide")
inject_g2_css()
render_curated_registry_banner()
init_g6_sidebar()

snapshot = cache_load_snapshot()
render_stage_header(
    snapshot,
    stage=6,
    title="Analysis Intent, Execution Plan, and JcvPCA",
    caption="Build validated analysis intent and dry-run Layer 3 plan. Batch runs require G6 + Stage 5 sign-off.",
)

state = st.session_state.get("verification_state")
disk_state = load_verification_snapshot(REPO_ROOT)
unlocked = stage6_unlocked(state, disk_state=disk_state)
if not unlocked:
    st.warning(
        "Stage 6 is locked until you verify segments and sign off on **Stage 5 — QC Verification**. "
        "You may still preview tabs below for planning, but execution remains disabled."
    )

tab_request, tab_plan, tab_results = st.tabs(
    ["Analysis request", "Execution plan (dry-run)", "Batch results"]
)

with tab_request:
    render_analysis_request(snapshot)

with tab_plan:
    render_execution_plan(snapshot, verification_unlocked=unlocked)

with tab_results:
    render_decision_summary_reader(snapshot)
