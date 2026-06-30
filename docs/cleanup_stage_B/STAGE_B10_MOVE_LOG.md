# Stage B.10 — Move Log

**Date:** 2026-06-30  
**Operation:** Move top-level `archive/` outside repository  
**Errors:** None

---

## Commands used

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project

mkdir -p ../gaga_psylo_external_archive

mv archive ../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B
```

---

## Source / destination

| | Path |
|---|------|
| **Source (before)** | `3Layers_project/archive/` |
| **Destination (after)** | `../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/` |
| **Absolute destination** | `/Users/drorhazan/Desktop/gaga_psilo/projects/gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/` |

---

## Verification

| Check | Result |
|-------|--------|
| Source `archive/` no longer in repo | **OK** — path absent |
| Destination exists | **OK** |
| Size at destination | **2.0 GB** (`du -sh`) |
| File count at destination | **8,432 files** |
| Canonical batch `193319` | **OK** — unchanged |
| `poster_ready_evidence_package/` | **OK** — unchanged |
| `outputs/poster_final_figures/` | **OK** — unchanged |
| `Layer2_Motive_Kinematics/outputs/archive/` | **OK** — still **22 GB**, not moved |

---

## Pre-move checks (recorded)

| Check | Result |
|-------|--------|
| `archive/` existed | Yes |
| Git ignore | `.gitignore:89:archive/` |
| Git tracked files under `archive/` | 0 |
| Pre-move size | 2.0 GB |

---

## Contents moved

```
archive_2026-06-30_cleanup_stage_B/
└── 2026-06-30_cleanup_stage_B/
    ├── layer3_superseded_batches/   (5 superseded gaga_batch_* folders)
    └── layer2_5_scratch_archive/    (reevluate_project + old L2.5 outputs/archive)
```

Original Stage B internal moves documented in `docs/cleanup_stage_B/move_log.csv`.

---

## Restore command

From repository root:

```bash
mv /Users/drorhazan/Desktop/gaga_psilo/projects/gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B \
   /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/archive
```

Relative form:

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
mv ../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B archive
```

---

## Post-move Git status summary

- **No change to Git index** — `archive/` was gitignored with no tracked files.
- Working tree still shows ~115 status lines (modified analysis code, untracked Layer 3 files) — same as before B.10.
- New untracked documentation: `docs/cleanup_stage_B/STAGE_B10_*.md` (not committed per B.10 rules).

---

*Move completed successfully. No deletions. Stage C not started.*
