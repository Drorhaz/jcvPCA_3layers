"""Normalize Layer 1 QC events for review tables."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from pre_jvcpca_review.discovery import Layer1Paths
from pre_jvcpca_review.load_layer1 import load_layer1_artifact_events, load_layer1_gap_summary
from pre_jvcpca_review.mapping import DataDescriptions, MappingEntry, is_labeled_marker, mapping_by_raw


@dataclass(frozen=True)
class NormalizedEvent:
    frame_start: int
    frame_end: int
    duration_frames: int
    qc_type: str
    reason: str
    source_file: str
    raw_marker_or_region: str


def _parse_gap_intervals(text: str, fps: float) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    if not isinstance(text, str) or not text.strip():
        return intervals
    for token in text.split(";"):
        token = token.strip()
        if not token:
            continue
        match = re.match(r"([\d.]+)\s*-\s*([\d.]+)", token)
        if not match:
            continue
        start_s, end_s = float(match.group(1)), float(match.group(2))
        start_f = int(round(start_s * fps))
        end_f = int(round(end_s * fps))
        if end_f < start_f:
            start_f, end_f = end_f, start_f
        intervals.append((start_f, end_f))
    return intervals


def _clip_event(start: int, end: int, frame_start: int, frame_end: int) -> tuple[int, int] | None:
    s = max(start, frame_start)
    e = min(end, frame_end)
    if e < s:
        return None
    return s, e


def expand_gap_events(path: Path, qc_type: str, fps: float) -> list[NormalizedEvent]:
    df = load_layer1_gap_summary(path)
    events: list[NormalizedEvent] = []
    for _, row in df.iterrows():
        marker = str(row["marker_name"])
        for start_f, end_f in _parse_gap_intervals(str(row.get("gap_intervals_s", "")), fps):
            events.append(
                NormalizedEvent(
                    frame_start=start_f,
                    frame_end=end_f,
                    duration_frames=end_f - start_f + 1,
                    qc_type=qc_type,
                    reason="marker_gap",
                    source_file=path.name,
                    raw_marker_or_region=marker,
                )
            )
    return events


def load_artifact_events(path: Path) -> list[NormalizedEvent]:
    df = load_layer1_artifact_events(path)
    events: list[NormalizedEvent] = []
    for _, row in df.iterrows():
        method = str(row["method"])
        if method == "velocity_mad":
            qc_type, reason = "artifact_sigma", "velocity_mad"
        elif method == "segment_length_violation":
            qc_type, reason = "segment_swap", "segment_length_violation"
        else:
            continue
        events.append(
            NormalizedEvent(
                frame_start=int(row["start_frame"]),
                frame_end=int(row["end_frame"]),
                duration_frames=int(row["duration_frames"]),
                qc_type=qc_type,
                reason=reason,
                source_file=path.name,
                raw_marker_or_region=str(row["marker_name"]),
            )
        )
    return events


def collect_all_raw_events(layer1: Layer1Paths, fps: float) -> list[NormalizedEvent]:
    events: list[NormalizedEvent] = []
    if layer1.gaps_over_0p5s:
        events.extend(expand_gap_events(layer1.gaps_over_0p5s, "gap_0p5", fps))
    if layer1.gaps_over_0p2s:
        events.extend(expand_gap_events(layer1.gaps_over_0p2s, "gap_0p2", fps))
    if layer1.artifact_events:
        events.extend(load_artifact_events(layer1.artifact_events))
    return events


def collect_marker_regions(layer1: Layer1Paths) -> dict[str, str]:
    regions: dict[str, str] = {}
    for path, _ in (
        (layer1.gaps_over_0p2s, None),
        (layer1.gaps_over_0p5s, None),
        (layer1.artifact_events, None),
    ):
        if path is None:
            continue
        df = pd.read_csv(path)
        col = "marker_name" if "marker_name" in df.columns else "affected_markers"
        region_col = "body_region_group"
        for _, row in df.iterrows():
            marker = str(row[col])
            region = str(row.get(region_col, ""))
            if region:
                regions[marker] = region
                regions[normalize_marker(marker)] = region
    return regions


def normalize_marker(name: str) -> str:
    return name.split(":", 1)[-1] if ":" in name else name


def filter_labeled_events(
    events: list[NormalizedEvent],
    dd: DataDescriptions | None,
) -> list[NormalizedEvent]:
    return [e for e in events if is_labeled_marker(e.raw_marker_or_region, dd)]


def events_in_window(
    events: list[NormalizedEvent],
    frame_start: int,
    frame_end: int,
    selected_qc_types: set[str],
) -> list[NormalizedEvent]:
    clipped: list[NormalizedEvent] = []
    for event in events:
        if event.qc_type not in selected_qc_types:
            continue
        bounds = _clip_event(event.frame_start, event.frame_end, frame_start, frame_end)
        if bounds is None:
            continue
        s, e = bounds
        clipped.append(
            NormalizedEvent(
                frame_start=s,
                frame_end=e,
                duration_frames=e - s + 1,
                qc_type=event.qc_type,
                reason=event.reason,
                source_file=event.source_file,
                raw_marker_or_region=event.raw_marker_or_region,
            )
        )
    return sorted(clipped, key=lambda ev: (ev.frame_start, ev.raw_marker_or_region))


def event_marker_names(events: list[NormalizedEvent]) -> set[str]:
    return {e.raw_marker_or_region for e in events}


def filter_events_for_selected_links(
    events: list[NormalizedEvent],
    lookup: dict[str, MappingEntry],
    selected_link_ids: list[str],
) -> list[NormalizedEvent]:
    """Keep QC events whose mapped candidate links overlap selected joints."""
    selected = set(selected_link_ids)
    if not selected:
        return events
    return [
        event
        for event in events
        if any(event_relates_to_link(event, link_id, lookup) for link_id in selected)
    ]


def event_relates_to_link(event: NormalizedEvent, link_id: str, lookup: dict[str, MappingEntry]) -> bool:
    entry = lookup.get(event.raw_marker_or_region)
    if entry is None:
        bare = normalize_marker(event.raw_marker_or_region)
        entry = lookup.get(bare) or lookup.get(f"671:{bare}")
    if entry is None:
        return False
    return link_id in entry.candidate_link_ids
