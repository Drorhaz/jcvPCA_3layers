# Results layout — canonical pointers

**Date:** 2026-06-30  
**Purpose:** Lightweight navigation to active research outputs without moving or symlinking large trees.

Machine-readable paths: [`config/paths.yaml`](../../config/paths.yaml)

---

## Active research outputs (on disk)

| Role | Path |
|------|------|
| Canonical Layer 3 batch | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` |
| Poster evidence package | `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` |
| Poster figures | `outputs/poster_final_figures/` |
| Layer 2.5 exports | `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` |
| Nullspace review sidecar | `Layer3_JcvPCA/outputs/nullspace_link_stability_review/` |
| Movement org report | `Layer3_JcvPCA/outputs/movement_organization_question_report/` |

---

## External archives (off-repo)

| Role | Path |
|------|------|
| Layer 2 archive | `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` |
| Stage B cleanup | `../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/` |

---

## `results/` subfolders (placeholders)

| Folder | Intended use |
|--------|----------------|
| `results/active/` | Future symlink or index to current canonical batch |
| `results/poster/` | Poster deliverable index |
| `results/manuscript/` | Manuscript tables/figures index |
| `results/reports/` | Generated report index |
| `results/archive_index/` | Off-repo archive registry |

No symlinks are created in M11 — update this file when promoting a new canonical batch.

---

## Verify paths

```bash
python scripts/check_project_paths.py
```

See [`CONTINUATION_RUNBOOK.md`](../research_recovery/CONTINUATION_RUNBOOK.md) for operational commands.
