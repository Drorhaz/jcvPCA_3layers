# F3 Approved Deletions Log

**Date:** 2026-06-30  
**Phase:** F3  
**Approver:** Phase 2 implementation plan (user approved)

| ID | Path | Action | Restore |
|----|------|--------|---------|
| F3.1 | `Layer3_JcvPCA/outputs/layer3_jcvpca/` | Deleted — dry-validate stub (`sample_dry_validate/validation_report.json` only) | N/A (regenerate via L3 dry-validate) |
| F3.2 | `Layer2.5_Segmentation/outputs/pre_jvpca_review/` | Deleted — typo duplicate; empty manifest CSV header only | N/A; use `pre_jvcpca_review/` |
| F3.3 | L1 QC tracked outputs | Already removed in P1 commit; archived at `../gaga_psylo_external_archive/final_cleanup_2026-06-30/layer1_qc_outputs/` | `mv` from external archive |
| F3.4 | Layer `__pycache__`, `.pytest_cache` | Deleted — regenerates on next run | N/A |

## Validation after F3

```bash
python scripts/run_health_check.py   # exit 0
test ! -e Layer3_JcvPCA/outputs/layer3_jcvpca
test ! -e Layer2.5_Segmentation/outputs/pre_jvpca_review
test -d Layer2.5_Segmentation/outputs/pre_jvcpca_review
```

## Rollback F3.1 / F3.2

Not required — stubs only. F3.3 restore:

```bash
mv ../gaga_psylo_external_archive/final_cleanup_2026-06-30/layer1_qc_outputs/* \
   Layer1_motive_qc/motive_qc/outputs/
```
