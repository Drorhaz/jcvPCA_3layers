# RUN — 3Layers JcvPCA Pipeline

**Start here.** Copy-paste commands from repo root unless noted.

| Doc | Use |
|-----|-----|
| [`README_WORKING.md`](README_WORKING.md) | Daily narrative, don't-touch list |
| [`docs/DATA_MAP.md`](docs/DATA_MAP.md) | Raw → processed → batch map |
| [`results/`](results/) | Categorized result indexes |
| [`docs/research_recovery/CONTINUATION_RUNBOOK.md`](docs/research_recovery/CONTINUATION_RUNBOOK.md) | Extended reference |

---

## 1. Health check (always first)

```bash
cd /path/to/3Layers_project
python scripts/run_health_check.py
# or: python scripts/check_project_paths.py
```

Exit code **0** = all required registry paths exist.

---

## 2. Python environments

| Layer | venv |
|-------|------|
| Layer 1 QC | `Layer1_motive_qc/motive_qc/.venv/bin/python` |
| Layer 2 kinematics | `Layer2_Motive_Kinematics/.venv/bin/python` |
| Layer 2.5 segmentation | `Layer2.5_Segmentation/.venv/bin/python` |
| Layer 3 JcvPCA | `Layer3_JcvPCA/.venv/bin/python` |

Root wrappers (preferred after P4): `python scripts/run_layer*.py`

---

## 3. Canonical batch (do not overwrite)

| Item | Value |
|------|-------|
| Batch ID | `gaga_batch_jcvpca_20260626_193319` |
| On disk | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` |
| Index | [`results/active/CANONICAL_BATCH.md`](results/active/CANONICAL_BATCH.md) |
| Config key | `layer3.canonical_batch` in [`config/paths.yaml`](config/paths.yaml) |

Verify:

```bash
python -c "
import sys; sys.path.insert(0,'src')
from project_paths import load_project_paths
p = load_project_paths()
print('canonical_batch_id:', p.layer3_canonical_batch_id)
print('canonical_batch:', p.layer3_canonical_batch)
print('exists:', p.layer3_canonical_batch.is_dir())
"
```

**Never overwrite** the canonical batch folder. New runs use a **new timestamped** `--output-dir`.

---

## 4. Layer 1 — Motive QC

```bash
cd Layer1_motive_qc/motive_qc
.venv/bin/python motive_batch_qc.py --config config.yaml --discover
.venv/bin/python motive_batch_qc.py --config config.yaml --subject 671 --verbose
```

Raw data: `Layer1_motive_qc/motive_qc/data/` (yaml: `raw_data.layer1`).

---

## 5. Layer 2 — Kinematics sessions

```bash
cd Layer2_Motive_Kinematics
.venv/bin/python -m layer2_motive.cli --help
```

Active session outputs: `Layer2_Motive_Kinematics/outputs/*_Take_*/`  
Raw inputs: `Layer2_Motive_Kinematics/data/{671,252}/`

---

## 6. Layer 2.5 — Gaga exports

```bash
cd Layer2.5_Segmentation
.venv/bin/python scripts/build_gaga_exports.py --help
ls outputs/pre_jvcpca_review/671/
```

Export root: `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` (yaml: `layer2_5.pre_jvcpca_review`).

252 manifest: `Layer2.5_Segmentation/config/group4_core_16link_within_252_feature_manifest.csv`

---

## 7. Layer 3 — Batch run (new timestamped output)

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python run_gaga_batch_jcvpca.py --help
../.venv/bin/python run_gaga_batch_jcvpca.py \
  --layer25-root ../../Layer2.5_Segmentation/outputs/pre_jvcpca_review \
  --output-dir ../outputs/gaga_batch_jcvpca_$(date -u +%Y%m%d_%H%M%S)
```

Paths resolve from `config/paths.yaml` when `--layer25-root` is omitted.

---

## 8. Layer 3 — Validate (read-only, no regeneration)

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_final_integrated_review.py --validate-paths
../.venv/bin/python generate_master_full_numeric_report.py --dry-run
../.venv/bin/python generate_directional_robustness_full_numeric_report.py --validate-paths
../.venv/bin/python generate_nullspace_full_numeric_report.py --dry-run
../.venv/bin/python generate_movement_organization_question_report.py --validate-paths
```

---

## 9. Promote a new canonical batch

Only after reviewing a new batch folder:

1. Edit `config/paths.yaml` — update `layer3.canonical_batch_id` and `layer3.canonical_batch`
2. Run `python scripts/run_health_check.py`
3. Re-run validators with `--batch-dir` if needed
4. Document in `results/archive_index/`

**Never delete** batch `193319` without explicit backup plan.

---

## 10. Poster figures

```bash
python scripts/make_poster_final_figures.py --help
python scripts/make_poster_671_figures.py --help
```

Output: `outputs/poster_final_figures/` (index: [`results/poster/`](results/poster/))

---

## 11. Results map

| What | Where |
|------|-------|
| Canonical batch | [`results/active/`](results/active/) |
| Smoke tests | [`results/smoke_tests/`](results/smoke_tests/) |
| Poster deliverables | [`results/poster/`](results/poster/) |
| Sidecar reports | [`results/reports/`](results/reports/) |
| External archives | [`results/archive_index/EXTERNAL_ARCHIVE.md`](results/archive_index/EXTERNAL_ARCHIVE.md) |

---

## 12. Do not touch

| Path | Why |
|------|-----|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | Frozen canonical batch |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | Poster evidence chain |
| `outputs/poster_final_figures/` | Poster figures |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/` | Active exports |
| `**/data/**` raw CSVs | Immutable inputs |
| `../gaga_psylo_external_archive/` | Off-repo archives |

---

## 13. External archive restore

Scratch and L1 QC outputs archived under:

```
../gaga_psylo_external_archive/final_cleanup_2026-06-30/
├── layer1_qc_outputs/
├── layer3_workbench_scratch/
└── smoke_batch_671_20260630/   (after P3 archive)
```

See [`results/archive_index/EXTERNAL_ARCHIVE.md`](results/archive_index/EXTERNAL_ARCHIVE.md).

---

*Updated Phase 2 P1 — primary runner surface.*
