#!/usr/bin/env python3
"""Generate the 4 final poster-ready JcvPCA figures (A-D) + combined panel.

Descriptive within-participant analysis; participants are never pooled.
All plotted values are read/derived from validated CSVs in the Layer3 outputs.
"""
from __future__ import annotations

import os
import sys
import tempfile
import argparse

os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="mplconfig_"))

import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

try:
    from adjustText import adjust_text  # noqa: F401
    HAS_ADJUST = True
except Exception:
    HAS_ADJUST = False

try:
    import seaborn  # noqa: F401
    HAS_SNS = True
except Exception:
    HAS_SNS = False

# --------------------------------------------------------------------------- #
# Paths (loaded from config/paths.yaml; override via configure_poster_paths)
# --------------------------------------------------------------------------- #
_SCRIPT_ROOT = Path(__file__).resolve().parents[1]
_SRC = _SCRIPT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from project_paths import load_project_paths  # noqa: E402

PROJECT_ROOT = _SCRIPT_ROOT
OUT_DIR = PROJECT_ROOT / "outputs" / "poster_final_figures"
CANONICAL_BATCH_DIR = (
    PROJECT_ROOT / "Layer3_JcvPCA" / "outputs" / "gaga_batch_jcvpca_20260626_193319"
)
SEARCH_DIRS: list[Path] = []


def _default_search_dirs(
    *,
    project_root: Path,
    evidence_dir: Path,
    batch_dir: Path,
    out_dir: Path,
    layer3_outputs_root: Path,
) -> list[Path]:
    return [
        evidence_dir,
        batch_dir,
        layer3_outputs_root,
        out_dir.parent,
        project_root,
    ]


def configure_poster_paths(
    *,
    config_path: Path | None = None,
    batch_dir: Path | None = None,
    out_dir: Path | None = None,
    evidence_dir: Path | None = None,
) -> None:
    """Resolve poster input/output paths from config with optional CLI overrides."""
    global PROJECT_ROOT, OUT_DIR, CANONICAL_BATCH_DIR, SEARCH_DIRS

    paths = load_project_paths(config_path=config_path)
    PROJECT_ROOT = paths.project_root

    resolved_batch = (batch_dir or paths.layer3_canonical_batch).resolve()
    resolved_evidence = (evidence_dir or paths.poster_evidence_package).resolve()
    resolved_out = (out_dir or paths.poster_final_figures).resolve()
    layer3_outputs = paths.get("layer3.outputs_root").resolve()

    missing: list[str] = []
    if not resolved_evidence.is_dir():
        missing.append(f"poster evidence package ({resolved_evidence})")
    if not resolved_batch.is_dir():
        missing.append(f"canonical Layer 3 batch ({resolved_batch})")
    if missing:
        raise FileNotFoundError(
            "Required poster input path(s) missing:\n  - "
            + "\n  - ".join(missing)
            + f"\nConfig: {paths.config_path}"
        )

    CANONICAL_BATCH_DIR = resolved_batch
    OUT_DIR = resolved_out
    SEARCH_DIRS = _default_search_dirs(
        project_root=PROJECT_ROOT,
        evidence_dir=resolved_evidence,
        batch_dir=resolved_batch,
        out_dir=resolved_out,
        layer3_outputs_root=layer3_outputs,
    )


def parse_poster_path_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate poster-ready JcvPCA figures from validated CSV inputs.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config/paths.yaml (default: auto-detect project root).",
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=None,
        help="Override Layer 3 batch directory (default: layer3.canonical_batch).",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="Override poster evidence package (default: layer3.poster_evidence_package).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Override poster figure output directory (default: poster.final_figures).",
    )
    return parser.parse_args(argv)


configure_poster_paths()

PARTICIPANTS = ["671", "252"]
FIG_A_PARTICIPANTS = ["671"]  # Figure A standalone: flagship participant only
COMPARISONS = ["T1_vs_T2", "T1_vs_T3"]
MAIN_BLOCK = "P3_P4_P5"
MAIN_FOCUS = "all"

# --------------------------------------------------------------------------- #
# Color & typography discipline
# --------------------------------------------------------------------------- #
# Anatomical family -> warm (upper limb / shoulder), cool (lower limb / pelvis),
# neutral (trunk / head / neck).
FAMILY_COLORS = {
    "distal_upper_limb": "#B2182B",     # deep red  (warm)
    "proximal_upper_limb": "#E0602F",   # orange    (warm)
    "shoulder_chain": "#F2A65A",        # amber     (warm)
    "lower_limb": "#2166AC",            # deep blue (cool)
    "pelvis_root": "#5AA0CF",           # light blue(cool)
    "trunk_neck_head": "#8C8C8C",       # gray      (neutral)
}
FAMILY_GROUP = {
    "distal_upper_limb": "Upper limb / shoulder",
    "proximal_upper_limb": "Upper limb / shoulder",
    "shoulder_chain": "Upper limb / shoulder",
    "lower_limb": "Lower limb / pelvis",
    "pelvis_root": "Lower limb / pelvis",
    "trunk_neck_head": "Trunk / head / neck",
}
FAMILY_LABEL = {
    "distal_upper_limb": "Distal upper limb",
    "proximal_upper_limb": "Proximal upper limb",
    "shoulder_chain": "Shoulder chain",
    "lower_limb": "Lower limb",
    "pelvis_root": "Pelvis root",
    "trunk_neck_head": "Trunk / neck / head",
}

# Participant color families (distinct from the family palette).
PARTICIPANT_COLORS = {"671": "#5E3C99", "252": "#1B9E77"}
PARTICIPANT_LIGHT = {"671": "#B6A4D6", "252": "#9FD9C3"}

# Direction-vs-magnitude category palette (Figure D2).
CATEGORY_ORDER = [
    "stable_magnitude_stable_direction",
    "low_magnitude_stable_direction",
    "stable_magnitude_direction_sensitive",
    "unstable_both",
]
CATEGORY_COLORS = {
    "stable_magnitude_stable_direction": "#1A9850",   # robust (green)
    "low_magnitude_stable_direction": "#91BFDB",      # low-magnitude (blue)
    "stable_magnitude_direction_sensitive": "#FDAE61",  # caution (orange)
    "unstable_both": "#D73027",                       # least robust (red)
}
CATEGORY_LABEL = {
    "stable_magnitude_stable_direction": "Stable magnitude + stable direction",
    "low_magnitude_stable_direction": "Low magnitude, stable direction",
    "stable_magnitude_direction_sensitive": "Stable magnitude, direction-sensitive",
    "unstable_both": "Unstable in both",
}

NOTE_TEXT = "Descriptive within-participant analysis; participants not pooled."

FS = {  # font sizes (poster 90x180 cm: tick >= 8, titles 14-16, axis 10-12, note 8-9)
    "fig_title": 16,
    "fig_subtitle": 11,
    "panel_title": 13,
    "axis": 11,
    "tick": 9.5,
    "annot": 8.5,
    "note": 8.5,
    "legend": 9,
}


def set_style() -> str:
    """Apply a clean scientific rcParams; return the resolved font family."""
    available = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
    for cand in ("Arial", "Helvetica", "DejaVu Sans"):
        if cand in available:
            font = cand
            break
    else:
        font = "sans-serif"
    plt.rcParams.update({
        "font.family": font,
        "font.size": FS["tick"],
        "axes.titlesize": FS["panel_title"],
        "axes.labelsize": FS["axis"],
        "xtick.labelsize": FS["tick"],
        "ytick.labelsize": FS["tick"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.9,
        "axes.edgecolor": "#444444",
        "axes.labelcolor": "#1a1a1a",
        "text.color": "#1a1a1a",
        "xtick.color": "#444444",
        "ytick.color": "#444444",
        "xtick.major.width": 0.9,
        "ytick.major.width": 0.9,
        "axes.grid": False,
        "figure.dpi": 120,
        "savefig.dpi": 600,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    })
    return font


def wrap_link(link: str, width: int = 16) -> str:
    """Make link ids readable: A_to_B -> 'A -> B' and wrap if long."""
    pretty = link.replace("_to_", " -> ")
    return "\n".join(textwrap.wrap(pretty, width=width)) or pretty


# --------------------------------------------------------------------------- #
# CSV resolver / loader
# --------------------------------------------------------------------------- #
class DataError(Exception):
    pass


def find_csv(name: str) -> Path:
    for d in SEARCH_DIRS:
        p = d / name
        if p.exists():
            return p
    raise DataError(f"Required CSV not found in any search dir: {name}")


def load_csv(name: str) -> pd.DataFrame:
    df = pd.read_csv(find_csv(name))
    df.columns = [c.strip() for c in df.columns]
    if "participant_id" in df.columns:
        df["participant_id"] = df["participant_id"].astype(str)
    return df


# --------------------------------------------------------------------------- #
# Validation harness
# --------------------------------------------------------------------------- #
class Validator:
    def __init__(self) -> None:
        self.files: list[tuple[str, str]] = []          # (name, resolved path)
        self.column_checks: list[tuple[str, list[str], list[str]]] = []
        self.value_checks: list[dict] = []
        self.sanity_checks: list[dict] = []             # boolean structural checks
        self.row_counts: list[tuple[str, int]] = []
        self.notes: list[str] = []                      # informational, non-blocking
        self.errors: list[str] = []

    def register_file(self, name: str) -> None:
        try:
            self.files.append((name, str(find_csv(name).relative_to(PROJECT_ROOT))))
        except DataError as exc:
            self.errors.append(str(exc))

    def check_columns(self, label: str, df: pd.DataFrame, required: list[str]) -> None:
        missing = [c for c in required if c not in df.columns]
        self.column_checks.append((label, required, missing))
        if missing:
            self.errors.append(f"{label}: missing columns {missing}")

    def check_value(self, fig: str, key: str, expected: float, actual: float,
                    tol: float) -> None:
        ok = (actual is not None) and (abs(float(actual) - float(expected)) <= tol)
        self.value_checks.append({
            "figure": fig, "item": key, "expected": expected,
            "actual": (None if actual is None else round(float(actual), 4)),
            "tol": tol, "match": ok,
        })

    def check_sanity(self, fig: str, key: str, passed: bool, detail: str = "",
                     fatal: bool = False) -> None:
        self.sanity_checks.append({"figure": fig, "item": key,
                                   "pass": bool(passed), "detail": detail})
        if not passed and fatal:
            self.errors.append(f"{fig} {key}: {detail}")

    def record_rows(self, label: str, n: int) -> None:
        self.row_counts.append((label, int(n)))

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    @property
    def status(self) -> str:
        if self.errors:
            return "FAIL"
        bad = any(not v["match"] for v in self.value_checks) or \
            any(not s["pass"] for s in self.sanity_checks)
        return "WARNING" if bad else "PASS"

    def write_report(self, path: Path) -> None:
        lines = ["# Poster Final Figures - Data Validation Report", ""]
        lines.append(f"**Final status: {self.status}**")
        lines.append("")
        lines.append("Descriptive within-participant analysis; participants not pooled.")
        lines.append("")
        lines.append("## Files used")
        lines.append("")
        for name, rel in self.files:
            lines.append(f"- `{name}` -> `{rel}`")
        lines.append("")
        lines.append("## Column checks")
        lines.append("")
        lines.append("| Table | Required columns | Missing |")
        lines.append("| --- | --- | --- |")
        for label, req, missing in self.column_checks:
            miss = "none" if not missing else ", ".join(missing)
            lines.append(f"| {label} | {len(req)} checked | {miss} |")
        lines.append("")
        if self.row_counts:
            lines.append("## Row counts after filtering")
            lines.append("")
            lines.append("| Subset | Rows |")
            lines.append("| --- | --- |")
            for label, n in self.row_counts:
                lines.append(f"| {label} | {n} |")
            lines.append("")
        if self.sanity_checks:
            lines.append("## Structural / sanity checks")
            lines.append("")
            lines.append("| Figure | Check | Pass | Detail |")
            lines.append("| --- | --- | --- | --- |")
            for s in self.sanity_checks:
                lines.append(f"| {s['figure']} | {s['item']} | "
                             f"{'YES' if s['pass'] else 'NO'} | {s['detail']} |")
            lines.append("")
        lines.append("## Expected-vs-actual value checks")
        lines.append("")
        lines.append("| Figure | Item | Expected | Actual | Tol | Match |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for v in self.value_checks:
            lines.append(
                f"| {v['figure']} | {v['item']} | {v['expected']} | "
                f"{v['actual']} | {v['tol']} | {'YES' if v['match'] else 'NO'} |"
            )
        lines.append("")
        n_ok = sum(v["match"] for v in self.value_checks)
        lines.append(f"Value checks matched: {n_ok}/{len(self.value_checks)}")
        lines.append("")
        if self.errors:
            lines.append("## Errors / deviations")
            lines.append("")
            for e in self.errors:
                lines.append(f"- {e}")
            lines.append("")
        deviations = [v for v in self.value_checks if not v["match"]]
        if deviations:
            lines.append("## Value deviations")
            lines.append("")
            for v in deviations:
                lines.append(
                    f"- {v['figure']} {v['item']}: expected {v['expected']}, "
                    f"got {v['actual']} (tol {v['tol']})"
                )
            lines.append("")
        if self.notes:
            lines.append("## Notes (informational)")
            lines.append("")
            for n in self.notes:
                lines.append(f"- {n}")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Data preparation (one builder per figure)
# --------------------------------------------------------------------------- #
FIG_A_TOP_N = 8  # links per panel (readable on a large poster panel)


def prepare_figure_a(v: Validator) -> pd.DataFrame:
    """Figure A: longitudinal link-level shift relative to natural variability.

    Source: longitudinal_delta_nv_ratio_by_link.csv (Model 1). For each
    participant x comparison, keep the top-N links by abs_longitudinal_delta;
    bar length = abs_longitudinal_delta, colour = delta_to_NV_T1_ratio,
    flag links outside the T1 natural-variability reference.
    """
    name = "longitudinal_delta_nv_ratio_by_link.csv"
    v.register_file(name)
    df = load_csv(name)
    req = ["participant_id", "block_label", "comparison_label", "link_id",
           "anatomical_family", "longitudinal_delta", "abs_longitudinal_delta",
           "NV_T1_abs_delta", "delta_to_NV_T1_ratio", "outside_T1_NV_reference",
           "rank_by_abs_longitudinal_delta"]
    v.check_columns("Figure A", df, req)

    sub = df[(df.block_label == MAIN_BLOCK)
             & (df.comparison_label.isin(COMPARISONS))
             & (df.participant_id.isin(PARTICIPANTS))].copy()
    for c in ["longitudinal_delta", "abs_longitudinal_delta", "NV_T1_abs_delta",
              "delta_to_NV_T1_ratio", "rank_by_abs_longitudinal_delta"]:
        sub[c] = pd.to_numeric(sub[c], errors="coerce")
    sub["outside_T1_NV_reference"] = (
        sub["outside_T1_NV_reference"].astype(str).str.strip().str.lower()
        .isin(["true", "1", "yes"]))

    # Top-N links per participant x comparison by abs longitudinal delta.
    top = (sub.sort_values("rank_by_abs_longitudinal_delta")
           .groupby(["participant_id", "comparison_label"], group_keys=False)
           .head(FIG_A_TOP_N))
    keep = ["participant_id", "comparison_label", "block_label", "link_id",
            "anatomical_family", "longitudinal_delta", "abs_longitudinal_delta",
            "NV_T1_abs_delta", "delta_to_NV_T1_ratio", "outside_T1_NV_reference",
            "rank_by_abs_longitudinal_delta"]
    out = (top[keep].sort_values(
        ["participant_id", "comparison_label", "rank_by_abs_longitudinal_delta"])
        .reset_index(drop=True))
    out = out[out.participant_id.astype(str).isin(FIG_A_PARTICIPANTS)].reset_index(drop=True)

    for pid in FIG_A_PARTICIPANTS:
        for comp in COMPARISONS:
            n = len(out[(out.participant_id == pid) & (out.comparison_label == comp)])
            v.record_rows(f"A {pid} {comp} (top links shown)", n)

    # --- Structural / sanity checks --------------------------------------- #
    nv_min = float(sub["NV_T1_abs_delta"].min())
    v.check_sanity("A", "NV_T1_abs_delta denominator > 0", nv_min > 0,
                   f"min NV_T1_abs_delta = {nv_min:.5f}", fatal=True)

    # delta_to_NV_T1_ratio should equal abs_delta / NV (where NV>0).
    ok_ratio = sub[sub.NV_T1_abs_delta > 0].copy()
    recomputed = ok_ratio["abs_longitudinal_delta"] / ok_ratio["NV_T1_abs_delta"]
    max_dev = float((recomputed - ok_ratio["delta_to_NV_T1_ratio"]).abs().max())
    v.check_sanity("A", "delta_to_NV_T1_ratio = abs_delta / NV", max_dev <= 1e-2,
                   f"max |recomputed - stored| = {max_dev:.4f}")

    # outside_T1_NV_reference should agree with ratio > 1.
    mismatch = int((sub["outside_T1_NV_reference"]
                    != (sub["delta_to_NV_T1_ratio"] > 1.0)).sum())
    v.check_sanity("A", "outside-NV flag agrees with ratio>1", mismatch == 0,
                   f"{mismatch} rows disagree")

    # Report extreme ratios alongside their (tiny) NV denominators.
    extreme = out[out.delta_to_NV_T1_ratio >= 8.0]
    for _, r in extreme.iterrows():
        v.note(f"A {r.participant_id} {r.comparison_label} {r.link_id}: "
               f"ratio {r.delta_to_NV_T1_ratio:.1f}x driven by small "
               f"NV_T1_abs_delta = {r.NV_T1_abs_delta:.5f} "
               f"(abs_delta = {r.abs_longitudinal_delta:.5f})")

    # --- Anchor value checks (from graph_enhancment_plan.md) --------------- #
    def g(pid, comp, link, col):
        r = out[(out.participant_id == pid) & (out.comparison_label == comp)
                & (out.link_id == link)]
        return None if r.empty else float(r.iloc[0][col])

    expect = [  # (pid, comp, link, abs_delta, delta_to_NV_T1_ratio)
        ("671", "T1_vs_T2", "RFArm_to_RHand", 0.0390, 3.6190),
        ("671", "T1_vs_T2", "RUArm_to_RFArm", 0.0232, 8.7172),
        ("671", "T1_vs_T2", "LThigh_to_LShin", 0.0225, 1.9632),
        ("671", "T1_vs_T3", "RFArm_to_RHand", 0.0417, 3.8740),
        ("671", "T1_vs_T3", "LThigh_to_LShin", 0.0304, 2.6561),
    ]
    for pid, comp, link, ad, ratio in expect:
        v.check_value("A", f"{pid} {comp} {link} abs_delta", ad,
                      g(pid, comp, link, "abs_longitudinal_delta"), 1e-3)
        v.check_value("A", f"{pid} {comp} {link} delta/NV", ratio,
                      g(pid, comp, link, "delta_to_NV_T1_ratio"), 1e-2)
    return out


FIG_B_COMP = "T1_vs_T2"  # primary longitudinal comparison for Figure B


def prepare_figure_b(v: Validator) -> tuple[pd.DataFrame, dict]:
    """Figure B: functional (p50) vs null-space (after p50) family contribution.

    Source: body_region_anatomical_family_summary.csv (Model 3). Per participant,
    grouped bars of relative_family_share by anatomical_family for the functional
    subspace (functional_p50) vs the complementary null-space (null_space_after_p50).
    PC-count annotations come from nullspace_top7_links_all_contexts.csv.
    """
    name = "body_region_anatomical_family_summary.csv"
    v.register_file(name)
    df = load_csv(name)
    req = ["participant_id", "block_label", "comparison_label", "focus_mode",
           "anatomical_family", "relative_family_share", "n_links_in_family",
           "family_rank", "top_link_in_family", "appears_in_p50", "appears_in_p60"]
    v.check_columns("Figure B", df, req)

    focuses = ["functional_p50", "null_space_after_p50"]
    sub = df[(df.block_label == MAIN_BLOCK)
             & (df.comparison_label == FIG_B_COMP)
             & (df.focus_mode.isin(focuses))
             & (df.participant_id.isin(PARTICIPANTS))].copy()
    sub["relative_family_share"] = pd.to_numeric(sub["relative_family_share"],
                                                 errors="coerce")
    keep = ["participant_id", "comparison_label", "focus_mode", "anatomical_family",
            "relative_family_share", "n_links_in_family", "family_rank",
            "top_link_in_family", "appears_in_p50", "appears_in_p60"]
    out = sub[keep].sort_values(
        ["participant_id", "focus_mode", "family_rank"]).reset_index(drop=True)

    for pid in PARTICIPANTS:
        v.record_rows(f"B {pid} families x subspaces",
                      len(out[out.participant_id == pid]))

    # --- Sanity: family shares sum to ~1 within participant x focus_mode ---- #
    for pid in PARTICIPANTS:
        for fm in focuses:
            s = float(out[(out.participant_id == pid)
                          & (out.focus_mode == fm)]["relative_family_share"].sum())
            v.check_sanity("B", f"{pid} {fm} family shares sum to 1",
                           abs(s - 1.0) <= 1e-2, f"sum = {s:.4f}")

    # --- PC counts (functional vs null-space) from the link-level table ----- #
    pc_counts: dict = {}
    cname = "nullspace_top7_links_all_contexts.csv"
    v.register_file(cname)
    try:
        cm = load_csv(cname)
        v.check_columns("Figure B (PC counts)", cm,
                        ["participant_id", "block_label", "comparison_label",
                         "functional_pc_count", "nullspace_pc_count"])
        cmf = cm[(cm.block_label == MAIN_BLOCK)
                 & (cm.comparison_label == FIG_B_COMP)]
        for pid in PARTICIPANTS:
            r = cmf[cmf.participant_id == pid]
            if not r.empty:
                fpc = int(float(r.iloc[0]["functional_pc_count"]))
                npc = int(float(r.iloc[0]["nullspace_pc_count"]))
                pc_counts[pid] = {"functional": fpc, "nullspace": npc,
                                  "m": fpc + npc}
    except DataError:
        v.note("B: PC-count source unavailable; PC annotations omitted.")

    v.check_value("B", "671 functional PCs", 3, pc_counts.get("671", {}).get("functional"), 0.5)
    v.check_value("B", "671 null-space PCs", 6, pc_counts.get("671", {}).get("nullspace"), 0.5)
    v.check_value("B", "252 functional PCs", 4, pc_counts.get("252", {}).get("functional"), 0.5)
    v.check_value("B", "252 null-space PCs", 6, pc_counts.get("252", {}).get("nullspace"), 0.5)

    # --- Anchor family-share values (verified against the table) ------------ #
    def g(pid, fm, fam):
        r = out[(out.participant_id == pid) & (out.focus_mode == fm)
                & (out.anatomical_family == fam)]
        return None if r.empty else float(r.iloc[0]["relative_family_share"])

    expect = [  # (pid, focus_mode, family, relative_family_share)
        ("671", "functional_p50", "distal_upper_limb", 0.3545),
        ("671", "functional_p50", "shoulder_chain", 0.2633),
        ("671", "null_space_after_p50", "lower_limb", 0.3440),
        ("252", "functional_p50", "proximal_upper_limb", 0.3107),
        ("252", "functional_p50", "shoulder_chain", 0.2781),
        ("252", "null_space_after_p50", "shoulder_chain", 0.2953),
    ]
    for pid, fm, fam, share in expect:
        v.check_value("B", f"{pid} {fm} {fam} share", share, g(pid, fm, fam), 1e-3)
    return out, pc_counts


def prepare_figure_c(v: Validator) -> pd.DataFrame:
    name = "natural_variability_scalar_poster_table.csv"
    v.register_file(name)
    df = load_csv(name)
    req = ["participant_id", "block_label", "timepoint", "focus_mode",
           "mean_abs_delta", "top3_abs_delta_share", "gini",
           "links_needed_for_80_percent_abs_delta"]
    v.check_columns("Figure C", df, req)
    sub = df[(df.block_label == MAIN_BLOCK) & (df.focus_mode == MAIN_FOCUS)
             & (df.participant_id.isin(PARTICIPANTS))].copy()

    # concentration_label from the concentration metrics table.
    cname = "concentration_metrics_all_analyses.csv"
    v.register_file(cname)
    cm = load_csv(cname)
    v.check_columns("Figure C (concentration)", cm,
                    ["participant_id", "block_label", "focus_mode",
                     "analysis_type", "timepoint_if_repetition", "concentration_label"])
    cm = cm[(cm.block_label == MAIN_BLOCK) & (cm.focus_mode == MAIN_FOCUS)
            & (cm.analysis_type == "repetition_variability")].copy()
    label_map = {(str(r.participant_id), str(r.timepoint_if_repetition)): r.concentration_label
                 for _, r in cm.iterrows()}
    sub["concentration_label"] = [label_map.get((p, t)) for p, t in
                                  zip(sub.participant_id, sub.timepoint)]

    out = sub.rename(columns={"top3_abs_delta_share": "top3_share",
                              "links_needed_for_80_percent_abs_delta": "links_needed_for_80_percent"})
    keep = ["participant_id", "timepoint", "mean_abs_delta", "gini", "top3_share",
            "links_needed_for_80_percent", "concentration_label"]
    out = out[keep].sort_values(["participant_id", "timepoint"]).reset_index(drop=True)

    def g(pid, tp, col):
        r = out[(out.participant_id == pid) & (out.timepoint == tp)]
        return None if r.empty else float(r.iloc[0][col])

    expect = [
        ("671", "T1", 0.0125, 0.5956, 0.5366), ("671", "T2", 0.0156, 0.6114, 0.5634),
        ("671", "T3", 0.0110, 0.4701, 0.4592), ("252", "T1", 0.0140, 0.5832, 0.5867),
        ("252", "T2", 0.0072, 0.4348, 0.4646), ("252", "T3", 0.0090, 0.6184, 0.6244),
    ]
    for pid, tp, mad, t3, gini in expect:
        v.check_value("C", f"{pid} {tp} mean_abs_delta", mad, g(pid, tp, "mean_abs_delta"), 1e-3)
        v.check_value("C", f"{pid} {tp} top3_share", t3, g(pid, tp, "top3_share"), 1e-3)
        v.check_value("C", f"{pid} {tp} gini", gini, g(pid, tp, "gini"), 1e-3)
    return out


def prepare_figure_d(v: Validator) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # D1: sign-agreement aggregates from directional robustness summaries (focus=all).
    summ_files = {
        "T1_vs_T2": "directional_robustness_t1_t2_summary.csv",
        "T1_vs_T3": "directional_robustness_t1_t3_summary.csv",
        "T2_vs_T3": "directional_robustness_t2_t3_summary.csv",
    }
    rows = []
    long_rows = []
    for comp, fname in summ_files.items():
        v.register_file(fname)
        df = load_csv(fname)
        v.check_columns(f"Figure D summary ({comp})", df,
                        ["participant_id", "block_label", "focus_mode",
                         "percent_sign_agreement_all_links"])
        f = df[df.focus_mode == MAIN_FOCUS].copy()
        p3 = f[f.block_label == MAIN_BLOCK]["percent_sign_agreement_all_links"]
        allb = f[f.block_label == "all_P1_P2_P3_P4_P5"]["percent_sign_agreement_all_links"]
        both = f[f.block_label.isin([MAIN_BLOCK, "all_P1_P2_P3_P4_P5"])]["percent_sign_agreement_all_links"]
        rows.append({
            "comparison": comp,
            "p3_mean_sign_agreement": round(float(p3.mean()), 4),
            "all_block_mean_sign_agreement": round(float(allb.mean()), 4),
            "overall_median_sign_agreement": round(float(both.median()), 4),
        })
        f2 = f.copy()
        f2["comparison"] = comp
        long_rows.append(f2)
    d1 = pd.DataFrame(rows)
    d1_long = pd.concat(long_rows, ignore_index=True)[
        ["comparison", "participant_id", "block_label", "focus_mode",
         "percent_sign_agreement_all_links", "percent_sign_agreement_top5_pooled_links",
         "spearman_rho_delta", "spearman_rho_abs_rank"]
    ]

    # Sanity: percent_sign_agreement must be on a 0-100 scale (not 0-1 fractions).
    pmax = float(pd.to_numeric(d1_long["percent_sign_agreement_all_links"],
                               errors="coerce").max())
    pmin = float(pd.to_numeric(d1_long["percent_sign_agreement_all_links"],
                               errors="coerce").min())
    v.check_sanity("D1", "percent_sign_agreement on 0-100 scale",
                   1.5 < pmax <= 100.0,
                   f"observed range [{pmin:.1f}, {pmax:.1f}]")
    v.record_rows("D1 sign-agreement rows (focus=all)", len(d1_long))

    exp_d1 = {
        "T1_vs_T2": (62.5, 59.4, 58.5), "T1_vs_T3": (53.1, 60.2, 43.2),
        "T2_vs_T3": (62.5, 65.8, 59.6),
    }
    for comp, (med, p3m, allm) in exp_d1.items():
        r = d1[d1.comparison == comp].iloc[0]
        v.check_value("D1", f"{comp} overall median", med, r.overall_median_sign_agreement, 0.2)
        v.check_value("D1", f"{comp} P3 mean", p3m, r.p3_mean_sign_agreement, 0.2)
        v.check_value("D1", f"{comp} all-block mean", allm, r.all_block_mean_sign_agreement, 0.2)

    # D2: direction-vs-magnitude categories (P3_P4_P5, focus=all, both participants).
    dname = "direction_vs_magnitude_integrated_report.csv"
    v.register_file(dname)
    dvm = load_csv(dname)
    v.check_columns("Figure D2", dvm,
                    ["participant_id", "block_label", "comparison_label",
                     "focus_mode", "interpretation_label"])
    dd = dvm[(dvm.block_label == MAIN_BLOCK) & (dvm.focus_mode == MAIN_FOCUS)
             & (dvm.comparison_label.isin(COMPARISONS))
             & (dvm.participant_id.isin(PARTICIPANTS))]
    d2 = (dd.groupby(["comparison_label", "interpretation_label"]).size()
          .rename("n_links").reset_index())
    # ensure all categories present
    full = []
    for comp in COMPARISONS:
        for cat in CATEGORY_ORDER:
            n = d2[(d2.comparison_label == comp) & (d2.interpretation_label == cat)]["n_links"]
            full.append({"comparison_label": comp, "interpretation_label": cat,
                         "n_links": int(n.iloc[0]) if len(n) else 0})
    d2 = pd.DataFrame(full)

    exp_d2 = {
        ("T1_vs_T2", "low_magnitude_stable_direction"): 9,
        ("T1_vs_T2", "stable_magnitude_direction_sensitive"): 11,
        ("T1_vs_T2", "stable_magnitude_stable_direction"): 5,
        ("T1_vs_T2", "unstable_both"): 5,
        ("T1_vs_T3", "low_magnitude_stable_direction"): 8,
        ("T1_vs_T3", "stable_magnitude_direction_sensitive"): 5,
        ("T1_vs_T3", "stable_magnitude_stable_direction"): 9,
        ("T1_vs_T3", "unstable_both"): 8,
    }
    for (comp, cat), n in exp_d2.items():
        got = d2[(d2.comparison_label == comp) & (d2.interpretation_label == cat)]["n_links"]
        v.check_value("D2", f"{comp} {cat}", n, float(got.iloc[0]) if len(got) else None, 0.5)
    return d1, d1_long, d2


# --------------------------------------------------------------------------- #
# Figure helpers
# --------------------------------------------------------------------------- #
def _family_legend_handles() -> list[Patch]:
    seen, handles = set(), []
    for fam, col in FAMILY_COLORS.items():
        handles.append(Patch(facecolor=col, edgecolor="none", label=FAMILY_LABEL[fam]))
        seen.add(fam)
    return handles


def _panel_title(ax, text, color="#1a1a1a"):
    ax.set_title(text, fontsize=FS["panel_title"], fontweight="bold",
                 color=color, pad=6, loc="left")


# --------------------------------------------------------------------------- #
# Figure A - longitudinal link-level signed Delta (2x2)
# --------------------------------------------------------------------------- #
NV_CMAP = plt.cm.YlOrRd          # sequential: higher delta/NV -> warmer
NV_VMIN, NV_VMAX = 0.0, 4.0      # colour clipped at 4x; >=1 means outside NV
NV_NORM = matplotlib.colors.Normalize(vmin=NV_VMIN, vmax=NV_VMAX)


def draw_figure_a(fig, df: pd.DataFrame) -> None:
    fig.suptitle(
        "Longitudinal link-level shift relative to repetition-to-repetition "
        "variability (NV = T1_R1 vs T1_R2)",
        fontsize=FS["fig_title"] + 1, fontweight="bold",
        x=0.015, ha="left", y=0.995,
    )

    pids = [p for p in FIG_A_PARTICIPANTS
            if p in df.participant_id.astype(str).unique()]
    axes = fig.subplots(1, len(COMPARISONS))
    fig.subplots_adjust(left=0.13, right=0.88, top=0.92, bottom=0.26,
                        wspace=0.42)

    for pid in pids:
        pmax = float(df[df.participant_id.astype(str) == pid]["abs_longitudinal_delta"].max())
        for j, comp in enumerate(COMPARISONS):
            ax = axes[j]
            d = (df[(df.participant_id.astype(str) == pid) & (df.comparison_label == comp)]
                 .sort_values("abs_longitudinal_delta", ascending=False)
                 .reset_index(drop=True))
            y = np.arange(len(d))

            for yi, (_, row) in zip(y, d.iterrows()):
                absd = float(row["abs_longitudinal_delta"])
                ratio = float(row["delta_to_NV_T1_ratio"])
                outside = bool(row["outside_T1_NV_reference"])
                mcol = NV_CMAP(NV_NORM(min(ratio, NV_VMAX)))
                ax.hlines(yi, 0, absd, color="#cfcfcf", linewidth=1.6, zorder=2)
                ax.scatter(absd, yi, s=120, color=mcol, zorder=4,
                           edgecolor=("#222222" if outside else "#9a9a9a"),
                           linewidth=(1.9 if outside else 0.9))
                sign = "+" if row["longitudinal_delta"] >= 0 else "\u2212"
                ax.text(-pmax * 0.045, yi, sign, va="center", ha="center",
                        fontsize=FS["annot"], color="#9a9a9a", zorder=5)
                nv = float(row["NV_T1_abs_delta"])
                txt = f"{ratio:.1f}x  (NV {nv:.3f})"
                ax.text(absd + pmax * 0.06, yi, txt, va="center", ha="left",
                        fontsize=FS["annot"], zorder=5,
                        color=("#1a1a1a" if outside else "#888888"),
                        fontweight=("bold" if outside else "normal"))

            ax.axvline(0, color="#333333", linewidth=1.0, zorder=3)
            ax.set_ylim(-0.7, len(d) - 0.3)
            ax.invert_yaxis()
            ax.set_yticks(y)
            labels = ax.set_yticklabels([wrap_link(l) for l in d["link_id"]],
                                        fontsize=FS["tick"])
            for lab, fam in zip(labels, d["anatomical_family"]):
                lab.set_color(FAMILY_COLORS.get(fam, "#444444"))
            ax.set_xlim(-pmax * 0.10, pmax * 1.42)
            ax.tick_params(axis="y", length=0)
            ax.grid(axis="x", color="#ececec", linewidth=0.7, zorder=0)
            ax.set_axisbelow(True)
            ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.02f"))

            _panel_title(ax, f"Participant {pid}  -  {comp.replace('_vs_', ' vs ')}",
                         color=PARTICIPANT_COLORS[pid])

    fig.supxlabel("Absolute longitudinal JcvPCA link Delta",
                  fontsize=FS["axis"], y=0.19)

    sm = matplotlib.cm.ScalarMappable(norm=NV_NORM, cmap=NV_CMAP)
    cax = fig.add_axes([0.905, 0.30, 0.018, 0.52])
    cbar = fig.colorbar(sm, cax=cax, extend="max")
    cbar.set_label("Delta / T1 natural-variability ratio", fontsize=FS["axis"])
    cbar.ax.tick_params(labelsize=FS["tick"])
    cbar.ax.axhline(1.0, color="#222222", linewidth=1.4)
    cbar.ax.text(1.6, 1.0, "= NV", va="center", ha="left",
                 fontsize=FS["annot"], color="#222222",
                 transform=cbar.ax.get_yaxis_transform())

    # Legends: anatomical family (label colours) + NV marker meaning.
    fam_handles = _family_legend_handles()
    leg1 = fig.legend(handles=fam_handles, loc="lower left", ncol=3, frameon=False,
                      fontsize=FS["legend"], bbox_to_anchor=(0.015, 0.06),
                      handlelength=1.1, columnspacing=1.3,
                      title="Anatomical family (link-label colour)")
    leg1.get_title().set_fontsize(FS["annot"])
    leg1._legend_box.align = "left"
    marker_handles = [
        Line2D([0], [0], marker="o", linestyle="none", markersize=9,
               markerfacecolor="#fdae61", markeredgecolor="#222222",
               markeredgewidth=1.9, label="Outside T1 NV reference (ratio > 1)"),
        Line2D([0], [0], marker="o", linestyle="none", markersize=9,
               markerfacecolor="#ffe9b0", markeredgecolor="#9a9a9a",
               markeredgewidth=0.9, label="Within T1 NV reference (ratio <= 1)"),
        Line2D([0], [0], marker="$+$", linestyle="none", color="#9a9a9a",
               markersize=9, label="+/- = direction of signed Delta"),
    ]
    fig.legend(handles=marker_handles, loc="lower right", ncol=1, frameon=False,
               fontsize=FS["legend"], bbox_to_anchor=(0.88, 0.06))
    fig.text(0.5, 0.012,
             "NV is a descriptive T1-repetition reference, not an inferential "
             "significance threshold.   " + NOTE_TEXT,
             fontsize=FS["note"], color="#888888", ha="center")


# --------------------------------------------------------------------------- #
# Figure B - longitudinal Delta relative to T1 natural variability (2x2)
# --------------------------------------------------------------------------- #
FUNC_COLOR = "#3B6FB6"      # functional subspace (first ~50% variance)
NULL_COLOR = "#D98C2B"      # null-space after p50 (redundant / expressive)


def draw_figure_b(fig, df: pd.DataFrame, pc_counts: dict) -> None:
    fig.suptitle("B.  Functional vs null-space contribution by anatomical family",
                 fontsize=FS["fig_title"] + 1, fontweight="bold",
                 x=0.015, ha="left", y=0.995)
    fig.text(0.015, 0.945,
             "Relative family share of absolute link contribution within the "
             "variance-informed functional subspace (first ~50%) and the "
             f"complementary null-space (P3-P5, {FIG_B_COMP.replace('_vs_', ' vs ')}). "
             "Participants analysed separately.",
             fontsize=FS["fig_subtitle"], color="#555555", ha="left")

    axes = fig.subplots(1, 2)
    fig.subplots_adjust(left=0.20, right=0.97, top=0.86, bottom=0.16, wspace=0.55)
    xmax = float(df["relative_family_share"].max()) * 1.32

    for k, pid in enumerate(PARTICIPANTS):
        ax = axes[k]
        d = df[df.participant_id == pid]
        func = (d[d.focus_mode == "functional_p50"]
                .set_index("anatomical_family")["relative_family_share"])
        null = (d[d.focus_mode == "null_space_after_p50"]
                .set_index("anatomical_family")["relative_family_share"])
        fams = list(func.sort_values(ascending=False).index)
        y = np.arange(len(fams))
        h = 0.38
        for yi, fam in zip(y, fams):
            fv = float(func.get(fam, 0.0))
            nv = float(null.get(fam, 0.0))
            ax.barh(yi + h / 2 + 0.01, fv, height=h, color=FUNC_COLOR,
                    edgecolor="white", linewidth=0.7, zorder=3)
            ax.barh(yi - h / 2 - 0.01, nv, height=h, color=NULL_COLOR,
                    edgecolor="white", linewidth=0.7, zorder=3)
            ax.text(fv + xmax * 0.012, yi + h / 2 + 0.01, f"{fv*100:.0f}%",
                    va="center", ha="left", fontsize=FS["annot"], color="#1a1a1a")
            gains = nv > fv + 1e-9
            ax.text(nv + xmax * 0.012, yi - h / 2 - 0.01,
                    (f"{nv*100:.0f}%  \u25b2" if gains else f"{nv*100:.0f}%"),
                    va="center", ha="left", fontsize=FS["annot"],
                    color=("#9A5A00" if gains else "#1a1a1a"),
                    fontweight=("bold" if gains else "normal"))

        ax.set_yticks(y)
        labels = ax.set_yticklabels([FAMILY_LABEL.get(f, f) for f in fams],
                                    fontsize=FS["tick"])
        for lab, fam in zip(labels, fams):
            lab.set_color(FAMILY_COLORS.get(fam, "#444444"))
        ax.invert_yaxis()
        ax.set_xlim(0, xmax)
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", color="#ececec", linewidth=0.7, zorder=0)
        ax.set_axisbelow(True)
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))

        pc = pc_counts.get(pid)
        sub = (f"  (functional = {pc['functional']} PCs, null-space = "
               f"{pc['nullspace']} PCs; m = {pc['m']})" if pc else "")
        _panel_title(ax, f"Participant {pid}" + sub, color=PARTICIPANT_COLORS[pid])
        ax.set_xlabel("Relative family share of |link Delta|", fontsize=FS["axis"])

    handles = [
        Patch(facecolor=FUNC_COLOR, edgecolor="white",
              label="Functional subspace (first ~50% variance)"),
        Patch(facecolor=NULL_COLOR, edgecolor="white",
              label="Null-space after p50 (redundant / expressive)"),
        Line2D([0], [0], marker="^", linestyle="none", color="#9A5A00",
               markersize=9, label="Family gains share in null-space"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
               fontsize=FS["legend"], bbox_to_anchor=(0.5, -0.01),
               handlelength=1.2, columnspacing=1.6)
    fig.text(0.5, -0.045,
             "Null-space = redundant / expressive / coordination-related degrees "
             "of freedom, not unused movement; subspace membership is variance-informed.   "
             + NOTE_TEXT, fontsize=FS["note"], color="#888888", ha="center")


# --------------------------------------------------------------------------- #
# Figure C - natural variability is timepoint- and participant-dependent (1x2)
# --------------------------------------------------------------------------- #
def draw_figure_c(fig, df: pd.DataFrame) -> None:
    fig.suptitle("C.  Movement-organization metrics and natural-variability structure",
                 fontsize=FS["fig_title"], fontweight="bold", x=0.02, ha="left", y=0.99)
    fig.text(0.02, 0.925,
             "Within-timepoint repetition (R1-R2) variability and its concentration "
             "across links (P3-P5, all-PC)",
             fontsize=FS["fig_subtitle"], color="#555555", ha="left")

    axes = fig.subplots(1, 2)
    timepoints = ["T1", "T2", "T3"]
    x = np.arange(len(timepoints))

    # --- C1: grouped bars of mean_abs_delta ---
    ax1 = axes[0]
    width = 0.36
    peak = {"671": "T2", "252": "T1"}
    for k, pid in enumerate(PARTICIPANTS):
        d = df[df.participant_id == pid].set_index("timepoint").reindex(timepoints)
        vals = d["mean_abs_delta"].values
        bars = ax1.bar(x + (k - 0.5) * width, vals, width,
                       color=PARTICIPANT_COLORS[pid], edgecolor="white", linewidth=0.8,
                       label=f"Participant {pid}", zorder=3)
        for xi, (tp, val) in zip(x + (k - 0.5) * width, zip(timepoints, vals)):
            ax1.text(xi, val + 0.0004, f"{val:.4f}", ha="center", va="bottom",
                     fontsize=FS["annot"] - 0.5, color="#444444")
            if tp == peak[pid]:
                ax1.text(xi, val + 0.0019, "largest", ha="center", va="bottom",
                         fontsize=FS["annot"], color=PARTICIPANT_COLORS[pid],
                         fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(timepoints)
    ax1.set_xlabel("Timepoint", fontsize=FS["axis"])
    ax1.set_ylabel("Mean abs JcvPCA Delta (all-PC)", fontsize=FS["axis"])
    ax1.set_ylim(0, float(df["mean_abs_delta"].max()) * 1.42)
    ax1.grid(axis="y", color="#ededed", linewidth=0.7, zorder=0)
    ax1.set_axisbelow(True)
    ax1.legend(frameon=False, fontsize=FS["legend"], loc="upper right")
    _panel_title(ax1, "C1  Magnitude of repetition variability")

    # --- C2: top3_share (primary) + Gini (secondary) ---
    ax2 = axes[1]
    for pid in PARTICIPANTS:
        d = df[df.participant_id == pid].set_index("timepoint").reindex(timepoints)
        col = PARTICIPANT_COLORS[pid]
        ax2.plot(x, d["top3_share"].values, "-o", color=col, markersize=8,
                 linewidth=2.0, label=f"Participant {pid} - top-3 share", zorder=3)
        ax2.plot(x, d["gini"].values, "--D", color=col, markersize=6.5,
                 markerfacecolor="white", markeredgecolor=col, linewidth=1.3,
                 alpha=0.8, label=f"Participant {pid} - Gini", zorder=2)
        dy, va = (0.013, "bottom") if pid == "671" else (-0.013, "top")
        for xi, t3 in zip(x, d["top3_share"].values):
            ax2.text(xi, t3 + dy, f"{t3:.2f}", ha="center", va=va,
                     fontsize=FS["annot"] - 0.5, color=col)
    ax2.set_xticks(x)
    ax2.set_xticklabels(timepoints)
    ax2.set_xlabel("Timepoint", fontsize=FS["axis"])
    ax2.set_ylabel("Concentration across links", fontsize=FS["axis"])
    ax2.set_ylim(0.35, 0.72)
    ax2.grid(axis="y", color="#ededed", linewidth=0.7, zorder=0)
    ax2.set_axisbelow(True)
    ax2.legend(frameon=False, fontsize=FS["legend"] - 0.5, loc="lower left", ncol=1)
    _panel_title(ax2, "C2  Concentration: top-3 share (solid) / Gini (dashed)")

    fig.text(0.02, 0.02, "NV is link-structured; not a single universal scalar.   " + NOTE_TEXT,
             fontsize=FS["note"], color="#888888", ha="left")


# --------------------------------------------------------------------------- #
# Figure D - directional robustness check (D1 heatmap + D2 stacked bars)
# --------------------------------------------------------------------------- #
def draw_figure_d(fig, d1: pd.DataFrame, d2: pd.DataFrame) -> None:
    fig.suptitle("D.  Directional robustness and magnitude-direction separation",
                 fontsize=FS["fig_title"], fontweight="bold", x=0.02, ha="left", y=0.99)
    fig.text(0.02, 0.93,
             "Signed Delta direction varies across repetition pairings; magnitude / rank should be emphasized",
             fontsize=FS["fig_subtitle"], color="#555555", ha="left")

    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1.0], wspace=0.32,
                          left=0.10, right=0.97, top=0.84, bottom=0.16)

    # --- D1 heatmap ---
    axh = fig.add_subplot(gs[0, 0])
    comps = ["T1_vs_T2", "T1_vs_T3", "T2_vs_T3"]
    cols = ["p3_mean_sign_agreement", "all_block_mean_sign_agreement",
            "overall_median_sign_agreement"]
    col_labels = ["P3-P5\nmean", "All-block\nmean", "Overall\nmedian"]
    d1i = d1.set_index("comparison").reindex(comps)
    mat = d1i[cols].values.astype(float)
    im = axh.imshow(mat, cmap="YlGnBu", vmin=45, vmax=75, aspect="auto")
    axh.set_xticks(range(len(cols)))
    axh.set_xticklabels(col_labels, fontsize=FS["tick"])
    axh.set_yticks(range(len(comps)))
    axh.set_yticklabels([c.replace("_vs_", " vs ") for c in comps], fontsize=FS["tick"])
    axh.tick_params(length=0)
    for s in axh.spines.values():
        s.set_visible(False)
    for r in range(mat.shape[0]):
        for c in range(mat.shape[1]):
            val = mat[r, c]
            txtcol = "white" if val >= 67 else "#1a1a1a"
            axh.text(c, r, f"{val:.1f}%", ha="center", va="center",
                     fontsize=FS["annot"] + 1, color=txtcol, fontweight="bold")
    cbar = fig.colorbar(im, ax=axh, fraction=0.046, pad=0.04)
    cbar.set_label("Sign agreement with pooled comparison (%)", fontsize=FS["annot"])
    cbar.ax.tick_params(labelsize=FS["tick"] - 1)
    _panel_title(axh, "D1  Sign agreement (focus = all-PC)")

    # --- D2 stacked bars ---
    axb = fig.add_subplot(gs[0, 1])
    comps2 = ["T1_vs_T2", "T1_vs_T3"]
    y = np.arange(len(comps2))
    left = np.zeros(len(comps2))
    for cat in CATEGORY_ORDER:
        widths = [int(d2[(d2.comparison_label == c) & (d2.interpretation_label == cat)]["n_links"].iloc[0])
                  for c in comps2]
        axb.barh(y, widths, left=left, color=CATEGORY_COLORS[cat],
                 edgecolor="white", linewidth=0.8, label=CATEGORY_LABEL[cat], zorder=3)
        for yi, w, l in zip(y, widths, left):
            if w > 0:
                axb.text(l + w / 2, yi, str(w), ha="center", va="center",
                         fontsize=FS["annot"], color="white", fontweight="bold")
        left += np.array(widths)
    axb.set_yticks(y)
    axb.set_yticklabels([c.replace("_vs_", " vs ") for c in comps2], fontsize=FS["tick"])
    axb.invert_yaxis()  # T1 vs T2 on top, matching D1 reading order
    axb.set_xlabel("Number of links", fontsize=FS["axis"])
    axb.tick_params(axis="y", length=0)
    axb.set_xlim(0, left.max() * 1.02)
    axb.grid(axis="x", color="#ededed", linewidth=0.7, zorder=0)
    axb.set_axisbelow(True)
    _panel_title(axb, "D2  Direction vs magnitude (P3-P5, all-PC)")
    axb.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2,
               frameon=False, fontsize=FS["legend"] - 0.5, handlelength=1.1,
               columnspacing=1.2)

    fig.text(0.02, 0.02,
             "Pooled R1+R2 summaries describe aggregates; signed link direction is repetition-pairing sensitive.   "
             + NOTE_TEXT, fontsize=FS["note"], color="#888888", ha="left")


# --------------------------------------------------------------------------- #
# Export helpers
# --------------------------------------------------------------------------- #
def save_all(fig, stem: str) -> list[str]:
    paths = []
    for ext in ("png", "pdf", "svg"):
        p = OUT_DIR / f"{stem}.{ext}"
        fig.savefig(p, dpi=600 if ext == "png" else None)
        paths.append(str(p.relative_to(PROJECT_ROOT)))
    return paths


def export_standalone(draw_fn, stem: str, figsize, *args) -> list[str]:
    fig = plt.figure(figsize=figsize)
    draw_fn(fig, *args)
    paths = save_all(fig, stem)
    plt.close(fig)
    return paths


# Portrait combined-overview layout (poster is 90 x 180 cm, ratio 1:2).
COMBINED_W = 20.0
COMBINED_H = 40.0                       # 1:2 portrait
COMBINED_ROW_RATIOS = [1.30, 0.92, 0.86, 0.92]   # A largest, then B, C, D
MIN_PANEL_HEIGHT_IN = 7.0               # readability floor for a stacked panel


def combined_readability(out_dir: Path) -> tuple[bool, list[str]]:
    """Decide whether a portrait combined overview stays readable, and report."""
    usable_h = COMBINED_H * (0.985 - 0.012)   # top - bottom margins
    total = sum(COMBINED_ROW_RATIOS)
    names = ["A", "B", "C", "D"]
    heights = [usable_h * r / total for r in COMBINED_ROW_RATIOS]
    ok = min(heights) >= MIN_PANEL_HEIGHT_IN
    lines = ["# Combined Poster Panel - Readability Check", ""]
    lines.append(f"Poster target: 90 x 180 cm (portrait, ratio 1:2). "
                 f"Combined canvas: {COMBINED_W:.0f} x {COMBINED_H:.0f} in.")
    lines.append("")
    lines.append("| Panel | Allocated height (in) | >= floor (%.1f in) |" % MIN_PANEL_HEIGHT_IN)
    lines.append("| --- | --- | --- |")
    for n, h in zip(names, heights):
        lines.append(f"| Figure {n} | {h:.1f} | {'YES' if h >= MIN_PANEL_HEIGHT_IN else 'NO'} |")
    lines.append("")
    lines.append(f"**Decision: combined overview {'GENERATED' if ok else 'SKIPPED'}.** "
                 "The four standalone figures are the primary, print-resolution "
                 "deliverables; the combined panel is a lightweight portrait overview only.")
    lines.append("")
    (out_dir / "combined_panel_readability_check.md").write_text(
        "\n".join(lines), encoding="utf-8")
    return ok, [str((out_dir / "combined_panel_readability_check.md")
                    .relative_to(PROJECT_ROOT))]


def export_combined(fa, fb, pc_b, fc, fd) -> list[str]:
    ok, report = combined_readability(OUT_DIR)
    if not ok:
        return ["[skipped - see combined_panel_readability_check.md]"] + report

    fig = plt.figure(figsize=(COMBINED_W, COMBINED_H))
    gs = fig.add_gridspec(4, 1, top=0.985, bottom=0.012, left=0.01, right=0.99,
                          hspace=0.12, height_ratios=COMBINED_ROW_RATIOS)
    draw_figure_a(fig.add_subfigure(gs[0, 0]), fa)
    draw_figure_b(fig.add_subfigure(gs[1, 0]), fb, pc_b)
    draw_figure_c(fig.add_subfigure(gs[2, 0]), fc)
    draw_figure_d(fig.add_subfigure(gs[3, 0]), fd[0], fd[2])
    paths = save_all(fig, "final_4figure_poster_panel_portrait")
    plt.close(fig)
    return paths + report


# --------------------------------------------------------------------------- #
# Captions & recommendations
# --------------------------------------------------------------------------- #
def write_captions(path: Path) -> None:
    text = """# Final Figure Captions

Descriptive within-participant analysis; participants not pooled. Language is
descriptive only - no causal, treatment-effect, clinical, or improvement claims.
Reading order: A = what changed -> B = where in the body -> C = how organized ->
D = how trustworthy.

## Figure A - Longitudinal link-level shift relative to natural variability (P3-P5, all-PC)
Top links per participant and comparison (T1 vs T2, T1 vs T3) for participants
671 and 252, analysed separately. Lollipop length is the absolute longitudinal
JcvPCA link Delta; marker colour encodes the Delta / T1 natural-variability (NV)
ratio; a dark ring flags links outside the T1 NV reference (ratio > 1) and a
small +/- glyph shows the de-emphasised direction of the signed Delta. The
largest longitudinal shifts recur in arm/hand and lower-limb links, and many
exceed the participant-specific descriptive NV reference derived from T1
repetitions. Very large ratios are driven by small NV denominators, so the NV
value is printed beside each ratio. NV is a descriptive repetition reference,
not an inferential significance threshold.

## Figure B - Functional vs null-space contribution by anatomical family (P3-P5, T1 vs T2)
For each participant, relative family share of absolute link contribution within
the variance-informed functional subspace (PCs explaining the first ~50% of
Dataset A variance) and the complementary null-space (after p50). Upper-limb and
shoulder-chain families dominate the functional subspace, consistent with
explicit task-performing links, while lower-limb, trunk, and (252 only)
pelvis-root families carry a larger relative share of the null-space (flagged
with a triangle). The null-space should be read as redundant, expressive, or
coordination-related degrees of freedom, not unused movement. Subspace
membership is variance-informed; PC-count splits are annotated per participant.

## Figure C - Movement-organization metrics and natural-variability structure
Within-timepoint R1-R2 variability on P3-P5, all-PC. Panel C1 shows the
magnitude of repetition variability (mean abs Delta) by timepoint; participant
671 shows its largest P3 repetition variability at T2, whereas participant 252
peaks at T1. Panel C2 shows concentration across links (top-3 share, with Gini
as a secondary metric). Repetition variability differs across timepoints and
participants, and concentration metrics show that natural variability changes in
its distribution across links, not only in magnitude. Higher repetition
variability is described as a broader distribution of link-level changes, not as
improved or better movement.

## Figure D - Directional robustness and magnitude-direction separation
Panel D1 summarises percent sign agreement (focus = all-PC, 0-100 scale) between
repetition-pairing variants and the pooled R1+R2 comparison, by comparison and
block. Panel D2 classifies P3-P5 all-PC links into direction-vs-magnitude
categories. Median sign agreement is roughly 53-63% for all-PC longitudinal
comparisons, so pooled link signs are useful aggregate descriptions but are not
uniformly preserved at the link level. Accordingly, abs Delta (magnitude) is
treated as the robust quantity; signed direction is reported only as secondary
context, and high-magnitude/low-agreement links are flagged as direction-sensitive.
"""
    path.write_text(text, encoding="utf-8")


def write_recommendations(path: Path) -> None:
    text = """# Optional Extra Figure Recommendations

These are optional supplementary/inset ideas only. They are NOT generated here
and must never modify, replace, or reorder the four locked figures (A-D). Each
is directly supported by an existing validated CSV. All language is descriptive
only - no causal, treatment-effect, clinical, or improvement claims. No new
modeling or unvalidated data is involved.

## Optional 1 - Robustness of the Delta/NV ratio to the chosen NV reference
1. **Proposed title:** Longitudinal Delta vs alternative natural-variability references (T1 / mean / max)
2. **Scientific purpose:** Show that the top longitudinal links of Figure A
   remain notable when the NV denominator is changed from the T1 repetition
   reference to the across-timepoint mean and max NV references.
3. **Required data source:** `longitudinal_delta_nv_ratio_by_link.csv`
   (columns `delta_to_NV_T1_ratio`, `delta_to_NV_mean_ratio`,
   `delta_to_NV_max_ratio`, `NV_mean_abs_delta`, `NV_max_abs_delta`).
4. **Added value beyond A-D:** Directly addresses the small-denominator caveat
   of Figure A by showing the ranking is not an artefact of one NV reference.
5. **Placement:** Small inset beside Figure A or supplementary panel.
6. **Caution:** Never average across participants; ratios remain descriptive
   scale comparisons, not significance, and tiny denominators still inflate ratios.

## Optional 2 - Null-space vs all-PC variability and threshold stability
1. **Proposed title:** Later-PC / null-space variability and link-identity stability
2. **Scientific purpose:** Show that null-space-like subsets often carry
   elevated mean link-level variability, and that family-level structure is more
   threshold-stable than exact link identity.
3. **Required data source:** `nullspace_noise_vs_structure_diagnostic.csv`
   (null/all ratios) and `nullspace_threshold_stability_summary.csv`
   (`threshold_stability_label`).
4. **Added value beyond A-D:** Adds a robustness/dimensionality dimension not
   covered by A-D, clarifying which structure is stable across thresholds.
5. **Placement:** Supplementary.
6. **Caution:** Magnitude elevation does not imply stable exact link identity;
   p70 is threshold-sensitive and supplementary only.

## Optional 3 - One-page take-home evidence table
1. **Proposed title:** Descriptive take-home evidence summary
2. **Scientific purpose:** Provide a compact text table of the main descriptive
   evidence questions, primary results, interpretations, and cautions.
3. **Required data source:** `poster_takehome_numeric_summary.csv`.
4. **Added value beyond A-D:** A single readable synthesis panel tying the
   figures together for viewers who do not read every panel.
5. **Placement:** Main poster bottom row or supplementary.
6. **Caution:** Keep neutral, descriptive language only; it is a summary, not an
   inferential or clinical conclusion.
"""
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    args = parse_poster_path_args(argv)
    try:
        configure_poster_paths(
            config_path=args.config,
            batch_dir=args.batch_dir,
            evidence_dir=args.evidence_dir,
            out_dir=args.out_dir,
        )
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    set_style()
    v = Validator()

    try:
        df_a = prepare_figure_a(v)
        df_b, pc_b = prepare_figure_b(v)
        df_c = prepare_figure_c(v)
        d1, d1_long, d2 = prepare_figure_d(v)
    except DataError as exc:
        v.errors.append(str(exc))
        v.write_report(OUT_DIR / "data_validation_report.md")
        print(f"[FAIL] Missing required data: {exc}")
        print(f"See {OUT_DIR / 'data_validation_report.md'}")
        return 1

    v.write_report(OUT_DIR / "data_validation_report.md")
    if v.status == "FAIL":
        print("[FAIL] Validation failed; figures not generated. See report.")
        return 1

    # Guard against silently empty figures.
    for label, frame in (("A", df_a), ("B", df_b), ("C", df_c),
                         ("D1", d1), ("D2", d2)):
        if frame.empty:
            print(f"[FAIL] Empty plotting table for figure {label}; aborting.")
            return 1

    # Save plotting tables.
    df_a.to_csv(OUT_DIR / "figure_A_plot_table.csv", index=False)
    df_b.to_csv(OUT_DIR / "figure_B_plot_table.csv", index=False)
    df_c.to_csv(OUT_DIR / "figure_C_plot_table.csv", index=False)
    d2_wide = d2.pivot(index="comparison_label", columns="interpretation_label",
                       values="n_links").reset_index()
    d1.to_csv(OUT_DIR / "figure_D_plot_table.csv", index=False)
    d1_long.to_csv(OUT_DIR / "figure_D_sign_agreement_long.csv", index=False)
    d2_wide.to_csv(OUT_DIR / "figure_D_direction_vs_magnitude_counts.csv", index=False)

    # Export figures.
    out = {}
    out["A"] = export_standalone(draw_figure_a, "figure_A_longitudinal_shift_vs_NV", (14.5, 7.4), df_a)
    out["B"] = export_standalone(draw_figure_b, "figure_B_functional_vs_nullspace_family", (13, 7.5), df_b, pc_b)
    out["C"] = export_standalone(draw_figure_c, "figure_C_movement_organization_metrics", (13, 6.2), df_c)
    out["D"] = export_standalone(lambda f: draw_figure_d(f, d1, d2),
                                 "figure_D_directional_robustness", (13, 6.4))
    out["combined"] = export_combined(df_a, df_b, pc_b, df_c, (d1, d1_long, d2))

    write_captions(OUT_DIR / "final_figure_captions.md")
    write_recommendations(OUT_DIR / "optional_extra_figure_recommendations.md")

    # Terminal summary.
    print("=" * 74)
    print("POSTER FINAL FIGURES - SUMMARY")
    print("=" * 74)
    print(f"Output directory : {OUT_DIR.relative_to(PROJECT_ROOT)}")
    print(f"Validation status: {v.status} "
          f"({sum(x['match'] for x in v.value_checks)}/{len(v.value_checks)} value checks matched)")
    print("-" * 74)
    print("Figure A  Longitudinal link-level shift vs T1 NV (671 only; P3-P5, all-PC);")
    print("          lollipop length = abs Delta, colour = Delta/NV ratio, ring = outside NV.")
    print("Figure B  Functional (p50) vs null-space anatomical-family contribution; upper-limb")
    print("          /shoulder dominate functional, lower-limb/trunk/pelvis gain in null-space.")
    print("Figure C  Within-timepoint R1-R2 variability: 671 peaks at T2, 252 at T1;")
    print("          concentration (top-3 share / Gini) varies -> NV is link-structured.")
    print("Figure D  Sign-agreement heatmap + direction-vs-magnitude categories ->")
    print("          signed direction is repetition-pairing sensitive; emphasize magnitude/rank.")
    print("-" * 74)
    for k in ("A", "B", "C", "D", "combined"):
        print(f"  [{k}] " + ", ".join(out[k]))
    print("  tables   : figure_A/B/C/D_plot_table.csv (+ figure_D_*_long / _counts)")
    print("  captions : final_figure_captions.md")
    print("  report   : data_validation_report.md")
    print("  optional : optional_extra_figure_recommendations.md")
    print("  data note: all values read/derived from validated poster CSVs; "
          "no substitutions required.")
    print("=" * 74)
    return 0 if v.status in ("PASS", "WARNING") else 1


if __name__ == "__main__":
    raise SystemExit(main())
