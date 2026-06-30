"""Scan Layer 2.5 JcvPCA-ready exports and build a workbench data inventory."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from layer3_jcvpca.data_contract import (
    CENTRAL_MANIFEST_NAME,
    EXPORT_GRANULARITY_COMBINED,
    EXPORT_GRANULARITY_PER_EXERCISE,
    GAGA_EXERCISE_LABELS,
    INVENTORY_COLUMNS,
    ISSUE_SEVERITY_INFO,
    ISSUE_SEVERITY_WARNING,
    InventoryIssue,
    InventoryRow,
    MATRIX_FILE_NAMES,
    MATRIX_MANIFEST_NAME,
    derive_qc_status,
    exercise_metadata_from_manifest,
    is_per_exercise_export,
    parse_session_key,
)
from layer3_jcvpca.io import infer_feature_columns, load_matrix


@dataclass
class DataInventory:
    root_dir: str
    scanned_at: str
    rows: list[InventoryRow] = field(default_factory=list)
    issues: list[InventoryIssue] = field(default_factory=list)
    manifest_files_found: int = 0
    matrix_files_found: int = 0

    def to_dataframe(self) -> pd.DataFrame:
        records = [row.to_dict() for row in self.rows]
        df = pd.DataFrame(records)
        for col in INVENTORY_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        extra = [c for c in df.columns if c not in INVENTORY_COLUMNS]
        return df[INVENTORY_COLUMNS + extra] if not df.empty else pd.DataFrame(columns=INVENTORY_COLUMNS)

    def issues_dataframe(self) -> pd.DataFrame:
        if not self.issues:
            return pd.DataFrame(
                columns=[
                    "issue_code",
                    "severity",
                    "message",
                    "matrix_path",
                    "manifest_path",
                    "session_id",
                    "field",
                ]
            )
        return pd.DataFrame([issue.__dict__ for issue in self.issues])

    def summary(self) -> dict[str, Any]:
        df = self.to_dataframe()
        per_exercise = sum(1 for row in self.rows if is_per_exercise_export(row))
        return {
            "root_dir": self.root_dir,
            "scanned_at": self.scanned_at,
            "n_inventory_rows": len(self.rows),
            "n_issues": len(self.issues),
            "participants": sorted(df["participant_id"].dropna().unique().tolist())
            if not df.empty
            else [],
            "timepoints": sorted(df["timepoint"].dropna().unique().tolist()) if not df.empty else [],
            "repetitions": sorted(df["repetition"].dropna().unique().tolist()) if not df.empty else [],
            "gaga_exercises_found": sorted(
                e
                for e in df["gaga_exercise_label"].dropna().unique().tolist()
                if e in GAGA_EXERCISE_LABELS
            )
            if not df.empty
            else [],
            "per_exercise_export_count": per_exercise,
            "combined_group4_count": sum(
                1 for row in self.rows if row.export_granularity == EXPORT_GRANULARITY_COMBINED
            ),
            "manifest_files_found": self.manifest_files_found,
            "matrix_files_found": self.matrix_files_found,
        }


def default_layer25_root(repo_root: Path) -> Path:
    return repo_root / "Layer2.5_Segmentation" / "outputs" / "pre_jvcpca_review"


def scan_layer25_exports(
    root_dir: str | Path,
    *,
    load_matrix_stats: bool = True,
) -> DataInventory:
    """Discover Layer 2.5 matrix exports under ``root_dir``."""
    root = Path(root_dir).resolve()
    inventory = DataInventory(
        root_dir=str(root),
        scanned_at=datetime.now(timezone.utc).isoformat(),
    )

    if not root.is_dir():
        inventory.issues.append(
            InventoryIssue(
                issue_code="missing_scan_root",
                severity=ISSUE_SEVERITY_WARNING,
                message=f"Scan root does not exist: {root}",
                field="root_dir",
            )
        )
        return inventory

    central_path = root / CENTRAL_MANIFEST_NAME
    if central_path.is_file():
        return _scan_from_central_manifest(
            root,
            central_path,
            inventory=inventory,
            load_matrix_stats=load_matrix_stats,
        )

    manifest_paths = sorted(root.rglob(MATRIX_MANIFEST_NAME))
    inventory.manifest_files_found = len(manifest_paths)
    seen_matrix_paths: set[str] = set()

    for manifest_path in manifest_paths:
        row, row_issues = _inventory_row_from_manifest(
            manifest_path,
            load_matrix_stats=load_matrix_stats,
        )
        inventory.rows.append(row)
        inventory.issues.extend(row_issues)
        if row.matrix_path:
            seen_matrix_paths.add(str(Path(row.matrix_path).resolve()))

    orphan_matrices = _find_orphan_matrices(root, seen_matrix_paths)
    inventory.matrix_files_found = len(seen_matrix_paths) + len(orphan_matrices)
    for matrix_path in orphan_matrices:
        row, row_issues = _inventory_row_from_orphan_matrix(
            matrix_path,
            load_matrix_stats=load_matrix_stats,
        )
        inventory.rows.append(row)
        inventory.issues.extend(row_issues)

    inventory.rows.sort(
        key=lambda r: (
            r.participant_id,
            r.timepoint,
            r.repetition,
            r.gaga_exercise_label or "ZZZ",
            r.session_id,
        )
    )
    return inventory


def write_inventory_artifacts(
    inventory: DataInventory,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write inventory CSV/JSON artifacts for audit."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    inv_csv = out / "layer25_data_inventory.csv"
    issues_csv = out / "layer25_data_inventory_issues.csv"
    summary_json = out / "layer25_data_inventory_summary.json"

    inventory.to_dataframe().to_csv(inv_csv, index=False)
    inventory.issues_dataframe().to_csv(issues_csv, index=False)
    payload = inventory.summary()
    issues_df = inventory.issues_dataframe()
    payload["issues_by_code"] = (
        issues_df["issue_code"].value_counts().to_dict() if not issues_df.empty else {}
    )
    summary_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "inventory_csv": inv_csv,
        "issues_csv": issues_csv,
        "summary_json": summary_json,
    }


def _find_orphan_matrices(root: Path, seen: set[str]) -> list[Path]:
    orphans: list[Path] = []
    for name in MATRIX_FILE_NAMES:
        for path in root.rglob(name):
            resolved = str(path.resolve())
            if resolved not in seen:
                orphans.append(path)
    return sorted(set(orphans))


def _inventory_row_from_manifest(
    manifest_path: Path,
    *,
    load_matrix_stats: bool,
) -> tuple[InventoryRow, list[InventoryIssue]]:
    issues: list[InventoryIssue] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(
            InventoryIssue(
                issue_code="invalid_manifest",
                severity=ISSUE_SEVERITY_WARNING,
                message=f"Could not read manifest: {exc}",
                manifest_path=str(manifest_path),
            )
        )
        return InventoryRow(manifest_path=str(manifest_path)), issues

    matrix_path = _resolve_matrix_path(manifest_path.parent, manifest)
    identity = manifest.get("identity") or {}
    session_id = str(manifest.get("session_id") or identity.get("session_id") or "")
    parsed = parse_session_key(session_id)

    participant_id = str(
        manifest.get("selected_participant")
        or identity.get("participant_id")
        or parsed.get("participant_id")
        or ""
    )
    timepoint = str(identity.get("timepoint") or parsed.get("timepoint") or "")
    repetition = str(identity.get("repetition_id") or parsed.get("repetition") or "")
    task_part_id = str(identity.get("part_id") or parsed.get("task_part_id") or "")

    if not participant_id:
        issues.append(
            InventoryIssue(
                issue_code="missing_participant_id",
                severity=ISSUE_SEVERITY_WARNING,
                message="participant_id not found in manifest or session_id",
                manifest_path=str(manifest_path),
                session_id=session_id,
                field="participant_id",
            )
        )
    if not timepoint:
        issues.append(
            InventoryIssue(
                issue_code="missing_timepoint",
                severity=ISSUE_SEVERITY_WARNING,
                message="timepoint not found in manifest identity",
                manifest_path=str(manifest_path),
                session_id=session_id,
                field="timepoint",
            )
        )
    if not repetition:
        issues.append(
            InventoryIssue(
                issue_code="missing_repetition",
                severity=ISSUE_SEVERITY_WARNING,
                message="repetition not found in manifest identity",
                manifest_path=str(manifest_path),
                session_id=session_id,
                field="repetition",
            )
        )

    gaga_ex_id, gaga_label, export_granularity, meta_notes = exercise_metadata_from_manifest(
        manifest
    )
    explicit_granularity = bool(str(manifest.get("export_granularity") or "").strip())
    explicit_mode = bool(str(manifest.get("export_mode") or "").strip())
    explicit_label = bool(
        str(manifest.get("gaga_exercise_label") or manifest.get("exercise") or "").strip()
    )

    if not explicit_granularity and not explicit_mode:
        issues.append(
            InventoryIssue(
                issue_code="missing_export_granularity",
                severity=ISSUE_SEVERITY_WARNING,
                message=(
                    "export_granularity not explicit in manifest "
                    f"(inferred={export_granularity or 'unknown'})"
                ),
                manifest_path=str(manifest_path),
                session_id=session_id,
                field="export_granularity",
            )
        )
    if not gaga_label:
        issues.append(
            InventoryIssue(
                issue_code="missing_gaga_exercise_label",
                severity=ISSUE_SEVERITY_WARNING,
                message="gaga_exercise_label not present (P1–P5 or combined_group4)",
                manifest_path=str(manifest_path),
                matrix_path=str(matrix_path) if matrix_path else "",
                session_id=session_id,
                field="gaga_exercise_label",
            )
        )
    elif not explicit_label:
        issues.append(
            InventoryIssue(
                issue_code="inferred_gaga_exercise_label",
                severity=ISSUE_SEVERITY_INFO,
                message=f"gaga_exercise_label inferred as '{gaga_label}' (not explicit in manifest)",
                manifest_path=str(manifest_path),
                session_id=session_id,
                field="gaga_exercise_label",
            )
        )
    if export_granularity == EXPORT_GRANULARITY_COMBINED:
        issues.append(
            InventoryIssue(
                issue_code="combined_group4_only",
                severity=ISSUE_SEVERITY_WARNING,
                message=(
                    "Export is combined_group4 only. Workbench exercise presets require "
                    "per_exercise P1–P5 matrices (Phase 2)."
                ),
                manifest_path=str(manifest_path),
                session_id=session_id,
                field="export_granularity",
            )
        )
    elif export_granularity == EXPORT_GRANULARITY_PER_EXERCISE and gaga_label not in GAGA_EXERCISE_LABELS:
        issues.append(
            InventoryIssue(
                issue_code="missing_per_exercise_label",
                severity=ISSUE_SEVERITY_WARNING,
                message="export_granularity=per_exercise but gaga_exercise_label is not P1–P5",
                manifest_path=str(manifest_path),
                session_id=session_id,
                field="gaga_exercise_label",
            )
        )

    layer3_safe_raw = manifest.get("layer3_safe")
    if layer3_safe_raw is None:
        layer3_safe = "unknown"
        issues.append(
            InventoryIssue(
                issue_code="missing_layer3_safe",
                severity=ISSUE_SEVERITY_WARNING,
                message="layer3_safe flag missing from export manifest",
                manifest_path=str(manifest_path),
                session_id=session_id,
                field="layer3_safe",
            )
        )
    else:
        layer3_safe = str(bool(layer3_safe_raw)).lower()

    qc_status, qc_inferred = derive_qc_status(manifest)
    if qc_status == "unknown":
        issues.append(
            InventoryIssue(
                issue_code="missing_qc_status",
                severity=ISSUE_SEVERITY_WARNING,
                message="qc_status not present and warnings_summary unavailable",
                manifest_path=str(manifest_path),
                session_id=session_id,
                field="qc_status",
            )
        )
    elif qc_inferred:
        issues.append(
            InventoryIssue(
                issue_code="inferred_qc_status",
                severity=ISSUE_SEVERITY_INFO,
                message=(
                    f"qc_status inferred from warnings_summary as '{qc_status}' "
                    "(not explicit in manifest)"
                ),
                manifest_path=str(manifest_path),
                session_id=session_id,
                field="qc_status",
            )
        )

    if matrix_path is None or not matrix_path.is_file():
        issues.append(
            InventoryIssue(
                issue_code="missing_matrix_path",
                severity=ISSUE_SEVERITY_WARNING,
                message="JcvPCA matrix file referenced by manifest not found on disk",
                manifest_path=str(manifest_path),
                session_id=session_id,
                field="matrix_path",
            )
        )

    n_frames = manifest.get("n_frames") or manifest.get("jvcpca_matrix_row_count")
    n_features = manifest.get("n_features") or manifest.get("jvcpca_matrix_column_count")
    try:
        n_frames = int(n_frames) if n_frames is not None else None
    except (TypeError, ValueError):
        n_frames = None
    try:
        n_features = int(n_features) if n_features is not None else None
    except (TypeError, ValueError):
        n_features = None

    if load_matrix_stats and matrix_path is not None and matrix_path.is_file():
        try:
            df = load_matrix(matrix_path)
            n_frames = len(df)
            n_features = len(infer_feature_columns(df))
        except Exception as exc:
            issues.append(
                InventoryIssue(
                    issue_code="matrix_load_failed",
                    severity=ISSUE_SEVERITY_WARNING,
                    message=f"Could not load matrix for stats: {exc}",
                    manifest_path=str(manifest_path),
                    matrix_path=str(matrix_path),
                    session_id=session_id,
                )
            )

    notes_parts = [p for p in [meta_notes] if p]
    if qc_inferred:
        notes_parts.append("qc_status_inferred")

    export_mode = str(manifest.get("export_mode") or export_granularity or "")
    feature_schema_id = str(
        manifest.get("feature_schema_id")
        or manifest.get("feature_hash")
        or manifest.get("marker_set_id")
        or identity.get("marker_set_id")
        or ""
    )

    row = InventoryRow(
        participant_id=participant_id,
        timepoint=timepoint,
        repetition=repetition,
        task_part_id=task_part_id,
        session_id=session_id,
        run_label=str(manifest.get("run_label") or ""),
        gaga_exercise_id=gaga_ex_id,
        gaga_exercise_label=gaga_label,
        export_granularity=export_granularity,
        export_mode=export_mode,
        matrix_path=str(matrix_path) if matrix_path else "",
        manifest_path=str(manifest_path),
        layer3_safe=layer3_safe,
        qc_status=qc_status,
        n_frames=n_frames,
        n_features=n_features,
        feature_schema_id=feature_schema_id,
        created_at=str(manifest.get("created_at") or ""),
        notes="; ".join(notes_parts),
        issues=issues,
    )
    return row, issues


def _inventory_row_from_orphan_matrix(
    matrix_path: Path,
    *,
    load_matrix_stats: bool,
) -> tuple[InventoryRow, list[InventoryIssue]]:
    issues: list[InventoryIssue] = [
        InventoryIssue(
            issue_code="missing_manifest",
            severity=ISSUE_SEVERITY_WARNING,
            message="Matrix file found without window_export_manifest.json",
            matrix_path=str(matrix_path),
            field="manifest_path",
        )
    ]
    session_id = ""
    n_frames = None
    n_features = None
    if load_matrix_stats:
        try:
            df = load_matrix(matrix_path)
            n_frames = len(df)
            n_features = len(infer_feature_columns(df))
            if "session_id" in df.columns and len(df):
                session_id = str(df["session_id"].iloc[0])
        except Exception as exc:
            issues.append(
                InventoryIssue(
                    issue_code="matrix_load_failed",
                    severity=ISSUE_SEVERITY_WARNING,
                    message=f"Could not load orphan matrix: {exc}",
                    matrix_path=str(matrix_path),
                )
            )

    parsed = parse_session_key(session_id)
    row = InventoryRow(
        participant_id=parsed.get("participant_id", ""),
        timepoint=parsed.get("timepoint", ""),
        repetition=parsed.get("repetition", ""),
        task_part_id=parsed.get("task_part_id", ""),
        matrix_path=str(matrix_path),
        session_id=session_id,
        n_frames=n_frames,
        n_features=n_features,
        notes="orphan_matrix_no_manifest",
        issues=issues,
    )
    issues.extend(
        [
            InventoryIssue(
                issue_code="missing_gaga_exercise_label",
                severity=ISSUE_SEVERITY_WARNING,
                message="gaga_exercise_label unavailable (no manifest)",
                matrix_path=str(matrix_path),
                session_id=session_id,
                field="gaga_exercise_label",
            ),
            InventoryIssue(
                issue_code="missing_export_granularity",
                severity=ISSUE_SEVERITY_WARNING,
                message="export_granularity unavailable (no manifest)",
                matrix_path=str(matrix_path),
                session_id=session_id,
                field="export_granularity",
            ),
        ]
    )
    return row, issues


def _resolve_matrix_path(manifest_dir: Path, manifest: dict[str, Any]) -> Path | None:
    rel = manifest.get("jvcpca_matrix_file") or MATRIX_FILE_NAMES[0]
    candidate = manifest_dir / str(rel)
    if candidate.is_file():
        return candidate
    for name in MATRIX_FILE_NAMES:
        alt = manifest_dir / name
        if alt.is_file():
            return alt
    return candidate if candidate.exists() else None


def _scan_from_central_manifest(
    root: Path,
    central_path: Path,
    *,
    inventory: DataInventory,
    load_matrix_stats: bool,
) -> DataInventory:
    """Build inventory from centralized layer25_export_manifest.csv."""
    try:
        df = pd.read_csv(central_path)
    except (OSError, pd.errors.ParserError) as exc:
        inventory.issues.append(
            InventoryIssue(
                issue_code="invalid_central_manifest",
                severity=ISSUE_SEVERITY_WARNING,
                message=f"Could not read central manifest: {exc}",
                manifest_path=str(central_path),
                field="layer25_export_manifest.csv",
            )
        )
        return inventory

    inventory.manifest_files_found = len(list(root.rglob(MATRIX_MANIFEST_NAME)))
    seen_matrix_paths: set[str] = set()

    for _, record in df.iterrows():
        row, row_issues = _inventory_row_from_central_record(
            record,
            central_manifest_path=str(central_path),
            load_matrix_stats=load_matrix_stats,
        )
        inventory.rows.append(row)
        inventory.issues.extend(row_issues)
        if row.matrix_path:
            seen_matrix_paths.add(str(Path(row.matrix_path).resolve()))

    orphan_matrices = _find_orphan_matrices(root, seen_matrix_paths)
    inventory.matrix_files_found = len(seen_matrix_paths) + len(orphan_matrices)
    for matrix_path in orphan_matrices:
        row, row_issues = _inventory_row_from_orphan_matrix(
            matrix_path,
            load_matrix_stats=load_matrix_stats,
        )
        inventory.rows.append(row)
        inventory.issues.extend(row_issues)

    inventory.rows.sort(
        key=lambda r: (
            r.participant_id,
            r.timepoint,
            r.repetition,
            r.gaga_exercise_label or "ZZZ",
            r.session_id,
        )
    )
    return inventory


def _inventory_row_from_central_record(
    record: pd.Series,
    *,
    central_manifest_path: str,
    load_matrix_stats: bool,
) -> tuple[InventoryRow, list[InventoryIssue]]:
    issues: list[InventoryIssue] = []
    session_id = str(record.get("session_id") or "")

    participant_id = str(record.get("participant_id") or "")
    timepoint = str(record.get("timepoint") or "")
    repetition = str(record.get("repetition") or "")
    task_part_id = str(record.get("task_part_id") or "")
    gaga_label = str(record.get("gaga_exercise_label") or "")
    export_granularity = str(record.get("export_granularity") or "")
    export_mode = str(record.get("export_mode") or export_granularity or "")
    matrix_path_raw = str(record.get("matrix_path") or "")
    manifest_path_raw = str(record.get("manifest_path") or "")
    layer3_safe = str(record.get("layer3_safe") or "unknown").lower()
    qc_status = str(record.get("qc_status") or "unknown").lower()

    if not participant_id:
        issues.append(
            InventoryIssue(
                issue_code="missing_participant_id",
                severity=ISSUE_SEVERITY_WARNING,
                message="participant_id missing in central manifest row",
                manifest_path=central_manifest_path,
                session_id=session_id,
                field="participant_id",
            )
        )
    if not gaga_label:
        issues.append(
            InventoryIssue(
                issue_code="missing_gaga_exercise_label",
                severity=ISSUE_SEVERITY_WARNING,
                message="gaga_exercise_label missing in central manifest row",
                manifest_path=central_manifest_path,
                session_id=session_id,
                field="gaga_exercise_label",
            )
        )
    if not export_granularity:
        issues.append(
            InventoryIssue(
                issue_code="missing_export_granularity",
                severity=ISSUE_SEVERITY_WARNING,
                message="export_granularity missing in central manifest row",
                manifest_path=central_manifest_path,
                session_id=session_id,
                field="export_granularity",
            )
        )
    if export_granularity == EXPORT_GRANULARITY_COMBINED:
        issues.append(
            InventoryIssue(
                issue_code="combined_group4_only",
                severity=ISSUE_SEVERITY_WARNING,
                message=(
                    "Export is combined_group4 only. Workbench exercise presets require "
                    "per_exercise P1–P5 matrices (Phase 2)."
                ),
                manifest_path=manifest_path_raw or central_manifest_path,
                session_id=session_id,
                field="export_granularity",
            )
        )

    matrix_path: Path | None = None
    if matrix_path_raw:
        matrix_path = Path(matrix_path_raw)
        if not matrix_path.is_file():
            issues.append(
                InventoryIssue(
                    issue_code="missing_matrix_path",
                    severity=ISSUE_SEVERITY_WARNING,
                    message="Matrix path from central manifest not found on disk",
                    manifest_path=manifest_path_raw or central_manifest_path,
                    matrix_path=matrix_path_raw,
                    session_id=session_id,
                    field="matrix_path",
                )
            )

    n_frames = record.get("n_frames")
    n_features = record.get("n_features")
    try:
        n_frames = int(n_frames) if pd.notna(n_frames) else None
    except (TypeError, ValueError):
        n_frames = None
    try:
        n_features = int(n_features) if pd.notna(n_features) else None
    except (TypeError, ValueError):
        n_features = None

    if load_matrix_stats and matrix_path is not None and matrix_path.is_file():
        try:
            df = load_matrix(matrix_path)
            n_frames = len(df)
            n_features = len(infer_feature_columns(df))
        except Exception as exc:
            issues.append(
                InventoryIssue(
                    issue_code="matrix_load_failed",
                    severity=ISSUE_SEVERITY_WARNING,
                    message=f"Could not load matrix for stats: {exc}",
                    manifest_path=manifest_path_raw or central_manifest_path,
                    matrix_path=str(matrix_path),
                    session_id=session_id,
                )
            )

    row = InventoryRow(
        participant_id=participant_id,
        timepoint=timepoint,
        repetition=repetition,
        task_part_id=task_part_id,
        session_id=session_id,
        run_label=str(record.get("run_label") or ""),
        gaga_exercise_id=str(record.get("gaga_exercise_id") or ""),
        gaga_exercise_label=gaga_label,
        export_granularity=export_granularity,
        export_mode=export_mode,
        matrix_path=matrix_path_raw,
        manifest_path=manifest_path_raw,
        layer3_safe=layer3_safe,
        qc_status=qc_status,
        n_frames=n_frames,
        n_features=n_features,
        feature_schema_id=str(record.get("feature_schema_id") or ""),
        created_at=str(record.get("created_at") or ""),
        notes="central_manifest",
        issues=issues,
    )
    return row, issues
