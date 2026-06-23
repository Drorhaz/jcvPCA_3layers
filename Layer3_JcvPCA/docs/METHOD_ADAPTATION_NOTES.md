# Layer 3 method-adaptation notes

This document records exactly where the Layer 3 implementation follows the
paper's `S1_File.py` JcvPCA sequence and where it deliberately adapts it. It is
a method description, not a scientific claim. This package emits numbers only;
it does not classify changes as significant, robust, meaningful, or beyond
variability.

## Preserved from the paper (`S1_File.py`, JcvPCA section only)

The core sequence in `core.py: compute_jcvpca` matches the paper lines ~82-106:

1. center A independently (`A - A.mean()`);
2. fit `PCA` on A; keep `pca_A.components_` and `explained_variance_ratio_`;
3. center B independently (`B - B.mean()`);
4. project B into A's PCA space by `np.matmul(B_centered, pca_A_frame.T)`;
5. fit `PCA` on the projected B;
6. re-express B loadings via `np.matmul(pca_B_frame, pca_A_frame)`;
7. `JcvPCA_axis = abs(B_reprojected) - abs(A)`.

Libraries are restricted to `numpy`, `pandas`, and
`sklearn.decomposition.PCA`, as in the paper.

## Deliberate adaptations (minimum needed for this data)

- Variable feature count: the paper uses two scalar joints; here there are many
  `_rx/_ry/_rz` feature columns.
- Variable `selected_m`: the paper hardcodes `n_components=2`. Here `selected_m`
  is the smallest number of A-PCs reaching `variance_threshold` (default 0.90),
  computed from A only, optionally overridden by config and re-validated.
- Subspace re-expression: when `selected_m < n_features`, `pca_A_frame` is
  `(selected_m, n_features)` and `pca_B_frame @ pca_A_frame` re-expresses B's
  PCs within A's retained subspace. This is the paper's square-frame reprojection
  generalised to a retained subspace.
- Joint-link RSS aggregation: the paper uses scalar joints. Here each parent-child
  link has an rx/ry/rz triplet; link magnitude uses root-sum-square across the
  triplet (`aggregation.py`). Simple summation is intentionally not used.
- Manifest-driven A/B construction, validation gates, and neutral output writers
  are project infrastructure with no analogue in the paper script.

## Explicitly excluded from the paper script

Simulation/sample-data generation, all plotting (`matplotlib`, `%matplotlib tk`),
the CRP/JsvCRP section, and `shapely` polygon-area logic are not ported.

## Forbidden choices (asserted by tests)

- `PCA_A.transform(B_raw)` is never used (it would apply A's mean to B);
- no z-scoring, variance-scaling, or range-normalisation;
- B is centered by its own mean, never A's mean;
- `selected_m` is chosen from A only.

## Project-specific implementation decisions (not from any reference)

- `tests/conftest.py` synthetic fixtures for deterministic unit tests;
- `export_weighted` config flag (default `false`); weighted columns are A-variance
  weighted secondary outputs only;
- `min_rows_for_pca` computational floor;
- `selected_m` validated against both A and B dimensions before PCA;
- YAML config format (`pyyaml`).
