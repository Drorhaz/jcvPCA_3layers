"""Stage 7 — Config / Thresholds (read-only until G6)."""

from __future__ import annotations

import streamlit as st

from analysis_config import ConfigValidationError, SCIENCE_CONFIG_FILES, load_analysis_config
from g2_components import (
    cache_load_snapshot,
    inject_g2_css,
    render_comparability_banner,
    render_curated_registry_banner,
    render_threshold_badges,
)
from g6_controls import g6_is_enabled, init_g6_sidebar
from stage_layout import render_stage_header
from ui_bootstrap import REPO_ROOT, configure_python_paths

configure_python_paths()

st.set_page_config(page_title="Config / Thresholds", page_icon="⚙️", layout="wide")
inject_g2_css()
render_curated_registry_banner()
init_g6_sidebar()

snapshot = cache_load_snapshot()
render_stage_header(
    snapshot,
    stage=7,
    title="Config / Thresholds",
    caption="Read-only registry by default. Enable G6 to edit `gui_editable` thresholds (audited).",
)

config = snapshot.config

c1, c2 = st.columns(2)
c1.metric("Science hash", config.science_hash[:16] + "…")
c2.metric("Display hash", config.display_hash[:16] + "…")
with st.expander("Full hashes"):
    st.code(f"science_hash: {config.science_hash}\ndisplay_hash: {config.display_hash}")

render_comparability_banner(
    snapshot.canonical_comparability,
    artifact_label=f"Canonical batch {snapshot.canonical_batch_id}",
    artifact_hash=snapshot.canonical_config_hash,
    current_hash=config.science_hash,
)

file_filter = st.selectbox(
    "Config file",
    options=list(SCIENCE_CONFIG_FILES) + ["gui_settings.yaml", "all"],
    index=0,
)
layer_filter = st.selectbox(
    "Layer prefix",
    options=["all", "layer1", "layer2", "layer2_5", "pca", "pc_focus", "weighting", "cohort", "outputs"],
)

thresholds = sorted(config.thresholds.values(), key=lambda t: t.key)
if file_filter != "all":
    thresholds = [t for t in thresholds if t.file == file_filter]
if layer_filter != "all":
    thresholds = [t for t in thresholds if t.key.startswith(layer_filter + ".") or t.key.startswith(layer_filter)]

st.subheader(f"Threshold entries ({len(thresholds)} shown)")
st.caption(
    "L3 (`analysis_params.yaml`) is fully registered. "
    "L1/L2/L2.5 entries in `qc_rules.yaml` are curated high-impact subsets."
)

if g6_is_enabled():
    st.info("G6 editing enabled — changes write to YAML and append to `config/change_audit.log`.")

for t in thresholds:
    title = f"`{t.key}` = {t.value!r}"
    with st.expander(title):
        v1, v2, v3, v4 = st.columns(4)
        v1.write(f"**Current:** {t.value!r}")
        v2.write(f"**Default:** {t.default!r}")
        cbv = t.canonical_batch_value
        v3.write(f"**Canonical batch:** {cbv!r}" if cbv is not None else "**Canonical batch:** —")
        sav = t.scope_approved_value
        v4.write(f"**Scope-approved:** {sav!r}" if sav is not None else "**Scope-approved:** —")

        render_threshold_badges(t)

        st.write(t.description)
        if t.scientific_meaning:
            st.caption(t.scientific_meaning)

        meta1, meta2 = st.columns(2)
        with meta1:
            st.write(f"**Source file:** `{t.file}`")
            src_key = t.raw.get("source_config_key")
            if src_key:
                st.write(f"**Source config key:** `{src_key}`")
            if t.allowed_range:
                st.write(f"**Allowed range:** {t.allowed_range}")
            if t.allowed_values:
                st.write(f"**Allowed values:** {t.allowed_values}")
        with meta2:
            st.write(f"**GUI editable (G6):** {t.gui_editable}")
            st.write(f"**Scope locked:** {t.locked_by_scope}")
            st.write(f"**Requires approval:** {t.requires_approval}")

        if t.invalidates:
            st.write("**Invalidates:** " + ", ".join(f"`{x}`" for x in t.invalidates))
        else:
            st.write("**Invalidates:** *(none)*")

        if t.regenerate_after_change:
            st.write(
                "**Regenerate after change:** "
                + ", ".join(f"`{x}`" for x in t.regenerate_after_change)
            )
        if t.affects:
            st.caption("Affects: " + ", ".join(t.affects))

        if g6_is_enabled() and t.gui_editable and not t.locked_by_scope:
            if t.allowed_values and t.key != "default_participant":
                options = list(t.allowed_values)
                new_value = st.selectbox(
                    "New value",
                    options=options,
                    index=options.index(t.value) if t.value in options else 0,
                    key=f"edit_{t.key}",
                )
            elif t.key == "default_participant" and snapshot.participants:
                new_value = st.selectbox(
                    "New value",
                    options=snapshot.participants,
                    index=(
                        snapshot.participants.index(str(t.value))
                        if str(t.value) in snapshot.participants
                        else 0
                    ),
                    key=f"edit_{t.key}",
                )
            elif t.allowed_range:
                lo, hi = t.allowed_range
                new_value = st.number_input(
                    "New value",
                    value=float(t.value) if isinstance(t.value, (int, float)) else lo,
                    min_value=lo,
                    max_value=hi,
                    key=f"edit_{t.key}",
                )
                if isinstance(t.value, int) and not isinstance(t.value, bool):
                    new_value = int(new_value)
            else:
                new_value = st.text_input("New value", value=str(t.value), key=f"edit_{t.key}")

            reason = st.text_input("Change reason (required)", key=f"reason_{t.key}")
            approved = True
            if t.requires_approval:
                approved = st.checkbox(
                    "I approve changing this threshold (requires_approval)",
                    key=f"approve_{t.key}",
                )
            if st.button(f"Save `{t.key}`", key=f"save_{t.key}"):
                try:
                    live = load_analysis_config(project_root=REPO_ROOT)
                    updated, audit = live.apply_threshold_update(
                        t.key,
                        new_value,
                        reason=reason,
                        approved=approved,
                    )
                    cache_load_snapshot.clear()
                    st.success(
                        f"Updated `{updated.key}` → {updated.value!r}. "
                        f"Invalidates: {', '.join(updated.invalidates) or 'none'}"
                    )
                    st.caption(f"Audit: science_hash {audit['science_hash_before'][:12]}… → {audit['science_hash_after'][:12]}…")
                except ConfigValidationError as exc:
                    st.error(str(exc))

st.subheader("Coverage summary")
for layer, meta in snapshot.registry_coverage.items():
    st.write(f"- **{layer}:** {meta['label']}")

if not g6_is_enabled():
    st.info("Enable **G6 guarded execution** in the sidebar to edit thresholds.")
