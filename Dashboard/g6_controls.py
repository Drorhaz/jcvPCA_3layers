"""G6 sidebar toggle and confirmation widgets."""

from __future__ import annotations

import streamlit as st

from g6_execution import G6_SESSION_KEY


def init_g6_sidebar() -> bool:
    """Render sidebar G6 toggle; return whether guarded execution is enabled."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("G6 — Guarded execution")
    enabled = st.sidebar.checkbox(
        "Enable guarded execution",
        value=bool(st.session_state.get(G6_SESSION_KEY, False)),
        help="Unlocks run triggers on Stages 2–4 and 6, config edits on Stage 7, "
        "and verification persistence on Stage 5. Never targets the canonical batch.",
        key="g6_execution_toggle",
    )
    st.session_state[G6_SESSION_KEY] = enabled
    if enabled:
        st.sidebar.warning("Run triggers active. Canonical batch is protected.")
    else:
        st.sidebar.caption("G1–G5 read-only mode (dry-run plans only).")
    return enabled


def g6_is_enabled() -> bool:
    return bool(st.session_state.get(G6_SESSION_KEY, False))


def render_g6_confirmation(
    *,
    action_label: str,
    write_paths: list[str],
    extra_checks: list[str] | None = None,
) -> bool:
    """Return True when the user confirmed the guarded action."""
    st.markdown(f"**G6 action:** {action_label}")
    if write_paths:
        st.caption("Writes to:")
        for path in write_paths:
            st.code(path, language="text")
    checks = [
        "I understand this runs real pipeline commands (not a dry-run).",
        "I confirm output paths do not target the canonical Layer 3 batch.",
    ]
    checks.extend(extra_checks or [])
    confirmed = all(
        st.checkbox(label, key=f"g6_confirm_{idx}_{action_label[:24]}")
        for idx, label in enumerate(checks)
    )
    return confirmed
