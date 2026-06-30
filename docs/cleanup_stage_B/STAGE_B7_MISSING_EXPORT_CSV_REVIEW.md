# Stage B.7 — Missing Export CSV Review

**Date:** 2026-06-30  
**Scope:** Two tracked paths marked `D` in git status after export pipeline refresh  
**Action in B.7:** Investigation and recommendations only — **no restore, no commit**

---

## Executive summary

| File | Recommendation | Rationale |
|------|----------------|-----------|
| `mapping_logic_table.csv` (per-export) | **Accept deletion in git** | Superseded by newer export artifacts (`window_export_manifest.json`, parquets); not produced by current `export_window` pipeline |
| `joint_overlap_table.csv` (participant-level) | **Accept deletion in git** | Generated output; regeneratable on next notebook/dashboard discovery run; newer copy exists in `_archive/` if needed locally |

**Poster reproduction:** Neither file is referenced — **no impact**.

**Optional local restore (not for commit):** Copy from `_archive/pre_jvcpca_review_671_252_20260626_181500/` if you want files on disk before re-running Layer 2.5 UI (documented below).

---

## File 1 — `mapping_logic_table.csv`

### Exact tracked path

```
Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T1_P1_R2/671_T1_P1_R2_g4_s14040_e20880/mapping_logic_table.csv
```

| Attribute | Detail |
|-----------|--------|
| Git status | `D` (deleted from working tree, still in index at `HEAD`) |
| Last committed in | `baa706b` — *Expand pipeline with Layer 2.5/3, evidence-only Layer 1, and tighter gitignore.* |
| Size at `HEAD` | ~7,514 bytes (~33 data rows + header) |
| On disk at original path | **No** |

### Exists elsewhere in project?

| Location | Same export window? | Notes |
|----------|---------------------|-------|
| `.../pre_jvcpca_review/_archive/pre_jvcpca_review_671_252_20260626_181500/671/671_T1_P1_R2/671_T1_P1_R2_g4_s14040_e20880/mapping_logic_table.csv` | **Yes** | Snapshot from 2026-06-26 batch refresh; matches tracked content era |
| `.../pre_jvcpca_review/671/671_T1_P1_R1/671_T1_P1_R1_s14280_e15240/mapping_logic_table.csv` | Different window | Older review-table export (non-g4 path) |
| `archive/.../layer2_5_scratch_archive/outputs/archive/...` | Various smoke/debug | Superseded archive copies |
| Active g4 export folder today | **No** `mapping_logic_table.csv` | Folder contains new export set (see below) |

### Current contents of active export folder (replacement artifacts)

Path: `.../671_T1_P1_R2_g4_s14040_e20880/`

| File | Role |
|------|------|
| `window_export_manifest.json` | Canonical export metadata (links, frames, layer3_safe) |
| `window_jvcpca_matrix.parquet` | Layer 3 input matrix |
| `window_selected_rotvecs_long.parquet` | Selected rotvec window |
| `pilot_export_validation_report.json` | Validation summary |
| `window_jvcpca_matrix_summary.md` | Human-readable summary |
| `window_joint_frame_flag_log.csv` | QC flags (large; gitignored pattern) |
| `window_warnings.csv` | Export warnings |

**Conclusion:** The per-window export was **re-run** with the `export_window` pipeline, which **does not write** `mapping_logic_table.csv` (confirmed: no references in `export_window.py`).

### Newer duplicate / equivalent?

| Artifact | Equivalent to mapping_logic? |
|----------|---------------------------|
| `window_export_manifest.json` | **Partial** — encodes selected links, frames, validation; not marker-level mapping audit |
| `mapping_logic_table.csv` in `_archive/` | **Historical** — same path snapshot; **not** equivalent to current manifest (stale vs re-export) |

Mapping logic is still produced by `tables.write_mapping_table()` / `write_review_tables()` for **interactive review** workflows, not for the current pilot export path.

### Required by active scripts?

| Consumer | Reads this path? | Notes |
|----------|------------------|-------|
| `export_window.py` | **No** | Current export path |
| `tables.py` | **Writes** (review path) | Generates fresh file when review tables run |
| `build.py` | References name generically | Error message suggests inspecting file if present |
| `review_display.py`, `review_output.py` | Lists as review artifact | Display spec, not hard-coded path |
| `pre_jvcpca_review.ipynb` | Displays when generated | Review step, not export step |
| `scripts/make_poster_*.py` | **No** | |
| Layer 3 batch / poster chain | **No** | |

### Required for poster reproduction?

**No.** Zero references under `scripts/` or Layer 3 poster paths.

### Generated output or curated input?

**Generated output** — produced by `write_mapping_table()` from mapping entries during review/export table writes. Not hand-edited source data.

### Recommendation

**Accept deletion in git** (stage the `D` when committing).

**Evidence:**

1. Active disk state matches intentional pipeline change (manifest + parquet export).
2. Restoring the old CSV would **contradict** the current export folder contents dated 2026-06-26 21:28.
3. File is regeneratable via review-table workflow if needed for debugging.
4. Path falls under `pre_jvcpca_review/671/` — **gitignored in B.6**; should not remain in remote index.

**Do not restore for commit.** Optional local copy from `_archive/` only for historical comparison (not required for Layer 3 or poster).

---

## File 2 — `joint_overlap_table.csv`

### Exact tracked path

```
Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/joint_overlap_table.csv
```

| Attribute | Detail |
|-----------|--------|
| Git status | `D` |
| Last committed in | `baa706b` (same commit as mapping_logic) |
| Size at `HEAD` | ~4,679 bytes (**10 link rows** + header) |
| On disk at original path | **No** |

### Exists elsewhere in project?

| Location | Rows (approx) | Notes |
|----------|---------------|-------|
| `.../pre_jvcpca_review/_archive/pre_jvcpca_review_671_252_20260626_181500/671/joint_overlap_table.csv` | **20 link rows** | Newer participant-level snapshot (2026-06-26 batch) |
| `archive/.../layer2_5_scratch_archive/outputs/archive/pre_jvcpca_review/671/joint_overlap_table.csv` | 10 rows | Older archive copy (pre-refresh) |
| Active `.../pre_jvcpca_review/671/` | **Missing** | Not regenerated after batch export refresh |

### Newer duplicate / equivalent?

**Yes — newer local equivalent** at:

```
Layer2.5_Segmentation/outputs/pre_jvcpca_review/_archive/pre_jvcpca_review_671_252_20260626_181500/671/joint_overlap_table.csv
```

Expanded link coverage (core_candidate set, T3 topology rows) vs older 10-row `HEAD` version. This is the best on-disk reference if you want the table locally **without** committing it.

### Required by active scripts?

| Consumer | Reads fixed path? | Notes |
|----------|-------------------|-------|
| `app_controller.py` | **Writes** `out_dir / "joint_overlap_table.csv"` | Regenerates when `build_overlap_table()` runs |
| `pre_jvcpca_review.ipynb` | Writes + displays | Participant discovery step |
| `joint_overlap.py` | `write_joint_overlap_table()` | Writer only |
| `notebook_ui.py` | Label convention | Matches `canonical_link_name` column |
| Tests | Classification logic | Do not read committed CSV path |
| `export_window.py` | **No** | |
| Poster scripts | **No** | |
| Layer 3 | **No** | |

**Runtime behavior:** Missing file does **not** block Layer 3 or poster. Layer 2.5 notebook/dashboard **regenerates** the file when the user runs participant discovery / overlap build.

### Required for poster reproduction?

**No.**

### Generated output or curated input?

**Generated output** — derived from cross-session link classification (`classify_links`, `overlap_dataframe`).

### Recommendation

**Accept deletion in git** (stage the `D` when committing).

**Evidence:**

1. File is a **cache of an interactive review step**, not an upstream input to Layer 3.
2. Code path still **writes** the file on demand — absence is a stale-output artifact, not lost logic.
3. Newer content exists in `_archive/` if needed locally.
4. Participant export tree is **gitignored** in B.6 — keeping this in the index is inconsistent.

**Optional local restore (disk only, do not commit):**

```bash
cp "Layer2.5_Segmentation/outputs/pre_jvcpca_review/_archive/pre_jvcpca_review_671_252_20260626_181500/671/joint_overlap_table.csv" \
   "Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/joint_overlap_table.csv"
```

Or regenerate via notebook discovery step.

**Do not `git restore` for commit** — restored file would be gitignored and should not re-enter the index.

---

## Script and documentation search results

### `mapping_logic_table.csv` / `mapping_logic`

| Location | Usage |
|----------|---------|
| `tables.py` | `mapping_logic_dataframe()`, `write_mapping_table()` — **writer** |
| `review_output.py`, `review_display.py` | Listed as standard review artifact name |
| `build.py` | Diagnostic message referencing filename |
| `pre_jvcpca_review.ipynb` | Display in review UI |
| `tests/test_pre_jvcpca_review.py`, `test_review_table_repair.py` | Assert generation in review tests |
| `LAYER2_5_PROGRAM_AUDIT_REPORT.md` | Documents artifact role |
| **`export_window.py`** | **No references** |
| **`scripts/` (poster)** | **No references** |

### `joint_overlap_table.csv` / `joint_overlap`

| Location | Usage |
|----------|---------|
| `joint_overlap.py` | Core logic + `write_joint_overlap_table()` |
| `app_controller.py` | `build_overlap_table()` **writer** to participant dir |
| `export_window.py` | `emit_joint_comparability_warnings` import only |
| `pre_jvcpca_review.ipynb` | Participant overlap UI |
| `notebook_ui.py` | Display label helper |
| Multiple tests | Classification behavior |
| **`scripts/` (poster)** | **No references** |

---

## Comparison: git `HEAD` vs `_archive` vs active export

| Item | Git `HEAD` | `_archive` snapshot | Active path today |
|------|------------|---------------------|-------------------|
| mapping_logic (T1_P1_R2 g4) | 7,514 B | Same path, same era | **Absent** — replaced by manifest/parquet |
| joint_overlap (671/) | 4,679 B, 10 rows | 8,707 B, 20 rows | **Absent** — regeneratable |

---

## Final decisions for commit (B.7)

| Path | Git commit action | Local disk action (optional) |
|------|-------------------|------------------------------|
| `.../mapping_logic_table.csv` | **Stage deletion** (`git add -u` on path) | None required |
| `.../joint_overlap_table.csv` | **Stage deletion** (`git add -u` on path) | Optional `cp` from `_archive/` for notebook convenience |

**No `git restore` recommended for the checkpoint commit.**

---

*Investigation only. See `STAGE_B7_COMMIT_PLAN_FINAL.md` for staging commands.*
