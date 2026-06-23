# Review-table repair diagnostic

Date: 2026-06-23  
Scope: `pre_jvcpca_review.ipynb` diagnostics buttons (Run mapping, Run full review, Show review tables)

## Summary

The review-table **backend** (`pre_jvcpca_review/build.py`, `tables.py`, `scripts/build_pre_jvcpca_review.py`) still works against real Layer 1 / Layer 2 output roots when given valid session directories. Failures in the notebook are primarily **integration and contract drift** issues, not broken Layer 1 / Layer 2 pipelines.

## Broken actions and root causes

### 1. Run mapping / Run full review

| Check | Finding |
|-------|---------|
| What fails? | `NotADirectoryError` / missing manifest when `LAYER1_DIR` / `LAYER2_DIR` are empty, or review runs before **Discover → participant → session**. |
| Path / discovery? | **Yes.** Session dirs are only populated after discovery; buttons did not gate on `CURRENT_ROW` or non-empty session paths. |
| Output location? | **Yes.** Review wrote to flat `outputs/pre_jvcpca_review/session_window` while export uses `outputs/pre_jvcpca_review/<participant>/<session>/<window_label>`. |
| Schema / naming? | Partial — tables lacked canonical identity and Stage 08 summary columns expected by the updated architecture. |
| Old verdict fields? | No — backend already uses Layer 1 evidence flags, not removed verdict labels. |
| Stage 08 NaN-only? | Partial — jump/block percentages existed but Stage 08 flag context and computational NaN counts were not surfaced separately. |
| Subprocess? | Works when venv has package installed; direct API is more reliable inside the notebook. |

### 2. Show review tables

| Check | Finding |
|-------|---------|
| What fails? | Shows **"Run full review first"** even after a successful review when tables were written under a different folder than the flat `OUTPUT_DIR`. |
| Path issue? | **Yes** — reads `OUTPUT_DIR/session_window` instead of participant/session/window folder. |
| Missing tables? | No structured warning for individual missing optional tables (silent skip). |

### 3. Default joint selection

| Check | Finding |
|-------|---------|
| What fails? | User sees "Select at least one joint" when pilot manifest resolution fails for a session. |
| Fix | Fall back to first three `core_candidate` links after manifest miss. |

### 4. DataDescriptions visibility

| Check | Finding |
|-------|---------|
| What fails? | Notebook passes DD path optionally but review summary only exposed `datadescriptions_used` boolean. |
| Fix | Record path, found/used flags, mapping mode, and warnings in `window_decision_summary.csv`. |

## What did **not** break

- Layer 1 / Layer 2 discovery and pairing (`session_index.py`)
- Canonical export path (`export_layer3_window`)
- Joint overlap / comparability tables
- Existing pytest suite for backend build + export (11/11 pass on fixtures)

## Repair plan (non-destructive)

1. Route review outputs to `outputs/pre_jvcpca_review/<participant>/<session>/<window_label>/`.
2. Gate review actions on discovery + session selection + non-empty L1/L2 dirs.
3. Call `build_mapping_only` / `build_full_review` directly from the notebook (same code as CLI).
4. Extend review tables with canonical link identity + Stage 08 flag summaries; write `window_warnings.csv` for missing optional evidence.
5. Restore **Show review tables** via shared display helper with per-table availability warnings.
6. Add focused regression tests; leave Layer 3 export path unchanged.
