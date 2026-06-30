# M4 Batch Summary — Untrack Layer 2.5 export outputs

**Date:** 2026-06-30  
**Batch:** M4 — Untrack Layer 2.5 pre-JcvPCA export outputs

## Files changed

- Git index only: 15 paths under `Layer2.5_Segmentation/outputs/`
- No on-disk deletions

## Files staged

- 15 export/manifest/session_index paths via `git rm --cached`

## Commit hash

`740ee1d` — `chore: untrack Layer 2.5 pre-JcvPCA export outputs`

## Validation commands run

- `test -d Layer2.5_Segmentation/outputs/pre_jvcpca_review/671` — **OK**
- `python scripts/check_project_paths.py` — **exit 0**
- `git diff --cached --stat` — 15 index deletions

## Analysis run?

**No**

## Raw data touched?

**No**

## Generated data moved/deleted from disk?

**No**

## Scientific logic changed?

**No**

## Remaining dirty status summary

- Git index cleanup (M2–M4) complete
- ~45 modified tracked source files (L2.5/L3) remain
- ~59 untracked paths (L3 automation, L2.5 additions) remain

## Next batch

**M5** — movement organization report path refactor (blocked in plan mode — requires agent mode for `.py` edits)
