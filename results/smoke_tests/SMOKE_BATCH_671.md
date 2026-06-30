# M12b smoke batch pointer (671-only)

**Batch ID:** `gaga_batch_jcvpca_smoke_671_20260630_214341`  
**Status:** Non-canonical smoke test — **archived off-repo (P3)**

## External location

```
../gaga_psylo_external_archive/final_cleanup_2026-06-30/smoke_batch_671_20260630/
```

**Symlink:** [`smoke_batch_671`](smoke_batch_671) → external path above

**Config key:** `layer3.smoke_batch_external`

## Summary

10/10 comparisons completed for participant 671 only (~65 s runtime). Canonical batch `193319` unchanged.

**Log:** [`docs/research_recovery/M12B_671_SMOKE_BATCH_LOG.md`](../../docs/research_recovery/M12B_671_SMOKE_BATCH_LOG.md)

## Regenerate smoke batch

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python run_gaga_batch_jcvpca.py \
  --participants 671 \
  --output-dir ../outputs/gaga_batch_jcvpca_smoke_671_$(date -u +%Y%m%d_%H%M%S)
```

**Do not promote** to canonical without explicit review.
