# M12 Pre-Analysis Readiness Review

**Date:** 2026-06-30  
**Mode:** Readiness review only — **no analysis executed**  
**Prerequisite:** M1–M11 complete ([`MASTER_CONTINUATION_PLAN.md`](MASTER_CONTINUATION_PLAN.md))  
**Related:** [`CONTINUATION_RUNBOOK.md`](CONTINUATION_RUNBOOK.md)

---

## Executive summary

| Check | Result |
|-------|--------|
| Path registry | **PASS** — `check_project_paths.py` exit 0 |
| Canonical batch `193319` | **Intact** on disk |
| Participant 671 | **Ready** for new batch (exports + L2 sessions present) |
| Participant 252 | **Mostly ready** — exports present; QC warnings + untracked raw data in Git |
| Overwrite risk to `193319` | **Low** if new batch uses timestamped `--output-dir` |
| Raw data staging for M12 | **Not required** for Layer 3 batch (reads L2.5 parquet exports) |

**Recommended first M12 action:** **M12a — dry-run / validation only** (no JcvPCA, no new batch folder write beyond optional dry-run outputs).

---

## 1. Path check result

Command run:

```bash
python scripts/check_project_paths.py
```

**Result:** Exit **0** — all required registry paths exist.

Highlights:

| Registry key | Status |
|--------------|--------|
| `layer3.canonical_batch` | OK — `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319` |
| `layer2_5.pre_jvcpca_review` | OK |
| `layer2.active_session_glob` | OK — 12 `*_Take_*` sessions |
| `layer3.poster_evidence_package` | OK |
| `external_archive.layer2_outputs_archive` | OK (off-repo) |
| `participants.batch_cohort` | `671`, `252` |

YAML loader: minimal fallback (PyYAML optional).

---

## 2. Current canonical batch

| Item | Value |
|------|-------|
| **Batch ID** | `gaga_batch_jcvpca_20260626_193319` |
| **Path** | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` |
| **Config** | `layer3.canonical_batch`, `layer3.canonical_batch_id` in [`config/paths.yaml`](../../config/paths.yaml) |
| **Poster-era status** | Frozen — do not overwrite or modify for M12 |

Canonical batch summary (on disk): **20 comparisons completed** (`batch_summary.md`).

---

## 3. Layer 2.5 exports — participants detected

Under `Layer2.5_Segmentation/outputs/pre_jvcpca_review/`:

| Participant folder | Present |
|--------------------|---------|
| `671/` | Yes |
| `252/` | Yes |
| `session_window/` | Yes (shared metadata) |

Central manifest: `layer25_export_manifest.csv` (2026-06-26).

### g4 combined windows (batch inputs)

| Participant | g4 folders on disk | Manifest rows (total) | Manifest g4 rows | `layer3_safe=true` | QC `warning` rows |
|-------------|-------------------|----------------------|------------------|--------------------|-------------------|
| **671** | **6** | 36 | 6 | 36/36 | 36/36 |
| **252** | **6** | 36 | 6 | 36/36 | 34/36 |

**671 g4 windows:** T1/T2/T3 × P1/P2 (R1/R2 sessions as exported).

**252 g4 windows:** T1/T2/T3 × P1/P2 — all six combined windows present on disk.

Feature manifests committed (M7):

- `Layer2.5_Segmentation/config/group4_core_14link_within_671_feature_manifest.csv`
- `Layer2.5_Segmentation/config/group4_core_16link_within_252_feature_manifest.csv`

---

## 4. Layer 2 active sessions

| Participant | `*_Take_*` session folders |
|-------------|----------------------------|
| 671 | 6 |
| 252 | 6 |

Layer 2 raw tree for 252 exists on disk (`Layer2_Motive_Kinematics/data/252/T1|T2|T3`) but is **untracked in Git** (gitignored kinematic CSVs — expected).

252 `data_description/` CSVs for T3 sessions were committed in M7b.

---

## 5. Participant readiness

### 671 — appears ready

- Canonical batch already built from this cohort.
- 6 L2 sessions, 6 L2.5 g4 exports, central manifest populated.
- All manifest rows marked `layer3_safe=true` (QC warnings present but consistent with prior successful batch).
- **No L2.5 re-export required** before a validation pass or optional new batch.

### 252 — appears mostly ready (verify before full cohort batch)

- **On disk:** 6 L2 sessions, 6 g4 exports, 36 manifest rows — structurally parallel to 671.
- **Gaps / caveats:**
  - 34/36 manifest rows have `qc_status=warning` (review before treating 252 as production-ready).
  - L2 raw data untracked in Git (not a runtime blocker; do not stage raw CSVs).
  - 252 was in canonical `193319`; a *new* batch would re-validate 252 under current exports.
- **Not missing:** g4 export folders or L2 session outputs for the six expected windows.

---

## 6. Input gaps remaining

| Gap | Severity | Blocks M12a? | Blocks M12b/d? |
|-----|----------|---------------|----------------|
| QC warnings on 252 exports (34/36) | Medium | No | Review before M12d |
| L2 raw 252 untracked in Git | Low | No | No |
| Uncommitted L3 planning docs/figures | None | No | No |
| Modified unstaged PDF reference | None | No | No |
| No `--dry-run` flag on `run_gaga_batch_jcvpca.py` | Info | Use M12a validators below | — |

No missing g4 folders detected for either participant.

---

## 7. Raw data — would M12 require staging or touching?

**No.**

Layer 3 batch reads **Layer 2.5 pre_jvcpca_review parquet exports** and manifests, not raw Motive CSVs.

| Data class | M12 batch reads? | Git staging needed? |
|------------|------------------|-------------------|
| L2.5 export parquet/manifests | Yes | No (gitignored outputs) |
| L2 raw CSVs | No | **Do not stage** |
| Canonical batch `193319` | No (unless explicitly pointed via `--output-dir`) | No |

---

## 8. Generated outputs — overwrite risk

| Target | M12a (validation) | M12b/c | M12d (new batch) |
|--------|-------------------|--------|------------------|
| `gaga_batch_jcvpca_20260626_193319/` | **Not touched** | **Not touched** if new `--output-dir` | **Not touched** if timestamped dir |
| `poster_ready_evidence_package/` | Not touched | Not touched | Not touched by batch runner alone |
| L2.5 export trees | Read-only in M12a | M12c could write exports | Read unless re-export approved |

**Safe pattern for any real batch (M12b/d):**

```bash
--output-dir ../outputs/gaga_batch_jcvpca_$(date -u +%Y%m%d_%H%M%S)
```

Never set `--output-dir` to the canonical `193319` path.

---

## 9. Git / repo hygiene (non-blocking)

Current dirty summary (~29 entries):

- Modified: `Layer3_JcvPCA/references/JcvPCA and JsvCRP.pdf`
- Untracked gitignored: L2/L3 `outputs/`, L2 `data/252/`, L3 planning docs

None of these block M12a validation.

---

## 10. M12 action options

| ID | Action | JcvPCA? | New batch dir? | When to use |
|----|--------|---------|----------------|-------------|
| **M12a** | Dry-run / validation only | **No** | **No** | **First — recommended** |
| **M12b** | 671-only test batch | Yes | Yes (new timestamp) | After M12a passes; smoke-test runner |
| **M12c** | 252 onboarding / export check | Maybe export | Maybe | If manifest/QC review finds 252 gaps |
| **M12d** | Full 671+252 timestamped batch | Yes | Yes | After M12a (+ optional M12b) and 252 QC sign-off |

---

## 11. Recommended first M12 action: **M12a**

**Rationale:**

1. Confirms config-driven paths and sidecar inputs without compute.
2. Does not write a new batch folder or run JcvPCA.
3. 252 QC warnings should be reviewed before M12d even though exports exist.
4. Canonical `193319` remains untouched.

### Exact commands (do not run until M12 approved — listed for copy/paste)

From repository root:

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project

# 1. Path registry (already passed 2026-06-30)
python scripts/check_project_paths.py

# 2. Confirm canonical batch pointer
python -c "
import sys; sys.path.insert(0,'src')
from project_paths import load_project_paths
p = load_project_paths()
print('canonical_batch_id:', p.layer3_canonical_batch_id)
print('exists:', p.layer3_canonical_batch.is_dir())
"

# 3. Layer 2.5 export manifest sanity (read-only)
wc -l Layer2.5_Segmentation/outputs/pre_jvcpca_review/layer25_export_manifest.csv
find Layer2.5_Segmentation/outputs/pre_jvcpca_review/671 -type d -name '*_g4_*' | wc -l
find Layer2.5_Segmentation/outputs/pre_jvcpca_review/252 -type d -name '*_g4_*' | wc -l

# 4. Layer 3 read-only report validators (no MD regeneration)
cd Layer3_JcvPCA/scripts
python generate_final_integrated_review.py --validate-paths
python generate_master_full_numeric_report.py --dry-run
python generate_movement_organization_question_report.py --validate-paths

# 5. Batch runner CLI check (no execution)
python run_gaga_batch_jcvpca.py --help

# 6. Optional: lightweight unit tests if Layer 3 env has deps
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
python -m pytest Layer3_JcvPCA/tests/test_inventory.py Layer3_JcvPCA/tests/test_dataset_builder.py -q
```

**Expected M12a outcome:** All validators exit 0; no new folders under `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_*` except any pre-existing ignored outputs.

---

## 12. Next steps after M12a (requires separate approval)

| Step | Action | Command sketch |
|------|--------|----------------|
| M12b | 671-only smoke batch | `python run_gaga_batch_jcvpca.py --participant 671 --output-dir ../outputs/gaga_batch_jcvpca_$(date -u +%Y%m%d_%H%M%S)` |
| M12c | 252 QC / export review | Inspect `layer25_export_readiness_report.csv`; optionally `cd Layer2.5_Segmentation && python scripts/build_gaga_exports.py --help` |
| M12d | Full cohort batch | `python run_gaga_batch_jcvpca.py --output-dir ../outputs/gaga_batch_jcvpca_$(date -u +%Y%m%d_%H%M%S)` |

See [`CONTINUATION_RUNBOOK.md`](CONTINUATION_RUNBOOK.md) Sections 6–7 for promotion workflow after a successful new batch.

---

## 13. Stop conditions (unchanged)

Do not proceed to M12b/d if:

- Path check fails
- `--validate-paths` reports missing batch sidecars
- `--output-dir` would point at `193319`
- 252 QC review unresolved when running full cohort batch

---

*Readiness review completed without analysis execution, batch generation, file moves, or deletions.*
