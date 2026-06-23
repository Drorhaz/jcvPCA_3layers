"""Main vs natural-variability comparison tables."""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_main_vs_nv_table(
    main_link_df: pd.DataFrame,
    nv_link_df: pd.DataFrame,
    *,
    epsilon: float = 1e-6,
) -> pd.DataFrame:
    """Compare main ΔJRW against NV ΔJRW per link (aggregated across PCs)."""
    main = (
        main_link_df.groupby("link_id")["JcvPCA_link"]
        .apply(lambda s: float(np.mean(np.abs(s))))
        .rename("main_abs_delta_jrw")
    )
    nv = (
        nv_link_df.groupby("link_id")["JcvPCA_link"]
        .apply(lambda s: float(np.mean(np.abs(s))))
        .rename("nv_abs_delta_jrw")
    )
    out = pd.concat([main, nv], axis=1).reset_index()
    out["main_minus_nv"] = out["main_abs_delta_jrw"] - out["nv_abs_delta_jrw"]
    out["ratio"] = np.where(
        out["nv_abs_delta_jrw"] > epsilon,
        out["main_abs_delta_jrw"] / out["nv_abs_delta_jrw"],
        np.nan,
    )
    out["ratio_hidden"] = out["nv_abs_delta_jrw"] <= epsilon
    out["exceeds_nv"] = out["main_abs_delta_jrw"] > out["nv_abs_delta_jrw"]
    out = out.sort_values("main_minus_nv", ascending=False)
    return out
