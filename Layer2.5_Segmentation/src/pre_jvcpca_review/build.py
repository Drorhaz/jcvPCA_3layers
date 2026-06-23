"""Orchestrate pre-JcvPCA review table generation."""

from __future__ import annotations

from pathlib import Path

from pre_jvcpca_review.discovery import resolve_layer1, resolve_layer2
from pre_jvcpca_review.events import (
    collect_all_raw_events,
    collect_marker_regions,
    event_marker_names,
    events_in_window,
    filter_events_for_selected_links,
    filter_labeled_events,
)
from pre_jvcpca_review.load_layer1 import load_layer1_manifest, load_qc_mask
from pre_jvcpca_review.load_layer2 import (
    load_link_manifest,
    load_rotvecs_window_full,
    load_session_summary,
)
from pre_jvcpca_review.mapping import (
    build_mapping_table,
    filter_mapping_by_selected_links,
    mapping_by_raw,
    parse_datadescriptions,
)
from pre_jvcpca_review.review_output import (
    datadescriptions_meta,
    infer_mapping_mode,
    unmapped_link_ids,
)
from pre_jvcpca_review.tables import write_mapping_table, write_review_tables
from pre_jvcpca_review.warnings import SEVERITY_INFO, SEVERITY_WARNING, WarningCollector

_REVIEW_ROTVEC_COLUMNS = [
    "frame",
    "link_id",
    "stage07_jump_status",
    "stage07_jump_magnitude_rad",
    "stage08_filter_status",
    "stage08_mask_reason",
    "stage08_analysis_eligible",
    "rx_filtered_analysis",
    "ry_filtered_analysis",
    "rz_filtered_analysis",
]


def _validate_frame_window(frame_start: int, frame_end: int, n_frames: int) -> None:
    if frame_start < 0 or frame_end < frame_start:
        raise ValueError(f"Invalid frame window: {frame_start}..{frame_end}")
    if frame_end >= n_frames:
        raise ValueError(f"frame_end {frame_end} exceeds session n_frames {n_frames - 1}")


def _collect_review_warnings(
    layer1_paths,
    datadescriptions_path: Path | None,
    dd_meta: dict[str, object],
    selected_qc_types: set[str],
) -> WarningCollector:
    collector = WarningCollector()
    if datadescriptions_path and not dd_meta["datadescriptions_found"]:
        collector.emit(
            "datadescriptions.missing",
            SEVERITY_WARNING,
            "mapping",
            f"DataDescriptions file not found: {datadescriptions_path}",
            recommended_action="Provide a valid DataDescriptions CSV or continue with heuristic mapping only.",
        )
    if not dd_meta["datadescriptions_found"]:
        collector.emit(
            "datadescriptions.not_used",
            SEVERITY_INFO,
            "mapping",
            "Review mapping uses heuristic / Layer 1 marker inventory only (no DataDescriptions).",
            recommended_action="Optional: point DataDesc to a session DataDescriptions CSV.",
        )
    if "gap_0p5" in selected_qc_types and layer1_paths.gaps_over_0p5s is None:
        collector.emit(
            "layer1.gap_0p5_missing",
            SEVERITY_WARNING,
            "layer1_evidence",
            "Layer 1 gaps_over_0p5s.csv not found; gap ≥ 0.5 s evidence unavailable.",
            recommended_action="Re-run Layer 1 QC or deselect gap ≥ 0.5 s evidence.",
            source_layer="layer1",
        )
    if "gap_0p2" in selected_qc_types and layer1_paths.gaps_over_0p2s is None:
        collector.emit(
            "layer1.gap_0p2_missing",
            SEVERITY_WARNING,
            "layer1_evidence",
            "Layer 1 gaps_over_0p2s.csv not found; gap ≥ 0.2 s evidence unavailable.",
            recommended_action="Re-run Layer 1 QC or deselect gap ≥ 0.2 s evidence.",
            source_layer="layer1",
        )
    if selected_qc_types & {"artifact_sigma", "segment_swap"} and layer1_paths.artifact_events is None:
        collector.emit(
            "layer1.artifact_events_missing",
            SEVERITY_WARNING,
            "layer1_evidence",
            "Layer 1 artifact_events.csv not found; artifact / segment-swap evidence unavailable.",
            recommended_action="Re-run Layer 1 QC or deselect artifact evidence types.",
            source_layer="layer1",
        )
    return collector


def build_mapping_only(
    layer1_dir: Path,
    layer2_dir: Path,
    out_dir: Path,
    datadescriptions: Path | None = None,
    selected_link_ids: list[str] | None = None,
) -> Path:
    layer1_paths = resolve_layer1(layer1_dir)
    layer2_paths = resolve_layer2(layer2_dir)
    l1 = load_layer1_manifest(layer1_paths.manifest)
    links = load_link_manifest(layer2_paths.link_manifest)
    dd = parse_datadescriptions(datadescriptions)
    dd_meta = datadescriptions_meta(datadescriptions)

    raw_events = collect_all_raw_events(layer1_paths, l1.fps)
    labeled = filter_labeled_events(raw_events, dd)
    regions = collect_marker_regions(layer1_paths)
    entries = build_mapping_table(dd, links, event_marker_names(labeled), regions)
    if selected_link_ids:
        entries = filter_mapping_by_selected_links(entries, selected_link_ids)

    out_dir.mkdir(parents=True, exist_ok=True)
    mapping_path = write_mapping_table(entries, out_dir)
    collector = _collect_review_warnings(layer1_paths, datadescriptions, dd_meta, set())
    warnings_df = collector.to_dataframe()
    if not warnings_df.empty:
        warnings_df.to_csv(out_dir / "window_warnings.csv", index=False)
    return mapping_path


def build_full_review(
    layer1_dir: Path,
    layer2_dir: Path,
    out_dir: Path,
    frame_start: int,
    frame_end: int,
    selected_link_ids: list[str],
    qc_evidence: list[str],
    datadescriptions: Path | None = None,
    joint_selection_preset: str | None = None,
) -> dict[str, Path]:
    layer1_paths = resolve_layer1(layer1_dir)
    layer2_paths = resolve_layer2(layer2_dir)
    l1 = load_layer1_manifest(layer1_paths.manifest)
    l2 = load_session_summary(layer2_paths.session_summary)
    links = load_link_manifest(layer2_paths.link_manifest)
    link_by_id = {link.link_id: link for link in links}

    _validate_frame_window(frame_start, frame_end, l1.n_frames)
    if not selected_link_ids:
        raise ValueError("At least one selected link is required for full review")

    unknown = [lid for lid in selected_link_ids if lid not in link_by_id]
    if unknown:
        raise ValueError(f"Unknown link IDs: {', '.join(unknown)}")

    selected_qc = set(qc_evidence)
    dd = parse_datadescriptions(datadescriptions)
    dd_meta = datadescriptions_meta(datadescriptions)
    raw_events = collect_all_raw_events(layer1_paths, l1.fps)
    labeled = filter_labeled_events(raw_events, dd)
    regions = collect_marker_regions(layer1_paths)
    mapping_entries = build_mapping_table(dd, links, event_marker_names(labeled), regions)
    full_lookup = mapping_by_raw(mapping_entries)
    mapping_entries = filter_mapping_by_selected_links(mapping_entries, selected_link_ids)
    window_events = events_in_window(labeled, frame_start, frame_end, selected_qc)
    window_events = filter_events_for_selected_links(
        window_events, full_lookup, selected_link_ids
    )
    selected_links = [link_by_id[lid] for lid in selected_link_ids]
    qc_window = load_qc_mask(layer1_paths.qc_mask, frame_start, frame_end)
    rotvecs = load_rotvecs_window_full(
        layer2_paths.rotvecs_parquet,
        selected_link_ids,
        frame_start,
        frame_end,
        columns=_REVIEW_ROTVEC_COLUMNS,
    )

    mapping_mode = infer_mapping_mode(bool(dd_meta["datadescriptions_used"]), mapping_entries)
    unmapped_links = unmapped_link_ids(mapping_entries, selected_link_ids)
    collector = _collect_review_warnings(layer1_paths, datadescriptions, dd_meta, selected_qc)
    mapping_warnings: list[str] = []
    if unmapped_links:
        msg = f"Selected links without mapped marker evidence: {', '.join(unmapped_links)}"
        mapping_warnings.append(msg)
        collector.emit(
            "mapping.unmapped_selected_links",
            SEVERITY_WARNING,
            "mapping",
            msg,
            recommended_action="Inspect mapping_logic_table.csv or adjust joint selection.",
        )

    return write_review_tables(
        out_dir=out_dir,
        mapping_entries=mapping_entries,
        events=window_events,
        selected_links=selected_links,
        all_links=links,
        rotvecs=rotvecs,
        l2_session=l2,
        frame_start=frame_start,
        frame_end=frame_end,
        fps=l1.fps,
        selected_qc_types=selected_qc,
        joint_selection_preset=joint_selection_preset,
        qc_window=qc_window,
        datadescriptions_meta=dd_meta,
        mapping_mode=mapping_mode,
        unmapped_link_ids=unmapped_links,
        mapping_warnings=mapping_warnings,
        review_warnings=collector.to_dataframe(),
    )
