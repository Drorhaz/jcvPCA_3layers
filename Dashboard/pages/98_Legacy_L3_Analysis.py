"""Legacy Layer 3 analysis page — retired; use Stage 6."""

from __future__ import annotations

import streamlit as st

from ui_bootstrap import configure_python_paths

configure_python_paths()

st.set_page_config(page_title="Legacy L3 (retired)", layout="wide")
st.title("Legacy Layer 3 analysis page (retired)")
st.warning(
    "This page has been superseded by **Stage 6 — Analysis Intent, Execution Plan, and JcvPCA**. "
    "Use the batch results reader and G6 guarded execution there."
)
st.page_link("pages/6_Analysis_Execution.py", label="Open Stage 6 — Analysis & JcvPCA", icon="📊")
st.markdown(
    """
The Stage 6 reader includes:
- Validated `analysis_request.yaml` planning
- G6 guarded Layer 3 batch runs (timestamped outputs only)
- `link_focus` PCA-input ledgers
- Decision summary and diff vs canonical batch
- On-demand numeric/poster report generation
"""
)
