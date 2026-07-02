"""Stage 6 decision summary reader (canonical + new batches)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from comparability import ComparabilityStatus
from decision_summary import compare_batch_summaries, load_batch_decision_summary
from g2_components import render_comparability_banner
from g6_controls import g6_is_enabled, render_g6_confirmation
from g6_execution import assert_non_canonical_batch_path, execute_on_demand_reports
from project_status import ProjectSnapshot
from ui_bootstrap import REPO_ROOT


def _list_batches(snapshot: ProjectSnapshot) -> list[tuple[str, Path, bool]]:
    batches: list[tuple[str, Path, bool]] = []
    if snapshot.canonical_batch_path and snapshot.canonical_batch_exists:
        batches.append(("Canonical batch", snapshot.canonical_batch_path, True))
    outputs_root = snapshot.paths.get("layer3.outputs_root")
    if outputs_root.is_dir():
        for path in sorted(outputs_root.glob("gaga_batch_jcvpca_*"), reverse=True):
            if snapshot.canonical_batch_path and path.resolve() == snapshot.canonical_batch_path.resolve():
                continue
            batches.append((path.name, path, False))
    return batches


def render_decision_summary_reader(snapshot: ProjectSnapshot) -> None:
    st.subheader("Batch results reader")
    st.caption("Read-only rollup: comparison status, link_focus ledgers, effect-vs-NV, and batch diff vs canonical.")

    batches = _list_batches(snapshot)
    if not batches:
        st.info("No Layer 3 batch directories found.")
        return

    labels = [label for label, _, _ in batches]
    default_index = 0
    last_batch = st.session_state.get("last_g6_batch_root")
    if last_batch:
        for idx, (_, path, _) in enumerate(batches):
            if str(path) == last_batch or path.name == Path(last_batch).name:
                default_index = idx
                break

    choice = st.selectbox("Batch", options=labels, index=default_index)
    _, batch_path, is_canonical = next(item for item in batches if item[0] == choice)

    summary = load_batch_decision_summary(
        batch_path,
        current_science_hash=snapshot.config.science_hash,
        is_canonical=is_canonical,
    )

    c1, c2, c3, c4 = st.columns(4)
    cs = summary["comparison_status"]
    c1.metric("Comparisons completed", f"{cs['completed']}/{cs['total']}")
    c2.metric("Config hash", (summary.get("config_hash") or "—")[:16] + "…")
    c3.metric("Comparability", summary.get("comparability", "unknown"))
    c4.metric("Link-focus exclusions", summary.get("link_focus_excluded_count", 0))

    render_comparability_banner(
        ComparabilityStatus(summary.get("comparability", ComparabilityStatus.UNKNOWN.value)),
        artifact_label=f"Batch {summary['batch_id']}",
        artifact_hash=summary.get("config_hash"),
        current_hash=snapshot.config.science_hash,
    )

    st.markdown("**Request provenance**")
    st.json(summary.get("request_provenance") or {})

    if summary.get("link_focus"):
        st.markdown("**Link focus (PCA input filtering)**")
        st.dataframe(summary["link_focus"], use_container_width=True, hide_index=True)
        ledger_path = batch_path / "link_focus_ledger_by_comparison.csv"
        if ledger_path.is_file():
            with st.expander("Link focus ledger (included/excluded with reasons)"):
                st.dataframe(pd.read_csv(ledger_path), use_container_width=True, hide_index=True)
        st.caption(
            "When `link_focus_changes_pca_basis` is true, filtering happened **before PCA input construction** "
            "(analysis feature filter, not display-only)."
        )

    on_demand = summary.get("on_demand_reports") or {}
    if on_demand:
        st.markdown("**On-demand report policies**")
        st.json(on_demand.get("policies") or {})
        artifacts = on_demand.get("artifacts") or {}
        if artifacts:
            rows = []
            for name, meta in artifacts.items():
                if isinstance(meta, dict):
                    rows.append(
                        {
                            "artifact": name,
                            "status": meta.get("status"),
                            "output_path": meta.get("output_path"),
                        }
                    )
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)

    if not is_canonical and g6_is_enabled():
        st.divider()
        st.markdown("**Generate on-demand reports (G6)**")
        st.caption("Runs heavy numeric/poster packages into this timestamped batch folder only.")
        try:
            assert_non_canonical_batch_path(batch_path, snapshot)
        except Exception as exc:
            st.error(str(exc))
        else:
            confirmed = render_g6_confirmation(
                action_label="Generate on-demand Layer 3 reports",
                write_paths=[
                    str(batch_path / "Gaga_JcvPCA_MASTER_full_numeric_report.md"),
                    str(batch_path / "poster_ready_evidence_package"),
                    str(batch_path / "on_demand_reports_manifest.json"),
                ],
            )
            if st.button("Generate reports now", disabled=not confirmed):
                with st.spinner("Generating on-demand reports…"):
                    result = execute_on_demand_reports(
                        REPO_ROOT,
                        snapshot,
                        batch_path,
                    )
                st.success("On-demand report generation finished.")
                st.json(result.get("manifest") or {})
                st.rerun()

    st.markdown("**Effect vs natural variability (batch NV table)**")
    nv = summary.get("effect_vs_nv") or {}
    if nv:
        st.write(nv)
    else:
        st.caption("No `nv_baseline_results.csv` summary available for this batch.")

    st.markdown("**Comparison status**")
    if cs.get("rows"):
        st.dataframe(cs["rows"], use_container_width=True, hide_index=True)
    else:
        st.caption("No comparison_status.csv rows.")

    if not is_canonical and snapshot.canonical_batch_path and snapshot.canonical_batch_exists:
        st.divider()
        st.markdown("**Diff vs canonical batch**")
        baseline = load_batch_decision_summary(
            snapshot.canonical_batch_path,
            current_science_hash=snapshot.config.science_hash,
            is_canonical=True,
        )
        diff = compare_batch_summaries(baseline, summary)
        d1, d2, d3 = st.columns(3)
        d1.metric("Baseline completed", diff.get("baseline_completed"))
        d2.metric("Candidate completed", diff.get("candidate_completed"))
        d3.metric("Config hash match", "yes" if diff.get("config_hash_match") else "no")
        if diff.get("comparison_diff"):
            st.dataframe(diff["comparison_diff"], use_container_width=True, hide_index=True)

    st.markdown("**Top links (by |JcvPCA|)**")
    if summary.get("top_links"):
        st.dataframe(summary["top_links"], use_container_width=True, hide_index=True)
    else:
        st.caption("No link-level results found.")

    st.markdown("**Body regions**")
    if summary.get("body_regions"):
        st.dataframe(summary["body_regions"], use_container_width=True, hide_index=True)

    if summary.get("batch_summary_exists"):
        with st.expander("batch_summary.md"):
            st.markdown((batch_path / "batch_summary.md").read_text(encoding="utf-8"))
