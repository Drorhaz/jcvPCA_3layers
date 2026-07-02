"""G2 — Stage 0 Project Overview (read-only)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from g2_components import (
    cache_load_snapshot,
    inject_g2_css,
    render_advisory_banner,
    render_comparability_banner,
    render_curated_registry_banner,
    render_discovered_participants_banner,
    render_recommendation,
)
from project_status import participant_coverage_table, pipeline_layer_status
from recommend import all_recommendations, default_comparison_requests, recommend_comparison
from stage_gates import build_stage_gate_summaries
from stage_layout import render_stage_gate_strip
from ui_bootstrap import configure_python_paths

configure_python_paths()

st.set_page_config(page_title="Project Overview", page_icon="🧭", layout="wide")
inject_g2_css()
render_curated_registry_banner()

st.title("Stage 0 — Project Overview")
st.caption("Pipeline status, cohort coverage, canonical batch — integrated workflow entry point.")

snapshot = cache_load_snapshot()

st.subheader("Discovered participants")
render_discovered_participants_banner(snapshot)

st.subheader("Workflow stage summary")
gate_df = pd.DataFrame(
    [
        {
            "stage": g.stage,
            "title": g.title,
            "exists": g.exists,
            "missing": g.missing,
            "ready": g.ready,
            "risky": g.risky,
            "blocked": g.blocked,
            "next_action": g.next_action,
        }
        for g in build_stage_gate_summaries(snapshot)
    ]
)
st.dataframe(gate_df, use_container_width=True, hide_index=True)
render_stage_gate_strip(build_stage_gate_summaries(snapshot)[1])

if not snapshot.path_validation_ok:
    st.error("Path registry validation failed:")
    for msg in snapshot.path_validation_errors:
        st.write(f"- {msg}")
else:
    st.success("Path registry validation passed (`config/paths.yaml`).")

st.subheader("Gate recommendations")
render_advisory_banner()
for rec in all_recommendations(snapshot):
    render_recommendation(rec)

st.subheader("Default comparison readiness (advisory)")
for req in default_comparison_requests(snapshot):
    render_recommendation(recommend_comparison(snapshot, req))

st.subheader("Pipeline status by layer")
for row in pipeline_layer_status(snapshot):
    with st.expander(f"{row.layer} — {row.status.upper()}", expanded=row.status != "ok"):
        st.write(row.summary)
        if row.detail:
            st.caption(row.detail)

st.subheader("Participants and P-phase coverage")
cov = participant_coverage_table(snapshot)
if cov:
    st.dataframe(cov, use_container_width=True, hide_index=True)
else:
    st.info("No session index or export manifest found.")

st.subheader("Session index summary")
if snapshot.session_index_rows:
    st.caption(f"{len(snapshot.session_index_rows)} sessions indexed.")
    display_cols = [
        "participant_id",
        "timepoint",
        "repetition_id",
        "session_id",
        "is_matched",
        "match_warning",
    ]
    df = pd.DataFrame(snapshot.session_index_rows)
    cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)
else:
    st.warning("No `session_index.csv` found under `processed/` or Layer 2.5 outputs.")

st.subheader("Layer 3 batches")
st.write(f"**Canonical batch ID:** `{snapshot.canonical_batch_id}`")
st.write(f"**Canonical path exists:** {snapshot.canonical_batch_exists}")
if snapshot.batch_dirs:
    st.write("Timestamped batches under `Layer3_JcvPCA/outputs/`:")
    for name in snapshot.batch_dirs:
        marker = " ← canonical" if name == snapshot.canonical_batch_id else ""
        st.write(f"- `{name}`{marker}")
else:
    st.caption("No `gaga_batch_jcvpca_*` directories found.")

render_comparability_banner(
    snapshot.canonical_comparability,
    artifact_label=f"Canonical batch {snapshot.canonical_batch_id}",
    artifact_hash=snapshot.canonical_config_hash,
    current_hash=snapshot.config.science_hash,
)

st.subheader("Registry coverage (mirrored in central config)")
for layer, meta in snapshot.registry_coverage.items():
    st.write(f"- **{layer}:** {meta['label']} (`{meta['mirrored']}`)")
