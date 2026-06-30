# Results layout — canonical pointers

**Date:** 2026-06-30 (updated after F1)  
**Purpose:** Lightweight navigation to active research outputs without moving or symlinking large trees.

Machine-readable paths: [`config/paths.yaml`](../../config/paths.yaml)

---

## Subfolders

| Folder | Purpose |
|--------|---------|
| [`active/`](active/) | Canonical batch pointer |
| [`smoke_tests/`](smoke_tests/) | M12b and future smoke batch pointers |
| [`poster/`](poster/) | Poster figures and evidence index |
| [`reports/`](reports/) | Sidecar report and L2 index pointers |
| [`archive_index/`](archive_index/) | Off-repo archive map |
| [`manuscript/`](manuscript/) | Placeholder |

---

## Active research outputs (on disk)

| Role | Path |
|------|------|
| Canonical Layer 3 batch | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` |
| M12b smoke batch (671) | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` |
| Poster evidence package | `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` |
| Poster figures | `outputs/poster_final_figures/` |
| Layer 2.5 exports | `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` |
| Nullspace review sidecar | `Layer3_JcvPCA/outputs/nullspace_link_stability_review/` |
| Movement org report | `Layer3_JcvPCA/outputs/movement_organization_question_report/` |

---

## External archives (off-repo)

| Role | Path |
|------|------|
| F2 cleanup archive | `../gaga_psylo_external_archive/final_cleanup_2026-06-30/` |
| Layer 2 archive | `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` |
| Stage B cleanup | `../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/` |

Detail: [`archive_index/EXTERNAL_ARCHIVE.md`](archive_index/EXTERNAL_ARCHIVE.md)

---

## Verify paths

```bash
python scripts/check_project_paths.py
```

See [`CONTINUATION_RUNBOOK.md`](../research_recovery/CONTINUATION_RUNBOOK.md) for operational commands.
