# Stage C.0 — Layer 2 Archive Review

**Date:** 2026-06-30  
**Scope:** Risk review of `Layer2_Motive_Kinematics/outputs/archive/` before any move  
**Action:** Documentation only — **no move, no deletion, no commit**

---

## Executive summary

| Question | Answer |
|----------|--------|
| Can the archive be moved without rerunning Layer 3 / poster **today**? | **Likely yes** for runtime — active pipeline does not read this path |
| Is the archive a pure duplicate of active outputs? | **No** — stage08 differs for all 671 sessions; stage07 differs for T3_P1_R1 |
| Does poster reproduction depend on this archive? | **No** |
| Does canonical batch `193319` depend on this archive? | **No** — built from Layer 2.5 exports sourced from **active** Layer 2 sessions |
| Recommended action | **Move outside repo after poster submission** (conservative) |

---

## What is inside `Layer2_Motive_Kinematics/outputs/archive/`

### Size and inventory

| Metric | Value |
|--------|-------|
| **Total size** | ~22.5 GB (`du -sh` ≈ 22G) |
| **File count** | 852 files |
| **Git tracked files** | 389 (legacy index entries) |
| **Git ignore** | Matched by `**/outputs/archive/` in `.gitignore` |
| **Top-level directories** | 13 folders + 27 root index/report files |

### Folder breakdown

| Category | Folders | Approx. size | Description |
|----------|---------|--------------|-------------|
| **671 session copies** | 6 | ~11.3 GB | Same Take folder names as active `outputs/*_Take_*` for participant 671 |
| **audit_rerun_*** | 6 | ~11.1 GB | Layer 2 QC audit re-runs (Jun 2026); no active-tree counterparts |
| **layer2_exports** | 1 | ~134 MB | Old parquet export bundle (superseded by active `outputs/layer2_exports/`) |
| **Root indices/reports** | 27 files | ~5 MB | Historical stage00–08 indices, QC manifests, gate reports |

### Session / timepoint / repetition coverage

**671 session copies (archived Take folders):**

| Session | Folder |
|---------|--------|
| T1 R1 | `671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001` |
| T1 R2 | `671_T1_P1_R2_Take_2026-01-06_03.57.12_PM_003` |
| T2 R1 | `671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005` |
| T2 R2 | `671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009` |
| T3 R1 | `671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000` |
| T3 R2 | `671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005` |

**audit_rerun folders (671 audit series, Jun 2026):**

| Folder | Documented in |
|--------|---------------|
| `audit_rerun_T1_P1_R1` … `audit_rerun_T3_P1_R2` | `Layer2_Motive_Kinematics/docs/LAYER2_KINEMATIC_CHAIN_QC_AUDIT_2026-06-23.md` |

**Not present in archive:** participant **252** sessions (252 exists only in active `outputs/*_Take_*`).

Each session/audit folder typically contains stages `00_csv_structure` through `08_filtered_rotvecs` plus assumptions logs.

---

## Duplication vs active outputs

### Active vs archived size (671 sessions)

Active trees are **~500–630 MB larger** per session than archive copies (newer stage08 artifacts, parquets, flag reports):

| Session | Active (MB) | Archive (MB) | Delta (MB) |
|---------|-------------|--------------|------------|
| T1 R1 | 2353 | 1845 | +509 |
| T1 R2 | 2310 | 1786 | +524 |
| T2 R1 | 2327 | 1800 | +527 |
| T2 R2 | 2328 | 1800 | +528 |
| T3 R1 | 2661 | 2032 | +628 |
| T3 R2 | 2630 | 2020 | +610 |

Archive copies are **older/smaller snapshots**, not supersets of active data.

### Stage A checksum findings (671 core files)

From `docs/cleanup_stage_A/checksum_comparison.csv`:

| Stage / file | Match active? | Sessions |
|--------------|---------------|----------|
| **Stage 07** `relative_rotation_vectors.csv` | **Identical SHA256** | 5/6 (T1_R1, T1_R2, T2_R1, T2_R2, T3_R2) |
| **Stage 07** `relative_rotation_vectors.csv` | **Different SHA256** | **T3_R1 only** — active `b1ec3c6b…` vs archive `ced54d0d…` |
| **Stage 08** `filtered_relative_rotation_vectors.csv` | **Different size + sampled hash** | **All 6** sessions — active files ~10–15% larger |
| **Stage 08** `stage08_flag_report.csv` | Present on active only | Active has fuller filtering QC artifacts |

**Interpretation:**

- Archive 671 Take folders preserve an **older stage08 filtering generation** (pre-current pipeline).
- Stage 07 rotvecs are largely unchanged except **T3_R1**, where archive and active disagree — this may reflect a re-run or frame-range fix and **should be documented before move**.
- **audit_rerun_*** trees are **not duplicates** — they exist only under archive and capture audit-era outputs.

### layer2_exports subfolder

| Location | Size | Status |
|----------|------|--------|
| `outputs/archive/layer2_exports/` | ~134 MB | Archive-era exports |
| `outputs/layer2_exports/` (active) | ~1 GB | **Current** bundle used by Layer 2.5 summaries |

---

## Scientific significance of differences

| Difference | May matter because | Impact on current chain |
|------------|-------------------|-------------------------|
| Stage 08 archive vs active | Filtering policy / flag handling evolved after archive snapshot | **None** — Layer 2.5 and Layer 3 use **active** stage08 / `layer2_exports` |
| T3_R1 stage 07 mismatch | Could indicate corrected rotation-vector extraction for T3 | **Low for poster** if current batch used active path; **medium for historical audit** |
| audit_rerun_* folders | Document Layer 2 QC audit methodology (Jun 2026) | **None for rerun** of Layer 3; **value for methods appendix / audit trail** |
| Archive root stage indices | Point to archived run paths | **None** — active indices live in `outputs/stage*_index.*` |

---

## Poster reproduction dependency

**Does not depend on Layer 2 archive.**

Verified chain (`POSTER_REPRO_PATH_CHECK.md`):

1. `scripts/make_poster_*.py` → `poster_ready_evidence_package/` + batch `193319`
2. Batch `193319` built from Layer 2.5 `pre_jvcpca_review` exports
3. Layer 2.5 `session_index.scan_layer2_sessions()` **explicitly skips** paths under `archive/`

No poster script references `Layer2_Motive_Kinematics/outputs/archive`.

---

## Layer 3 canonical batch dependency

**Does not depend on Layer 2 archive.**

| Layer | Input source |
|-------|--------------|
| Layer 3 batch `193319` | Layer 2.5 g4 export parquets + manifests |
| Layer 2.5 exports | Active `Layer2_Motive_Kinematics/outputs/*_Take_*` and `layer2_exports/` |
| Layer 2 archive | **Not scanned** by `session_index.py` |

Moving archive off-disk would **not** invalidate existing batch `193319` artifacts on disk.

Regenerating batch from scratch would still use active Layer 2 paths, not archive.

---

## Would moving require rerunning data?

| Scenario | Rerun needed? |
|----------|---------------|
| Continue using existing batch `193319` + poster figures | **No** |
| Re-run poster scripts from existing evidence package | **No** |
| Re-export Layer 2.5 windows from notebooks | **No** (uses active Layer 2) |
| Re-run full Layer 3 batch | **No** (uses Layer 2.5 exports) |
| Re-open Layer 2 Jun-2026 QC audit comparing audit_rerun outputs | **Yes** — need archive accessible **somewhere** (external path OK) |
| Forensic compare old vs new stage08 for 671 | **Yes** — need archive accessible externally |

**Conclusion:** Moving outside repo does **not** force analysis rerun if external archive remains mounted/available. Deleting would.

---

## Script and documentation references

### Active code (Layer 2.5)

| File | Reference | Runtime impact |
|------|-----------|----------------|
| `session_index.py` | Skips dirs where `archive` in parent path names | **Archive excluded from discovery** |
| `discovery.py`, `load_layer2.py`, `gaga_batch_export.py` | Resolve paths under user-supplied Layer 2 root | Use active sessions when index built |
| `pilot_safety_report.py` | `_find_layer2_export(base_dir, …)` | No hard-coded archive path |

**No matches** in Layer 3 `src/` or `scripts/`, root `scripts/`, or Layer 2.5 tests for `outputs/archive` as a read path.

### Documentation only

References appear in cleanup docs (Stages A–B.10), `PROJECT_STATUS.md`, `CLEANUP_INDEX.md`, and:

- `Layer2_Motive_Kinematics/docs/LAYER2_KINEMATIC_CHAIN_QC_AUDIT_2026-06-23.md` — cites `outputs/audit_rerun_*` (note: audit folders live under **`outputs/archive/audit_rerun_*`** on disk today)

### Git legacy

389 files under archive remain in Git index from before ignore rules. Move should be paired with explicit `git rm --cached` plan (Stage C.1+), not required for runtime.

---

## Risks and recommended safeguards

| Risk | Level | Safeguard |
|------|-------|-----------|
| Lose audit trail for Layer 2 QC report | Medium | Move to external archive, do not delete; keep restore command |
| T3_R1 stage07 diff unexplained | Medium | Document diff in Stage C.1 before move; optional side-by-side note |
| Broken doc links to `outputs/archive/` | Low | Update paths in docs after move |
| Git index bloat (389 tracked files) | Low | `git rm --cached` after move (separate commit) |
| Accidental move of active sessions | High | Verify source path is **only** `outputs/archive/`; post-check active `*_Take_*` |
| Poster / batch breakage | Low | Post-move verification checklist (batch, evidence package, poster figures) |

### Pre-move checklist (before Stage C execution)

1. Confirm poster submission timeline (defer move until after if conservative).
2. Document T3_R1 stage07 active vs archive difference (1-page note).
3. Verify batch `193319` + evidence package + poster scripts still pass path checks.
4. Plan Git untrack for 389 legacy files.
5. Copy/move to external path with `du` verification (source size = destination size).
6. Keep restore command tested on a small subfolder if desired.

---

## Recommendation (Stage C.0)

### **Move outside repo after poster submission**

**Rationale (conservative):**

1. Runtime pipeline and poster **do not read** this archive today.
2. Archive is **not byte-identical** — contains unique `audit_rerun_*` history and older stage08 snapshots.
3. T3_R1 stage07 mismatch deserves a **short scientific note** before move (not a blocker for external storage).
4. ~22 GB relief is high value, but poster period is the wrong time to lose quick local access to audit artifacts.
5. **Do not split** archive by session — complexity outweighs benefit; move as one unit to external storage after poster.

**Not recommended now:**

- **Move immediately** — acceptable technically, but conflicts with “keep until poster” guidance from Stages A/B.
- **Delete** — never without external backup.
- **Keep in place indefinitely** — leaves ~22 GB visual clutter in project.

---

## Related artifacts

| Document | Purpose |
|----------|---------|
| [`STAGE_C0_LAYER2_ARCHIVE_MOVE_PLAN.md`](STAGE_C0_LAYER2_ARCHIVE_MOVE_PLAN.md) | Proposed move procedure (not executed) |
| [`STAGE_C0_KEEP_VS_MOVE_DECISION_TABLE.csv`](STAGE_C0_KEEP_VS_MOVE_DECISION_TABLE.csv) | Per-path keep/move matrix |
| [`../cleanup_stage_A/checksum_comparison.csv`](../cleanup_stage_A/checksum_comparison.csv) | Stage A hash evidence |
| [`../cleanup_stage_B/STAGE_B9_OUTPUT_SLIMMING_PLAN.md`](../cleanup_stage_B/STAGE_B9_OUTPUT_SLIMMING_PLAN.md) | Size context |

---

*Review only. Layer 2 archive not moved in Stage C.0.*
