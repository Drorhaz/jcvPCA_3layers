# Stage B.10 — Move Plan: Top-Level `archive/` Outside Repo

**Date:** 2026-06-30  
**Stage:** B.10 — physical slimming (external archive)  
**Prerequisite:** Stage B.9 output audit; checkpoint commits `393fb68`, `c6cc222`, `ced27e5`

---

## Source path

```
archive/
```

**On-disk structure (pre-move):**

```
archive/
└── 2026-06-30_cleanup_stage_B/
    ├── layer3_superseded_batches/     (5 superseded gaga_batch_* folders)
    └── layer2_5_scratch_archive/      (reevluate_project + old L2.5 outputs/archive)
```

**Estimated size:** ~2.0 GB (2,058 MB per Stage B.9 audit; `du -sh` ≈ 2.0G)

---

## Destination path

```
../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/
```

**Absolute path (expected):**

```
/Users/drorhazan/Desktop/gaga_psilo/projects/gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/
```

**Parent folder to create if missing:**

```
../gaga_psylo_external_archive/
```

---

## Pre-move verification

| Check | Expected | Status |
|-------|----------|--------|
| `archive/` exists | Yes | Verified |
| `archive/` gitignored | `.gitignore:89:archive/` | Verified |
| Destination parent writable | Create if needed | Verified at move time |
| No Git-tracked files under `archive/` | 0 tracked | Verified (ignored since B.6) |

---

## Why it is safe to move

1. **Gitignored** — nothing in `archive/` is in the remote index; move does not affect Git history.
2. **Superseded content only** — Stage B moved superseded Layer 3 batches and Layer 2.5 scratch here; canonical batch `193319` was never in this tree.
3. **Documented** — original Stage B moves recorded in `docs/cleanup_stage_B/move_log.csv`.
4. **Poster chain independent** — poster scripts reference `poster_ready_evidence_package/`, batch `193319`, and `outputs/poster_final_figures/` — none live under top-level `archive/`.
5. **Reversible** — single `mv` command restores the folder.

---

## Risks

| Risk | Level | Mitigation |
|------|-------|------------|
| Broken relative paths in old notes referencing `archive/` | Low | Update docs; restore command documented |
| External drive/path unavailable on another machine | Medium | Document absolute path; user copies external archive with project |
| Accidental move of wrong folder | Low | Explicit source/destination checks before and after |
| Layer 2 `outputs/archive/` touched | **Must not happen** | Separate path; verified post-move |

**Risk level overall:** **Low** for active analysis and poster reproduction.

---

## How to restore

From repository root:

```bash
mkdir -p ../gaga_psylo_external_archive  # if needed
mv ../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B archive
```

Or restore to original name only:

```bash
mv /Users/drorhazan/Desktop/gaga_psilo/projects/gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B \
   /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/archive
```

---

## Poster reproduction — not affected

| Path | Role | Under `archive/`? |
|------|------|-------------------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | Canonical batch | **No** |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | Poster CSVs | **No** |
| `outputs/poster_final_figures/` | Poster outputs | **No** |
| `scripts/make_poster_*.py` | Generator scripts | **No** |

Superseded batches in `archive/` are **not** referenced by poster scripts (`POSTER_REPRO_PATH_CHECK.md`).

---

## Layer 2 `outputs/archive/` — not touched

| Path | Size (approx) | Stage B.10 action |
|------|---------------|-------------------|
| `Layer2_Motive_Kinematics/outputs/archive/` | ~22 GB | **No move** — deferred to Stage C |

This move targets **only** top-level `archive/` (~2 GB).

---

## Planned command

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
mkdir -p ../gaga_psylo_external_archive
mv archive ../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B
```

---

*Plan only until move executed; see `STAGE_B10_MOVE_LOG.md` after move.*
