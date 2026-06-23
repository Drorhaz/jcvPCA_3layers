"""Assemble and write spec output CSV tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pre_jvcpca_review.events import NormalizedEvent, event_relates_to_link
from pre_jvcpca_review.layer2_flags import block_filter_mask, frame_percent, jump_fail_rad_mask, problem_notes
from pre_jvcpca_review.load_layer1 import flagged_frame_percent
from pre_jvcpca_review.load_layer2 import Layer2Session, LinkRecord
from pre_jvcpca_review.mapping import MappingEntry, link_joint_family, mapping_by_raw
from pre_jvcpca_review.schemas import (
    LINK_JOINT_REVIEW_COLUMNS,
    MAPPING_LOGIC_COLUMNS,
    QC_EVENT_REVIEW_COLUMNS,
    QC_EVIDENCE_SUMMARY_COLUMNS,
    QC_TYPES,
    WINDOW_DECISION_SUMMARY_COLUMNS,
)


def _write_df(df: pd.DataFrame, path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    df[columns].to_csv(path, index=False)


def mapping_logic_dataframe(entries: list[MappingEntry]) -> pd.DataFrame:
    rows = [
        {
            "raw_marker_or_region": e.raw_marker_or_region,
            "normalized_marker_or_region": e.normalized_marker_or_region,
            "component_markers": e.component_markers,
            "attached_bone": e.attached_bone,
            "attached_bone_canonical": e.attached_bone_canonical,
            "marker_family": e.marker_family,
            "related_joint_family": e.related_joint_family,
            "candidate_layer2_links": e.candidate_layer2_links,
            "candidate_layer2_link_ids": e.candidate_layer2_link_ids,
            "mapping_source": e.mapping_source,
            "mapping_status": e.mapping_status,
            "candidate_mapping_level": e.candidate_mapping_level,
            "included_in_review": e.included_in_review,
            "review_note": e.review_note,
        }
        for e in entries
    ]
    return pd.DataFrame(rows)


def qc_evidence_summary_dataframe(
    events: list[NormalizedEvent],
    lookup: dict[str, MappingEntry],
    duration_frames: int,
    selected_qc_types: set[str],
) -> pd.DataFrame:
    rows = []
    for qc_type in QC_TYPES:
        if qc_type not in selected_qc_types:
            continue
        subset = [e for e in events if e.qc_type == qc_type]
        if not subset:
            continue
        markers = sorted({e.raw_marker_or_region for e in subset})
        families = sorted(
            {
                (lookup.get(m) or lookup.get(m.split(":", 1)[-1])).related_joint_family
                for m in markers
                if lookup.get(m) or lookup.get(m.split(":", 1)[-1])
            }
        )
        mapped = sum(
            1
            for m in markers
            if (lookup.get(m) or lookup.get(m.split(":", 1)[-1]))
            and (lookup.get(m) or lookup.get(m.split(":", 1)[-1])).mapping_status == "mapped"
        )
        unmapped = len(markers) - mapped
        total_dur = sum(e.duration_frames for e in subset)
        sources = sorted({e.source_file for e in subset})
        rows.append(
            {
                "qc_type": qc_type,
                "event_count": len(subset),
                "total_event_duration_frames": total_dur,
                "total_event_duration_percent_of_window": round(100.0 * total_dur / duration_frames, 2)
                if duration_frames
                else 0.0,
                "unique_marker_or_region_count": len(markers),
                "markers_or_regions": "; ".join(markers),
                "related_joint_families": "; ".join(families),
                "mapping_status_summary": f"mapped:{mapped}; unmapped:{unmapped}",
                "source_files": "; ".join(sources),
            }
        )
    return pd.DataFrame(rows)


def qc_event_review_dataframe(
    events: list[NormalizedEvent],
    lookup: dict[str, MappingEntry],
) -> pd.DataFrame:
    rows = []
    for event in events:
        entry = lookup.get(event.raw_marker_or_region)
        if entry is None:
            bare = event.raw_marker_or_region.split(":", 1)[-1]
            entry = lookup.get(bare) or lookup.get(f"671:{bare}")
        rows.append(
            {
                "frame_start": event.frame_start,
                "frame_end": event.frame_end,
                "duration_frames": event.duration_frames,
                "qc_type": event.qc_type,
                "reason": event.reason,
                "source_file": event.source_file,
                "raw_marker_or_region": event.raw_marker_or_region,
                "related_joint_family": entry.related_joint_family if entry else "unknown",
                "candidate_layer2_links": entry.candidate_layer2_links if entry else "",
                "candidate_mapping_level": entry.candidate_mapping_level if entry else "unmapped_unknown",
                "mapping_status": entry.mapping_status if entry else "unmapped",
                "included_in_review": True,
            }
        )
    return pd.DataFrame(rows)


def link_joint_review_dataframe(
    selected_links: list[LinkRecord],
    events: list[NormalizedEvent],
    lookup: dict[str, MappingEntry],
    rotvecs: pd.DataFrame,
    duration_frames: int,
) -> pd.DataFrame:
    rows = []
    for link in selected_links:
        link_events = {
            qc: [e for e in events if e.qc_type == qc and event_relates_to_link(e, link.link_id, lookup)]
            for qc in QC_TYPES
        }
        link_df = rotvecs[rotvecs["link_id"] == link.link_id]
        jump_mask = jump_fail_rad_mask(link_df, link)
        block_mask = block_filter_mask(link_df, link)
        jump_count = int(jump_mask.sum())
        block_count = int(block_mask.sum())

        related_markers = sorted(
            {
                e.raw_marker_or_region
                for e in events
                if event_relates_to_link(e, link.link_id, lookup)
            }
        )

        def regional_frames(qc: str) -> int:
            return sum(e.duration_frames for e in link_events[qc])

        def regional_percent(frames: int) -> float:
            return round(100.0 * frames / duration_frames, 2) if duration_frames else 0.0

        rows.append(
            {
                "link_id": link.link_id,
                "link_or_joint": link.display_name,
                "joint_family": link_joint_family(link),
                "l1_regional_gap_0p5_event_frames": regional_frames("gap_0p5"),
                "l1_regional_gap_0p5_event_percent": regional_percent(regional_frames("gap_0p5")),
                "l1_regional_gap_0p2_event_frames": regional_frames("gap_0p2"),
                "l1_regional_gap_0p2_event_percent": regional_percent(regional_frames("gap_0p2")),
                "l1_regional_artifact_sigma_event_frames": regional_frames("artifact_sigma"),
                "l1_regional_artifact_sigma_event_percent": regional_percent(
                    regional_frames("artifact_sigma")
                ),
                "l1_regional_segment_swap_event_frames": regional_frames("segment_swap"),
                "l1_regional_segment_swap_event_percent": regional_percent(
                    regional_frames("segment_swap")
                ),
                "layer2_ineligible_jump_fail_rad_frame_percent": frame_percent(jump_mask, duration_frames),
                "layer2_ineligible_block_filter_frame_percent": frame_percent(block_mask, duration_frames),
                "mapped_qc_marker_names_related_to_link": "; ".join(related_markers),
                "layer2_problem_notes": problem_notes(jump_count, block_count, duration_frames, link),
            }
        )
    return pd.DataFrame(rows)


def window_decision_summary_dataframe(
    l2_session: Layer2Session,
    frame_start: int,
    frame_end: int,
    duration_frames: int,
    fps: float,
    selected_qc_types: set[str],
    joint_selection_preset: str | None,
    selected_links: list[LinkRecord],
    mapping_entries: list[MappingEntry],
    datadescriptions_used: bool,
    events: list[NormalizedEvent],
    qc_window: pd.DataFrame,
    link_review: pd.DataFrame,
    all_links_count: int,
) -> pd.DataFrame:
    mapped = sum(1 for e in mapping_entries if e.mapping_status == "mapped")
    unmapped_names = [
        e.raw_marker_or_region for e in mapping_entries if e.mapping_status == "unmapped"
    ]
    source_parts = []
    if datadescriptions_used:
        source_parts.append("DataDescriptions")
    source_parts.append("Layer1 event files")

    mapping_summary_parts = [
        f"{mapped} datadescriptions-mapped" if datadescriptions_used else f"{mapped} mapped"
    ]
    if unmapped_names:
        mapping_summary_parts.append(f"{len(unmapped_names)} unmapped")
    else:
        mapping_summary_parts[-1] += "; 0 unmapped"

    jump_parts = []
    block_parts = []
    for _, row in link_review.iterrows():
        label = f"{row['link_id']} {row['link_or_joint']}"
        jump_parts.append(f"{label}: {row['layer2_ineligible_jump_fail_rad_frame_percent']}%")
        block_parts.append(f"{label}: {row['layer2_ineligible_block_filter_frame_percent']}%")

    def count_qc(qc: str) -> int:
        return sum(1 for e in events if e.qc_type == qc)

    row = {
        "session_id": l2_session.session_id,
        "run_label": l2_session.run_label,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "duration_frames": duration_frames,
        "duration_sec": round(duration_frames / fps, 2),
        "selected_qc_evidence_types": "; ".join(sorted(selected_qc_types)),
        "joint_selection_preset": joint_selection_preset or "",
        "selected_layer2_links": "; ".join(link.display_name for link in selected_links),
        "selected_layer2_link_ids": "; ".join(link.link_id for link in selected_links),
        "layer1_labeled_marker_source": " + ".join(source_parts),
        "layer1_total_labeled_markers": len(mapping_entries),
        "layer1_mapped_labeled_markers": mapped,
        "layer1_unmapped_labeled_marker_names": "; ".join(unmapped_names),
        "unlabeled_marker_policy": "excluded_from_main_review",
        "layer2_total_links_available": all_links_count,
        "layer2_selected_links_count": len(selected_links),
        "datadescriptions_used": datadescriptions_used,
        "mapping_source_summary": "; ".join(mapping_summary_parts),
        "n_gap_0p5_events": count_qc("gap_0p5"),
        "n_gap_0p2_events": count_qc("gap_0p2"),
        "n_artifact_sigma_events": count_qc("artifact_sigma"),
        "n_segment_swap_events": count_qc("segment_swap"),
        "gap_0p5_flagged_frame_percent": flagged_frame_percent(qc_window, "flag_gap_0p5", duration_frames),
        "gap_0p2_flagged_frame_percent": flagged_frame_percent(qc_window, "flag_gap_0p2", duration_frames),
        "artifact_sigma_flagged_frame_percent": flagged_frame_percent(
            qc_window, "flag_artifact_sigma", duration_frames
        ),
        "segment_swap_flagged_frame_percent": flagged_frame_percent(
            qc_window, "flag_segment_swap", duration_frames
        ),
        "jump_fail_rad_links_frame_percent": "; ".join(jump_parts),
        "block_filter_links_frame_percent": "; ".join(block_parts),
    }
    return pd.DataFrame([row])


def write_mapping_table(entries: list[MappingEntry], out_dir: Path) -> Path:
    path = out_dir / "mapping_logic_table.csv"
    _write_df(mapping_logic_dataframe(entries), path, MAPPING_LOGIC_COLUMNS)
    return path


def write_review_tables(
    out_dir: Path,
    mapping_entries: list[MappingEntry],
    events: list[NormalizedEvent],
    selected_links: list[LinkRecord],
    all_links: list[LinkRecord],
    rotvecs: pd.DataFrame,
    l2_session: Layer2Session,
    frame_start: int,
    frame_end: int,
    fps: float,
    selected_qc_types: set[str],
    joint_selection_preset: str | None,
    qc_window: pd.DataFrame,
    datadescriptions_used: bool,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    lookup = mapping_by_raw(mapping_entries)
    duration_frames = frame_end - frame_start + 1

    link_review = link_joint_review_dataframe(
        selected_links, events, lookup, rotvecs, duration_frames
    )
    summary = window_decision_summary_dataframe(
        l2_session,
        frame_start,
        frame_end,
        duration_frames,
        fps,
        selected_qc_types,
        joint_selection_preset,
        selected_links,
        mapping_entries,
        datadescriptions_used,
        events,
        qc_window,
        link_review,
        all_links_count=len(all_links),
    )
    paths = {
        "mapping_logic_table.csv": write_mapping_table(mapping_entries, out_dir),
        "window_decision_summary.csv": out_dir / "window_decision_summary.csv",
        "qc_evidence_summary_table.csv": out_dir / "qc_evidence_summary_table.csv",
        "link_joint_review_table.csv": out_dir / "link_joint_review_table.csv",
        "qc_event_review_table.csv": out_dir / "qc_event_review_table.csv",
    }
    _write_df(summary, paths["window_decision_summary.csv"], WINDOW_DECISION_SUMMARY_COLUMNS)
    _write_df(
        qc_evidence_summary_dataframe(events, lookup, duration_frames, selected_qc_types),
        paths["qc_evidence_summary_table.csv"],
        QC_EVIDENCE_SUMMARY_COLUMNS,
    )
    _write_df(link_review, paths["link_joint_review_table.csv"], LINK_JOINT_REVIEW_COLUMNS)
    _write_df(
        qc_event_review_dataframe(events, lookup),
        paths["qc_event_review_table.csv"],
        QC_EVENT_REVIEW_COLUMNS,
    )
    return paths
