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
