# M12b 671-Only Smoke Batch Log

**Date:** 2026-06-30  
**Scope:** Smoke test — 671-only JcvPCA batch via current runner  
**Approval:** User-approved M12b (671-only, new timestamped folder, no canonical promotion)

---

## Summary

| Field | Value |
|-------|-------|
| **Result** | **PASS** — exit 0, 10/10 comparisons completed |
| **Participants** | **671 only** (252 not included) |
| **Output folder** | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` |
| **Runtime** | **64.8 s** wall (`/usr/bin/time -p real 64.78`) |
| **Canonical batch modified?** | **No** — `193319/batch_summary.md` mtime unchanged (2026-06-26 23:53:08) |
| **New outputs location** | **Smoke folder only** (~1780 files) |
| **Promoted to canonical?** | **No** |

---

## Preflight (before batch)

### 1. Project path check

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
python scripts/check_project_paths.py
```

| Exit | Result |
|------|--------|
| **0** | `Path check passed (all required paths exist).` |

### 2. Layer 2.5 exports for 671

**Path:** `Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/`  
**Status:** **Present** — per-exercise and g4 window exports under six session trees (T1–T3 × R1–R2).

### 3. Participant filtering support

**Verified:** `run_gaga_batch_jcvpca.py` exposes `--participant` (`action="append"`).  
**Decision:** Proceed with 671-only batch (did not run full cohort).

---

## Exact command run

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer3_JcvPCA/scripts

OUTPUT_DIR="../outputs/gaga_batch_jcvpca_smoke_671_$(date -u +%Y%m%d_%H%M%S)"

/usr/bin/time -p ../.venv/bin/python run_gaga_batch_jcvpca.py \
  --participant 671 \
  --output-dir "$OUTPUT_DIR"
```

**Resolved output directory:**

`Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/`

**Python:** `Layer3_JcvPCA/.venv/bin/python`  
**Layer 2.5 root:** default from config (`Layer2.5_Segmentation/outputs/pre_jvcpca_review`)

---

## Batch outcome

| Field | Value |
|-------|-------|
| **Exit code** | **0** |
| **Comparisons attempted** | 10 |
| **Completed** | 10 |
| **Failed / blocked / skipped** | 0 |
| **Central manifest rows scanned** | 72 (full manifest refresh; availability filtered to 671 in report) |

**stdout (key lines):**

```
Batch complete: ../outputs/gaga_batch_jcvpca_smoke_671_20260630_214341
Summary: ../outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/batch_summary.md
```

---

## Participants included

| Participant | Included | Notes |
|-------------|----------|-------|
| **671** | **Yes** | All block/comparison plan rows |
| **252** | **No** | No `252` strings in smoke batch CSVs |

---

## Comparisons generated (671)

**Blocks:** A (`P1–P5`), B (`P3–P5`)  
**Specs:** 5 per block → **10 total**

| Block | Comparison ID | Label | Mode | Status |
|-------|---------------|-------|------|--------|
| A | L1_T1_vs_T2 | T1_vs_T2 | longitudinal | completed |
| A | L2_T1_vs_T3 | T1_vs_T3 | longitudinal | completed |
| A | I_T1_R1_vs_R2 | T1_R1_vs_T1_R2 | exploratory | completed |
| A | I_T2_R1_vs_R2 | T2_R1_vs_T2_R2 | exploratory | completed |
| A | I_T3_R1_vs_R2 | T3_R1_vs_T3_R2 | exploratory | completed |
| B | L1_T1_vs_T2 | T1_vs_T2 | longitudinal | completed |
| B | L2_T1_vs_T3 | T1_vs_T3 | longitudinal | completed |
| B | I_T1_R1_vs_R2 | T1_R1_vs_T1_R2 | exploratory | completed |
| B | I_T2_R1_vs_R2 | T2_R1_vs_T2_R2 | exploratory | completed |
| B | I_T3_R1_vs_R2 | T3_R1_vs_T3_R2 | exploratory | completed |

Each comparison also ran PC-focus sensitivity runs (`functional_p2`, `null_space_p2`) — all completed per `comparison_status_by_focus.csv`.

**Comparable links:** 14 per comparison; **feature_schema_id:** `4c5188a32774cf9b`.

**Top-level artifacts:** `batch_summary.md`, `comparison_plan.csv`, `comparison_status.csv`, `jcvpca_link_results.csv`, `plot_index.csv`, `comparisons/671_*`, `plots/671/*`, etc.

---

## Warnings and non-fatal stderr

| Source | Message | Impact |
|--------|---------|--------|
| Matplotlib | `~/.matplotlib` not writable; temp cache dir used | Non-fatal; ~20s font cache on cold start |
| Apache Arrow | `sysctlbyname` sandbox warnings (L1/L2/L3 cache) | Non-fatal |
| Layer 2.5 QC | `qc_status=warning` on 671 exports in availability report | Exports used successfully; same pattern as canonical 671 run |

No comparison failures, preflight blocks, or harmonization blocks.

---

## Outputs created or modified

| Location | Action |
|----------|--------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` | **Created** (new smoke batch only) |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | **Not modified** |
| L2.5 exports | **Not modified** (read-only inputs) |
| Source code | **Not modified** |
| Git-tracked docs (except this log) | **Not modified** |

**Batch directories on disk after M12b:**

- `gaga_batch_jcvpca_20260626_193319` (canonical, frozen)
- `gaga_batch_jcvpca_smoke_671_20260630_214341` (smoke, non-canonical)

---

## Canonical batch modified?

**No.** Verified via `batch_summary.md` mtime on `193319` unchanged.

---

## Smoke batch retention recommendation

| Option | Recommendation |
|--------|----------------|
| **Keep (short term)** | **Yes** — documents post-refactor pipeline health; all 671 comparisons completed cleanly in ~65s |
| **Archive later** | Move to external archive or `results/archive_index` entry after M12d full batch is validated (do not promote) |
| **Delete now** | **No** — useful diff baseline until full cohort batch succeeds |

This smoke batch is **not** a replacement for canonical `193319` and should **not** be promoted without explicit promotion plan.

---

## M12c / M12d recommendation

| Batch | Next? | Rationale |
|-------|-------|-----------|
| **M12c** (252 export/QC review) | **Recommended before M12d** | 252 manifest has 34/36 QC warnings; smoke proves runner + 671 path, not 252 readiness |
| **M12d** (full 671+252 batch) | **Conditional after M12c** | Runner and venv validated; proceed only after 252 QC sign-off and explicit approval for new timestamped folder |

**Suggested order:** M12c (read-only QC review) → M12d (full cohort batch to new folder) → compare against canonical / smoke as needed.

---

## Related docs

- [`M12A_VALIDATION_LOG.md`](M12A_VALIDATION_LOG.md)
- [`M12_PRE_ANALYSIS_READINESS.md`](M12_PRE_ANALYSIS_READINESS.md)
- [`CONTINUATION_RUNBOOK.md`](CONTINUATION_RUNBOOK.md)

---

*Smoke batch log created without commit. Generated outputs remain untracked.*
