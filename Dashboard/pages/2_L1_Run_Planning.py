"""Stage 2 — Layer 1 QC / run planning (dry-run only until G6)."""

from __future__ import annotations

import streamlit as st

from g2_components import cache_load_snapshot, inject_g2_css, render_curated_registry_banner
from g6_controls import init_g6_sidebar
from pipeline_dry_run import ensure_index_in_session, render_dry_run_commands, render_g6_execute_panel, render_session_picker
from project_paths import load_project_paths
from session_pipeline import plan_layer1_commands
from stage_layout import render_stage_header
from ui_bootstrap import REPO_ROOT, configure_python_paths

configure_python_paths()

st.set_page_config(page_title="L1 Run Planning", page_icon="1️⃣", layout="wide")
inject_g2_css()
render_curated_registry_banner()
init_g6_sidebar()

snapshot = cache_load_snapshot()
render_stage_header(
    snapshot,
    stage=2,
    title="Layer 1 QC / Run Planning",
    caption="Select sessions and preview Motive QC commands. G6 enables guarded execution below.",
)

paths = load_project_paths(project_root=REPO_ROOT)
index_df = ensure_index_in_session(paths)
if index_df.empty:
    st.warning("Run Stage 1 discovery first.")
    st.stop()

selected_rows = render_session_picker(index_df)
planned = plan_layer1_commands(selected_rows, repo_root=REPO_ROOT)
st.subheader("Dry-run L1 command plan")
render_dry_run_commands(planned)
render_g6_execute_panel(
    planned,
    repo_root=REPO_ROOT,
    layer_label="Layer 1 Motive QC",
    write_paths=[
        str(REPO_ROOT / "Layer1_motive_qc" / "motive_qc" / "outputs"),
        str(REPO_ROOT / "Layer2.5_Segmentation" / "input" / "Layer1_QC"),
    ],
)
