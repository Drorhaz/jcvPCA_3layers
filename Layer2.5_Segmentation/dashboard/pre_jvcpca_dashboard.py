"""Pre-JcvPCA review dashboard — web UI for Layer 2.5 window export."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from dashboard_state import (  # noqa: E402
    joint_filter_signature,
    set_selected_joints,
    sync_joint_selection_to_filters,
)
from pre_jvcpca_review.app_controller import PreJcvpcaReviewController  # noqa: E402
from pre_jvcpca_review.exercise_segments import GROUP4_LABEL, exercise_choice_label  # noqa: E402
from pre_jvcpca_review.joint_body_sections import (  # noqa: E402
    BODY_SECTION_ALL,
    BODY_SECTION_LABELS,
)
from pre_jvcpca_review.session_index import participants  # noqa: E402

st.set_page_config(
    page_title="Pre-JcvPCA Review",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _inject_css() -> None:
    st.markdown(
        """
        <style>
          .block-container { padding-top: 1.2rem; }
          div[data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
          }
          .scope-banner {
            background: #f5f7fa;
            border: 1px solid #dde3ea;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin: 0.5rem 0 1rem 0;
            font-size: 0.92rem;
          }
          .verdict-blocked { color: #b00020; font-weight: 700; }
          .verdict-strong { color: #d35400; font-weight: 700; }
          .verdict-ok { color: #2e7d32; font-weight: 700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_state() -> PreJcvpcaReviewController:
    if "controller" not in st.session_state:
        st.session_state.controller = PreJcvpcaReviewController(PROJECT_ROOT)
    defaults = {
        "participant_id": None,
        "session_id": None,
        "selected_joints": [],
        "frame_start": 16000,
        "frame_end": 17000,
        "window_label": "window_01",
        "window_label_tag": "",
        "exercise_choice": None,
        "exercise_file_path": "",
        "joint_filter_core_only": False,
        "joint_filter_directly_comparable": False,
        "joint_filter_body_section": BODY_SECTION_ALL,
        "allow_nan_matrix": False,
        "qc_types": ["gap_0p5", "gap_0p2", "artifact_sigma", "segment_swap"],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    return st.session_state.controller


def _qc_types(gap_0p5: bool, gap_0p2: bool, artifact: bool, swap: bool) -> list[str]:
    types: list[str] = []
    if gap_0p5:
        types.append("gap_0p5")
    if gap_0p2:
        types.append("gap_0p2")
    if artifact:
        types.append("artifact_sigma")
    if swap:
        types.append("segment_swap")
    return types


def _sync_window_label(ctrl: PreJcvpcaReviewController) -> None:
    session_id = st.session_state.get("session_id")
    if not session_id:
        return
    st.session_state.window_label = ctrl.build_window_label(
        session_id,
        st.session_state.frame_start,
        st.session_state.frame_end,
        tag=st.session_state.get("window_label_tag", ""),
    )


def _render_joint_checkboxes(
    ctrl: PreJcvpcaReviewController,
    visible_options,
) -> None:
    previous = list(st.session_state.get("selected_joints", []))
    selected = set(previous)
    updated: set[str] = set()

    if not visible_options:
        st.info("No joints match the current filters.")
        if previous:
            set_selected_joints(st.session_state, [])
        return

    with st.container(height=360):
        cols = st.columns(2)
        for index, opt in enumerate(visible_options):
            col = cols[index % 2]
            checked = col.checkbox(
                opt.label,
                value=opt.link_id in selected,
                key=f"joint_cb_{opt.link_id}",
            )
            if checked:
                updated.add(opt.link_id)

    new_selection = sorted(updated)
    if new_selection != previous:
        st.session_state.selected_joints = new_selection
        st.session_state.pop("warning_summary", None)


def _exercise_choices(ctrl: PreJcvpcaReviewController, session_id: str | None) -> list[str]:
    if not session_id:
        return []
    segments = ctrl.exercises_for_session(session_id)
    if not segments:
        return []
    choices = [GROUP4_LABEL]
    choices.extend(exercise_choice_label(segment) for segment in segments)
    return choices


def _load_exercise_catalog_from_path(ctrl: PreJcvpcaReviewController, path: Path) -> None:
    catalog = ctrl.load_exercise_catalog(path)
    st.session_state.exercise_file_path = str(path)
    st.session_state.exercise_catalog_sessions = sorted(catalog)


def _apply_manual_frames(ctrl: PreJcvpcaReviewController) -> None:
    st.session_state.exercise_choice = None
    st.session_state.window_label_tag = ""
    _sync_window_label(ctrl)


def _exercise_window_tag(choice: str) -> str:
    return "g4" if choice == GROUP4_LABEL else ""


def _reset_joint_filter_baseline() -> None:
    st.session_state.joint_filter_signature = joint_filter_signature(
        st.session_state.joint_filter_core_only,
        st.session_state.joint_filter_directly_comparable,
        st.session_state.joint_filter_body_section,
    )


def _on_participant_change(
    ctrl: PreJcvpcaReviewController,
    participant_id: str,
    output_root: Path,
) -> None:
    ctrl.build_overlap_table(participant_id, output_root)
    sess_df = ctrl.participant_sessions(participant_id)
    if sess_df.empty:
        st.session_state.session_id = None
        return
    session_id = str(sess_df.iloc[0]["session_id"])
    st.session_state.session_id = session_id
    ctrl.select_session(session_id)
    set_selected_joints(st.session_state, ctrl.default_selected_joint_ids())
    _reset_joint_filter_baseline()
    _sync_window_label(ctrl)


def _on_session_change(ctrl: PreJcvpcaReviewController, session_id: str) -> None:
    ctrl.select_session(session_id)
    set_selected_joints(st.session_state, ctrl.default_selected_joint_ids())
    _reset_joint_filter_baseline()
    _sync_window_label(ctrl)


def _render_participant_session_selectors(
    ctrl: PreJcvpcaReviewController,
    participant_ids: list[str],
    output_root: Path,
) -> None:
    st.subheader("Participant & session")
    participant_id = st.selectbox(
        "Participant",
        options=participant_ids,
        index=participant_ids.index(st.session_state.participant_id)
        if st.session_state.participant_id in participant_ids
        else 0,
    )
    if participant_id != st.session_state.participant_id:
        st.session_state.participant_id = participant_id
        _on_participant_change(ctrl, participant_id, output_root)

    sess_df = ctrl.participant_sessions(participant_id)
    session_options = sess_df["session_id"].tolist()
    if not session_options:
        st.warning("No sessions found for this participant.")
        return

    session_id = st.selectbox(
        "Session",
        options=session_options,
        index=session_options.index(st.session_state.session_id)
        if st.session_state.session_id in session_options
        else 0,
    )
    if session_id != st.session_state.session_id:
        st.session_state.session_id = session_id
        _on_session_change(ctrl, session_id)

    row = ctrl.current_row
    if row is not None:
        m1, m2, m3 = st.columns(3)
        m1.metric("L1 frames", str(row.get("n_frames_layer1", "—")))
        m2.metric("L2 frames", str(row.get("n_frames_layer2", "—")))
        m3.metric("Matched", "Yes" if row.get("is_matched") else "No")


def _sidebar(ctrl: PreJcvpcaReviewController) -> dict[str, Path]:
    st.sidebar.header("Input roots")
    layer1_root = Path(
        st.sidebar.text_input("Layer 1 root", value=str(ctrl.default_layer1_root))
    )
    layer2_root = Path(
        st.sidebar.text_input("Layer 2 root", value=str(ctrl.default_layer2_root))
    )
    output_root = Path(
        st.sidebar.text_input("Review output root", value=str(ctrl.default_output_root))
    )
    datadescriptions = Path(
        st.sidebar.text_input("DataDescriptions CSV", value=str(ctrl.default_datadescriptions))
    )

    if st.sidebar.button(
        "Discover participants / sessions",
        type="primary",
        use_container_width=True,
    ):
        try:
            result = ctrl.discover(layer1_root, layer2_root, output_root)
            st.session_state.participant_id = (
                result.participant_ids[0] if result.participant_ids else None
            )
            if st.session_state.participant_id:
                _on_participant_change(ctrl, st.session_state.participant_id, output_root)
            st.sidebar.success(
                f"Found {len(result.session_index)} sessions ({result.n_matched} matched). "
                f"Saved `{result.index_path.name}`."
            )
        except Exception as exc:
            st.sidebar.error(str(exc))

    return {
        "layer1_root": layer1_root,
        "layer2_root": layer2_root,
        "output_root": output_root,
        "datadescriptions": datadescriptions,
    }


def main() -> None:
    _inject_css()
    ctrl = _init_state()
    paths = _sidebar(ctrl)

    st.title("Pre-JcvPCA Segment / Joint Review")
    st.caption(
        "Layer 2.5 control interface — from participant/session selection to a "
        "canonical, QC-aware, Layer 3-ready export."
    )

    scope = ctrl.scope
    st.markdown(
        f"""
        <div class="scope-banner">
          <b>Default feature scope</b> (<code>{scope.source_path.name}</code>):
          scope=<code>{scope.default_body_scope}</code>,
          link set=<code>{scope.core_link_set_name}</code>,
          exclude_fingers=<b>{scope.exclude_fingers}</b>,
          exclude_toes=<b>{scope.exclude_toes}</b>,
          naming=<code>{scope.feature_naming_policy}</code><br>
          <b>{len(ctrl.required_links)}</b> canonical links /
          <b>{len(ctrl.canonical_feature_order)}</b> features.
          Edit scope in the config file, not here.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if ctrl.session_index is None:
        st.info(
            "Set Layer 1 / Layer 2 roots in the sidebar, then click "
            "**Discover participants / sessions**."
        )
        return

    if (
        not ctrl.exercise_catalog
        and ctrl.default_exercise_segments.is_file()
        and not st.session_state.get("exercise_autoload_done")
    ):
        try:
            ctrl.load_exercise_catalog(ctrl.default_exercise_segments)
            st.session_state.exercise_file_path = str(ctrl.default_exercise_segments)
        except Exception:
            pass
        st.session_state.exercise_autoload_done = True

    tab_sessions, tab_window, tab_warnings, tab_export, tab_diagnostics = st.tabs(
        ["Sessions", "Window & joints", "Warnings", "Export", "Diagnostics"]
    )

    participant_ids = participants(ctrl.session_index)
    participant_id = st.session_state.participant_id or participant_ids[0]
    sess_df = ctrl.participant_sessions(participant_id)

    with tab_sessions:
        st.caption(
            "Read-only session context. Choose participant and session in the "
            "**Window & joints** tab."
        )
        st.subheader("Layer 1 / Layer 2 pairing")
        pairing_cols = [
            "session_id",
            "timepoint",
            "part_id",
            "repetition_id",
            "is_matched",
            "match_warning",
        ]
        st.dataframe(sess_df[pairing_cols], use_container_width=True, hide_index=True)

        st.subheader("Joint / link overlap & comparability")
        if ctrl.current_overlap is not None:
            st.dataframe(
                ctrl.current_overlap[
                    [
                        "canonical_link_name",
                        "classification",
                        "present_in_sessions",
                        "missing_in_sessions",
                        "recommended_action",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
            bad = ctrl.non_comparable_features()
            if bad:
                st.error(
                    "Not directly comparable across sessions: "
                    + ", ".join(bad)
                    + " — cross-session Layer 3 export would be blocked."
                )
        else:
            st.warning("No matched Layer 2 sessions to compare.")

        row = ctrl.current_row
        if row is not None:
            st.markdown("**Resolved session directories**")
            c1, c2 = st.columns(2)
            c1.code(str(row["layer1_run_dir"] or "(missing)"))
            c2.code(str(row["layer2_run_dir"] or "(missing)"))
            m1, m2, m3 = st.columns(3)
            m1.metric("L1 frames", str(row.get("n_frames_layer1", "—")))
            m2.metric("L2 frames", str(row.get("n_frames_layer2", "—")))
            m3.metric("Matched", "Yes" if row.get("is_matched") else "No")

        with st.expander("Full session index"):
            index_cols = [
                "session_id",
                "is_matched",
                "n_frames_layer1",
                "n_frames_layer2",
                "match_warning",
            ]
            st.dataframe(
                ctrl.session_index[index_cols],
                use_container_width=True,
                hide_index=True,
            )

    with tab_window:
        _render_participant_session_selectors(ctrl, participant_ids, paths["output_root"])

        st.subheader("Exercise segmentation (auto frame window)")
        ex_cols = st.columns([2, 1])
        default_ex_path = (
            st.session_state.get("exercise_file_path") or str(ctrl.default_exercise_segments)
        )
        with ex_cols[0]:
            exercise_path = Path(
                st.text_input(
                    "Segmentation file (xlsx/csv)",
                    value=default_ex_path,
                )
            )
        with ex_cols[1]:
            load_clicked = st.button("Load segmentation file", use_container_width=True)

        uploaded = st.file_uploader(
            "Or upload segmentation workbook",
            type=["xlsx", "xls", "csv"],
            help="Each Excel sheet should match a session, e.g. `671 - T1P1R2`.",
        )

        if load_clicked:
            try:
                _load_exercise_catalog_from_path(ctrl, exercise_path)
                st.success(
                    f"Loaded exercises for {len(ctrl.exercise_catalog)} session(s): "
                    f"{', '.join(sorted(ctrl.exercise_catalog))}"
                )
            except Exception as exc:
                st.error(str(exc))

        if uploaded is not None:
            try:
                ctrl.load_exercise_catalog_bytes(uploaded.getvalue(), uploaded.name)
                st.session_state.exercise_file_path = uploaded.name
                st.success(
                    f"Uploaded `{uploaded.name}` — "
                    f"{len(ctrl.exercise_catalog)} session sheet(s) parsed."
                )
            except Exception as exc:
                st.error(str(exc))

        exercise_choices = _exercise_choices(ctrl, st.session_state.get("session_id"))
        if exercise_choices:
            current_choice = st.session_state.get("exercise_choice")
            if current_choice not in exercise_choices:
                current_choice = exercise_choices[0]
            exercise_choice = st.selectbox(
                "Exercise window",
                options=exercise_choices,
                index=exercise_choices.index(current_choice),
                help="Pick a single exercise or the Group 4 bundle (exercises 9–13).",
            )
            if exercise_choice != st.session_state.get("exercise_choice"):
                st.session_state.exercise_choice = exercise_choice
                applied = ctrl.apply_exercise_selection(
                    str(st.session_state.session_id),
                    exercise_choice,
                )
                if applied:
                    start, end, label = applied
                    st.session_state.frame_start = start
                    st.session_state.frame_end = end
                    st.session_state.window_label = label
                    st.session_state.window_label_tag = _exercise_window_tag(exercise_choice)
            elif st.session_state.get("exercise_choice") is None:
                applied = ctrl.apply_exercise_selection(
                    str(st.session_state.session_id),
                    exercise_choice,
                )
                if applied:
                    start, end, label = applied
                    st.session_state.frame_start = start
                    st.session_state.frame_end = end
                    st.session_state.window_label = label
                    st.session_state.window_label_tag = _exercise_window_tag(exercise_choice)
                    st.session_state.exercise_choice = exercise_choice
        elif ctrl.exercise_catalog:
            st.warning(
                f"No exercise rows for session `{st.session_state.get('session_id')}` "
                "in the loaded segmentation file."
            )
        else:
            st.caption(
                "Load `671_ex_segmentatios_frames.xlsx` (or upload) to auto-fill frame windows."
            )

        w1, w2 = st.columns(2)
        prev_start = st.session_state.frame_start
        prev_end = st.session_state.frame_end
        st.session_state.frame_start = int(
            w1.number_input("Start frame", min_value=0, value=st.session_state.frame_start)
        )
        st.session_state.frame_end = int(
            w2.number_input("End frame", min_value=0, value=st.session_state.frame_end)
        )
        if (
            st.session_state.frame_start != prev_start
            or st.session_state.frame_end != prev_end
        ):
            _apply_manual_frames(ctrl)

        _sync_window_label(ctrl)
        st.text_input(
            "Window label (auto)",
            value=st.session_state.window_label,
            disabled=True,
            help=(
                "Format: `<session>_s<start>_e<end>` or "
                "`<session>_g4_s<start>_e<end>` for Group 4."
            ),
        )

        st.subheader("QC evidence types")
        qc_cols = st.columns(4)
        st.session_state.qc_types = _qc_types(
            qc_cols[0].checkbox("gap ≥ 0.5 s", value=True),
            qc_cols[1].checkbox("gap ≥ 0.2 s", value=True),
            qc_cols[2].checkbox("artifact_sigma", value=True),
            qc_cols[3].checkbox("segment_swap", value=True),
        )
        st.session_state.allow_nan_matrix = st.checkbox(
            "Allow NaN in JcvPCA matrix (do not impute)",
            value=st.session_state.allow_nan_matrix,
            help=(
                "Unchecked (default): export fails if any filtered-analysis rotvec is NaN. "
                "Checked: export proceeds and keeps NaNs; counts are recorded in the manifest."
            ),
        )

        st.subheader("Joint selection")
        filter_cols = st.columns(3)
        filter_cols[0].checkbox(
            "Show only core_candidate",
            key="joint_filter_core_only",
        )
        filter_cols[1].checkbox(
            "Show only directly_comparable",
            key="joint_filter_directly_comparable",
        )
        body_section_options = list(BODY_SECTION_LABELS.keys())
        filter_cols[2].selectbox(
            "Body section",
            options=body_section_options,
            format_func=lambda key: BODY_SECTION_LABELS[key],
            key="joint_filter_body_section",
        )

        visible_options = ctrl.filtered_joint_options(
            core_only=st.session_state.joint_filter_core_only,
            directly_comparable_only=st.session_state.joint_filter_directly_comparable,
            body_section=st.session_state.joint_filter_body_section,
        )
        current_filter_signature = joint_filter_signature(
            st.session_state.joint_filter_core_only,
            st.session_state.joint_filter_directly_comparable,
            st.session_state.joint_filter_body_section,
        )
        if sync_joint_selection_to_filters(
            st.session_state,
            [opt.link_id for opt in visible_options],
            current_filter_signature,
        ):
            st.rerun()

        btn_cols = st.columns(4)
        if btn_cols[0].button("Select all visible"):
            visible_ids = [opt.link_id for opt in visible_options]
            set_selected_joints(
                st.session_state,
                sorted(set(st.session_state.selected_joints) | set(visible_ids)),
            )
            st.rerun()
        if btn_cols[1].button("Select directly comparable"):
            comparable_ids = ctrl.directly_comparable_joint_ids()
            set_selected_joints(st.session_state, comparable_ids)
            if not comparable_ids:
                st.session_state["joint_selection_notice"] = (
                    "No directly comparable joints — run discovery and ensure matched "
                    "Layer 2 sessions."
                )
            st.rerun()
        if btn_cols[2].button("Select core joints"):
            set_selected_joints(st.session_state, ctrl.core_joint_ids())
            st.rerun()
        if btn_cols[3].button("Clear selection"):
            set_selected_joints(st.session_state, [])
            st.rerun()
        if st.button("Reload joint list") and ctrl.current_row is not None:
            ctrl.load_joints(str(ctrl.current_row["layer2_run_dir"] or ""))
            set_selected_joints(st.session_state, ctrl.default_selected_joint_ids())
            st.session_state["joint_selection_notice"] = (
                f"Reloaded {len(ctrl.joint_options)} joints from Layer 2 manifest."
            )
            st.rerun()

        notice = st.session_state.pop("joint_selection_notice", None)
        if notice:
            if notice.startswith("No directly comparable"):
                st.warning(notice)
            else:
                st.success(notice)

        st.markdown("**Joints (canonical_link_name)**")
        _render_joint_checkboxes(ctrl, visible_options)

        n_core = sum(1 for opt in ctrl.joint_options if opt.is_core)
        n_visible = len(visible_options)
        n_selected = len(st.session_state.selected_joints)
        st.caption(
            f"{len(ctrl.joint_options)} joints loaded ({n_core} core_candidate). "
            f"{n_visible} visible · {n_selected} selected."
        )

    selected_link_ids: list[str] = st.session_state.selected_joints

    with tab_warnings:
        if st.button("Preview warnings", type="secondary"):
            st.session_state.warning_summary = ctrl.summarize_warnings(selected_link_ids)

        summary = st.session_state.get("warning_summary")
        if summary is None and ctrl.current_row is not None:
            summary = ctrl.summarize_warnings(selected_link_ids)
            st.session_state.warning_summary = summary

        if summary is None:
            st.info("Select a session, then preview warnings.")
        else:
            if summary.has_blocking:
                st.markdown('<p class="verdict-blocked">EXPORT BLOCKED</p>', unsafe_allow_html=True)
            elif summary.requires_user_approval:
                st.markdown(
                    '<p class="verdict-strong">EXPORT ALLOWED — strong warnings need review</p>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown('<p class="verdict-ok">EXPORT ALLOWED</p>', unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Blocking", summary.n_blocking)
            c2.metric("Strong", summary.n_strong_warning)
            c3.metric("Warning", summary.n_warning)
            c4.metric("Info", summary.n_info)
            st.subheader("Warning details")
            if summary.dataframe.empty:
                st.success("No warnings.")
            else:
                st.dataframe(summary.dataframe, use_container_width=True, hide_index=True)

    with tab_export:
        summary = st.session_state.get("warning_summary")
        export_disabled = summary.has_blocking if summary else True
        st.write(
            "Writes canonical `window_jvcpca_matrix.parquet`, `window_warnings.csv`, "
            "and `window_export_manifest.json` (with `layer3_safe=true` when checks pass)."
        )
        if export_disabled:
            st.warning(
                "Export is disabled until blocking warnings are resolved. "
                "Preview warnings first."
            )

        if st.button("Export Layer 3 window", type="primary", disabled=export_disabled):
            row = ctrl.current_row
            if row is None:
                st.error("Select a participant and session first.")
            else:
                try:
                    st.session_state.export_result = ctrl.export_window(
                        layer1_dir=Path(str(row["layer1_run_dir"])),
                        layer2_dir=Path(str(row["layer2_run_dir"])),
                        output_root=paths["output_root"],
                        window_label=st.session_state.window_label,
                        frame_start=st.session_state.frame_start,
                        frame_end=st.session_state.frame_end,
                        selected_link_ids=selected_link_ids,
                        allow_nan_matrix=st.session_state.allow_nan_matrix,
                    )
                except Exception as exc:
                    st.error(str(exc))

        result = st.session_state.get("export_result")
        if result:
            if result.status == "blocked":
                st.error(result.message)
                if result.warnings_csv:
                    st.dataframe(pd.read_csv(result.warnings_csv), use_container_width=True)
            else:
                st.success(result.message)
                st.json(result.manifest)
                if result.matrix_preview is not None:
                    st.subheader("Matrix preview")
                    st.dataframe(result.matrix_preview, use_container_width=True)
                if result.manifest.get("requires_user_approval"):
                    st.warning(
                        "Strong warnings present — review window_warnings.csv "
                        "before using this export for Layer 3."
                    )
                if result.paths:
                    st.markdown("**Output files**")
                    for name, path in sorted(result.paths.items()):
                        st.code(f"{name}: {path}")

    with tab_diagnostics:
        st.caption("Mapping / full review write to the same window folder as Layer 3 export.")
        d1, d2, d3 = st.columns(3)
        run_mapping = d1.button("Run mapping table")
        run_review = d2.button("Run full review")
        show_tables = d3.button("Show review tables")

        row = ctrl.current_row
        layer1 = Path(str(row["layer1_run_dir"])) if row is not None else None
        layer2 = Path(str(row["layer2_run_dir"])) if row is not None else None

        if run_mapping and layer1 and layer2:
            try:
                mapping_path, df = ctrl.run_mapping(
                    layer1_dir=layer1,
                    layer2_dir=layer2,
                    output_root=paths["output_root"],
                    window_label=st.session_state.window_label,
                    selected_link_ids=selected_link_ids,
                    datadescriptions=paths["datadescriptions"],
                )
                st.success(f"Wrote {mapping_path}")
                st.dataframe(df, use_container_width=True)
            except Exception as exc:
                st.error(str(exc))

        if run_review and layer1 and layer2:
            try:
                review_paths = ctrl.run_full_review(
                    layer1_dir=layer1,
                    layer2_dir=layer2,
                    output_root=paths["output_root"],
                    window_label=st.session_state.window_label,
                    frame_start=st.session_state.frame_start,
                    frame_end=st.session_state.frame_end,
                    selected_link_ids=selected_link_ids,
                    qc_evidence=st.session_state.qc_types,
                    datadescriptions=paths["datadescriptions"],
                )
                st.success(f"Review complete — wrote {len(review_paths)} artifacts.")
                summary_path = review_paths.get("window_decision_summary.csv")
                if summary_path and Path(summary_path).is_file():
                    st.dataframe(pd.read_csv(summary_path), use_container_width=True)
            except Exception as exc:
                st.error(str(exc))

        if show_tables:
            try:
                tables = ctrl.load_review_tables(
                    paths["output_root"],
                    st.session_state.window_label,
                )
                if not tables:
                    st.warning("No review tables found for the current window folder.")
                for title, df, max_rows in tables:
                    st.subheader(title)
                    st.dataframe(df.head(max_rows) if max_rows else df, use_container_width=True)
            except Exception as exc:
                st.error(str(exc))


if __name__ == "__main__":
    main()
