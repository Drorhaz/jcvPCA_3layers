"""Stage 4 — Segmentation & Export Review (all xlsx exercises)."""

from __future__ import annotations

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
from g6_controls import init_g6_sidebar
from pipeline_dry_run import ensure_index_in_session, render_dry_run_commands, render_g6_execute_panel, render_session_picker
from project_paths import load_project_paths
from session_pipeline import default_layer25_output_root, plan_layer25_commands
from segmentation_coverage import (
    EXERCISE_SELECTION_ALL_IN_SHEET,
    EXERCISE_SELECTION_EXPLICIT_IDS,
    EXERCISE_SELECTION_GAGA_P_PHASES,
    build_segmentation_coverage_rows,
    list_sheet_exercises_for_participant,
    summarize_segmentation_coverage,
)
from project_status import GAGA_P_PHASES
from stage_layout import render_stage_header
from ui_bootstrap import REPO_ROOT, configure_python_paths
from verdict import verdict_from_coverage_row

configure_python_paths()

st.set_page_config(page_title="Segmentation & Export", page_icon="🧩", layout="wide")
inject_g2_css()
render_curated_registry_banner()
init_g6_sidebar()

snapshot = cache_load_snapshot()
render_stage_header(
    snapshot,
    stage=4,
    title="Segmentation & Export Review",
    caption="Segmentation xlsx is source of truth for all exercises (ex01 … end).",
)

render_advisory_banner(
    "Default view includes all sheet exercises. Gaga P-phases are a filter, not the catalog ceiling."
)
render_discovered_participants_banner(snapshot)

c1, c2 = st.columns(2)
with c1:
    participant = participant_selectbox(snapshot, label="Participant", key="seg_participant")
with c2:
    repetitions = c2.multiselect("Repetitions", options=["R1", "R2"], default=["R1", "R2"])
if participant is None:
    st.stop()

exercise_options = list_sheet_exercises_for_participant(snapshot, participant)
mode = st.radio(
    "Exercise catalog filter",
    options=[
        ("All exercises in sheet (default)", EXERCISE_SELECTION_ALL_IN_SHEET),
        ("Gaga P-phases only", EXERCISE_SELECTION_GAGA_P_PHASES),
        ("Explicit exercise IDs", EXERCISE_SELECTION_EXPLICIT_IDS),
    ],
    format_func=lambda x: x[0],
    horizontal=True,
    index=0,
)
exercise_selection_mode = mode[1]
selected_exercise_ids: tuple[int, ...] = ()
p_phases = list(GAGA_P_PHASES)
if exercise_selection_mode == EXERCISE_SELECTION_GAGA_P_PHASES:
    p_phases = st.multiselect("Gaga P-phases", options=list(GAGA_P_PHASES), default=["P1", "P2", "P3"])
elif exercise_selection_mode == EXERCISE_SELECTION_EXPLICIT_IDS and exercise_options:
    id_labels = [f"Ex {opt['exercise_id']:02d} ({opt['label']})" for opt in exercise_options]
    picked = st.multiselect("Exercise IDs", options=id_labels, default=id_labels)
    id_map = {id_labels[i]: exercise_options[i]["exercise_id"] for i in range(len(id_labels))}
    selected_exercise_ids = tuple(id_map[l] for l in picked)

inp = AnalysisRequestInput(
    participant_id=participant,
    p_phases=tuple(p_phases),
    repetitions=tuple(repetitions) if repetitions else ("R1", "R2"),
    comparisons=[comparison_spec_from_preset("L2_T1_vs_T3", tuple(repetitions or ("R1", "R2")))],
    exercise_selection_mode=exercise_selection_mode,
    selected_exercise_ids=selected_exercise_ids,
)

rows, seg_path = build_segmentation_coverage_rows(snapshot, inp)
summary = summarize_segmentation_coverage(rows)

if seg_path:
    st.success(f"Workbook: `{seg_path}`")
else:
    st.error("Segmentation workbook not found.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Sheet rows", summary.get("sheet_rows", 0))
m2.metric("Requested", summary.get("requested", 0))
m3.metric("Exported", summary.get("exported", 0))
m4.metric("Need export", summary.get("requested_not_exported", 0))

if rows:
    display_rows = [
        {
            "session": r["session_id"],
            "ex_id": r["exercise_id"],
            "label": r["exercise_export_label"],
            "frames": f"{r['start_frame']}–{r['end_frame']}",
            "requested": r["requested"],
            "status": r["coverage_status"],
            "qc": r.get("qc_status", ""),
            "layer3_safe": r.get("layer3_safe", ""),
        }
        for r in rows
    ]
    st.dataframe(display_rows, use_container_width=True, hide_index=True)

    st.subheader("Explanation-first verdicts (sample)")
    requested_rows = [r for r in rows if r.get("requested")][:8]
    for row in requested_rows:
        render_verdict_card(verdict_from_coverage_row(row))

st.divider()
st.subheader("Layer 2.5 export planning (G6)")
paths = load_project_paths(project_root=REPO_ROOT)
index_df = ensure_index_in_session(paths)
if index_df.empty:
    st.warning("Run Stage 1 discovery before planning L2.5 export.")
else:
    export_all = st.checkbox(
        "Export all exercises in segmentation xlsx (`--all-sheet-exercises`)",
        value=True,
    )
    selected_rows = render_session_picker(index_df)
    l25_root = default_layer25_output_root(paths)
    st.caption(f"Output root: `{l25_root}`")
    planned_l25 = plan_layer25_commands(
        selected_rows,
        repo_root=REPO_ROOT,
        output_root=l25_root,
        export_all_sheet_exercises=export_all,
    )
    render_dry_run_commands(planned_l25)
    render_g6_execute_panel(
        planned_l25,
        repo_root=REPO_ROOT,
        layer_label="Layer 2.5 Gaga export",
        write_paths=[str(l25_root)],
    )
