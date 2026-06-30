# R1 — Layer 2 Archive External Move

**Date:** 2026-06-30  
**Stage:** R1 — research continuation (poster complete)  
**Operation:** Reversible move only — no deletion

---

## Summary

Moved the historical Layer 2 archive (~22 GB) outside the repository to reduce project size while preserving recoverability.

| | |
|---|---|
| **Source** | `Layer2_Motive_Kinematics/outputs/archive/` |
| **Destination** | `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` |
| **Size moved** | **22 GB** (23,086,228 KB; 852 files) |
| **Errors** | None |

---

## Command used

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project

mkdir -p ../gaga_psylo_external_archive

mv Layer2_Motive_Kinematics/outputs/archive \
   ../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30
```

---

## Pre-move verification

| Check | Result |
|-------|--------|
| Source exists | OK |
| Destination parent exists | OK (created if needed) |
| Destination path free | OK |
| Canonical batch `193319` | OK |
| Layer 2.5 `pre_jvcpca_review/` | OK |
| Poster evidence package | OK |
| Poster final figures | OK |
| Raw data not in move path | OK (no `data/` under archive) |
| Pre-move size / files | 22G / 852 |

---

## Post-move verification

| Check | Result |
|-------|--------|
| Source `outputs/archive/` absent | OK |
| Destination exists | OK |
| Post-move size / files | 22G / 852 (matches pre-move) |
| Batch `193319` | OK |
| Active Layer 2 session (671 T1 R1) | OK |
| Active `layer2_exports/` | OK |
| Layer 2.5 exports | OK |
| Layer 2 raw `data/` | OK (untouched) |
| Poster evidence + figures | OK |

**External archive siblings:**

- `../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/` (Stage B.10)
- `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` (this move)

---

## Restore command

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project

mv ../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30 \
   Layer2_Motive_Kinematics/outputs/archive
```

Absolute form:

```bash
mv /Users/drorhazan/Desktop/gaga_psilo/projects/gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30 \
   /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/outputs/archive
```

---

## Risks

| Risk | Level | Mitigation |
|------|-------|------------|
| Loss of Layer 2 QC audit trail (`audit_rerun_*`) | Medium if deleted | External copy retained; restore command above |
| Broken doc links to `outputs/archive/` | Low | Update docs; archive index in `results/archive_index/` |
| Git shows 389 deleted tracked files | Low | Plan `git rm --cached` in separate doc commit |
| Active pipeline breakage | **None observed** | `session_index.py` skips archive paths; active sessions unchanged |
| Poster / batch breakage | **None observed** | Post-move checks passed |

---

## What remains active (in repo)

| Path | Role |
|------|------|
| `Layer2_Motive_Kinematics/outputs/*_Take_*` | 12 active session trees (~31 GB) |
| `Layer2_Motive_Kinematics/outputs/layer2_exports/` | Layer 2.5 parquet bundle (~1 GB) |
| `Layer2_Motive_Kinematics/data/` | Raw Layer 2 inputs |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | Layer 3 upstream exports |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | Canonical batch |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | Poster CSVs |
| `outputs/poster_final_figures/` | Poster deliverables |

---

## Git note

389 files under the moved path were historically tracked in Git. Physical move does not update the index. Recommended follow-up: explicit `git rm --cached` on archive paths (separate commit when requested).

---

*Move executed per Stage C.0 plan, post-poster research continuation mode.*
