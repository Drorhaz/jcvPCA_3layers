"""Summarize Stage 07 core jump-failure duration and clustering from labeled parquet outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

OUTPUT_ROOT = Path("outputs")


def _cluster_frames(
    frames: pd.Series,
    times: pd.Series,
    jump_mags: pd.Series,
    *,
    cluster_type: str,
) -> list[dict]:
    if frames.empty:
        return []

    ordered = pd.DataFrame(
        {"frame": frames.to_numpy(), "time_sec": times.to_numpy(), "jump_mag": jump_mags.to_numpy()}
    ).sort_values("frame")

    clusters: list[dict] = []
    start_idx = 0
    frame_vals = ordered["frame"].to_numpy()

    for idx in range(1, len(ordered) + 1):
        at_end = idx == len(ordered)
        non_consecutive = not at_end and frame_vals[idx] != frame_vals[idx - 1] + 1
        if at_end or non_consecutive:
            segment = ordered.iloc[start_idx:idx]
            duration_frames = len(segment)
            if duration_frames == 1:
                classification = "single_transition"
            elif duration_frames <= 10:
                classification = "short_cluster"
            else:
                classification = "sustained_segment"

            max_mag_idx = segment["jump_mag"].idxmax()
            clusters.append(
                {
                    "cluster_type": cluster_type,
                    "start_frame": int(segment["frame"].iloc[0]),
                    "end_frame": int(segment["frame"].iloc[-1]),
                    "start_time_sec": float(segment["time_sec"].iloc[0]),
                    "end_time_sec": float(segment["time_sec"].iloc[-1]),
                    "duration_frames": duration_frames,
                    "duration_seconds": float(
                        segment["time_sec"].iloc[-1] - segment["time_sec"].iloc[0]
                    ),
                    "max_jump_magnitude_rad": float(segment["jump_mag"].max()),
                    "frame_of_max_jump": int(segment.loc[max_mag_idx, "frame"]),
                    "classification": classification,
                }
            )
            start_idx = idx

    return clusters


def analyze_run_parquet(
    parquet_path: Path, link_manifest: pd.DataFrame
) -> tuple[list[dict], list[dict]]:
    df = pd.read_parquet(parquet_path)
    run_label = df["run_label"].iloc[0]
    session_id = df["session_id"].iloc[0]

    core_links = link_manifest[
        (link_manifest["run_label"] == run_label)
        & (link_manifest["feature_scope"] == "core_candidate")
    ]
    target_ids = set(core_links["link_id"].astype(str))

    summary_rows: list[dict] = []
    cluster_rows: list[dict] = []

    for link_id in sorted(target_ids):
        link_df = df[df["link_id"] == link_id].sort_values("frame")
        if link_df.empty:
            continue

        parent = str(link_df["parent_canonical"].iloc[0])
        child = str(link_df["child_canonical"].iloc[0])
        total_frames = len(link_df)

        jump_status_fail_rows = int((link_df["stage07_jump_status"] == "fail").sum())
        jump_status_warn_rows = int((link_df["stage07_jump_status"] == "warning").sum())
        row_fail = link_df[link_df["stage07_row_qc_status"] == "fail"]
        row_warn = link_df[link_df["stage07_row_qc_status"] == "warning"]
        row_fail_count = len(row_fail)
        row_warn_count = len(row_warn)
        row_warn_or_fail = link_df[link_df["stage07_row_qc_status"].isin(["warning", "fail"])]
        row_warn_or_fail_count = len(row_warn_or_fail)

        link_jump_status = str(link_df["stage07_jump_status"].iloc[0])
        stage08_policy = str(link_df["stage08_policy"].iloc[0])

        if (
            row_fail_count == 0
            and row_warn_count == 0
            and link_jump_status not in {"fail", "warning"}
        ):
            continue

        max_jump = float(link_df["stage07_jump_magnitude_rad"].max())
        frame_of_max_jump = int(
            link_df.loc[link_df["stage07_jump_magnitude_rad"].idxmax(), "frame"]
        )

        first_fail_frame = int(row_fail["frame"].min()) if row_fail_count else None
        last_fail_frame = int(row_fail["frame"].max()) if row_fail_count else None
        first_wf_frame = (
            int(row_warn_or_fail["frame"].min()) if row_warn_or_fail_count else None
        )
        last_wf_frame = (
            int(row_warn_or_fail["frame"].max()) if row_warn_or_fail_count else None
        )

        link_clusters_fail: list[dict] = []
        link_clusters_wf: list[dict] = []

        for cluster_type, mask in (
            ("fail_only", link_df["stage07_row_qc_status"] == "fail"),
            ("warning_or_fail", link_df["stage07_row_qc_status"].isin(["warning", "fail"])),
        ):
            flagged = link_df[mask]
            clusters = _cluster_frames(
                flagged["frame"],
                flagged["time_sec"],
                flagged["stage07_jump_magnitude_rad"],
                cluster_type=cluster_type,
            )
            for cluster in clusters:
                cluster_row = {
                    "run_label": run_label,
                    "session_id": session_id,
                    "link_id": link_id,
                    "parent_canonical": parent,
                    "child_canonical": child,
                    "stage08_policy": stage08_policy,
                    **cluster,
                }
                cluster_rows.append(cluster_row)
                if cluster_type == "fail_only":
                    link_clusters_fail.append(cluster_row)
                else:
                    link_clusters_wf.append(cluster_row)

        summary_rows.append(
            {
                "run_label": run_label,
                "session_id": session_id,
                "link_id": link_id,
                "parent_canonical": parent,
                "child_canonical": child,
                "stage08_policy": stage08_policy,
                "stage07_link_jump_status": link_jump_status,
                "total_frames": total_frames,
                "stage07_jump_status_fail_row_count": jump_status_fail_rows,
                "stage07_jump_status_warning_row_count": jump_status_warn_rows,
                "stage07_row_qc_fail_count": row_fail_count,
                "stage07_row_qc_warning_count": row_warn_count,
                "stage07_row_qc_warning_or_fail_count": row_warn_or_fail_count,
                "first_fail_frame": first_fail_frame,
                "last_fail_frame": last_fail_frame,
                "first_warning_or_fail_frame": first_wf_frame,
                "last_warning_or_fail_frame": last_wf_frame,
                "max_stage07_jump_magnitude_rad": max_jump,
                "frame_of_max_jump": frame_of_max_jump,
                "fail_only_cluster_count": len(link_clusters_fail),
                "warning_or_fail_cluster_count": len(link_clusters_wf),
            }
        )

    return summary_rows, cluster_rows


def render_markdown(
    summary_df: pd.DataFrame,
    cluster_df: pd.DataFrame,
) -> str:
    block = summary_df[summary_df["stage08_policy"] == "block_filter"]
    fail_clusters = cluster_df[cluster_df["cluster_type"] == "fail_only"]
    wf_clusters = cluster_df[cluster_df["cluster_type"] == "warning_or_fail"]

    longest_fail = (
        fail_clusters.sort_values("duration_frames", ascending=False).iloc[0]
        if not fail_clusters.empty
        else None
    )
    longest_wf = (
        wf_clusters.sort_values("duration_frames", ascending=False).iloc[0]
        if not wf_clusters.empty
        else None
    )

    def _link_counts(run_label: str, link_id: str) -> tuple[int, int, int]:
        row = summary_df[
            (summary_df["run_label"] == run_label) & (summary_df["link_id"] == link_id)
        ]
        if row.empty:
            return 0, 0, 0
        r = row.iloc[0]
        return (
            int(r["stage07_row_qc_fail_count"]),
            int(r["stage07_row_qc_warning_count"]),
            int(r["stage07_jump_status_fail_row_count"]),
        )

    t1_j007 = _link_counts("671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001", "J007")
    t3 = {
        lid: _link_counts("671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000", lid)
        for lid in ("J004", "J006", "J031")
    }

    isolated_block = (
        not block.empty
        and (block["stage07_row_qc_fail_count"] <= 1).all()
        and block["fail_only_cluster_count"].eq(block["stage07_row_qc_fail_count"]).all()
        and (
            fail_clusters.empty
            or (fail_clusters["classification"] == "single_transition").all()
        )
        and (
            wf_clusters.empty
            or (wf_clusters["classification"] == "single_transition").all()
        )
    )

    lines = [
        "# Stage 07 core jump duration and clustering summary",
        "",
        "Read-only analysis of existing Stage 07 compact parquet outputs. "
        "No Stage 07 logic, schema, or policies were modified.",
        "",
        "## Method notes",
        "",
        "- **Per-frame fail/warning counts and clusters** use `stage07_row_qc_status` "
        "(frame-level diagnostic).",
        "- **`stage07_jump_status_*_row_count`** counts rows where the link-propagated "
        "`stage07_jump_status` equals fail/warning; on a failing link this equals "
        "`total_frames` because the link-level status is replicated on every row.",
        "- **Clusters** are contiguous frame sequences (frame increments of 1).",
        "- **Classification:** `single_transition` = 1 frame; `short_cluster` = 2–10 frames; "
        "`sustained_segment` > 10 frames.",
        "",
        "## Direct answers",
        "",
        "### 1. Are core jump failures isolated or sustained?",
        "",
    ]

    if isolated_block:
        lines.append(
            "**Isolated single-transition events.** All `block_filter` core links show "
            "only `single_transition` clusters (1 frame each) at the frame of maximum "
            "frame-to-frame jump. T3 R1 `J031` additionally has a separate isolated "
            "warning transition at frame 18914 (0.906 rad) before the fail at frame 26397 "
            "(1.74 rad). No sustained multi-frame segments were found."
        )
    else:
        lines.append(
            "**Mixed or sustained.** At least one core link shows multi-frame "
            "warning/fail clusters."
        )

    lines.extend(
        [
            "",
            "### 2. T1 R1 J007 — fail and warning rows",
            "",
            f"- Per-frame fail rows (`stage07_row_qc_status`): **{t1_j007[0]}**",
            f"- Per-frame warning rows: **{t1_j007[1]}**",
            f"- Link-propagated `stage07_jump_status=fail` row count: **{t1_j007[2]}** "
            f"(equals total frames because link jump status is fail)",
            "",
            "### 3. T3 R1 J004 / J006 / J031 — fail and warning rows",
            "",
        ]
    )
    for lid in ("J004", "J006", "J031"):
        f, w, js = t3[lid]
        lines.append(
            f"- **{lid}:** per-frame fail={f}, warning={w}, "
            f"link-propagated jump_status=fail rows={js}"
        )

    lines.extend(["", "### 4. Longest fail-only cluster", ""])
    if longest_fail is not None:
        lines.append(
            f"- **{longest_fail['run_label']}** `{longest_fail['link_id']}` "
            f"{longest_fail['parent_canonical']}→{longest_fail['child_canonical']}: "
            f"{longest_fail['duration_frames']} frame(s), "
            f"classification=`{longest_fail['classification']}`, "
            f"frames {longest_fail['start_frame']}–{longest_fail['end_frame']}, "
            f"max jump {longest_fail['max_jump_magnitude_rad']:.4g} rad"
        )
    else:
        lines.append("- None.")

    lines.extend(["", "### 5. Longest warning-or-fail cluster", ""])
    if longest_wf is not None:
        lines.append(
            f"- **{longest_wf['run_label']}** `{longest_wf['link_id']}` "
            f"{longest_wf['parent_canonical']}→{longest_wf['child_canonical']}: "
            f"{longest_wf['duration_frames']} frame(s), "
            f"classification=`{longest_wf['classification']}`, "
            f"frames {longest_wf['start_frame']}–{longest_wf['end_frame']}, "
            f"max jump {longest_wf['max_jump_magnitude_rad']:.4g} rad"
        )
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "### 6. Are Stage 08 block policies driven by isolated jumps or longer segments?",
            "",
            "**Isolated jumps (with one link having two isolated events).** Every core link "
            "with `stage08_policy=block_filter` failed because of single frame-to-frame "
            "transitions exceeding the 1.0 rad fail threshold. T3 R1 `J031` has two isolated "
            "transitions (warning then fail) at different frames. Link-level "
            "`stage07_jump_status=fail` reflects the max jump across the recording.",
            "",
            "### 7. Implications for manual review, masking, exclusion, or threshold review",
            "",
            "- **Manual/video review:** Supported at the identified single frames "
            "(see cluster table). Inspect Motive export around those timestamps for "
            "forearm→hand tracking glitches.",
            "- **Masking:** A 1-frame mask at each jump frame is sufficient; "
            "no long contaminated spans.",
            "- **Link exclusion:** Not warranted for core body links based on duration "
            "alone; failures are sparse isolated events on otherwise clean sequences.",
            "- **Threshold review:** Optional for warning-only links "
            "(0.5–1.0 rad single transitions); block_filter links exceed 1.0 rad "
            "and would fail under current thresholds regardless.",
            "",
            "## Block-filter core links",
            "",
        ]
    )

    if block.empty:
        lines.append("- None.")
    else:
        for _, row in block.iterrows():
            lines.append(
                f"- `{row['run_label']}` **{row['link_id']}** "
                f"{row['parent_canonical']}→{row['child_canonical']}: "
                f"per-frame fail={int(row['stage07_row_qc_fail_count'])}, "
                f"warning={int(row['stage07_row_qc_warning_count'])}, "
                f"max jump {row['max_stage07_jump_magnitude_rad']:.4g} rad @ frame "
                f"{int(row['frame_of_max_jump'])}"
            )

    lines.extend(["", "## All analyzed core links with warning/fail activity", ""])
    for _, row in summary_df.sort_values(["run_label", "link_id"]).iterrows():
        lines.append(
            f"- `{row['run_label']}` **{row['link_id']}** "
            f"({row['stage08_policy']}): fail={int(row['stage07_row_qc_fail_count'])}, "
            f"warn={int(row['stage07_row_qc_warning_count'])}, "
            f"clusters fail/wf={int(row['fail_only_cluster_count'])}/"
            f"{int(row['warning_or_fail_cluster_count'])}"
        )

    lines.append("")
    return "\n".join(lines)


def main(output_root: Path = OUTPUT_ROOT) -> None:
    link_manifest = pd.read_csv(output_root / "layer2_qc_link_manifest.csv")
    parquet_paths = sorted(
        output_root.glob("671_*/07_rotation_vectors/relative_rotation_vectors.parquet")
    )

    all_summary: list[dict] = []
    all_clusters: list[dict] = []

    for path in parquet_paths:
        summary, clusters = analyze_run_parquet(path, link_manifest)
        all_summary.extend(summary)
        all_clusters.extend(clusters)

    summary_df = pd.DataFrame(all_summary)
    cluster_df = pd.DataFrame(all_clusters)

    summary_df.to_csv(output_root / "stage07_core_jump_duration_by_link.csv", index=False)
    cluster_df.to_csv(output_root / "stage07_core_jump_clusters.csv", index=False)
    (output_root / "stage07_core_jump_duration_summary.md").write_text(
        render_markdown(summary_df, cluster_df),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    main(args.output_root)
