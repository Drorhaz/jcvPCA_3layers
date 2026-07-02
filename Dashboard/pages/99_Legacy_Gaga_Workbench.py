"""Legacy Gaga workbench page — retired; use Stage 6."""

from __future__ import annotations

import streamlit as st

from ui_bootstrap import configure_python_paths

configure_python_paths()

st.set_page_config(page_title="Legacy Workbench (retired)", layout="wide")
st.title("Legacy Gaga workbench page (retired)")
st.warning(
    "This page has been superseded by **Stage 6 — Analysis Intent, Execution Plan, and JcvPCA**. "
    "Per-comparison workbench exports remain under each batch's `comparisons/<key>/run/` directory."
)
st.page_link("pages/6_Analysis_Execution.py", label="Open Stage 6 — Analysis & JcvPCA", icon="📊")
st.markdown(
    """
For deep per-comparison inspection, open a timestamped batch folder:
- `comparison_status.csv` — run status
- `comparisons/<participant>_<block>_<comparison_id>/link_focus_manifest.json` — PCA input filtering
- `comparisons/.../run/` — workbench CSV exports
"""
)
