# Stage A Summary — Hash Comparison & Backup Verification

**Date:** 2026-06-30  
**Stage:** A (verification only — no files moved, deleted, or renamed)  
**Artifacts produced:** `docs/cleanup_stage_A/` (7 files)

---

## What was verified

### File inventory

- **`file_inventory.csv`** — 39,695 files catalogued (~89 GB on disk excluding `.venv`, `__pycache__`, `.pytest_cache`, `.git`).
- Each row includes path, size, extension, category, git tracking status, and modification time.
- **Excluded from inventory (documented):** `.venv/` (~93k additional files if included), `__pycache__/`, `.pytest_cache/`, `.git/`.

### Checksum comparison (targeted)

- **`checksum_comparison.csv`** — 76 files hashed (not full 85 GB).
- **Full SHA256:** files ≤ 500 MB.
- **Sampled hash (first 64 MB + last 64 MB + size):** files > 500 MB (Layer 2 frame-level CSVs).
- **Priority areas covered:**
  - Layer 2 archive vs active 671 sessions (key stage 07/08 files)
  - Layer 2 archive `audit_rerun_*` folders
  - All 6 Layer 3 batch runs (key manifests/reports)
  - Poster evidence CSVs
  - Raw 671_T1_P1_R1 CSV across 4 locations

### Key checksum findings

| Finding | Confidence | Implication |
|---------|------------|-------------|
| Layer 1 `data/671/` vs flat `data/*.csv` same session | **High** (identical SHA256) | Flat copy is redundant; keep `data/671/` as canonical |
| `reevluate_project/` 671 CSV = Layer 1 copy (50 MB) | **High** | Scratch duplicate; archive candidate |
| `671_test_data_des/` CSV (243 MB) ≠ Layer 1 (50 MB) ≠ Layer 2 (225 MB) | **High** | **Not duplicates** — likely different Motive export types; manual review required |
| Layer 2 archive `stage07/relative_rotation_vectors.csv` = active for 5/6 671 sessions | **High** | Archive stage07 copies are redundant |
| Layer 2 archive `stage07` for T3_R1 **differs** from active | **High** | Do not bulk-delete archive without session-level review |
| Layer 2 `stage08/filtered_relative_rotation_vectors.csv` active vs archive **differs** (size + sampled hash) | **Medium** | Archive holds **older/smaller** filtered outputs; active is current pipeline |
| `jcvpca_link_results.csv` in 193110 = 193319 | **High** | 193110 core results match canonical run |
| Batch runs 174553–180044 share stub link results | **High** | Safe archive candidates |

### Layer 3 batch comparison

- Documented in **`layer3_batch_comparison.md`**.
- **`gaga_batch_jcvpca_20260626_193319` confirmed as canonical:**
  - 20/20 completed core comparisons
  - 72 comparison directories (includes 52 directional-robustness expansions)
  - 14 interpretive MD reports (vs 1 in all other runs)
  - Hard-coded in poster script search paths
  - Identical core link results to 193110 plus full downstream analysis

### Poster outputs review

- Documented in **`poster_outputs_review.md`**.
- Reproducibility chain: batch `193319` → `poster_ready_evidence_package/` → `make_poster_*.py` → `outputs/poster_final_figures/`.

### Manifests

- **`proposed_archive_manifest.csv`** — 20 entries, ~**24.3 GB** total if all archived later.
- **`proposed_active_manifest.csv`** — 25 entries defining clean active project core.

---

## What was NOT verified

| Item | Reason | Risk |
|------|--------|------|
| Full SHA256 of all files > 500 MB | Would require hashing ~50+ GB; sampled hash used instead | Medium for exact byte-identical claims on filtered_rotvecs |
| All 252 raw CSV duplicates across Layer 1/Layer 2 | Only 671_T1_P1_R1 sampled | Medium |
| Off-repo / cloud backup existence | No external storage access in this stage | **High** if cleanup proceeds without backup |
| Layer 2.5 parquet matrix equivalence across export versions | Parquet not checksum-compared | Low (regeneratable from Layer 2) |
| Git LFS or remote tracking of large files | Not inspected | Medium |
| Whether 252 P2 sessions are needed for poster | Scope question, not file question | Low |
| Content equivalence of `193319` DR comparison dirs vs rerunnable from scripts | Dir count verified, not rerun | Low |

---

## Largest safe archive candidates (evidence-based)

| Path | Size (approx) | Evidence | Risk |
|------|---------------|----------|------|
| `Layer2_Motive_Kinematics/outputs/archive/` | **22 GB** | Stage07 duplicates for 5/6 sessions; stage08 differs (older) | **Medium** — confirm active outputs sufficient first |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193110/` | 780 MB | Core CSV matches 193319; missing downstream reports | **Low** after spot-check |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_{174553,175138,180044,193235}/` | ~1.3 GB combined | Failed/partial/superseded runs | **Low** |
| `Layer2.5_Segmentation/outputs/archive/` | 338 MB | Marked superseded in audit | **Medium** |
| `Layer2.5_Segmentation/reevluate_project/` | 318 MB | CSV duplicates Layer 1; parquets regeneratable | **Medium** — read scratch MD first |
| `Layer1_motive_qc/motive_qc/data/671_T1_P1_R1_Take*.csv` (flat copy) | 48 MB | Identical to `data/671/` copy | **Low** |
| Layer 3 `_workbench_*` folders | ~10 MB | Exploratory previews | **Low** |

**Estimated recoverable space (conservative):** ~**24 GB** if all low/medium-risk items archived after review.

---

## Risky / uncertain files (do NOT archive yet)

| Path | Issue |
|------|-------|
| `671_test_data_des/671_T1_P1_R1_Take*.csv` (243 MB) | Different from Layer 1 and Layer 2 copies — may be unique full raw export |
| `Layer2_Motive_Kinematics/data/252/**/*.avi` (13 files, ~19 GB) | No in-repo regeneration; irreplaceable video |
| All Layer 1/2 raw CSV trees | Primary scientific capture data |
| `Layer2.5_Segmentation/segmentation/*.xlsx` | Manual human annotations |
| `Layer2_Motive_Kinematics/outputs/archive/audit_rerun_*` | May document audit trail for filtering policy changes |
| Active Layer 2 671 session outputs | Current pipeline version; stage08 differs from archive |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | Canonical analysis + poster source |
| `poster_ready_evidence_package/` + `outputs/poster_final_figures/` | Publication deliverables |

---

## Recommended next step: Stage B (Git hygiene)

1. **Confirm off-repo backup** of all raw data (CSV + AVI) before any archive moves.
2. Extend `.gitignore` for Layer 3 batch output folders and `_workbench_*` (see `proposed_archive_manifest.csv`).
3. Resolve 3 deleted tracked files in git status (restore or commit intentional removal).
4. Create `docs/ACTIVE_RUNS.md` declaring batch `193319` as canonical.
5. Update root `README.md` Layer 3 status (still says "planned").

**Do not start Stage C (physical archive moves) until Stage B complete and backup confirmed.**

---

## Exact warnings before Stage B

1. **NO DELETIONS** — Stage B is gitignore and documentation only; no data moves.
2. **671_test_data_des is NOT a duplicate** — do not treat the 243 MB CSV as redundant with Layer 1/Layer 2 without export-type documentation.
3. **Layer 2 archive ≠ byte-identical to active** for stage08 filtered rotvecs — archive may be pre-NaN-policy-fix runs.
4. **Batch 193319 has 72 comparison dirs but 20 status rows** — this is expected (DR grid expansion); not a sign of corruption.
5. **Poster reproducibility depends on `poster_ready_evidence_package/`** — do not gitignore or archive this before poster submission.
6. **Checksum sampling on large CSVs** — archive decisions for stage08 files should use full hash or regeneration test if disputed.
7. **No external backup was verified in Stage A** — archiving in Stage C without off-repo backup is **unsafe**.

---

## Stage A deliverables checklist

| File | Status |
|------|--------|
| `file_inventory.csv` | Created (39,695 rows) |
| `checksum_comparison.csv` | Created (76 rows) |
| `layer3_batch_comparison.md` | Created |
| `poster_outputs_review.md` | Created |
| `proposed_archive_manifest.csv` | Created (20 rows, ~24.3 GB) |
| `proposed_active_manifest.csv` | Created (25 rows) |
| `STAGE_A_SUMMARY.md` | Created (this file) |

---

*Stage A complete. No project files were moved, renamed, deleted, or modified outside `docs/cleanup_stage_A/`.*
