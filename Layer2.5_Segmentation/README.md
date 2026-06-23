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

Web UI replacing the Jupyter notebook for window selection, warnings, and Layer 3 export.

Run all commands from **`Layer2.5_Segmentation/`** (not the repo root):

```bash
cd Layer2.5_Segmentation
source .venv/bin/activate   # after Setup above
python -m pip install -r requirements-dashboard.txt
python -m pip install -e .

# Launch (opens http://localhost:8501)
./scripts/run_pre_jvcpca_dashboard.sh
# or:
streamlit run dashboard/pre_jvcpca_dashboard.py
```

From the **repo root**, use the full path instead:

```bash
pip install -r Layer2.5_Segmentation/requirements-dashboard.txt
```

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
ruff check src tests scripts
```

See `docs/POST_LAYER2_SEGMENTATION_NOTEBOOK_README.md` (Phase 11) for full documentation.
