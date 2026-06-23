"""Export selected window data for downstream JcvPCA preprocessing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pre_jvcpca_review.discovery import resolve_layer1, resolve_layer2
from pre_jvcpca_review.layer2_flags import block_filter_mask, jump_fail_rad_mask
from pre_jvcpca_review.load_layer1 import load_layer1_manifest, load_qc_mask
from pre_jvcpca_review.load_layer2 import (
    LinkRecord,
    load_link_manifest,
    load_rotvecs_window_full,
    load_session_summary,
    resolve_selected_link_order,
)
from pre_jvcpca_review.mapping import link_joint_family

LONG_ROTVEC_FILE = "window_selected_rotvecs_long.parquet"
MATRIX_FILE = "window_jvcpca_matrix.parquet"
FLAG_LOG_FILE = "window_joint_frame_flag_log.csv"
MANIFEST_FILE = "window_export_manifest.json"

LONG_ROTVEC_COLUMNS = [
    "session_id",
    "run_label",
    "frame",
    "time_sec",
    "link_id",
    "parent_canonical",
    "child_canonical",
    "link_or_joint",
    "joint_family",
    "feature_scope",
    "rx_raw",
    "ry_raw",
    "rz_raw",
    "rotvec_norm_raw",
    "rx_filtered_native",
    "ry_filtered_native",
    "rz_filtered_native",
    "rotvec_norm_filtered_native",
    "rx_filtered_analysis",
    "ry_filtered_analysis",
    "rz_filtered_analysis",
    "rotvec_norm_filtered_analysis",
]

L1_QC_SOURCE_COLUMNS = [
    "status",
    "flag_gap_0p2",
    "flag_gap_0p5",
    "flag_artifact_sigma",
    "flag_segment_swap",
    "flag_edge_effect",
    "reason",
]

L1_FRAME_FLAG_COLUMNS = [
    "l1_frame_status",
    "l1_frame_flag_gap_0p2",
    "l1_frame_flag_gap_0p5",
    "l1_frame_flag_artifact_sigma",
    "l1_frame_flag_segment_swap",
    "l1_frame_flag_edge_effect",
    "l1_frame_reason",
]

L1_RENAME_MAP = {
    "status": "l1_frame_status",
    "flag_gap_0p2": "l1_frame_flag_gap_0p2",
    "flag_gap_0p5": "l1_frame_flag_gap_0p5",
    "flag_artifact_sigma": "l1_frame_flag_artifact_sigma",
    "flag_segment_swap": "l1_frame_flag_segment_swap",
    "flag_edge_effect": "l1_frame_flag_edge_effect",
    "reason": "l1_frame_reason",
}

L2_DEFAULT_FLAG_COLUMNS = [
    "stage07_jump_status",
    "stage07_row_qc_status",
    "stage07_link_qc_status",
    "stage08_policy",
    "stage08_filter_status",
    "stage08_analysis_eligible",
    "stage08_mask_reason",
    "stage08_within_jump_context_window",
]

FLAG_LOG_IDENTITY_COLUMNS = [
    "session_id",
    "run_label",
    "frame",
    "time_sec",
    "link_id",
    "link_or_joint",
    "joint_family",
    "parent_canonical",
    "child_canonical",
    "selected_for_export",
]

DERIVED_FLAG_COLUMNS = ["jump_fail_rad_frame", "block_filter_frame"]

MATRIX_IDENTITY_COLUMNS = ["session_id", "run_label", "frame", "time_sec"]
MATRIX_SOURCE_COLUMNS = [
    "rx_filtered_analysis",
    "ry_filtered_analysis",
    "rz_filtered_analysis",
]
PRIMARY_ROTVEC_COLUMNS = list(MATRIX_SOURCE_COLUMNS)

ROTVEC_COMPONENT_PREFIXES = ("rx_", "ry_", "rz_", "rotvec_norm_")
FEATURE_NAMING_POLICY = "link_id_parent_to_child_axis"
FEATURE_AXES = ("rx", "ry", "rz")


class WindowExportError(Exception):
    """Export validation or contract failure."""


def feature_column_name(link: LinkRecord, axis: str) -> str:
    if axis not in FEATURE_AXES:
        raise ValueError(f"Invalid axis: {axis}")
    return f"{link.link_id}_{link.parent_canonical}_to_{link.child_canonical}_{axis}"


def expected_feature_order(
    links_by_id: dict[str, LinkRecord],
    selected_link_order: list[str],
) -> list[str]:
    names: list[str] = []
    for link_id in selected_link_order:
        link = links_by_id[link_id]
        for axis in FEATURE_AXES:
            names.append(feature_column_name(link, axis))
    return names


def validate_feature_column_names(
    matrix_df: pd.DataFrame,
    expected_feature_order: list[str],
) -> None:
    actual = [col for col in matrix_df.columns if col not in MATRIX_IDENTITY_COLUMNS]
    if actual != expected_feature_order:
        raise WindowExportError(
            "Feature column names do not match naming policy "
            f"{FEATURE_NAMING_POLICY!r}.\n"
            f"Expected: {expected_feature_order}\n"
            f"Actual:   {actual}"
        )


def _is_rotvec_component_column(name: str) -> bool:
    return any(name.startswith(prefix) for prefix in ROTVEC_COMPONENT_PREFIXES)


def _validate_frame_window(frame_start: int, frame_end: int, n_frames: int) -> None:
    if frame_start < 0 or frame_end < frame_start:
        raise WindowExportError(f"Invalid frame window: {frame_start}..{frame_end}")
    if frame_end >= n_frames:
        raise WindowExportError(
            f"frame_end {frame_end} exceeds session n_frames {n_frames - 1}"
        )


def validate_complete_frame_link_grid(
    df: pd.DataFrame,
    frame_start: int,
    frame_end: int,
    link_ids: list[str],
) -> list[tuple[int, str]]:
    expected_frames = set(range(frame_start, frame_end + 1))
    missing: list[tuple[int, str]] = []
    present = set(zip(df["frame"].astype(int), df["link_id"].astype(str)))
    for frame in sorted(expected_frames):
        for link_id in link_ids:
            if (frame, link_id) not in present:
                missing.append((frame, link_id))
    if missing:
        preview = ", ".join(f"({f},{lid})" for f, lid in missing[:10])
        suffix = f" (+{len(missing) - 10} more)" if len(missing) > 10 else ""
        raise WindowExportError(
            f"Missing {len(missing)} frame×link combinations before export: {preview}{suffix}"
        )
    counts = df.groupby(["frame", "link_id"]).size()
    dupes = counts[counts > 1]
    if not dupes.empty:
        raise WindowExportError(
            f"Duplicate frame×link rows found: {dupes.head(5).to_dict()}"
        )
    out_of_window = df[(df["frame"] < frame_start) | (df["frame"] > frame_end)]
    if not out_of_window.empty:
        raise WindowExportError("Rows found outside requested frame window")
    extra_links = set(df["link_id"].unique()) - set(link_ids)
    if extra_links:
        raise WindowExportError(f"Unexpected link IDs in slice: {sorted(extra_links)}")
    return missing


def _sort_by_frame_and_link_order(
    df: pd.DataFrame,
    selected_link_order: list[str],
) -> pd.DataFrame:
    out = df.copy()
    out["link_id"] = pd.Categorical(
        out["link_id"], categories=selected_link_order, ordered=True
    )
    out = out.sort_values(["frame", "link_id"]).reset_index(drop=True)
    out["link_id"] = out["link_id"].astype(str)
    return out


def _require_columns(df: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise WindowExportError(
            f"{label} missing required columns: {', '.join(missing)}"
        )


def _load_export_slice_columns(
    parquet_path: Path,
    include_full_l2_audit_columns: bool,
) -> list[str]:
    schema_names = pd.Series(pq_schema_names(parquet_path))
    base = list(dict.fromkeys(LONG_ROTVEC_COLUMNS + L2_DEFAULT_FLAG_COLUMNS))
    base = [col for col in base if col not in {"link_or_joint", "joint_family"}]
    if include_full_l2_audit_columns:
        audit = [
            name
            for name in schema_names
            if name not in base and not _is_rotvec_component_column(name)
        ]
        base.extend(audit)
    return list(dict.fromkeys(base))


def pq_schema_names(parquet_path: Path) -> list[str]:
    import pyarrow.parquet as pq

    return pq.read_schema(parquet_path).names


def build_long_rotvec_export(
    full_slice: pd.DataFrame,
    links_by_id: dict[str, LinkRecord],
    selected_link_order: list[str],
) -> pd.DataFrame:
    parquet_cols = [
        col for col in LONG_ROTVEC_COLUMNS if col not in {"link_or_joint", "joint_family"}
    ]
    _require_columns(full_slice, parquet_cols, "Long rotvec export")

    rows: list[pd.DataFrame] = []
    for link_id in selected_link_order:
        link = links_by_id[link_id]
        part = full_slice.loc[full_slice["link_id"] == link_id, parquet_cols].copy()
        part["link_or_joint"] = link.display_name
        part["joint_family"] = link_joint_family(link)
        rows.append(part)

    out = pd.concat(rows, ignore_index=True)
    out = _sort_by_frame_and_link_order(out, selected_link_order)
    return out[LONG_ROTVEC_COLUMNS]


def build_jvcpca_matrix(
    long_df: pd.DataFrame,
    links_by_id: dict[str, LinkRecord],
    selected_link_order: list[str],
    frame_start: int,
    frame_end: int,
    *,
    allow_nan_matrix: bool,
) -> tuple[pd.DataFrame, list[str], int, list[dict[str, object]]]:
    feature_order = expected_feature_order(links_by_id, selected_link_order)
    expected_frames = list(range(frame_start, frame_end + 1))
    rows: list[dict[str, object]] = []

    for frame in expected_frames:
        frame_rows = long_df[long_df["frame"] == frame]
        if frame_rows.empty:
            raise WindowExportError(f"No rows for frame {frame} in long rotvec export")
        identity = frame_rows.iloc[0]
        row: dict[str, object] = {
            col: identity[col] for col in MATRIX_IDENTITY_COLUMNS
        }
        for link_id in selected_link_order:
            link_row = frame_rows[frame_rows["link_id"] == link_id]
            if link_row.empty:
                raise WindowExportError(f"Missing link {link_id} at frame {frame}")
            link = links_by_id[link_id]
            for axis, src_col in zip(FEATURE_AXES, MATRIX_SOURCE_COLUMNS, strict=True):
                row[feature_column_name(link, axis)] = link_row.iloc[0][src_col]
        rows.append(row)

    matrix_df = pd.DataFrame(rows)
    validate_feature_column_names(matrix_df, feature_order)

    if matrix_df["frame"].duplicated().any():
        raise WindowExportError("Duplicate frames in JcvPCA matrix")
    if list(matrix_df["frame"]) != expected_frames:
        raise WindowExportError("JcvPCA matrix frames are not sorted ascending contiguous")

    nan_records: list[dict[str, object]] = []
    nan_count = 0
    for col in feature_order:
        nan_mask = matrix_df[col].isna()
        if nan_mask.any():
            frames = matrix_df.loc[nan_mask, "frame"].astype(int).tolist()
            nan_count += int(nan_mask.sum())
            nan_records.append({"feature_column": col, "frames": frames})

    if nan_records and not allow_nan_matrix:
        details = "; ".join(
            f"{rec['feature_column']} at frames {rec['frames'][:5]}"
            for rec in nan_records[:5]
        )
        raise WindowExportError(
            f"NaNs in JcvPCA matrix feature columns (nan_policy=fail_fast): {details}"
        )

    return matrix_df, feature_order, nan_count, nan_records


def build_joint_frame_flag_log(
    full_slice: pd.DataFrame,
    qc_window: pd.DataFrame,
    links_by_id: dict[str, LinkRecord],
    selected_link_order: list[str],
    *,
    include_full_l2_audit_columns: bool,
) -> pd.DataFrame:
    _require_columns(full_slice, L2_DEFAULT_FLAG_COLUMNS, "Flag log L2 slice")
    _require_columns(qc_window, L1_QC_SOURCE_COLUMNS, "Flag log L1 qc_mask")

    l1_cols = ["frame", *L1_QC_SOURCE_COLUMNS]
    l1 = qc_window[l1_cols].rename(columns=L1_RENAME_MAP)
    merged = full_slice.merge(l1, on="frame", how="left")

    merged["link_or_joint"] = merged["link_id"].map(
        lambda lid: links_by_id[str(lid)].display_name
    )
    merged["joint_family"] = merged["link_id"].map(
        lambda lid: link_joint_family(links_by_id[str(lid)])
    )
    merged["selected_for_export"] = True

    for link_id in selected_link_order:
        link = links_by_id[link_id]
        mask = merged["link_id"] == link_id
        group = merged.loc[mask]
        merged.loc[mask, "jump_fail_rad_frame"] = jump_fail_rad_mask(group, link).values
        merged.loc[mask, "block_filter_frame"] = block_filter_mask(group, link).values

    rotvec_cols = [col for col in merged.columns if _is_rotvec_component_column(col)]
    if rotvec_cols:
        merged = merged.drop(columns=rotvec_cols)

    flag_cols = list(L2_DEFAULT_FLAG_COLUMNS)
    if include_full_l2_audit_columns:
        extra = [
            col
            for col in merged.columns
            if col not in flag_cols
            and not col.startswith("l1_frame_")
            and col not in FLAG_LOG_IDENTITY_COLUMNS
            and col not in DERIVED_FLAG_COLUMNS
            and not _is_rotvec_component_column(col)
        ]
        flag_cols.extend(sorted(extra))

    output_cols = (
        FLAG_LOG_IDENTITY_COLUMNS
        + L1_FRAME_FLAG_COLUMNS
        + flag_cols
        + DERIVED_FLAG_COLUMNS
    )
    output_cols = list(dict.fromkeys(col for col in output_cols if col in merged.columns))
    out = merged[output_cols]
    return _sort_by_frame_and_link_order(out, selected_link_order)


def build_export_manifest(
    *,
    session_id: str,
    run_label: str,
    frame_start: int,
    frame_end: int,
    fps: float,
    selected_link_ids: list[str],
    selected_link_order: list[str],
    selected_link_order_source: str,
    links_by_id: dict[str, LinkRecord],
    feature_order: list[str],
    layer1_dir: Path,
    layer2_dir: Path,
    source_parquet: Path,
    source_qc_mask: Path,
    source_link_manifest: Path,
    source_summary_json: Path,
    long_df: pd.DataFrame,
    matrix_df: pd.DataFrame,
    flag_log: pd.DataFrame,
    nan_policy: str,
    nan_count_matrix: int,
    missing_frame_link_combinations: list[tuple[int, str]],
    include_full_l2_audit_columns: bool,
    allow_nan_matrix: bool,
) -> dict[str, object]:
    duration_frames = frame_end - frame_start + 1
    return {
        "session_id": session_id,
        "run_label": run_label,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "duration_frames": duration_frames,
        "duration_sec": round(duration_frames / fps, 4) if fps else 0.0,
        "fps": fps,
        "selected_link_ids": list(selected_link_ids),
        "selected_link_names": [links_by_id[lid].display_name for lid in selected_link_order],
        "selected_link_order": list(selected_link_order),
        "selected_link_order_source": selected_link_order_source,
        "n_selected_links": len(selected_link_order),
        "source_layer1_dir": str(layer1_dir.resolve()),
        "source_layer2_dir": str(layer2_dir.resolve()),
        "source_parquet": str(source_parquet.resolve()),
        "source_qc_mask": str(source_qc_mask.resolve()),
        "source_link_manifest": str(source_link_manifest.resolve()),
        "source_summary_json": str(source_summary_json.resolve()),
        "long_rotvec_file": LONG_ROTVEC_FILE,
        "jvcpca_matrix_file": MATRIX_FILE,
        "flag_log_file": FLAG_LOG_FILE,
        "long_rotvec_row_count": len(long_df),
        "long_rotvec_column_count": len(long_df.columns),
        "jvcpca_matrix_row_count": len(matrix_df),
        "jvcpca_matrix_column_count": len(matrix_df.columns),
        "flag_log_row_count": len(flag_log),
        "flag_log_column_count": len(flag_log.columns),
        "primary_rotvec_columns": PRIMARY_ROTVEC_COLUMNS,
        "feature_naming_policy": FEATURE_NAMING_POLICY,
        "feature_order": feature_order,
        "n_frames": duration_frames,
        "n_features": len(feature_order),
        "centering_scaling_status": "not_centered_not_scaled",
        "pca_status": "not_fitted",
        "jvcpca_status": "not_run",
        "nan_policy": nan_policy,
        "nan_count_matrix": nan_count_matrix,
        "missing_frame_link_combinations": [
            {"frame": frame, "link_id": link_id}
            for frame, link_id in missing_frame_link_combinations
        ],
        "include_full_l2_audit_columns": include_full_l2_audit_columns,
        "allow_nan_matrix": allow_nan_matrix,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def write_window_exports(
    out_dir: Path,
    long_df: pd.DataFrame,
    matrix_df: pd.DataFrame,
    flag_log: pd.DataFrame,
    manifest: dict[str, object],
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "long_rotvec": out_dir / LONG_ROTVEC_FILE,
        "jvcpca_matrix": out_dir / MATRIX_FILE,
        "flag_log": out_dir / FLAG_LOG_FILE,
        "manifest": out_dir / MANIFEST_FILE,
    }
    long_df.to_parquet(paths["long_rotvec"], index=False)
    matrix_df.to_parquet(paths["jvcpca_matrix"], index=False)
    flag_log.to_csv(paths["flag_log"], index=False)
    paths["manifest"].write_text(
        json.dumps(manifest, indent=2, default=str),
        encoding="utf-8",
    )
    return paths


def export_window_for_jvcpca(
    layer1_dir: Path,
    layer2_dir: Path,
    out_dir: Path,
    frame_start: int,
    frame_end: int,
    selected_link_ids: list[str],
    *,
    selected_link_order: list[str] | None = None,
    preserve_input_link_order: bool = False,
    include_full_l2_audit_columns: bool = False,
    allow_nan_matrix: bool = False,
) -> dict[str, Path]:
    layer1_paths = resolve_layer1(layer1_dir)
    layer2_paths = resolve_layer2(layer2_dir)
    l1 = load_layer1_manifest(layer1_paths.manifest)
    l2 = load_session_summary(layer2_paths.session_summary)
    manifest_links = load_link_manifest(layer2_paths.link_manifest)
    links_by_id = {link.link_id: link for link in manifest_links}

    _validate_frame_window(frame_start, frame_end, l1.n_frames)

    order, order_source = resolve_selected_link_order(
        selected_link_ids,
        manifest_links,
        selected_link_order=selected_link_order,
        preserve_input_link_order=preserve_input_link_order,
    )
    duration_frames = frame_end - frame_start + 1
    expected_long_rows = duration_frames * len(order)

    load_columns = _load_export_slice_columns(
        layer2_paths.rotvecs_parquet,
        include_full_l2_audit_columns,
    )
    full_slice = load_rotvecs_window_full(
        layer2_paths.rotvecs_parquet,
        order,
        frame_start,
        frame_end,
        columns=load_columns,
    )
    validate_complete_frame_link_grid(full_slice, frame_start, frame_end, order)

    long_df = build_long_rotvec_export(full_slice, links_by_id, order)
    if len(long_df) != expected_long_rows:
        raise WindowExportError(
            f"Long rotvec row count {len(long_df)} != expected {expected_long_rows}"
        )
    if long_df[["session_id", "frame", "link_id"]].isna().any().any():
        raise WindowExportError("Null session_id, frame, or link_id in long rotvec export")

    matrix_df, feature_order, nan_count, _nan_records = build_jvcpca_matrix(
        long_df,
        links_by_id,
        order,
        frame_start,
        frame_end,
        allow_nan_matrix=allow_nan_matrix,
    )
    if len(matrix_df) != duration_frames:
        raise WindowExportError(
            f"Matrix row count {len(matrix_df)} != expected {duration_frames}"
        )
    if matrix_df[["session_id", "frame"]].isna().any().any():
        raise WindowExportError("Null session_id or frame in JcvPCA matrix")

    qc_window = load_qc_mask(layer1_paths.qc_mask, frame_start, frame_end)
    flag_log = build_joint_frame_flag_log(
        full_slice,
        qc_window,
        links_by_id,
        order,
        include_full_l2_audit_columns=include_full_l2_audit_columns,
    )
    if len(flag_log) != expected_long_rows:
        raise WindowExportError(
            f"Flag log row count {len(flag_log)} != expected {expected_long_rows}"
        )

    nan_policy = (
        "allow_nan_matrix" if allow_nan_matrix else "fail_fast_unless_allow_nan_matrix"
    )
    manifest = build_export_manifest(
        session_id=l2.session_id,
        run_label=l2.run_label,
        frame_start=frame_start,
        frame_end=frame_end,
        fps=l1.fps,
        selected_link_ids=selected_link_ids,
        selected_link_order=order,
        selected_link_order_source=order_source,
        links_by_id=links_by_id,
        feature_order=feature_order,
        layer1_dir=layer1_paths.dir,
        layer2_dir=layer2_paths.dir,
        source_parquet=layer2_paths.rotvecs_parquet,
        source_qc_mask=layer1_paths.qc_mask,
        source_link_manifest=layer2_paths.link_manifest,
        source_summary_json=layer2_paths.session_summary,
        long_df=long_df,
        matrix_df=matrix_df,
        flag_log=flag_log,
        nan_policy=nan_policy,
        nan_count_matrix=nan_count,
        missing_frame_link_combinations=[],
        include_full_l2_audit_columns=include_full_l2_audit_columns,
        allow_nan_matrix=allow_nan_matrix,
    )

    return write_window_exports(out_dir, long_df, matrix_df, flag_log, manifest)
