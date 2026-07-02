"""Segmentation xlsx ↔ manifest ↔ analysis-request coverage (G4)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from project_status import ProjectSnapshot

# Layer 2.5 helpers (Layer2.5_Segmentation/src on sys.path in dashboard/tests).
from pre_jvcpca_review.exercise_segments import (
    EXERCISE_SELECTION_ALL_IN_SHEET,
    EXERCISE_SELECTION_EXPLICIT_IDS,
    EXERCISE_SELECTION_GAGA_P_PHASES,
    ExerciseSegment,
    export_label_for_segment,
    exercise_segments_path_for_participant,
    gaga_label_for_exercise_id,
    load_exercise_segments,
    make_window_label,
    resolve_segmentation_dir,
    resolve_target_exercise_ids,
    segments_for_exercise_ids,
)

COVERAGE_EXPORTED = "exported"
COVERAGE_REQUESTED_NOT_EXPORTED = "requested_not_exported"
COVERAGE_AVAILABLE_NOT_REQUESTED = "available_not_requested"
COVERAGE_MISSING_FROM_SHEET = "missing_from_sheet"

SESSION_KEY_RE = re.compile(
    r"(?P<participant>\d+)_T(?P<timepoint>\d+)_P(?P<part>\d+)_R(?P<repetition>\d+)"
)


@dataclass(frozen=True)
class SegmentationSelection:
    mode: str = EXERCISE_SELECTION_ALL_IN_SHEET
    p_phases: tuple[str, ...] = ("P1", "P2", "P3")
    selected_exercise_ids: tuple[int, ...] = ()


def load_participant_segmentation_catalog(
    snapshot: ProjectSnapshot,
    participant_id: str,
) -> tuple[dict[str, list[ExerciseSegment]], Path | None]:
    """Load xlsx catalog for one participant; return sessions map and source path."""
    seg_path = exercise_segments_path_for_participant(snapshot.project_root, participant_id)
    if not seg_path.is_file():
        return {}, None
    return load_exercise_segments(seg_path), seg_path


def _sessions_for_request(
    participant_id: str,
    timepoints: set[str],
    repetitions: set[str],
    catalog: dict[str, list[ExerciseSegment]],
) -> list[str]:
    out: list[str] = []
    for session_id in sorted(catalog):
        m = SESSION_KEY_RE.match(session_id)
        if not m or m.group("participant") != str(participant_id):
            continue
        if f"T{m.group('timepoint')}" not in timepoints:
            continue
        if f"R{m.group('repetition')}" not in repetitions:
            continue
        out.append(session_id)
    return out


def _manifest_index(manifest_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Key: (session_id, export_label) where export_label is P1 or ex01."""
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in manifest_rows:
        if str(row.get("export_granularity")) == "combined_group4":
            continue
        session_id = str(row.get("session_id", ""))
        label = str(row.get("gaga_exercise_label") or "")
        if not session_id or not label:
            continue
        index[(session_id, label)] = row
    return index


def _timepoints_and_repetitions_from_comparisons(inp: Any) -> tuple[set[str], set[str]]:
    timepoints: set[str] = set()
    repetitions: set[str] = set(inp.repetitions)
    for comp in inp.comparisons:
        if comp.comparison_type == "longitudinal":
            if comp.timepoint_a:
                timepoints.add(comp.timepoint_a)
            if comp.timepoint_b:
                timepoints.add(comp.timepoint_b)
            repetitions.update(comp.repetitions)
        elif comp.comparison_type == "within_timepoint_repetition":
            if comp.timepoint:
                timepoints.add(comp.timepoint)
            repetitions.add(comp.repetition_a)
            repetitions.add(comp.repetition_b)
    return timepoints, repetitions


def build_segmentation_coverage_rows(
    snapshot: ProjectSnapshot,
    inp: Any,
    *,
    selection: SegmentationSelection | None = None,
) -> tuple[list[dict[str, Any]], Path | None]:
    """Compare xlsx sheets, manifest exports, and request exercise selection."""
    sel = selection or SegmentationSelection(
        mode=getattr(inp, "exercise_selection_mode", EXERCISE_SELECTION_GAGA_P_PHASES),
        p_phases=tuple(getattr(inp, "p_phases", ())),
        selected_exercise_ids=tuple(getattr(inp, "selected_exercise_ids", ())),
    )
    catalog, seg_path = load_participant_segmentation_catalog(snapshot, inp.participant_id)
    timepoints, repetitions = _timepoints_and_repetitions_from_comparisons(inp)
    sessions = _sessions_for_request(inp.participant_id, timepoints, repetitions, catalog)

    manifest_rows = [
        r
        for r in snapshot.l25_manifest_rows
        if str(r.get("participant_id")) == inp.participant_id
        and str(r.get("export_granularity")) != "combined_group4"
    ]
    manifest_by_key = _manifest_index(manifest_rows)

    rows: list[dict[str, Any]] = []
    for session_id in sessions:
        sheet_segments = catalog.get(session_id, [])
        m = SESSION_KEY_RE.match(session_id)
        timepoint = f"T{m.group('timepoint')}" if m else ""
        repetition = f"R{m.group('repetition')}" if m else ""
        requested_ids = resolve_target_exercise_ids(
            sel.mode,
            p_phases=sel.p_phases,
            selected_exercise_ids=sel.selected_exercise_ids,
            sheet_segments=sheet_segments,
        )
        for seg in sheet_segments:
            export_label = export_label_for_segment(seg)
            gaga_label = gaga_label_for_exercise_id(seg.exercise_id)
            requested = seg.exercise_id in requested_ids
            manifest_row = manifest_by_key.get((session_id, export_label))
            if manifest_row:
                coverage_status = COVERAGE_EXPORTED if requested else COVERAGE_AVAILABLE_NOT_REQUESTED
            elif requested:
                coverage_status = COVERAGE_REQUESTED_NOT_EXPORTED
            else:
                coverage_status = COVERAGE_AVAILABLE_NOT_REQUESTED
            expected_window = make_window_label(
                session_id,
                seg.start_frame,
                seg.end_frame,
                tag=export_label if gaga_label else export_label,
            )
            rows.append(
                {
                    "participant_id": inp.participant_id,
                    "session_id": session_id,
                    "timepoint": timepoint,
                    "repetition": repetition,
                    "sheet_name": seg.sheet_name,
                    "exercise_id": seg.exercise_id,
                    "exercise_name": seg.exercise_name,
                    "exercise_export_label": export_label,
                    "p_phase": gaga_label or "",
                    "start_frame": seg.start_frame,
                    "end_frame": seg.end_frame,
                    "expected_window_label": expected_window,
                    "requested": requested,
                    "coverage_status": coverage_status,
                    "in_manifest": manifest_row is not None,
                    "matrix_path": str(manifest_row.get("matrix_path", "")) if manifest_row else "",
                    "manifest_path": str(manifest_row.get("manifest_path", "")) if manifest_row else "",
                    "qc_status": str(manifest_row.get("qc_status", "")) if manifest_row else "",
                    "layer3_safe": str(manifest_row.get("layer3_safe", "")) if manifest_row else "",
                    "segmentation_source": str(seg_path) if seg_path else "",
                }
            )

        exported_labels = {
            label
            for (sid, label), _row in manifest_by_key.items()
            if sid == session_id
        }
        for label in sorted(exported_labels):
            if any(r["session_id"] == session_id and r["exercise_export_label"] == label for r in rows):
                continue
            manifest_row = manifest_by_key[(session_id, label)]
            rows.append(
                {
                    "participant_id": inp.participant_id,
                    "session_id": session_id,
                    "timepoint": timepoint,
                    "repetition": repetition,
                    "sheet_name": "",
                    "exercise_id": manifest_row.get("gaga_exercise_id", ""),
                    "exercise_name": "",
                    "exercise_export_label": label,
                    "p_phase": label if label in sel.p_phases else "",
                    "start_frame": None,
                    "end_frame": None,
                    "expected_window_label": "",
                    "requested": False,
                    "coverage_status": COVERAGE_MISSING_FROM_SHEET,
                    "in_manifest": True,
                    "matrix_path": str(manifest_row.get("matrix_path", "")),
                    "manifest_path": str(manifest_row.get("manifest_path", "")),
                    "qc_status": str(manifest_row.get("qc_status", "")),
                    "layer3_safe": str(manifest_row.get("layer3_safe", "")),
                    "segmentation_source": str(seg_path) if seg_path else "",
                }
            )

    return rows, seg_path


def build_resolved_segments(
    snapshot: ProjectSnapshot,
    inp: Any,
    *,
    selection: SegmentationSelection | None = None,
) -> list[dict[str, Any]]:
    """Resolve analysis segments with xlsx frame provenance and manifest linkage."""
    coverage_rows, _ = build_segmentation_coverage_rows(snapshot, inp, selection=selection)
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in coverage_rows:
        if not row.get("requested"):
            continue
        session_id = str(row["session_id"])
        export_label = str(row["exercise_export_label"])
        segment_id = f"{session_id}::{export_label}"
        if segment_id in seen:
            continue
        seen.add(segment_id)

        entry: dict[str, Any] = {
            "segment_id": segment_id,
            "session_id": session_id,
            "timepoint": row["timepoint"],
            "repetition": row["repetition"],
            "exercise_id": row["exercise_id"],
            "exercise_name": row["exercise_name"],
            "exercise_export_label": export_label,
            "p_phase": row["p_phase"] or export_label,
            "start_frame": row["start_frame"],
            "end_frame": row["end_frame"],
            "expected_window_label": row["expected_window_label"],
            "sheet_name": row["sheet_name"],
            "segmentation_source": row["segmentation_source"],
            "export_status": COVERAGE_EXPORTED if row["in_manifest"] else COVERAGE_REQUESTED_NOT_EXPORTED,
            "matrix_path": row["matrix_path"],
            "manifest_path": row["manifest_path"],
            "feature_schema_id": "",
            "qc_status": row["qc_status"],
            "layer3_safe": row["layer3_safe"],
        }
        if row["in_manifest"]:
            manifest_row = next(
                (
                    m
                    for m in snapshot.l25_manifest_rows
                    if str(m.get("session_id")) == session_id
                    and str(m.get("gaga_exercise_label")) == export_label
                    and str(m.get("export_granularity")) != "combined_group4"
                ),
                None,
            )
            if manifest_row:
                entry["feature_schema_id"] = str(manifest_row.get("feature_schema_id", ""))
        resolved.append(entry)

    return sorted(resolved, key=lambda r: (r["timepoint"], r["repetition"], str(r["exercise_id"])))


def summarize_segmentation_coverage(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        COVERAGE_EXPORTED: 0,
        COVERAGE_REQUESTED_NOT_EXPORTED: 0,
        COVERAGE_AVAILABLE_NOT_REQUESTED: 0,
        COVERAGE_MISSING_FROM_SHEET: 0,
    }
    for row in rows:
        status = str(row.get("coverage_status", ""))
        if status in counts:
            counts[status] += 1
    counts["requested"] = sum(1 for r in rows if r.get("requested"))
    counts["sheet_rows"] = len(rows)
    return counts


def list_sheet_exercises_for_participant(
    snapshot: ProjectSnapshot,
    participant_id: str,
) -> list[dict[str, Any]]:
    """All exercises across xlsx sheets (for GUI multiselect)."""
    catalog, seg_path = load_participant_segmentation_catalog(snapshot, participant_id)
    options: list[dict[str, Any]] = []
    seen: set[int] = set()
    for _session_id, segments in sorted(catalog.items()):
        for seg in segments:
            if seg.exercise_id in seen:
                continue
            seen.add(seg.exercise_id)
            options.append(
                {
                    "exercise_id": seg.exercise_id,
                    "label": export_label_for_segment(seg),
                    "name": seg.exercise_name,
                    "gaga_p_phase": gaga_label_for_exercise_id(seg.exercise_id) or "",
                    "segmentation_source": str(seg_path) if seg_path else "",
                }
            )
    return sorted(options, key=lambda o: o["exercise_id"])
