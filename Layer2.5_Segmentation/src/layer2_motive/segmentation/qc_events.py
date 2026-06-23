"""Normalize Layer 1 QC artifacts into a common event schema."""

from __future__ import annotations

import pandas as pd

from layer2_motive.segmentation.marker_family import MarkerFamilyMapper
from layer2_motive.segmentation.schemas import (
    LAYER1_FLAG_QC_TYPES,
    LAYER1_NORMALIZED_EVENT_COLUMNS,
    Layer1Bundle,
)

INTERVAL_CRITERION_TO_QC_TYPE: dict[str, str] = {
    "gaps_over_0p5": "marker_gap_0p5",
    "gaps_over_0p2": "marker_gap_0p2",
    "artifact_sigma": "artifact_sigma",
    "segment_swap": "segment_swap",
    "edge_effect": "edge_effect",
}

MASK_FLAG_QC_TYPES = frozenset(INTERVAL_CRITERION_TO_QC_TYPE.values()) - {"edge_effect"}

ARTIFACT_METHOD_TO_QC_TYPE: dict[str, str] = {
    "velocity_mad": "artifact_sigma",
    "segment_length_violation": "segment_swap",
}

INTERVAL_CRITERIA_SUPERSEDED_BY_GAP_FILES = frozenset({"gaps_over_0p5", "gaps_over_0p2"})
INTERVAL_CRITERIA_SUPERSEDED_BY_ARTIFACT_FILE = frozenset({"artifact_sigma", "segment_swap"})
ARTIFACT_QC_TYPES = frozenset({"artifact_sigma", "segment_swap"})

# Base columns produced by normalization (before marker-family overlay)
LAYER1_BASE_EVENT_COLUMNS = tuple(
    c
    for c in LAYER1_NORMALIZED_EVENT_COLUMNS
    if c
    not in {
        "normalized_marker_name",
        "attached_bone",
        "attached_bone_canonical",
        "related_joint_family",
        "adjacent_joint_family",
        "mapping_source",
        "mapping_confidence",
        "template_mapping_status",
    }
)

_EMPTY_EVENTS = pd.DataFrame(columns=list(LAYER1_BASE_EVENT_COLUMNS))


def _empty_events() -> pd.DataFrame:
    return _EMPTY_EVENTS.copy()


def _coerce_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def looks_like_marker_name(value: object) -> bool:
    """Return True when text looks like a labeled marker or segment-pair id."""
    if value is None or pd.isna(value):
        return False
    text = str(value).strip()
    if not text or text == "unknown":
        return False
    if text.isdigit():
        return False
    if "-" in text:
        start, end = text.split("-", 1)
        if start.isdigit() and end.isdigit():
            return False
    return ":" in text or "__" in text


def parse_affected_markers(affected: object) -> list[str]:
    """Split semicolon-separated affected_markers into cleaned marker ids."""
    if affected is None or pd.isna(affected):
        return []
    return [part.strip() for part in str(affected).split(";") if part.strip()]


def interval_criterion_to_qc_type(criterion: object) -> str:
    if criterion is None or pd.isna(criterion) or not str(criterion).strip():
        return "interval_status"
    key = str(criterion).strip()
    return INTERVAL_CRITERION_TO_QC_TYPE.get(key, key)


def marker_identity_from_event_row(row: dict | pd.Series) -> str | None:
    """Prefer explicit marker_raw_name; ignore frame-only entity ids."""
    raw = row.get("marker_raw_name")
    if raw is not None and not pd.isna(raw) and str(raw).strip():
        return str(raw).strip()
    entity = row.get("entity_name")
    if looks_like_marker_name(entity):
        return str(entity).strip()
    return None


def _entity_type_for_marker(marker: str) -> str:
    return "segment_pair" if "__" in marker else "marker"


def _row_base(session_key: str, source_file: str) -> dict:
    return {
        "session_key": session_key,
        "source_layer": "layer1",
        "source_file": source_file,
        "qc_type": None,
        "severity": None,
        "frame": None,
        "start_frame": None,
        "end_frame": None,
        "time_sec": None,
        "start_time_sec": None,
        "end_time_sec": None,
        "duration_frames": None,
        "duration_seconds": None,
        "entity_type": None,
        "entity_name": None,
        "marker_raw_name": None,
        "body_region_group": None,
        "reason": None,
        "notes": None,
    }


def normalize_qc_mask_events(
    qc_mask: pd.DataFrame,
    session_key: str,
    *,
    frame_col: str = "frame",
    time_col: str = "time_s",
    source_file: str = "qc_mask.csv",
    frame_rate_hz: float = 120.0,
) -> pd.DataFrame:
    """Convert qc_mask frame rows into normalized events from boolean flag columns."""
    rows: list[dict] = []
    has_time = time_col in qc_mask.columns
    flag_cols = [c for c in LAYER1_FLAG_QC_TYPES if c in qc_mask.columns]

    for _, row in qc_mask.iterrows():
        frame = int(row[frame_col])
        time_sec = float(row[time_col]) if has_time else frame / frame_rate_hz
        reason = row.get("reason", "")
        reason_str = "" if pd.isna(reason) else str(reason)

        for flag_col in flag_cols:
            if not _coerce_bool(pd.Series([row[flag_col]])).iloc[0]:
                continue
            event = _row_base(session_key, source_file)
            event.update(
                {
                    "qc_type": LAYER1_FLAG_QC_TYPES[flag_col],
                    "severity": "flag",
                    "frame": frame,
                    "start_frame": frame,
                    "end_frame": frame,
                    "time_sec": time_sec,
                    "start_time_sec": time_sec,
                    "end_time_sec": time_sec,
                    "duration_frames": 1,
                    "duration_seconds": 1.0 / frame_rate_hz,
                    "entity_type": "frame",
                    "entity_name": str(frame),
                    "reason": reason_str or flag_col,
                    "notes": f"flag={flag_col}",
                }
            )
            rows.append(event)

    if not rows:
        return _empty_events()
    return pd.DataFrame(rows, columns=list(LAYER1_BASE_EVENT_COLUMNS))


def normalize_interval_events(
    intervals: pd.DataFrame,
    session_key: str,
    *,
    source_file: str = "qc_mask_intervals.csv",
    frame_rate_hz: float = 120.0,
) -> pd.DataFrame:
    """Normalize qc_mask_intervals into marker-attributed interval events."""
    rows: list[dict] = []
    for _, row in intervals.iterrows():
        start_frame = int(row["start_frame"])
        end_frame = int(row["end_frame"])
        duration_frames = int(end_frame - start_frame + 1)
        start_s = row.get("start_s")
        end_s = row.get("end_s")
        duration_s = row.get("duration_s")
        if pd.isna(start_s):
            start_s = start_frame / frame_rate_hz
        if pd.isna(end_s):
            end_s = end_frame / frame_rate_hz
        if pd.isna(duration_s):
            duration_s = duration_frames / frame_rate_hz

        status = str(row.get("status", "")).lower()
        reason = row.get("reason", "")
        criterion = row.get("criterion", "")
        affected = row.get("affected_markers", "")
        qc_type = interval_criterion_to_qc_type(criterion)
        markers = parse_affected_markers(affected)
        severity = str(criterion or reason or "interval").strip() or "interval"

        base = {
            "qc_type": qc_type,
            "severity": severity,
            "frame": start_frame,
            "start_frame": start_frame,
            "end_frame": end_frame,
            "time_sec": float(start_s),
            "start_time_sec": float(start_s),
            "end_time_sec": float(end_s),
            "duration_frames": duration_frames,
            "duration_seconds": float(duration_s),
            "reason": str(reason) if pd.notna(reason) else "",
            "notes": f"criterion={criterion}" if pd.notna(criterion) else "",
        }

        if markers:
            for marker in markers:
                event = _row_base(session_key, source_file)
                event.update(base)
                event.update(
                    {
                        "entity_type": _entity_type_for_marker(marker),
                        "entity_name": marker,
                        "marker_raw_name": marker,
                        "notes": (
                            f"affected_markers={affected}; marker={marker}"
                            if pd.notna(affected)
                            else f"marker={marker}"
                        ),
                    }
                )
                rows.append(event)
            continue

        event = _row_base(session_key, source_file)
        event.update(base)
        event.update(
            {
                "entity_type": "interval",
                "entity_name": f"{start_frame}-{end_frame}",
                "notes": f"affected_markers={affected}" if pd.notna(affected) else "",
            }
        )
        rows.append(event)

    if not rows:
        return _empty_events()
    return pd.DataFrame(rows, columns=list(LAYER1_BASE_EVENT_COLUMNS))


def parse_gap_intervals_s(gap_intervals: object) -> list[tuple[float, float]]:
    """Parse semicolon-separated second ranges like '131.80-132.50; 152.22-152.74'."""
    if gap_intervals is None or pd.isna(gap_intervals):
        return []
    ranges: list[tuple[float, float]] = []
    for chunk in str(gap_intervals).split(";"):
        text = chunk.strip()
        if not text or "-" not in text:
            continue
        start_text, end_text = text.split("-", 1)
        try:
            start_s = float(start_text.strip())
            end_s = float(end_text.strip())
        except ValueError:
            continue
        if end_s < start_s:
            start_s, end_s = end_s, start_s
        ranges.append((start_s, end_s))
    return ranges


def seconds_to_frame(time_s: float, frame_rate_hz: float) -> int:
    """Convert session time in seconds to the nearest frame index."""
    return int(round(float(time_s) * float(frame_rate_hz)))


def artifact_method_to_qc_type(method: object) -> str:
    if method is None or pd.isna(method):
        return "artifact_sigma"
    key = str(method).strip()
    return ARTIFACT_METHOD_TO_QC_TYPE.get(key, key)


def normalize_gap_summary_events(
    gaps_df: pd.DataFrame,
    session_key: str,
    *,
    qc_type: str,
    source_file: str,
    frame_rate_hz: float = 120.0,
) -> pd.DataFrame:
    """Normalize gaps_over_0p2s/gaps_over_0p5s into marker-attributed gap events."""
    rows: list[dict] = []
    for _, row in gaps_df.iterrows():
        marker = str(row.get("marker_name", "")).strip()
        if not marker:
            continue
        body_region = row.get("body_region_group", "")
        for start_s, end_s in parse_gap_intervals_s(row.get("gap_intervals_s")):
            start_frame = seconds_to_frame(start_s, frame_rate_hz)
            end_frame = seconds_to_frame(end_s, frame_rate_hz)
            if end_frame < start_frame:
                start_frame, end_frame = end_frame, start_frame
            duration_frames = int(end_frame - start_frame + 1)
            duration_seconds = float(end_s - start_s)
            event = _row_base(session_key, source_file)
            event.update(
                {
                    "qc_type": qc_type,
                    "severity": "caution",
                    "frame": start_frame,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "time_sec": float(start_s),
                    "start_time_sec": float(start_s),
                    "end_time_sec": float(end_s),
                    "duration_frames": duration_frames,
                    "duration_seconds": duration_seconds,
                    "entity_type": _entity_type_for_marker(marker),
                    "entity_name": marker,
                    "marker_raw_name": marker,
                    "body_region_group": str(body_region) if pd.notna(body_region) else "",
                    "reason": qc_type.replace("marker_", "gap_"),
                    "notes": f"gap_interval_s={start_s:.4f}-{end_s:.4f}",
                }
            )
            rows.append(event)

    if not rows:
        return _empty_events()
    return pd.DataFrame(rows, columns=list(LAYER1_BASE_EVENT_COLUMNS))


def _filter_interval_events_when_authoritative_sources_exist(
    intervals: pd.DataFrame,
    *,
    has_gap_0p5_file: bool,
    has_gap_0p2_file: bool,
    has_artifact_file: bool,
) -> pd.DataFrame:
    if intervals.empty:
        return intervals
    drop_types: set[str] = set()
    if has_gap_0p5_file:
        drop_types.add("marker_gap_0p5")
    if has_gap_0p2_file:
        drop_types.add("marker_gap_0p2")
    if has_artifact_file:
        drop_types.update(ARTIFACT_QC_TYPES)
    if not drop_types:
        return intervals
    return intervals.loc[~intervals["qc_type"].isin(drop_types)].copy()


def _authoritative_frame_coverage(events: pd.DataFrame) -> set[tuple[int, str]]:
    """Return (frame, qc_type) pairs covered by parsed gap/artifact event sources."""
    authoritative_files = {
        "gaps_over_0p5s.csv",
        "gaps_over_0p2s.csv",
        "artifact_events.csv",
        "qc_mask_intervals.csv",
    }
    covered: set[tuple[int, str]] = set()
    subset = events.loc[events["source_file"].isin(authoritative_files)]
    for _, row in subset.iterrows():
        if (
            row["source_file"] == "qc_mask_intervals.csv"
            and marker_identity_from_event_row(row) is None
        ):
            continue
        qc_type = str(row.get("qc_type", ""))
        if qc_type not in MASK_FLAG_QC_TYPES:
            continue
        start = int(row["start_frame"])
        end = int(row["end_frame"])
        for frame in range(start, end + 1):
            covered.add((frame, qc_type))
    return covered


def _dedupe_mask_flags_covered_by_intervals(events: pd.DataFrame) -> pd.DataFrame:
    """Drop per-frame mask flags when a higher-fidelity event already covers the frame."""
    if events.empty:
        return events

    mask = events.loc[events["source_file"] == "qc_mask.csv"]
    if mask.empty:
        return events

    covered = _authoritative_frame_coverage(events)
    if not covered:
        return events

    keep_mask_idx: list[int] = []
    for idx, row in mask.iterrows():
        qc_type = str(row.get("qc_type", ""))
        if qc_type in MASK_FLAG_QC_TYPES:
            frame = int(row["start_frame"])
            if (frame, qc_type) in covered:
                continue
        keep_mask_idx.append(idx)

    other = events.loc[events["source_file"] != "qc_mask.csv"]
    kept_mask = mask.loc[keep_mask_idx]
    return pd.concat([kept_mask, other], ignore_index=True)


def normalize_artifact_events(
    artifacts: pd.DataFrame,
    session_key: str,
    *,
    source_file: str = "artifact_events.csv",
) -> pd.DataFrame:
    """Normalize artifact_events.csv into marker/segment artifact events."""
    rows: list[dict] = []
    for _, row in artifacts.iterrows():
        start_frame = int(row["start_frame"])
        end_frame = int(row["end_frame"])
        marker_name = row.get("marker_name", "")
        body_region = row.get("body_region_group", "")
        event_class = row.get("event_class", "")
        method = row.get("method", "")
        severity = row.get("severity", "moderate")
        marker_name = str(marker_name).strip() if pd.notna(marker_name) else ""
        qc_type = artifact_method_to_qc_type(method)

        event = _row_base(session_key, source_file)
        event.update(
            {
                "qc_type": qc_type,
                "severity": str(severity) if pd.notna(severity) else "moderate",
                "frame": start_frame,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "start_time_sec": float(row["start_time_s"])
                if pd.notna(row.get("start_time_s"))
                else None,
                "end_time_sec": float(row["end_time_s"])
                if pd.notna(row.get("end_time_s"))
                else None,
                "duration_frames": int(row["duration_frames"])
                if pd.notna(row.get("duration_frames"))
                else int(end_frame - start_frame + 1),
                "duration_seconds": float(row["duration_seconds"])
                if pd.notna(row.get("duration_seconds"))
                else None,
                "entity_type": _entity_type_for_marker(marker_name) if marker_name else "marker",
                "entity_name": marker_name,
                "marker_raw_name": marker_name,
                "body_region_group": str(body_region) if pd.notna(body_region) else "",
                "reason": str(method) if pd.notna(method) else str(event_class),
                "notes": f"event_id={row.get('event_id', '')}; event_class={event_class}",
            }
        )
        rows.append(event)

    if not rows:
        return _empty_events()
    return pd.DataFrame(rows, columns=list(LAYER1_BASE_EVENT_COLUMNS))


def build_layer1_event_table(
    bundle: Layer1Bundle,
    session_key: str,
    *,
    mapper: MarkerFamilyMapper | None = None,
) -> pd.DataFrame:
    """Build combined Layer 1 normalized event table from all available sources."""
    if mapper is None:
        mapper = MarkerFamilyMapper()

    frame_rate_hz = float(bundle.manifest.get("frame_rate_hz", 120.0))
    frame_col = str(bundle.manifest.get("frame_index_column", "frame"))
    time_col = str(bundle.manifest.get("time_column", "time_s"))

    has_gap_0p5_file = bundle.gaps_over_0p5s is not None and not bundle.gaps_over_0p5s.empty
    has_gap_0p2_file = bundle.gaps_over_0p2s is not None and not bundle.gaps_over_0p2s.empty
    has_artifact_file = bundle.artifact_events is not None and not bundle.artifact_events.empty

    parts: list[pd.DataFrame] = []

    if has_gap_0p5_file:
        parts.append(
            normalize_gap_summary_events(
                bundle.gaps_over_0p5s,
                session_key,
                qc_type="marker_gap_0p5",
                source_file="gaps_over_0p5s.csv",
                frame_rate_hz=frame_rate_hz,
            )
        )

    if has_gap_0p2_file:
        parts.append(
            normalize_gap_summary_events(
                bundle.gaps_over_0p2s,
                session_key,
                qc_type="marker_gap_0p2",
                source_file="gaps_over_0p2s.csv",
                frame_rate_hz=frame_rate_hz,
            )
        )

    if has_artifact_file:
        parts.append(
            normalize_artifact_events(
                bundle.artifact_events,
                session_key,
                source_file="artifact_events.csv",
            )
        )

    if bundle.qc_mask_intervals is not None:
        intervals = normalize_interval_events(
            bundle.qc_mask_intervals,
            session_key,
            source_file="qc_mask_intervals.csv",
            frame_rate_hz=frame_rate_hz,
        )
        intervals = _filter_interval_events_when_authoritative_sources_exist(
            intervals,
            has_gap_0p5_file=has_gap_0p5_file,
            has_gap_0p2_file=has_gap_0p2_file,
            has_artifact_file=has_artifact_file,
        )
        if not intervals.empty:
            parts.append(intervals)

    parts.append(
        normalize_qc_mask_events(
            bundle.qc_mask,
            session_key,
            frame_col=frame_col,
            time_col=time_col,
            source_file="qc_mask.csv",
            frame_rate_hz=frame_rate_hz,
        )
    )

    combined = pd.concat([p for p in parts if not p.empty], ignore_index=True)
    if combined.empty:
        return _empty_events()

    combined = _dedupe_mask_flags_covered_by_intervals(combined)
    return _apply_marker_family_overlay(combined, mapper)


def _apply_marker_family_overlay(
    events: pd.DataFrame,
    mapper: MarkerFamilyMapper,
) -> pd.DataFrame:
    """Annotate events with marker-family mapping columns."""
    rows: list[dict] = []
    for _, ev in events.iterrows():
        row = ev.to_dict()
        marker = marker_identity_from_event_row(row)
        region = row.get("body_region_group")
        mapping = mapper.map_marker_to_family(marker, body_region_group=region)
        row["normalized_marker_name"] = mapping.normalized_marker_name
        row["attached_bone"] = mapping.attached_bone
        row["attached_bone_canonical"] = mapping.attached_bone_canonical
        row["related_joint_family"] = mapping.joint_family
        row["adjacent_joint_family"] = mapping.adjacent_joint_family
        row["mapping_source"] = mapping.mapping_source
        row["mapping_confidence"] = mapping.mapping_confidence
        row["template_mapping_status"] = mapping.template_mapping_status
        rows.append(row)

    return pd.DataFrame(rows, columns=list(LAYER1_NORMALIZED_EVENT_COLUMNS))


def gap_files_status(bundle: Layer1Bundle) -> dict[str, str]:
    """Report optional Layer 1 supplementary file parsing status."""
    status: dict[str, str] = {}
    for name, df in (
        ("gaps_over_0p2s.csv", bundle.gaps_over_0p2s),
        ("gaps_over_0p5s.csv", bundle.gaps_over_0p5s),
    ):
        if df is None:
            status[name] = "not_present"
        elif df.empty:
            status[name] = "empty"
        else:
            status[name] = "present_parsed"

    if bundle.artifact_events is None:
        status["artifact_events.csv"] = "not_present"
    elif bundle.artifact_events.empty:
        status["artifact_events.csv"] = "empty"
    else:
        status["artifact_events.csv"] = "present_parsed"

    if bundle.artifacts_by_segment is None:
        status["artifacts_by_segment.csv"] = "not_present"
    elif bundle.artifacts_by_segment.empty:
        status["artifacts_by_segment.csv"] = "empty"
    else:
        status["artifacts_by_segment.csv"] = "present_regional_summary"

    return status
