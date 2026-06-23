# Layer 2.5 Critical Fixes — Implementation Report

Scope: implement **only** the critical fixes (R1–R5) from
`LAYER2_5_PROGRAM_AUDIT_REPORT.md`. No broad refactor; no changes to Layer 1 QC
logic, Layer 2 quaternion/filter/jump/kinematic math, or Layer 3 JcvPCA logic.

Goal: make Layer 2.5 safe enough to guide a user from participant/session
selection to a **canonically aligned, QC-aware, Layer 3-ready export**, and remove
the critical silent-failure risks identified in the audit.

This document does not claim the program is scientifically final.

---

## 1. Files changed

| File | Change |
|---|---|
| `Layer2.5_Segmentation/notebooks/pre_jvcpca_review.ipynb` | Reworked workflow: input roots → discovery → participant/session selection → pairing status → joint overlap table → window + config-driven scope → warning panel → **canonical-only** Layer 3 export. Export button disabled until blocking checks pass. Legacy mapping/review kept under "Diagnostics". |
| `src/pre_jvcpca_review/export_window.py` | Canonical `export_pilot_window_for_jvcpca` now writes `layer3_safe=true`, a matrix summary `.md`, and optional identity/warnings into the manifest. Legacy `export_window_for_jvcpca` now writes `layer3_safe=false` + `legacy_layer3_warning`. Added `export_layer3_window` orchestrator (blocking warning gate + canonical export). Hardened `out_dir` coercion to `Path`. |
| `src/pre_jvcpca_review/discovery.py` | `resolve_layer1`/`resolve_layer2` are now subdir-aware so canonical export works directly on real output trees (`tables/`, `07_rotation_vectors/`, `08_filtered_rotvecs/`) and added real filenames (`qc_link_manifest.csv`, `qc_session_manifest.csv`, `filtered_relative_rotation_vectors.parquet`). |
| `src/pre_jvcpca_review/load_layer1.py` | `load_qc_mask` derives an aggregate `status` column from the real Layer 1 per-flag columns when absent (Layer 2.5-side adaptation; Layer 1 output unchanged). |

## 2. New modules added

| Module | Purpose |
|---|---|
| `src/pre_jvcpca_review/session_index.py` | Scans Layer 1/Layer 2 **output roots**, detects participants, lists sessions, pairs L1↔L2 by canonical session key `<subject>_T#_P#_R#`, and builds the full session index (all required columns). |
| `src/pre_jvcpca_review/pairing.py` | Pre-export L1↔L2 identity / source / frame / provenance / marker-set gate (minimal critical-checks wrapper). |
| `src/pre_jvcpca_review/joint_overlap.py` | Cross-session canonical link comparability: `directly_comparable`, `requires_composite_mapping`, `not_comparable`, `missing_in_some_sessions`, `ambiguous_requires_user_decision`. Direct-comparability detection only (no composite rotation math). |
| `src/pre_jvcpca_review/warnings.py` | Structured warning records + collector; severities `info`/`warning`/`strong_warning`/`blocking`; CSV + manifest serialization. |
| `src/pre_jvcpca_review/feature_scope.py` | Dependency-free loader for the default feature-scope config. |

## 3. Notebook cells changed

- Markdown cell 0: rewritten to describe the new participant→session→export workflow and the canonical-only / blocking guarantee.
- Code cell 1 (single control cell): imports, default **roots**, config-driven scope display, participant/session dropdowns, discovery/pairing/overlap handlers, pre-export warning panel, and a rewired **canonical** export handler. Legacy buttons retained under "Diagnostics".

## 4. New config files

- `config/default_feature_scope.yaml` — `default_body_scope`, `exclude_fingers: true`, `exclude_toes: true`, `core_link_set_name`, `allowed_feature_scope`, `feature_naming_policy: canonical_parent_child_axis`, `feature_manifest`, and excluded finger/toe child prefixes.

## 5. New output files (per run)

- Root: `outputs/pre_jvcpca_review/session_index.csv`
- Participant: `outputs/pre_jvcpca_review/<participant>/joint_overlap_table.csv`
- Window export dir `outputs/pre_jvcpca_review/<participant>/<session>/<window_label>/`:
  - `window_jvcpca_matrix.parquet`
  - `window_selected_rotvecs_long.parquet`
  - `window_joint_frame_flag_log.csv`
  - `window_warnings.csv`
  - `window_export_manifest.json` (incl. `layer3_safe`, `feature_naming_policy`, canonical feature order, pairing result, joint alignment status, warnings summary)
  - `window_jvcpca_matrix_summary.md`
  - `pilot_export_validation_report.json`

## 6. Tests added

`tests/test_layer2_5_critical_fixes.py` (13 tests) covering: default roots;
participant discovery; multiple-session discovery; unmatched flagging; pairing
source/frame mismatch blocking; missing-provenance non-blocking warning; canonical
naming (no `J00x`) + warnings written to CSV and manifest; legacy
`layer3_safe=false`; missing-required-feature block; incomplete-triplet block;
joint overlap direct/missing/composite classification; non-comparable feature
blocks export; blocking warning prevents export (no matrix written).

## 7. Tests run and results

- Export-focused suite (`test_canonical_pilot_export.py`, `test_pre_jvcpca_review.py`, `test_layer2_5_critical_fixes.py`): **29 passed**.
- Full suite: all pass **except two pre-existing failures unrelated to this work**, both in the older `layer2_motive.segmentation` subsystem that was not modified:
  - `tests/test_window_summary.py::test_layer1_summary_matches_brute_force` — the test file uses `pd` without `import pandas` (pre-existing bug).
  - `tests/test_validate_inputs.py::test_missing_time_column_still_validates_frame_based` — old validator subsystem, untouched.
- Notebook smoke test: cell executes; discovery finds participant `671` and 6 sessions; selecting a matched session enables export; canonical export produces a `(frames × 34)` matrix with first feature `Neck_to_Head_rx` and `layer3_safe=true`.

## 8. Remaining known limitations

- **"Core 16" maps to the frozen canonical manifest** (Group4 upper-body pilot = 10 links / 30 features), fingers/toes excluded. Widening to additional core links is a config/manifest change (`feature_manifest`), intentionally not invented here.
- **Layer 2 provenance** (git commit / config hash) is **not emitted** by current Layer 2 outputs → recorded as `unknown` with a (non-blocking) warning. Pinning provenance requires a Layer 2 change (out of scope).
- **Composite rotation math is not implemented.** Composite/non-comparable links are detected and **blocked** for cross-session Layer 3 export unless a harmonization manifest is supplied; harmonization itself is left for later.
- Window-scoped QC warnings (jump/mask/L1 overlap) are computed from the written flag log after a successful build; they are strong/info (non-blocking). NaN/inf in the matrix is blocked by the existing fail-fast gate unless "Allow NaN" is set.
- Deeper unification with `layer2_motive.segmentation.validate_inputs` was deliberately avoided (it expects the normalized single-folder layout); a minimal critical-checks wrapper is used instead.

## 9. Exact commands

Run tests:

```bash
cd Layer2.5_Segmentation
.venv/bin/python -m pytest tests/test_layer2_5_critical_fixes.py -q
```

Run the notebook UI:

```bash
cd Layer2.5_Segmentation
.venv/bin/jupyter lab notebooks/pre_jvcpca_review.ipynb   # or open in the IDE
```

Programmatic Layer 3-safe export (canonical only):

```python
import sys; sys.path.insert(0, "Layer2.5_Segmentation/src")
from pre_jvcpca_review.session_index import build_session_index, session_row
from pre_jvcpca_review.export_window import export_layer3_window

idx = build_session_index()                      # defaults to the two output roots
row = session_row(idx, "671_T1_P1_R2")
result = export_layer3_window(
    row["layer1_run_dir"], row["layer2_run_dir"],
    "outputs/pre_jvcpca_review/671/671_T1_P1_R2/window_01",
    frame_start=100, frame_end=199,
    session_row=row, window_label="window_01",
)
print(result["status"], result["warnings_summary"])
```

## 10. Is the export Layer 3-safe by default?

**Yes.** The notebook export button and `export_layer3_window` use the canonical
manifest-driven path only: feature names are `parent_to_child_axis`, the manifest
records `layer3_safe=true` and `feature_naming_policy=canonical_parent_child_axis`,
blocking warnings (identity/source/frame mismatch, missing required feature,
incomplete triplet, non-comparable-without-harmonization) **prevent** the matrix
from being written, and the legacy `J00x` path is marked `layer3_safe=false` and is
not reachable from the export button.
