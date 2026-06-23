"""Resolve input files from Layer 1 / Layer 2 folders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Layer1Paths:
    dir: Path
    manifest: Path
    qc_mask: Path
    gaps_over_0p2s: Path | None
    gaps_over_0p5s: Path | None
    artifact_events: Path | None
    qc_mask_intervals: Path | None


@dataclass(frozen=True)
class Layer2Paths:
    dir: Path
    rotvecs_parquet: Path
    link_manifest: Path
    session_summary: Path


def _first_existing(folder: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = folder / name
        if path.is_file():
            return path
    return None


def _require(folder: Path, names: tuple[str, ...], label: str) -> Path:
    path = _first_existing(folder, names)
    if path is None:
        expected = ", ".join(names)
        raise FileNotFoundError(f"Missing {label} in {folder} (expected one of: {expected})")
    return path


def resolve_layer1(layer1_dir: Path) -> Layer1Paths:
    folder = Path(layer1_dir).resolve()
    if not folder.is_dir():
        raise NotADirectoryError(f"Layer 1 folder not found: {folder}")
    return Layer1Paths(
        dir=folder,
        manifest=_require(folder, ("layer1_segmentation_notebook_manifest.json",), "manifest"),
        qc_mask=_require(folder, ("qc_mask.csv",), "qc_mask.csv"),
        gaps_over_0p2s=_first_existing(folder, ("gaps_over_0p2s.csv",)),
        gaps_over_0p5s=_first_existing(folder, ("gaps_over_0p5s.csv",)),
        artifact_events=_first_existing(folder, ("artifact_events.csv",)),
        qc_mask_intervals=_first_existing(folder, ("qc_mask_intervals.csv",)),
    )


def resolve_layer2(layer2_dir: Path) -> Layer2Paths:
    folder = Path(layer2_dir).resolve()
    if not folder.is_dir():
        raise NotADirectoryError(f"Layer 2 folder not found: {folder}")
    return Layer2Paths(
        dir=folder,
        rotvecs_parquet=_require(
            folder,
            (
                "layer2_session_filtered_rotvecs.parquet",
                "filtered_relative_rotation_vectors.parquet",
            ),
            "rotvecs parquet",
        ),
        link_manifest=_require(
            folder,
            ("layer2_session_link_manifest.csv", "layer2_qc_link_manifest.csv"),
            "link manifest",
        ),
        session_summary=_require(
            folder,
            ("layer2_session_summary.json", "layer2_qc_session_manifest.csv"),
            "session summary",
        ),
    )
