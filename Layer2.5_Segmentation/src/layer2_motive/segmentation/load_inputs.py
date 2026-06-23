"""Load Layer 1 QC and Layer 2 export folders (read-only)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from layer2_motive.segmentation.schemas import (
    LAYER1_OPTIONAL_FILES,
    LAYER1_REQUIRED_FILES,
    LAYER2_OPTIONAL_FILES,
    LAYER2_REQUIRED_FILES,
    Layer1Bundle,
    Layer2Bundle,
)


class InputLoadError(Exception):
    """Raised when required input files are missing or unreadable."""


def _resolve_dir(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise InputLoadError(f"Directory not found: {resolved}")
    return resolved


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _read_optional_csv(path: Path, name: str, warnings: list[str]) -> pd.DataFrame | None:
    if not path.exists():
        warnings.append(f"Optional file not found (skipped): {name}")
        return None
    df = _read_csv(path)
    if df.empty:
        warnings.append(f"Optional file is empty (skipped): {name}")
        return None
    return df


def load_layer1_qc_folder(path: str | Path) -> Layer1Bundle:
    """Load Layer 1 QC folder. Required files raise; optional files warn."""
    source_dir = _resolve_dir(path)
    warnings: list[str] = []
    source_paths: dict[str, Path] = {}

    for name in LAYER1_REQUIRED_FILES:
        file_path = source_dir / name
        if not file_path.exists():
            raise InputLoadError(f"Required Layer 1 file missing: {name}")
        source_paths[name] = file_path

    with source_paths["layer1_segmentation_notebook_manifest.json"].open(encoding="utf-8") as fh:
        manifest = json.load(fh)

    qc_mask = _read_csv(source_paths["qc_mask.csv"])

    qc_mask_intervals = _read_optional_csv(
        source_dir / "qc_mask_intervals.csv", "qc_mask_intervals.csv", warnings
    )
    artifact_events = _read_optional_csv(
        source_dir / "artifact_events.csv", "artifact_events.csv", warnings
    )
    artifacts_by_segment = _read_optional_csv(
        source_dir / "artifacts_by_segment.csv", "artifacts_by_segment.csv", warnings
    )
    gaps_over_0p2s = _read_optional_csv(
        source_dir / "gaps_over_0p2s.csv", "gaps_over_0p2s.csv", warnings
    )
    gaps_over_0p5s = _read_optional_csv(
        source_dir / "gaps_over_0p5s.csv", "gaps_over_0p5s.csv", warnings
    )
    quarantined_markers = _read_optional_csv(
        source_dir / "quarantined_markers.csv", "quarantined_markers.csv", warnings
    )

    for name in LAYER1_OPTIONAL_FILES:
        p = source_dir / name
        if p.exists():
            source_paths[name] = p

    return Layer1Bundle(
        source_dir=source_dir,
        manifest=manifest,
        qc_mask=qc_mask,
        qc_mask_intervals=qc_mask_intervals,
        artifact_events=artifact_events,
        artifacts_by_segment=artifacts_by_segment,
        gaps_over_0p2s=gaps_over_0p2s,
        gaps_over_0p5s=gaps_over_0p5s,
        quarantined_markers=quarantined_markers,
        warnings=warnings,
        source_paths=source_paths,
    )


def load_layer2_export_folder(path: str | Path) -> Layer2Bundle:
    """Load Layer 2 per-session export folder. Required files raise; optional files warn."""
    source_dir = _resolve_dir(path)
    warnings: list[str] = []
    source_paths: dict[str, Path] = {}

    for name in LAYER2_REQUIRED_FILES:
        file_path = source_dir / name
        if not file_path.exists():
            raise InputLoadError(f"Required Layer 2 file missing: {name}")
        source_paths[name] = file_path

    with source_paths["layer2_session_summary.json"].open(encoding="utf-8") as fh:
        summary = json.load(fh)

    parquet_df = pd.read_parquet(source_paths["layer2_session_filtered_rotvecs.parquet"])
    link_manifest = _read_csv(source_paths["layer2_session_link_manifest.csv"])

    integrity_audit = _read_optional_csv(
        source_dir / "layer2_session_integrity_audit.csv",
        "layer2_session_integrity_audit.csv",
        warnings,
    )

    for name in LAYER2_OPTIONAL_FILES:
        p = source_dir / name
        if p.exists():
            source_paths[name] = p

    return Layer2Bundle(
        source_dir=source_dir,
        summary=summary,
        parquet_df=parquet_df,
        link_manifest=link_manifest,
        integrity_audit=integrity_audit,
        warnings=warnings,
        source_paths=source_paths,
    )
