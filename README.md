# jcvPCA Three-Layer Pipeline

Adaptation of the JcvPCA computational framework to OptiTrack/Motive-derived Gaga movement data. The pipeline transforms raw optical marker captures into filtered parent-child relative rotation-vector features, supports interactive segmentation review, and prepares windowed matrices for JcvPCA coordination analysis.

**Scientific framing:** filtered parent-child relative rotation-vector features derived from Motive-solved global bone quaternions, supported by raw marker quality control — not direct encoder-based anatomical joint-angle measurement.

---

## Three-layer architecture

```text
Layer 1 — Raw marker QC          (Layer1_motive_qc/motive_qc/)
Layer 2 — Solved skeleton kinematics (Layer2_Motive_Kinematics/)
Layer 2.5 — Segmentation + pre-JcvPCA review (Layer2.5_Segmentation/)
Layer 3 — JcvPCA coordination analysis (planned; see 3_layers_Matser_plan_Full/)
```

Data flow:

```text
Raw marker CSV
  → Layer 1 QC (gaps, artifacts, qc_mask)
  → Motive mixed CSV with global bone quaternions
  → Layer 2 kinematic feature extraction (filtered relative rotation vectors)
  → Layer 2.5 segmentation review + window export
  → Layer 3 JcvPCA (planned)
```

Primary analytical focus (from master plan): **Group 4 — Curvilinear exploration**; secondary: **Group 5 — Single-leg balance with whole-body curves**.

---

## Repository structure

| Path | Role |
|------|------|
| `3_layers_Matser_plan_Full/` | Master plan, pseudocode, scope addendum |
| `Layer1_motive_qc/motive_qc/` | Layer 1 — raw Motive marker QC pipeline |
| `Layer2_Motive_Kinematics/` | Layer 2 — quaternion → filtered rotvec features |
| `Layer2.5_Segmentation/` | Post-Layer 2 segmentation review + pre-JcvPCA export |
| `671_test_data_des/` | Sample data-description sidecar (raw CSV excluded) |

Each layer is a self-contained Python project with its own `pyproject.toml` or `requirements.txt`, configs, tests, and documentation.

---

## What is included in Git

This repository intentionally includes **documentation, configuration, source code, tests, notebooks, and small outputs/reports** so a reviewer can understand the full project without local data.

**Included by default:**

- Source code, scripts, tests, notebooks
- Markdown plans, specs, implementation notes
- Configuration files and small sample/fixture CSVs
- QC reports (`.md`, `.html`, `.json`), summary tables, plots
- Small output summaries in `outputs/` (validation reports, stage reports, index files)
- Layer 1 example run for session `671_T1_P1_R1` (tables, plots, HTML report)
- Layer 2 stage reports and small CSVs for session `671_T1_P1_R1`
- Layer 2.5 `pre_jvcpca_review/` and `segmentation_validation/` outputs

---

## What is excluded from Git

Heavy, raw, or easily regenerated data is excluded via `.gitignore`:

| Category | Examples | Reason |
|----------|----------|--------|
| Raw Motive CSV exports | `data/**/*.csv`, `671_test_data_des/*_Take*.csv` | 100–230 MB per file; participant capture data |
| Parquet / numpy arrays | `*.parquet`, `*.npy`, `*.npz` | Large intermediate matrices; regenerate from pipeline |
| Frame-level kinematic CSVs | `relative_quaternions.csv`, `filtered_relative_rotation_vectors.csv`, etc. | 100–780 MB; regenerate from Layer 2 |
| Frame-level QC event dumps | `combined_qc_events.csv`, `qc_event_display.csv` | 5–63 MB debug exports; regenerate from notebook |
| Virtual environments | `.venv/`, `venv/` | Local install only |
| Nested git history | `Layer1_motive_qc/motive_qc/.git/` | Absorbed into monorepo |

See folder-level `README.md` files in `data/` and `outputs/` directories for regeneration instructions.

---

## How to run the pipeline

### Layer 1 — Raw marker QC

```bash
cd Layer1_motive_qc/motive_qc
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Place Motive CSVs under data/{subject_id}/, then:
python motive_raw_qc.py --config config.yaml --verbose \
  --input "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv"
```

See [`Layer1_motive_qc/motive_qc/README.md`](Layer1_motive_qc/motive_qc/README.md).

### Layer 2 — Kinematics

```bash
cd Layer2_Motive_Kinematics
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

layer2-motive run-until --input /path/to/motive.csv --stage 08 --output-dir outputs/session_name
```

See [`Layer2_Motive_Kinematics/scripts/README.md`](Layer2_Motive_Kinematics/scripts/README.md).

### Layer 2.5 — Segmentation review

```bash
cd Layer2.5_Segmentation
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

python scripts/validate_segmentation_inputs.py \
  --layer1-dir input/Layer1_QC/QC_671_T1_P1_R1 \
  --layer2-dir input/Layer2_Kinematics/671_T1_P1_R1 \
  --out outputs/segmentation_validation/671_T1_P1_R1
```

Open `notebooks/post_layer2_segmentation_review.ipynb` and `notebooks/pre_jvcpca_review.ipynb` for interactive review.

See [`Layer2.5_Segmentation/README.md`](Layer2.5_Segmentation/README.md).

---

## Implementation status

| Layer | Status | Notes |
|-------|--------|-------|
| **Layer 1** | Implemented (v0.6.0) | Full L1–L5 QC pipeline, batch mode, notebooks, `qc_mask.csv` deliverable |
| **Layer 2** | Implemented (stages 00–08) | Parser through filtered rotvecs; validated on subject 671 sessions |
| **Layer 2.5** | In progress | Segmentation validation, interactive notebooks, pre-JcvPCA window export |
| **Layer 3** | Planned | Pseudocode and master plan complete; JcvPCA execution not yet implemented |

Reference session for development: **`671_T1_P1_R1`**.

---

## Where to start (reviewer guide)

1. **[`3_layers_Matser_plan_Full/MASTER_PLAN.md`](3_layers_Matser_plan_Full/MASTER_PLAN.md)** — overall architecture and scientific scope
2. **[`Layer1_motive_qc/motive_qc/README.md`](Layer1_motive_qc/motive_qc/README.md)** — Layer 1 QC pipeline and deliverables
3. **[`Layer2_Motive_Kinematics/00_README_LAYER2_OVERVIEW.md`](Layer2_Motive_Kinematics/00_README_LAYER2_OVERVIEW.md)** — Layer 2 stage overview
4. **[`Layer2.5_Segmentation/POST_LAYER2_SEGMENTATION_NOTEBOOK_PLAN_DECISION_SCOPE_REVISED.md`](Layer2.5_Segmentation/POST_LAYER2_SEGMENTATION_NOTEBOOK_PLAN_DECISION_SCOPE_REVISED.md)** — Layer 2.5 design decisions
5. **[`3_layers_Matser_plan_Full/layer3 psuedocode.txt`](3_layers_Matser_plan_Full/layer3%20psuedocode.txt)** — Layer 3 planned logic
6. **Example outputs:** Layer 1 run at `Layer1_motive_qc/motive_qc/outputs/runs/671_T1_P1_R1_*`; Layer 2 reports at `Layer2_Motive_Kinematics/outputs/671_T1_P1_R1_*`; Layer 2.5 at `Layer2.5_Segmentation/outputs/pre_jvcpca_review/session_window/`

---

## License / citation

Academic research tooling. Cite session manifests, `config_used.yaml`, and run reports for reproducibility.
