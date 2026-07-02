"""Stage 1 — Discover & Data Inventory."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from g2_components import (
    cache_load_snapshot,
    inject_g2_css,
    render_discovered_participants_banner,
    render_curated_registry_banner,
)
from participant_discovery import discovery_table_rows
from project_paths import load_project_paths
from session_pipeline import (
    default_layer1_root,
    default_layer1_scan_roots,
    default_layer2_root,
    load_session_index,
    processed_session_index_path,
    rebuild_session_index,
)
from stage_layout import render_stage_header
from ui_bootstrap import REPO_ROOT, configure_python_paths

configure_python_paths()

st.set_page_config(page_title="Discover & Inventory", page_icon="🔍", layout="wide")
inject_g2_css()
render_curated_registry_banner()

snapshot = cache_load_snapshot()
render_stage_header(
    snapshot,
    stage=1,
    title="Discover & Data Inventory",
    caption="Scan Layer 1 / Layer 2 outputs and repair `processed/session_index.csv` (metadata sync only).",
)

paths = load_project_paths(project_root=REPO_ROOT)
index_path = processed_session_index_path(paths)

if "discovered_index" not in st.session_state:
    st.session_state.discovered_index = load_session_index(index_path)

c1, c2 = st.columns(2)
layer1_root = Path(c1.text_input("Layer 1 scan root", value=str(default_layer1_root(paths))))
layer2_root = Path(c2.text_input("Layer 2 scan root", value=str(default_layer2_root(paths))))
st.caption(
    "Layer 1 multi-root scan: " + ", ".join(f"`{p}`" for p in default_layer1_scan_roots(paths))
)

if st.button("Discover & repair index", type="primary"):
    try:
        summary = rebuild_session_index(
            layer1_root=layer1_root,
            layer2_root=layer2_root,
            index_path=index_path,
            project_root=REPO_ROOT,
        )
        st.session_state.discovered_index = summary.session_index
        cache_load_snapshot.clear()
        st.success(f"Indexed {summary.n_sessions} sessions ({summary.n_matched} matched).")
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))

index_df: pd.DataFrame = st.session_state.discovered_index
snapshot = cache_load_snapshot()
render_discovered_participants_banner(snapshot)

disc_rows = discovery_table_rows(snapshot.participant_discovery) if snapshot.participant_discovery else []
if disc_rows:
    st.subheader("Participant discovery map")
    st.dataframe(disc_rows, use_container_width=True, hide_index=True)

if index_df.empty:
    st.warning("No sessions indexed yet.")
    st.stop()

display_cols = [
    "session_id", "participant_id", "timepoint", "is_matched", "match_warning",
    "layer1_run_dir", "layer2_run_dir", "n_frames_layer1", "n_frames_layer2",
]
view = index_df[display_cols].copy()
view["is_matched"] = view["is_matched"].map({True: "yes", False: "no", "True": "yes", "False": "no"})
st.dataframe(view, use_container_width=True, hide_index=True)

with st.expander("L1/L2 full log drill-down (audit)"):
    st.caption("Open Stage 2 / Stage 3 after runs for per-session QC detail. Full logs are not primary daily views.")
