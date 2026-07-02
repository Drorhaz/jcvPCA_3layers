"""3Layers integrated workflow dashboard — Stages 0–7."""

from __future__ import annotations

import streamlit as st

from g2_components import inject_g2_css, render_curated_registry_banner
from ui_bootstrap import configure_python_paths

configure_python_paths()

st.set_page_config(
    page_title="3Layers Research Assistant",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_g2_css()
render_curated_registry_banner()

st.title("3Layers Research Workflow Assistant")
st.caption("Integrated pipeline: discover → L1 → L2 → segment (all xlsx) → verify → analyze.")

st.markdown(
    """
| Stage | Page |
|-------|------|
| **0** | Project Overview |
| **1** | Discover & Data Inventory |
| **2** | Layer 1 QC / Run Planning *(G6: run)* |
| **3** | Layer 2 QC / Run Planning *(G6: run)* |
| **4** | Segmentation & Export Review *(G6: L2.5 export)* |
| **5** | QC Verification *(gate before Layer 3)* |
| **6** | Analysis Intent & Execution Plan *(G6: L3 batch)* |
| **7** | Config / Thresholds *(G6: audited edits)* |

Legacy pages **98–99** redirect to Stage 6 (retired workbench surfaces).
"""
)

st.info(
    "**G1–G5:** read-only planning, explanation-first verdicts, dry-run by default. "
    "**G6:** enable **Guarded execution** in the sidebar on any stage page for runs, config edits, and verification persistence."
)
