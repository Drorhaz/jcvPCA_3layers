# Review-table repair — implementation report

Date: 2026-06-23

## 1. Broken review-table actions

| Action | Symptom |
|--------|---------|
| **Run mapping** | Failed when session dirs empty (before Discover) or wrote to stale flat folder |
| **Run full review** | Same path/context issues; subprocess hid errors behind empty `LAYER1_DIR` |
| **Show review tables** | Looked in `outputs/pre_jvcpca_review/session_window` while review/export used other paths |

## 2. Root causes

1. **Output path drift** — review used flat `session_window`; export used `<participant>/<session>/<window_label>`.
2. **Missing session gating** — no check for `CURRENT_ROW` / matched L1+L2 dirs before review.
3. **Schema drift** — review tables lacked canonical identity + Stage 08 flag summaries required by updated Layer 2.5 contract.
4. **DataDescriptions opacity** — only boolean `datadescriptions_used`; no path/mode/warnings.
5. **Empty default joint selection** when pilot manifest did not resolve for a session.

## 3. Files changed

| File | Change |
|------|--------|
| `src/pre_jvcpca_review/review_output.py` | **New** — review out-dir helpers, context validation, DD meta |
| `src/pre_jvcpca_review/review_display.py` | **New** — shared Show review tables renderer |
| `src/pre_jvcpca_review/build.py` | Extended rotvec columns, DD meta, `window_warnings.csv` |
| `src/pre_jvcpca_review/tables.py` | Canonical + Stage 08 columns; enriched decision summary |
| `src/pre_jvcpca_review/schemas.py` | Updated column contracts |
| `src/pre_jvcpca_review/layer2_flags.py` | `stage08_review_stats()` |
| `notebooks/pre_jvcpca_review.ipynb` | Review actions wired to structured paths + direct API |
| `outputs/pre_jvcpca_review/review_table_repair_diagnostic.md` | Diagnostic report |
| `tests/test_review_table_repair.py` | **New** regression tests |

## 4. Notebook cells changed

Single code cell (`cell 1`):

- Review root default → `outputs/pre_jvcpca_review`
- Added `_review_out_dir()`, `_require_review_context()`, `_dd_path()`
- **Run mapping / Run full review** call `build_mapping_only` / `build_full_review` directly
- **Show review tables** calls `display_review_tables(_review_out_dir())`
- Export uses same `_review_out_dir()` as review (shared window folder)
- Default joint selection falls back to first 3 `core_candidate` links

## 5. New / updated functions

- `resolve_review_out_dir`, `require_review_context`, `datadescriptions_meta`, `infer_mapping_mode`
- `display_review_tables`, `review_table_status`
- `stage08_review_stats`
- `_collect_review_warnings` (build)

## 6. Output paths

```
outputs/pre_jvcpca_review/
  session_index.csv
  <participant_id>/
    joint_overlap_table.csv
    <session_id>/
      <window_label>/
        mapping_logic_table.csv
        window_decision_summary.csv
        qc_evidence_summary_table.csv
        link_joint_review_table.csv
        qc_event_review_table.csv
        window_warnings.csv
        (Layer 3 export files when exported to same window folder)
```

Deterministic overwrite per window label (same convention as export).

## 7. New / updated tests

`tests/test_review_table_repair.py` — 11 tests covering mapping, full review, canonical columns, L1 evidence-only, Stage 08 flags, DataDescriptions status, missing-table warnings, L3 export policy.

## 8. Tests run

```
pytest tests/test_pre_jvcpca_review.py tests/test_review_table_repair.py tests/test_notebook_ui.py
→ 26 passed, 1 skipped (L3 export blocked on fixture warnings — gate still active)
```

Integration on discovered session `671_T1_P1_R1` succeeds with real Layer 1 / Layer 2 roots.

## 9. Layer 3 export unchanged

- `export_layer3_window` not modified
- Canonical naming policy `parent_canonical_to_child_canonical_axis` preserved
- Existing export tests still pass

## 10. Remaining limitations

- Review tables do not yet write `window_joint_frame_flag_log.csv` or `window_jvcpca_matrix_summary.md` (export-only artifacts).
- `mapping_logic_table.csv` does not yet include per-row `parent_canonical` columns (link tables do).
- DataDescriptions path is still manual (default fixture path); auto-discovery from session folder not implemented.
- Pilot manifest default joint pre-selection may differ from user's checkbox scope.
