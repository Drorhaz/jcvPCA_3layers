# Stage B.6 — Deleted Tracked Files Review

**Date:** 2026-06-30  
**Total deleted paths in `git status`:** 12  
**Action taken in Stage B.6:** Documentation only — **no restore, no automatic `git rm`**

---

## Summary table

| Path | On disk at original? | Cause | Recommendation |
|------|----------------------|-------|----------------|
| 9× `reevluate_project/*` | **No** (moved to archive) | Stage B move | **Accept deletion in git** |
| `671_ex_segmentatios_frames.xlsx` (old path) | **No** (relocated) | Path reorganization | **Accept deletion** + **add** `segmentation/671_ex_segmentatios_frames.xlsx` |
| `mapping_logic_table.csv` | **No** | Export refactor / removed artifact | **Manual review** — likely accept deletion |
| `joint_overlap_table.csv` | **No** | Export refactor / removed artifact | **Manual review** — likely accept deletion |

---

## Group 1 — Stage B archive move (9 files)

**Intentionally moved to:**

```
archive/2026-06-30_cleanup_stage_B/layer2_5_scratch_archive/reevluate_project/
```

| Deleted path | In archive? |
|--------------|-------------|
| `Layer2.5_Segmentation/reevluate_project/artifact_events.csv` | Yes |
| `Layer2.5_Segmentation/reevluate_project/gaps_over_0p2s.csv` | Yes |
| `Layer2.5_Segmentation/reevluate_project/gaps_over_0p5s.csv` | Yes |
| `Layer2.5_Segmentation/reevluate_project/layer1_segmentation_notebook_manifest.json` | Yes |
| `Layer2.5_Segmentation/reevluate_project/layer2_qc_link_manifest.csv` | Yes |
| `Layer2.5_Segmentation/reevluate_project/layer2_qc_session_manifest.csv` | Yes |
| `Layer2.5_Segmentation/reevluate_project/qc_mask.csv` | Yes |
| `Layer2.5_Segmentation/reevluate_project/qc_mask_intervals.csv` | Yes |
| `Layer2.5_Segmentation/reevluate_project/revised_pre_jvcpca_review_tables.md` | Yes |

**Decision:** **Remain deleted in git index.**

**Rationale:**

- Scratch/re-evaluation folder deliberately removed from active tree (Stage B).
- Content preserved locally under `archive/` (gitignored — not in remote repo).
- Restoring to original path would undo cleanup.

**If you need these in git history:** Do not restore to old path; optionally add a README pointer in `docs/` to archive location (already in `move_log.csv`).

---

## Group 2 — Segmentation xlsx relocation (1 file)

| Deleted path | New location | New file exists? |
|--------------|--------------|------------------|
| `Layer2.5_Segmentation/671_ex_segmentatios_frames.xlsx` | `Layer2.5_Segmentation/segmentation/671_ex_segmentatios_frames.xlsx` | **Yes** |

**Decision:**

1. **Accept deletion** of old path when committing.
2. **Stage new path** explicitly: `Layer2.5_Segmentation/segmentation/671_ex_segmentatios_frames.xlsx`
3. Also stage `Layer2.5_Segmentation/segmentation/252_ex_segmentatios_frames.xlsx` (never tracked; scientifically important).

**Do not restore** old root-level path.

---

## Group 3 — Missing export CSVs (2 files)

### `Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T1_P1_R2/671_T1_P1_R2_g4_s14040_e20880/mapping_logic_table.csv`

| Check | Result |
|-------|--------|
| Original path exists | **No** |
| Copy in archive | **No** |
| Related export still exists | Yes — same folder has `pilot_export_validation_report.json`, `window_export_manifest.json` (modified tracked) |

**Decision:** **Manual review** — **likely accept deletion.**

**Rationale:** File appears superseded by export manifest / validation report changes in active Layer 2.5 work. No evidence it was moved rather than dropped.

**If needed:** Regenerate from Layer 2.5 export pipeline or recover from git history (`git show HEAD:...`) before committing deletion.

---

### `Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/joint_overlap_table.csv`

| Check | Result |
|-------|--------|
| Original path exists | **No** |
| Copy in archive | **No** |
| Code changes | `joint_overlap.py` modified (tracked) |

**Decision:** **Manual review** — **likely accept deletion.**

**Rationale:** Participant-level joint overlap table may have been replaced by per-export logic or consolidated elsewhere. Confirm with Layer 2.5 export changes before commit.

**If needed:** Regenerate via updated export scripts or restore from git history.

---

## What NOT to do automatically

- **Do not** `git restore` reevluate paths to active tree without reversing Stage B archive policy.
- **Do not** commit deletions for Group 3 without confirming export pipeline no longer produces these files.
- **Do not** add `archive/` contents to git to "fix" deletions — archive stays local and gitignored.

---

## Suggested commit-time handling

| Group | Git action when committing |
|-------|----------------------------|
| reevluate (9) | Stage deletions (`git add -u Layer2.5_Segmentation/reevluate_project/`) |
| xlsx relocate | Stage deletion + `git add Layer2.5_Segmentation/segmentation/*.xlsx` |
| missing CSVs (2) | After manual OK: `git add -u` on those paths, or `git rm` if needed |

---

*See `STAGE_B6_COMMIT_PLAN.md` for explicit commands.*
