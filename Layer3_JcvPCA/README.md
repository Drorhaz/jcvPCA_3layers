# Layer 3 JcvPCA (V1)

JcvPCA-style comparison of Motive-derived parent-child relative rotation-vector
contribution structure. V1 implements only **Group 4, group-level,
cross-repetition** analysis with T1 as the reference condition.

This package is computational and auditable. It emits numbers only and does
**not** classify changes as significant, robust, meaningful, or beyond
variability. Those judgements are made later, outside this package (e.g. in a
notebook).

Layer 3 is independent of Layers 1, 2, and 2.5 and does not modify them. It
consumes Layer 2.5 JcvPCA-ready matrices as read-only input.

## Install

```bash
cd Layer3_JcvPCA
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

The run mode is read from the config file (`mode: dry_validate` or `mode: full`).

```bash
python scripts/run_layer3_jcvpca.py --config config/layer3_config.yaml
```

- `dry_validate`: loads every included matrix in the manifest and runs schema
  validation only (no A/B comparisons, no PCA, no interpretation). Writes
  `outputs/layer3_jcvpca/validation_report.json`.
- `full`: requires all six Group 4 matrices; builds A_T1/B_T2/B_T3/NV_T1, runs
  the three comparisons, and writes all neutral outputs. Deferred until all
  inputs are provided and approved.

## V1 datasets and comparisons

```text
A_T1  = A_T1_R1 + A_T1_R2
B_T2  = B_T2_R1 + B_T2_R2
B_T3  = B_T3_R1 + B_T3_R2
NV_T1 = A_T1_R1 vs A_T1_R2   (natural-variability reference; not a statistical test)

compute_jcvpca(A_T1, B_T2)
compute_jcvpca(A_T1, B_T3)
compute_jcvpca(A_T1_R1, A_T1_R2)
```

## Input contract

Each matrix is one repetition with metadata columns `session_id, run_label,
frame, time_sec` and feature columns ending in `_rx/_ry/_rz`. Only feature
columns enter PCA. See `docs/LAYER3_SCOPE.md` and `docs/METHOD_ADAPTATION_NOTES.md`.

## Outputs (`outputs/layer3_jcvpca/`)

`validation_report.json`, `analysis_metadata.json`, `explained_variance.csv`,
`jrw_axis.csv`, `jcvpca_axis.csv`, `jrw_link.csv`, `jcvpca_link.csv`,
`natural_variability_t1.csv`, `interpretation_summary.md`.

## Tests

```bash
pytest -q
```
