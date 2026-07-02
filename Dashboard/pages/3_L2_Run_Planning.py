"""Stage 3 — Layer 2 QC / run planning (dry-run only until G6)."""

from __future__ import annotations

import streamlit as st

from g2_components import cache_load_snapshot, inject_g2_css, render_curated_registry_banner
from g6_controls import init_g6_sidebar
from pipeline_dry_run import ensure_index_in_session, render_dry_run_commands, render_g6_execute_panel, render_session_picker
from project_paths import load_project_paths
from session_pipeline import plan_layer2_commands
from stage_layout import render_stage_header
from ui_bootstrap import REPO_ROOT, configure_python_paths

configure_python_paths()

st.set_page_config(page_title="L2 Run Planning", page_icon="2️⃣", layout="wide")
inject_g2_css()
render_curated_registry_banner()
init_g6_sidebar()

snapshot = cache_load_snapshot()
render_stage_header(
    snapshot,
    stage=3,
    title="Layer 2 QC / Run Planning",
    caption="Preview kinematics (stage 08 + export) commands. G6 enables guarded execution below.",
)

paths = load_project_paths(project_root=REPO_ROOT)
index_df = ensure_index_in_session(paths)
if index_df.empty:
    st.warning("Run Stage 1 discovery first.")
    st.stop()

selected_rows = render_session_picker(index_df)
planned = plan_layer2_commands(
    selected_rows,
    repo_root=REPO_ROOT,
    raw_layer2_root=paths.data_raw_layer2,
)
st.subheader("Dry-run L2 command plan")
render_dry_run_commands(planned)
render_g6_execute_panel(
    planned,
    repo_root=REPO_ROOT,
    layer_label="Layer 2 kinematics",
    write_paths=[str(REPO_ROOT / "Layer2_Motive_Kinematics" / "outputs")],
)

with st.expander("L2 QC log drill-down (audit)"):
    st.caption("Per-link and per-frame evidence appears on Stage 5 after export.")
