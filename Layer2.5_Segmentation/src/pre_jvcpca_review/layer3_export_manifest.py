"""Centralized Layer 2.5 export manifest and export-readiness reporting."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from pre_jvcpca_review.exercise_segments import (
    EXPORT_GRANULARITY_COMBINED,
    EXPORT_GRANULARITY_PER_EXERCISE,
    EXERCISE_SEGMENTS_FILENAME_TEMPLATE,
    GAGA_EXERCISE_ID_TO_LABEL,
    GAGA_EXERCISE_LABELS,
    CENTRAL_MANIFEST_FILENAME,
    EXPORT_ATTEMPTS_REPORT_FILENAME,
    SESSION_COVERAGE_REPORT_FILENAME,
    exercise_segments_path_for_participant,
)
from pre_jvcpca_review.export_constants import WINDOW_MANIFEST_FILE, WINDOW_MATRIX_FILE

CENTRAL_MANIFEST_COLUMNS: list[str] = [
    "participant_id",
    "timepoint",
    "repetition",
    "task_part_id",
    "session_id",
    "run_label",
    "gaga_exercise_id",
    "gaga_exercise_label",
    "export_granularity",
    "export_mode",
    "matrix_path",
    "manifest_path",
    "layer3_safe",
    "qc_status",
    "n_frames",
    "n_features",
    "feature_schema_id",
    "created_at",
]

READINESS_BLOCKING = "blocking"
READINESS_WARNING = "warning"
READINESS_PASS = "pass"

SESSION_STATUS_SUCCESSFUL = "successful"
SESSION_STATUS_PARTIAL = "partial"
SESSION_STATUS_SKIPPED = "skipped"
SESSION_STATUS_FAILED = "failed"
SESSION_STATUS_MISSING = "missing"

ATTEMPT_STATUS_EXPORTED = "exported"
ATTEMPT_STATUS_SKIPPED = "skipped"
ATTEMPT_STATUS_FAILED = "failed"

EXPECTED_EXPORT_LABELS: tuple[str, ...] = ("combined_group4", *GAGA_EXERCISE_LABELS)

EXPORT_ATTEMPTS_COLUMNS: list[str] = [
    "session_id",
    "participant_id",
    "timepoint",
    "repetition",
    "export_label",
    "status",
    "reason_code",
    "reason_message",
    "artifact_path",
    "source_dependency",
    "warning_file",
]

SESSION_COVERAGE_COLUMNS: list[str] = [
    "participant_id",
    "timepoint",
    "repetition",
    "session_id",
    "session_status",
    "in_session_index",
    "in_segmentation_catalog",
    "manifest_export_count",
    "combined_group4",
    "P1",
    "P2",
    "P3",
    "P4",
    "P5",
    "reason_code",
    "reason_message",
    "source_dependency",
    "warning_file",
]


@dataclass(frozen=True)
class GagaExportMetadata:
    gaga_exercise_id: int | str | None
    gaga_exercise_label: str
    export_granularity: str
    export_mode: str | None = None

    def __post_init__(self) -> None:
        if self.export_mode is None:
            object.__setattr__(self, "export_mode", self.export_granularity)


def derive_qc_status(warnings_summary: dict[str, Any] | None) -> str:
    """Explicit qc_status from export warnings summary."""
    ws = warnings_summary or {}
    if ws.get("has_blocking") or int(ws.get("n_blocking", 0)) > 0:
        return "blocking"
    if int(ws.get("n_strong_warning", 0)) > 0 or int(ws.get("n_warning", 0)) > 0:
        return "warning"
    return "pass"


def feature_schema_id_from_order(feature_order: list[str]) -> str:
    joined = "\n".join(feature_order)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def apply_gaga_export_metadata(
    manifest_payload: dict[str, Any],
    *,
    metadata: GagaExportMetadata,
    warnings_summary: dict[str, Any] | None,
    manifest_path: Path | str,
    matrix_path: Path | str,
) -> dict[str, Any]:
    """Patch window export manifest with Gaga / readiness fields."""
    identity = manifest_payload.get("identity") or {}
    ws = warnings_summary or manifest_payload.get("warnings_summary") or {}
    feature_order = manifest_payload.get("canonical_feature_order") or manifest_payload.get(
        "feature_order"
    ) or []

    manifest_payload["task_part_id"] = str(identity.get("part_id") or "")
    manifest_payload["gaga_exercise_id"] = (
        "" if metadata.gaga_exercise_id is None else str(metadata.gaga_exercise_id)
    )
    manifest_payload["gaga_exercise_label"] = metadata.gaga_exercise_label
    manifest_payload["export_granularity"] = metadata.export_granularity
    manifest_payload["export_mode"] = metadata.export_mode or metadata.export_granularity
    manifest_payload["qc_status"] = derive_qc_status(ws)
    manifest_payload["feature_schema_id"] = feature_schema_id_from_order(list(feature_order))
    manifest_payload["manifest_path"] = str(Path(manifest_path).resolve())
    manifest_payload["matrix_path"] = str(Path(matrix_path).resolve())
    return manifest_payload


def manifest_row_from_window_manifest(
    manifest: dict[str, Any],
    *,
    manifest_path: Path | str,
    matrix_path: Path | str | None = None,
) -> dict[str, Any]:
    """Build one centralized-manifest row from a window export manifest."""
    identity = manifest.get("identity") or {}
    matrix_path = matrix_path or manifest.get("matrix_path") or ""
    if not matrix_path:
        mp = Path(manifest_path).parent / str(manifest.get("jvcpca_matrix_file", WINDOW_MATRIX_FILE))
        matrix_path = str(mp) if mp.is_file() else ""

    feature_order = manifest.get("canonical_feature_order") or manifest.get("feature_order") or []
    ws = manifest.get("warnings_summary") or {}
    session_key = str(
        identity.get("session_id")
        or manifest.get("selected_session")
        or manifest.get("session_id")
        or ""
    )

    return {
        "participant_id": str(
            manifest.get("selected_participant") or identity.get("participant_id") or ""
        ),
        "timepoint": str(identity.get("timepoint") or ""),
        "repetition": str(identity.get("repetition_id") or ""),
        "task_part_id": str(manifest.get("task_part_id") or identity.get("part_id") or ""),
        "session_id": session_key,
        "run_label": str(manifest.get("run_label") or ""),
        "gaga_exercise_id": str(manifest.get("gaga_exercise_id") or ""),
        "gaga_exercise_label": str(manifest.get("gaga_exercise_label") or ""),
        "export_granularity": str(manifest.get("export_granularity") or ""),
        "export_mode": str(manifest.get("export_mode") or manifest.get("export_granularity") or ""),
        "matrix_path": str(matrix_path),
        "manifest_path": str(Path(manifest_path).resolve()),
        "layer3_safe": str(bool(manifest.get("layer3_safe", False))).lower(),
        "qc_status": str(manifest.get("qc_status") or derive_qc_status(ws)),
        "n_frames": manifest.get("n_frames"),
        "n_features": manifest.get("n_features"),
        "feature_schema_id": str(
            manifest.get("feature_schema_id")
            or feature_schema_id_from_order(list(feature_order))
        ),
        "created_at": str(manifest.get("created_at") or ""),
    }


def scan_window_exports(root_dir: Path | str) -> list[dict[str, Any]]:
    """Collect manifest rows by scanning window_export_manifest.json files."""
    root = Path(root_dir)
    rows: list[dict[str, Any]] = []
    for manifest_path in sorted(root.rglob(WINDOW_MANIFEST_FILE)):
        if "_archive" in manifest_path.parts:
            continue
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("export_status") == "blocked":
            continue
        matrix_path = manifest_path.parent / WINDOW_MATRIX_FILE
        if not matrix_path.is_file():
            continue
        rows.append(
            manifest_row_from_window_manifest(
                payload,
                manifest_path=manifest_path,
                matrix_path=matrix_path,
            )
        )
    if not rows:
        return rows
    df = pd.DataFrame(rows).drop_duplicates(subset=["matrix_path"], keep="last")
    return df.to_dict("records")


def write_layer25_export_manifest(
    rows: list[dict[str, Any]],
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    for col in CENTRAL_MANIFEST_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[CENTRAL_MANIFEST_COLUMNS]
    df.to_csv(output_path, index=False)
    return output_path


def central_manifest_path(review_root: Path | str) -> Path:
    return Path(review_root) / CENTRAL_MANIFEST_FILENAME


def load_layer25_export_manifest(path: Path | str) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        return pd.DataFrame(columns=CENTRAL_MANIFEST_COLUMNS)
    df = pd.read_csv(path)
    for col in CENTRAL_MANIFEST_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[CENTRAL_MANIFEST_COLUMNS]


def build_export_readiness_report(manifest_df: pd.DataFrame) -> pd.DataFrame:
    """Per participant/timepoint/repetition coverage of P1–P5 and combined_group4."""
    if manifest_df.empty:
        return pd.DataFrame(
            columns=[
                "participant_id",
                "timepoint",
                "repetition",
                "session_id",
                "combined_group4_present",
                "per_exercise_count",
                "missing_gaga_labels",
                "readiness_status",
                "readiness_message",
            ]
        )

    records: list[dict[str, Any]] = []
    group_cols = ["participant_id", "timepoint", "repetition", "session_id"]
    for key, group in manifest_df.groupby(group_cols, dropna=False):
        participant_id, timepoint, repetition, session_id = key
        labels = set(group["gaga_exercise_label"].astype(str).tolist())
        pe_rows = group[group["export_granularity"] == EXPORT_GRANULARITY_PER_EXERCISE]
        per_exercise = {
            label
            for label in pe_rows["gaga_exercise_label"].astype(str).tolist()
            if label in GAGA_EXERCISE_LABELS
        }
        combined_present = "combined_group4" in labels or (
            group["export_granularity"] == EXPORT_GRANULARITY_COMBINED
        ).any()
        missing = [label for label in GAGA_EXERCISE_LABELS if label not in per_exercise]
        qc_values = set(group["qc_status"].astype(str).str.lower().tolist())
        layer3_safe_vals = set(group["layer3_safe"].astype(str).str.lower().tolist())
        matrix_ok = group["matrix_path"].astype(str).str.len().gt(0).all()

        if "blocking" in qc_values or "false" in layer3_safe_vals or not matrix_ok:
            status = READINESS_BLOCKING
            message = "Blocking export/QC state or missing matrix path."
        elif missing:
            status = READINESS_WARNING
            message = f"Missing per-exercise exports: {', '.join(missing)}"
        elif "warning" in qc_values:
            status = READINESS_WARNING
            message = "Exports present with QC warning status."
        elif len(per_exercise) == len(GAGA_EXERCISE_LABELS):
            status = READINESS_PASS
            message = "All Gaga P1–P5 per-exercise exports present."
        else:
            status = READINESS_WARNING
            message = "Incomplete per-exercise coverage."

        records.append(
            {
                "participant_id": participant_id,
                "timepoint": timepoint,
                "repetition": repetition,
                "session_id": session_id,
                "combined_group4_present": bool(combined_present),
                "per_exercise_count": len(per_exercise),
                "missing_gaga_labels": ",".join(missing),
                "readiness_status": status,
                "readiness_message": message,
            }
        )
    return pd.DataFrame(records)


def build_field_readiness_report(manifest_df: pd.DataFrame) -> pd.DataFrame:
    """Required-field presence per export row."""
    if manifest_df.empty:
        return pd.DataFrame(columns=["field", "present_count", "missing_count", "all_present"])

    rows: list[dict[str, Any]] = []
    for field in CENTRAL_MANIFEST_COLUMNS:
        if field not in manifest_df.columns:
            missing = len(manifest_df)
            present = 0
        else:
            series = manifest_df[field]
            missing = int(series.isna().sum() + (series.astype(str).str.strip() == "").sum())
            present = len(manifest_df) - missing
        rows.append(
            {
                "field": field,
                "present_count": present,
                "missing_count": missing,
                "all_present": missing == 0,
            }
        )
    return pd.DataFrame(rows)


def write_export_readiness_artifacts(
    manifest_df: pd.DataFrame,
    output_dir: Path | str,
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    coverage = build_export_readiness_report(manifest_df)
    fields = build_field_readiness_report(manifest_df)
    coverage_path = out / "layer25_export_readiness_report.csv"
    fields_path = out / "layer25_export_readiness_fields.csv"
    coverage.to_csv(coverage_path, index=False)
    fields.to_csv(fields_path, index=False)
    return {"coverage": coverage_path, "fields": fields_path}


def export_attempts_report_path(review_root: Path | str) -> Path:
    return Path(review_root) / EXPORT_ATTEMPTS_REPORT_FILENAME


def session_coverage_report_path(review_root: Path | str) -> Path:
    return Path(review_root) / SESSION_COVERAGE_REPORT_FILENAME


def load_export_attempts_report(path: Path | str) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        return pd.DataFrame(columns=EXPORT_ATTEMPTS_COLUMNS)
    df = pd.read_csv(path)
    for col in EXPORT_ATTEMPTS_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[EXPORT_ATTEMPTS_COLUMNS]


def write_export_attempts_report(
    rows: list[dict[str, Any]],
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    for col in EXPORT_ATTEMPTS_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[EXPORT_ATTEMPTS_COLUMNS]
    df.to_csv(output_path, index=False)
    return output_path


def write_session_coverage_report(
    df: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in SESSION_COVERAGE_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    out = out[SESSION_COVERAGE_COLUMNS]
    out.to_csv(output_path, index=False)
    return output_path


def _session_identity_from_row(row: pd.Series) -> dict[str, str]:
    return {
        "participant_id": str(row.get("participant_id") or ""),
        "timepoint": str(row.get("timepoint") or ""),
        "repetition": str(row.get("repetition_id") or row.get("repetition") or ""),
        "session_id": str(row.get("session_id") or ""),
    }


def _manifest_labels_for_session(manifest_df: pd.DataFrame, session_id: str) -> set[str]:
    if manifest_df.empty or "session_id" not in manifest_df.columns:
        return set()
    group = manifest_df[manifest_df["session_id"].astype(str) == session_id]
    return set(group["gaga_exercise_label"].astype(str).tolist())


def _attempt_summary_for_session(
    attempts_df: pd.DataFrame,
    session_id: str,
) -> dict[str, Any]:
    if attempts_df.empty:
        return {
            "failed_labels": [],
            "skipped_labels": [],
            "exported_labels": [],
            "reason_code": "",
            "reason_message": "",
            "source_dependency": "",
            "warning_file": "",
        }
    group = attempts_df[attempts_df["session_id"].astype(str) == session_id]
    if group.empty:
        return {
            "failed_labels": [],
            "skipped_labels": [],
            "exported_labels": [],
            "reason_code": "",
            "reason_message": "",
            "source_dependency": "",
            "warning_file": "",
        }

    failed = group[group["status"] == ATTEMPT_STATUS_FAILED]
    skipped = group[group["status"] == ATTEMPT_STATUS_SKIPPED]
    exported = group[group["status"] == ATTEMPT_STATUS_EXPORTED]

    primary = failed.iloc[0] if not failed.empty else (skipped.iloc[0] if not skipped.empty else None)
    return {
        "failed_labels": failed["export_label"].astype(str).tolist(),
        "skipped_labels": skipped["export_label"].astype(str).tolist(),
        "exported_labels": exported["export_label"].astype(str).tolist(),
        "reason_code": str(primary["reason_code"]) if primary is not None else "",
        "reason_message": str(primary["reason_message"]) if primary is not None else "",
        "source_dependency": str(primary["source_dependency"]) if primary is not None else "",
        "warning_file": str(primary["warning_file"]) if primary is not None else "",
    }


def build_session_coverage_diff(
    *,
    session_index: pd.DataFrame,
    exercise_catalog: dict[str, Any],
    manifest_df: pd.DataFrame,
    attempts_df: pd.DataFrame | None = None,
    participant_ids: list[str] | None = None,
    project_root: Path | str | None = None,
) -> pd.DataFrame:
    """Compare expected sessions (index + segmentation) against manifest exports."""
    attempts_df = attempts_df if attempts_df is not None else pd.DataFrame(columns=EXPORT_ATTEMPTS_COLUMNS)
    if session_index.empty:
        return pd.DataFrame(columns=SESSION_COVERAGE_COLUMNS)

    participants = participant_ids or sorted(session_index["participant_id"].unique().tolist())
    matched = session_index[
        session_index["participant_id"].isin(participants) & session_index["is_matched"]
    ]

    records: list[dict[str, Any]] = []
    for _, row in matched.iterrows():
        identity = _session_identity_from_row(row)
        session_id = identity["session_id"]
        participant_id = identity["participant_id"]
        segments = exercise_catalog.get(session_id, [])
        in_catalog = bool(segments)
        labels = _manifest_labels_for_session(manifest_df, session_id)
        attempt_info = _attempt_summary_for_session(attempts_df, session_id)

        combined = "yes" if "combined_group4" in labels else "no"
        pe_cols = {
            label: ("yes" if label in labels else "no") for label in GAGA_EXERCISE_LABELS
        }
        manifest_count = int(
            manifest_df[manifest_df["session_id"].astype(str) == session_id].shape[0]
            if not manifest_df.empty
            else 0
        )

        if not in_catalog:
            session_status = SESSION_STATUS_SKIPPED
            seg_path = ""
            if project_root is not None:
                seg_path = str(
                    exercise_segments_path_for_participant(project_root, participant_id)
                )
            reason_code = "missing_exercise_segmentation"
            reason_message = (
                f"No exercise frame boundaries for {session_id} in segmentation catalog."
            )
            source_dependency = seg_path
            warning_file = ""
        elif manifest_count >= len(EXPECTED_EXPORT_LABELS):
            session_status = SESSION_STATUS_SUCCESSFUL
            reason_code = attempt_info["reason_code"]
            reason_message = (
                attempt_info["reason_message"]
                or "All expected Gaga export labels present in manifest."
            )
            source_dependency = attempt_info["source_dependency"]
            warning_file = attempt_info["warning_file"]
        elif manifest_count == 0 and attempt_info["failed_labels"]:
            session_status = SESSION_STATUS_FAILED
            reason_code = attempt_info["reason_code"] or "export_blocked"
            reason_message = attempt_info["reason_message"] or "Export blocked by warnings."
            source_dependency = attempt_info["source_dependency"]
            warning_file = attempt_info["warning_file"]
        elif manifest_count == 0:
            session_status = SESSION_STATUS_MISSING
            reason_code = attempt_info["reason_code"] or "not_in_manifest"
            reason_message = (
                attempt_info["reason_message"]
                or "Session expected from index/segmentation but absent from manifest."
            )
            source_dependency = attempt_info["source_dependency"]
            warning_file = attempt_info["warning_file"]
        else:
            session_status = SESSION_STATUS_PARTIAL
            missing_labels = [
                label
                for label in EXPECTED_EXPORT_LABELS
                if label not in labels
            ]
            reason_code = attempt_info["reason_code"] or "partial_export_coverage"
            reason_message = (
                attempt_info["reason_message"]
                or f"Manifest missing export labels: {', '.join(missing_labels)}"
            )
            source_dependency = attempt_info["source_dependency"]
            warning_file = attempt_info["warning_file"]

        records.append(
            {
                **identity,
                "session_status": session_status,
                "in_session_index": True,
                "in_segmentation_catalog": in_catalog,
                "manifest_export_count": manifest_count,
                "combined_group4": combined,
                **pe_cols,
                "reason_code": reason_code,
                "reason_message": reason_message,
                "source_dependency": source_dependency,
                "warning_file": warning_file,
            }
        )

    df = pd.DataFrame(records)
    for col in SESSION_COVERAGE_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[SESSION_COVERAGE_COLUMNS] if not df.empty else pd.DataFrame(columns=SESSION_COVERAGE_COLUMNS)
