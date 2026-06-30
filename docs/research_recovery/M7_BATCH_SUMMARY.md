# M7 Batch Summary — Layer 2.5 source and tests

**Date:** 2026-06-30  
**Batch:** M7 — Commit Layer 2.5 source and tests (split M7a + M7b)

## Files changed

**M7a (20 files):** export pipeline `src/pre_jvcpca_review/*`, `scripts/build_gaga_exports.py`, config manifests, tests

**M7b (9 files):** dashboard, notebooks, 252 `data_description/` CSVs (session metadata per `paths.yaml`)

## Excluded

- `Layer2.5_Segmentation/outputs/**`
- `Layer2_Motive_Kinematics/data/252/` raw kinematic data

## Commit hashes

- `5b804cc` — M7a export pipeline source and tests
- `c95441c` — M7b dashboard, notebooks, descriptions

## Validation

- `git diff --cached --name-only` reviewed — no `outputs/` paths
- Lightweight pytest not run (environment may lack deps)

## Analysis run?

**No**

## Raw data touched?

**No** — only small DataDescriptions CSVs (configured input path)

## Generated data moved/deleted from disk?

**No**

## Scientific logic changed?

**No commit intent** — code already present locally; review diffs for export behavior separately

## Next batch

**M8** — Layer 3 automation source
