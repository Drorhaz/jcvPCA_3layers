# M2 Batch Summary — Layer 2 archive index cleanup

**Date:** 2026-06-30  
**Batch:** M2 — Git index cleanup for Layer 2 archive deletions

## Files changed

- Git index only: 389 paths under `Layer2_Motive_Kinematics/outputs/archive/` removed from tracking
- No on-disk file edits

## Files staged

- 389 deletions via `git rm --cached` on all tracked `outputs/archive/**` paths

## Commit hash

`0b8a15c` — `chore: stop tracking Layer 2 archive moved to external storage`

## Validation commands run

- `test -d ../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` — **OK**
- `git ls-files 'Layer2_Motive_Kinematics/outputs/archive/' | wc -l` — 389 before cleanup
- `git diff --cached --stat` — 389 files, index-only deletions
- Post-commit: archive `D` count — **0**

## Analysis run?

**No**

## Raw data touched?

**No**

## Generated data moved/deleted from disk?

**No** — archive data remains at `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/`

## Scientific logic changed?

**No**

## Remaining dirty status summary

- Archive deletion noise cleared from status
- ~386 Layer 2 active output paths still tracked (M3 target)
- Layer 2.5 / Layer 3 dirty entries unchanged

## Next batch

**M3** — untrack generated Layer 2 session outputs
