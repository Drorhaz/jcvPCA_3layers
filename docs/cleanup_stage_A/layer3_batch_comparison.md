# Layer 3 Batch Run Comparison — Stage A

**Date:** 2026-06-30  
**Scope:** All `gaga_batch_jcvpca_20260626_*` folders under `Layer3_JcvPCA/outputs/`  
**Method:** Folder size, `batch_summary.md`, `comparison_status.csv`, comparison-directory counts, checksum of key CSVs (see `checksum_comparison.csv`).

---

## Summary table

| Folder | Size | Completed (status CSV) | Comparison dirs | Participants | Key reports | Verdict |
|--------|------|------------------------|-----------------|--------------|-------------|---------|
| `gaga_batch_jcvpca_20260626_174553` | 91 MB | **0 / 20** | 6 | 671 only (partial) | `batch_summary.md` only | **Failed smoke run** — archive later |
| `gaga_batch_jcvpca_20260626_175138` | 91 MB | **6 / 20** | 6 | 671 only | `batch_summary.md` only | **Superseded partial** — archive later |
| `gaga_batch_jcvpca_20260626_180044` | 91 MB | **6 / 20** | 6 | 671 only | `batch_summary.md` only | **Superseded partial** — archive later |
| `gaga_batch_jcvpca_20260626_193110` | 780 MB | **20 / 20** | 20 | 671 + 252 | `batch_summary.md` only | **Superseded full core** — archive after 193319 verified |
| `gaga_batch_jcvpca_20260626_193235` | 371 MB | **10 / 20** | 10 | 671 only | `batch_summary.md` only | **Superseded partial (671)** — archive later |
| `gaga_batch_jcvpca_20260626_193319` | **3.6 GB** | **20 / 20** | **72** | **671 + 252** | **14 root MD reports** + full CSV suite | **Canonical run** — keep active |

---

## Per-run details

### `gaga_batch_jcvpca_20260626_174553` (91 MB)

- **Status:** 6 `failed_error`, 14 `skipped_missing_data`, 0 completed.
- **Comparison dirs:** 6 (671 block A/B introspective + L1/L2 only).
- **Timepoint coverage:** T1, T2 only (no T3, no 252).
- **Important files:** `batch_manifest.csv`, `comparison_status.csv`, empty/failed comparison stubs.
- **Recommendation:** **Archive later** (low risk). No scientific conclusions depend on this run.

### `gaga_batch_jcvpca_20260626_175138` (91 MB)

- **Status:** 6 completed, 14 skipped (252 data not yet available).
- **Comparison dirs:** Same 6 as 174553 but with successful outputs for 671.
- **Checksum note:** `comparison_plan.csv` identical to 174553/180044; `jcvpca_link_results.csv` identical across early partial runs (43 KB stub).
- **Recommendation:** **Archive later** (low risk).

### `gaga_batch_jcvpca_20260626_180044` (91 MB)

- **Status:** 6 completed, 14 skipped — same pattern as 175138.
- **Recommendation:** **Archive later** (low risk). Redundant with 175138.

### `gaga_batch_jcvpca_20260626_193110` (780 MB)

- **Status:** 20/20 completed (both participants).
- **Comparison dirs:** 20 — core comparison set (I, L1, L2, L3 longitudinal + NV blocks).
- **Participants:** 671 and 252.
- **Timepoint / repetition coverage:** T1/T2/T3 longitudinal (L1/L2/L3) + within-session NV (I: R1 vs R2) for both blocks A and B.
- **Checksum vs 193319:** `jcvpca_link_results.csv` **identical SHA256** to 193319; `comparison_plan.csv` identical; `comparison_status.csv` differs (193319 has post-run additions).
- **Missing vs 193319:** No `FINAL_integrated_deep_review_after_p50_p60.md`, no directional-robustness full numeric reports, no joint heatmap reports, no natural variability deep dive, no poster planning docs, no PC-focus hierarchy in `batch_summary.md`.
- **Recommendation:** **Archive later** after confirming 193319 reproducibility. Core link results match, but downstream interpretation layer exists only in 193319.

### `gaga_batch_jcvpca_20260626_193235` (371 MB)

- **Status:** 10/20 completed.
- **Comparison dirs:** 10 — 671-only subset (all A-block comparisons for 671).
- **Recommendation:** **Archive later** (low risk). Strict subset of 193319.

### `gaga_batch_jcvpca_20260626_193319` (3.6 GB) — **CANONICAL**

- **Status:** 20/20 completed in `comparison_status.csv`.
- **Comparison dirs:** **72** — includes:
  - 20 core comparisons (same families as 193110)
  - **52 additional directional-robustness (DR) comparisons** (`*_DR_*` naming, 24 per block A/B per participant)
- **Participants:** 671 (36 dirs) + 252 (36 dirs).
- **Comparison families detected:**
  - `I` — within-session natural variability (R1 vs R2) at T1/T2/T3
  - `L1/L2/L3` — longitudinal T1 vs T2, T1 vs T3, T2 vs T3
  - `DR` — directional robustness cross-repetition grid
- **Important output files (root level):**
  - `FINAL_integrated_deep_review_after_p50_p60.md`
  - `Gaga_JcvPCA_MASTER_full_numeric_report.md`
  - `directional_robustness_t1_t2_FULL_NUMERIC_REPORT.md`
  - `directional_robustness_t1_t3_FULL_NUMERIC_REPORT.md`
  - `joint_heatmap_full_numeric_report.md`
  - `natural_variability_FULL_NUMERIC_REPORT.md`
  - `natural_variability_deep_dive_report.md`
  - `gaga_batch_interpretation_report.md`
  - `poster_plot_shortlist.md`
  - `poster_scientific_story_and_figure_plan.md`
  - `PC_focus_p50_p60_interpretation_review.md`
  - Core CSVs: `jcvpca_link_results.csv`, `jcvpca_link_results_by_pc_focus*.csv`, `comparable_links_by_comparison.csv`, directional robustness CSVs
- **`batch_summary.md` uniquely documents:**
  - PC-focus interpretation hierarchy (all / p50 / p60 / archived p2)
  - Downstream artifact index
- **Why canonical (evidence):**
  1. Latest timestamp in the batch sequence (193319 > 193235 > 193110).
  2. Only run with full interpretive report suite (14 MD files vs 1).
  3. Same core `jcvpca_link_results.csv` as 193110 (verified SHA256).
  4. Referenced explicitly by `scripts/make_poster_final_figures.py` `SEARCH_DIRS`.
  5. Feeds `poster_ready_evidence_package` generation pipeline.
- **Caveat:** 72 comparison dirs vs 20 status rows — the extra 52 DR dirs are **downstream directional-robustness expansions**, not failures. Do not treat the folder as inconsistent.
- **Recommendation:** **Keep active.** Treat as single source of truth for Layer 3 batch science and poster inputs.

---

## Cross-run checksum findings

| File | 193110 vs 193319 | Interpretation |
|------|------------------|----------------|
| `jcvpca_link_results.csv` | Identical | Core results stable between full runs |
| `comparison_plan.csv` | Identical | Same comparison design |
| `comparison_status.csv` | Different | 193319 has post-processing status updates |
| `batch_manifest.csv` | Different | 193319 manifest updated |
| `FINAL_integrated_deep_review_after_p50_p60.md` | Present only in 193319 | Downstream analysis added after 193110 |

Early runs (174553–180044) share identical stub `jcvpca_link_results.csv` (43 KB) — not comparable to final results.

---

## Recommended disposition (Stage B+)

| Action | Folders |
|--------|---------|
| **Keep active** | `gaga_batch_jcvpca_20260626_193319` |
| **Archive later (low risk)** | `174553`, `175138`, `180044`, `193235` |
| **Archive later (after 193319 spot-check)** | `193110` |
| **Optional future slimming of 193319** | Strip per-comparison `.npy`/diagnostic `.png` only after reproducing from scripts |
