"""Parquet/CSV I/O and output directory layout."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def stage_output_dir(output_dir: Path, stage_id: str) -> Path:
    """Return (and create) the stage subfolder under the run output directory."""
    stage_dirs = {
        "00": "00_csv_structure",
        "01": "01_joint_mapping",
        "02": "02_component_order",
        "03": "03_frame_time_validation",
        "04": "04_quaternion_qc",
        "05": "05_sign_continuity",
        "06": "06_relative_quaternions",
        "07": "07_rotation_vectors",
        "08": "08_filtered_rotvecs",
    }
    if stage_id not in stage_dirs:
        raise ValueError(f"Unknown stage id: {stage_id}")
    path = output_dir / stage_dirs[stage_id]
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
