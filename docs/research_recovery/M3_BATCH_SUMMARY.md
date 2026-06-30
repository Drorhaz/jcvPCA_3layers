# M3 Batch Summary — Untrack Layer 2 session outputs

**Date:** 2026-06-30  
**Batch:** M3 — Untrack generated Layer 2 session outputs

## Files changed

- Git index only: 385 paths under `Layer2_Motive_Kinematics/outputs/` (kept `.gitkeep`)
- No on-disk deletions

## Files staged

- 385 paths via `git rm --cached` (all tracked outputs except `.gitkeep`)

## Commit hash

`f322744` — `chore: untrack generated Layer 2 session outputs`

## Validation commands run

- `ls -d Layer2_Motive_Kinematics/outputs/*_Take_* | wc -l` — **12** session folders on disk
- `python scripts/check_project_paths.py` — **exit 0**
- `git diff --cached --stat` — 385 index deletions

## Analysis run?

**No**

## Raw data touched?

**No**

## Generated data moved/deleted from disk?

**No**

## Scientific logic changed?

**No**

## Remaining dirty status summary

- L2 output tracking cleared (`.gitkeep` only remains tracked under outputs/)
- 15 Layer 2.5 export paths still tracked (M4 target)
- L2.5 source / L3 untracked code unchanged

## Next batch

**M4** — untrack Layer 2.5 export outputs
