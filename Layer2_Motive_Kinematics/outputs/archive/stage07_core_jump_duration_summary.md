# Stage 07 core jump duration and clustering summary

Read-only analysis of existing Stage 07 compact parquet outputs. No Stage 07 logic, schema, or policies were modified.

## Method notes

- **Per-frame fail/warning counts and clusters** use `stage07_row_qc_status` (frame-level diagnostic).
- **`stage07_jump_status_*_row_count`** counts rows where the link-propagated `stage07_jump_status` equals fail/warning; on a failing link this equals `total_frames` because the link-level status is replicated on every row.
- **Clusters** are contiguous frame sequences (frame increments of 1).
- **Classification:** `single_transition` = 1 frame; `short_cluster` = 2–10 frames; `sustained_segment` > 10 frames.

## Direct answers

### 1. Are core jump failures isolated or sustained?

**Isolated single-transition events.** All `block_filter` core links show only `single_transition` clusters (1 frame each) at the frame of maximum frame-to-frame jump. T3 R1 `J031` additionally has a separate isolated warning transition at frame 18914 (0.906 rad) before the fail at frame 26397 (1.74 rad). No sustained multi-frame segments were found.

### 2. T1 R1 J007 — fail and warning rows

- Per-frame fail rows (`stage07_row_qc_status`): **1**
- Per-frame warning rows: **0**
- Link-propagated `stage07_jump_status=fail` row count: **30604** (equals total frames because link jump status is fail)

### 3. T3 R1 J004 / J006 / J031 — fail and warning rows

- **J004:** per-frame fail=1, warning=0, link-propagated jump_status=fail rows=31674
- **J006:** per-frame fail=1, warning=0, link-propagated jump_status=fail rows=31674
- **J031:** per-frame fail=1, warning=1, link-propagated jump_status=fail rows=31674

### 4. Longest fail-only cluster

- **671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001** `J007` LFArm→LHand: 1 frame(s), classification=`single_transition`, frames 16334–16334, max jump 1.474 rad

### 5. Longest warning-or-fail cluster

- **671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001** `J005` LUArm→LFArm: 1 frame(s), classification=`single_transition`, frames 16611–16611, max jump 0.6736 rad

### 6. Are Stage 08 block policies driven by isolated jumps or longer segments?

**Isolated jumps (with one link having two isolated events).** Every core link with `stage08_policy=block_filter` failed because of single frame-to-frame transitions exceeding the 1.0 rad fail threshold. T3 R1 `J031` has two isolated transitions (warning then fail) at different frames. Link-level `stage07_jump_status=fail` reflects the max jump across the recording.

### 7. Implications for manual review, masking, exclusion, or threshold review

- **Manual/video review:** Supported at the identified single frames (see cluster table). Inspect Motive export around those timestamps for forearm→hand tracking glitches.
- **Masking:** A 1-frame mask at each jump frame is sufficient; no long contaminated spans.
- **Link exclusion:** Not warranted for core body links based on duration alone; failures are sparse isolated events on otherwise clean sequences.
- **Threshold review:** Optional for warning-only links (0.5–1.0 rad single transitions); block_filter links exceed 1.0 rad and would fail under current thresholds regardless.

## Block-filter core links

- `671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001` **J007** LFArm→LHand: per-frame fail=1, warning=0, max jump 1.474 rad @ frame 16334
- `671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000` **J004** LUArm→LFArm: per-frame fail=1, warning=0, max jump 1.333 rad @ frame 18914
- `671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000` **J006** LFArm→LHand: per-frame fail=1, warning=0, max jump 1.45 rad @ frame 18914
- `671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000` **J031** RFArm→RHand: per-frame fail=1, warning=1, max jump 1.74 rad @ frame 26397

## All analyzed core links with warning/fail activity

- `671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001` **J005** (allow_filter_with_warning): fail=0, warn=1, clusters fail/wf=0/1
- `671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001` **J007** (block_filter): fail=1, warn=0, clusters fail/wf=1/1
- `671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001` **J029** (allow_filter_with_warning): fail=0, warn=1, clusters fail/wf=0/1
- `671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005` **J029** (allow_filter_with_warning): fail=0, warn=1, clusters fail/wf=0/1
- `671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005` **J031** (allow_filter_with_warning): fail=0, warn=1, clusters fail/wf=0/1
- `671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000` **J004** (block_filter): fail=1, warn=0, clusters fail/wf=1/1
- `671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000` **J006** (block_filter): fail=1, warn=0, clusters fail/wf=1/1
- `671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000` **J031** (block_filter): fail=1, warn=1, clusters fail/wf=1/2
- `671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005` **J006** (allow_filter_with_warning): fail=0, warn=1, clusters fail/wf=0/1
