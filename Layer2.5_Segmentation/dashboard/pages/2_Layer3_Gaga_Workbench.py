"""Layer 3 Gaga JcvPCA Workbench — Phase 0–2: diagnostics, inventory, export readiness."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

L25_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = L25_ROOT.parent
L25_SRC = L25_ROOT / "src"
L3_SRC = REPO_ROOT / "Layer3_JcvPCA" / "src"
if str(L25_SRC) not in sys.path:
    sys.path.insert(0, str(L25_SRC))
if str(L3_SRC) not in sys.path:
    sys.path.insert(0, str(L3_SRC))

from layer3_jcvpca.diagnostics import collect_diagnostics  # noqa: E402
from layer3_jcvpca.inventory import (  # noqa: E402
    default_layer25_root,
    scan_layer25_exports,
    write_inventory_artifacts,
)
from layer3_jcvpca.comparable_links import (  # noqa: E402
    COMPARABILITY_BLOCKING,
    COMPARABILITY_PASS,
    COMPARABILITY_WARNING,
    detect_comparable_links,
    load_central_manifest,
    select_manifest_rows,
    validate_manual_link_selection,
    write_comparability_artifacts,
)
from layer3_jcvpca.dataset_builder import (  # noqa: E402
    ANALYSIS_MODE_EXPLORATORY,
    ANALYSIS_MODE_LONGITUDINAL,
    CONSTRUCTION_BLOCKING,
    CONSTRUCTION_PASS,
    CONSTRUCTION_WARNING,
    PRESET_ALL_P1_P5,
    PRESET_CUSTOM,
    PRESET_P1_P2,
    PRESET_P3_P4_P5,
    DatasetConstructionConfig,
    DatasetSideSpec,
    build_dataset_construction_preview,
    build_upstream_fingerprint,
    resolve_exercise_labels,
    write_dataset_construction_artifacts,
)
from layer3_jcvpca.workbench_preflight import (  # noqa: E402
    PREFLIGHT_BLOCKING,
    PREFLIGHT_PASS,
    PREFLIGHT_WARNING,
    bundle_from_construction_result,
    run_workbench_preflight,
    save_preflight_acknowledgment,
    write_workbench_preflight_artifacts,
)
from layer3_jcvpca.jcvpca_trace import (  # noqa: E402
    DEFAULT_MAX_PCS,
    DEFAULT_MIN_PCS,
    DEFAULT_VARIANCE_THRESHOLD,
    PcaAParameters,
    SELECTED_M_MODE_AUTO,
    SELECTED_M_MODE_MANUAL,
    validate_selected_m_workbench,
)
from layer3_jcvpca.pc_focus import (  # noqa: E402
    PC_FOCUS_ALL,
    PC_FOCUS_FUNCTIONAL,
    PC_FOCUS_MANUAL,
    PC_FOCUS_MODES,
    PC_FOCUS_NULL_SPACE,
    PcFocusParameters,
    validate_pc_focus_parameters,
)
from layer3_jcvpca.step_runner import (  # noqa: E402
    Phase6RunContext,
    StepRunError,
    initialize_run_state,
    run_step,
)
from layer3_jcvpca.workbench_pca_stability import (
    check_pca_stability_gate,
    save_pca_stability_acknowledgment,
)
from layer3_jcvpca.workbench_jcvpca_runner import WeightingParameters
from layer3_jcvpca.workbench_state import (  # noqa: E402
    PHASE6_STEP_ORDER,
    STEP_6A_LOAD,
    STEP_6B_RAW_PREVIEW,
    STEP_6C_CENTERING,
    STEP_7A_PCA_A,
    STEP_9A_PC_FOCUS,
    STEP_10A_B_PROJECTION,
    STEP_11A_PCA_B,
    STEP_12A_REEXPRESS,
    STEP_13A_AXIS_JCVPCA,
    STEP_14A_RSS,
    STEP_15A_WEIGHTING,
    STEP_16A_NV,
    STEP_17A_EXPLORATORY,
    STEP_18A_EXPORT,
    WORKBENCH_STEP_ORDER,
    STEP_COMPLETED,
    STEP_DISPLAY_NAMES,
    check_phase6_gate,
    ensure_workbench_step_registry,
    load_run_state,
    sync_upstream_invalidation,
)
from pre_jvcpca_review.app_controller import PreJcvpcaReviewController  # noqa: E402
from pre_jvcpca_review.exercise_segments import (  # noqa: E402
    EXPORT_GRANULARITY_COMBINED,
    EXPORT_GRANULARITY_PER_EXERCISE,
    GAGA_EXERCISE_LABELS,
)
from pre_jvcpca_review.layer3_export_manifest import (  # noqa: E402
    ATTEMPT_STATUS_FAILED,
    ATTEMPT_STATUS_SKIPPED,
    CENTRAL_MANIFEST_FILENAME,
    READINESS_BLOCKING,
    READINESS_PASS,
    READINESS_WARNING,
    SESSION_STATUS_FAILED,
    SESSION_STATUS_SKIPPED,
    SESSION_STATUS_SUCCESSFUL,
    build_export_readiness_report,
    build_session_coverage_diff,
    central_manifest_path,
    export_attempts_report_path,
    load_export_attempts_report,
    load_layer25_export_manifest,
    session_coverage_report_path,
)

st.set_page_config(page_title="Gaga JcvPCA Workbench", layout="wide")


def _css() -> None:
    st.markdown(
        """
        <style>
          .diag-ok { color: #2e7d32; font-weight: 600; }
          .diag-fail { color: #b00020; font-weight: 600; }
          .phase-disabled { color: #757575; }
          .readiness-pass { color: #2e7d32; font-weight: 600; }
          .readiness-warning { color: #d35400; font-weight: 600; }
          .readiness-blocking { color: #b00020; font-weight: 600; }
          .missing-label { color: #b00020; font-weight: 700; }
          .present-label { color: #2e7d32; font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _status(ok: bool) -> str:
    return "OK" if ok else "FAILED"


def _render_diagnostics() -> None:
    st.header("0. Implementation status / diagnostics")
    diag = collect_diagnostics(REPO_ROOT)

    c1, c2, c3 = st.columns(3)
    c1.metric("Layer 3 import", _status(diag["layer3_import_ok"]))
    c2.metric("Layer 2.5 import", _status(diag["pre_jvcpca_import_ok"]))
    c3.metric("L2.5 manifests found", diag["layer25_manifest_count"])

    with st.expander("Diagnostics detail", expanded=False):
        st.json(diag)

    st.caption(f"Run tests: `{diag['pytest_command']}`")

    st.subheader("Workbench feature availability")
    features = diag["workbench_features"]
    for name, enabled in features.items():
        label = name.replace("_", " ")
        if enabled:
            st.markdown(f"- **{label}**: enabled")
        else:
            st.markdown(f"- <span class='phase-disabled'>{label}: not yet implemented</span>", unsafe_allow_html=True)


def _filter_inventory(df, filters: dict) -> "pd.DataFrame":
    import pandas as pd

    if df.empty:
        return df
    out = df.copy()
    for col, val in filters.items():
        if val and val != "(all)" and col in out.columns:
            out = out[out[col].astype(str) == str(val)]
    return out


def _render_inventory() -> None:
    st.header("1. Layer 2.5 data inventory")

    default_root = default_layer25_root(REPO_ROOT)
    scan_root = st.text_input(
        "Layer 2.5 scan root",
        value=str(default_root),
        help="Directory to scan for window_export_manifest.json files",
    )
    artifact_dir = st.text_input(
        "Inventory artifact output directory",
        value=str(REPO_ROOT / "Layer3_JcvPCA" / "outputs" / "_workbench_inventory_preview"),
    )

    if st.button("Rescan Layer 2.5 exports", type="primary"):
        inventory = scan_layer25_exports(scan_root)
        st.session_state.workbench_inventory = inventory
        try:
            paths = write_inventory_artifacts(inventory, artifact_dir)
            st.session_state.inventory_artifact_paths = {k: str(v) for k, v in paths.items()}
            st.success("Scan complete. Artifacts written.")
        except Exception as exc:
            st.error(f"Scan succeeded but artifact write failed: {exc}")

    inventory = st.session_state.get("workbench_inventory")
    if inventory is None:
        inventory = scan_layer25_exports(scan_root)
        st.session_state.workbench_inventory = inventory

    summary = inventory.summary()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Inventory rows", summary["n_inventory_rows"])
    m2.metric("Issues", summary["n_issues"])
    m3.metric("Per-exercise P1–P5", summary["per_exercise_export_count"])
    m4.metric("Combined Group4", summary["combined_group4_count"])
    m5.metric("Participants", len(summary["participants"]))

    st.caption(
        "Note: `P1` in session IDs like `671_T1_P1_R1` is Gaga Task Part 1 (`part_id`), "
        "not Gaga exercise P1. Exercise column refers to movement exercises P1–P5 only."
    )

    inv_df = inventory.to_dataframe()
    issues_df = inventory.issues_dataframe()

    st.subheader("Filters")
    f1, f2, f3, f4, f5, f6 = st.columns(6)
    participants = ["(all)"] + summary["participants"]
    timepoints = ["(all)"] + summary["timepoints"]
    repetitions = ["(all)"] + summary["repetitions"]
    exercises = ["(all)"] + summary.get("gaga_exercises_found", []) + ["combined_group4", "(empty)"]
    qc_values = ["(all)"]
    if not inv_df.empty and "qc_status" in inv_df.columns:
        qc_values += sorted(inv_df["qc_status"].dropna().unique().tolist())
    safe_values = ["(all)"]
    if not inv_df.empty and "layer3_safe" in inv_df.columns:
        safe_values += sorted(inv_df["layer3_safe"].dropna().unique().tolist())

    filt_participant = f1.selectbox("Participant", participants, key="inv_f_participant")
    filt_timepoint = f2.selectbox("Timepoint", timepoints, key="inv_f_timepoint")
    filt_repetition = f3.selectbox("Repetition", repetitions, key="inv_f_repetition")
    filt_exercise = f4.selectbox("Gaga exercise label", exercises, key="inv_f_exercise")
    filt_qc = f5.selectbox("QC status", qc_values, key="inv_f_qc")
    filt_safe = f6.selectbox("layer3_safe", safe_values, key="inv_f_safe")

    filters = {
        "participant_id": None if filt_participant == "(all)" else filt_participant,
        "timepoint": None if filt_timepoint == "(all)" else filt_timepoint,
        "repetition": None if filt_repetition == "(all)" else filt_repetition,
        "gaga_exercise_label": "" if filt_exercise == "(empty)" else (None if filt_exercise == "(all)" else filt_exercise),
        "qc_status": None if filt_qc == "(all)" else filt_qc,
        "layer3_safe": None if filt_safe == "(all)" else filt_safe,
    }
    filtered = _filter_inventory(inv_df, {k: v for k, v in filters.items() if v is not None})

    st.subheader("Inventory table")
    display_cols = [
        "participant_id",
        "timepoint",
        "repetition",
        "task_part_id",
        "gaga_exercise_label",
        "export_granularity",
        "session_id",
        "n_frames",
        "n_features",
        "layer3_safe",
        "qc_status",
        "notes",
    ]
    show_cols = [c for c in display_cols if c in filtered.columns]
    st.dataframe(filtered[show_cols] if not filtered.empty else filtered, use_container_width=True, hide_index=True)

    st.subheader("Inventory issues")
    if issues_df.empty:
        st.info("No issues reported.")
    else:
        issue_filter = st.multiselect(
            "Filter by issue code",
            sorted(issues_df["issue_code"].unique().tolist()),
            default=sorted(issues_df["issue_code"].unique().tolist()),
        )
        show_issues = issues_df[issues_df["issue_code"].isin(issue_filter)] if issue_filter else issues_df
        st.dataframe(show_issues, use_container_width=True, hide_index=True)

        st.markdown("**Issue counts**")
        st.dataframe(
            show_issues.groupby(["issue_code", "severity"]).size().reset_index(name="count"),
            hide_index=True,
            use_container_width=True,
        )

    artifact_paths = st.session_state.get("inventory_artifact_paths")
    if artifact_paths:
        st.subheader("Saved artifacts")
        for name, path in artifact_paths.items():
            st.code(f"{name}: {path}")


def _partial_dataset_banner() -> None:
    st.info(
        "Partial dataset: participant 671 only; available sessions T1R1, T1R2, T2R2; "
        "missing T2R1 and T3; qc_status=warning."
    )


def _readiness_class(status: str) -> str:
    if status == READINESS_PASS:
        return "readiness-pass"
    if status == READINESS_BLOCKING:
        return "readiness-blocking"
    return "readiness-warning"


def _comparability_class(status: str) -> str:
    if status == COMPARABILITY_PASS:
        return "readiness-pass"
    if status == COMPARABILITY_BLOCKING:
        return "readiness-blocking"
    return "readiness-warning"


def _p_coverage_grid(manifest_df: pd.DataFrame) -> pd.DataFrame:
    if manifest_df.empty:
        return pd.DataFrame(
            columns=[
                "participant_id",
                "timepoint",
                "repetition",
                "session_id",
                "combined_group4",
                *GAGA_EXERCISE_LABELS,
                "readiness_status",
                "missing_gaga_labels",
            ]
        )

    readiness = build_export_readiness_report(manifest_df)
    rows: list[dict[str, object]] = []
    group_cols = ["participant_id", "timepoint", "repetition", "session_id"]
    for key, group in manifest_df.groupby(group_cols, dropna=False):
        participant_id, timepoint, repetition, session_id = key
        session_pe = group[group["export_granularity"] == EXPORT_GRANULARITY_PER_EXERCISE]
        pe_labels = set(session_pe["gaga_exercise_label"].astype(str).tolist())
        has_combined = (group["export_granularity"] == EXPORT_GRANULARITY_COMBINED).any() or (
            "combined_group4" in group["gaga_exercise_label"].astype(str).tolist()
        )
        row: dict[str, object] = {
            "participant_id": participant_id,
            "timepoint": timepoint,
            "repetition": repetition,
            "session_id": session_id,
            "combined_group4": "yes" if has_combined else "no",
        }
        for label in GAGA_EXERCISE_LABELS:
            row[label] = "yes" if label in pe_labels else "MISSING"
        match = readiness[
            (readiness["participant_id"] == participant_id)
            & (readiness["timepoint"] == timepoint)
            & (readiness["repetition"] == repetition)
            & (readiness["session_id"] == session_id)
        ]
        if not match.empty:
            row["readiness_status"] = match.iloc[0]["readiness_status"]
            row["missing_gaga_labels"] = match.iloc[0]["missing_gaga_labels"]
        else:
            row["readiness_status"] = READINESS_WARNING
            row["missing_gaga_labels"] = ",".join(
                label for label in GAGA_EXERCISE_LABELS if label not in pe_labels
            )
        rows.append(row)
    return pd.DataFrame(rows)


def _render_export_readiness() -> None:
    st.header("2. Export readiness (Phase 2 / 2.5)")
    _partial_dataset_banner()

    default_root = default_layer25_root(REPO_ROOT)
    output_root = Path(
        st.text_input(
            "Layer 2.5 output root",
            value=str(default_root),
            key="export_output_root",
        )
    )
    manifest_path = central_manifest_path(output_root)
    attempts_path = export_attempts_report_path(output_root)
    coverage_path = session_coverage_report_path(output_root)
    st.caption(
        f"Central manifest: `{manifest_path}` · attempts: `{attempts_path}` · "
        f"coverage: `{coverage_path}`"
    )

    if "gaga_controller" not in st.session_state:
        st.session_state.gaga_controller = PreJcvpcaReviewController(L25_ROOT)

    controller: PreJcvpcaReviewController = st.session_state.gaga_controller
    segments_path = controller.default_exercise_segments
    st.text_input(
        "Default exercise segmentation file (671 pilot)",
        value=str(segments_path),
        disabled=True,
        help="Participant-specific workbooks live under Layer2.5_Segmentation/segmentation/.",
    )

    c1, c2, c3 = st.columns(3)
    export_combined = c1.checkbox("Export combined_group4", value=True, key="export_combined")
    export_per_exercise = c2.checkbox("Export per-exercise P1–P5", value=True, key="export_per_exercise")
    allow_nan = c3.checkbox("Allow NaN matrix", value=False, key="export_allow_nan")

    participant_options = ["(all)"]
    if controller.session_index is None:
        try:
            controller.discover(
                controller.default_layer1_root,
                controller.default_layer2_root,
                output_root,
            )
        except Exception:
            pass
    if controller.session_index is not None and not controller.session_index.empty:
        participant_options += sorted(controller.session_index["participant_id"].unique().tolist())
    selected_participants = st.multiselect(
        "Limit batch export to participant(s)",
        participant_options[1:] or participant_options,
        help="Leave empty to export all discovered participants.",
    )

    if st.button("Run Gaga batch export + write manifest", type="primary", key="run_gaga_batch"):
        try:
            summary = controller.run_gaga_batch_export(
                output_root=output_root,
                participant_ids=selected_participants or None,
                allow_nan_matrix=allow_nan,
                export_combined=export_combined,
                export_per_exercise=export_per_exercise,
            )
            st.session_state.central_manifest_df = pd.DataFrame(summary.manifest_rows)
            st.session_state.export_attempts_df = pd.DataFrame(summary.attempt_rows)
            st.session_state.session_coverage_df = pd.read_csv(summary.session_coverage_report_path)
            st.session_state.export_readiness_paths = {
                **summary.readiness_paths,
                "attempts": summary.attempts_report_path,
                "session_coverage": summary.session_coverage_report_path,
            }
            st.success(
                f"Batch export complete. Manifest rows={len(summary.manifest_rows)}, "
                f"attempt rows={len(summary.attempt_rows)}."
            )
        except Exception as exc:
            st.error(f"Batch export failed: {exc}")

    if st.button("Reload export reports", key="reload_central_manifest"):
        st.session_state.central_manifest_df = load_layer25_export_manifest(manifest_path)
        st.session_state.export_attempts_df = load_export_attempts_report(attempts_path)
        if coverage_path.is_file():
            st.session_state.session_coverage_df = pd.read_csv(coverage_path)

    manifest_df = st.session_state.get("central_manifest_df")
    if manifest_df is None:
        manifest_df = load_layer25_export_manifest(manifest_path)
        st.session_state.central_manifest_df = manifest_df

    attempts_df = st.session_state.get("export_attempts_df")
    if attempts_df is None:
        attempts_df = load_export_attempts_report(attempts_path)
        st.session_state.export_attempts_df = attempts_df

    coverage_df = st.session_state.get("session_coverage_df")
    if coverage_df is None and coverage_path.is_file():
        coverage_df = pd.read_csv(coverage_path)
        st.session_state.session_coverage_df = coverage_df
    if coverage_df is None and controller.session_index is not None:
        from pre_jvcpca_review.exercise_segments import load_merged_exercise_catalog

        participants = selected_participants or sorted(
            controller.session_index["participant_id"].unique().tolist()
        )
        catalog, _ = load_merged_exercise_catalog(L25_ROOT, participants)
        coverage_df = build_session_coverage_diff(
            session_index=controller.session_index,
            exercise_catalog=catalog,
            manifest_df=manifest_df,
            attempts_df=attempts_df,
            participant_ids=participants,
            project_root=L25_ROOT,
        )
        st.session_state.session_coverage_df = coverage_df

    readiness_df = build_export_readiness_report(manifest_df)
    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric("Manifest rows", len(manifest_df))
    r2.metric("Expected sessions", len(coverage_df) if coverage_df is not None else 0)
    r3.metric(
        "Successful sessions",
        int((coverage_df["session_status"] == SESSION_STATUS_SUCCESSFUL).sum())
        if coverage_df is not None and not coverage_df.empty
        else 0,
    )
    r4.metric(
        "Skipped / failed sessions",
        int(
            coverage_df["session_status"].isin(
                [SESSION_STATUS_SKIPPED, SESSION_STATUS_FAILED]
            ).sum()
        )
        if coverage_df is not None and not coverage_df.empty
        else 0,
    )
    r5.metric(
        "Pass readiness (manifest)",
        int((readiness_df["readiness_status"] == READINESS_PASS).sum())
        if not readiness_df.empty
        else 0,
    )

    st.subheader("Attempted session coverage")
    if coverage_df is None or coverage_df.empty:
        st.info("No session coverage report available. Run batch export or reload reports.")
    else:
        st.dataframe(coverage_df, use_container_width=True, hide_index=True)

    failed_skipped = pd.DataFrame()
    if coverage_df is not None and not coverage_df.empty:
        failed_skipped = coverage_df[
            coverage_df["session_status"].isin([SESSION_STATUS_SKIPPED, SESSION_STATUS_FAILED])
        ]
    if attempts_df is not None and not attempts_df.empty:
        attempt_problems = attempts_df[
            attempts_df["status"].isin([ATTEMPT_STATUS_SKIPPED, ATTEMPT_STATUS_FAILED])
        ]
    else:
        attempt_problems = pd.DataFrame()

    st.subheader("Failed / skipped sessions")
    if failed_skipped.empty and attempt_problems.empty:
        st.success("No skipped or failed sessions in the coverage report.")
    else:
        if not failed_skipped.empty:
            st.markdown("**Session rollup**")
            show_session = [
                "session_id",
                "session_status",
                "reason_code",
                "reason_message",
                "source_dependency",
                "warning_file",
                "combined_group4",
                "P1",
                "P2",
                "P3",
                "P4",
                "P5",
            ]
            st.dataframe(
                failed_skipped[[c for c in show_session if c in failed_skipped.columns]],
                use_container_width=True,
                hide_index=True,
            )
        if not attempt_problems.empty:
            st.markdown("**Per-export attempts (skipped / failed)**")
            show_attempts = [
                "session_id",
                "export_label",
                "status",
                "reason_code",
                "reason_message",
                "source_dependency",
                "warning_file",
                "artifact_path",
            ]
            st.dataframe(
                attempt_problems[[c for c in show_attempts if c in attempt_problems.columns]],
                use_container_width=True,
                hide_index=True,
            )

    st.subheader("Per-exercise coverage (manifest only)")
    if manifest_df.empty:
        st.warning("No manifest export rows yet.")
    else:
        coverage = _p_coverage_grid(manifest_df)
        st.dataframe(coverage, use_container_width=True, hide_index=True)

    combined_df = manifest_df[
        manifest_df["export_granularity"] == EXPORT_GRANULARITY_COMBINED
    ] if not manifest_df.empty else manifest_df
    per_exercise_df = manifest_df[
        manifest_df["export_granularity"] == EXPORT_GRANULARITY_PER_EXERCISE
    ] if not manifest_df.empty else manifest_df

    show_cols = [
        "participant_id",
        "timepoint",
        "repetition",
        "session_id",
        "gaga_exercise_label",
        "export_granularity",
        "layer3_safe",
        "qc_status",
        "n_frames",
        "matrix_path",
    ]

    st.subheader("Manifest exports — combined Group4")
    st.dataframe(
        combined_df[[c for c in show_cols if c in combined_df.columns]]
        if not combined_df.empty
        else combined_df,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Manifest exports — per-exercise P1–P5")
    st.dataframe(
        per_exercise_df[[c for c in show_cols if c in per_exercise_df.columns]]
        if not per_exercise_df.empty
        else per_exercise_df,
        use_container_width=True,
        hide_index=True,
    )

    if not readiness_df.empty:
        st.subheader("Manifest readiness summary")
        for _, row in readiness_df.iterrows():
            status = str(row["readiness_status"])
            st.markdown(
                f"- **{row['session_id']}**: "
                f"<span class='{_readiness_class(status)}'>{status}</span> — "
                f"{row['readiness_message']}",
                unsafe_allow_html=True,
            )

    artifact_paths = st.session_state.get("export_readiness_paths")
    if artifact_paths:
        st.subheader("Report paths")
        for name, path in artifact_paths.items():
            st.code(f"{name}: {path}")


def _render_comparable_links() -> None:
    st.header("3. Comparable links / joints (Phase 3)")
    _partial_dataset_banner()
    st.caption(
        "Detect which joint links are comparable across selected export matrices before any analysis. "
        "No harmonization, renaming, or dataset construction in this phase."
    )

    default_root = default_layer25_root(REPO_ROOT)
    l25_root = Path(
        st.text_input(
            "Layer 2.5 manifest root",
            value=str(default_root),
            key="comparability_manifest_root",
        )
    )
    artifact_dir = Path(
        st.text_input(
            "Comparability artifact output directory",
            value=str(REPO_ROOT / "Layer3_JcvPCA" / "outputs" / "_workbench_comparability"),
            key="comparability_artifact_dir",
        )
    )

    manifest_df = load_central_manifest(l25_root)
    if manifest_df.empty:
        st.warning(f"No `{CENTRAL_MANIFEST_FILENAME}` found under {l25_root}.")
        return

    participants = sorted(manifest_df["participant_id"].dropna().unique().tolist())
    timepoints = sorted(manifest_df["timepoint"].dropna().unique().tolist())
    repetitions = sorted(manifest_df["repetition"].dropna().unique().tolist())
    exercise_options = sorted(
        {
            str(x)
            for x in manifest_df["gaga_exercise_label"].dropna().unique().tolist()
            if str(x)
        }
    )
    granularity_options = sorted(manifest_df["export_granularity"].dropna().unique().tolist())

    f1, f2, f3, f4, f5 = st.columns(5)
    sel_participants = f1.multiselect("Participant", participants, default=["671"] if "671" in participants else participants)
    sel_timepoints = f2.multiselect("Timepoints", timepoints, default=timepoints)
    sel_repetitions = f3.multiselect("Repetitions", repetitions, default=repetitions)
    sel_exercises = f4.multiselect(
        "Gaga exercises",
        exercise_options,
        default=[e for e in ["P1"] if e in exercise_options] or exercise_options,
    )
    sel_granularity = f5.multiselect(
        "export_granularity",
        granularity_options,
        default=[g for g in ["per_exercise"] if g in granularity_options] or granularity_options,
    )

    selected_rows = select_manifest_rows(
        manifest_df,
        participant_ids=sel_participants or None,
        timepoints=sel_timepoints or None,
        repetitions=sel_repetitions or None,
        gaga_exercise_labels=sel_exercises or None,
        export_granularities=sel_granularity or None,
    )

    st.subheader("Selected matrices for comparability")
    preview_cols = [
        "session_id",
        "gaga_exercise_label",
        "export_granularity",
        "n_frames",
        "n_features",
        "feature_schema_id",
        "layer3_safe",
        "qc_status",
        "matrix_path",
    ]
    st.dataframe(
        selected_rows[[c for c in preview_cols if c in selected_rows.columns]]
        if not selected_rows.empty
        else selected_rows,
        use_container_width=True,
        hide_index=True,
    )

    if st.button("Detect comparable links", type="primary", key="detect_comparable_links"):
        if selected_rows.empty:
            st.error("Select at least one manifest row.")
        else:
            report = detect_comparable_links(selected_rows)
            paths = write_comparability_artifacts(report, artifact_dir)
            st.session_state.comparability_report = report
            st.session_state.comparability_paths = {k: str(v) for k, v in paths.items()}
            st.session_state.selected_comparable_links = list(report.comparable_link_stems)
            st.success(
                f"Detected {report.summary['n_comparable_links']} comparable links "
                f"across {report.summary['n_selected_matrices']} matrices."
            )

    report = st.session_state.get("comparability_report")
    if report is None and not selected_rows.empty:
        report = detect_comparable_links(selected_rows)
        st.session_state.comparability_report = report

    if report is None:
        return

    summary = report.summary
    status = str(summary.get("comparability_status", COMPARABILITY_WARNING))
    st.markdown(
        f"Comparability status: "
        f"<span class='{_comparability_class(status)}'>{status}</span> — "
        f"{summary.get('n_comparable_links', 0)} comparable / "
        f"{summary.get('n_excluded_links', 0)} excluded link issues",
        unsafe_allow_html=True,
    )

    comparable_df = report.comparable_links
    excluded_df = report.excluded_links

    st.subheader("Comparable links")
    if comparable_df.empty:
        st.warning("No links detected.")
    else:
        show_comp = comparable_df[comparable_df["comparable"]]
        st.dataframe(show_comp, use_container_width=True, hide_index=True)

    st.subheader("Excluded links")
    if excluded_df.empty:
        st.success("No excluded links.")
    else:
        st.dataframe(excluded_df, use_container_width=True, hide_index=True)

    comparable_stems = report.comparable_link_stems
    if comparable_stems:
        default_selection = st.session_state.get("selected_comparable_links", comparable_stems)
        default_selection = [s for s in default_selection if s in comparable_stems]
        chosen = st.multiselect(
            "Manual subset (comparable links only)",
            comparable_stems,
            default=default_selection or comparable_stems,
            key="manual_comparable_links",
        )
        try:
            validate_manual_link_selection(chosen, comparable_stems)
            st.session_state.selected_comparable_links = chosen
            st.caption(f"Selected {len(chosen)} comparable link(s) for future phases.")
        except ValueError as exc:
            st.error(str(exc))
    else:
        st.warning("No comparable links available for manual selection.")

    with st.expander("Feature triplet report", expanded=False):
        st.dataframe(report.feature_triplet_report, use_container_width=True, hide_index=True)

    comp_paths = st.session_state.get("comparability_paths")
    if comp_paths:
        st.subheader("Comparability artifact paths")
        for name, path in comp_paths.items():
            st.code(f"{name}: {path}")


def _construction_class(status: str) -> str:
    if status == CONSTRUCTION_PASS:
        return "readiness-pass"
    if status == CONSTRUCTION_BLOCKING:
        return "readiness-blocking"
    return "readiness-warning"


def _workbench_upstream_payload() -> dict:
    return {
        "manifest_root": st.session_state.get("comparability_manifest_root", ""),
        "inventory_root": st.session_state.get("inv_f_participant", ""),
        "selected_comparable_links": sorted(
            st.session_state.get("selected_comparable_links", [])
        ),
        "comparability_status": (
            st.session_state.get("comparability_report").summary.get("comparability_status")
            if st.session_state.get("comparability_report") is not None
            else ""
        ),
    }


def _invalidate_dataset_preview_if_stale() -> None:
    current = build_upstream_fingerprint(_workbench_upstream_payload())
    built = st.session_state.get("dataset_preview_upstream_fingerprint")
    if built and built != current:
        st.session_state.pop("dataset_construction_result", None)
        st.session_state.pop("dataset_construction_paths", None)
        st.session_state.pop("dataset_preview_upstream_fingerprint", None)


def _render_dataset_construction() -> None:
    st.header("4. Dataset construction preview (Phase 4)")
    _partial_dataset_banner()
    _invalidate_dataset_preview_if_stale()
    st.caption(
        "Build a transparent Dataset A / Dataset B construction plan from approved comparable links. "
        "No PCA, centering, projection, RSS, NV, or analysis execution in this phase."
    )

    selected_links = st.session_state.get("selected_comparable_links", [])
    if not selected_links:
        st.warning("Complete Section 3 and select comparable links before building datasets.")
        return

    default_root = default_layer25_root(REPO_ROOT)
    manifest_df = load_central_manifest(
        Path(st.session_state.get("comparability_manifest_root", str(default_root)))
    )
    if manifest_df.empty:
        st.warning("Central manifest not available.")
        return

    artifact_dir = Path(
        st.text_input(
            "Dataset construction artifact output directory",
            value=str(REPO_ROOT / "Layer3_JcvPCA" / "outputs" / "_workbench_dataset_preview"),
            key="dataset_construction_artifact_dir",
        )
    )

    participants = sorted(manifest_df["participant_id"].dropna().unique().tolist())
    timepoints = sorted(manifest_df["timepoint"].dropna().unique().tolist())
    repetitions = sorted(manifest_df["repetition"].dropna().unique().tolist())
    granularity_options = sorted(manifest_df["export_granularity"].dropna().unique().tolist())

    st.subheader("Analysis mode")
    analysis_mode = st.radio(
        "Dataset construction mode",
        [ANALYSIS_MODE_LONGITUDINAL, ANALYSIS_MODE_EXPLORATORY],
        horizontal=True,
        key="dataset_analysis_mode",
    )

    c1, c2, c3 = st.columns(3)
    sel_participants = c1.multiselect(
        "Participant(s)",
        participants,
        default=["671"] if "671" in participants else participants,
        key="dataset_participants",
    )
    sel_granularity = c2.multiselect(
        "export_granularity",
        granularity_options,
        default=[g for g in ["per_exercise"] if g in granularity_options] or granularity_options,
        key="dataset_granularity",
    )
    exercise_preset = c3.selectbox(
        "Exercise preset",
        [PRESET_P1_P2, PRESET_P3_P4_P5, PRESET_ALL_P1_P5, PRESET_CUSTOM],
        key="dataset_exercise_preset",
    )
    custom_exercises = st.multiselect(
        "Custom exercises (when preset=Custom)",
        ["P1", "P2", "P3", "P4", "P5", "combined_group4"],
        default=["P1"],
        key="dataset_custom_exercises",
    )
    exercises = resolve_exercise_labels(
        preset=exercise_preset,
        custom_exercises=custom_exercises,
    )

    st.subheader("Dataset definitions")
    if analysis_mode == ANALYSIS_MODE_LONGITUDINAL:
        a1, a2, b1, b2 = st.columns(4)
        a_timepoints = a1.multiselect(
            "Dataset A timepoints",
            timepoints,
            default=[t for t in ["T1"] if t in timepoints] or timepoints,
            key="dataset_a_timepoints",
        )
        a_repetitions = a2.multiselect(
            "Dataset A repetitions",
            repetitions,
            default=[r for r in ["R1", "R2"] if r in repetitions] or repetitions,
            key="dataset_a_repetitions",
        )
        b_timepoints = b1.multiselect(
            "Dataset B timepoints",
            timepoints,
            default=[t for t in ["T2"] if t in timepoints] or timepoints,
            key="dataset_b_timepoints",
        )
        b_repetitions = b2.multiselect(
            "Dataset B repetitions",
            repetitions,
            default=[r for r in ["R2"] if r in repetitions] or repetitions,
            key="dataset_b_repetitions",
        )
        acknowledge_missing = st.checkbox(
            "Continue with available data when expected repetitions/sessions are missing",
            value=True,
            key="dataset_ack_missing",
        )
        config = DatasetConstructionConfig(
            analysis_mode=analysis_mode,
            participant_ids=sel_participants,
            export_granularities=sel_granularity,
            exercise_preset=exercise_preset,
            exercises=exercises,
            dataset_a=DatasetSideSpec(timepoints=a_timepoints, repetitions=a_repetitions),
            dataset_b=DatasetSideSpec(timepoints=b_timepoints, repetitions=b_repetitions),
            selected_link_stems=selected_links,
            acknowledge_missing_repetitions=acknowledge_missing,
        )
    else:
        e1, e2, e3 = st.columns(3)
        exploratory_tp = e1.selectbox(
            "Timepoint",
            timepoints,
            index=timepoints.index("T1") if "T1" in timepoints else 0,
            key="dataset_exploratory_timepoint",
        )
        rep_a = e2.selectbox(
            "Dataset A repetition",
            repetitions,
            index=repetitions.index("R1") if "R1" in repetitions else 0,
            key="dataset_exploratory_rep_a",
        )
        rep_b = e3.selectbox(
            "Dataset B repetition",
            repetitions,
            index=repetitions.index("R2") if "R2" in repetitions else min(1, len(repetitions) - 1),
            key="dataset_exploratory_rep_b",
        )
        config = DatasetConstructionConfig(
            analysis_mode=analysis_mode,
            participant_ids=sel_participants,
            export_granularities=sel_granularity,
            exercise_preset=exercise_preset,
            exercises=exercises,
            exploratory_timepoint=exploratory_tp,
            exploratory_repetition_a=rep_a,
            exploratory_repetition_b=rep_b,
            selected_link_stems=selected_links,
        )

    st.caption(
        f"Selected comparable links ({len(selected_links)}): "
        f"{', '.join(selected_links[:6])}{'...' if len(selected_links) > 6 else ''}"
    )

    if st.button("Build Dataset Preview", type="primary", key="build_dataset_preview"):
        result = build_dataset_construction_preview(manifest_df, config)
        paths = write_dataset_construction_artifacts(result, artifact_dir)
        st.session_state.dataset_construction_result = result
        st.session_state.dataset_construction_paths = {k: str(v) for k, v in paths.items()}
        st.session_state.dataset_preview_upstream_fingerprint = build_upstream_fingerprint(
            _workbench_upstream_payload()
        )
        st.success(
            f"Dataset preview built — status={result.construction_status}, "
            f"A rows={result.dataset_a.total_rows}, B rows={result.dataset_b.total_rows}."
        )

    result = st.session_state.get("dataset_construction_result")
    if result is None:
        return

    summary = result.summary
    status = str(summary.get("construction_status", CONSTRUCTION_BLOCKING))
    st.markdown(
        f"Construction status: "
        f"<span class='{_construction_class(status)}'>{status}</span>",
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Dataset A rows", summary.get("dataset_a_total_rows", 0))
    m2.metric("Dataset B rows", summary.get("dataset_b_total_rows", 0))
    m3.metric("Selected links", summary.get("n_selected_links", 0))
    m4.metric("PCA feature columns", summary.get("n_pca_feature_columns", 0))
    m5.metric("Metadata columns (excluded)", summary.get("n_metadata_columns", 0))

    st.subheader("Dataset A sources")
    st.dataframe(result.dataset_a.sources, use_container_width=True, hide_index=True)
    st.subheader("Dataset B sources")
    st.dataframe(result.dataset_b.sources, use_container_width=True, hide_index=True)

    if not result.warnings.empty:
        st.subheader("Warnings")
        st.dataframe(result.warnings, use_container_width=True, hide_index=True)
    if not result.blocking_errors.empty:
        st.subheader("Blocking errors")
        st.dataframe(result.blocking_errors, use_container_width=True, hide_index=True)

    with st.expander("Dataset A preview (first 20 rows)", expanded=False):
        st.dataframe(result.dataset_a.preview.head(20), use_container_width=True, hide_index=True)
    with st.expander("Dataset B preview (first 20 rows)", expanded=False):
        st.dataframe(result.dataset_b.preview.head(20), use_container_width=True, hide_index=True)
    with st.expander("Feature columns", expanded=False):
        st.dataframe(result.feature_columns, use_container_width=True, hide_index=True)
        st.caption(
            "Metadata excluded from PCA: "
            f"{', '.join(result.metadata_columns)} · preview tracking: "
            f"{', '.join(summary.get('preview_tracking_columns_excluded_from_pca', []))}"
        )

    ds_paths = st.session_state.get("dataset_construction_paths")
    if ds_paths:
        st.subheader("Dataset construction artifact paths")
        for name, path in ds_paths.items():
            st.code(f"{name}: {path}")


def _preflight_class(status: str) -> str:
    if status == PREFLIGHT_PASS:
        return "readiness-pass"
    if status == PREFLIGHT_BLOCKING:
        return "readiness-blocking"
    return "readiness-warning"


def _dataset_upstream_payload() -> dict:
    payload = _workbench_upstream_payload()
    result = st.session_state.get("dataset_construction_result")
    if result is not None:
        payload["construction_status"] = result.construction_status
        payload["dataset_a_rows"] = result.dataset_a.total_rows
        payload["dataset_b_rows"] = result.dataset_b.total_rows
    return payload


def _invalidate_preflight_if_stale() -> None:
    current = build_upstream_fingerprint(_dataset_upstream_payload())
    built = st.session_state.get("preflight_upstream_fingerprint")
    if built and built != current:
        st.session_state.pop("workbench_preflight_report", None)
        st.session_state.pop("preflight_paths", None)
        st.session_state.pop("preflight_upstream_fingerprint", None)
        st.session_state.pop("preflight_warnings_acknowledged", None)


def _render_preflight() -> None:
    st.header("5. Feature alignment & preflight (Phase 5)")
    _partial_dataset_banner()
    _invalidate_preflight_if_stale()
    st.caption(
        "Validate feature alignment and matrix readiness from the Phase 4 construction plan. "
        "No PCA, centering, projection, RSS, NV, or analysis execution in this phase."
    )

    construction_result = st.session_state.get("dataset_construction_result")
    if construction_result is None:
        st.warning("Build a dataset preview in Section 4 before running preflight.")
        return

    if construction_result.construction_status == CONSTRUCTION_BLOCKING:
        st.error("Phase 4 construction is blocking. Resolve construction errors before preflight.")

    default_root = default_layer25_root(REPO_ROOT)
    manifest_df = load_central_manifest(
        Path(st.session_state.get("comparability_manifest_root", str(default_root)))
    )
    artifact_dir = Path(
        st.text_input(
            "Preflight artifact output directory",
            value=str(REPO_ROOT / "Layer3_JcvPCA" / "outputs" / "_workbench_preflight"),
            key="preflight_artifact_dir",
        )
    )
    construction_paths = st.session_state.get("dataset_construction_paths") or {}
    construction_dir = Path(construction_paths.get("dataset_construction_plan", artifact_dir)).parent
    st.caption(f"Using construction artifacts from: `{construction_dir}`")

    if st.button("Run preflight", type="primary", key="run_workbench_preflight"):
        bundle = bundle_from_construction_result(construction_result, construction_dir)
        report = run_workbench_preflight(
            bundle,
            manifest_df=manifest_df,
            warnings_acknowledged=st.session_state.get("preflight_warnings_acknowledged", False),
        )
        paths = write_workbench_preflight_artifacts(report, artifact_dir)
        st.session_state.workbench_preflight_report = report
        st.session_state.preflight_paths = {k: str(v) for k, v in paths.items()}
        st.session_state.preflight_upstream_fingerprint = build_upstream_fingerprint(
            _dataset_upstream_payload()
        )
        st.success(f"Preflight complete — status={report.preflight_status}.")

    report = st.session_state.get("workbench_preflight_report")
    if report is None:
        bundle = bundle_from_construction_result(construction_result, construction_dir)
        report = run_workbench_preflight(bundle, manifest_df=manifest_df)
        st.session_state.workbench_preflight_report = report

    status = report.preflight_status
    st.markdown(
        f"Preflight status: <span class='{_preflight_class(status)}'>{status}</span>",
        unsafe_allow_html=True,
    )

    s1, s2, s3 = st.columns(3)
    s1.metric("Dataset A status", report.dataset_a_status)
    s2.metric("Dataset B status", report.dataset_b_status)
    s3.metric("Can continue to Phase 6", "Yes" if report.can_continue_to_phase6 else "No")

    st.subheader("Feature alignment")
    st.dataframe(report.feature_alignment, use_container_width=True, hide_index=True)

    with st.expander("Feature order preview", expanded=False):
        st.markdown("**Dataset A order**")
        st.code("\n".join(report.feature_order_a))
        st.markdown("**Dataset B order**")
        st.code("\n".join(report.feature_order_b))

    st.subheader("Rows-to-features adequacy")
    st.dataframe(report.rows_to_features, use_container_width=True, hide_index=True)

    st.subheader("Source matrix QC / layer3_safe")
    st.dataframe(report.source_qc, use_container_width=True, hide_index=True)

    if not report.warnings.empty:
        st.subheader("Warnings")
        st.dataframe(report.warnings, use_container_width=True, hide_index=True)

    if not report.blocking_errors.empty:
        st.subheader("Blocking errors")
        st.dataframe(report.blocking_errors, use_container_width=True, hide_index=True)

    if status == PREFLIGHT_WARNING and report.blocking_errors.empty:
        ack = st.checkbox(
            "I acknowledge preflight warnings and understand the partial dataset / QC limitations.",
            value=st.session_state.get("preflight_warnings_acknowledged", False),
            key="preflight_ack_checkbox",
        )
        if ack:
            report = run_workbench_preflight(
                bundle_from_construction_result(construction_result, construction_dir),
                manifest_df=manifest_df,
                warnings_acknowledged=True,
            )
            st.session_state.workbench_preflight_report = report
            st.session_state.preflight_warnings_acknowledged = True
            paths = write_workbench_preflight_artifacts(report, artifact_dir)
            save_preflight_acknowledgment(
                artifact_dir,
                acknowledged=True,
                preflight_summary=report.summary,
            )
            st.session_state.preflight_paths = {k: str(v) for k, v in paths.items()}
            st.success("Preflight warnings acknowledged. Phase 6 may proceed when implemented.")
        else:
            st.session_state.preflight_warnings_acknowledged = False
            st.info("Acknowledge warnings to unlock Phase 6.")
    elif status == PREFLIGHT_BLOCKING:
        st.error("Blocking preflight errors must be resolved before Phase 6.")
    else:
        st.success("Preflight passed with no warnings.")

    preflight_paths = st.session_state.get("preflight_paths")
    if preflight_paths:
        st.subheader("Preflight artifact paths")
        for name, path in preflight_paths.items():
            st.code(f"{name}: {path}")


def _phase6_upstream_payload() -> dict:
    payload = _dataset_upstream_payload()
    payload["preflight_acknowledged"] = st.session_state.get("preflight_warnings_acknowledged", False)
    preflight_paths = st.session_state.get("preflight_paths") or {}
    payload["preflight_summary_path"] = preflight_paths.get("preflight_summary", "")
    return payload


def _step_status_class(status: str) -> str:
    if status == STEP_COMPLETED:
        return "readiness-pass"
    if status in {"blocking", "invalidated"}:
        return "readiness-blocking"
    if status == "warning":
        return "readiness-warning"
    return ""


def _render_step_runner() -> None:
    st.header("6. Step runner — raw preview & centering (Phase 6)")
    _partial_dataset_banner()
    _invalidate_preflight_if_stale()
    st.caption(
        "Run computation steps one at a time: load datasets, raw preview, independent centering. "
        "No PCA, projection, RSS, NV, or full JcvPCA analysis in this phase."
    )

    construction_result = st.session_state.get("dataset_construction_result")
    if construction_result is None:
        st.warning("Complete Section 4 (dataset construction) before Phase 6.")
        return

    construction_paths = st.session_state.get("dataset_construction_paths") or {}
    preflight_paths = st.session_state.get("preflight_paths") or {}
    if not construction_paths:
        st.warning("Build dataset preview artifacts in Section 4.")
        return

    construction_dir = Path(construction_paths.get("dataset_construction_plan", "")).parent
    preflight_dir = Path(
        preflight_paths.get("preflight_summary", REPO_ROOT / "Layer3_JcvPCA" / "outputs" / "_workbench_preflight")
    ).parent

    gate_passed, gate_report = check_phase6_gate(preflight_dir)
    st.subheader("Preflight gate")
    if gate_passed:
        st.success("Preflight gate passed — Phase 6 steps are unlocked.")
    else:
        st.error("Phase 6 blocked: " + "; ".join(gate_report.get("messages") or ["Preflight gate failed."]))
        for msg in gate_report.get("messages") or []:
            st.markdown(f"- {msg}")

    run_output_dir = Path(
        st.text_input(
            "Phase 6 run output directory",
            value=str(REPO_ROOT / "Layer3_JcvPCA" / "outputs" / "_workbench_phase6"),
            key="phase6_output_dir",
        )
    )

    upstream_fp = build_upstream_fingerprint(_phase6_upstream_payload())
    if st.button("Initialize / reload run state", key="init_phase6_run"):
        ctx = Phase6RunContext(
            construction_artifact_dir=construction_dir,
            preflight_artifact_dir=preflight_dir,
            output_dir=run_output_dir,
            upstream_fingerprint=upstream_fp,
        )
        state = load_run_state(run_output_dir)
        if state is None:
            state = initialize_run_state(ctx)
        else:
            sync_upstream_invalidation(state, upstream_fp)
            ensure_workbench_step_registry(state)
        st.session_state.phase6_run_state = state
        st.session_state.phase6_context = ctx
        st.success("Run state loaded.")

    state = st.session_state.get("phase6_run_state")
    ctx = st.session_state.get("phase6_context")
    if state is None or ctx is None:
        if gate_passed:
            st.info("Click **Initialize / reload run state** to begin.")
        return

    if sync_upstream_invalidation(state, upstream_fp):
        st.warning("Upstream Sections 3–5 changed — downstream steps invalidated. Re-run from Step 6A.")

    for step_id in PHASE6_STEP_ORDER:
        step = state.steps[step_id]
        st.markdown("---")
        st.subheader(f"{step_id}: {STEP_DISPLAY_NAMES[step_id]}")
        st.markdown(
            f"Status: <span class='{_step_status_class(step.status)}'>{step.status}</span>",
            unsafe_allow_html=True,
        )

        if step_id == STEP_6A_LOAD:
            st.caption("Load full constructed Dataset A/B from Phase 4 previews; confirm PCA columns exclude metadata.")
        elif step_id == STEP_6B_RAW_PREVIEW:
            st.caption("Display-only raw stats (mean, std, min, max, variance). No transformation.")
        elif step_id == STEP_6C_CENTERING:
            st.caption("A_centered = A - mean(A); B_centered = B - mean(B). Independent means only.")

        if step.blocking_errors:
            st.dataframe(pd.DataFrame(step.blocking_errors), hide_index=True, use_container_width=True)

        col_run, col_info = st.columns([1, 3])
        with col_run:
            run_disabled = not gate_passed or step.status in {"blocking", "invalidated"}
            if st.button(f"Run {step_id}", key=f"run_{step_id}", disabled=run_disabled):
                try:
                    run_step(step_id, ctx, state)
                    st.session_state.phase6_run_state = load_run_state(run_output_dir)
                    st.success(f"{step_id} completed.")
                except StepRunError as exc:
                    st.error(str(exc))

        with col_info:
            if step.completed_at:
                st.caption(f"Completed at: {step.completed_at}")
            if step.artifact_paths:
                for name, path in step.artifact_paths.items():
                    st.code(f"{name}: {path}")

        if step_id == STEP_6B_RAW_PREVIEW and step.status == STEP_COMPLETED:
            stats_a_path = run_output_dir / "raw_feature_stats_A.csv"
            stats_b_path = run_output_dir / "raw_feature_stats_B.csv"
            if stats_a_path.is_file():
                with st.expander("Raw feature stats (A)", expanded=False):
                    st.dataframe(pd.read_csv(stats_a_path), use_container_width=True, hide_index=True)
            if stats_b_path.is_file():
                with st.expander("Raw feature stats (B)", expanded=False):
                    st.dataframe(pd.read_csv(stats_b_path), use_container_width=True, hide_index=True)

        if step_id == STEP_6C_CENTERING and step.status == STEP_COMPLETED:
            cv_a = run_output_dir / "centering_values_A.csv"
            cv_b = run_output_dir / "centering_values_B.csv"
            val_path = run_output_dir / "centered_validation_report.csv"
            if cv_a.is_file() and cv_b.is_file():
                with st.expander("Centering values", expanded=False):
                    st.markdown("**Dataset A**")
                    st.dataframe(pd.read_csv(cv_a), use_container_width=True, hide_index=True)
                    st.markdown("**Dataset B**")
                    st.dataframe(pd.read_csv(cv_b), use_container_width=True, hide_index=True)
            if val_path.is_file():
                with st.expander("Centering validation", expanded=False):
                    st.dataframe(pd.read_csv(val_path), use_container_width=True, hide_index=True)

        if step.user_can_continue and step.status in {STEP_COMPLETED, "warning"}:
            st.caption("Stop here to inspect artifacts, or continue to the next step.")


def _render_pca_on_a() -> None:
    st.header("7. PCA on Dataset A (Phase 7)")
    st.caption(
        "Fit PCA on centered Dataset A only. Inspect explained variance and approve selected_m "
        "before any B projection (Phase 8). No z-score, scaling, or Dataset B usage."
    )

    state = st.session_state.get("phase6_run_state")
    ctx = st.session_state.get("phase6_context")
    if state is None or ctx is None:
        st.info("Initialize run state in Section 6 before running PCA on A.")
        return

    ensure_workbench_step_registry(state)
    step = state.steps.get(STEP_7A_PCA_A)
    if step is None:
        st.error("Step 7A not registered in run state.")
        return

    centering_step = state.steps.get(STEP_6C_CENTERING)
    centering_ok = (
        centering_step is not None
        and centering_step.status == STEP_COMPLETED
        and (ctx.output_dir / "centering_summary.json").is_file()
    )
    if centering_ok:
        import json

        summary = json.loads((ctx.output_dir / "centering_summary.json").read_text(encoding="utf-8"))
        centering_ok = bool(summary.get("validation_pass"))

    run_output_dir = ctx.output_dir
    dims_path = run_output_dir / "loaded_dimensions.json"
    n_rows_a = 0
    n_features = 0
    if dims_path.is_file():
        import json

        dims = json.loads(dims_path.read_text(encoding="utf-8"))
        n_rows_a = int(dims.get("dataset_a_rows") or 0)
        n_features = int(dims.get("n_pca_features") or 0)

    max_pcs_bound = min(n_rows_a, n_features) if n_rows_a and n_features else DEFAULT_MAX_PCS

    st.markdown(
        f"Status: <span class='{_step_status_class(step.status)}'>{step.status}</span>",
        unsafe_allow_html=True,
    )

    if not centering_ok:
        st.warning("Complete Step 6C with validation_pass=true before PCA on A.")

    st.subheader("PCA parameters")
    c1, c2, c3 = st.columns(3)
    with c1:
        variance_threshold = st.number_input(
            "Variance threshold",
            min_value=0.5,
            max_value=0.99,
            value=float(DEFAULT_VARIANCE_THRESHOLD),
            step=0.01,
            key="pca_a_variance_threshold",
        )
    with c2:
        min_pcs = st.number_input(
            "min_pcs",
            min_value=1,
            max_value=max(max_pcs_bound, 1),
            value=DEFAULT_MIN_PCS,
            step=1,
            key="pca_a_min_pcs",
        )
    with c3:
        max_pcs = st.number_input(
            "max_pcs",
            min_value=int(min_pcs),
            max_value=max(max_pcs_bound, DEFAULT_MAX_PCS),
            value=min(DEFAULT_MAX_PCS, max_pcs_bound) if max_pcs_bound else DEFAULT_MAX_PCS,
            step=1,
            key="pca_a_max_pcs",
        )

    selected_m_mode = st.radio(
        "selected_m_mode",
        options=[SELECTED_M_MODE_AUTO, SELECTED_M_MODE_MANUAL],
        horizontal=True,
        key="pca_a_selected_m_mode",
    )
    selected_m_override: int | None = None
    if selected_m_mode == SELECTED_M_MODE_MANUAL:
        selected_m_override = st.number_input(
            "selected_m_override",
            min_value=1,
            max_value=max(max_pcs_bound, 1),
            value=int(min_pcs),
            step=1,
            key="pca_a_selected_m_override",
        )
        if n_rows_a and n_features:
            manual_errors = validate_selected_m_workbench(
                int(selected_m_override),
                n_rows=n_rows_a,
                n_features=n_features,
                min_pcs=int(min_pcs),
                max_pcs=int(max_pcs),
            )
            for err in manual_errors:
                st.error(err)

    m1, m2, m3 = st.columns(3)
    m1.metric("n_rows_A", n_rows_a or "—")
    m2.metric("n_features", n_features or "—")
    m3.metric("max_pcs (data bound)", max_pcs_bound or "—")

    run_disabled = (
        not centering_ok
        or step.status in {"blocking", "invalidated"}
        or step.status == "running"
    )
    if selected_m_mode == SELECTED_M_MODE_MANUAL and n_rows_a and n_features and selected_m_override:
        if validate_selected_m_workbench(
            int(selected_m_override),
            n_rows=n_rows_a,
            n_features=n_features,
            min_pcs=int(min_pcs),
            max_pcs=int(max_pcs),
        ):
            run_disabled = True

    if st.button("Run PCA on A (Step 7A)", key="run_step_7a", disabled=run_disabled):
        params = PcaAParameters(
            variance_threshold=float(variance_threshold),
            min_pcs=int(min_pcs),
            max_pcs=int(max_pcs),
            selected_m_mode=selected_m_mode,
            selected_m_override=int(selected_m_override) if selected_m_override is not None else None,
        )
        try:
            run_step(STEP_7A_PCA_A, ctx, state, pca_a_params=params)
            st.session_state.phase6_run_state = load_run_state(run_output_dir)
            st.success("Step 7A completed.")
        except StepRunError as exc:
            st.error(str(exc))

    if step.status not in {STEP_COMPLETED, "warning", "blocking"}:
        return

    _render_pca_stability_panel(run_output_dir, step)

    if step.status == "blocking":
        st.error("Step 7A blocked by PCA stability checks on Dataset A and/or B.")
        return

    selected_path = run_output_dir / "pca_A_selected_m.json"
    if selected_path.is_file():
        import json

        selected = json.loads(selected_path.read_text(encoding="utf-8"))
        s1, s2, s3 = st.columns(3)
        s1.metric("selected_m", selected.get("selected_m", "—"))
        s2.metric("variance threshold", selected.get("variance_threshold", "—"))
        s3.metric(
            "cum. variance @ selected_m",
            f"{selected.get('cumulative_variance_at_selected_m', 0):.3f}",
        )
        st.caption(f"**selected_m reason:** {selected.get('selected_m_reason', '')}")

    evr_path = run_output_dir / "pca_A_explained_variance.csv"
    cum_path = run_output_dir / "pca_A_cumulative_variance.csv"
    if evr_path.is_file():
        with st.expander("Explained variance", expanded=True):
            st.dataframe(pd.read_csv(evr_path), use_container_width=True, hide_index=True)
    if cum_path.is_file():
        with st.expander("Cumulative variance", expanded=False):
            st.dataframe(pd.read_csv(cum_path), use_container_width=True, hide_index=True)

    scree = run_output_dir / "plots" / "pca_A_scree_plot.png"
    cum_plot = run_output_dir / "plots" / "pca_A_cumulative_variance.png"
    heatmap = run_output_dir / "plots" / "pca_A_loadings_heatmap.png"
    pc1, pc2, pc3 = st.columns(3)
    if scree.is_file():
        pc1.image(str(scree), caption="Scree plot")
    if cum_plot.is_file():
        pc2.image(str(cum_plot), caption="Cumulative variance")
    if heatmap.is_file():
        pc3.image(str(heatmap), caption="Loadings heatmap")

    loadings_path = run_output_dir / "pca_A_loadings.csv"
    if loadings_path.is_file():
        loadings = pd.read_csv(loadings_path)
        with st.expander("A loadings table (link / axis labeled)", expanded=False):
            st.dataframe(loadings, use_container_width=True, hide_index=True)
        with st.expander("Top contributing features per PC", expanded=True):
            top = loadings[loadings["rank_within_pc"] <= 5].sort_values(["pc", "rank_within_pc"])
            st.dataframe(top, use_container_width=True, hide_index=True)

    st.subheader("Artifacts")
    if step.artifact_paths:
        for name, path in step.artifact_paths.items():
            st.code(f"{name}: {path}")

    if step.user_can_continue and step.status in {STEP_COMPLETED, "warning"}:
        gate_ok, gate_report = check_pca_stability_gate(run_output_dir)
        if gate_ok:
            st.success("Step 7A complete — continue to Section 9 (PC focus selection).")
        elif gate_report.get("combined_status") == "warning":
            st.warning("Acknowledge PCA stability warnings to continue to Phase 8.")
        else:
            for msg in gate_report.get("messages") or []:
                st.info(msg)
    else:
        st.info("Resolve blocking issues before continuing to Phase 8.")


def _render_pca_stability_panel(run_output_dir: Path, step) -> None:
    import json

    combined_path = run_output_dir / "pca_stability_combined_summary.json"
    if not combined_path.is_file():
        return

    st.subheader("PCA Stability / Readiness")
    st.caption(
        "Numerical readiness only — not scientific conclusions. "
        "**Dataset A** defines the PCA reference frame. "
        "**Dataset B** readiness is diagnostic for later projection; selected_m is derived from A only."
    )

    combined = json.loads(combined_path.read_text(encoding="utf-8"))
    c1, c2, c3 = st.columns(3)
    c1.metric("Combined status", combined.get("combined_status", "—"))
    c2.metric("Dataset A status", combined.get("A_status", "—"))
    c3.metric("Dataset B status", combined.get("B_status", "—"))

    tab_a, tab_b = st.tabs(
        [
            "Dataset A — reference PCA readiness",
            "Dataset B — comparison matrix readiness",
        ]
    )

    for tab, side, label in (
        (tab_a, "A", "reference"),
        (tab_b, "B", "comparison"),
    ):
        with tab:
            summary_path = run_output_dir / f"pca_{side}_stability_summary.json"
            report_path = run_output_dir / f"pca_{side}_stability_report.csv"
            sv_path = run_output_dir / f"pca_{side}_singular_values.csv"
            nz_path = run_output_dir / f"pca_{side}_near_zero_variance_features.csv"
            sh_path = run_output_dir / f"pca_{side}_split_half_similarity.csv"

            if label == "reference":
                st.info("A defines the PCA reference frame and selected_m.")
            else:
                st.info("B readiness is diagnostic only; B does not choose selected_m.")

            if summary_path.is_file():
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                metrics = summary.get("metrics") or {}
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("n_rows", metrics.get("n_rows", "—"))
                m2.metric("n_features", metrics.get("n_features", "—"))
                m3.metric("rows/features", metrics.get("rows_to_features_ratio", "—"))
                m4.metric("status", summary.get("status", "—"))

                m5, m6, m7, m8 = st.columns(4)
                m5.metric("matrix rank", metrics.get("matrix_rank", "—"))
                m6.metric("rank deficiency", metrics.get("rank_deficiency", "—"))
                m7.metric("condition number", metrics.get("condition_number", "—"))
                m8.metric("dominant PC %", metrics.get("dominant_pc_variance_percent", "—"))

                m9, m10, m11 = st.columns(3)
                m9.metric("NaN count", metrics.get("nan_count", "—"))
                m10.metric("inf count", metrics.get("inf_count", "—"))
                m11.metric("PCA fit", "OK" if metrics.get("pca_fit_success") else "FAIL")

                if side == "A":
                    st.markdown("**A-only PCA selection (reference frame)**")
                    a1, a2, a3 = st.columns(3)
                    a1.metric("selected_m", metrics.get("selected_m", "—"))
                    a2.metric(
                        "cum. variance @ selected_m",
                        metrics.get("cumulative_variance_at_selected_m", "—"),
                    )
                    a3.metric("variance threshold", metrics.get("variance_threshold", "—"))
                    if metrics.get("selected_m_reason"):
                        st.caption(f"selected_m reason: {metrics.get('selected_m_reason')}")
                    if metrics.get("selected_m_clamp_warning"):
                        st.warning(metrics.get("selected_m_clamp_warning"))

            if report_path.is_file():
                with st.expander(f"{side} stability findings", expanded=False):
                    st.dataframe(pd.read_csv(report_path), use_container_width=True, hide_index=True)
            if sv_path.is_file():
                with st.expander(f"{side} singular values", expanded=False):
                    st.dataframe(pd.read_csv(sv_path), use_container_width=True, hide_index=True)
            if nz_path.is_file():
                nz_df = pd.read_csv(nz_path)
                if not nz_df.empty:
                    with st.expander(f"{side} near-zero variance features", expanded=False):
                        st.dataframe(nz_df, use_container_width=True, hide_index=True)
            if sh_path.is_file():
                with st.expander(f"{side} split-half similarity", expanded=False):
                    st.dataframe(pd.read_csv(sh_path), use_container_width=True, hide_index=True)

    if combined.get("requires_acknowledgment"):
        st.warning("PCA stability warnings require acknowledgment before Phase 8.")
        ack = st.checkbox(
            "I acknowledge PCA stability warnings for Dataset A and/or B "
            "(numerical readiness only; not a scientific conclusion).",
            key="pca_stability_ack",
        )
        if st.button("Save PCA stability acknowledgment", key="save_pca_stability_ack"):
            save_pca_stability_acknowledgment(
                run_output_dir,
                acknowledged=ack,
                combined_summary=combined,
            )
            st.success("PCA stability acknowledgment saved." if ack else "Acknowledgment cleared.")

    gate_ok, gate_report = check_pca_stability_gate(run_output_dir)
    if gate_ok:
        st.success("PCA stability gate passed — ready for Phase 8 when implemented.")
    else:
        for msg in gate_report.get("messages") or []:
            st.caption(msg)


def _render_pc_focus_selection() -> None:
    st.header("9. PC analysis focus selection (Phase 9)")
    st.caption(
        "Choose which PCs from A's selected_m are included in downstream JcvPCA summaries. "
        "p is never inferred silently. No B projection or full JcvPCA in this phase."
    )

    state = st.session_state.get("phase6_run_state")
    ctx = st.session_state.get("phase6_context")
    if state is None or ctx is None:
        st.info("Initialize run state in Section 6 before PC focus selection.")
        return

    ensure_workbench_step_registry(state)
    step = state.steps.get(STEP_9A_PC_FOCUS)
    if step is None:
        st.error("Step 9A not registered in run state.")
        return

    run_output_dir = ctx.output_dir
    selected_path = run_output_dir / "pca_A_selected_m.json"
    selected_m = 0
    if selected_path.is_file():
        import json

        selected_m = int(json.loads(selected_path.read_text()).get("selected_m") or 0)

    stab_ok, stab_msgs = check_pca_stability_gate(run_output_dir)
    if not stab_ok:
        st.warning("PCA stability gate: " + "; ".join(stab_msgs))

    st.markdown(
        f"Status: <span class='{_step_status_class(step.status)}'>{step.status}</span>",
        unsafe_allow_html=True,
    )
    st.metric("selected_m (from Step 7A)", selected_m or "—")

    pc_focus_mode = st.radio(
        "PC focus mode",
        options=list(PC_FOCUS_MODES),
        index=list(PC_FOCUS_MODES).index(PC_FOCUS_ALL),
        horizontal=True,
        key="pc_focus_mode",
        format_func=lambda x: {
            PC_FOCUS_FUNCTIONAL: "Functional PCs (first p)",
            PC_FOCUS_NULL_SPACE: "Null-space PCs (p+1 .. selected_m)",
            PC_FOCUS_ALL: "All selected PCs (PC1 .. selected_m)",
            PC_FOCUS_MANUAL: "Manual PC selection",
        }.get(x, x),
    )

    p_value: int | None = None
    manual_pcs: list[int] | None = None
    if pc_focus_mode in {PC_FOCUS_FUNCTIONAL, PC_FOCUS_NULL_SPACE}:
        p_value = st.number_input(
            "p / estimated task DoF (required)",
            min_value=1,
            max_value=max(selected_m, 1),
            value=min(2, max(selected_m, 1)),
            step=1,
            key="pc_focus_p",
        )
    if pc_focus_mode == PC_FOCUS_MANUAL:
        manual_pcs = st.multiselect(
            "Manual PCs to include",
            options=list(range(1, selected_m + 1)) if selected_m else [],
            default=[1] if selected_m else [],
            key="pc_focus_manual_pcs",
        )

    focus_params = PcFocusParameters(
        pc_focus_mode=pc_focus_mode,
        p=int(p_value) if p_value is not None else None,
        manual_pcs=[int(x) for x in manual_pcs] if manual_pcs is not None else None,
    )
    if selected_m:
        for err in validate_pc_focus_parameters(focus_params, selected_m=selected_m):
            st.error(err)

    run_disabled = (
        not selected_m
        or not stab_ok
        or step.status in {"blocking", "invalidated"}
        or bool(validate_pc_focus_parameters(focus_params, selected_m=selected_m)) if selected_m else True
    )

    if st.button("Run PC focus selection (Step 9A)", key="run_step_9a", disabled=run_disabled):
        try:
            run_step(STEP_9A_PC_FOCUS, ctx, state, pc_focus_params=focus_params)
            st.session_state.phase6_run_state = load_run_state(run_output_dir)
            st.success("Step 9A completed.")
        except StepRunError as exc:
            st.error(str(exc))

    if step.status not in {STEP_COMPLETED, "warning"}:
        return

    table_path = run_output_dir / "pc_focus_table.csv"
    sel_path = run_output_dir / "pc_focus_selection.json"
    if table_path.is_file():
        with st.expander("PC focus table", expanded=True):
            st.dataframe(pd.read_csv(table_path), use_container_width=True, hide_index=True)
    if sel_path.is_file():
        import json

        payload = json.loads(sel_path.read_text())
        st.caption(f"**Included PCs:** {payload.get('included_pcs')} — {payload.get('selection_reason')}")

    if step.artifact_paths:
        st.subheader("Artifacts")
        for name, path in step.artifact_paths.items():
            st.code(f"{name}: {path}")

    if step.user_can_continue and step.status in {STEP_COMPLETED, "warning"}:
        st.success("Step 9A complete — continue to Section 10 (JcvPCA pipeline).")


def _render_jcvpca_pipeline() -> None:
    st.header("10–18. JcvPCA pipeline (projection through export)")
    st.caption(
        "Stepwise B projection, PCA on projected B, re-expression, axis-level JcvPCA, "
        "RSS link aggregation, optional weighting, NV baseline, exploratory summary, and export. "
        "Numeric readiness outputs only — no scientific conclusions."
    )

    state = st.session_state.get("phase6_run_state")
    ctx = st.session_state.get("phase6_context")
    if state is None or ctx is None:
        st.info("Initialize run state in Section 6 first.")
        return

    ensure_workbench_step_registry(state)
    run_output_dir = ctx.output_dir

    weight_on = st.checkbox("Explained-variance weighting (Step 15)", value=False, key="jcvpca_weight_on")

    pipeline_steps = (
        STEP_10A_B_PROJECTION,
        STEP_11A_PCA_B,
        STEP_12A_REEXPRESS,
        STEP_13A_AXIS_JCVPCA,
        STEP_14A_RSS,
        STEP_15A_WEIGHTING,
        STEP_16A_NV,
        STEP_17A_EXPLORATORY,
        STEP_18A_EXPORT,
    )

    if st.button("Run all pipeline steps (10A–18A)", key="run_all_jcvpca"):
        try:
            for step_id in pipeline_steps:
                kwargs = {}
                if step_id == STEP_15A_WEIGHTING:
                    kwargs["weighting_params"] = WeightingParameters(explained_variance_weighting=weight_on)
                run_step(step_id, ctx, state, **kwargs)
            st.session_state.phase6_run_state = load_run_state(run_output_dir)
            st.success("Pipeline steps 10A–18A completed.")
        except StepRunError as exc:
            st.error(str(exc))

    for step_id in pipeline_steps:
        step = state.steps.get(step_id)
        if step is None:
            continue
        st.markdown("---")
        st.subheader(f"{step_id}: {STEP_DISPLAY_NAMES.get(step_id, step_id)}")
        st.markdown(
            f"Status: <span class='{_step_status_class(step.status)}'>{step.status}</span>",
            unsafe_allow_html=True,
        )
        col_run, _ = st.columns([1, 4])
        with col_run:
            if st.button(f"Run {step_id}", key=f"run_{step_id}"):
                try:
                    kwargs = {}
                    if step_id == STEP_15A_WEIGHTING:
                        kwargs["weighting_params"] = WeightingParameters(explained_variance_weighting=weight_on)
                    run_step(step_id, ctx, state, **kwargs)
                    st.session_state.phase6_run_state = load_run_state(run_output_dir)
                    st.success(f"{step_id} done.")
                except StepRunError as exc:
                    st.error(str(exc))

    if (run_output_dir / "link_level_jcvpca_unweighted.csv").is_file():
        with st.expander("Link-level JcvPCA (unweighted)", expanded=False):
            st.dataframe(pd.read_csv(run_output_dir / "link_level_jcvpca_unweighted.csv"), use_container_width=True)
    if (run_output_dir / "main_vs_nv_descriptive_comparison.csv").is_file():
        with st.expander("Main vs NV descriptive comparison", expanded=False):
            st.dataframe(pd.read_csv(run_output_dir / "main_vs_nv_descriptive_comparison.csv"), use_container_width=True)
    if (run_output_dir / "workbench_export_manifest.json").is_file():
        st.success(f"Export manifest: {run_output_dir / 'workbench_export_manifest.json'}")


def main() -> None:
    _css()
    st.title("Layer 3 Gaga JcvPCA Workbench")
    st.caption(
        "Stepwise analysis workbench (Phases 0–18: inventory through JcvPCA export). "
        "Numeric outputs only — no scientific conclusions."
    )
    _render_diagnostics()
    st.divider()
    _render_inventory()
    st.divider()
    _render_export_readiness()
    st.divider()
    _render_comparable_links()
    st.divider()
    _render_dataset_construction()
    st.divider()
    _render_preflight()
    st.divider()
    _render_step_runner()
    st.divider()
    _render_pca_on_a()
    st.divider()
    _render_pc_focus_selection()
    st.divider()
    _render_jcvpca_pipeline()


if __name__ == "__main__":
    main()
