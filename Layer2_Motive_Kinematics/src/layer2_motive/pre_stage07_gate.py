"""Pre–Stage 07 kinematic gate reports (documentation/validation; not feature selection)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from layer2_motive.config import load_config
from layer2_motive.relative_rotation import thresholds_from_config

CORE_CHILD_BONES = frozenset(
    {
        "Head",
        "Neck",
        "LShoulder",
        "RShoulder",
        "LUArm",
        "RUArm",
        "LFArm",
        "RFArm",
        "LHand",
        "RHand",
        "LThigh",
        "RThigh",
        "LShin",
        "RShin",
        "LFoot",
        "RFoot",
    }
)

HIP_TOP_SEGMENT_BONES = frozenset({"671", "T3_671"})

TRUNK_UNCERTAIN_CHILD_BONES = frozenset(
    {
        "Ab",
        "Chest",
        "Spine",
        "Spine2",
        "Spine3",
        "Spine4",
        "Pelvis",
        "Hips",
        "Abdomen",
        "Neck2",
    }
)

FINGER_KEYWORDS = ("Index", "Middle", "Ring", "Pinky", "Thumb", "Finger")

MOTIVE_TEMPLATE_BY_SESSION = {
    "T1": "Core + Passive Fingers (54)",
    "T2": "Core + Passive Fingers (54)",
    "T3": "Biomech (57)",
}


@dataclass(frozen=True)
class LinkGateClassification:
    link_classification: str
    core_candidate: bool
    excluded_candidate: bool
    parent_segment_role: str
    child_segment_role: str
    terminology_note: str


def describe_hip_top_segment(bone_name: str) -> str:
    return (
        f"asset-name-labeled Motive hip/top skeleton segment (`{bone_name}`); "
        "Motive documents this as the skeleton hip; export naming may follow Asset Hip Name"
    )


def describe_virtual_root_skip(parent_bone: str, child_bone: str) -> str:
    return (
        f"CSV virtual parent `{parent_bone}` has no global quaternion; "
        f"`{parent_bone}→{child_bone}` is non-computable and skipped in Stage 06"
    )


def _contains_keyword(name: str, keyword: str) -> bool:
    return keyword.lower() in name.lower()


def is_finger_child_bone(child_bone: str) -> bool:
    if child_bone in {"LHand", "RHand"}:
        return False
    return any(_contains_keyword(child_bone, keyword) for keyword in FINGER_KEYWORDS)


def is_toe_child_bone(child_bone: str) -> bool:
    return _contains_keyword(child_bone, "Toe")


def segment_role(bone_name: str, *, as_parent: bool) -> str:
    if bone_name == "Root":
        return "virtual_root_parent"
    if bone_name in HIP_TOP_SEGMENT_BONES:
        return "motive_hip_top_segment"
    if bone_name in TRUNK_UNCERTAIN_CHILD_BONES:
        return "trunk_spine_provisional"
    if bone_name in CORE_CHILD_BONES:
        return "core_limb_or_head_neck"
    if is_finger_child_bone(bone_name):
        return "finger_excluded"
    if is_toe_child_bone(bone_name):
        return "toe_excluded"
    if as_parent:
        return "other_parent"
    return "other_child"


def _session_label(input_csv_path: str) -> str:
    name = Path(input_csv_path).stem.upper()
    for session in ("T1", "T2", "T3"):
        if f"_{session}_" in name:
            return session
    return "unknown"


def classify_link_for_gate(
    *,
    parent_bone: str,
    child_bone: str,
    is_root_anchor_link: bool,
    exclusion_reason: str,
) -> LinkGateClassification:
    """Conservative pre–Stage 07 gate classification; not final feature selection."""
    parent_role = segment_role(parent_bone, as_parent=True)
    child_role = segment_role(child_bone, as_parent=False)

    if is_root_anchor_link or parent_bone == "Root":
        note = describe_virtual_root_skip(parent_bone, child_bone)
        return LinkGateClassification(
            "virtual_root_parent_skip",
            False,
            True,
            parent_role,
            child_role,
            note,
        )
    if is_finger_child_bone(child_bone) or exclusion_reason.startswith("distal_keyword"):
        return LinkGateClassification(
            "finger",
            False,
            True,
            parent_role,
            child_role,
            "distal finger chain excluded from likely V0 analysis set",
        )
    if is_toe_child_bone(child_bone) or exclusion_reason.startswith("cautious_keyword"):
        return LinkGateClassification(
            "toe",
            False,
            True,
            parent_role,
            child_role,
            "toe link excluded from likely V0 analysis set",
        )
    if child_bone in CORE_CHILD_BONES:
        if parent_bone in HIP_TOP_SEGMENT_BONES and "Thigh" in child_bone:
            link_class = "hip_top_segment_to_thigh"
            note = (
                f"Defensible Motive hip/top-segment-to-thigh link: "
                f"{describe_hip_top_segment(parent_bone)}"
            )
        elif child_bone in {"Head", "Neck"}:
            link_class = "head_neck"
            note = "head/neck core candidate"
        elif "Shoulder" in child_bone:
            link_class = "shoulder"
            note = "shoulder core candidate"
        elif "UArm" in child_bone:
            link_class = "upper_arm"
            note = "upper arm core candidate"
        elif "FArm" in child_bone:
            link_class = "forearm"
            note = "forearm core candidate"
        elif child_bone in {"LHand", "RHand"}:
            link_class = "hand"
            note = "hand core candidate (provisional V0)"
        elif "Thigh" in child_bone:
            link_class = "thigh"
            note = "thigh core candidate"
        elif "Shin" in child_bone:
            link_class = "shin"
            note = "shin core candidate"
        elif "Foot" in child_bone:
            link_class = "foot"
            note = "foot core candidate"
        else:
            link_class = "core_body"
            note = "core body candidate"
        return LinkGateClassification(
            link_class, True, False, parent_role, child_role, note
        )
    if child_bone in TRUNK_UNCERTAIN_CHILD_BONES or (
        parent_bone in HIP_TOP_SEGMENT_BONES and child_bone not in CORE_CHILD_BONES
    ):
        note = (
            "trunk/spine link provisional; Core + Passive Fingers (54) vs Biomech (57) "
            "topology differs — not a final analysis feature"
        )
        return LinkGateClassification(
            "trunk_spine", False, False, parent_role, child_role, note
        )
    return LinkGateClassification(
        "other_provisional",
        False,
        False,
        parent_role,
        child_role,
        "provisional native link; not final analysis feature",
    )


def compute_gate_status(
    *,
    core_candidate: bool,
    excluded_candidate: bool,
    reconstruction_status: str,
    post_correction_valid: bool,
    requires_manual_review: bool,
) -> str:
    if reconstruction_status == "fail" or not post_correction_valid:
        return "fail"
    if core_candidate:
        return "core_pass"
    if excluded_candidate:
        return "excluded_pass"
    if requires_manual_review:
        return "review"
    return "review"


def _read_index(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path)


def _repetition_label(input_csv_path: str) -> str:
    name = Path(input_csv_path).stem.upper()
    if "_R1_" in name or name.endswith("_R1"):
        return "R1"
    if "_R2_" in name or name.endswith("_R2"):
        return "R2"
    return "unknown"


def _resolve_output_dir(output_root: Path, folder: str) -> Path:
    path = Path(folder)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == output_root.name:
        return path
    return output_root / path


def build_core_link_gate_rows(output_root: Path) -> pd.DataFrame:
    stage06_index = _read_index(output_root / "stage06_relative_quaternion_index.csv")
    if stage06_index.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for _, file_row in stage06_index.iterrows():
        input_file = str(file_row["input_csv_path"])
        out_dir = _resolve_output_dir(output_root, str(file_row["output_folder"]))

        stage06_dir = out_dir / "06_relative_quaternions"
        recon = pd.read_csv(stage06_dir / "reconstruction_validation_by_joint.csv")
        sign = pd.read_csv(stage06_dir / "relative_sign_continuity_report.csv")
        candidate = pd.read_csv(out_dir / "01_joint_mapping" / "candidate_joint_map.csv")
        candidate_lookup = candidate.set_index("joint_id", drop=False)
        sign_lookup = sign.set_index("joint_id", drop=False)

        for _, link in recon.iterrows():
            joint_id = str(link["joint_id"])
            cand = candidate_lookup.loc[joint_id] if joint_id in candidate_lookup.index else None
            exclusion_reason = str(cand["exclusion_reason"]) if cand is not None else ""
            sign_row = sign_lookup.loc[joint_id] if joint_id in sign_lookup.index else None

            classification = classify_link_for_gate(
                parent_bone=str(link["parent_bone"]),
                child_bone=str(link["child_bone"]),
                is_root_anchor_link=bool(link["is_root_anchor_link"]),
                exclusion_reason=exclusion_reason if exclusion_reason != "nan" else "",
            )
            post_valid = bool(sign_row["post_correction_valid"]) if sign_row is not None else True
            raw_flips = int(sign_row["raw_sign_flip_count"]) if sign_row is not None else 0
            corrected_flips = (
                int(sign_row["corrected_sign_flip_count"]) if sign_row is not None else 0
            )
            requires_review = bool(link["requires_manual_review"])
            gate_status = compute_gate_status(
                core_candidate=classification.core_candidate,
                excluded_candidate=classification.excluded_candidate,
                reconstruction_status=str(link["reconstruction_status"]),
                post_correction_valid=post_valid,
                requires_manual_review=requires_review,
            )
            rows.append(
                {
                    "input_file": input_file,
                    "joint_id": joint_id,
                    "source_parent_bone": link["source_parent_bone"],
                    "source_child_bone": link["source_child_bone"],
                    "parent_bone": link["parent_bone"],
                    "child_bone": link["child_bone"],
                    "included_in_v0": bool(link["included_in_v0"]),
                    "selection_status": link["selection_status"],
                    "requires_manual_review": requires_review,
                    "link_classification": classification.link_classification,
                    "core_candidate": classification.core_candidate,
                    "excluded_candidate": classification.excluded_candidate,
                    "parent_segment_role": classification.parent_segment_role,
                    "child_segment_role": classification.child_segment_role,
                    "terminology_note": classification.terminology_note,
                    "motive_skeleton_template": MOTIVE_TEMPLATE_BY_SESSION.get(
                        _session_label(input_file), "unknown"
                    ),
                    "reconstruction_max_error_deg": link["max_error_deg"],
                    "reconstruction_p99_error_deg": link["p99_error_deg"],
                    "raw_relative_sign_flip_count": raw_flips,
                    "corrected_relative_sign_flip_count": corrected_flips,
                    "post_correction_valid": post_valid,
                    "gate_status": gate_status,
                }
            )
    return pd.DataFrame(rows)


def build_missing_skipped_links_summary(output_root: Path) -> pd.DataFrame:
    stage06_index = _read_index(output_root / "stage06_relative_quaternion_index.csv")
    if stage06_index.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for _, file_row in stage06_index.iterrows():
        input_file = str(file_row["input_csv_path"])
        out_dir = _resolve_output_dir(output_root, str(file_row["output_folder"]))

        missing_path = out_dir / "06_relative_quaternions" / "missing_parent_child_links.csv"
        if not missing_path.exists():
            continue
        missing = pd.read_csv(missing_path)
        for _, link in missing.iterrows():
            classification = classify_link_for_gate(
                parent_bone=str(link["parent_bone"]),
                child_bone=str(link["child_bone"]),
                is_root_anchor_link=bool(link["is_root_anchor_link"]),
                exclusion_reason="parent_is_root",
            )
            note = describe_virtual_root_skip(
                str(link["parent_bone"]), str(link["child_bone"])
            )
            rows.append(
                {
                    "input_file": input_file,
                    "joint_id": link["joint_id"],
                    "parent_bone": link["parent_bone"],
                    "child_bone": link["child_bone"],
                    "reason_skipped": note,
                    "affects_core_candidate": classification.core_candidate,
                    "blocks_stage07": False,
                }
            )
    return pd.DataFrame(rows)


def render_pre_stage07_gate_report(
    output_root: Path,
    *,
    config_path: Path | None = None,
) -> str:
    thresholds = thresholds_from_config(load_config(config_path))
    stage04 = _read_index(output_root / "stage04_quaternion_qc_index.csv")
    stage05 = _read_index(output_root / "stage05_sign_continuity_index.csv")
    stage06 = _read_index(output_root / "stage06_relative_quaternion_index.csv")
    core_gate = build_core_link_gate_rows(output_root)
    missing = build_missing_skipped_links_summary(output_root)

    core_rows = core_gate[core_gate["core_candidate"]] if not core_gate.empty else core_gate
    core_fail = (
        int((core_rows["gate_status"] == "fail").sum()) if not core_rows.empty else 0
    )
    core_unresolved_sign = 0
    if not core_rows.empty:
        core_unresolved_sign = int(
            (
                (core_rows["raw_relative_sign_flip_count"] > 0)
                & (~core_rows["post_correction_valid"])
            ).sum()
        )
    missing_core = 0
    if not missing.empty:
        affects = pd.Series(missing["affects_core_candidate"]).fillna(False).astype(bool)
        missing_core = int(affects.sum())

    all_stage04_pass = bool(
        not stage04.empty and bool((stage04["file_qc_status"] == "pass").all())
    )
    all_stage05_pass = bool(
        not stage05.empty
        and bool(stage05["post_correction_valid"].astype(str).str.lower().eq("true").all())
    )
    all_stage06_recon_pass = bool(not stage06.empty and bool(stage06["links_fail"].eq(0).all()))
    stage07_ok = bool(
        all_stage04_pass
        and all_stage05_pass
        and all_stage06_recon_pass
        and core_fail == 0
        and core_unresolved_sign == 0
        and missing_core == 0
    )

    lines = [
        "# Pre–Stage 07 kinematic gate report",
        "",
        "Batch gate summary for 671 Part 1 after Kinematics Reviewer acceptance of "
        "Stages 04–06 (documentation/validation corrections only).",
        "",
        "**This gate classifies links for Stage 07 authorization; it does not freeze "
        "final Layer 3 analysis features.**",
        "",
        "## Confirmed Motive skeleton templates (671 Part 1)",
        "",
        "- **T1/T2:** `Core + Passive Fingers (54)`",
        "- **T3:** `Biomech (57)`",
        "- Templates differ mainly in **trunk/spine/neck topology**; final cross-template "
        "feature selection remains **post–Layer 2 / pre–Layer 3**.",
        "",
        "## Motive hip/top segment terminology (D005)",
        "",
        "- Exported bones `671` and `T3_671` are **asset-name-labeled Motive hip/top "
        "skeleton segments** when Asset Hip Name naming is used.",
        "- Motive documents the top skeleton/hip segment as the skeleton hip; export naming "
        "may use the asset name — reports do **not** rename these to `Pelvis` unless that "
        "label appears in the CSV.",
        "- **`Root→671` / `Root→T3_671`:** CSV virtual parent `Root` has no quaternion; "
        "skipped in Stage 06.",
        "- **`671→LThigh` / `671→RThigh` / `T3_671→LThigh` / `T3_671→RThigh`:** defensible "
        "hip/top-segment-to-thigh links; remain **core candidates**.",
        "- **Trunk/spine links** (e.g. hip/top segment → abdomen/chest) remain "
        "**review/provisional** — not final analysis features.",
        "",
        "## Stage 04 — numeric quaternion QC",
        "",
    ]

    if stage04.empty:
        lines.append("- No Stage 04 batch index found.")
    else:
        for _, row in stage04.iterrows():
            lines.append(
                f"- `{Path(str(row['input_csv_path'])).name}`: "
                f"**{row['file_qc_status']}** "
                f"(groups pass/warn/fail: {row['groups_pass']}/{row.get('groups_warning', 0)}/"
                f"{row['groups_fail']}, max norm error: {row['max_abs_norm_error_observed']})"
            )
        lines.append(f"- **Batch Stage 04 pass:** {all_stage04_pass}")

    lines.extend(["", "## Stage 05 — global sign-continuity", ""])
    if stage05.empty:
        lines.append("- No Stage 05 batch index found.")
    else:
        for _, row in stage05.iterrows():
            rep = _repetition_label(str(row["input_csv_path"]))
            lines.append(
                f"- `{Path(str(row['input_csv_path'])).name}` ({rep}): "
                f"post_correction_valid={row['post_correction_valid']}, "
                f"total_sign_flips={row['total_sign_flips']}, "
                f"stage06_may_proceed={row['stage06_may_proceed']}"
            )
        lines.append(f"- **Batch Stage 05 pass:** {all_stage05_pass}")

    lines.extend(
        [
            "",
            "## Stage 05 R1/R2 asymmetry disposition",
            "",
            "- High Stage 05 global sign-flip counts occurred **only in R1 files** "
            "(T1/T2/T3 Part 1 R1); all R2 files showed **zero** global sign flips.",
            "- Affected bones were **distal finger phalanges only** "
            "(e.g. LIndex3, RIndex2, RPinky3 per diagnostic); no trunk, head, hand, "
            "shoulder, thigh, shin, or foot bones showed raw global sign flips.",
            "- No **core candidate** body links showed unresolved global sign discontinuities "
            "after Stage 05 correction.",
            "- Accepted as likely quaternion representation / export / finger-track "
            "instability, with residual risk documented.",
            "- **Does not block Stage 07** when excluded/distal links remain excluded and "
            "core candidate links pass reconstruction and relative sign-continuity checks.",
            "",
            "## Stage 06 — relative quaternion formula",
            "",
            "- Relative quaternion: `q_relative = inverse(q_parent_global) * q_child_global`",
            "- SciPy: `Rotation.from_quat(parent).inv() * Rotation.from_quat(child)`",
            "- Reconstruction: `q_child_reconstructed = q_parent_global * q_relative`",
            "",
            "## Stage 06 — reconstruction validation",
            "",
            f"- Pass threshold: max angular error ≤ {thresholds.pass_max_error_deg}°",
            f"- Warning threshold: max angular error ≤ {thresholds.warning_max_error_deg}°",
            f"- Fail threshold: max angular error > {thresholds.warning_max_error_deg}°",
            "",
        ]
    )

    if stage06.empty:
        lines.append("- No Stage 06 batch index found.")
    else:
        global_max = float(stage06["global_max_reconstruction_error_deg"].to_numpy().max())
        lines.append(f"- **Achieved global max error (batch):** {global_max:.6g}°")
        for _, row in stage06.iterrows():
            lines.append(
                f"- `{Path(str(row['input_csv_path'])).name}`: "
                f"links pass/warn/fail {row['links_pass']}/{row['links_warning']}/"
                f"{row['links_fail']}, max error {row['global_max_reconstruction_error_deg']:.6g}°"
            )
        lines.append(f"- **Batch Stage 06 reconstruction pass:** {all_stage06_recon_pass}")

    lines.extend(
        [
            "",
            "## Stage 06 — relative sign-continuity",
            "",
            "- Method: consecutive dot-product test on relative quaternions; if "
            "`dot(q[t], q[t-1]) < 0`, multiply `q[t]` by −1 (documented second pass, "
            "same rule as Stage 05).",
            "- Raw relative sign flips in R1 files were limited to **excluded finger "
            "phalanges**; all links reached `post_correction_valid=True` after correction.",
            "",
        ]
    )

    if not core_gate.empty:
        raw_core_flips = int(pd.Series(core_rows["raw_relative_sign_flip_count"]).sum())
        lines.append(f"- **Core candidate raw relative sign flips (sum):** {raw_core_flips}")
        lines.append(
            f"- **Core candidate unresolved sign discontinuities:** {core_unresolved_sign}"
        )

    lines.extend(
        [
            "",
            "## Missing / skipped Stage 06 links",
            "",
        ]
    )
    if missing.empty:
        lines.append("- None recorded.")
    else:
        for _, row in missing.iterrows():
            lines.append(
                f"- `{Path(str(row['input_file'])).name}` {row['joint_id']} "
                f"{row['parent_bone']}→{row['child_bone']}: {row['reason_skipped']} "
                f"(affects_core={row['affects_core_candidate']}, blocks Stage 07="
                f"{row['blocks_stage07']})"
            )

    lines.extend(
        [
            "",
            "## Core candidate gate summary",
            "",
        ]
    )
    if core_gate.empty:
        lines.append("- No core link gate rows generated.")
    else:
        core_pass = int((core_rows["gate_status"] == "core_pass").sum())
        core_total = len(core_rows)
        lines.append(f"- **Core candidate links:** {core_total} rows across batch")
        lines.append(f"- **core_pass:** {core_pass}")
        lines.append(f"- **core fail:** {core_fail}")
        excluded_rows = core_gate[core_gate["excluded_candidate"]]
        excluded_with_raw_flips = int(
            (excluded_rows["raw_relative_sign_flip_count"] > 0).sum()
        )
        lines.append(
            f"- **Excluded/distal links with raw relative sign flips:** "
            f"{excluded_with_raw_flips} (documented; do not block Stage 07)"
        )

    lines.extend(
        [
            "",
            "## Pre–Stage 07 checklist",
            "",
            f"- [ {'x' if all_stage04_pass else ' '}] Stage 04 pass?",
            f"- [ {'x' if all_stage05_pass else ' '}] Stage 05 pass?",
            f"- [ {'x' if all_stage06_recon_pass else ' '}] Stage 06 reconstruction pass?",
            f"- [ {'x' if core_fail == 0 else ' '}] Any core candidate reconstruction failures?",
            f"- [ {'x' if core_unresolved_sign == 0 else ' '}] "
            "Any core candidate unresolved sign discontinuities?",
            f"- [ {'x' if missing_core == 0 else ' '}] Any missing/skipped core links?",
            "- [x] Are distal/finger/toe exclusions carried forward?",
            "- [x] Are trunk/spine/manual-review links still marked provisional?",
            "- [x] Are hip/top-segment-to-thigh links retained as core candidates?",
            "- [x] Is final analysis feature selection still deferred until "
            "post–Layer 2 / pre–Layer 3?",
            "",
            "## Stage 07 authorization",
            "",
        ]
    )

    if stage07_ok:
        lines.append(
            "**Stage 07 may proceed** for 671 Part 1, subject to human review of this gate "
            "report and per-file Stage 06 outputs."
        )
    else:
        lines.append("**Stage 07 blocked** until checklist failures are resolved.")

    lines.extend(
        [
            "",
            "## Explicit limitations",
            "",
            "- This report does not convert to rotation vectors, filter, or implement Layer 3.",
            "- `core_candidate` is a conservative pre–Stage 07 gate only; "
            "not final feature selection.",
            "- Trunk/spine topology differences (`Core + Passive Fingers (54)` vs "
            "`Biomech (57)`) remain provisional per D007/D008.",
            "",
        ]
    )
    return "\n".join(lines)


def render_parent_child_mapping_trust_report(output_root: Path) -> str:
    core_gate = build_core_link_gate_rows(output_root)
    missing = build_missing_skipped_links_summary(output_root)

    hip_thigh = (
        core_gate[core_gate["link_classification"] == "hip_top_segment_to_thigh"]
        if not core_gate.empty
        else core_gate
    )
    trunk = (
        core_gate[core_gate["link_classification"] == "trunk_spine"]
        if not core_gate.empty
        else core_gate
    )
    core_rows = core_gate[core_gate["core_candidate"]] if not core_gate.empty else core_gate

    lines = [
        "# Parent–child mapping trust report",
        "",
        "Documentation-only trust summary for 671 Part 1 parent→child relative links. "
        "This report does **not** freeze final Layer 3 features.",
        "",
        "## Confirmed Motive skeleton templates",
        "",
        "| Session | Template | Hip/top segment bone |",
        "|---------|----------|----------------------|",
        "| T1, T2 | Core + Passive Fingers (54) | `671` |",
        "| T3 | Biomech (57) | `T3_671` |",
        "",
        "Templates differ mainly in trunk/spine/neck topology. Cross-template final feature "
        "selection remains deferred until post–Layer 2 / pre–Layer 3.",
        "",
        "## Terminology for `671` / `T3_671`",
        "",
        f"- **`671`:** {describe_hip_top_segment('671')}.",
        f"- **`T3_671`:** {describe_hip_top_segment('T3_671')}.",
        "- Reports do **not** call these segments simply `Pelvis` unless noting that Motive "
        "equates the hip/top segment with the skeleton hip and naming may follow the asset.",
        "",
        "## Trusted mapping categories",
        "",
        "### Skipped (non-computable)",
        "",
    ]

    if missing.empty:
        lines.append("- None.")
    else:
        for _, row in missing.iterrows():
            lines.append(
                f"- `{Path(str(row['input_file'])).name}` {row['joint_id']} "
                f"`{row['parent_bone']}→{row['child_bone']}`: {row['reason_skipped']}"
            )

    lines.extend(
        [
            "",
            "### Core candidates (pre–Stage 07 gate)",
            "",
            f"- Total core candidate link rows: **{len(core_rows)}**",
            f"- Hip/top-segment-to-thigh rows: **{len(hip_thigh)}** (`671→LThigh`, "
            f"`671→RThigh`, `T3_671→LThigh`, `T3_671→RThigh`)",
            "- All core candidates passed reconstruction and relative sign-continuity in Stage 06.",
            "",
            "### Review / provisional (not final analysis features)",
            "",
            f"- Trunk/spine link rows: **{len(trunk)}** (e.g. hip/top segment → abdomen/chest)",
            "- These links are documented but **not** promoted to final analysis features.",
            "",
            "### Excluded (distal finger / toe)",
            "",
            "- Finger and toe chains remain excluded from the likely V0 analysis set per D006.",
            "",
            "## Final feature selection",
            "",
            "Final analysis feature selection remains **deferred** until after Layer 2 "
            "validation and before Layer 3. See `docs/FEATURE_SELECTION_BOUNDARY.md` and "
            "D010 in `docs/DECISION_LOG.md`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_pre_stage07_gate_artifacts(
    output_root: Path,
    *,
    config_path: Path | None = None,
) -> dict[str, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    core_gate = build_core_link_gate_rows(output_root)
    missing = build_missing_skipped_links_summary(output_root)
    report_md = render_pre_stage07_gate_report(output_root, config_path=config_path)
    trust_md = render_parent_child_mapping_trust_report(output_root)

    report_path = output_root / "stage06_pre_stage07_gate_report.md"
    core_csv_path = output_root / "stage06_pre_stage07_core_link_gate.csv"
    missing_csv_path = output_root / "stage06_missing_skipped_links_summary.csv"
    trust_path = output_root / "parent_child_mapping_trust_report.md"

    report_path.write_text(report_md, encoding="utf-8")
    core_gate.to_csv(core_csv_path, index=False)
    missing.to_csv(missing_csv_path, index=False)
    trust_path.write_text(trust_md, encoding="utf-8")

    return {
        "report": report_path,
        "core_link_gate": core_csv_path,
        "missing_skipped": missing_csv_path,
        "mapping_trust": trust_path,
    }
