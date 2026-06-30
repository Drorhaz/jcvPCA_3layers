"""Layer 2.5 → Layer 3 data contract definitions for the Gaga workbench.

Defines canonical inventory columns, issue codes, and exercise label mapping.
Does not invent missing metadata — callers surface gaps via structured issues.

Out of scope (not tracked): time-normalization, DTW, padding, duration equalization,
or any time-manipulation provenance fields. Layer 2.5 does not perform those ops.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Centralized Layer 2.5 export manifest / inventory columns (Phase 2 target).
INVENTORY_COLUMNS: list[str] = [
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
    "notes",
]

GAGA_EXERCISE_ID_TO_LABEL: dict[int, str] = {
    9: "P1",
    10: "P2",
    11: "P3",
    12: "P4",
    13: "P5",
}

GAGA_EXERCISE_LABELS: tuple[str, ...] = ("P1", "P2", "P3", "P4", "P5")
EXPORT_GRANULARITY_PER_EXERCISE = "per_exercise"
EXPORT_GRANULARITY_COMBINED = "combined_group4"
EXPORT_GRANULARITY_VALUES: tuple[str, ...] = (
    EXPORT_GRANULARITY_PER_EXERCISE,
    EXPORT_GRANULARITY_COMBINED,
)

SESSION_KEY_RE = re.compile(
    r"(?P<participant>\d+)_T(?P<timepoint>\d+)_P(?P<part>\d+)_R(?P<rep>\d+)"
)

MATRIX_MANIFEST_NAME = "window_export_manifest.json"
CENTRAL_MANIFEST_NAME = "layer25_export_manifest.csv"
MATRIX_FILE_NAMES = ("window_jvcpca_matrix.parquet", "window_jvcpca_matrix.csv")

REQUIRED_METADATA_COLUMNS = ("session_id", "run_label", "frame", "time_sec")

ISSUE_SEVERITY_BLOCKING = "blocking"
ISSUE_SEVERITY_WARNING = "warning"
ISSUE_SEVERITY_INFO = "info"


@dataclass(frozen=True)
class InventoryIssue:
    issue_code: str
    severity: str
    message: str
    matrix_path: str = ""
    manifest_path: str = ""
    session_id: str = ""
    field: str = ""


@dataclass
class InventoryRow:
    participant_id: str = ""
    timepoint: str = ""
    repetition: str = ""
    task_part_id: str = ""
    session_id: str = ""
    run_label: str = ""
    gaga_exercise_id: str = ""
    gaga_exercise_label: str = ""
    export_granularity: str = ""
    export_mode: str = ""
    matrix_path: str = ""
    manifest_path: str = ""
    layer3_safe: str = "unknown"
    qc_status: str = "unknown"
    n_frames: int | None = None
    n_features: int | None = None
    feature_schema_id: str = ""
    created_at: str = ""
    notes: str = ""
    issues: list[InventoryIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "participant_id": self.participant_id,
            "timepoint": self.timepoint,
            "repetition": self.repetition,
            "task_part_id": self.task_part_id,
            "session_id": self.session_id,
            "run_label": self.run_label,
            "gaga_exercise_id": self.gaga_exercise_id,
            "gaga_exercise_label": self.gaga_exercise_label,
            "export_granularity": self.export_granularity,
            "export_mode": self.export_mode,
            "matrix_path": self.matrix_path,
            "manifest_path": self.manifest_path,
            "layer3_safe": self.layer3_safe,
            "qc_status": self.qc_status,
            "n_frames": self.n_frames,
            "n_features": self.n_features,
            "feature_schema_id": self.feature_schema_id,
            "created_at": self.created_at,
            "notes": self.notes,
        }


def parse_session_key(session_id: str) -> dict[str, str]:
    """Parse ``671_T1_P1_R1`` into participant / timepoint / task part / repetition."""
    m = SESSION_KEY_RE.match(str(session_id).strip())
    if not m:
        return {}
    return {
        "participant_id": m.group("participant"),
        "timepoint": f"T{m.group('timepoint')}",
        "task_part_id": f"P{m.group('part')}",
        "repetition": f"R{m.group('rep')}",
    }


def exercise_metadata_from_manifest(manifest: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return (gaga_exercise_id, gaga_exercise_label, export_granularity, notes)."""
    notes: list[str] = []

    granularity = str(manifest.get("export_granularity") or "").strip().lower()
    export_mode = str(manifest.get("export_mode") or "").strip().lower()
    if not granularity and export_mode in EXPORT_GRANULARITY_VALUES:
        granularity = export_mode
        notes.append("export_granularity_from_export_mode")

    gaga_label = ""
    for key in ("gaga_exercise_label", "exercise"):
        raw = manifest.get(key)
        if raw is not None and str(raw).strip():
            text = str(raw).strip()
            upper = text.upper()
            if upper in GAGA_EXERCISE_LABELS:
                gaga_label = upper
                notes.append(f"from_manifest_{key}")
                break
            if upper == "COMBINED_GROUP4" or text.lower() == "combined_group4":
                gaga_label = "combined_group4"
                notes.append(f"from_manifest_{key}")
                break

    gaga_ex_id = manifest.get("gaga_exercise_id") or manifest.get("exercise_id")
    gaga_ex_id_str = str(gaga_ex_id) if gaga_ex_id is not None else ""
    if not gaga_label and gaga_ex_id is not None:
        try:
            mapped = GAGA_EXERCISE_ID_TO_LABEL.get(int(gaga_ex_id))
            if mapped:
                gaga_label = mapped
                notes.append("from_manifest_gaga_exercise_id")
        except (TypeError, ValueError):
            pass

    if not granularity:
        window_label = str(manifest.get("window_label", "")).lower()
        if "g4" in window_label or manifest.get("exercise_scope") == "group4_combined":
            granularity = EXPORT_GRANULARITY_COMBINED
            if not gaga_label:
                gaga_label = "combined_group4"
            notes.append("inferred_combined_group4_from_window_label")

    if granularity == EXPORT_GRANULARITY_COMBINED and not gaga_label:
        gaga_label = "combined_group4"

    return gaga_ex_id_str, gaga_label, granularity, "; ".join(notes)


def derive_qc_status(manifest: dict[str, Any]) -> tuple[str, bool]:
    """Return (qc_status, was_inferred)."""
    explicit = manifest.get("qc_status")
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip().lower(), False

    ws = manifest.get("warnings_summary") or {}
    if not ws:
        return "unknown", False

    if ws.get("has_blocking") or int(ws.get("n_blocking", 0)) > 0:
        return "blocking", True
    if int(ws.get("n_strong_warning", 0)) > 0 or int(ws.get("n_warning", 0)) > 0:
        return "warning", True
    return "pass", True


def is_per_exercise_export(row: InventoryRow) -> bool:
    return (
        row.export_granularity == EXPORT_GRANULARITY_PER_EXERCISE
        and row.gaga_exercise_label in GAGA_EXERCISE_LABELS
    )
