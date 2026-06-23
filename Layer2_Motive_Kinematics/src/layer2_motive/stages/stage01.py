"""Stage 01 — joint/bone hierarchy mapping and candidate joint detection."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from layer2_motive.config import load_config
from layer2_motive.hierarchy import (
    build_bone_inventory,
    build_candidate_joint_map,
    build_excluded_distal_bones,
    build_hierarchy_mapping,
    build_joint_channel_map,
    build_parent_child_joint_map,
    build_selected_joint_map_v0,
    summarize_skeleton_structure,
)
from layer2_motive.io import stage_output_dir, write_csv, write_text
from layer2_motive.parsing import ParsedMotiveHeader
from layer2_motive.population import compute_rotation_population_report
from layer2_motive.reporting import append_assumptions_log, render_stage_report

FEATURE_BOUNDARY_NOTE = (
    "Final analysis feature selection is deferred until after Layer 2 output validation "
    "and before Layer 3 JcvPCA. See `docs/FEATURE_SELECTION_BOUNDARY.md`."
)


def _render_joint_selection_summary(
    candidate_df: pd.DataFrame,
    selected_df: pd.DataFrame,
    excluded_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    skeleton_summary: dict,
    population_df: pd.DataFrame,
) -> str:
    auto_included = selected_df[selected_df["included_in_v0"]]
    review_df = candidate_df.loc[candidate_df["requires_manual_review"]].copy()
    root_children = candidate_df.loc[
        candidate_df["exclusion_reason"] == "parent_is_root"
    ].copy()
    trunk_review = review_df.loc[
        review_df["selection_rule"].isin(
            ["trunk_or_root_candidate", "exclude_root_children_by_default"]
        )
    ].copy()

    pop_fail = int((population_df["population_status"] == "fail").sum())
    pop_warn = int((population_df["population_status"] == "warning").sum())

    lines = [
        "# Joint selection summary (provisional — not frozen)",
        "",
        "## Feature selection boundary",
        "",
        "- `selected_joint_map_v0.csv` is **provisional** (`frozen = false`).",
        "- This file does **not** define the final analysis feature set.",
        f"- {FEATURE_BOUNDARY_NOTE}",
        "",
        "## Overview",
        "",
        f"- Bones in inventory: {len(inventory_df)}",
        f"- Candidate parent-child joints: {len(candidate_df)}",
        f"- Provisional auto-included joints (heuristic only): {len(auto_included)}",
        f"- Excluded distal/toe/finger candidates: {len(excluded_df)}",
        f"- Uncertain candidates requiring manual review: {len(review_df)}",
        f"- Structural population check: {pop_fail} fail, {pop_warn} warning "
        f"(see `rotation_population_report.csv`)",
        "",
        "## Detected skeleton / root anchor",
        "",
        "Root/asset anchor bones are reported exactly as detected in the CSV. "
        "They are **not** renamed to Pelvis unless that name appears in the export.",
        "",
    ]

    root_anchors = skeleton_summary["root_anchors"]
    if not root_anchors:
        lines.append("- No root anchor bone detected (`Parent == Root`).")
    else:
        for anchor in root_anchors:
            lines.append(
                f"- Source `{anchor['source_bone_name']}` → "
                f"canonical `{anchor['canonical_bone_name']}` "
                f"(parent `{anchor['source_parent_name']}`)"
            )

    lines.extend(["", "## Trunk chain / main hierarchy summary", ""])
    trunk_chains = skeleton_summary["trunk_chains"]
    if not trunk_chains:
        lines.append("- No trunk chain inferred from hierarchy.")
    else:
        for idx, chain in enumerate(trunk_chains, start=1):
            lines.append(f"- Chain {idx}: {' → '.join(chain)}")

    lines.extend(
        [
            "",
            "## Provisional auto-included joints",
            "",
        ]
    )
    if auto_included.empty:
        lines.append("- None")
    else:
        for _, row in auto_included.iterrows():
            lines.append(f"- `{row['parent_bone']}` → `{row['child_bone']}` ({row['joint_id']})")

    lines.extend(["", "## Root / trunk candidates requiring review", ""])
    if root_children.empty and trunk_review.empty:
        lines.append("- None flagged")
    else:
        trunk_rows = pd.concat([root_children, trunk_review]).drop_duplicates(subset=["joint_id"])
        for _, row in trunk_rows.iterrows():
            reason = row["exclusion_reason"] or row["selection_rule"]
            review_flag = row["requires_manual_review"]
            lines.append(
                f"- `{row['parent_bone']}` → `{row['child_bone']}` "
                f"(reason={reason}, review={review_flag})"
            )

    lines.extend(["", "## Excluded distal / finger / toe candidates", ""])
    if excluded_df.empty:
        lines.append("- None")
    else:
        for _, row in excluded_df.iterrows():
            lines.append(
                f"- `{row['parent_bone']}` → `{row['child_bone']}`: {row['exclusion_reason']}"
            )

    lines.extend(["", "## All uncertain candidates", ""])
    if review_df.empty:
        lines.append("- None")
    else:
        for _, row in review_df.iterrows():
            lines.append(
                f"- `{row['parent_bone']}` → `{row['child_bone']}` "
                f"(rule={row['selection_rule']}, reason={row['exclusion_reason'] or 'none'})"
            )

    lines.extend(
        [
            "",
            "## Next step",
            "",
            "Validate native skeleton documentation, provisional joint heuristics, and "
            "structural population reports for this file. Continue to Stage 02 only after review.",
            "Do not treat `selected_joint_map_v0.csv` as the final Layer 3 feature set.",
            "",
        ]
    )
    return "\n".join(lines)


def run_stage_01(
    input_csv: Path,
    output_dir: Path,
    parsed: ParsedMotiveHeader | None = None,
    config_path: Path | None = None,
) -> dict[str, pd.DataFrame]:
    if parsed is None:
        from layer2_motive.stages.stage00 import run_stage_00

        parsed = run_stage_00(input_csv, output_dir)

    config = load_config(config_path)
    prefix_rule = config.get("naming", {}).get("subject_prefix_rule", "colon_suffix")
    stage_dir = stage_output_dir(output_dir, "01")

    inventory = build_bone_inventory(parsed.columns, prefix_rule=prefix_rule)
    inventory_df = pd.DataFrame(inventory)
    skeleton_summary = summarize_skeleton_structure(inventory)
    candidate = build_candidate_joint_map(inventory, config)
    candidate_df = pd.DataFrame(candidate)
    selected = build_selected_joint_map_v0(candidate)
    selected_df = pd.DataFrame(selected)
    excluded = build_excluded_distal_bones(candidate)
    excluded_df = pd.DataFrame(excluded)
    hierarchy_df = pd.DataFrame(build_hierarchy_mapping(inventory))
    parent_child_df = pd.DataFrame(build_parent_child_joint_map(candidate))
    channel_df = pd.DataFrame(build_joint_channel_map(parsed.columns))

    population_rows, _ = compute_rotation_population_report(input_csv, parsed, inventory)
    population_df = pd.DataFrame(population_rows)

    selected_body_df = selected_df[selected_df["included_in_v0"]][
        ["joint_id", "parent_bone", "child_bone", "source_parent_bone", "source_child_bone"]
    ].copy()

    missing_expected_df = pd.DataFrame(columns=["expected_joint", "status", "notes"])

    write_csv(inventory_df, stage_dir / "bone_inventory.csv")
    write_csv(inventory_df, stage_dir / "all_bones_inventory.csv")
    write_csv(candidate_df, stage_dir / "candidate_joint_map.csv")
    write_csv(selected_df, stage_dir / "selected_joint_map_v0.csv")
    write_csv(excluded_df, stage_dir / "excluded_distal_bones.csv")
    write_csv(hierarchy_df, stage_dir / "hierarchy_mapping.csv")
    write_csv(parent_child_df, stage_dir / "parent_child_joint_map.csv")
    write_csv(channel_df, stage_dir / "joint_channel_map.csv")
    write_csv(selected_body_df, stage_dir / "selected_body_bones.csv")
    write_csv(missing_expected_df, stage_dir / "missing_expected_joints.csv")
    write_csv(population_df, stage_dir / "rotation_population_report.csv")

    summary = _render_joint_selection_summary(
        candidate_df,
        selected_df,
        excluded_df,
        inventory_df,
        skeleton_summary,
        population_df,
    )
    write_text(stage_dir / "joint_selection_summary.md", summary)

    auto_count = int(selected_df["included_in_v0"].sum())
    review_count = int(candidate_df["requires_manual_review"].sum())
    pop_fail = int((population_df["population_status"] == "fail").sum())
    pop_warn = int((population_df["population_status"] == "warning").sum())
    assumptions = [
        f"Subject prefix rule: {prefix_rule} "
        "(reversible via subject_prefix + canonical_bone_name).",
        "Distal exclusion uses provisional config heuristics only; joint set not frozen.",
        f"Provisional auto-included joints: {auto_count}; uncertain candidates: {review_count}.",
        "Parent==Root joints excluded from auto-selection but reported for manual review.",
        "Root/asset anchor reported as detected; not renamed to Pelvis unless present in CSV.",
        FEATURE_BOUNDARY_NOTE,
        (
            "Structural rotation population check counts complete raw XYZW rows only; "
            "not norm QC or component-order validation."
        ),
    ]

    root_anchor_names = [
        anchor["canonical_bone_name"] for anchor in skeleton_summary["root_anchors"]
    ]
    trunk_chains = skeleton_summary["trunk_chains"]

    detected = [
        f"Bones detected: {len(inventory_df)}",
        f"Candidate joints: {len(candidate_df)}",
        f"Provisional auto-included: {auto_count}",
        f"Excluded distal/toe/finger: {len(excluded_df)}",
        f"Uncertain for review: {review_count}",
        f"Root/asset anchors: {root_anchor_names or ['none']}",
        f"Trunk chains: {trunk_chains or ['none inferred']}",
        f"Population check fail/warning bones: {pop_fail}/{pop_fail + pop_warn}",
        "selected_joint_map_v0 frozen=false (provisional only)",
    ]

    outputs = [
        str(stage_dir / "report.md"),
        str(stage_dir / "bone_inventory.csv"),
        str(stage_dir / "candidate_joint_map.csv"),
        str(stage_dir / "selected_joint_map_v0.csv"),
        str(stage_dir / "excluded_distal_bones.csv"),
        str(stage_dir / "joint_selection_summary.md"),
        str(stage_dir / "rotation_population_report.csv"),
        str(stage_dir / "hierarchy_mapping.csv"),
        str(stage_dir / "parent_child_joint_map.csv"),
        str(stage_dir / "joint_channel_map.csv"),
    ]

    report = render_stage_report(
        stage_name="Stage 01 — Joint mapping and candidate joint detection",
        input_files=[str(input_csv)],
        detected=detected,
        assumptions=assumptions,
        outputs=outputs,
        warnings=[],
        errors=[],
        validation_status="PASS — native skeleton documented; joint set not frozen",
        next_action=(
            "Review native skeleton summary, provisional joint map, and population report. "
            "Final analysis feature selection is deferred until after Layer 2 validation "
            "and before Layer 3. Continue to Stage 02 after review."
        ),
    )
    write_text(stage_dir / "report.md", report)
    append_assumptions_log(output_dir, assumptions)

    return {
        "inventory": inventory_df,
        "candidate": candidate_df,
        "selected": selected_df,
        "excluded": excluded_df,
        "population": population_df,
    }
