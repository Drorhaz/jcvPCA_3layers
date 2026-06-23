"""Joint-link aggregation for Layer 3 JcvPCA.

Axis-level absolute loadings are aggregated to joint-link magnitudes using
root-sum-square (RSS) across the rx/ry/rz triplet. RSS treats the three
rotation-vector axes as a single 3D joint-link magnitude. Simple summation of
absolute components is intentionally NOT used.

This module produces tidy, long-format tables of numbers only. It makes no
interpretive judgement.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from layer3_jcvpca.io import axis_of, link_id_of


def aggregate_axis_to_link_rss(
    A_abs_loadings: np.ndarray,
    B_abs_loadings: np.ndarray,
    feature_names: list[str],
    joint_link_map: dict[str, dict[str, str]],
    pca_A_variance_ratio: np.ndarray | None = None,
    export_weighted: bool = False,
) -> pd.DataFrame:
    """Aggregate axis-level absolute loadings to link-level RSS magnitudes.

    ``A_abs_loadings`` and ``B_abs_loadings`` are ``(selected_m, n_features)``
    arrays of absolute loadings (rows = PCs, columns = features in
    ``feature_names`` order).

    For each PC and each joint-link::

        JRW_A_link  = sqrt(sum_axis A_abs**2)
        JRW_B_link  = sqrt(sum_axis B_abs**2)
        JcvPCA_link = JRW_B_link - JRW_A_link

    Returns a long-format DataFrame with columns:
    ``pc, link_id, JRW_A_link, JRW_B_link, JcvPCA_link`` and, when
    ``export_weighted`` is True, the A-variance-weighted secondary columns.
    """
    feature_index = {feat: i for i, feat in enumerate(feature_names)}
    selected_m = A_abs_loadings.shape[0]

    rows: list[dict] = []
    for pc in range(selected_m):
        for link_id, axes in joint_link_map.items():
            axis_indices = [feature_index[axes[a]] for a in ("rx", "ry", "rz")]
            jrw_a = float(np.sqrt(np.sum(A_abs_loadings[pc, axis_indices] ** 2)))
            jrw_b = float(np.sqrt(np.sum(B_abs_loadings[pc, axis_indices] ** 2)))
            row = {
                "pc": pc + 1,
                "link_id": link_id,
                "JRW_A_link": jrw_a,
                "JRW_B_link": jrw_b,
                "JcvPCA_link": jrw_b - jrw_a,
            }
            if export_weighted:
                if pca_A_variance_ratio is None:
                    raise ValueError(
                        "export_weighted=True requires pca_A_variance_ratio."
                    )
                weight = float(pca_A_variance_ratio[pc])
                row["weight_A_variance_ratio"] = weight
                row["weighted_JcvPCA_link"] = (jrw_b - jrw_a) * weight
            rows.append(row)

    return pd.DataFrame(rows)


def build_axis_table(
    A_abs_loadings: np.ndarray,
    B_abs_loadings: np.ndarray,
    jcvpca_axis: np.ndarray,
    feature_names: list[str],
    pca_A_variance_ratio: np.ndarray,
    pca_B_variance_ratio: np.ndarray,
    export_weighted: bool = False,
) -> pd.DataFrame:
    """Build the long-format axis-level table for one comparison.

    Columns: ``pc, feature, link_id, axis, loading_A_abs,
    loading_B_reprojected_abs, jcvpca_axis, explained_variance_A,
    explained_variance_B_projected`` (+ optional weighted column).
    """
    selected_m = A_abs_loadings.shape[0]
    rows: list[dict] = []
    for pc in range(selected_m):
        for j, feat in enumerate(feature_names):
            row = {
                "pc": pc + 1,
                "feature": feat,
                "link_id": link_id_of(feat),
                "axis": axis_of(feat),
                "loading_A_abs": float(A_abs_loadings[pc, j]),
                "loading_B_reprojected_abs": float(B_abs_loadings[pc, j]),
                "jcvpca_axis": float(jcvpca_axis[pc, j]),
                "explained_variance_A": float(pca_A_variance_ratio[pc]),
                "explained_variance_B_projected": float(pca_B_variance_ratio[pc]),
            }
            if export_weighted:
                row["weighted_jcvpca_axis"] = float(
                    jcvpca_axis[pc, j] * pca_A_variance_ratio[pc]
                )
            rows.append(row)
    return pd.DataFrame(rows)
