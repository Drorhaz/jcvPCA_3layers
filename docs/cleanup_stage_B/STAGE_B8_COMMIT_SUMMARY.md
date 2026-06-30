# Stage B.8 — Checkpoint Commit Summary

**Date:** 2026-06-30  
**Stage:** B.8 complete — first cleanup checkpoint committed

---

## Commit

| Field | Value |
|-------|-------|
| **Hash** | `393fb683ec3e521a274e8713b56425931353736a` |
| **Short hash** | `393fb68` |
| **Message** | `chore: checkpoint project cleanup through stage B` |
| **Branch** | `main` |

---

## Change statistics

| Metric | Value |
|--------|-------|
| Files changed | **57** |
| Insertions | **+46,094** |
| Deletions | **−31,650** |

### Deletions committed (11 paths)

- 2× superseded export CSVs (`mapping_logic_table.csv`, `joint_overlap_table.csv`)
- 9× `reevluate_project/*` (moved to local `archive/` in Stage B)

### Relocation

- `671_ex_segmentatios_frames.xlsx` → `Layer2.5_Segmentation/segmentation/671_ex_segmentatios_frames.xlsx` (rename, 65% similarity)
- New: `segmentation/252_ex_segmentatios_frames.xlsx`

### Major additions

- `.gitignore` (Stage B.6 rules)
- Cleanup documentation (Stages A–B.8)
- Poster generator scripts + plot tables/captions
- `PROJECT_STATUS.md`, `docs/CLEANUP_INDEX.md`, audit draft

---

## Post-commit working tree

**Not clean** — intentional. This commit was scoped to cleanup/docs only.

### Modified, unstaged (~45 tracked files)

| Area | Count (approx) | Deferred to |
|------|----------------|-------------|
| Layer 2.5 source, tests, notebooks, dashboard | ~26 | Second commit |
| Layer 2.5 export JSON/MD under `pre_jvcpca_review/671/` | ~9 | Second commit or gitignored |
| Layer 2 stage indices | 16 | Second commit |
| Layer 3 README, viz.py, PDF reference | 3 | Second commit |

### Untracked (~60+ paths)

- New Layer 2.5 config manifests, export scripts, tests
- Layer 2 `data/252/`
- Layer 3 scripts, src modules, tests, docs, local outputs (evidence package, review reports)

Most Layer 3 batch outputs and `archive/` remain **gitignored** and correctly absent from git index.

---

## Verification retained

| Check | Status |
|-------|--------|
| `archive/` gitignored | Yes (`.gitignore:89`) |
| Canonical batch `193319` on disk | Yes |
| Poster evidence package on disk | Yes |
| Poster scripts committed | Yes |
| No raw data / batch outputs in commit | Confirmed |

Pre-commit record: [`STAGE_B8_PRE_COMMIT_VERIFICATION.md`](STAGE_B8_PRE_COMMIT_VERIFICATION.md)

---

## What this commit did NOT include

- Layer 2.5 / Layer 3 analysis code changes
- Layer 2 stage index updates
- Notebooks
- `archive/` contents
- Canonical batch or evidence package outputs
- Stage C physical moves

---

## Next recommended stages

1. **Optional second commit** — Layer 2.5 / Layer 3 source, tests, notebooks, Layer 2 indices (review and stage explicitly; still no `git add .`).

2. **Stage C (not started)** — Physical move of Layer 2 `outputs/archive/` (~22 GB) after poster submission and stronger verification; resolve `671_test_data_des/` export-type question.

3. **Local-only optional** — Copy `joint_overlap_table.csv` from `_archive/` if needed for Layer 2.5 notebook UX (documented in B.7; not required for poster).

---

*Checkpoint commit created per `STAGE_B7_COMMIT_PLAN_FINAL.md`. Stage C not started.*
