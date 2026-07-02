"""Shared G2 read-only Streamlit UI helpers."""

from __future__ import annotations

from typing import Any

import streamlit as st

from comparability import ComparabilityStatus, comparability_banner_text, threshold_badge_flags
from project_status import REGISTRY_COVERAGE

STATUS_COLORS = {
    "pass": "#2e7d32",
    "warn": "#ed6c02",
    "warning": "#ed6c02",
    "fail": "#b00020",
    "block": "#b00020",
    "blocking": "#b00020",
    "strong_warning": "#d35400",
    "missing": "#546e7a",
    "unknown": "#78909c",
    "ok": "#2e7d32",
    "partial": "#ed6c02",
    "review_required": "#ed6c02",
    "ready": "#2e7d32",
    "proceed_with_caution": "#ed6c02",
}


def inject_g2_css() -> None:
    st.markdown(
        """
        <style>
          .block-container { padding-top: 1.25rem; max-width: 1200px; }
          .g2-banner {
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin: 0.5rem 0 1rem 0;
            font-size: 0.92rem;
          }
          .g2-banner-warn {
            background: #fff8e1;
            border-color: #ffcc80;
          }
          .g2-badge {
            display: inline-block;
            padding: 0.1rem 0.45rem;
            margin: 0.1rem 0.15rem 0.1rem 0;
            border-radius: 4px;
            font-size: 0.78rem;
            font-weight: 600;
            border: 1px solid #cbd5e1;
            background: #eef2f7;
          }
          .g2-status-pill {
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 700;
            color: white;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_curated_registry_banner() -> None:
    st.markdown(
        """
        <div class="g2-banner g2-banner-warn">
          <b>Governed threshold registry — curated, not complete.</b>
          L3 is fully mirrored in <code>config/analysis_params.yaml</code>.
          L1/L2/L2.5 show high-impact subsets only (<code>config/qc_rules.yaml</code>).
          Traffic lights cite registered thresholds; unregistered layer knobs remain in layer YAML.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_coverage_banners() -> None:
    cols = st.columns(4)
    for idx, (layer, meta) in enumerate(REGISTRY_COVERAGE.items()):
        label = meta["label"]
        mirrored = meta["mirrored"]
        cols[idx].metric(layer.upper(), mirrored, delta=label, delta_color="off")


def status_pill(status: str) -> str:
    color = STATUS_COLORS.get(status.lower(), "#78909c")
    return (
        f'<span class="g2-status-pill" style="background:{color};">'
        f"{status}</span>"
    )


def render_status_pill(status: str) -> None:
    st.markdown(status_pill(status), unsafe_allow_html=True)


def render_comparability_banner(
    status: ComparabilityStatus,
    *,
    artifact_label: str,
    artifact_hash: str | None,
    current_hash: str,
) -> None:
    css = "g2-banner" if status == ComparabilityStatus.COMPARABLE else "g2-banner g2-banner-warn"
    text = comparability_banner_text(
        status,
        artifact_label=artifact_label,
        artifact_hash=artifact_hash,
        current_hash=current_hash,
    )
    st.markdown(f'<div class="{css}">{text}</div>', unsafe_allow_html=True)


def render_threshold_badges(threshold: Any) -> None:
    flags = threshold_badge_flags(threshold)
    badges: list[str] = []
    if flags["differs_from_default"]:
        badges.append("differs from default")
    if flags["differs_from_canonical"]:
        badges.append("differs from canonical")
    if flags["differs_from_scope_approved"]:
        badges.append("differs from scope-approved")
    if flags["scope_locked"]:
        badges.append("scope-locked")
    if flags["requires_approval"]:
        badges.append("requires approval")
    if flags["gui_editable_later"]:
        badges.append("GUI-editable later (G6)")
    if not badges:
        st.caption("No badge flags.")
        return
    html = " ".join(f'<span class="g2-badge">{b}</span>' for b in badges)
    st.markdown(html, unsafe_allow_html=True)


def render_advisory_banner(text: str = "Advisory only — recommendations guide review; they are not final exclusion decisions.") -> None:
    st.markdown(
        f'<div class="g2-banner g2-banner-warn"><b>{text}</b></div>',
        unsafe_allow_html=True,
    )


def render_recommendation(rec: Any) -> None:
    """Render one Recommendation dataclass."""
    cols = st.columns([2, 3])
    with cols[0]:
        st.markdown(f"**{rec.gate}**")
        render_status_pill(rec.verdict)
        if getattr(rec, "advisory_label", None):
            st.caption(rec.advisory_label)
    with cols[1]:
        for reason in rec.reasons:
            st.write(reason)
        if rec.threshold_refs:
            st.caption("Threshold / policy refs: " + ", ".join(f"`{r}`" for r in rec.threshold_refs))


def render_verdict_card(card: Any) -> None:
    """Render a VerdictCard (explanation-first; headline is not sufficient alone)."""
    headline = getattr(card, "headline", "Unknown")
    color = STATUS_COLORS.get(headline.lower().replace(" ", "_"), "#546e7a")
    if headline == "Ready":
        color = STATUS_COLORS["ready"]
    elif "caution" in headline.lower():
        color = STATUS_COLORS["proceed_with_caution"]
    elif headline in {"Blocked", "Not recommended"}:
        color = STATUS_COLORS["fail"]
    elif "Missing" in headline:
        color = STATUS_COLORS["missing"]

    st.markdown(
        f'<div class="g2-banner" style="border-left:4px solid {color};">'
        f"<b>{headline}</b>"
        f"{(' · ' + card.subject_id) if getattr(card, 'subject_id', '') else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.write(getattr(card, "explanation", ""))
    evidence = getattr(card, "evidence", ()) or ()
    if evidence:
        rows = []
        for item in evidence:
            rows.append(
                {
                    "issue_type": item.issue_type,
                    "scope": item.scope,
                    "severity": item.severity,
                    "blocks_L3": item.blocks_layer3,
                    "threshold_key": item.threshold_key,
                    "threshold_value": item.threshold_value,
                    "observed_value": item.observed_value,
                    "detail": (item.detail or "")[:200],
                    "qc_source": item.qc_source,
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
    if getattr(card, "consequence", ""):
        st.caption(f"**Interpretation:** {card.consequence}")
    if getattr(card, "action", ""):
        st.caption(f"**Recommended action:** {card.action}")


@st.cache_data(show_spinner=False)
def cache_load_snapshot():
    """Streamlit cache wrapper for read-only project snapshot."""
    from project_status import load_project_snapshot

    return load_project_snapshot()


def render_discovered_participants_banner(snapshot: Any) -> None:
    """Show merged participant inventory and config drift advisories."""
    discovery = getattr(snapshot, "participant_discovery", None)
    if discovery is None or not discovery.participant_ids:
        st.warning(
            "No participants discovered yet. Add raw data / segmentation xlsx / session outputs, "
            "then run **Stage 1 — Discover & repair index**."
        )
        return

    st.success(
        f"**Discovered participants ({discovery.count}):** "
        + ", ".join(discovery.participant_ids)
        + (f" · default `{discovery.default_participant}`" if discovery.default_participant else "")
    )
    if discovery.discovered_not_registered:
        st.info(
            "New participant(s) detected on disk but not listed in `config/paths.yaml` "
            f"`participants.batch_cohort`: {', '.join(discovery.discovered_not_registered)}. "
            "They are fully supported by the GUI; add them to config when you want them registered."
        )
    if discovery.registered_not_discovered:
        st.caption(
            "Registered in config but not yet found on disk: "
            + ", ".join(discovery.registered_not_discovered)
        )


def participant_selectbox(
    snapshot: Any,
    *,
    label: str = "Participant",
    key: str | None = None,
) -> str | None:
    """Participant picker backed by discovered cohort (not hardcoded lists)."""
    if not snapshot.participants:
        st.warning(
            "No participants discovered. Add data under `data/raw_layer2/{id}/`, "
            "segmentation xlsx, or L1/L2 outputs, then refresh Stage 1."
        )
        return None
    index = 0
    default_pid = getattr(snapshot, "default_participant", "") or snapshot.participants[0]
    if default_pid in snapshot.participants:
        index = snapshot.participants.index(default_pid)
    kwargs: dict[str, Any] = {
        "label": label,
        "options": snapshot.participants,
        "index": index,
    }
    if key:
        kwargs["key"] = key
    return st.selectbox(**kwargs)
