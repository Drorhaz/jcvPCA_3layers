"""Shared session selection + dry-run command preview for Stages 2–3."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from g6_controls import g6_is_enabled, render_g6_confirmation
from g6_execution import execute_pipeline_commands, log_pipeline_results
from project_paths import ProjectPaths
from session_pipeline import (
    load_session_index,
    plan_layer1_commands,
    plan_layer2_commands,
    processed_session_index_path,
    rebuild_session_index,
)


def ensure_index_in_session(paths: ProjectPaths) -> pd.DataFrame:
    index_path = processed_session_index_path(paths)
    key = "discovered_index"
    if key not in st.session_state:
        st.session_state[key] = load_session_index(index_path)
    return st.session_state[key]


def render_session_picker(index_df: pd.DataFrame) -> list[dict[str, Any]]:
    participant_filter = st.multiselect(
        "Participants",
        options=sorted(index_df["participant_id"].astype(str).unique()),
        default=sorted(index_df["participant_id"].astype(str).unique()),
    )
    filtered = index_df[index_df["participant_id"].astype(str).isin(participant_filter)]
    session_options = filtered["session_id"].astype(str).tolist()
    selected = st.multiselect("Sessions", options=session_options, default=session_options)
    return filtered[filtered["session_id"].astype(str).isin(selected)].to_dict("records")


def render_dry_run_commands(planned: list[Any]) -> None:
    if not planned:
        st.info("No commands in plan.")
        return
    for i, cmd in enumerate(planned, start=1):
        with st.expander(f"{i}. {cmd.description}", expanded=i == 1):
            st.code(" ".join(cmd.argv) if cmd.argv else "(blocked — missing inputs)", language="bash")
            st.caption(f"cwd: `{cmd.cwd}` · sessions: {', '.join(cmd.session_ids)}")


def render_g6_execute_panel(
    planned: list[Any],
    *,
    repo_root: Path,
    layer_label: str,
    write_paths: list[str] | None = None,
) -> None:
    """Show guarded run controls when G6 is enabled in the sidebar."""
    st.divider()
    st.subheader(f"G6 guarded execution — {layer_label}")

    if not g6_is_enabled():
        st.info("Enable **G6 guarded execution** in the sidebar to run these commands.")
        return

    blocked = [cmd for cmd in planned if not cmd.argv]
    if blocked:
        st.error(f"{len(blocked)} command(s) are blocked (missing inputs). Fix the plan before running.")
        return

    paths = write_paths or []
    for cmd in planned:
        if cmd.cwd:
            paths.append(str(cmd.cwd))
    paths = sorted(set(paths))

    confirmed = render_g6_confirmation(action_label=f"Run {layer_label}", write_paths=paths)
    if st.button(f"Run {layer_label} (guarded)", type="primary", disabled=not confirmed):
        with st.spinner(f"Running {layer_label}…"):
            results = execute_pipeline_commands(planned, dry_run=False)
            log_path = log_pipeline_results(repo_root, results, action=layer_label)
        failures = [r for r in results if r.returncode != 0]
        if failures:
            st.error(f"{len(failures)} command(s) failed. See log: `{log_path}`")
        else:
            st.success(f"All {len(results)} command(s) completed. Log: `{log_path}`")
        for result in results:
            with st.expander(f"{result.planned.description} — exit {result.returncode}"):
                if result.stdout:
                    st.text("stdout")
                    st.code(result.stdout[-8000:])
                if result.stderr:
                    st.text("stderr")
                    st.code(result.stderr[-8000:])
