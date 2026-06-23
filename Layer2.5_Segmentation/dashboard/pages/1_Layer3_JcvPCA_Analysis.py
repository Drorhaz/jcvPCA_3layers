"""Layer 3 JcvPCA analysis page — multipage Streamlit app."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

L25_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = L25_ROOT.parent
L3_SRC = REPO_ROOT / "Layer3_JcvPCA" / "src"
if str(L3_SRC) not in sys.path:
    sys.path.insert(0, str(L3_SRC))

from layer3_jcvpca.analysis_service import AnalysisIdentity, AnalysisParams  # noqa: E402
from layer3_jcvpca.app_controller import DEFAULT_PATHS, Layer3AnalysisController  # noqa: E402
from layer3_jcvpca.matrix_stability import MatrixStabilityParams  # noqa: E402
from layer3_jcvpca import viz  # noqa: E402

st.set_page_config(page_title="Layer 3 JcvPCA", layout="wide")


def _css() -> None:
    st.markdown(
        """
        <style>
          .verdict-blocking { color: #b00020; font-weight: 700; }
          .verdict-warning { color: #d35400; font-weight: 700; }
          .verdict-pass { color: #2e7d32; font-weight: 700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _status_badge(status: str) -> str:
    cls = {"blocking": "verdict-blocking", "warning": "verdict-warning", "pass": "verdict-pass"}.get(
        status, ""
    )
    return f'<span class="{cls}">{status.upper()}</span>'


def _init() -> Layer3AnalysisController:
    if "l3_ctrl" not in st.session_state:
        st.session_state.l3_ctrl = Layer3AnalysisController(repo_root=REPO_ROOT)
    return st.session_state.l3_ctrl


def main() -> None:
    _css()
    ctrl = _init()
    st.title("Layer 3 JcvPCA Analysis")
    st.caption(
        "JcvPCA-style comparison using Layer 2.5 window matrices. "
        "Calibration test — not a final scientific result."
    )

    # --- Section 1: Analysis identity ---
    st.header("1. Analysis identity")
    c1, c2, c3 = st.columns(3)
    analysis_id = c1.text_input("analysis_id", value="671_g4_validation_001")
    participant_id = c2.text_input("participant_id", value="671")
    task_group = c3.text_input("task_group", value="Group4")
    exercise_name = st.text_input("exercise / window label", value="g4_upper_body_pilot")
    analysis_type = st.selectbox(
        "analysis_type",
        ["single_window_validation", "single_exercise", "accumulated_exercise", "natural_variability"],
    )
    notes = st.text_area("notes", value="First Layer 3 validation: T1R1 vs T2R2; NV T1R1 vs T1R2.")

    # --- Section 2: Input windows ---
    st.header("2. Input windows")
    paths = {}
    for role, default in DEFAULT_PATHS.items():
        default_path = REPO_ROOT / default
        paths[role] = st.text_input(
            f"{role} matrix path",
            value=str(default_path),
            help="Path to window_jvcpca_matrix.parquet",
        )
        exists = Path(paths[role]).expanduser().is_file()
        st.caption(f"{'Found' if exists else 'NOT FOUND'}: `{paths[role]}`")

    if st.button("Load & validate windows", type="primary"):
        try:
            report = ctrl.load_preflight(paths)
            st.session_state.l3_preflight = report
            st.session_state.warnings_ack = False
            if report.windows:
                st.success(f"Preflight complete — loaded {len(report.windows)} window(s). Status: {report.status}")
            else:
                st.error(
                    "Preflight finished but no matrices loaded. Check paths above (file must exist). "
                    "See blocking checks below."
                )
        except Exception as exc:
            st.error(str(exc))

    # Keep report on controller after Streamlit reruns
    if st.session_state.get("l3_preflight") is not None:
        ctrl.preflight_report = st.session_state.l3_preflight

    if ctrl.preflight_report:
        st.subheader("Loaded windows")
        win_df = ctrl.windows_table()
        if win_df.empty:
            st.warning("No windows loaded. All four matrix paths must point to existing .parquet files.")
        else:
            st.dataframe(win_df, use_container_width=True, hide_index=True)

        # --- Section 3: Preflight ---
        st.header("3. Preflight validation")
        st.markdown(f"Overall: {_status_badge(ctrl.preflight_report.status)}", unsafe_allow_html=True)
        checks_df = ctrl.checks_table()
        if not checks_df.empty:
            st.dataframe(checks_df, use_container_width=True, hide_index=True)
        blocking = checks_df[checks_df["status"] == "blocking"] if not checks_df.empty else checks_df
        if not blocking.empty:
            st.error("Blocking issues:\n" + "\n".join(f"- {m}" for m in blocking["message"]))

        a_stab = ctrl.preflight_report.stability.get("A") if ctrl.preflight_report.stability else None

        # --- Section 4: Matrix Stability / PCA Readiness ---
        st.header("4. Matrix Stability / PCA Readiness")
        st.info(
            "Matrix Stability / PCA Readiness indicates whether the selected window is "
            "numerically suitable for PCA/JcvPCA and whether the reference PCA space appears fragile. "
            "It does not establish statistical significance or biological meaning by itself. "
            "A weak A/reference matrix can produce a mathematically valid but unstable JcvPCA comparison."
        )
        stab_df = ctrl.stability_table()
        if not stab_df.empty:
            st.dataframe(stab_df, use_container_width=True, hide_index=True)
            if a_stab:
                st.markdown("### A/reference PCA readiness")
                st.markdown(_status_badge(a_stab.status), unsafe_allow_html=True)
                m = a_stab.metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("rank", m.get("matrix_rank", "—"))
                m2.metric("condition #", f"{m.get('condition_number', 0):.2e}" if m.get("condition_number") else "—")
                m3.metric("dominant PC %", m.get("dominant_pc_variance_percent", "—"))
                m4.metric("frame/feature", m.get("frame_to_feature_ratio", "—"))

        # --- Section 5: Parameters ---
        st.header("5. Parameters")
        p1, p2, p3 = st.columns(3)
        ctrl.analysis_params.pc_selection_mode = p1.selectbox(
            "PC selection mode", ["project_default", "cumulative_variance", "fixed_n"]
        )
        ctrl.analysis_params.cumulative_variance_threshold = p2.selectbox(
            "cumulative variance threshold", [0.80, 0.85, 0.90, 0.95], index=2
        )
        if ctrl.analysis_params.pc_selection_mode == "fixed_n":
            ctrl.analysis_params.n_pcs = p3.number_input("number_of_pcs", min_value=1, value=3)
        ctrl.stability_params.near_zero_variance_threshold = st.number_input(
            "near_zero_variance_threshold", value=1e-8, format="%.0e"
        )
        ctrl.stability_params.min_frames_per_feature_ratio = st.number_input(
            "min_frames_per_feature_ratio", value=5.0
        )
        ctrl.stability_params.pc_dominance_warning_threshold = st.number_input(
            "pc_dominance_warning_threshold", value=0.80
        )
        ctrl.stability_params.split_half_stability_check = st.checkbox(
            "split_half_stability_check", value=True
        )
        st.caption(
            "Method (fixed): center A and B independently; PCA on A only; "
            "no z-score; JcvPCA = abs(B)-abs(A); RSS link aggregation."
        )

        # --- Section 6: Pre-run plots ---
        st.header("6. Pre-run exploratory plots")
        if win_df.empty:
            st.info("Load valid window matrices to see pre-run plots.")
        else:
            loaded = {w.role: w for w in ctrl.preflight_report.windows}
            feats = ctrl.preflight_report.feature_names
            if a_stab and a_stab.feature_variance_table is not None:
                st.pyplot(viz.plot_feature_variance(a_stab.feature_variance_table))
            if a_stab and a_stab.joint_variance_table is not None:
                st.pyplot(viz.plot_joint_variance(a_stab.joint_variance_table))
            if a_stab and a_stab.singular_value_table is not None:
                st.pyplot(viz.plot_singular_values(a_stab.singular_value_table))
            if "A" in loaded:
                st.pyplot(viz.plot_motion_energy(loaded["A"].df, feats))
                st.pyplot(viz.plot_qc_timeline(loaded["A"].manifest))
            if a_stab and "A" in loaded and feats:
                from layer3_jcvpca.core import select_selected_m_from_A

                _, evr_table = select_selected_m_from_A(
                    loaded["A"].df, feats, ctrl.analysis_params.cumulative_variance_threshold
                )
                evr = evr_table["explained_variance_ratio"].to_numpy()
                st.pyplot(viz.plot_scree(evr))
                st.pyplot(viz.plot_cumulative_variance(evr))

        # Warnings acknowledgment
        if not win_df.empty:
            if ctrl.preflight_report.status == "warning":
                st.session_state.warnings_ack = st.checkbox(
                    "I acknowledge matrix-stability / QC warnings and wish to proceed.",
                    value=st.session_state.get("warnings_ack", False),
                )
                ctrl.warnings_acknowledged = st.session_state.warnings_ack
            else:
                ctrl.warnings_acknowledged = True
        else:
            ctrl.warnings_acknowledged = False

        # --- Section 7: Run ---
        st.header("7. Run analysis")
        can_run, run_msg = ctrl.can_run()
        st.write(run_msg)
        output_dir = st.text_input(
            "output directory",
            value=str(ctrl.default_output_dir(analysis_id)),
        )
        if st.button("Run JcvPCA analysis", disabled=not can_run, type="primary"):
            identity = AnalysisIdentity(
                analysis_id=analysis_id,
                participant_id=participant_id,
                task_group=task_group,
                exercise_name=exercise_name,
                analysis_type=analysis_type,
                notes=notes,
            )
            try:
                result = ctrl.run_analysis(identity, output_dir)
                st.success(f"Analysis complete: {result.output_dir}")
            except Exception as exc:
                st.error(str(exc))

        # --- Sections 8–10: Results ---
        if ctrl.analysis_result:
            r = ctrl.analysis_result
            st.header("8. Results overview")
            st.json(r.manifest)
            c1, c2, c3 = st.columns(3)
            c1.metric("selected PCs", r.selected_m)
            c2.metric("PC selection", r.pc_selection_reason)
            c3.metric("output", r.output_dir)

            st.header("9. Result plots")
            plots_dir = Path(r.output_dir) / "plots"
            if plots_dir.is_dir():
                for png in sorted(plots_dir.glob("*.png")):
                    st.image(str(png), caption=png.name)

            st.header("10. Distribution / democracy (exploratory)")
            dm = r.distribution_metrics
            if dm:
                st.write(
                    {
                        k: dm[k]
                        for k in (
                            "normalized_entropy",
                            "gini_coefficient",
                            "top1_joint_share",
                            "top3_joint_share",
                            "effective_number_of_joints",
                        )
                        if k in dm
                    }
                )
                st.caption("Descriptive motor-control evidence only — not a validated clinical endpoint.")

            st.header("11. Result tables")
            for name, df in r.tables.items():
                st.subheader(name)
                st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
