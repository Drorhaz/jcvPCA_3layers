"""Load Layer 2 link manifest, session summary, and parquet slices."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


@dataclass(frozen=True)
class LinkRecord:
    link_id: str
    parent_canonical: str
    child_canonical: str
    feature_scope: str
    stage07_jump_status: str
    display_name: str


@dataclass(frozen=True)
class Layer2Session:
    session_id: str
    run_label: str
    frame_count: int
    sampling_rate_hz: float


def load_session_summary(path: Path) -> Layer2Session:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return Layer2Session(
            session_id=str(data.get("session_id", "")),
            run_label=str(data.get("run_label", data.get("run_key", ""))),
            frame_count=int(data.get("frame_count", data.get("n_frames", 0))),
            sampling_rate_hz=float(data.get("sampling_rate_hz", data.get("frame_rate_hz", 120))),
        )
    df = pd.read_csv(path)
    row = df.iloc[0]
    return Layer2Session(
        session_id=str(row["session_id"]),
        run_label=str(row["run_label"]),
        frame_count=int(row["frame_count"]),
        sampling_rate_hz=float(row["sampling_rate_hz"]),
    )


def load_link_manifest(path: Path) -> list[LinkRecord]:
    df = pd.read_csv(path)
    records: list[LinkRecord] = []
    for _, row in df.iterrows():
        parent = str(row["parent_canonical"])
        child = str(row["child_canonical"])
        records.append(
            LinkRecord(
                link_id=str(row["link_id"]),
                parent_canonical=parent,
                child_canonical=child,
                feature_scope=str(row.get("feature_scope", "")),
                stage07_jump_status=str(row.get("stage07_jump_status", "")),
                display_name=f"{parent}->{child}",
            )
        )
    return records


def load_rotvecs_window(
    parquet_path: Path,
    link_ids: list[str],
    frame_start: int,
    frame_end: int,
) -> pd.DataFrame:
    return load_rotvecs_window_full(
        parquet_path,
        link_ids,
        frame_start,
        frame_end,
        columns=[
            "frame",
            "link_id",
            "stage07_jump_status",
            "stage08_filter_status",
            "stage08_mask_reason",
            "stage08_analysis_eligible",
        ],
    )


def load_rotvecs_window_full(
    parquet_path: Path,
    link_ids: list[str],
    frame_start: int,
    frame_end: int,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    if columns is None:
        table = pq.read_table(parquet_path)
    else:
        schema_names = pq.read_schema(parquet_path).names
        missing = [col for col in columns if col not in schema_names]
        if missing:
            raise ValueError(
                f"Parquet missing required columns: {', '.join(missing)} "
                f"(file: {parquet_path})"
            )
        table = pq.read_table(parquet_path, columns=columns)
    df = table.to_pandas()
    mask = (
        df["link_id"].isin(link_ids)
        & (df["frame"] >= frame_start)
        & (df["frame"] <= frame_end)
    )
    return df.loc[mask].copy()


def resolve_selected_link_order(
    selected_link_ids: list[str],
    manifest_links: list[LinkRecord],
    *,
    selected_link_order: list[str] | None = None,
    preserve_input_link_order: bool = False,
) -> tuple[list[str], str]:
    if not selected_link_ids:
        raise ValueError("At least one selected link is required")

    if len(selected_link_ids) != len(set(selected_link_ids)):
        raise ValueError("selected_link_ids contains duplicates")

    manifest_ids = {link.link_id for link in manifest_links}
    unknown = [lid for lid in selected_link_ids if lid not in manifest_ids]
    if unknown:
        raise ValueError(f"Unknown link IDs: {', '.join(unknown)}")

    selected_set = set(selected_link_ids)

    if selected_link_order is not None:
        if len(selected_link_order) != len(set(selected_link_order)):
            raise ValueError("selected_link_order contains duplicates")
        if set(selected_link_order) != selected_set:
            raise ValueError(
                "selected_link_order must contain exactly the selected link IDs"
            )
        return list(selected_link_order), "explicit_selected_link_order"

    if preserve_input_link_order:
        return list(selected_link_ids), "preserve_input_link_order"

    order = [link.link_id for link in manifest_links if link.link_id in selected_set]
    return order, "manifest_order"


def links_by_preset(links: list[LinkRecord], preset: str | None) -> list[str]:
    if not preset or preset.lower() in ("none", ""):
        return []
    if preset == "core_candidate":
        return [link.link_id for link in links if link.feature_scope == "core_candidate"]
    if preset == "all_links":
        return [link.link_id for link in links]
    raise ValueError(f"Unknown joint_selection_preset: {preset}")
