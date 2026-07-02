"""G5 execution plan UI (Stage 6 tab)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

from analysis_config import load_analysis_config
from analysis_request import load_analysis_request
from execution_plan import build_execution_plan, save_execution_plan
from g2_components import render_advisory_banner, render_comparability_banner, status_pill
from g6_controls import g6_is_enabled, render_g6_confirmation
from g6_execution import assert_non_canonical_batch_path, execute_layer3_batch, prepare_plan_for_g6_execution
from project_status import ProjectSnapshot
from ui_bootstrap import REPO_ROOT


def render_execution_plan(snapshot: ProjectSnapshot, *, verification_unlocked: bool = False) -> None:
    if g6_is_enabled():
        render_advisory_banner(
            "G6 enabled — guarded Layer 3 batch runs available when preflight passes and Stage 5 sign-off exists."
        )
    else:
        render_advisory_banner(
            "Dry-run execution planning only. Enable G6 in the sidebar to run a timestamped batch."
        )
    requests_dir = REPO_ROOT / "requests" / "analysis_requests"
    saved_requests: list[Path] = []
    if requests_dir.is_dir():
        saved_requests = sorted(requests_dir.glob("*.yaml"))

    session_request = st.session_state.get("g4_request")

    source = st.radio(
        "Request source",
        options=["Saved YAML", "Builder session (Stage 6 tab)"],
        horizontal=True,
        index=0 if not session_request else 1,
    )

    request: dict | None = None
    request_path: Path | None = None

    if source == "Builder session (Stage 6 tab)":
        if session_request:
            request = session_request
            st.success(f"Using in-memory request `{session_request.get('request_id', '?')}` from Analysis Request tab.")
        else:
            st.warning("No validated request in session. Validate one on the Analysis request tab first.")
    else:
        if saved_requests:
            labels = [p.name for p in saved_requests]
            choice = st.selectbox("Saved analysis request", options=labels)
            request_path = requests_dir / choice
            try:
                request = load_analysis_request(request_path)
            except Exception as exc:
                st.error(f"Failed to load request: {exc}")
        else:
            st.info(f"No saved requests in `{requests_dir}`. Save one from Stage 6 Analysis request tab.")

    if request and st.button("Build dry-run execution plan", type="primary"):
        st.session_state["g5_plan"] = build_execution_plan(
            snapshot,
            request,
            request_path=request_path,
        )

    plan = st.session_state.get("g5_plan")
    if not plan:
        st.info("Select a request and click **Build dry-run execution plan**.")
        st.stop()

    g6_plan = prepare_plan_for_g6_execution(plan) if g6_is_enabled() else plan
    execution_allowed = bool(g6_plan.get("execution", {}).get("allowed"))

    st.subheader("Plan status")
    exec_label = "enabled (G6)" if execution_allowed else "disabled"
    st.markdown(
        f"**Plan status:** {status_pill(g6_plan.get('plan_status', 'unknown'))} · "
        f"**Execution:** {exec_label}",
        unsafe_allow_html=True,
    )

    pf = g6_plan.get("preflight", {})
    c1, c2, c3 = st.columns(3)
    c1.metric("Blockers", len(pf.get("blockers", [])))
    c2.metric("Warnings", len(pf.get("warnings", [])))
    c3.metric("Advisory", len(pf.get("advisory_notes", [])))

    for label, key in (("Blockers", "blockers"), ("Warnings", "warnings"), ("Advisory", "advisory_notes")):
        items = pf.get(key, [])
        if items:
            st.markdown(f"**{label}**")
            for item in items:
                st.write(f"- [{item.get('source', '?')}] `{item.get('code', '')}` — {item.get('message', '')}")

    runner = plan.get("runner_translation", {})
    st.subheader("Runner translation")
    r1, r2, r3 = st.columns(3)
    r1.metric("Requested jobs", runner.get("requested_job_count", 0))
    r2.metric("Runner default jobs (same participant)", runner.get("current_runner_default_job_count", 0))
    r3.metric("Resolved segments", len(runner.get("resolved_segments", [])))

    st.code(runner.get("invocation_preview", {}).get("command", ""), language="bash")
    st.caption(runner.get("invocation_preview", {}).get("note", ""))

    if runner.get("compatibility_gaps"):
        st.markdown("**Runner compatibility gaps**")
        for gap in runner["compatibility_gaps"]:
            st.write(f"- `{gap.get('code')}`: {gap.get('message')}")

    st.markdown("**Proposed batch**")
    st.write(
        f"- Batch ID: `{runner.get('proposed_batch_id')}`\n"
        f"- Root: `{runner.get('proposed_batch_root')}`\n"
        f"- Layer 2.5 root: `{runner.get('layer25_root')}`"
    )

    jobs = runner.get("requested_jobs") or []
    if jobs:
        st.dataframe(
            [
                {
                    "comparison_key": j["comparison_key"],
                    "block": j["block_id"],
                    "exercises": "+".join(j["block_exercises"]),
                    "comparison": j["comparison_id"],
                    "mode": j["analysis_mode"],
                    "output_dir": j["comparison_output_dir"],
                }
                for j in jobs
            ],
            use_container_width=True,
            hide_index=True,
        )

    out = plan.get("output_plan", {})
    st.subheader("Expected outputs")
    st.write(f"**Batch root:** `{out.get('proposed_batch_root')}`")
    st.caption(
        f"Canonical batch `{out.get('unchanged_canonical', {}).get('batch_id')}` "
        f"— policy: {out.get('unchanged_canonical', {}).get('policy')}"
    )
    with st.expander("Batch artifact classes"):
        st.write(", ".join(out.get("batch_level_artifacts", [])))
    with st.expander("Comparison output directories"):
        for d in out.get("comparison_directories", []):
            st.write(f"- `{d}`")

    repro = plan.get("reproducibility_package", {})
    st.subheader("Reproducibility package (future `_config_snapshot/`)")
    st.caption(repro.get("write_policy", ""))
    render_comparability_banner(
        snapshot.canonical_comparability,
        artifact_label=f"Canonical batch {snapshot.canonical_batch_id}",
        artifact_hash=snapshot.canonical_config_hash,
        current_hash=snapshot.config.science_hash,
    )
    with st.expander("Would copy / generate"):
        st.json(repro)

    st.subheader("Full plan YAML")
    st.download_button(
        "Download execution_plan.yaml",
        data=yaml.safe_dump(plan, sort_keys=False, allow_unicode=True),
        file_name=f"{plan.get('source_request_id', 'plan')}_execution_plan.yaml",
        mime="text/yaml",
    )
    if st.button("Save to requests/execution_plans/"):
        path = save_execution_plan(REPO_ROOT, plan)
        st.success(f"Saved dry-run plan (no execution): `{path}`")

    if g6_is_enabled():
        st.divider()
        st.subheader("G6 guarded Layer 3 batch run")
        runner = g6_plan.get("runner_translation", {})
        batch_root = Path(runner.get("proposed_batch_root", ""))
        custom_batch = st.text_input(
            "Optional custom batch folder name",
            value=batch_root.name,
            help="Must not match the canonical batch id.",
        )
        if custom_batch.strip():
            batch_root = batch_root.parent / custom_batch.strip()

        try:
            assert_non_canonical_batch_path(batch_root, snapshot)
            st.caption(f"Target batch root: `{batch_root}`")
        except Exception as exc:
            st.error(str(exc))
            st.stop()

        can_run = execution_allowed and verification_unlocked
        if not verification_unlocked:
            st.warning("Stage 5 verification sign-off required before running Layer 3.")
        if not execution_allowed:
            st.warning("Resolve preflight blockers before running Layer 3.")

        confirmed = render_g6_confirmation(
            action_label="Run Layer 3 JcvPCA batch",
            write_paths=[str(batch_root)],
        )
        if st.button(
            "Run Layer 3 batch (guarded)",
            type="primary",
            disabled=not (can_run and confirmed),
        ):
            runner_plan = dict(runner)
            runner_plan["proposed_batch_root"] = str(batch_root)
            runner_plan["proposed_batch_id"] = batch_root.name
            request_path = plan.get("source_request_path")
            with st.spinner("Running Layer 3 batch (this may take a long time)…"):
                result = execute_layer3_batch(
                    REPO_ROOT,
                    snapshot,
                    runner_plan,
                    batch_root=batch_root,
                    analysis_request_path=request_path,
                )
            if result["returncode"] == 0:
                cfg = load_analysis_config(project_root=REPO_ROOT)
                snap_dir = cfg.write_snapshot(batch_root)
                st.session_state["last_g6_batch_root"] = str(batch_root)
                st.success(f"Batch complete: `{batch_root}` · config snapshot: `{snap_dir}`")
            else:
                st.error(f"Batch failed (exit {result['returncode']}). See stderr below.")
            if result.get("stdout"):
                st.code(result["stdout"][-12000:])
            if result.get("stderr"):
                st.code(result["stderr"][-12000:])
