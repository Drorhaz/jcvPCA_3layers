"""Batch Gaga P1–P5 and combined Group4 Layer 3-safe exports."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from pre_jvcpca_review.canonical_manifest import core_manifest_path_for_participant
from pre_jvcpca_review.exercise_segments import (
    EXPORT_GRANULARITY_COMBINED,
    EXPORT_GRANULARITY_PER_EXERCISE,
    EXPORT_GRANULARITY_SHEET_EXERCISE,
    GAGA_EXERCISE_ID_TO_LABEL,
    GAGA_EXERCISE_LABELS,
    ExerciseSegment,
    exercise_segments_path_for_participant,
    export_label_for_segment,
    gaga_label_for_exercise_id,
    gaga_segments_for_session,
    group4_window,
    make_window_label,
    segments_for_exercise_ids,
    window_tag_for_segment,
)
from pre_jvcpca_review.export_constants import WINDOW_MANIFEST_FILE
from pre_jvcpca_review.export_window import export_layer3_window
from pre_jvcpca_review.layer3_export_manifest import (
    ATTEMPT_STATUS_EXPORTED,
    ATTEMPT_STATUS_FAILED,
    ATTEMPT_STATUS_SKIPPED,
    EXPECTED_EXPORT_LABELS,
    GagaExportMetadata,
    build_session_coverage_diff,
    central_manifest_path,
    export_attempts_report_path,
    load_export_attempts_report,
    load_layer25_export_manifest,
    manifest_row_from_window_manifest,
    scan_window_exports,
    session_coverage_report_path,
    write_export_attempts_report,
    write_export_readiness_artifacts,
    write_layer25_export_manifest,
    write_session_coverage_report,
)
from pre_jvcpca_review.review_output import resolve_review_out_dir


@dataclass
class GagaBatchExportResult:
    participant_id: str
    session_id: str
    exported: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    attempts: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GagaBatchRunSummary:
    results: list[GagaBatchExportResult] = field(default_factory=list)
    manifest_rows: list[dict[str, Any]] = field(default_factory=list)
    attempt_rows: list[dict[str, Any]] = field(default_factory=list)
    central_manifest_path: str = ""
    readiness_paths: dict[str, str] = field(default_factory=dict)
    attempts_report_path: str = ""
    session_coverage_report_path: str = ""


def _read_window_manifest(manifest_path: Path) -> dict[str, Any]:
    import json

    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _attempt_base(session_row: pd.Series) -> dict[str, str]:
    return {
        "participant_id": str(session_row["participant_id"]),
        "timepoint": str(session_row["timepoint"]),
        "repetition": str(session_row["repetition_id"]),
        "session_id": str(session_row["session_id"]),
    }


def _blocking_warning_details(out_dir: Path, export_result: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return reason_code, reason_message, source_dependency, warning_file."""
    warnings_csv = export_result.get("warnings_csv")
    if warnings_csv is None:
        candidate = out_dir / "window_warnings.csv"
        warnings_csv = candidate if candidate.is_file() else None
    warning_file = str(warnings_csv) if warnings_csv else ""
    manifest_path = export_result.get("paths", {}).get("manifest", out_dir / WINDOW_MANIFEST_FILE)
    artifact_path = str(manifest_path)

    if warnings_csv and Path(warnings_csv).is_file():
        with Path(warnings_csv).open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if str(row.get("severity", "")).lower() == "blocking":
                    return (
                        str(row.get("warning_id") or "export_blocked"),
                        str(row.get("message") or "Layer 3 export blocked by warnings."),
                        str(row.get("source_file") or ""),
                        warning_file,
                    )

    summary = export_result.get("warnings_summary") or {}
    if summary.get("has_blocking"):
        return (
            "export_blocked",
            "Layer 3 export blocked by blocking warnings.",
            "",
            warning_file,
        )
    return (
        "export_blocked",
        "Layer 3 export blocked by warnings.",
        "",
        warning_file,
    )


def _record_attempt(
    result: GagaBatchExportResult,
    *,
    session_row: pd.Series,
    export_label: str,
    status: str,
    reason_code: str = "",
    reason_message: str = "",
    artifact_path: str = "",
    source_dependency: str = "",
    warning_file: str = "",
) -> None:
    attempt = {
        **_attempt_base(session_row),
        "export_label": export_label,
        "status": status,
        "reason_code": reason_code,
        "reason_message": reason_message,
        "artifact_path": artifact_path,
        "source_dependency": source_dependency,
        "warning_file": warning_file,
    }
    result.attempts.append(attempt)


def _merge_manifest_rows(
    new_rows: list[dict[str, Any]],
    output_root: Path,
    participant_ids: list[str],
) -> list[dict[str, Any]]:
    existing_path = central_manifest_path(output_root)
    existing = load_layer25_export_manifest(existing_path)
    if existing.empty:
        return new_rows
    kept = existing[~existing["participant_id"].astype(str).isin(participant_ids)]
    if kept.empty:
        return new_rows
    return pd.concat([kept, pd.DataFrame(new_rows)], ignore_index=True).to_dict("records")


def _merge_attempt_rows(
    new_rows: list[dict[str, Any]],
    output_root: Path,
    participant_ids: list[str],
) -> list[dict[str, Any]]:
    existing = load_export_attempts_report(export_attempts_report_path(output_root))
    if existing.empty:
        return new_rows
    kept = existing[~existing["participant_id"].astype(str).isin(participant_ids)]
    if kept.empty:
        return new_rows
    return pd.concat([kept, pd.DataFrame(new_rows)], ignore_index=True).to_dict("records")


def export_gaga_session(
    *,
    session_row: pd.Series,
    segments: list[ExerciseSegment],
    output_root: Path,
    segmentation_source: str = "",
    allow_nan_matrix: bool = False,
    export_combined: bool = True,
    export_per_exercise: bool = True,
    export_exercise_ids: set[int] | None = None,
    export_all_sheet_exercises: bool = False,
    pilot_manifest_path: Path | None = None,
) -> GagaBatchExportResult:
    """Export combined Group4 and/or per-exercise windows for one session."""
    participant_id = str(session_row["participant_id"])
    session_id = str(session_row["session_id"])
    session_manifest_path = pilot_manifest_path or core_manifest_path_for_participant(participant_id)
    result = GagaBatchExportResult(participant_id=participant_id, session_id=session_id)

    if not segments:
        source = segmentation_source or "segmentation catalog"
        message = (
            "No exercise frame boundaries in segmentation catalog for this session. "
            "Cannot export per-exercise P1–P5 without guessing."
        )
        result.skipped.append(
            {
                "session_id": session_id,
                "reason": "missing_exercise_segmentation",
                "message": message,
            }
        )
        for export_label in EXPECTED_EXPORT_LABELS:
            _record_attempt(
                result,
                session_row=session_row,
                export_label=export_label,
                status=ATTEMPT_STATUS_SKIPPED,
                reason_code="missing_exercise_segmentation",
                reason_message=message,
                source_dependency=source,
            )
        return result

    layer1_dir = Path(str(session_row["layer1_run_dir"]))
    layer2_dir = Path(str(session_row["layer2_run_dir"]))

    def _run_export(
        frame_start: int,
        frame_end: int,
        window_label: str,
        metadata: GagaExportMetadata,
        export_label: str,
    ) -> None:
        out_dir = resolve_review_out_dir(output_root, participant_id, session_id, window_label)
        export_result = export_layer3_window(
            layer1_dir,
            layer2_dir,
            out_dir,
            frame_start,
            frame_end,
            session_row=session_row,
            window_label=window_label,
            allow_nan_matrix=allow_nan_matrix,
            overlap_df=None,
            scope_required_links=None,
            gaga_export_metadata=metadata,
            pilot_manifest_path=session_manifest_path,
        )
        status = str(export_result.get("status", ""))
        window_manifest_path = Path(
            export_result.get("paths", {}).get("manifest", out_dir / WINDOW_MANIFEST_FILE)
        )

        if status == "blocked":
            reason_code, reason_message, source_dependency, warning_file = _blocking_warning_details(
                out_dir,
                export_result,
            )
            result.errors.append(
                {
                    "session_id": session_id,
                    "window_label": window_label,
                    "reason": reason_code,
                    "message": reason_message,
                }
            )
            _record_attempt(
                result,
                session_row=session_row,
                export_label=export_label,
                status=ATTEMPT_STATUS_FAILED,
                reason_code=reason_code,
                reason_message=reason_message,
                artifact_path=str(window_manifest_path),
                source_dependency=source_dependency,
                warning_file=warning_file,
            )
            return

        if status != "exported":
            result.errors.append(
                {
                    "session_id": session_id,
                    "window_label": window_label,
                    "reason": status or "export_failed",
                    "message": "Export did not complete successfully.",
                }
            )
            _record_attempt(
                result,
                session_row=session_row,
                export_label=export_label,
                status=ATTEMPT_STATUS_FAILED,
                reason_code=status or "export_failed",
                reason_message="Export did not complete successfully.",
                artifact_path=str(window_manifest_path),
            )
            return

        payload = _read_window_manifest(window_manifest_path)
        matrix_path = out_dir / "window_jvcpca_matrix.parquet"
        row = manifest_row_from_window_manifest(
            payload,
            manifest_path=window_manifest_path,
            matrix_path=matrix_path,
        )
        result.exported.append(row)
        _record_attempt(
            result,
            session_row=session_row,
            export_label=export_label,
            status=ATTEMPT_STATUS_EXPORTED,
            artifact_path=str(window_manifest_path),
        )

    if export_combined:
        window = group4_window(segments)
        if window is None:
            message = "No Group4 exercise_id 9–13 segments for combined export."
            result.skipped.append(
                {
                    "session_id": session_id,
                    "reason": "missing_group4_segments",
                    "message": message,
                }
            )
            _record_attempt(
                result,
                session_row=session_row,
                export_label="combined_group4",
                status=ATTEMPT_STATUS_SKIPPED,
                reason_code="missing_group4_segments",
                reason_message=message,
                source_dependency=segmentation_source,
            )
        else:
            start, end = window
            label = make_window_label(session_id, start, end, tag="g4")
            _run_export(
                start,
                end,
                label,
                GagaExportMetadata(
                    gaga_exercise_id="",
                    gaga_exercise_label="combined_group4",
                    export_granularity=EXPORT_GRANULARITY_COMBINED,
                ),
                "combined_group4",
            )

    if export_per_exercise:
        if export_all_sheet_exercises:
            ids_to_export = {seg.exercise_id for seg in segments}
        elif export_exercise_ids is not None:
            ids_to_export = set(export_exercise_ids)
        else:
            ids_to_export = {seg.exercise_id for seg in gaga_segments_for_session(segments)}

        selected_segments = segments_for_exercise_ids(segments, ids_to_export)
        found_ids = {seg.exercise_id for seg in selected_segments}
        for exercise_id in sorted(ids_to_export):
            if exercise_id in found_ids:
                continue
            export_label = export_label_for_segment(
                ExerciseSegment(
                    exercise_id=exercise_id,
                    exercise_name="",
                    start_frame=0,
                    end_frame=0,
                    session_id=session_id,
                    sheet_name="",
                )
            )
            message = (
                f"No frame boundaries for exercise_id {exercise_id} "
                f"({export_label}) in segmentation catalog."
            )
            result.skipped.append(
                {
                    "session_id": session_id,
                    "reason": "missing_exercise_segment",
                    "message": message,
                }
            )
            _record_attempt(
                result,
                session_row=session_row,
                export_label=export_label,
                status=ATTEMPT_STATUS_SKIPPED,
                reason_code="missing_exercise_segment",
                reason_message=message,
                source_dependency=segmentation_source,
            )
        for segment in selected_segments:
            export_label = export_label_for_segment(segment)
            gaga_label = gaga_label_for_exercise_id(segment.exercise_id)
            tag = window_tag_for_segment(segment)
            granularity = (
                EXPORT_GRANULARITY_PER_EXERCISE
                if gaga_label
                else EXPORT_GRANULARITY_SHEET_EXERCISE
            )
            label = make_window_label(
                session_id,
                segment.start_frame,
                segment.end_frame,
                tag=tag,
            )
            _run_export(
                segment.start_frame,
                segment.end_frame,
                label,
                GagaExportMetadata(
                    gaga_exercise_id=segment.exercise_id,
                    gaga_exercise_label=export_label,
                    export_granularity=granularity,
                ),
                export_label,
            )

    return result


def run_gaga_batch_export(
    *,
    session_index: pd.DataFrame,
    exercise_catalog: dict[str, list[ExerciseSegment]],
    output_root: Path,
    participant_ids: list[str] | None = None,
    project_root: Path | None = None,
    segmentation_paths: dict[str, Path] | None = None,
    allow_nan_matrix: bool = False,
    export_combined: bool = True,
    export_per_exercise: bool = True,
    export_exercise_ids: set[int] | None = None,
    export_all_sheet_exercises: bool = False,
    use_participant_core_manifests: bool = True,
) -> GagaBatchRunSummary:
    """Export Gaga windows for selected participants and write centralized manifest."""
    summary = GagaBatchRunSummary()
    all_rows: list[dict[str, Any]] = []
    all_attempts: list[dict[str, Any]] = []

    participants = participant_ids or sorted(session_index["participant_id"].unique().tolist())
    for participant_id in participants:
        seg_path = ""
        if segmentation_paths and participant_id in segmentation_paths:
            seg_path = str(segmentation_paths[participant_id])
        elif project_root is not None:
            candidate = exercise_segments_path_for_participant(project_root, participant_id)
            if candidate.is_file():
                seg_path = str(candidate)

        sess_df = session_index[
            (session_index["participant_id"] == participant_id) & session_index["is_matched"]
        ]
        for _, row in sess_df.iterrows():
            session_id = str(row["session_id"])
            segments = exercise_catalog.get(session_id, [])
            batch = export_gaga_session(
                session_row=row,
                segments=segments,
                output_root=output_root,
                segmentation_source=seg_path,
                allow_nan_matrix=allow_nan_matrix,
                export_combined=export_combined,
                export_per_exercise=export_per_exercise,
                export_exercise_ids=export_exercise_ids,
                export_all_sheet_exercises=export_all_sheet_exercises,
                pilot_manifest_path=(
                    core_manifest_path_for_participant(participant_id)
                    if use_participant_core_manifests
                    else None
                ),
            )
            summary.results.append(batch)
            all_rows.extend(batch.exported)
            all_attempts.extend(batch.attempts)

    scanned = scan_window_exports(output_root)
    seen_manifests = {r["manifest_path"] for r in all_rows}
    for row in scanned:
        if row["manifest_path"] not in seen_manifests:
            all_rows.append(row)

    if participant_ids:
        all_rows = _merge_manifest_rows(all_rows, output_root, participants)
        all_attempts = _merge_attempt_rows(all_attempts, output_root, participants)

    manifest_path = write_layer25_export_manifest(all_rows, central_manifest_path(output_root))
    attempts_path = write_export_attempts_report(
        all_attempts,
        export_attempts_report_path(output_root),
    )
    manifest_df = pd.DataFrame(all_rows)
    attempts_df = pd.DataFrame(all_attempts)
    coverage_df = build_session_coverage_diff(
        session_index=session_index,
        exercise_catalog=exercise_catalog,
        manifest_df=manifest_df,
        attempts_df=attempts_df,
        participant_ids=participants,
        project_root=project_root,
    )
    coverage_path = write_session_coverage_report(
        coverage_df,
        session_coverage_report_path(output_root),
    )

    summary.manifest_rows = all_rows
    summary.attempt_rows = all_attempts
    summary.central_manifest_path = str(manifest_path)
    summary.attempts_report_path = str(attempts_path)
    summary.session_coverage_report_path = str(coverage_path)
    readiness_paths = write_export_readiness_artifacts(manifest_df, output_root)
    summary.readiness_paths = {k: str(v) for k, v in readiness_paths.items()}
    return summary
