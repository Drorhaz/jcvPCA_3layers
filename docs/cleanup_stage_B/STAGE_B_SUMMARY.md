# Stage B Summary — Controlled Archiving

**Date:** 2026-06-30  
**Stage:** B — move only (no deletions, no code changes, no raw-data moves)  
**Archive root:** `archive/2026-06-30_cleanup_stage_B/`

---

## Outcome

Stage B completed **successfully** with **7/7 planned moves**, **0 errors**, and **26/26 post-move verification checks passed**.

| Metric | Value |
|--------|-------|
| Top-level folders moved | **7** |
| Total bytes moved | **2,158,615,100** (~**2.01 GB**) |
| Archive footprint | ~**2.06 GB** (`layer3_superseded_batches/` 1.4 GB + `layer2_5_scratch_archive/` 656 MB) |
| Failed/skipped moves | **0** |

Full per-item log: `docs/cleanup_stage_B/move_log.csv`  
Pre-move plan: `docs/cleanup_stage_B/STAGE_B_MOVE_PLAN.md`

---

## What was moved

### Group A — Superseded Layer 3 batches (low risk)

| Original path | New path | Size |
|---------------|----------|------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_174553/` | `archive/.../layer3_superseded_batches/gaga_batch_jcvpca_20260626_174553/` | 89 MB |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_175138/` | `archive/.../layer3_superseded_batches/gaga_batch_jcvpca_20260626_175138/` | 90 MB |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_180044/` | `archive/.../layer3_superseded_batches/gaga_batch_jcvpca_20260626_180044/` | 90 MB |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193110/` | `archive/.../layer3_superseded_batches/gaga_batch_jcvpca_20260626_193110/` | 769 MB |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193235/` | `archive/.../layer3_superseded_batches/gaga_batch_jcvpca_20260626_193235/` | 365 MB |

### Group B — Layer 2.5 scratch/archive (medium risk)

| Original path | New path | Size |
|---------------|----------|------|
| `Layer2.5_Segmentation/reevluate_project/` | `archive/.../layer2_5_scratch_archive/reevluate_project/` | 318 MB |
| `Layer2.5_Segmentation/outputs/archive/` | `archive/.../layer2_5_scratch_archive/outputs/archive/` | 338 MB |

All folder names and internal contents preserved unchanged.

---

## What was intentionally NOT moved

| Path | Size (approx) | Reason |
|------|---------------|--------|
| `Layer2_Motive_Kinematics/outputs/archive/` | **22 GB** | Deferred to Stage C — older pipeline outputs, not byte-identical to active stage08 |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | 3.6 GB | **Canonical batch** — poster + report source of truth |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | ~908 KB | Poster CSV inputs |
| `outputs/poster_final_figures/` | ~13 MB | Final poster deliverables |
| `671_test_data_des/` | 232 MB | Ambiguous export type — Stage A flagged `verify_manually` |
| All raw CSV / AVI data | — | Explicit Stage B prohibition |
| Layer 1/2 `data/` folders | — | Raw / primary inputs |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | 1.2 GB | Active JcvPCA-ready exports |
| `Layer2.5_Segmentation/segmentation/*.xlsx` | small | Manual annotations |
| Layer 3 `_workbench_*` folders | ~10 MB | Not in Stage B allowed list |
| Source code, configs, scripts | — | No code changes |

---

## Post-move verification (all passed)

| Check | Result |
|-------|--------|
| All 7 original paths removed | PASS |
| All 7 destination paths present | PASS |
| Canonical batch `gaga_batch_jcvpca_20260626_193319` exists | PASS |
| `poster_ready_evidence_package/` exists | PASS |
| `outputs/poster_final_figures/` + key PDF exist | PASS |
| Poster scripts unchanged in place | PASS |
| `671_test_data_des/` untouched | PASS |
| Layer 1/2 raw data untouched | PASS |
| Layer 2.5 active `pre_jvcpca_review/` untouched | PASS |
| Layer 2 `outputs/archive/` still in place (deferred) | PASS |

---

## Errors and uncertain cases

- **Errors during move:** none
- **Skipped moves:** none
- **Uncertain cases (unchanged from Stage A):**
  - `671_test_data_des/` CSV may be a distinct export type — still not moved
  - Layer 2 archive deferred pending stage08 equivalence review

---

## Poster reproduction status

**Active poster reproduction should still be possible.**

Evidence chain intact:

```text
gaga_batch_jcvpca_20260626_193319  (canonical — in place)
  → poster_ready_evidence_package/  (in place)
  → scripts/make_poster_final_figures.py, make_poster_671_figures.py  (unchanged)
  → outputs/poster_final_figures/  (in place)
```

Moved batches were **not** referenced in poster script `SEARCH_DIRS`. Superseded batch `193110` had identical core link CSV to `193319` but lacked downstream reports — not required for poster regeneration.

---

## Reversibility

Every move is reversible with a single `mv` per row in `move_log.csv` (destination → original_path). No files were renamed or deleted.

Example reversal:

```bash
mv archive/2026-06-30_cleanup_stage_B/layer3_superseded_batches/gaga_batch_jcvpca_20260626_193110 \
   Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193110
```

---

## Active project impact

- **Reduced clutter:** `Layer3_JcvPCA/outputs/` now contains only the canonical batch plus other active outputs (validation, evidence package, workbench previews).
- **Layer 2.5:** `reevluate_project/` and `outputs/archive/` removed from active tree; `pre_jvcpca_review/` remains the sole export location.
- **Total project disk size:** Still ~85 GB (data moved within repo, not deleted). Active workflow paths are cleaner; largest savings await Stage C (Layer 2 archive, 22 GB).

---

## Recommended Stage C

1. **After poster submission** (or after explicit approval): review `Layer2_Motive_Kinematics/outputs/archive/` session-by-session.
   - Stage A: stage07 rotvecs match active for 5/6 671 sessions; stage08 filtered rotvecs differ (older pipeline).
   - Move to `archive/2026-06-30_cleanup_stage_C/layer2_outputs_archive/` only after confirming active outputs are sufficient.
2. **Git hygiene (optional Stage C prep):** extend `.gitignore` for `archive/` and Layer 3 batch outputs.
3. **Documentation:** create `docs/ACTIVE_RUNS.md` declaring batch `193319` canonical.
4. **Optional:** archive Layer 3 `_workbench_*` exploratory folders (~10 MB).
5. **Optional:** deduplicate Layer 1 flat CSV copy (`data/671_T1_P1_R1_Take*.csv`) after hash confirmation — not done in Stage B.

---

## Stage B deliverables

| File | Status |
|------|--------|
| `STAGE_B_MOVE_PLAN.md` | Created (pre-move) |
| `move_log.csv` | Created (7 rows, all `moved_successfully=yes`) |
| `STAGE_B_SUMMARY.md` | Created (this file) |

---

*Stage B complete. No files deleted. No analysis code modified. No raw data moved.*
