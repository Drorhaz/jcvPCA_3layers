"""Core JcvPCA computation.

This module preserves the computational sequence of the paper's ``S1_File.py``
(the JcvPCA section only), generalised to many feature columns and a variable
number of retained principal components.

Sequence (matching the paper):
    1. center A independently;
    2. fit PCA on A;
    3. center B independently;
    4. manually project B into A's PCA space via matrix multiplication;
    5. fit PCA on the projected B;
    6. re-express B loadings in the original feature space (pca_B_frame @ pca_A_frame);
    7. JcvPCA_axis = abs(B_reprojected_loadings) - abs(A_loadings).

Forbidden (and intentionally not used here):
    - PCA_A.transform(B_raw)  (would apply A's fitted mean to B);
    - z-scoring / variance-scaling / range-normalisation;
    - any alternative PCA-space comparison method.

This module computes numbers only. It makes no judgement about whether a change
is significant, robust, meaningful, or beyond variability.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from layer3_jcvpca.validation import validate_selected_m


def select_selected_m_from_A(
    A_data: pd.DataFrame,
    feature_names: list[str],
    variance_threshold: float = 0.90,
) -> tuple[int, pd.DataFrame]:
    """Choose ``selected_m`` from A only.

    Fits a full PCA on independently-centered A and returns the smallest number
    of components whose cumulative explained-variance ratio reaches
    ``variance_threshold``, together with a per-PC explained-variance table.

    The rule is a computational default, not a scientific conclusion.
    """
    A_centered = A_data[feature_names] - A_data[feature_names].mean()
    max_components = min(A_centered.shape[0], A_centered.shape[1])
    pca_full = PCA(n_components=max_components)
    pca_full.fit(A_centered)

    evr = pca_full.explained_variance_ratio_
    cumulative = np.cumsum(evr)
    selected_m = int(np.searchsorted(cumulative, variance_threshold) + 1)
    selected_m = min(selected_m, max_components)

    evr_table = pd.DataFrame(
        {
            "pc": np.arange(1, len(evr) + 1),
            "explained_variance_ratio": evr,
            "cumulative_explained_variance": cumulative,
        }
    )
    return selected_m, evr_table


def compute_jcvpca(
    A_data: pd.DataFrame,
    B_data: pd.DataFrame,
    feature_names: list[str],
    variance_threshold: float = 0.90,
    selected_m: int | None = None,
    min_rows_for_pca: int = 10,
) -> dict:
    """Compute axis-level JcvPCA comparing B against reference A.

    Returns a dict of arrays/tables. No interpretation is attached.
    """
    if selected_m is None:
        selected_m, evr_table_full = select_selected_m_from_A(
            A_data, feature_names, variance_threshold
        )
    else:
        _, evr_table_full = select_selected_m_from_A(
            A_data, feature_names, variance_threshold
        )

    validate_selected_m(
        selected_m=selected_m,
        n_features_A=len(feature_names),
        n_rows_A=len(A_data),
        n_rows_B=len(B_data),
        min_rows_for_pca=min_rows_for_pca,
    )

    # Step 1: center A independently.
    A_centered = A_data[feature_names] - A_data[feature_names].mean()

    # Step 2: fit PCA on A.
    pca_A = PCA(n_components=selected_m)
    pca_A.fit(A_centered)
    pca_A_frame = pca_A.components_
    pca_A_variance_ratio = pca_A.explained_variance_ratio_

    # Step 3: center B independently (NOT with A's mean).
    B_centered = B_data[feature_names] - B_data[feature_names].mean()

    # Step 4: manually project B into A's PCA space.
    B_projected = np.matmul(B_centered.to_numpy(), pca_A_frame.transpose())

    # Step 5: fit PCA on the projected B.
    pca_B = PCA(n_components=selected_m)
    pca_B.fit(B_projected)
    pca_B_frame = pca_B.components_
    pca_B_variance_ratio = pca_B.explained_variance_ratio_

    # Step 6: re-express B loadings in the original feature space.
    B_reprojected_loadings = np.matmul(pca_B_frame, pca_A_frame)

    A_abs_loadings = np.abs(pca_A_frame)
    B_abs_loadings = np.abs(B_reprojected_loadings)

    # Step 7: axis-level JcvPCA.
    jcvpca_axis = B_abs_loadings - A_abs_loadings

    return {
        "feature_names": list(feature_names),
        "selected_m": int(selected_m),
        "variance_threshold": float(variance_threshold),
        "pca_A_frame": pca_A_frame,
        "pca_A_variance_ratio": pca_A_variance_ratio,
        "pca_B_variance_ratio": pca_B_variance_ratio,
        "A_abs_loadings": A_abs_loadings,
        "B_abs_loadings": B_abs_loadings,
        "jcvpca_axis": jcvpca_axis,
        "explained_variance_table_A": evr_table_full,
    }
