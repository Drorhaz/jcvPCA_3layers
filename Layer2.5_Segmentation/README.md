> **Navigation:** prefer [`RUN.md`](../RUN.md) and [`docs/DATA_MAP.md`](../docs/DATA_MAP.md). Runnable code stays in this folder.

# Layer 2.5 — Post-Layer 2 Segmentation Review

Interactive per-session segmentation review bridging Layer 1 marker QC and Layer 2 kinematic exports.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Pre-JcvPCA review dashboard (recommended)

Web UI for window selection, warnings, and Layer 3 export. **Canonical location:** [`Dashboard/`](../Dashboard/) at repo root (thin client over `pre_jvcpca_review`).

```bash
# From repo root (preferred)
./Dashboard/run_dashboard.sh
# or:
python scripts/run_dashboard.py
```

Opens http://localhost:8501. See [`Dashboard/README.md`](../Dashboard/README.md) for setup and pages.

Legacy redirect: `Layer2.5_Segmentation/scripts/run_pre_jvcpca_dashboard.sh` forwards to the same launcher.

**Workflow:** set Layer 1 / Layer 2 roots in the sidebar → **Discover** → pick participant & session → load segmentation xlsx (auto-detects per-session exercise windows) → configure joints via checkbox filters → **Preview warnings** → **Export Layer 3 window**.

Window labels auto-generate as `{session_id}_s{start}_e{end}` (or `{session_id}_g4_s{start}_e{end}` for the Group 4 bundle).

The legacy notebook remains at `notebooks/pre_jvcpca_review.ipynb` but the dashboard is the preferred control interface.

## CLI validation (Phase 0–4 acceptance gate)

```bash
python scripts/validate_segmentation_inputs.py \
  --layer1-dir input/Layer1_QC/QC_671_T1_P1_R1 \
  --layer2-dir input/Layer2_Kinematics/671_T1_P1_R1 \
  --out outputs/segmentation_validation/671_T1_P1_R1
```

## Tests

```bash
pytest
pytest ../Dashboard/tests/   # dashboard session-state helpers
ruff check src tests scripts
```

See `docs/POST_LAYER2_SEGMENTATION_NOTEBOOK_README.md` (Phase 11) for full documentation.
