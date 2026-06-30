# Smoke test outputs (pointer index)

Non-canonical JcvPCA smoke batches live on disk under `Layer3_JcvPCA/outputs/`. This folder indexes them only — **no bulk data here**.

---

## M12b — 671-only smoke batch

| Field | Value |
|-------|-------|
| **Batch ID** | `gaga_batch_jcvpca_smoke_671_20260630_214341` |
| **On disk** | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` |
| **Status** | Non-canonical — do not promote without explicit plan |
| **Result** | 10/10 comparisons completed (~65 s) |

**Detail:** [`SMOKE_BATCH_671.md`](SMOKE_BATCH_671.md)  
**Log:** [`docs/research_recovery/M12B_671_SMOKE_BATCH_LOG.md`](../../docs/research_recovery/M12B_671_SMOKE_BATCH_LOG.md)

---

## Canonical vs smoke

| Role | Index |
|------|-------|
| **Canonical batch (frozen)** | [`../active/CANONICAL_BATCH.md`](../active/CANONICAL_BATCH.md) |
| **Smoke tests** | This folder |

---

## External archive (optional, post-M12d)

Smoke batch may move to `../gaga_psylo_external_archive/final_cleanup_2026-06-30/layer3_smoke_batch_671/` only with explicit approval. **Not moved in F2.**

See [`../archive_index/EXTERNAL_ARCHIVE.md`](../archive_index/EXTERNAL_ARCHIVE.md).
