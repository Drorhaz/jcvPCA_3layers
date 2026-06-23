"""Export selected window data for downstream JcvPCA preprocessing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pre_jvcpca_review.canonical_manifest import (
    CANONICAL_NAMING_POLICY,
    DEFAULT_PILOT_MANIFEST,
    ManifestError,
    ManifestFeature,
    expected_pilot_feature_order,
    load_pilot_manifest,
    pilot_link_order,
    resolve_session_links_from_manifest,
)
from pre_jvcpca_review.discovery import resolve_layer1, resolve_layer2
from pre_jvcpca_review.export_constants import (
    FEATURE_AXES,
    MATRIX_IDENTITY_COLUMNS,
    MATRIX_SOURCE_COLUMNS,
)
from pre_jvcpca_review.pilot_export_validation import (
    PilotExportValidationError,
    validate_before_write,
)
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
from pre_jvcpca_review.pairing import run_pairing_gate
from pre_jvcpca_review.warnings import (
    SEVERITY_BLOCKING,
    SEVERITY_STRONG,
    SEVERITY_WARNING,
    WarningCollector,
)

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
    layer3_safe: bool = False,
    layer3_safe_reason: str = "",
) -> dict[str, object]:
    duration_frames = frame_end - frame_start + 1
    return {
        "layer3_safe": layer3_safe,
        "layer3_safe_reason": layer3_safe_reason,
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


def build_pilot_jvcpca_matrix(
    long_df: pd.DataFrame,
    manifest: list[ManifestFeature],
    links_by_canonical: dict[tuple[str, str], LinkRecord],
    frame_start: int,
    frame_end: int,
    *,
    allow_nan_matrix: bool,
) -> tuple[pd.DataFrame, list[str], int, list[dict[str, object]]]:
    feature_order = expected_pilot_feature_order(manifest, links_by_canonical)
    expected_frames = list(range(frame_start, frame_end + 1))
    rows: list[dict[str, object]] = []

    pilot_features = [feature for feature in manifest if feature.include_in_pilot]

    for frame in expected_frames:
        frame_rows = long_df[long_df["frame"] == frame]
        if frame_rows.empty:
            raise WindowExportError(f"No rows for frame {frame} in long rotvec export")
        identity = frame_rows.iloc[0]
        row: dict[str, object] = {col: identity[col] for col in MATRIX_IDENTITY_COLUMNS}
        for feature in pilot_features:
            link_row = frame_rows[
                (frame_rows["parent_canonical"] == feature.parent_canonical)
                & (frame_rows["child_canonical"] == feature.child_canonical)
            ]
            if link_row.empty:
                raise WindowExportError(
                    f"Missing link {feature.parent_canonical}->{feature.child_canonical} "
                    f"at frame {frame}"
                )
            row[feature.feature_name] = link_row.iloc[0][feature.source_layer2_column]
        rows.append(row)

    matrix_df = pd.DataFrame(rows)
    if matrix_df["frame"].duplicated().any():
        raise WindowExportError("Duplicate frames in pilot JcvPCA matrix")
    if list(matrix_df["frame"]) != expected_frames:
        raise WindowExportError("Pilot JcvPCA matrix frames are not sorted ascending contiguous")

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
            f"NaNs in pilot JcvPCA matrix (nan_policy=fail_fast): {details}"
        )

    actual_features = [col for col in matrix_df.columns if col not in MATRIX_IDENTITY_COLUMNS]
    if actual_features != feature_order:
        raise WindowExportError(
            "Pilot feature column order does not match canonical manifest order"
        )

    return matrix_df, feature_order, nan_count, nan_records


def export_pilot_window_for_jvcpca(
    layer1_dir: Path,
    layer2_dir: Path,
    out_dir: Path,
    frame_start: int,
    frame_end: int,
    *,
    pilot_manifest_path: Path | None = None,
    include_full_l2_audit_columns: bool = False,
    allow_nan_matrix: bool = False,
    warning_records: list[dict] | None = None,
    warnings_summary: dict | None = None,
    identity: dict | None = None,
    joint_alignment_status: str = "single_session_direct",
    pairing_result: str = "ok",
    window_label: str = "",
) -> dict[str, Path]:
    """Export window using frozen canonical pilot manifest and hard validation gate.

    This is the ONLY Layer 3-safe export path: feature names are
    ``parent_canonical_to_child_canonical_axis`` (canonical) and the resulting
    manifest carries ``layer3_safe=true``.
    """
    out_dir = Path(out_dir)
    manifest_path = pilot_manifest_path or DEFAULT_PILOT_MANIFEST
    manifest = load_pilot_manifest(manifest_path)

    layer1_paths = resolve_layer1(layer1_dir)
    layer2_paths = resolve_layer2(layer2_dir)
    l1 = load_layer1_manifest(layer1_paths.manifest)
    l2 = load_session_summary(layer2_paths.session_summary)
    session_links = load_link_manifest(layer2_paths.link_manifest)

    selected_link_ids, links_by_canonical = resolve_session_links_from_manifest(
        manifest, session_links
    )
    links_by_id = {link.link_id: link for link in session_links}

    _validate_frame_window(frame_start, frame_end, l1.n_frames)

    order = [links_by_canonical[key].link_id for key in pilot_link_order(manifest)]
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

    matrix_df, feature_order, nan_count, _nan_records = build_pilot_jvcpca_matrix(
        long_df,
        manifest,
        links_by_canonical,
        frame_start,
        frame_end,
        allow_nan_matrix=allow_nan_matrix,
    )

    try:
        validate_before_write(
            matrix_df,
            feature_order,
            manifest_path,
            session_links,
            allow_nan=allow_nan_matrix,
            out_dir=out_dir,
        )
    except PilotExportValidationError as exc:
        raise WindowExportError(str(exc)) from exc

    qc_window = load_qc_mask(layer1_paths.qc_mask, frame_start, frame_end)
    flag_log = build_joint_frame_flag_log(
        full_slice,
        qc_window,
        links_by_id,
        order,
        include_full_l2_audit_columns=include_full_l2_audit_columns,
    )

    nan_policy = "allow_nan_matrix" if allow_nan_matrix else "fail_fast"
    manifest_payload = build_export_manifest(
        session_id=l2.session_id,
        run_label=l2.run_label,
        frame_start=frame_start,
        frame_end=frame_end,
        fps=l1.fps,
        selected_link_ids=selected_link_ids,
        selected_link_order=order,
        selected_link_order_source="pilot_manifest_canonical_order",
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
        layer3_safe=True,
        layer3_safe_reason="canonical parent->child->axis feature identity",
    )
    manifest_payload["pilot_manifest_path"] = str(manifest_path.resolve())
    manifest_payload["feature_naming_policy"] = CANONICAL_NAMING_POLICY
    manifest_payload["canonical_feature_order"] = list(feature_order)
    manifest_payload["canonical_link_order"] = [
        f"{parent}->{child}" for parent, child in pilot_link_order(manifest)
    ]
    manifest_payload["window_label"] = window_label
    manifest_payload["joint_alignment_status"] = joint_alignment_status
    manifest_payload["layer1_layer2_pairing_result"] = pairing_result
    if identity:
        manifest_payload["selected_participant"] = identity.get("participant_id", "")
        manifest_payload["selected_session"] = identity.get("session_id", "")
        manifest_payload["selected_layer1_run_dir"] = identity.get("layer1_run_dir", "")
        manifest_payload["selected_layer2_run_dir"] = identity.get("layer2_run_dir", "")
        manifest_payload["identity"] = identity
    if warnings_summary is not None:
        manifest_payload["warnings_summary"] = warnings_summary
    if warning_records is not None:
        manifest_payload["warnings"] = warning_records

    paths = write_window_exports(out_dir, long_df, matrix_df, flag_log, manifest_payload)

    if warning_records is not None:
        warnings_csv = Path(out_dir) / "window_warnings.csv"
        pd.DataFrame(warning_records).to_csv(warnings_csv, index=False)
        paths["warnings"] = warnings_csv

    summary_path = write_matrix_summary_md(
        Path(out_dir) / "window_jvcpca_matrix_summary.md",
        manifest_payload,
        matrix_df,
        feature_order,
    )
    paths["summary"] = summary_path
    return paths


def write_matrix_summary_md(
    path: Path,
    manifest: dict,
    matrix_df: pd.DataFrame,
    feature_order: list[str],
) -> Path:
    lines = [
        "# Window JcvPCA Matrix Summary",
        "",
        f"- Layer 3 safe: **{manifest.get('layer3_safe')}**",
        f"- Feature naming policy: `{manifest.get('feature_naming_policy')}`",
        f"- Participant: {manifest.get('selected_participant', '')}",
        f"- Session: {manifest.get('session_id', '')}",
        f"- Run label: {manifest.get('run_label', '')}",
        f"- Frames: {manifest.get('frame_start')}..{manifest.get('frame_end')} "
        f"({manifest.get('n_frames')} frames)",
        f"- Window label: {manifest.get('window_label', '')}",
        f"- Features: {len(feature_order)}",
        f"- Matrix shape: {matrix_df.shape[0]} rows x {matrix_df.shape[1]} cols",
        f"- NaN count: {manifest.get('nan_count_matrix')}",
        f"- Joint alignment: {manifest.get('joint_alignment_status', '')}",
        f"- L1/L2 pairing: {manifest.get('layer1_layer2_pairing_result', '')}",
        "",
        "## Warnings summary",
        "",
    ]
    ws = manifest.get("warnings_summary") or {}
    if ws:
        for k, v in ws.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- (none recorded)")
    lines += ["", "## Canonical feature order", ""]
    lines += [f"{i + 1}. {name}" for i, name in enumerate(feature_order)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


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
        layer3_safe=False,
        layer3_safe_reason=(
            "LEGACY J00x feature naming (link_id may shift across sessions/templates); "
            "MUST NOT be used for Layer 3. Use export_pilot_window_for_jvcpca instead."
        ),
    )
    manifest["feature_naming_policy"] = FEATURE_NAMING_POLICY
    manifest["legacy_layer3_warning"] = (
        "This export uses J00x-based feature names and is not Layer 3 safe. "
        "Diagnostics only. The notebook export button must not call this path."
    )

    return write_window_exports(out_dir, long_df, matrix_df, flag_log, manifest)


def _row_get(row, key, default=""):
    if row is None:
        return default
    try:
        val = row[key]
    except (KeyError, TypeError, IndexError):
        return default
    if val is None:
        return default
    return val


def _check_manifest_triplets(manifest_features: list[ManifestFeature], collector, kw) -> None:
    axes_by_link: dict[tuple[str, str], set[str]] = {}
    for f in manifest_features:
        if not getattr(f, "include_in_pilot", True):
            continue
        axes_by_link.setdefault((f.parent_canonical, f.child_canonical), set()).add(f.axis)
    for (parent, child), axes in axes_by_link.items():
        missing = set(FEATURE_AXES) - axes
        if missing:
            collector.emit(
                "feature.incomplete_triplet", SEVERITY_BLOCKING, "feature_manifest",
                f"Canonical link {parent}->{child} is missing axes {sorted(missing)} "
                "(rx/ry/rz triplet incomplete).",
                recommended_action="Fix the feature manifest to include full rx/ry/rz triplet.",
                parent_canonical=parent, child_canonical=child,
                canonical_link_name=f"{parent}->{child}", **kw,
            )


def _collect_window_qc_warnings(flag_log_path: Path, collector, kw) -> None:
    """Emit strong/info warnings from the written flag log (window-scoped)."""
    try:
        fl = pd.read_csv(flag_log_path)
    except (OSError, ValueError):
        return
    if "jump_fail_rad_frame" in fl.columns:
        n_jump = int(fl["jump_fail_rad_frame"].fillna(False).astype(bool).sum())
        if n_jump:
            collector.emit(
                "window.stage07_jump", SEVERITY_STRONG, "layer2_qc",
                f"Stage 07 jump fail flag set on {n_jump} frame*link rows inside the window.",
                recommended_action="Review jumps; consider trimming window or excluding link.",
                source_layer="layer2", **kw,
            )
    if "block_filter_frame" in fl.columns:
        n_block = int(fl["block_filter_frame"].fillna(False).astype(bool).sum())
        if n_block:
            collector.emit(
                "window.stage08_masked", SEVERITY_STRONG, "layer2_qc",
                f"Stage 08 masked / not analysis-eligible on {n_block} frame*link rows in window.",
                recommended_action="Review masked frames; they are NaN/interpolated.",
                source_layer="layer2", **kw,
            )
    if "l1_frame_status" in fl.columns:
        bad = fl[fl["l1_frame_status"].astype(str).str.lower() != "ok"]
        n_l1 = int(bad["frame"].nunique()) if "frame" in fl.columns else len(bad)
        if n_l1:
            collector.emit(
                "window.layer1_evidence_overlap", SEVERITY_WARNING, "layer1_evidence",
                f"Layer 1 flagged {n_l1} frames (gap/artifact) overlapping the selected window.",
                recommended_action="Inspect Layer 1 evidence for these frames.",
                source_layer="layer1", **kw,
            )


def export_layer3_window(
    layer1_dir: Path,
    layer2_dir: Path,
    out_dir: Path,
    frame_start: int,
    frame_end: int,
    *,
    session_row=None,
    pilot_manifest_path: Path | None = None,
    window_label: str = "",
    include_full_l2_audit_columns: bool = False,
    allow_nan_matrix: bool = False,
    overlap_df=None,
    harmonization_manifest_exists: bool = False,
    scope_required_links: list[tuple[str, str]] | None = None,
    require_pairing: bool = True,
) -> dict[str, object]:
    """Layer 3-safe export orchestrator (canonical only) with a blocking warning gate.

    Returns a result dict: {"status", "paths", "warnings_csv", "warnings_summary",
    "blocked"}. Raises WindowExportError only on unexpected build failures; blocking
    *policy* warnings prevent matrix write and are reported via status="blocked".
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    collector = WarningCollector()

    kw = {
        "participant_id": str(_row_get(session_row, "participant_id")),
        "session_id": str(_row_get(session_row, "session_id")),
        "timepoint": str(_row_get(session_row, "timepoint")),
        "part_id": str(_row_get(session_row, "part_id")),
        "repetition_id": str(_row_get(session_row, "repetition_id")),
        "window_id": window_label,
        "start_frame": frame_start,
        "end_frame": frame_end,
    }

    if require_pairing and session_row is not None:
        run_pairing_gate(session_row, collector)

    manifest_path = pilot_manifest_path or DEFAULT_PILOT_MANIFEST
    manifest_features = load_pilot_manifest(manifest_path)
    _check_manifest_triplets(manifest_features, collector, kw)

    # Missing required canonical feature (resolve against the session link manifest).
    required_links = pilot_link_order(manifest_features)
    try:
        layer2_paths = resolve_layer2(layer2_dir)
        session_links = load_link_manifest(layer2_paths.link_manifest)
        resolve_session_links_from_manifest(manifest_features, session_links)
    except ManifestError as exc:
        collector.emit(
            "feature.missing_required", SEVERITY_BLOCKING, "feature_manifest",
            f"Required canonical feature(s) not present in this session: {exc}",
            recommended_action="Pick a session with all required links or narrow the manifest.",
            **kw,
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        collector.emit(
            "feature.layer2_unreadable", SEVERITY_BLOCKING, "feature_manifest",
            f"Could not read Layer 2 link manifest: {exc}",
            recommended_action="Verify Layer 2 export completeness.",
            source_layer="layer2", **kw,
        )

    # Cross-session comparability gate (scoped to user selection when provided).
    if overlap_df is not None and len(overlap_df):
        from pre_jvcpca_review.joint_overlap import emit_joint_comparability_warnings

        if scope_required_links is not None and not scope_required_links:
            collector.emit(
                "joint.no_selection",
                SEVERITY_BLOCKING,
                "joint_alignment",
                "No joints selected for export.",
                recommended_action="Select at least one joint before exporting.",
                **kw,
            )
        else:
            comparability_scope = (
                scope_required_links if scope_required_links is not None else required_links
            )
            emit_joint_comparability_warnings(
                collector,
                overlap_df,
                comparability_scope,
                harmonization_manifest_exists=harmonization_manifest_exists,
                **kw,
            )

    pairing_result = "ok" if not collector.has_blocking else "blocked"

    if collector.has_blocking:
        warnings_csv = collector.write_csv(out_dir / "window_warnings.csv")
        blocked_manifest = {
            "layer3_safe": False,
            "layer3_safe_reason": "export blocked by blocking warnings",
            "selected_participant": kw["participant_id"],
            "selected_session": kw["session_id"],
            "window_label": window_label,
            "feature_naming_policy": CANONICAL_NAMING_POLICY,
            "layer1_layer2_pairing_result": pairing_result,
            "joint_alignment_status": "blocked",
            "warnings_summary": collector.summary(),
            "warnings": collector.to_dataframe().to_dict(orient="records"),
            "export_status": "blocked",
        }
        (out_dir / MANIFEST_FILE).write_text(
            json.dumps(blocked_manifest, indent=2, default=str), encoding="utf-8"
        )
        return {
            "status": "blocked",
            "blocked": True,
            "paths": {"warnings": warnings_csv, "manifest": out_dir / MANIFEST_FILE},
            "warnings_csv": warnings_csv,
            "warnings_summary": collector.summary(),
        }

    identity = {
        "participant_id": kw["participant_id"],
        "session_id": kw["session_id"],
        "timepoint": kw["timepoint"],
        "part_id": kw["part_id"],
        "repetition_id": kw["repetition_id"],
        "layer1_run_dir": str(_row_get(session_row, "layer1_run_dir", str(layer1_dir))),
        "layer2_run_dir": str(_row_get(session_row, "layer2_run_dir", str(layer2_dir))),
        "marker_set_id": str(_row_get(session_row, "marker_set_id")),
        "layer2_git_commit": str(_row_get(session_row, "layer2_git_commit")),
        "layer2_config_hash": str(_row_get(session_row, "layer2_config_hash")),
    }

    paths = export_pilot_window_for_jvcpca(
        layer1_dir,
        layer2_dir,
        out_dir,
        frame_start,
        frame_end,
        pilot_manifest_path=manifest_path,
        include_full_l2_audit_columns=include_full_l2_audit_columns,
        allow_nan_matrix=allow_nan_matrix,
        identity=identity,
        joint_alignment_status="single_session_direct"
        if overlap_df is None
        else "cross_session_checked",
        pairing_result=pairing_result,
        window_label=window_label,
    )

    # Window-scoped QC warnings from the written flag log (non-blocking).
    _collect_window_qc_warnings(paths["flag_log"], collector, kw)

    # Re-write warnings + patch manifest with the complete warning set.
    warnings_csv = collector.write_csv(out_dir / "window_warnings.csv")
    paths["warnings"] = warnings_csv
    manifest_path_out = paths["manifest"]
    payload = json.loads(Path(manifest_path_out).read_text(encoding="utf-8"))
    payload["warnings_summary"] = collector.summary()
    payload["warnings"] = collector.to_dataframe().to_dict(orient="records")
    payload["export_status"] = "exported"
    payload["requires_user_approval"] = collector.requires_approval
    Path(manifest_path_out).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    return {
        "status": "exported",
        "blocked": False,
        "paths": paths,
        "warnings_csv": warnings_csv,
        "warnings_summary": collector.summary(),
        "requires_user_approval": collector.requires_approval,
    }
