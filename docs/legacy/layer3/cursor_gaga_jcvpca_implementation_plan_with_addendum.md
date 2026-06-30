# Cursor Implementation Plan — Gaga JcvPCA Stepwise Analysis Workbench

## 0. Mission

Build a step-by-step, UI-visible implementation of the Gaga JcvPCA workflow on top of the existing `Layer3_JcvPCA` package and the upstream `Layer2.5_Segmentation` outputs.

This is **not** a black-box "Run Analysis" feature. It is an **Analysis Workbench** where every data decision, parameter choice, computational step, intermediate output, warning, and result is visible to the user and can be inspected before continuing.

Cursor is allowed to inspect and modify both:

```text
Layer2.5_Segmentation
Layer3_JcvPCA
```

However, every phase of implementation must end with a UI-visible checkpoint that the user can test visually before moving to the next phase.

---

## 1. Non-Negotiable Product Principles

### 1.1 No hidden decisions

Any unresolved methodological, data, or parameter decision must be surfaced in the UI.

Do not silently choose:

```text
analysis type
participants
timepoints
repetitions
P1/P2/P3/P4/P5 exercises
joint/link subset
PC variance threshold
selected_m override
functional vs null-space PC focus
p / estimated task DoF
explained-variance weighting
NV baseline mode
NV random split count
SE denominator
summary aggregation method
```

Every such choice must be shown, editable where appropriate, and saved in the run manifest.

### 1.2 Every phase must include UI

Do not implement backend-only changes unless the same phase also adds or updates a UI section that lets the user inspect the result.

Each phase must include:

```text
1. Backend/data change
2. Validation logic
3. UI representation
4. User decision point, if applicable
5. Visual testing checklist
6. Output artifacts
7. Acceptance criteria
```

### 1.3 Step-by-step execution, not one black box

The final user experience must support:

```text
Run Step
Inspect Output
Stop Here
Go Back / Change Parameters
Re-run Step
Continue to Next Step
```

Every computational step must write its intermediate outputs into the analysis output folder.

### 1.4 The code does not generate scientific conclusions

The system must display numeric values, tables, diagnostics, and neutral descriptions only.

Forbidden language in UI, reports, and generated summaries:

```text
statistically significant
proves change
scientifically meaningful
clinically meaningful
causal motor change
strategy changed significantly
dancer explored more
improved creativity
```

Allowed language:

```text
numeric increase in B relative to A
numeric decrease in B relative to A
inside descriptive NV interval
outside descriptive NV interval
selected PC range
selected links
excluded links and reasons
raw JcvPCA value
weighted JcvPCA value
```

### 1.5 Keep the existing JcvPCA core protected

The existing `core.compute_jcvpca()` should be treated as the protected computational kernel.

Cursor should not rewrite the sequence unless it finds and documents a specific methodological mismatch.

Preferred approach:

```text
Add a transparent / traceable / stepwise execution path that exposes intermediate states.
Keep the existing public compute_jcvpca() behavior intact.
Add tests proving the stepwise path produces the same final values as the existing core.
```

If refactoring is needed, refactor into shared helper functions while preserving all existing tests and public behavior.

---

## 2. Existing Architecture Assumptions

Cursor must first inspect the repository and verify these assumptions against the actual code.

Current known structure:

```text
Layer 1  -> raw QC, gaps, artifacts
Layer 2  -> quaternions, filtering, kinematics
Layer 2.5 -> segmentation, window selection, JcvPCA-ready matrix export
Layer 3  -> JcvPCA comparison on exported matrices
```

Layer 3 currently consumes Layer 2.5 exported matrices such as:

```text
window_jvcpca_matrix.parquet
window_jvcpca_matrix.csv
```

Expected Layer 3 matrix contract:

```text
Required metadata columns:
- session_id
- run_label
- frame
- time_sec

Required feature columns:
- <link_name>_rx
- <link_name>_ry
- <link_name>_rz
```

Metadata columns must never enter PCA.

Feature triplets must be complete and comparable across all selected matrices.

---

## 3. Target User Workflow

The user should be able to work through the following UI flow:

```text
0. Inspect Layer 2.5 data inventory
1. Select analysis setup
2. Load selected matrices
3. Detect comparable links/joints
4. Select exercises P1-P5 dynamically
5. Build Dataset A / Dataset B preview
6. Align features
7. Preview raw data
8. Center data independently
9. Run PCA on Dataset A
10. Choose PC focus: functional, null-space, all, or manual
11. Project Dataset B into A PCA space
12. Run PCA on projected B
13. Re-express B loadings in original feature space
14. Calculate axis-level JcvPCA
15. Aggregate rx/ry/rz to link-level using RSS
16. Apply optional explained-variance weighting
17. Run Longitudinal descriptive NV baseline, if selected
18. Run Exploratory numeric summary, if selected
19. Review all results
20. Export reproducibility package
```

Every step must be stoppable and inspectable.

---

## 4. Canonical Data Model

The base data units are not fixed blocks. They are individual exercises:

```text
P1
P2
P3
P4
P5
```

The user chooses which exercises to combine during analysis.

Supported presets may exist, but they must not be hard-coded as the only option:

```text
Preset: P1 + P2
Preset: P3 + P4 + P5
Preset: P1 + P2 + P3 + P4 + P5
Custom: any subset of P1-P5
```

The target manifest / inventory should support at least:

```csv
participant_id,timepoint,repetition,exercise,matrix_path,session_id,run_label,layer3_safe,qc_status,n_frames,n_features,feature_set_id,source_window_id,exported_at,notes
```

Minimum expected values:

```text
participant_id: participant identifier, e.g. P001
timepoint: T1 / T2 / T3
repetition: r1 / r2
exercise: P1 / P2 / P3 / P4 / P5
matrix_path: path to Layer 2.5 JcvPCA-ready matrix
layer3_safe: true / false / unknown
qc_status: pass / warning / blocking / unknown
```

Cursor must not invent missing metadata silently.

If metadata is missing, Cursor must surface a Layer 2.5 adaptation requirement.

---

## 5. Required User-Controlled Parameters

The UI must expose these parameters.

### 5.1 Analysis setup

```text
analysis_id
participant(s)
analysis_type:
  - Longitudinal Strategy Shift
  - Exploratory Behavior
timepoint selection:
  - T1
  - T2
  - T3
repetition selection:
  - r1
  - r2
exercise selection:
  - P1
  - P2
  - P3
  - P4
  - P5
exercise preset:
  - P1+P2
  - P3+P4+P5
  - All P
  - Custom
```

### 5.2 Link/joint selection

```text
link selection mode:
  - all comparable links
  - manual subset
```

Only complete and comparable links may be selectable.

### 5.3 PCA parameters

```text
variance_threshold:
  default for Gaga workflow: 0.80
  editable by user

min_pcs:
  default: preserve existing project default unless repo says otherwise

max_pcs:
  default: preserve existing project default unless repo says otherwise

selected_m mode:
  - auto from Dataset A cumulative explained variance
  - manual override
```

The UI must show why `selected_m` was chosen.

### 5.4 PC focus parameters

The paper distinguishes between focusing on the first PCs for functional task structure and the later PCs for redundant / null-space dimensions.

Expose:

```text
PC focus:
  - Functional PCs: first p PCs
  - Null-space PCs: PCs p+1 through selected_m
  - All selected PCs: PC1 through PC selected_m
  - Manual PC selection

p / estimated task DoF:
  user-defined integer
  optional, but required for Functional or Null-space presets
```

The code must not infer `p` silently.

If `p` is not provided, default to:

```text
PC focus = All selected PCs
```

### 5.5 Weighting parameters

```text
explained_variance_weighting:
  - off
  - on
```

When feasible, always preserve both unweighted and weighted outputs, even if the UI default view shows only one.

### 5.6 Natural variability parameters

Only relevant for Longitudinal analysis.

```text
use_nv_baseline:
  - yes
  - no

nv_mode:
  - intra-subject r1 vs r2
  - inter-subject random split
  - both

random_split_count:
  default: 15
  editable

random_seed:
  optional, editable, saved

SE denominator:
  - number of subjects
  - number of comparisons
```

The UI must label this as a descriptive baseline, not a statistical test.

### 5.7 Summary parameters

The primary output must always be:

```text
link x PC table
axis x PC table
```

If a collapsed summary is offered, it must be user-controlled:

```text
summary method:
  - no collapse, show per-PC only
  - signed sum across included PCs
  - mean signed delta across included PCs
  - sum absolute delta across included PCs
  - mean absolute delta across included PCs
  - explained-variance weighted signed sum
```

Do not present collapsed summaries as scientific conclusions.

---

## 6. Sign Convention and RSS Convention

### 6.1 Axis-level sign convention

Use the existing project convention:

```text
JcvPCA_axis = |B_reexpressed_loading| - |A_loading|
```

Interpretation label:

```text
positive = numeric contribution increased in B relative to A
negative = numeric contribution decreased in B relative to A
```

### 6.2 Link-level RSS convention

Each link is represented by a complete triplet:

```text
<link>_rx
<link>_ry
<link>_rz
```

The PCA input matrix includes all selected axes as independent features.

After:

```text
PCA on A
projection of B into A PCA space
PCA on projected B
re-expression of B loadings in original feature space
```

compute link-level JRW separately for A and B:

```text
JRW_A_link_pc = sqrt(A_rx_pc^2 + A_ry_pc^2 + A_rz_pc^2)
JRW_B_link_pc = sqrt(B_rx_pc^2 + B_ry_pc^2 + B_rz_pc^2)
```

Then compute link-level delta:

```text
JcvPCA_link_pc = JRW_B_link_pc - JRW_A_link_pc
```

Do **not** use this as the primary metric:

```text
sqrt((B_rx - A_rx)^2 + (B_ry - A_ry)^2 + (B_rz - A_rz)^2)
```

That removes sign and changes the meaning.

The UI must show both:

```text
axis-level values before RSS
link-level RSS aggregation after RSS
```

---

## 7. Output Folder and Reproducibility Contract

Every analysis run must create an output folder such as:

```text
Layer3_JcvPCA/outputs/<analysis_id>/
```

The workbench must write intermediate artifacts after each step.

Required or recommended artifacts:

```text
run_manifest.json
user_selections.json
layer25_data_inventory.csv
layer25_data_inventory_issues.csv
matrix_loading_report.csv
comparable_links.csv
excluded_links.csv
dataset_construction_plan.json
dataset_A_sources.csv
dataset_B_sources.csv
feature_alignment_report.csv
raw_preview_A.csv
raw_preview_B.csv
centering_values_A.csv
centering_values_B.csv
centered_preview_A.csv
centered_preview_B.csv
centered_validation_report.csv
pca_A_explained_variance.csv
pca_A_loadings.csv
pc_focus_selection.json
pc_focus_table.csv
B_projected_preview.csv
pca_B_projected_explained_variance.csv
pca_B_projected_loadings.csv
B_reexpressed_loadings.csv
axis_level_jcvpca_unweighted.csv
link_level_jrw_rss.csv
link_level_jcvpca_unweighted.csv
axis_level_jcvpca_weighted.csv, if enabled
link_level_jcvpca_weighted.csv, if enabled
nv_runs_manifest.csv, if enabled
nv_baseline.csv, if enabled
exploratory_summary.csv, if enabled
analysis_summary.md
plots/
```

The run manifest must include:

```text
all user selections
all parameter values
input file paths
feature/link inclusion and exclusion
step status for every step
warnings and acknowledgments
code version if available
random seed if used
outputs written by each step
```

---

# Implementation Roadmap

## Phase 0 — Repository Orientation and Guardrails

### Goal

Inspect the actual repository before implementing. Confirm current file paths, modules, UI entry points, and tests.

### Backend tasks

1. Locate the current Layer 3 package.
2. Locate the current Layer 2.5 dashboard and export logic.
3. Identify the existing Streamlit page for Layer 3.
4. Identify existing modules:

```text
core.py
aggregation.py
validation.py
io.py
runner.py
preflight.py
matrix_stability.py
analysis_service.py
app_controller.py
nv_compare.py
distribution.py
reporting.py
viz.py
```

5. Run existing tests before changes.
6. Record current passing/failing status.

### UI tasks

Add or update a temporary / developer-only UI section:

```text
Implementation Status / Diagnostics
```

It should show:

```text
Layer 3 package import status
Layer 2.5 dashboard import status
known output folders found
existing tests command to run
current workbench feature availability
```

### Acceptance criteria

- Existing tests still run.
- Cursor has identified real files before modifying them.
- UI shows a diagnostics panel instead of relying only on logs.

### Visual test

Open the dashboard and confirm that the diagnostics panel shows detected Layer 2.5 and Layer 3 paths.

---

## Phase 1 — Layer 2.5 Data Contract Discovery

### Goal

Before implementing Layer 3 workflow logic, discover what Layer 2.5 actually exports.

### Backend tasks

Create or extend a scanner that can inspect Layer 2.5 outputs.

Suggested functionality:

```text
scan_layer25_exports(root_dir) -> DataInventory
```

The scanner should detect:

```text
participant_id
timepoint
repetition
exercise
matrix_path
session_id
run_label
layer3_safe
qc_status
n_frames
n_columns
feature columns
metadata columns
available links
complete rx/ry/rz triplets
missing metadata
invalid files
```

If the repository already has relevant functions in `io.py` or Layer 2.5 export utilities, reuse or extend them.

### Data contract warnings

If required fields are missing, create structured warnings:

```text
missing_participant_id
missing_timepoint
missing_repetition
missing_exercise
missing_matrix_path
missing_layer3_safe
missing_qc_status
missing_required_metadata_columns
missing_feature_triplets
inconsistent_feature_naming
```

Do not silently infer or invent missing fields unless the UI clearly labels them as inferred and asks the user to confirm. Prefer upstream Layer 2.5 adaptation.

### UI tasks

Add a UI section:

```text
Layer 2.5 Data Inventory
```

Display:

```text
participants found
timepoints found
repetitions found
exercises P1-P5 found
matrix paths
QC status
layer3_safe status
n_frames per matrix
n_features per matrix
missing data / issues
```

The user must be able to filter by:

```text
participant
timepoint
repetition
exercise
QC status
layer3_safe
```

### Output artifacts

```text
layer25_data_inventory.csv
layer25_data_inventory.json
layer25_data_inventory_issues.csv
```

### Acceptance criteria

- The UI shows all discovered P1-P5 units for the available participants.
- Missing metadata is shown as a warning or blocking issue.
- The user can visually confirm whether the data exists for each participant / T / r / P.

### Visual test

Use the two-participant sample data. Confirm that the grid shows each participant's available P1-P5 exercises and highlights missing files or metadata.

---

## Phase 2 — Layer 2.5 Adaptation, If Needed

### Goal

If Layer 2.5 does not export enough metadata for the desired workflow, Cursor is authorized to modify Layer 2.5.

### Backend tasks

If missing, add a Layer 2.5 export manifest or inventory writer.

Target manifest fields:

```csv
participant_id,timepoint,repetition,exercise,matrix_path,session_id,run_label,layer3_safe,qc_status,n_frames,n_features,feature_set_id,source_window_id,exported_at,notes
```

Ensure exported matrices preserve:

```text
session_id
run_label
frame
time_sec
<link>_rx
<link>_ry
<link>_rz
```

Ensure no metadata columns are mixed into PCA features.

Ensure all feature names are canonical and stable.

### UI tasks

Add a UI section:

```text
Layer 2.5 Export Readiness
```

Display:

```text
required fields
present / missing status
export readiness per matrix
which Layer 2.5 adaptations were applied
which issues still block Layer 3
```

### Output artifacts

```text
layer25_export_readiness_report.csv
layer25_export_manifest.csv
```

### Acceptance criteria

- If Layer 2.5 was incomplete, the UI shows exactly what was fixed.
- Layer 3 can read a manifest without manual path entry.
- No required metadata is silently guessed.

### Visual test

Regenerate or rescan Layer 2.5 outputs and confirm the manifest contains participant / T / r / P / matrix path for each available unit.

---

## Phase 3 — Comparable Link / Joint Detection

### Goal

Identify which links are actually comparable across the user's selected data.

### Backend tasks

Implement or extend a function:

```text
detect_comparable_links(selected_matrices) -> ComparableLinksReport
```

For each selected matrix:

1. Identify feature columns ending in `_rx`, `_ry`, `_rz`.
2. Infer link stem by removing the axis suffix.
3. Check complete triplet per link.
4. Check numeric type.
5. Check NaN / inf.
6. Check zero variance.
7. Check presence across all selected matrices.
8. Produce final comparable link set.

Rules:

```text
Only complete rx/ry/rz triplets are eligible.
Only links present in all required datasets are eligible.
No imputation.
No silent repair.
```

### UI tasks

Add a UI panel:

```text
Comparable Links / Joints
```

Display a table:

```text
Link
A status
B status
NV_A status, if relevant
NV_B status, if relevant
Triplet complete?
Numeric?
NaN/inf?
Zero variance?
Comparable?
Exclusion reason
```

Provide controls:

```text
Use all comparable links
Manually select comparable links
Show excluded links
Show feature columns per link
```

### Output artifacts

```text
comparable_links.csv
excluded_links.csv
feature_triplet_report.csv
```

### Acceptance criteria

- User can see which links can be compared before running PCA.
- Incomplete triplets are excluded and explained.
- UI prevents selecting non-comparable links.

### Visual test

Use data where at least one link is missing or incomplete. Confirm the UI excludes it and explains why.

---

## Phase 4 — Exercise Selection and Dataset Construction Preview

### Goal

Allow the user to choose any subset of P1-P5 and preview exactly how Dataset A and Dataset B will be built.

### Backend tasks

Create or extend:

```text
DatasetConstructionPlan
build_dataset_from_plan(plan) -> DatasetBundle
```

The plan should represent:

```text
analysis type
participant(s)
timepoints
repetitions
selected exercises
selected links
source matrices
row-wise concatenation order
feature columns retained
metadata columns excluded from PCA
```

Do not hard-code block definitions as the only options. Presets are allowed but must be editable.

### Longitudinal construction

Example:

```text
Dataset A = T1 r1 + T1 r2 for selected P exercises
Dataset B = T2 r1 + T2 r2 for selected P exercises
```

or:

```text
Dataset B = T3 r1 + T3 r2 for selected P exercises
```

The user should choose the target comparison.

### Exploratory construction

Example:

```text
Dataset A = T1 r1 for selected P exercises
Dataset B = T1 r2 for selected P exercises
```

Repeatable for T1, T2, T3.

### UI tasks

Add a panel:

```text
Dataset Construction Preview
```

Display:

```text
selected exercises
selected source files for A
selected source files for B
row-wise concatenation order
rows per source file
total rows in A
total rows in B
selected links
selected feature columns
metadata columns excluded
```

Provide buttons:

```text
Build Preview
Save Construction Plan
Continue
Back to Exercise Selection
```

### Output artifacts

```text
dataset_construction_plan.json
dataset_A_sources.csv
dataset_B_sources.csv
dataset_construction_preview.csv
```

### Acceptance criteria

- User can visually inspect exactly which P exercises are included.
- A/B source files are explicit.
- Concatenation order is explicit.
- No PCA is run yet.

### Visual test

Select P1+P2, then select P3+P4+P5, then select a custom combination. Confirm the preview updates each time.

---

## Phase 5 — Feature Alignment and Preflight Integration

### Goal

Before any computation, guarantee A and B have identical selected features in identical order.

### Backend tasks

Reuse existing validation/preflight logic where possible.

Checks:

```text
required metadata columns exist
feature columns numeric
no NaN
no inf
no zero-variance features
identical feature names
identical feature order
complete rx/ry/rz triplets
minimum rows for PCA
layer3_safe not false
QC status not blocking
rank > 0
matrix stability warnings
```

If feature mismatch occurs, the run must be blocking.

### UI tasks

Add a panel:

```text
Feature Alignment & Preflight
```

Display:

```text
A feature order
B feature order
matched / mismatched status
final selected feature list
blocking issues
warnings
matrix stability metrics
acknowledgment checkbox for warnings
```

### Output artifacts

```text
feature_alignment_report.csv
preflight_report.csv
matrix_stability_report.csv
```

### Acceptance criteria

- Blocking issues prevent continuation.
- Warnings require explicit acknowledgment.
- User can see feature order before PCA.

### Visual test

Run with matching data and verify pass/warning. Run with mismatched feature order and verify blocking.

---

## Phase 6 — Analysis Workbench Step Runner

### Goal

Create the stateful step-by-step execution shell used by all downstream computation.

### Backend tasks

Implement a workbench state model.

Suggested concepts:

```text
AnalysisRun
AnalysisStep
StepStatus
StepArtifact
StepParameterSet
```

Step statuses:

```text
not_started
ready
running
completed
warning
blocking
invalidated
```

Rules:

```text
Changing upstream parameters invalidates downstream steps.
Completed steps write artifacts.
The user can stop after any completed step.
The user can go back, change parameters, and re-run.
The run manifest tracks all changes.
```

### UI tasks

Create an Analysis Workbench / Step Runner UI.

Each step card should show:

```text
step name
short explanation
input parameters
Run Step button
status
outputs generated
preview tables/plots
Continue button
Back button
```

### Output artifacts

```text
run_manifest.json
step_status.json
user_selections.json
```

### Acceptance criteria

- User can execute one step at a time.
- User can stop after a step and inspect outputs.
- Changing an upstream selection invalidates later outputs.
- The UI does not force a full analysis run.

### Visual test

Run through matrix loading, stop, reload the page if possible, and confirm the completed step state persists.

---

# Detailed Workbench Computational Steps

The following steps must be implemented inside the Analysis Workbench.

---

## Step 0 — Layer 2.5 Data Discovery

### Purpose

Show what data exists before any analysis setup.

### UI output

```text
participants
timepoints
repetitions
P1-P5 availability
matrix paths
QC status
layer3_safe
issues
```

### User decision

Choose whether to continue, rescan, or fix Layer 2.5 exports.

### Artifacts

```text
layer25_data_inventory.csv
layer25_data_inventory_issues.csv
```

---

## Step 1 — Analysis Setup

### Purpose

Collect user choices for the analysis run.

### UI parameters

```text
analysis_id
analysis_type
participant(s)
timepoints
repetitions
exercise preset or custom exercise list
notes
```

### UI output

A plain-language setup summary.

### Artifacts

```text
user_selections.json
```

---

## Step 2 — Matrix Loading Preview

### Purpose

Load selected matrix files and show structure before any transformation.

### UI output per matrix

```text
path
rows
columns
metadata columns
feature columns
first rows preview
missing values
inf values
zero variance columns
```

### User decision

Continue or return to selection.

### Artifacts

```text
matrix_loading_report.csv
raw_preview_by_matrix/
```

---

## Step 3 — Feature / Joint Detection

### Purpose

Detect available and comparable links.

### UI output

```text
detected links
available axes per link
complete links
incomplete links
links missing in A/B/NV
excluded links and reasons
```

### User decision

```text
Use all comparable links
Manually select subset
```

### Artifacts

```text
comparable_links.csv
excluded_links.csv
selected_links.json
```

---

## Step 4 — Dataset Construction

### Purpose

Construct Dataset A and Dataset B from selected P exercises, timepoints, repetitions, and links.

### UI output

```text
Dataset A source files
Dataset B source files
row-wise concatenation order
rows before concatenation
rows after concatenation
selected links
selected feature columns
metadata removed from PCA
```

### User decision

Confirm construction plan or go back.

### Artifacts

```text
dataset_construction_plan.json
dataset_A_sources.csv
dataset_B_sources.csv
dataset_A_preview.csv
dataset_B_preview.csv
```

---

## Step 5 — Feature Alignment

### Purpose

Ensure A and B have the same feature columns in the same order.

### UI output

```text
feature order table
matched / mismatched status
final PCA feature list
blocking issues
```

### User decision

Continue only if pass/warning with acknowledgment.

### Artifacts

```text
feature_alignment_report.csv
```

---

## Step 6 — Raw Data Preview Before Centering

### Purpose

Show selected raw numeric matrices before centering.

### UI output

```text
Raw A matrix preview
Raw B matrix preview
per-feature mean
per-feature std for display only
min/max
variance
selected joint axis traces
motion energy timeline if available
```

Do not normalize or z-score.

### User decision

Confirm raw data view before centering.

### Artifacts

```text
raw_preview_A.csv
raw_preview_B.csv
raw_feature_stats_A.csv
raw_feature_stats_B.csv
```

---

## Step 7 — Independent Centering

### Purpose

Center A and B independently.

A is centered using A's own column means.
B is centered using B's own column means.

Do not center B using A's mean.
Do not z-score.
Do not variance-normalize.
Do not range-normalize.

### UI parameters

Centering mode should be shown as:

```text
Independent centering A and B separately — required
```

This should not be silently hidden.

### UI actions

```text
Calculate centers
Show centered data
Continue
```

### UI output

```text
center value per selected feature
center values grouped by link
A mean before centering
B mean before centering
A mean after centering, should be approximately 0
B mean after centering, should be approximately 0
before/after preview
before/after distribution
```

Example table:

```text
Link | Axis | A center | B center | A mean after | B mean after
```

### Artifacts

```text
centering_values_A.csv
centering_values_B.csv
centered_preview_A.csv
centered_preview_B.csv
centered_validation_report.csv
```

### Acceptance criteria

- User can see the exact center value for every selected feature.
- Means after centering are approximately zero.
- No scaling is applied.

---

## Step 8 — PCA on Dataset A

### Purpose

Fit PCA on centered Dataset A and create the reference frame.

### UI parameters

```text
variance_threshold, default 0.80 for Gaga workflow
min_pcs
max_pcs
selected_m mode: auto or manual override
```

### UI output

```text
explained variance per PC
cumulative explained variance
selected_m
reason selected_m was chosen
A PCA loading matrix shape
A loadings table
scree plot
cumulative variance plot
loading heatmap
```

### User decision

Approve selected_m or change threshold / override.

### Artifacts

```text
pca_A_explained_variance.csv
pca_A_cumulative_variance.csv
pca_A_loadings.csv
pca_A_metadata.json
plots/scree_plot_A.png
plots/cumulative_variance_A.png
plots/pca_A_loading_heatmap.png
```

### Acceptance criteria

- selected_m is derived only from Dataset A unless manually overridden.
- User can see why selected_m was selected.

---

## Step 9 — PC Analysis Focus Selection

### Purpose

Allow the user to choose which PCs are included in downstream JcvPCA summaries.

The PC focus is based on the phenomenon the user wants to characterize:

```text
Functional PCs: first p PCs
Null-space PCs: PCs p+1 through selected_m
All selected PCs: PC1 through selected_m
Manual PCs: user-selected PCs
```

### UI parameters

```text
PC focus
p / estimated task DoF
manual PC checkboxes
```

If Functional or Null-space focus is selected, `p` must be provided by the user.

The code must not infer `p` silently.

### UI output

```text
PC table with explained variance
cumulative variance
role: functional / null-space / manual / excluded
included yes/no
```

Example:

```text
PC | Explained variance | Cumulative variance | Role | Included
```

### User decision

Approve included PCs.

### Artifacts

```text
pc_focus_selection.json
pc_focus_table.csv
```

### Acceptance criteria

- User can select functional, null-space, all, or manual PCs.
- p is visible and saved.
- Included PCs are explicit.

---

## Step 10 — Project Dataset B Into A PCA Space

### Purpose

Project centered B into the PCA space defined by A.

Expected operation:

```text
B_projected = B_centered @ pca_A_frame.T
```

Use the existing project implementation as source of truth for exact matrix orientation.

Do not use `PCA_A.transform(B_raw)` because that would apply A's fitted mean to B.

### UI output

```text
B centered matrix dimensions
A PCA frame dimensions
B projected dimensions
sample rows of projected B
PC scores A vs projected B
PC1-PC2 trajectory
PC score heatmap
```

### Artifacts

```text
B_projected_preview.csv
B_projected_metadata.json
plots/pc_scores_A_vs_projected_B.png
plots/pc_score_heatmap_A_B.png
```

### Acceptance criteria

- Projection dimensions are shown.
- User can inspect projected B before the second PCA.

---

## Step 11 — PCA on Projected B

### Purpose

Run PCA on B after projection into A's PCA space.

### UI output

```text
B projected PCA explained variance
B projected PCA loading matrix shape
selected_m used
B projected loadings table
```

### Artifacts

```text
pca_B_projected_explained_variance.csv
pca_B_projected_loadings.csv
pca_B_projected_metadata.json
```

### Acceptance criteria

- Uses the same selected_m / included PC constraints as the approved workflow.
- User can inspect B PCA results before re-expression.

---

## Step 12 — Re-express B Loadings in Original Feature Space

### Purpose

Convert B projected PCA loadings back to original feature terms so they can be compared with A loadings.

Expected conceptual operation:

```text
B_reexpressed = pca_B_projected_frame @ pca_A_frame
```

Use the existing core implementation as the exact orientation source of truth.

### UI output

```text
A loading matrix shape
B projected loading matrix shape
B re-expressed loading matrix shape
feature names aligned
side-by-side A vs B re-expressed loadings
```

### Artifacts

```text
B_reexpressed_loadings.csv
A_vs_B_reexpressed_loadings_preview.csv
```

### Acceptance criteria

- Feature names remain aligned.
- User can inspect A and re-expressed B loadings side by side.

---

## Step 13 — Axis-Level JcvPCA Calculation

### Purpose

Calculate axis-level deltas for every selected feature and PC.

### Formula

```text
JcvPCA_axis_pc_feature = |B_reexpressed_pc_feature| - |A_loading_pc_feature|
```

### UI output

```text
A absolute loading
B absolute re-expressed loading
axis-level delta
sign convention
selected PC range
```

Required UI label:

```text
Positive value = numeric contribution increased in B relative to A.
Negative value = numeric contribution decreased in B relative to A.
No scientific conclusion is generated here.
```

### Artifacts

```text
axis_level_jrw_A_B.csv
axis_level_jcvpca_unweighted.csv
```

### Acceptance criteria

- User can inspect axis-level values before RSS aggregation.
- Sign convention is explicit.

---

## Step 14 — RSS Aggregation to Link-Level

### Purpose

Aggregate rx/ry/rz axis values into link-level JRW values using RSS.

### Formula

For every selected link and PC:

```text
JRW_A_link_pc = sqrt(A_rx_pc^2 + A_ry_pc^2 + A_rz_pc^2)
JRW_B_link_pc = sqrt(B_rx_pc^2 + B_ry_pc^2 + B_rz_pc^2)
JcvPCA_link_pc = JRW_B_link_pc - JRW_A_link_pc
```

Do not compute RSS over axis-level deltas as the primary metric.

### UI output

```text
rx contribution
ry contribution
rz contribution
JRW_A
JRW_B
Delta B-A
formula display
selected PC range
```

Example table:

```text
Link | PC | A_rx | A_ry | A_rz | JRW_A | B_rx | B_ry | B_rz | JRW_B | Delta B-A
```

### Artifacts

```text
link_level_jrw_rss.csv
link_level_jcvpca_unweighted.csv
plots/jrw_A_B_bar.png
plots/delta_jrw_bar.png
```

### Acceptance criteria

- User can see how axis-level values become link-level values.
- Sign is preserved through `JRW_B - JRW_A`.

---

## Step 15 — Optional Explained-Variance Weighting

### Purpose

Optionally multiply per-PC results by A explained variance.

### UI parameters

```text
Report results to explained variance:
  - Off
  - On
```

### UI output

```text
unweighted delta
A PC explained variance
weighted delta
```

### Artifacts

```text
axis_level_jcvpca_weighted.csv, if enabled
link_level_jcvpca_weighted.csv, if enabled
weighting_metadata.json
```

### Acceptance criteria

- Weighting is user-controlled.
- Unweighted outputs remain available.
- Weighted outputs are clearly labeled.

---

## Step 16 — Natural Variability Descriptive Baseline, Longitudinal Only

### Purpose

For Longitudinal mode, optionally compute a descriptive NV baseline from T1.

This is not a statistical conclusion engine.

### UI parameters

```text
use_nv_baseline
nv_mode:
  - intra-subject
  - inter-subject random split
  - both
random_split_count, default 15
random_seed
SE denominator:
  - number of subjects
  - number of comparisons
```

### Intra-subject NV

For each participant:

```text
Dataset A = T1 r1 for selected exercises and links
Dataset B = T1 r2 for selected exercises and links
Run the same stepwise JcvPCA computation
Save result
```

### Inter-subject NV

If implemented:

```text
Use T1 data only.
Preserve or clearly document subject/frame handling.
Randomly split baseline data according to selected mode.
Repeat random_split_count times.
Run JcvPCA for each split.
Save every run.
```

Cursor must expose the split logic in the UI. Do not hide whether the split is subject-level or frame-level.

### Threshold / interval output

```text
NV mean
NV SE
NV interval = [mean - SE, mean + SE]
main value
inside / outside descriptive interval
```

### UI language

Use:

```text
Inside descriptive NV interval
Outside descriptive NV interval
```

Do not use:

```text
significant
proof
scientific change
```

### Artifacts

```text
nv_runs_manifest.csv
nv_results_raw.csv
nv_baseline.csv
main_vs_nv_descriptive_comparison.csv
plots/delta_jrw_vs_nv.png
```

### Acceptance criteria

- NV is optional and clearly descriptive.
- User can inspect every NV run and its source data.
- Random split parameters are saved.

---

## Step 17 — Exploratory Numeric Summary, Exploratory Only

### Purpose

For Exploratory mode, compare r1 vs r2 within the same timepoint and selected exercises.

Example:

```text
T1: r1 vs r2
T2: r1 vs r2
T3: r1 vs r2
```

The system displays numeric results only.

### UI parameters

```text
timepoints to run:
  - T1
  - T2
  - T3
summary method:
  - no collapse, per-PC only
  - signed sum
  - mean signed delta
  - sum absolute delta
  - mean absolute delta
  - existing democracy/Gini metric, if already implemented
```

### UI output

```text
T1 r1 vs r2 result
T2 r1 vs r2 result
T3 r1 vs r2 result
raw per-link x PC values
optional numeric summary table
selected PC focus
weighted/unweighted state
```

Do not label higher values as creativity or improved exploration.

### Artifacts

```text
exploratory_runs_manifest.csv
exploratory_link_level_results.csv
exploratory_summary.csv
plots/jrw_democracy_curve.png, if available
```

### Acceptance criteria

- User can inspect r1 vs r2 results per timepoint.
- Summary is numeric and neutral.
- No group threshold is used unless explicitly selected and labeled descriptive.

---

## Step 18 — Results Review

### Purpose

Show everything that was done and all outputs in one review screen.

### UI output

```text
analysis_id
analysis type
participants
timepoints
repetitions
selected exercises
selected links
excluded links and reasons
feature alignment status
centering values
selected_m
variance threshold
PC focus
p value if used
included PCs
weighting on/off
NV settings if used
warnings and acknowledgments
axis-level results
link-level RSS results
weighted results if used
plots
export folder path
```

### Required notice

```text
This screen reports numeric JcvPCA outputs and descriptive comparisons only. It does not generate scientific or statistical conclusions.
```

### Artifacts

```text
analysis_summary.md
results_review.json
```

### Acceptance criteria

- User can answer: "What exactly was done to my data?"
- Every parameter and decision is visible.
- All output files are linked or listed.

---

## Step 19 — Export / Reproducibility Package

### Purpose

Export all data required to reproduce or audit the run.

### UI options

```text
Export all artifacts
Export selected tables
Export plots
Export run manifest
Export Markdown summary
```

### Required outputs

```text
run_manifest.json
user_selections.json
analysis_summary.md
all intermediate CSVs
plots/
```

### Acceptance criteria

- User can download or locate the full output package.
- The manifest is sufficient to reproduce the run.

---

# Suggested Code Organization

Cursor must inspect actual files before implementing, but the following module structure is recommended.

## Layer 2.5 additions, if needed

```text
Layer2.5_Segmentation/
  ...
  export_manifest.py or layer3_export_manifest.py
  dashboard components for export readiness
```

Responsibilities:

```text
write Layer 3-ready manifest
expose participant/timepoint/repetition/exercise metadata
preserve matrix paths
preserve layer3_safe and QC status
```

## Layer 3 additions

```text
Layer3_JcvPCA/src/layer3_jcvpca/
  data_contract.py
  inventory.py
  comparable_links.py
  dataset_builder.py
  workbench_state.py
  step_runner.py
  jcvpca_trace.py
  pc_focus.py
  workbench_reporting.py
```

### `data_contract.py`

Defines manifest schemas and validation objects.

### `inventory.py`

Scans Layer 2.5 outputs and builds data inventory.

### `comparable_links.py`

Detects link stems and rx/ry/rz completeness.

### `dataset_builder.py`

Builds A/B/NV datasets from manifest + user selections.

### `workbench_state.py`

Persists analysis run state, step statuses, and invalidation logic.

### `step_runner.py`

Runs one step at a time and writes artifacts.

### `jcvpca_trace.py`

Exposes intermediate JcvPCA computations.

Must match final outputs from `core.compute_jcvpca()`.

### `pc_focus.py`

Handles functional/null-space/all/manual PC inclusion logic.

### `workbench_reporting.py`

Writes intermediate outputs and final summary.

---

# UI Architecture Requirements

The existing Streamlit UI can be extended, or a new page can be added.

Recommended page:

```text
Layer 3 Gaga JcvPCA Workbench
```

Sections:

```text
1. Data Inventory
2. Analysis Setup
3. Comparable Links
4. Dataset Construction
5. Preflight
6. Step Runner
7. Results Review
8. Export
```

Each computational step should be a collapsible card or tab.

Each card must include:

```text
what this step does
parameters
Run Step button
status
output preview
artifact paths
Continue / Back controls
```

---

# Testing Requirements

## Preserve existing tests

Run existing tests before and after implementation:

```bash
cd Layer3_JcvPCA
pytest -q
```

Do not break existing core invariants:

```text
no z-scoring
independent centering
no PCA.transform(B_raw)
PC selection from A only
RSS aggregation, not simple sum
feature order enforcement
metadata excluded from PCA
```

## Add new tests

Add tests for:

```text
Layer 2.5 manifest discovery
missing metadata warnings
P1-P5 exercise selection
custom exercise selection
comparable link detection
incomplete rx/ry/rz triplet exclusion
dataset construction row-wise concatenation
feature alignment blocking
centering values and post-centering means
PCA A selected_m from A only
PC focus functional/null-space/all/manual
p required for functional/null-space
B projection uses independent B centering
trace final output matches core.compute_jcvpca
RSS formula JRW_B - JRW_A
weighting optional and labeled
NV descriptive interval calculation
step invalidation after upstream changes
run manifest completeness
```

## UI manual tests

Manual visual test checklist:

```text
1. Can I see all Layer 2.5 data units?
2. Can I identify missing P exercises?
3. Can I choose P1-P5 freely?
4. Can I see comparable and excluded links?
5. Can I build A/B and inspect source files?
6. Can I stop after raw preview?
7. Can I stop after centering and see center values?
8. Can I see selected_m and explained variance?
9. Can I choose functional/null-space/all/manual PCs?
10. Can I inspect B projection?
11. Can I inspect axis-level deltas?
12. Can I inspect RSS aggregation?
13. Can I toggle weighting?
14. Can I run Longitudinal with descriptive NV?
15. Can I run Exploratory r1 vs r2?
16. Can I export a complete reproducibility package?
```

---

# Development Order for Cursor

Implement in this order. Do not skip UI checkpoints.

```text
Phase 0: Repo orientation and diagnostics UI
Phase 1: Layer 2.5 data inventory scanner + UI
Phase 2: Layer 2.5 export manifest adaptation + UI, if needed
Phase 3: Comparable link detection + UI
Phase 4: Exercise selection + dataset construction preview UI
Phase 5: Feature alignment + preflight integration UI
Phase 6: Workbench step runner shell
Phase 7: Raw preview + centering step UI
Phase 8: PCA A + selected_m UI
Phase 9: PC focus selection UI
Phase 10: Projection + PCA B + re-expression UI
Phase 11: Axis-level JcvPCA + RSS aggregation UI
Phase 12: Weighting UI
Phase 13: Longitudinal descriptive NV UI
Phase 14: Exploratory numeric summary UI
Phase 15: Results review + export package
Phase 16: Tests, docs, and final acceptance checklist
```

At the end of each phase, Cursor must provide:

```text
files changed
what was implemented
how to run it
what the user should visually verify
known limitations
next phase recommendation
```

---

# Acceptance Criteria for the Whole Feature

The implementation is complete only when all of the following are true:

1. The UI can discover Layer 2.5 data inventory.
2. The UI shows participant / T / r / P availability.
3. The UI warns when Layer 2.5 data contract is incomplete.
4. Cursor has adapted Layer 2.5 if needed and allowed.
5. The user can select any subset of P1-P5.
6. The user can select comparable links only.
7. The UI shows excluded links and reasons.
8. Dataset A and Dataset B construction is previewed before computation.
9. Feature alignment is validated and visible.
10. Preflight warnings and blocking states are preserved.
11. The user can stop after every computational step.
12. Centering values are shown per feature/link-axis.
13. Post-centering means are shown and near zero.
14. PCA on A shows explained variance and selected_m.
15. The user can select functional, null-space, all, or manual PCs.
16. The user can define p; the code does not infer p silently.
17. B projection is shown before PCA on projected B.
18. Re-expressed B loadings are visible.
19. Axis-level JcvPCA values are visible.
20. RSS link-level aggregation is visible and uses `JRW_B - JRW_A`.
21. Weighting is optional and user-controlled.
22. Longitudinal NV is descriptive only.
23. Exploratory output is numeric only.
24. No UI/report text claims statistical or scientific conclusions.
25. All outputs and intermediate steps are saved in the run folder.
26. The run manifest captures all choices and parameters.
27. Existing Layer 3 tests pass.
28. New tests cover the workbench and data contract.

---

# Final Instruction to Cursor

Do not implement this as a single monolithic run.

Build it as a transparent, auditable, stepwise Gaga JcvPCA Analysis Workbench.

The user must always be able to answer:

```text
What data was used?
Which exercises were included?
Which links were comparable?
Which links were excluded and why?
What parameters were used?
What happened at each computation step?
What intermediate values were produced?
Where are the output files?
```

The system must show the data as it is, not produce scientific conclusions.
# Addendum -- Critical Methodological Safeguards

This addendum is a required supplement to the main Cursor implementation plan for the Gaga JcvPCA Analysis Workbench.

Its purpose is to prevent edge-case bugs, hidden methodological choices, and upstream data transformations that would make the Layer 3 output hard to audit.

These safeguards do not authorize the software to produce scientific conclusions. The system must continue to show transparent data, intermediate computations, warnings, and descriptive numeric outputs only.

Forbidden output language remains:

```text
statistically significant
proves change
clinically meaningful
scientifically valid threshold
dancer improved
dancer became more creative
```

Allowed output language:

```text
numeric increase/decrease in B relative to A
descriptive Natural Variability baseline
descriptive interval
inside/outside descriptive interval
PCA-readiness warning
computed with selected PC range
computed with selected split settings
```

Every safeguard below must end with a visible UI checkpoint and saved run artifacts.

---

## Safeguard A -- Iterative Random Splitting for Natural Variability

### Applies to

- Phase: Longitudinal workflow
- Workbench step: Natural Variability descriptive baseline
- Related UI step: Step 16 / NV settings and output review

### Requirement

Inter-subject Natural Variability must not be implemented as a single random split.

If the user enables inter-subject random-split NV, the system must implement an iterative loop that runs the same JcvPCA comparison multiple times across repeated random splits of the selected T1 baseline data.

Default number of iterations:

```text
random_split_count = 15
```

This value must be editable in the UI and saved in the run manifest.

### Rationale

A single random split gives one arbitrary comparison and does not expose the variability of the baseline comparison procedure. The workbench must produce a distribution of NV values so the user can inspect:

```text
all split results
mean
standard deviation
standard error
descriptive interval
```

Do not label this interval as statistical significance.

### Required UI controls

Add a Natural Variability settings panel with:

```text
Use Natural Variability baseline: yes / no
NV modes:
- intra-subject r1 vs r2
- inter-subject iterative random split
- both

Random split count:
- default: 15
- editable

Random seed:
- default generated
- editable for reproducibility

Split mode:
- subject-level split, when enough participants are available
- frame/row-level split, allowed with warning when participant count is low
- future option: repetition-level split, if supported by Layer 2.5 metadata

SE denominator:
- number of valid NV comparisons / iterations
- number of subjects
- manual override, advanced mode only
```

The UI must clearly show which SE denominator is selected and the exact formula used.

### Required algorithm

For inter-subject iterative random-split NV:

```text
1. Use T1 baseline data only.
2. Use the currently selected exercises P1-P5.
3. Use only the currently selected comparable links/features.
4. Build the eligible baseline data pool.
5. For each iteration i in 1..random_split_count:
   a. Randomly split the eligible baseline pool according to split_mode.
   b. Build NV_A_i and NV_B_i.
   c. Run the same JcvPCA computation path used by the main analysis.
   d. Save axis-level, link-level, selected_m, PC focus, and warning metadata for that split.
6. Aggregate valid split results.
7. Compute NV mean, SD, SE, and descriptive interval.
8. Display and export all intermediate and aggregate results.
```

Important: each split must be auditable. Do not only save the final mean and SE.

### Required warnings

Display warnings when:

```text
participant count is too low for subject-level splits
frame/row-level splits are used on time-series data
random_split_count is less than 15
any split has rows_to_features_ratio below the PCA-readiness warning threshold
any split fails preflight
split membership is unknown or not reproducible
```

Frame/row-level splitting may be allowed as a development or low-n descriptive mode, but the UI must warn that adjacent frames are time-series observations and should not be treated as fully independent subjects.

### Required outputs

Save these artifacts:

```text
nv_settings.json
nv_split_membership.csv
nv_split_results_axis.csv
nv_split_results_link.csv
nv_split_selected_m.csv
nv_split_preflight_report.csv
nv_baseline_summary.csv
nv_descriptive_interval.csv
nv_split_distribution_plot.png
```

The run manifest must include:

```json
{
  "nv_enabled": true,
  "nv_modes": ["inter_subject_iterative_random_split"],
  "random_split_count": 15,
  "random_seed": "...",
  "split_mode": "...",
  "se_denominator_mode": "...",
  "valid_split_count": "...",
  "invalid_split_count": "..."
}
```

### UI checkpoint

At the end of this safeguard, the UI must show:

```text
NV run list
split mode
random seed
number of valid / invalid splits
per-split results table
NV mean table
NV SE table
NV interval table
main result vs descriptive interval table, if main analysis has already run
warnings and acknowledgments
```

### Acceptance criteria

- The developer cannot satisfy inter-subject NV with only one random split.
- The UI exposes random_split_count and random_seed.
- Every split result is saved and visible.
- The exported report avoids the words "significant" and "proof".
- A test confirms that setting random_split_count = 15 produces 15 attempted split records.
- A test confirms that a failed split is logged rather than silently ignored.

---

## Safeguard B -- PCA Rows-to-Features Adequacy Check

### Applies to

- Phase: Data construction and preflight
- Workbench steps:
  - Dataset construction
  - Feature alignment
  - PCA on Dataset A
  - Natural Variability split checks

### Requirement

Add a passive PCA-readiness check based on the rows-to-features ratio.

Because the PCA input uses 3 axes per selected link, the number of variables can increase quickly when the user selects many links or combines exercises.

Compute:

```text
n_selected_features = number_of_selected_links * 3
rows_to_features_ratio = n_rows / n_selected_features
```

Metadata columns must never be counted as PCA features.

### Required checks

Compute the ratio for:

```text
Dataset A
Dataset B
NV_A and NV_B, if used
every iterative NV split dataset, if used
```

Dataset A must be emphasized because A defines the PCA reference frame.

### Suggested warning bands

```text
ratio < 5:
  warning: low rows-to-features ratio; PCA may be unstable for this selected data scope

5 <= ratio <= 20:
  monitored: within commonly used minimum range, inspect stability metrics

ratio > 20:
  pass: strong sample support by this heuristic
```

This must be a warning by default, not a blocking error, unless the UI has a user-enabled strict mode.

### Required UI display

Add a PCA Sample Adequacy panel showing:

```text
dataset role
n_rows
n_selected_links
n_selected_features
rows_to_features_ratio
status: pass / monitored / warning
recommended user actions
```

Recommended user actions for low ratio:

```text
include more repetitions
include more P exercises
select fewer links
use a broader exercise preset
inspect rank, condition number, and explained variance before continuing
```

### Important language

Call this a:

```text
PCA sample adequacy heuristic
```

Do not call it a statistical validity guarantee.

### Required outputs

Save:

```text
pca_sample_adequacy_report.csv
pca_sample_adequacy_report.md
```

Add to run manifest:

```json
{
  "pca_sample_adequacy": {
    "A": {
      "n_rows": "...",
      "n_selected_features": "...",
      "rows_to_features_ratio": "...",
      "status": "..."
    }
  }
}
```

### UI checkpoint

At the end of this safeguard, the user must be able to visually verify:

```text
how many rows are entering PCA
how many axis features are entering PCA
whether the selected data scope is sparse relative to feature count
whether changing P selection or link selection improves the ratio
```

### Acceptance criteria

- Ratio is computed after user link selection, not on all raw available columns.
- Metadata columns are excluded from feature count.
- A low ratio produces a visible UI warning.
- The user can continue after acknowledgment unless strict mode is enabled.
- The ratio appears in the exported run manifest and report.
- Tests cover ratio < 5, ratio between 5 and 20, and ratio > 20.

---

## Safeguard C -- Explicit JcvPCA Sign Convention

### Applies to

- Workbench steps:
  - Axis-level JcvPCA calculation
  - RSS aggregation to link-level
  - Weighted/unweighted result display
  - Results review
  - Exported method notes

### Requirement

The project sign convention must be explicit in code, UI, tests, and exported reports.

The source material contains a sign inconsistency: the written equation uses A minus B, while the surrounding textual interpretation says a positive value indicates greater use in Dataset B. This project intentionally uses B minus A to preserve the textual interpretation.

### Project convention

```text
positive value = numeric contribution increased in B relative to A
negative value = numeric contribution decreased in B relative to A
```

### Required formulas

Axis level:

```text
JcvPCA_axis = abs(B_reexpressed_loading) - abs(A_loading)
```

Link level after RSS:

```text
JRW_A_link_pc = sqrt(A_rx_pc^2 + A_ry_pc^2 + A_rz_pc^2)
JRW_B_link_pc = sqrt(B_rx_pc^2 + B_ry_pc^2 + B_rz_pc^2)
JcvPCA_link_pc = JRW_B_link_pc - JRW_A_link_pc
```

Do not compute RSS over axis-level deltas as the primary link metric.

Wrong primary metric for this workflow:

```text
sqrt((B_rx - A_rx)^2 + (B_ry - A_ry)^2 + (B_rz - A_rz)^2)
```

That removes the sign and changes the interpretation.

### Required developer comments

Add a comment near the axis delta and link delta calculations:

```text
Project sign convention: B - A.
This intentionally preserves the textual interpretation that positive values mean increased numeric contribution in Dataset B relative to Dataset A.
Do not change to A - B without an approved method decision and UI/report migration.
```

### Required UI display

Every result table that shows deltas must include or link to a sign convention note:

```text
Sign convention: Delta = B - A.
Positive values indicate numerically larger contribution in B relative to A.
Negative values indicate numerically smaller contribution in B relative to A.
No scientific conclusion is generated by this sign.
```

### Required outputs

Save method notes in:

```text
analysis_summary.md
method_notes.md
run_manifest.json
axis_level_jcvpca.csv metadata/header if supported
link_level_jcvpca.csv metadata/header if supported
```

Add to manifest:

```json
{
  "jcvpca_sign_convention": "B_minus_A",
  "positive_delta_label": "numeric contribution increased in B relative to A",
  "negative_delta_label": "numeric contribution decreased in B relative to A"
}
```

### Required tests

Add tests proving:

```text
if B axis magnitude > A axis magnitude, axis delta is positive
if B link RSS > A link RSS, link delta is positive
changing sign would fail the test
RSS is computed on A and B separately before subtraction
RSS over deltas is not used as the primary metric
```

### UI checkpoint

At the end of this safeguard, the user must be able to see:

```text
axis-level abs(A), abs(B), Delta B-A
link-level JRW_A, JRW_B, Delta B-A
formula used
sign convention note
weighted and unweighted values, if weighting is enabled
```

### Acceptance criteria

- No result table leaves the sign ambiguous.
- Code comments prevent accidental reversal to A minus B.
- Unit tests lock the sign convention.
- Exported reports document the convention.
- The UI never turns sign into a scientific conclusion.

---

## Safeguard D -- No Time Normalization / No DTW in Layer 2.5 Exports

### Applies to

- Phase 0: Layer 2.5 data contract discovery
- Phase 1: Layer 2.5 adaptation, if required
- Workbench steps:
  - Data discovery
  - Matrix loading preview
  - Dataset construction
  - Preflight

### Requirement

Layer 2.5 must provide a JcvPCA-safe export path that does not time-normalize repetitions for Layer 3.

JcvPCA does not require A and B to have the same number of rows. Repetitions and exercises may have different durations. The pipeline must preserve the natural number and order of frames in each selected exercise/repetition.

### Forbidden for JcvPCA-ready exports

Do not apply any of these transformations for the purpose of making repetitions equal length or temporally aligned:

```text
stretching repetitions to a fixed duration
compressing repetitions to a fixed duration
padding shorter repetitions with artificial rows
truncating longer repetitions solely to match another repetition
Dynamic Time Warping / DTW
interpolation for temporal alignment
resampling each P exercise to a fixed number of frames for PCA comparison
```

### Allowed, if already part of validated upstream processing and documented

The following are not automatically forbidden, but they must be documented in Layer 2.5 provenance:

```text
capture-system frame rate handling
standard filtering from validated Layer 2
segmentation into P1-P5 windows
removal of invalid frames by QC rules
ordinary interpolation used only to repair short gaps before segmentation, if already part of the validated upstream pipeline
```

If any operation changes the number or timing of frames specifically to align repetitions for comparison, it must not be used for the JcvPCA-ready export.

### Required Layer 2.5 manifest fields

Cursor must inspect Layer 2.5. If these fields are missing, Cursor is allowed to adapt Layer 2.5 to add them:

```text
time_normalized: true / false / unknown
dtw_applied: true / false / unknown
padding_applied: true / false / unknown
duration_equalized: true / false / unknown
fixed_length_resample_applied: true / false / unknown
alignment_interpolation_applied: true / false / unknown
original_n_frames
exported_n_frames
time_sec_start
time_sec_end
export_mode: jcvpca_safe / other / unknown
```

### Preflight behavior

Blocking:

```text
time_normalized = true
dtw_applied = true
padding_applied = true
duration_equalized = true
fixed_length_resample_applied = true
export_mode != jcvpca_safe, when export mode is known and incompatible
```

Warning requiring user acknowledgment:

```text
any provenance field is unknown
original_n_frames is unavailable
exported_n_frames is unavailable
time_sec range is unavailable
```

Pass:

```text
export_mode = jcvpca_safe
all forbidden transformation flags are false
row counts may differ between A and B
```

### Required UI display

Add a Layer 2.5 Time Provenance panel showing per matrix:

```text
matrix role
participant
timepoint
repetition
exercise
matrix path
original_n_frames
exported_n_frames
time_sec_start
time_sec_end
time_normalized
dtw_applied
padding_applied
duration_equalized
fixed_length_resample_applied
export_mode
status: pass / warning / blocking
```

The UI must explicitly state:

```text
Different row counts are allowed for JcvPCA.
The workbench does not require A and B to have equal duration.
No DTW, padding, or duration matching should be applied before PCA.
```

### Required Layer 2.5 adaptation

If Layer 2.5 cannot currently expose these fields, Cursor must add or propose the minimal required adaptation:

```text
1. Add a JcvPCA-safe export mode or manifest marker.
2. Preserve natural frame count per P exercise/repetition.
3. Write time-provenance fields into the export manifest.
4. Ensure Layer 3 can read and display these fields.
5. Do not silently infer missing provenance in Layer 3.
```

### Required outputs

Save:

```text
layer25_time_provenance_report.csv
layer25_time_provenance_report.md
jcvpca_safe_export_manifest.csv
```

Add to run manifest:

```json
{
  "time_normalization_policy": "no_time_normalization_no_dtw_for_jcvpca",
  "row_count_matching_required": false,
  "layer25_time_provenance_status": "pass_or_warning_or_blocking"
}
```

### Required tests

Add tests proving:

```text
A and B with different row counts can pass preflight if feature schema is compatible
DTW flag true causes blocking status
time_normalized flag true causes blocking status
padding_applied flag true causes blocking status
unknown provenance causes warning, not silent pass
row-wise concatenation preserves selected exercise order
```

### UI checkpoint

At the end of this safeguard, the user must be able to visually verify:

```text
which matrices came from a JcvPCA-safe export
whether any time normalization / DTW / padding occurred
that unequal durations are accepted
which missing provenance fields still require attention
```

### Acceptance criteria

- Layer 3 does not force equal row counts between A and B.
- Layer 2.5 JcvPCA exports expose time-provenance fields.
- Forbidden time-alignment transformations block analysis.
- Unknown provenance creates a warning and requires user acknowledgment.
- The UI clearly explains why unequal durations are allowed.

---

## Integration Into the Main Implementation Plan

Cursor must integrate these safeguards into the main plan as follows:

```text
Phase 0 / Step 0:
- Add Safeguard D: Layer 2.5 time provenance and no time normalization / no DTW checks.

Phase 1:
- If Layer 2.5 lacks required provenance fields, adapt Layer 2.5 export manifest.
- Add UI panel for JcvPCA-safe export readiness.

Steps 4-8:
- Add Safeguard B: rows-to-features PCA sample adequacy checks.
- Show warnings before PCA on A.

Steps 13-14:
- Add Safeguard C: explicit B-minus-A sign convention and RSS-before-delta documentation.

Step 16:
- Add Safeguard A: iterative random-split NV, not a single split.
```

---

## Global Acceptance Criteria for This Addendum

The addendum is complete only when all of the following are true:

```text
1. Every safeguard has visible UI representation.
2. Every safeguard writes an artifact to the run output folder.
3. Every safeguard is saved in run_manifest.json.
4. Every safeguard has at least one automated test.
5. Blocking vs warning behavior is explicit.
6. The user can inspect results before continuing.
7. No safeguard introduces scientific conclusion language.
8. The developer cannot accidentally run a black-box analysis that hides these choices.
```

