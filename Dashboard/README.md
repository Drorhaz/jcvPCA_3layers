# 3Layers Streamlit Dashboard

Thin web UI for the full pipeline: Pre-JcvPCA review (Layer 2.5), Layer 3 JcvPCA analysis, and the Gaga workbench.

Business logic lives in `Layer2.5_Segmentation/src/pre_jvcpca_review` and `Layer3_JcvPCA/src/layer3_jcvpca` — this folder is UI only.

## Run from repo root

```bash
./Dashboard/run_dashboard.sh
# or:
python scripts/run_dashboard.py
```

Opens **http://localhost:8501** with multipage navigation:

| Page | Purpose |
|------|---------|
| **Home** | G2 entry — read-only workflow assistant |
| **Project Overview** | Pipeline status, cohort coverage, canonical batch |
| **Data Readiness** | Participant × session × P-phase traffic lights |
| **Config / Thresholds** | Registry values, badges, invalidation, config hashes |
| **Joint / Link QC** | Advisory inclusion, link/body-region, comparison readiness |
| **Analysis Request Builder** | Validate and export `analysis_request.yaml` (no execution) |
| Layer 3 JcvPCA Analysis | Single-window validation analysis |
| Layer 3 Gaga Workbench | Stepwise inventory → export → JcvPCA pipeline |

The legacy **Pre-JcvPCA Review** single-page app remains at `Dashboard/pre_jvcpca_dashboard.py` (run directly if needed).

## Setup (first time)

Uses the Layer 2.5 venv (`Layer2.5_Segmentation/.venv`). The launch script installs dashboard deps and editable layer packages if needed:

```bash
cd Layer2.5_Segmentation
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt && python -m pip install -e .
cd ..
./Dashboard/run_dashboard.sh
```

Dashboard-specific requirements: [`requirements-dashboard.txt`](requirements-dashboard.txt)

## Tests

```bash
cd Layer2.5_Segmentation
.venv/bin/python -m pytest ../Dashboard/tests/ -q
```

See [`RUN.md`](../RUN.md) for the full pipeline command reference.
