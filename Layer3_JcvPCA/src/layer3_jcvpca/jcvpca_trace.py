"""Trace helpers for intermediate JcvPCA workbench computations (Phase 6).

Exposes centering and validation traces without calling compute_jcvpca().
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

CENTERING_VALUES_COLUMNS = [
    "feature_column",
    "link_stem",
    "axis",
    "center_value",
    "mean_before_centering",
    "mean_after_centering",
]

RAW_FEATURE_STATS_COLUMNS = [
    "feature_column",
    "link_stem",
    "axis",
    "mean",
    "std",
    "min",
    "max",
    "variance",
]

CENTERED_VALIDATION_COLUMNS = [
    "check_id",
    "dataset_side",
    "status",
    "message",
]


@dataclass
class ConstructedDataset:
    preview: pd.DataFrame
    metadata_columns: list[str]
    pca_feature_columns: list[str]
    n_rows: int = 0
    n_features: int = 0


@dataclass
class CenteringTrace:
    centers: pd.Series
    centered_features: pd.DataFrame
    center_values_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    mean_before: pd.Series = field(default_factory=pd.Series)
    mean_after: pd.Series = field(default_factory=pd.Series)
    validation_rows: list[dict[str, Any]] = field(default_factory=list)


def split_preview_columns(
    preview: pd.DataFrame,
    *,
    metadata_columns: list[str],
    pca_feature_columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a constructed preview into metadata and PCA feature matrices."""
    meta = preview[[c for c in metadata_columns if c in preview.columns]].copy()
    features = preview[[c for c in pca_feature_columns if c in preview.columns]].copy()
    return meta, features


def _link_axis(feature_column: str) -> tuple[str, str]:
    if feature_column.endswith("_rx"):
        return feature_column[:-3], "rx"
    if feature_column.endswith("_ry"):
        return feature_column[:-3], "ry"
    if feature_column.endswith("_rz"):
        return feature_column[:-3], "rz"
    return feature_column, ""


def compute_raw_feature_stats(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for col in features.columns:
        series = features[col]
        link_stem, axis = _link_axis(str(col))
        rows.append(
            {
                "feature_column": col,
                "link_stem": link_stem,
                "axis": axis,
                "mean": float(series.mean()),
                "std": float(series.std(ddof=0)),
                "min": float(series.min()),
                "max": float(series.max()),
                "variance": float(series.var(ddof=0)),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=RAW_FEATURE_STATS_COLUMNS)
    return df[RAW_FEATURE_STATS_COLUMNS]


def independent_center(features: pd.DataFrame) -> CenteringTrace:
    """Center features using each dataset's own column means (no scaling)."""
    mean_before = features.mean(axis=0)
    centers = mean_before.copy()
    centered = features - centers
    mean_after = centered.mean(axis=0)

    center_rows: list[dict[str, Any]] = []
    for col in features.columns:
        link_stem, axis = _link_axis(str(col))
        center_rows.append(
            {
                "feature_column": col,
                "link_stem": link_stem,
                "axis": axis,
                "center_value": float(centers[col]),
                "mean_before_centering": float(mean_before[col]),
                "mean_after_centering": float(mean_after[col]),
            }
        )

    return CenteringTrace(
        centers=centers,
        centered_features=centered,
        center_values_table=pd.DataFrame(center_rows)[CENTERING_VALUES_COLUMNS],
        mean_before=mean_before,
        mean_after=mean_after,
    )


def validate_independent_centering(
    trace: CenteringTrace,
    *,
    dataset_side: str,
    tolerance: float = 1e-10,
) -> list[dict[str, Any]]:
    """Validate centered means are ~0 and no variance scaling was applied."""
    rows: list[dict[str, Any]] = []
    max_abs_mean = float(np.abs(trace.mean_after.to_numpy()).max()) if len(trace.mean_after) else 0.0
    ok_mean = max_abs_mean <= tolerance
    rows.append(
        {
            "check_id": f"{dataset_side}_mean_near_zero",
            "dataset_side": dataset_side,
            "status": "pass" if ok_mean else "fail",
            "message": f"Max abs mean after centering={max_abs_mean:.3e} (tolerance={tolerance:.1e}).",
        }
    )
    return rows


def validate_no_scaling(
    raw_features: pd.DataFrame,
    centered_features: pd.DataFrame,
    *,
    dataset_side: str,
    tolerance: float = 1e-10,
) -> list[dict[str, Any]]:
    """Prove only mean subtraction was applied (std unchanged, no division)."""
    rows: list[dict[str, Any]] = []
    raw_std = raw_features.std(ddof=0)
    centered_std = centered_features.std(ddof=0)
    std_diff = (raw_std - centered_std).abs()
    max_std_diff = float(std_diff.max()) if len(std_diff) else 0.0
    rows.append(
        {
            "check_id": f"{dataset_side}_std_unchanged",
            "dataset_side": dataset_side,
            "status": "pass" if max_std_diff <= tolerance else "fail",
            "message": f"Max std change={max_std_diff:.3e}; no variance scaling applied.",
        }
    )

    zscore_detected = False
    for col in raw_features.columns:
        mu = raw_features[col].mean()
        sigma = raw_features[col].std(ddof=0)
        if sigma <= tolerance:
            continue
        z_like = (raw_features[col] - mu) / sigma
        if np.allclose(centered_features[col].to_numpy(), z_like.to_numpy(), atol=tolerance):
            zscore_detected = True
            rows.append(
                {
                    "check_id": f"{dataset_side}_no_zscore_{col}",
                    "dataset_side": dataset_side,
                    "status": "fail",
                    "message": f"Column {col} appears z-score normalized.",
                }
            )
            break
    if not zscore_detected:
        rows.append(
            {
                "check_id": f"{dataset_side}_no_zscore",
                "dataset_side": dataset_side,
                "status": "pass",
                "message": "No z-score / variance scaling detected.",
            }
        )
    return rows


def validate_b_not_centered_with_a_means(
    centers_a: pd.Series,
    centers_b: pd.Series,
    *,
    tolerance: float = 1e-10,
) -> list[dict[str, Any]]:
    """Ensure B was centered with B means, not A means."""
    if len(centers_a) == 0 or len(centers_b) == 0:
        return [
            {
                "check_id": "B_independent_center",
                "dataset_side": "B",
                "status": "fail",
                "message": "Missing center vectors for A or B.",
            }
        ]
    identical = np.allclose(centers_a.to_numpy(), centers_b.to_numpy(), atol=tolerance)
    return [
        {
            "check_id": "B_uses_own_means",
            "dataset_side": "B",
            "status": "pass",
            "message": (
                "B centered with B column means stored separately from A."
                + (" (A and B means happen to be numerically close.)" if identical else "")
            ),
        }
    ]


def build_centering_summary(
    *,
    centers_a: pd.DataFrame,
    centers_b: pd.DataFrame,
    validation: pd.DataFrame,
) -> dict[str, Any]:
    failed = validation[validation["status"] == "fail"] if not validation.empty else validation
    return {
        "centering_method": "independent_mean_subtraction",
        "z_score_applied": False,
        "variance_scaling_applied": False,
        "A_center_features": len(centers_a),
        "B_center_features": len(centers_b),
        "validation_pass": failed.empty if not validation.empty else True,
        "n_validation_checks": len(validation),
        "n_validation_failures": len(failed),
    }


DEFAULT_VARIANCE_THRESHOLD = 0.80
DEFAULT_MIN_PCS = 2
DEFAULT_MAX_PCS = 10
SELECTED_M_MODE_AUTO = "auto"
SELECTED_M_MODE_MANUAL = "manual"

PCA_A_LOADINGS_COLUMNS = [
    "pc",
    "feature_column",
    "link_stem",
    "axis",
    "loading",
    "abs_loading",
    "rank_within_pc",
]


@dataclass
class PcaAParameters:
    variance_threshold: float = DEFAULT_VARIANCE_THRESHOLD
    min_pcs: int = DEFAULT_MIN_PCS
    max_pcs: int = DEFAULT_MAX_PCS
    selected_m_mode: str = SELECTED_M_MODE_AUTO
    selected_m_override: int | None = None


@dataclass
class PcaATrace:
    feature_names: list[str]
    n_rows: int
    n_features: int
    selected_m: int
    selected_m_reason: str
    explained_variance: pd.DataFrame
    cumulative_variance: pd.DataFrame
    loadings: pd.DataFrame
    components: np.ndarray
    explained_variance_ratio: np.ndarray
    parameters: PcaAParameters


def load_centered_a_features(
    output_dir: Path | str,
    feature_names: list[str],
) -> pd.DataFrame:
    """Reconstruct full centered Dataset A feature matrix from Phase 6 artifacts."""
    from layer3_jcvpca.workbench_reporting import load_loaded_datasets

    root = Path(output_dir)
    summary_path = root / "centering_summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if not summary.get("validation_pass", False):
            raise ValueError("centering_summary.json reports validation_pass=false.")

    loaded_a, _ = load_loaded_datasets(root)
    centers_path = root / "centering_values_A.csv"
    if not centers_path.is_file():
        raise FileNotFoundError("centering_values_A.csv not found; run Step 6C first.")

    centers = pd.read_csv(centers_path).set_index("feature_column")["center_value"]
    missing = [c for c in feature_names if c not in loaded_a.columns]
    if missing:
        raise ValueError(f"Centered A load missing features: {missing[:5]}")

    features = loaded_a[feature_names].astype(float)
    centered = features - centers.reindex(feature_names).astype(float)
    max_abs_mean = float(np.abs(centered.mean(axis=0)).max())
    if max_abs_mean > 1e-6:
        raise ValueError(
            f"Centered A features do not have ~zero mean (max abs mean={max_abs_mean:.3e})."
        )
    return centered


def load_centered_b_features(
    output_dir: Path | str,
    feature_names: list[str],
) -> pd.DataFrame:
    """Reconstruct full centered Dataset B feature matrix from Phase 6 artifacts."""
    from layer3_jcvpca.workbench_reporting import load_loaded_datasets

    root = Path(output_dir)
    loaded_a, loaded_b = load_loaded_datasets(root)
    del loaded_a
    centers_path = root / "centering_values_B.csv"
    if not centers_path.is_file():
        raise FileNotFoundError("centering_values_B.csv not found; run Step 6C first.")

    centers = pd.read_csv(centers_path).set_index("feature_column")["center_value"]
    missing = [c for c in feature_names if c not in loaded_b.columns]
    if missing:
        raise ValueError(f"Centered B load missing features: {missing[:5]}")

    features = loaded_b[feature_names].astype(float)
    centered = features - centers.reindex(feature_names).astype(float)
    max_abs_mean = float(np.abs(centered.mean(axis=0)).max())
    if max_abs_mean > 1e-6:
        raise ValueError(
            f"Centered B features do not have ~zero mean (max abs mean={max_abs_mean:.3e})."
        )
    return centered


def validate_selected_m_workbench(
    selected_m: int,
    *,
    n_rows: int,
    n_features: int,
    min_pcs: int,
    max_pcs: int,
) -> list[str]:
    errors: list[str] = []
    max_allowed = min(n_rows, n_features)
    if selected_m < 1:
        errors.append("selected_m must be >= 1.")
    if selected_m > max_allowed:
        errors.append(f"selected_m={selected_m} exceeds min(n_rows, n_features)={max_allowed}.")
    if selected_m < min_pcs:
        errors.append(f"selected_m={selected_m} is below min_pcs={min_pcs}.")
    if selected_m > max_pcs:
        errors.append(f"selected_m={selected_m} exceeds max_pcs={max_pcs}.")
    return errors


def _link_axis_label(feature_column: str) -> tuple[str, str]:
    return _link_axis(feature_column)


def build_pca_a_loadings_table(
    components: np.ndarray,
    feature_names: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for pc_idx in range(components.shape[0]):
        pc_num = pc_idx + 1
        loadings = components[pc_idx]
        order = np.argsort(-np.abs(loadings))
        for rank, feat_idx in enumerate(order, start=1):
            col = feature_names[feat_idx]
            link_stem, axis = _link_axis_label(col)
            loading = float(loadings[feat_idx])
            rows.append(
                {
                    "pc": pc_num,
                    "feature_column": col,
                    "link_stem": link_stem,
                    "axis": axis,
                    "loading": loading,
                    "abs_loading": abs(loading),
                    "rank_within_pc": rank,
                }
            )
    df = pd.DataFrame(rows)
    return df[PCA_A_LOADINGS_COLUMNS] if not df.empty else pd.DataFrame(columns=PCA_A_LOADINGS_COLUMNS)


def fit_pca_on_centered_a(
    centered_a: pd.DataFrame,
    feature_names: list[str],
    params: PcaAParameters,
) -> PcaATrace:
    """Fit PCA on centered Dataset A only. Does not use Dataset B."""
    from sklearn.decomposition import PCA

    if list(centered_a.columns) != list(feature_names):
        raise ValueError("Feature column order differs from construction plan order.")

    n_rows, n_features = centered_a.shape
    max_components = min(n_rows, n_features)
    if max_components < 1:
        raise ValueError("Insufficient rows/features for PCA on A.")

    pca_full = PCA(n_components=max_components)
    pca_full.fit(centered_a.to_numpy())
    evr = pca_full.explained_variance_ratio_
    cumulative = np.cumsum(evr)

    auto_m = int(np.searchsorted(cumulative, params.variance_threshold) + 1)
    auto_m = min(auto_m, max_components)
    auto_m = max(params.min_pcs, min(auto_m, params.max_pcs))

    if params.selected_m_mode == SELECTED_M_MODE_MANUAL:
        if params.selected_m_override is None:
            raise ValueError("selected_m_override required when selected_m_mode=manual.")
        selected_m = int(params.selected_m_override)
        errors = validate_selected_m_workbench(
            selected_m,
            n_rows=n_rows,
            n_features=n_features,
            min_pcs=params.min_pcs,
            max_pcs=params.max_pcs,
        )
        if errors:
            raise ValueError("; ".join(errors))
        reason = f"manual override selected_m={selected_m}"
    else:
        selected_m = auto_m
        reason = (
            f"auto: smallest m>={params.min_pcs} with cumulative variance "
            f">= {params.variance_threshold:.2f} within max_pcs={params.max_pcs} "
            f"(selected_m={selected_m})"
        )

    components = pca_full.components_[:selected_m]
    evr_selected = evr[:selected_m]

    explained_df = pd.DataFrame(
        {
            "pc": np.arange(1, len(evr) + 1),
            "explained_variance_ratio": evr,
        }
    )
    cumulative_df = pd.DataFrame(
        {
            "pc": np.arange(1, len(cumulative) + 1),
            "cumulative_explained_variance": cumulative,
        }
    )
    loadings = build_pca_a_loadings_table(components, feature_names)

    if not np.isclose(float(evr.sum()), float(cumulative[-1]), rtol=0, atol=1e-12):
        raise ValueError("Explained variance ratios are inconsistent.")

    return PcaATrace(
        feature_names=list(feature_names),
        n_rows=n_rows,
        n_features=n_features,
        selected_m=selected_m,
        selected_m_reason=reason,
        explained_variance=explained_df,
        cumulative_variance=cumulative_df,
        loadings=loadings,
        components=components,
        explained_variance_ratio=evr_selected,
        parameters=params,
    )
