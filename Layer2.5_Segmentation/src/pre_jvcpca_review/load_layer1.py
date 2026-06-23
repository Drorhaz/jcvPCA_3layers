"""Load Layer 1 session metadata and QC mask."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from pre_jvcpca_review.discovery import Layer1Paths


@dataclass(frozen=True)
class Layer1Session:
    session_id: str
    run_key: str
    fps: float
    n_frames: int
    frame_column: str


def load_layer1_manifest(manifest_path: Path) -> Layer1Session:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_key = data.get("run_key") or data.get("session_id", "")
    session_id = data.get("session_id") or run_key
    return Layer1Session(
        session_id=session_id,
        run_key=run_key,
        fps=float(data["frame_rate_hz"]),
        n_frames=int(data["n_frames"]),
        frame_column=data.get("frame_index_column", "frame"),
    )


def load_qc_mask(qc_mask_path: Path, frame_start: int, frame_end: int) -> pd.DataFrame:
    df = pd.read_csv(qc_mask_path)
    window = df[(df["frame"] >= frame_start) & (df["frame"] <= frame_end)].copy()
    for col in ("flag_gap_0p2", "flag_gap_0p5", "flag_artifact_sigma", "flag_segment_swap"):
        if col in window.columns:
            window[col] = window[col].astype(str).str.lower() == "true"
    return window


def flagged_frame_percent(qc_window: pd.DataFrame, flag_col: str, duration_frames: int) -> float:
    if duration_frames <= 0 or flag_col not in qc_window.columns:
        return 0.0
    return round(100.0 * qc_window[flag_col].sum() / duration_frames, 2)


def load_layer1_artifact_events(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_layer1_gap_summary(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)
