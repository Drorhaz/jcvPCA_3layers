"""Exploratory JRW distribution / democracy metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _normalized_entropy(values: np.ndarray) -> float:
    v = np.abs(values.astype(float))
    total = v.sum()
    if total <= 0:
        return 0.0
    p = v / total
    p = p[p > 0]
    h = -np.sum(p * np.log(p))
    h_max = np.log(len(v)) if len(v) > 1 else 1.0
    return float(h / h_max) if h_max > 0 else 0.0


def _gini(values: np.ndarray) -> float:
    v = np.sort(np.abs(values.astype(float)))
    n = len(v)
    if n == 0 or v.sum() == 0:
        return 0.0
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * v) / (n * v.sum())) - (n + 1) / n)


def compute_jrw_distribution_metrics(
    link_df: pd.DataFrame,
    *,
    value_col: str = "JcvPCA_link",
    pc: int | None = None,
) -> dict:
    """Compute descriptive distribution metrics for link-level JRW/JcvPCA magnitudes."""
    df = link_df.copy()
    if pc is not None and "pc" in df.columns:
        df = df[df["pc"] == pc]
    if df.empty:
        return {}

    # Aggregate across PCs by mean absolute link magnitude
    agg = df.groupby("link_id")[value_col].apply(lambda s: np.mean(np.abs(s))).sort_values(ascending=False)
    values = agg.to_numpy()
    total = values.sum()
    cum = np.cumsum(values / total) if total > 0 else values

    return {
        "normalized_entropy": _normalized_entropy(values),
        "gini_coefficient": _gini(values),
        "top1_joint_share": float(values[0] / total) if total > 0 and len(values) else 0.0,
        "top3_joint_share": float(values[:3].sum() / total) if total > 0 else 0.0,
        "effective_number_of_joints": float(1.0 / np.sum((values / total) ** 2))
        if total > 0
        else 0.0,
        "n_links": len(values),
        "cumulative_curve": cum.tolist(),
        "link_ranking": agg.reset_index().rename(columns={value_col: "mean_abs_value"}),
    }
