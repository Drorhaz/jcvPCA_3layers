# Research Continuation Runbook

**Date:** 2026-06-30  
**Mode:** Research continuation — poster complete, canonical batch frozen  
**Prerequisites:** [`config/paths.yaml`](../../config/paths.yaml), [`src/project_paths.py`](../../src/project_paths.py)

---

## 1. Path check (always first)

```bash
cd /path/to/3Layers_project
python scripts/check_project_paths.py
```

Exit code **0** means registry paths exist. Fix missing paths before any export or batch run.

---

## 2. Current canonical batch

| Item | Value |
|------|-------|
| **Batch ID** | `gaga_batch_jcvpca_20260626_193319` |
| **On disk** | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` |
| **Config key** | `layer3.canonical_batch` in `config/paths.yaml` |

Verify without opening outputs:

```bash
python -c "
from pathlib import Path
import sys; sys.path.insert(0,'src')
from project_paths import load_project_paths
p = load_project_paths()
print('canonical_batch_id:', p.layer3_canonical_batch_id)
print('canonical_batch:', p.layer3_canonical_batch)
print('exists:', p.layer3_canonical_batch.is_dir())
"
```

**Do not overwrite** the canonical batch folder unless you explicitly promote a new run (Section 7).

---

## 3. Participant 671 — continue existing work

671 has active Layer 2 sessions, Layer 2.5 g4 exports, and is in the canonical batch.

**Check Layer 2.5 exports:**

```bash
ls Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/
```

**Refresh session index (if new L2 sessions added):**

Use the Layer 2.5 dashboard or `pre_jvcpca_review` notebook — do not delete existing 671 export folders.

**Re-validate read-only reports (no regeneration required):**

```bash
cd Layer3_JcvPCA/scripts
python generate_final_integrated_review.py --validate-paths
python generate_master_full_numeric_report.py --dry-run
```

---

## 4. Participant 252 — onboarding

252 is in `participants.batch_cohort` but may need additional Layer 2 / 2.5 / batch coverage.

**Check raw Layer 2 data (do not commit raw CSVs):**

```bash
ls Layer2_Motive_Kinematics/data/252/ 2>/dev/null || echo "No L2 raw tree"
ls Layer2_Motive_Kinematics/outputs/*252* 2>/dev/null | head
```

**Layer 2 processing:** Run Layer 2 pipeline for 252 `*_Take_*` sessions into active `Layer2_Motive_Kinematics/outputs/` (not external archive).

**Layer 2.5 export:**

```bash
# From repo root, with Layer 2.5 env active:
cd Layer2.5_Segmentation
python scripts/build_gaga_exports.py --help   # inspect flags before running
```

Export g4 windows under `Layer2.5_Segmentation/outputs/pre_jvcpca_review/252/`.

**252 feature manifest:** `Layer2.5_Segmentation/config/group4_core_16link_within_252_feature_manifest.csv`

---

## 5. Layer 2.5 export (general)

| Input | Path |
|-------|------|
| L2.5 review root | `Layer2.5_Segmentation/outputs/pre_jvcpca_review` |
| L2 active outputs | `Layer2_Motive_Kinematics/outputs/*_Take_*/` |
| Segmentation xlsx | `Layer2.5_Segmentation/segmentation/` |

Central manifest and window exports live under `pre_jvcpca_review/<participant>/`.

**Do not** commit generated export trees to Git (gitignored).

---

## 6. Layer 3 batch (new timestamped run)

**Entry point:**

```bash
cd Layer3_JcvPCA/scripts
python run_gaga_batch_jcvpca.py --help
```

**Typical invocation (creates NEW folder — safe default):**

```bash
cd Layer3_JcvPCA/scripts
python run_gaga_batch_jcvpca.py \
  --layer25-root ../../Layer2.5_Segmentation/outputs/pre_jvcpca_review \
  --output-dir ../outputs/gaga_batch_jcvpca_$(date -u +%Y%m%d_%H%M%S)
```

Paths resolve from `config/paths.yaml` when `--layer25-root` is omitted.

**After batch completes:**

1. Review batch summary under the new `outputs/gaga_batch_jcvpca_<timestamp>/` folder.
2. Run sidecar analyses only if explicitly approved (M12 — not auto-run).
3. Promote to canonical only after review (Section 7).

**Validate paths without running batch:**

```bash
python scripts/check_project_paths.py
cd Layer3_JcvPCA/scripts
python run_gaga_batch_jcvpca.py --help
```

---

## 7. Promote a new canonical batch

Only after reviewing a new batch folder:

1. Edit `config/paths.yaml`:

   ```yaml
   layer3:
     canonical_batch_id: "gaga_batch_jcvpca_<NEW_TIMESTAMP>"
     canonical_batch: "Layer3_JcvPCA/outputs/gaga_batch_jcvpca_<NEW_TIMESTAMP>"
   ```

2. Verify:

   ```bash
   python scripts/check_project_paths.py
   ```

3. Re-run read-only report validators with `--batch-dir` if needed:

   ```bash
   cd Layer3_JcvPCA/scripts
   python generate_master_full_numeric_report.py --batch-dir ../outputs/gaga_batch_jcvpca_<NEW> --validate-paths
   ```

4. Document promotion in `results/archive_index/` (optional).

**Never delete** the old `193319` batch unless explicitly planned and backed up.

---

## 8. What NOT to overwrite

| Path | Reason |
|------|--------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | Canonical poster-era batch |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | Poster evidence chain |
| `outputs/poster_final_figures/` | Poster figures |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/` | Active 671 exports |
| `**/data/**` raw kinematic CSVs | Immutable inputs |
| `../gaga_psylo_external_archive/` | Off-repo archives |

---

## 9. Read-only report regeneration (optional)

Reports load paths from config. Dry-run / validate only unless explicitly regenerating:

```bash
cd Layer3_JcvPCA/scripts
python generate_directional_robustness_full_numeric_report.py --validate-paths
python generate_nullspace_full_numeric_report.py --dry-run
python generate_movement_organization_question_report.py --validate-paths
```

Full regeneration overwrites markdown **outside** the canonical batch (or sidecar paths) — approve before running without `--dry-run`.

---

## 10. External archives

| Archive | Path |
|---------|------|
| Layer 2 historical | `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` |
| Stage B cleanup | `../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/` |

See [`R1_LAYER2_ARCHIVE_EXTERNAL_MOVE.md`](R1_LAYER2_ARCHIVE_EXTERNAL_MOVE.md).

---

## 11. Starting new analysis (M12 — explicit approval required)

When ready to **run** (not just validate):

```bash
python scripts/check_project_paths.py
cd Layer3_JcvPCA/scripts
python run_gaga_batch_jcvpca.py \
  --layer25-root ../../Layer2.5_Segmentation/outputs/pre_jvcpca_review \
  --output-dir ../outputs/gaga_batch_jcvpca_$(date -u +%Y%m%d_%H%M%S)
```

Then follow project-specific analysis scripts documented in `Layer3_JcvPCA/README.md`.

**This runbook does not authorize M12 execution by itself** — obtain explicit approval first.

---

## Related docs

- [`MASTER_CONTINUATION_PLAN.md`](MASTER_CONTINUATION_PLAN.md)
- [`R5_RESEARCH_CONTINUATION_STATUS.md`](R5_RESEARCH_CONTINUATION_STATUS.md)
- [`R3_CANONICAL_PATHS.md`](R3_CANONICAL_PATHS.md)
