"""G4 analysis request builder UI (Stage 6 tab)."""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
import yaml

from analysis_request import (
    AnalysisRequestInput,
    ComparisonSpecInput,
    build_analysis_request,
    comparison_spec_from_preset,
    save_analysis_request,
)
from comparison_readiness import KNOWN_LONGITUDINAL_COMPARISONS, KNOWN_REPETITION_COMPARISONS
from execution_plan import build_execution_plan
from g2_components import (
    render_advisory_banner,
    render_comparability_banner,
    participant_selectbox,
    status_pill,
)
from project_status import GAGA_P_PHASES, ProjectSnapshot
from segmentation_coverage import (
    EXERCISE_SELECTION_ALL_IN_SHEET,
    EXERCISE_SELECTION_EXPLICIT_IDS,
    EXERCISE_SELECTION_GAGA_P_PHASES,
    list_sheet_exercises_for_participant,
)
from ui_bootstrap import REPO_ROOT


def render_analysis_request(snapshot: ProjectSnapshot) -> None:
    render_advisory_banner("Define and validate analysis intent. Saving YAML does not run Layer 3.")

    # --- Builder form ---
    st.subheader("Request selection")
    c1, c2, c3 = st.columns(3)
    with c1:
        participant = participant_selectbox(snapshot, label="Participant", key="g4_participant")
    p_phases = c2.multiselect("P-phases", options=list(GAGA_P_PHASES), default=["P1", "P2", "P3"])
    repetitions = c3.multiselect("Repetitions", options=["R1", "R2"], default=["R1", "R2"])
    if participant is None:
        st.stop()

    longitudinal_options = list(KNOWN_LONGITUDINAL_COMPARISONS.keys())
    repetition_options = list(KNOWN_REPETITION_COMPARISONS.keys())
    all_comparison_ids = longitudinal_options + repetition_options

    selected_comparisons = st.multiselect(
        "Comparison pairs",
        options=all_comparison_ids,
        default=["L1_T1_vs_T2"],
        help="Mirrors Gaga batch comparison specs (L1/L2 longitudinal, I_* repetition).",
    )

    preset = st.selectbox(
        "Segment preset (metadata)",
        options=["manual", "only_P1", "only_P1_P3", "full_sequence", "high_quality_only"],
        index=2,
    )

    st.subheader("Exercise selection (segmentation xlsx)")
    exercise_options = list_sheet_exercises_for_participant(snapshot, participant)
    exercise_mode_label = st.radio(
        "Which sheet exercises to include in this request",
        options=[
            ("All exercises in each session sheet (default)", EXERCISE_SELECTION_ALL_IN_SHEET),
            ("Gaga P-phases only (P1–P5 / exercise 9–13)", EXERCISE_SELECTION_GAGA_P_PHASES),
            ("Pick explicit exercise IDs from sheet", EXERCISE_SELECTION_EXPLICIT_IDS),
        ],
        format_func=lambda x: x[0],
        horizontal=True,
        index=0,
    )
    exercise_selection_mode = exercise_mode_label[1]
    selected_exercise_ids: tuple[int, ...] = ()
    if exercise_selection_mode == EXERCISE_SELECTION_EXPLICIT_IDS and exercise_options:
        id_labels = [
            f"Ex {opt['exercise_id']:02d} ({opt['label']})"
            for opt in exercise_options
        ]
        default_labels = [
            lbl for lbl in id_labels if any(p in lbl for p in (p_phases or ["P1", "P2", "P3"]))
        ] or id_labels[8:13]
        picked_labels = st.multiselect(
            "Exercise IDs",
            options=id_labels,
            default=default_labels,
            help="Every row in the segmentation workbook can be exported via L2.5 batch export.",
        )
        id_map = {id_labels[i]: exercise_options[i]["exercise_id"] for i in range(len(id_labels))}
        selected_exercise_ids = tuple(id_map[lbl] for lbl in picked_labels)

    st.subheader("Outputs & link focus")
    o1, o2, o3 = st.columns(3)
    pc_spaces = o1.multiselect(
        "PC focus spaces",
        options=["all", "functional", "null_space"],
        default=["all", "functional", "null_space"],
    )
    gen_plots = o2.checkbox("Request comparison plots", value=True)
    use_comparable_only = o3.checkbox("Require comparable links only", value=True)

    body_regions = st.multiselect(
        "Body-region focus (optional)",
        options=[
            "upper_body", "lower_body", "trunk_spine",
            "left_arm", "right_arm", "left_leg", "right_leg", "other",
        ],
        default=[],
    )

    block_a_default = list(snapshot.config.get("cohort.block_a"))
    block_b_default = list(snapshot.config.get("cohort.block_b"))
    b1, b2 = st.columns(2)
    block_a = b1.multiselect("Block A exercises", options=list(GAGA_P_PHASES), default=block_a_default)
    block_b = b2.multiselect("Block B exercises", options=list(GAGA_P_PHASES), default=block_b_default)

    # --- Build & validate ---
    comps: list[ComparisonSpecInput] = []
    for cid in selected_comparisons:
        try:
            comps.append(comparison_spec_from_preset(cid, tuple(repetitions)))
        except KeyError as exc:
            st.error(str(exc))

    inp = AnalysisRequestInput(
        participant_id=participant,
        p_phases=tuple(p_phases) if p_phases else ("P1", "P2", "P3"),
        repetitions=tuple(repetitions) if repetitions else ("R1", "R2"),
        comparisons=comps,
        segment_preset=None if preset == "manual" else preset,
        block_a=tuple(block_a),
        block_b=tuple(block_b),
        pc_focus_spaces=tuple(pc_spaces) if pc_spaces else ("all", "functional", "null_space"),
        generate_comparison_plots=gen_plots,
        body_regions=tuple(body_regions),
        use_comparable_links_only=use_comparable_only,
        exercise_selection_mode=exercise_selection_mode,
        selected_exercise_ids=selected_exercise_ids,
    )

    request_id = st.text_input(
        "Request ID",
        value=f"{participant}_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{selected_comparisons[0] if selected_comparisons else 'draft'}",
    )

    if st.button("Validate request", type="primary"):
        st.session_state["g4_request"] = build_analysis_request(
            snapshot,
            inp,
            request_id=request_id or None,
            check_comparable_links=True,
        )

    request = st.session_state.get("g4_request")
    if request:
        st.subheader("Validation result")
        status = request["status"]
        st.markdown(f"**Status:** {status_pill(status)}", unsafe_allow_html=True)
        st.caption(request.get("advisory_label", ""))

        v = request.get("validation", {})
        e1, e2, e3 = st.columns(3)
        e1.metric("Errors (blockers)", len(v.get("errors", [])))
        e2.metric("Warnings", len(v.get("warnings", [])))
        e3.metric("Advisory notes", len(v.get("advisory_notes", [])))

        for label, key in (("Errors", "errors"), ("Warnings", "warnings"), ("Advisory", "advisory_notes")):
            items = v.get(key, [])
            if items:
                st.markdown(f"**{label}**")
                for item in items:
                    tk = f" · `{item['threshold_key']}`" if item.get("threshold_key") else ""
                    st.write(f"- [{item.get('source', '?')}] {item.get('message', '')}{tk}")

        st.markdown("**Comparison results**")
        for cr in v.get("comparison_results", []):
            st.write(f"- `{cr['comparison_id']}`: **{cr['verdict']}** — {cr['summary']}")

        st.markdown("**Resolved segments**")
        segs = request.get("resolved_segments", [])
        st.caption(f"{len(segs)} segment(s); comparable links: {v.get('comparable_link_count', 'n/a')}")
        if segs:
            st.dataframe(segs, use_container_width=True, hide_index=True)

        cov = request.get("segmentation_coverage") or []
        if cov:
            st.markdown("**Segmentation coverage**")
            st.caption(
                f"Summary: {v.get('segmentation_coverage', {})} · see Stage 4 Segmentation & Export Review"
            )

        render_comparability_banner(
            snapshot.canonical_comparability,
            artifact_label=f"Canonical batch {snapshot.canonical_batch_id}",
            artifact_hash=snapshot.canonical_config_hash,
            current_hash=snapshot.config.science_hash,
        )

        st.subheader("Provenance")
        prov = request.get("provenance", {})
        st.code(
            f"science_hash: {prov.get('science_hash', '')}\n"
            f"display_hash: {prov.get('display_hash', '')}\n"
            f"canonical_comparability: {prov.get('canonical_comparability', '')}",
        )

        yaml_text = yaml.safe_dump(request, sort_keys=False, allow_unicode=True)
        st.download_button(
            "Download analysis_request.yaml",
            data=yaml_text,
            file_name=f"{request['request_id']}.yaml",
            mime="text/yaml",
        )

        if st.button("Save to requests/analysis_requests/"):
            path = save_analysis_request(REPO_ROOT, request)
            st.success(f"Saved (no analysis run): `{path}`")
            st.caption("execution.allowed=false — G4 does not trigger computation.")

        st.divider()
        st.subheader("Dry-run execution plan preview")
        if st.button("Preview execution plan"):
            st.session_state["g5_plan_preview"] = build_execution_plan(snapshot, request)
        preview = st.session_state.get("g5_plan_preview")
        if preview:
            pf = preview.get("preflight", {})
            p1, p2, p3 = st.columns(3)
            p1.metric("Blockers", len(pf.get("blockers", [])))
            p2.metric("Warnings", len(pf.get("warnings", [])))
            p3.metric("Jobs", preview.get("runner_translation", {}).get("requested_job_count", 0))
            runner = preview.get("runner_translation", {})
            st.write(
                f"Proposed batch: `{runner.get('proposed_batch_id')}` · "
                f"status `{preview.get('plan_status')}` · execution disabled"
            )
            if pf.get("blockers"):
                st.error("Blockers present — resolve before any future execution.")

    else:
        st.info("Configure the request above, then click **Validate request**.")
