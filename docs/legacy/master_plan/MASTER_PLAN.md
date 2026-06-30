# MASTER_PLAN.md

# Three-Layer Pipeline for Motive-Derived JcvPCA Analysis of Gaga Part 1

## 1. Purpose

This master plan defines the implementation architecture for a three-layer pipeline that adapts the JcvPCA computational framework to OptiTrack/Motive-derived Gaga movement data.

The pipeline is designed for Gaga Task Part 1, where each participant has three timepoints:

```text
T1, T2, T3
```

At each timepoint, Part 1 is repeated twice:

```text
T1_P1_r1, T1_P1_r2
T2_P1_r1, T2_P1_r2
T3_P1_r1, T3_P1_r2
```

The first analytical focus will be:

```text
Primary:   Group 4 — Curvilinear exploration
Secondary: Group 5 — Single-leg balance with whole-body curves
```

The purpose is to compare changes in whole-body joint contribution structure from T1 to T2 and T3, using T1 as the reference condition.

This pipeline should be implemented conservatively and transparently. It should not claim to reproduce direct encoder-based anatomical joint-angle measurement. Instead, it should be framed as:

```text
An adaptation of the JcvPCA computational framework to Motive-derived relative joint rotation-vector features, supported by raw marker quality control.
```

---

## 2. Core Architecture

The pipeline has three strictly separated layers.

```text
Layer 1 — Raw marker QC
Layer 2 — Solved skeleton kinematics
Layer 3 — Segmentation + JcvPCA coordination analysis
```

The data flow is:

```text
Raw marker CSV
  -> Layer 1 QC only
  -> artifact flags and QC summaries

Mixed Motive CSV with global bone quaternions
  -> Layer 2 kinematic feature extraction
  -> continuous filtered relative rotation-vector features

Layer 2 continuous feature table + segment declaration table
  -> Layer 3 segmentation and JcvPCA
  -> JRW, JcvPCA, natural variability, interpretation tables
```

---

## 3. Layer Responsibilities

## 3.1 Layer 1 — Raw Marker QC

### Role

Layer 1 evaluates raw optical marker measurement quality.

It answers:

```text
Was the raw optical measurement stable during the recording and during the analysis windows later used in Layer 3?
```

### Input

```text
raw_marker_csv
segment_declaration_table.csv, optional but recommended once Layer 3 segments are declared
```

### Main operations

Layer 1 should detect and report:

```text
missing marker frames
long marker gaps
marker jumps
velocity spikes
unlabeled-marker bursts
segment-length instability
frame-level artifact burden
segment-level artifact burden
```

### Output

```text
raw_marker_qc_report.csv
raw_marker_missingness_by_marker.csv
raw_marker_jump_flags.csv
raw_marker_velocity_spike_flags.csv
raw_marker_unlabeled_marker_report.csv
raw_marker_segment_length_report.csv
raw_marker_frame_artifact_table.csv
raw_marker_window_qc_summary.csv
raw_marker_qc_metadata.json
```

### What Layer 1 must not do

Layer 1 must not:

```text
repair raw marker trajectories
gap-fill marker data for final analysis
derive joint angles
derive quaternions
create JcvPCA features
select the cleanest movement window automatically
```

Layer 1 is a QC evidence layer only.

---

## 3.2 Layer 2 — Solved Skeleton Kinematics

### Role

Layer 2 converts Motive-solved global bone quaternions into continuous filtered relative joint rotation-vector features.

It answers:

```text
Can we create a clean continuous feature table of joint_rx, joint_ry, joint_rz variables for later JcvPCA?
```

### Input

```text
mixed Motive CSV containing global bone quaternions
parent_child_joint_map.csv
```

### Main operations

Layer 2 should perform:

```text
bone quaternion column discovery
frame/time validation
global quaternion missingness check
quaternion normalization
global quaternion sign-continuity correction
parent-child relative quaternion computation
relative quaternion sign-continuity correction
log-map conversion to rotation vectors
rotation-vector jump checks
Butterworth low-pass filtering in tangent space
feature-manifest creation
final Layer 2 validation
```

The central transformation is:

```text
Motive global bone quaternions
  -> parent-child relative quaternions
  -> log-map rotation vectors
  -> continuous filtered joint_rx / joint_ry / joint_rz features
```

### Output

```text
relative_rotation_vectors_filtered.parquet
relative_rotation_vectors_filtered.csv
layer2_feature_table_continuous.parquet
layer3_feature_manifest.csv
layer2_metadata.json
```

### What Layer 2 must not do

Layer 2 must not:

```text
perform JcvPCA
center data for PCA
z-score or normalize features for PCA
segment the data into final Group/Task analysis windows
use raw marker data to compute final joint variables
use global bone quaternions directly as PCA features
convert to Euler angles unless explicitly requested in a separate diagnostic branch
```

### Important design lock

Layer 2 outputs continuous filtered features.

```text
segmentation_performed_in_layer2 = false
filtered_before_segmentation = true
```

Segmentation happens only after Layer 2 and immediately before Layer 3.

---

## 3.3 Layer 3 — Segmentation + JcvPCA Coordination Analysis

### Role

Layer 3 segments the continuous Layer 2 features, builds A/B datasets, and runs JcvPCA-style analysis.

It answers:

```text
How did joint contribution structure change from T1 to T2 and T3?
```

### Input

```text
layer2_feature_table_continuous.parquet
layer3_feature_manifest.csv
segment_declaration_table.csv
analysis_plan_config.yaml or analysis_plan_config.json
```

### Main operations

Layer 3 should perform:

```text
load segment declaration table
extract manually/video-verified windows
build A and B datasets
validate identical feature order
center A and B independently
fit PCA on A
select retained PCs from A only
project B into A PCA space manually
recompute PCA on projected B
reproject B loadings into original feature space
compute axis-level JRW and JcvPCA
group rx/ry/rz per joint using root-sum-square
compare observed change with T1 repetition-level variability
export results and metadata
```

### Main comparison structure

For Group 4:

```text
A    = T1_P1_r1_Group4 + T1_P1_r2_Group4
B_T2 = T2_P1_r1_Group4 + T2_P1_r2_Group4
B_T3 = T3_P1_r1_Group4 + T3_P1_r2_Group4
```

For Group 5:

```text
A    = T1_P1_r1_Group5 + T1_P1_r2_Group5
B_T2 = T2_P1_r1_Group5 + T2_P1_r2_Group5
B_T3 = T3_P1_r1_Group5 + T3_P1_r2_Group5
```

Natural variability:

```text
T1_P1_r1_GroupX vs T1_P1_r2_GroupX
```

### Output

```text
JRW_axis_table.csv
JcvPCA_axis_table.csv
JcvPCA_joint_table.csv
Natural_variability_table.csv
Interpretation_table.csv
PCA_stability_report.csv
metadata.json
plots/
```

### What Layer 3 must not do

Layer 3 must not:

```text
use raw marker columns as PCA features
use raw quaternion columns as PCA features
use global bone quaternion columns as PCA features
z-score or variance-normalize JcvPCA features
select PCs from T2 or T3
use PCA_A.transform(B_raw) if it subtracts A's mean automatically
interpret JcvPCA as synchronization or timing
claim statistical significance with only two T1 repetitions
```

---

## 4. Segment Declaration Table

A dedicated segment declaration file is required.

Layer 3 must not automatically decide which groups/tasks to analyze. Composer should implement a clear file where the scientist declares the analysis windows.

Recommended file:

```text
config/segment_declaration_table.csv
```

Required columns:

```text
subject_id
timepoint
part_id
repetition_id
group_id
task_id
start_time
end_time
start_frame
end_frame
include_in_analysis
boundary_source
boundary_verified
qc_required
notes
```

Example rows:

```text
S01,T1,P1,r1,Group4,,00:01:52.11,00:02:53.15,,,true,video,true,true,primary group
S01,T1,P1,r2,Group4,Task10,00:02:02.26,00:02:14.05,,,true,video,true,true,task-level exploratory
S01,T2,P1,r1,Group5,,00:02:53.15,00:03:33.29,,,true,video,true,true,secondary group
```

Rules:

```text
1. Segment boundaries must be manually/video verified before final analysis.
2. Transcript-based timestamps may be used as initial estimates only.
3. Layer 3 uses only rows where include_in_analysis = true.
4. Layer 1 uses the same table to compute segment-level QC summaries.
5. QC should evaluate declared windows; QC should not secretly define the windows.
```

---

## 5. Shared Configuration Files

The pipeline should use explicit config files.

Recommended structure:

```text
config/
  project_config.yaml
  file_manifest.csv
  parent_child_joint_map.csv
  marker_pair_map.csv
  segment_declaration_table.csv
  analysis_plan_config.yaml
```

## 5.1 file_manifest.csv

Purpose:

Declare which files belong to which subject/timepoint/repetition.

Columns:

```text
subject_id
timepoint
part_id
repetition_id
raw_marker_csv_path
mixed_motive_csv_path
include_in_pipeline
notes
```

## 5.2 parent_child_joint_map.csv

Purpose:

Declare which bones define each relative joint.

Columns:

```text
joint_name
parent_bone
child_bone
include_in_layer3
notes
```

Example:

```text
trunk,Pelvis,Chest,true,
left_knee,LThigh,LShin,true,
right_knee,RThigh,RShin,true,
left_elbow,LUArm,LFArm,true,
```

## 5.3 marker_pair_map.csv

Purpose:

Declare marker pairs for Layer 1 segment-length plausibility QC.

Columns:

```text
pair_name
marker_a
marker_b
body_region
include_in_qc
notes
```

## 5.4 analysis_plan_config.yaml

Purpose:

Declare what Layer 3 should run.

Example:

```yaml
subject_ids:
  - S01

reference_timepoint: T1
comparison_timepoints:
  - T2
  - T3

part_id: P1

primary_groups:
  - Group4
  - Group5

analysis_levels:
  - group_cross_repetition
  - group_single_repetition
  - single_task_cross_repetition
  - single_task_single_repetition

first_pass_analysis_levels:
  - group_cross_repetition

feature_scope: whole_body

variance_threshold: 0.90

centering_rule: center_each_dataset_independently
normalization_rule: no_z_score_no_variance_scaling
joint_grouping_rule: root_sum_square_rx_ry_rz
natural_variability_rule: T1_r1_vs_T1_r2
```

---

## 6. Notebook Structure

Each layer must have its own notebook so a scientist can inspect and run each stage independently.

Recommended notebooks:

```text
notebooks/
  01_layer1_raw_marker_qc.ipynb
  02_layer2_solved_skeleton_kinematics.ipynb
  03_layer3_jcvpca_analysis.ipynb
```

Optional additional notebooks:

```text
notebooks/
  00_file_and_config_validation.ipynb
  04_results_review_and_figures.ipynb
```

## 6.1 Notebook 00 — File and Config Validation

Purpose:

```text
Validate that all required files and config tables exist before running the pipeline.
```

Should show:

```text
file manifest
detected subjects/timepoints/repetitions
missing files
parent-child map validation
segment declaration validation
```

Stop condition:

```text
Do not proceed if required files or config rows are missing.
```

## 6.2 Notebook 01 — Layer 1 Raw Marker QC

Purpose:

```text
Run raw marker QC and inspect artifact flags.
```

Should show:

```text
marker inventory
frame/time validation
missingness summary
jump summary
velocity spike summary
unlabeled marker summary
segment-length plausibility summary
frame-level artifact table
segment-level QC summary for declared Layer 3 segments
QC plots
```

Human review checkpoint:

```text
Scientist reviews whether declared analysis windows have acceptable raw-marker QC.
```

## 6.3 Notebook 02 — Layer 2 Solved Skeleton Kinematics

Purpose:

```text
Create continuous filtered relative rotation-vector features.
```

Should show:

```text
bone inventory
frame/time validation
quaternion norm report
global sign-flip report
relative sign-flip report
rotation-vector jump report
filter settings
feature manifest
final output validation
example rotation-vector trajectories
```

Human review checkpoint:

```text
Scientist verifies that continuous joint_rx/joint_ry/joint_rz features are valid before Layer 3.
```

## 6.4 Notebook 03 — Layer 3 JcvPCA Analysis

Purpose:

```text
Run segmentation and JcvPCA on declared analysis units.
```

Should show:

```text
selected segment rows
A/B dataset construction
feature-order validation
selected_m and explained variance
PCA stability check
JRW axis table
JcvPCA axis table
JcvPCA joint table
natural variability table
interpretation table
plots
metadata
```

Human review checkpoint:

```text
Scientist reviews whether JcvPCA results are stable, interpretable, and supported by natural variability and QC.
```

---

## 7. Implementation Order With STOP Checkpoints

Composer must not implement the entire pipeline in one uncontrolled pass.

Implementation should proceed in stops.

## STOP 0 — Repository and Config Skeleton

Implement:

```text
folder structure
config templates
notebook templates
empty output folders
basic logging
```

Required output:

```text
project structure created
config files load successfully
notebooks created
```

Stop and wait for review.

---

## STOP 1 — File Manifest and Column Discovery

Implement:

```text
load file_manifest.csv
detect raw marker files
detect mixed Motive files
parse frame/time columns
detect marker XYZ columns
detect bone quaternion columns
```

Required output:

```text
raw_marker_inventory.csv
bone_inventory.csv
file_validation_report.csv
```

Stop and wait for review.

---

## STOP 2 — Layer 2 Minimal Prototype on One File

Implement Layer 2 on one representative mixed Motive CSV.

Run:

```text
quaternion extraction
normalization
global sign-continuity correction
relative quaternion computation
relative sign-continuity correction
log-map rotation vectors
continuous filtering
feature manifest export
```

Required output:

```text
layer2_feature_table_continuous.parquet
relative_rotation_vectors_filtered.csv
layer3_feature_manifest.csv
layer2_final_validation_report.csv
```

Stop and inspect trajectories.

---

## STOP 3 — Validate Layer 2 Across All Required T1/T2/T3 Repetitions

Run Layer 2 for:

```text
T1_P1_r1
T1_P1_r2
T2_P1_r1
T2_P1_r2
T3_P1_r1
T3_P1_r2
```

Required output:

```text
one continuous Layer 2 feature table per recording
consistent layer3_feature_manifest.csv
no missing JcvPCA features
```

Stop and verify that feature names and order are identical across all six files.

---

## STOP 4 — Segment Declaration Table

Create and validate:

```text
segment_declaration_table.csv
```

Start only with:

```text
Group4
Group5
```

For each subject/timepoint/repetition.

Rules:

```text
use transcript timestamps only as starting estimates
manual/video verification required before final analysis
include_in_analysis must be explicit
```

Required output:

```text
segment_declaration_validation_report.csv
```

Stop and manually review boundaries.

---

## STOP 5 — Layer 3 Minimal JcvPCA Prototype: Group 4 Only

Run first analysis:

```text
A    = T1_r1_Group4 + T1_r2_Group4
B_T2 = T2_r1_Group4 + T2_r2_Group4
B_T3 = T3_r1_Group4 + T3_r2_Group4
Natural variability = T1_r1_Group4 vs T1_r2_Group4
```

Required output:

```text
Group4_JRW_axis_table.csv
Group4_JcvPCA_axis_table.csv
Group4_JcvPCA_joint_table.csv
Group4_Natural_variability_table.csv
Group4_Interpretation_table.csv
Group4_metadata.json
```

Stop and review.

---

## STOP 6 — Add Layer 1 QC Attachment for Group 4 Windows

Run Layer 1 QC and compute segment-level QC for the same declared Group 4 windows.

Required output:

```text
raw_marker_window_qc_summary.csv
Group4_QC_attached_interpretation_table.csv
```

Stop and verify whether Group 4 results are supported by raw-marker QC.

---

## STOP 7 — Expand to Group 5

Run the same Layer 3 and Layer 1 attachment for Group 5.

Required output:

```text
Group5_JRW_axis_table.csv
Group5_JcvPCA_axis_table.csv
Group5_JcvPCA_joint_table.csv
Group5_Natural_variability_table.csv
Group5_Interpretation_table.csv
Group5_QC_attached_interpretation_table.csv
```

Stop and review.

---

## STOP 8 — Add Group-Level Single-Repetition Checks

Run:

```text
T1_r1_GroupX vs T2_r1_GroupX
T1_r2_GroupX vs T2_r2_GroupX
T1_r1_GroupX vs T3_r1_GroupX
T1_r2_GroupX vs T3_r2_GroupX
```

Purpose:

```text
Check whether r1 and r2 show consistent direction of change.
```

Stop and review consistency.

---

## STOP 9 — Add Task-Level Exploratory Analysis

Only after group-level results are stable, add task-level analysis.

Run:

```text
single_task_cross_repetition
single_task_single_repetition
```

Caution:

```text
short tasks may produce unstable PCA
task-level results should be marked exploratory unless stable
```

Stop and review.

---

## STOP 10 — Generalize to More Subjects

Only after one-subject workflow is validated, scale to additional participants.

Required output:

```text
batch_summary_table.csv
participant_level_results/
group_level_summary/
```

---

## 8. Non-Negotiable Methodological Rules

These rules must not be changed during implementation without explicit review.

## 8.1 Layer separation

```text
Layer 1 = QC only
Layer 2 = continuous kinematic feature extraction only
Layer 3 = segmentation + JcvPCA only
```

## 8.2 No raw marker features in JcvPCA

JcvPCA must not use raw marker XYZ columns.

## 8.3 No raw quaternion features in JcvPCA

JcvPCA must not use global bone quaternions or raw quaternion components.

## 8.4 Final Layer 3 features

The only default Layer 3 features are:

```text
filtered parent-child relative rotation-vector components:
joint_rx
joint_ry
joint_rz
```

## 8.5 No Euler-angle branch by default

Do not create Euler angles for the main analysis.

Euler conversion may be added later only as a separate diagnostic branch.

## 8.6 Filtering before segmentation

Layer 2 should filter continuous Part 1 or continuous recording features before Layer 3 segmentation.

## 8.7 Independent centering

Layer 3 must center each dataset independently:

```text
A_centered = A - mean(A)
B_centered = B - mean(B)
```

## 8.8 No variance scaling

Layer 3 must not z-score, standardize, or range-normalize features before JcvPCA.

## 8.9 Manual B projection

Do not use a PCA library transform on B if it automatically subtracts A’s training mean.

Use:

```text
B_scores_in_A_space = B_centered @ R_A.T
```

## 8.10 PC selection from A only

The number of retained PCs must be selected from the reference dataset A only.

Do not select retained PCs from B.

## 8.11 JcvPCA sign convention

Use:

```text
JcvPCA_axis = abs(B_reprojected_loading) - abs(A_loading)
```

Interpretation:

```text
positive = increased contribution in B relative to A
negative = decreased contribution in B relative to A
```

## 8.12 Joint grouping rule

For each joint and PC:

```text
JRW_A_joint = sqrt(A_rx^2 + A_ry^2 + A_rz^2)
JRW_B_joint = sqrt(B_rx^2 + B_ry^2 + B_rz^2)

JcvPCA_joint = JRW_B_joint - JRW_A_joint
```

This rule groups the three rotation-vector components into a joint-level contribution.

## 8.13 Natural variability

Natural variability is estimated from T1 only:

```text
T1_P1_r1_GroupX vs T1_P1_r2_GroupX
```

Do not describe results as statistically significant unless formal statistics are added later.

## 8.14 Segmentation

Segment boundaries must be declared explicitly in `segment_declaration_table.csv`.

Layer 3 must not automatically select windows based on cleanliness or result quality.

## 8.15 Interpretation

Use conservative language:

```text
increased beyond T1 repetition-level variability
decreased beyond T1 repetition-level variability
within T1 repetition-level variability / inconclusive
exploratory
stable / unstable PCA
```

Avoid:

```text
proved change
statistically significant
direct muscle use
direct anatomical joint loading
```

---

## 9. Required Output Folder Structure

Recommended structure:

```text
analysis_output/

  layer1_raw_marker_qc/
    raw_marker_inventory.csv
    raw_marker_positions.parquet
    raw_marker_frame_time_validation_report.csv
    raw_marker_missingness_by_marker.csv
    raw_marker_jump_flags.csv
    raw_marker_jump_summary.csv
    raw_marker_velocity_spike_flags.csv
    raw_marker_velocity_summary.csv
    raw_marker_unlabeled_marker_report.csv
    raw_marker_unlabeled_burst_flags.csv
    raw_marker_segment_length_report.csv
    raw_marker_segment_length_flags.csv
    raw_marker_frame_artifact_table.csv
    raw_marker_window_qc_summary.csv
    raw_marker_qc_report.csv
    raw_marker_qc_metadata.json
    plots/

  layer2_solved_skeleton_kinematics/
    bone_inventory.csv
    parent_child_joint_map_used.csv
    frame_time_validation_report.csv
    bone_quaternion_missingness_report.csv
    quaternion_norm_report.csv
    quaternion_sign_flip_report_global.csv
    quaternion_sign_flip_report_relative.csv
    relative_joint_quaternions.parquet
    relative_rotation_vectors_unfiltered.parquet
    relative_rotation_vectors_filtered.parquet
    relative_rotation_vectors_filtered.csv
    layer2_feature_table_continuous.parquet
    layer3_feature_manifest.csv
    layer2_final_validation_report.csv
    layer2_metadata.json
    plots/

  layer3_jcvpca_analysis/
    segment_declaration_validation_report.csv
    feature_validation_report.csv
    pca_A_summary.csv
    pca_B_projected_summary.csv
    JRW_axis_table.csv
    JcvPCA_axis_table.csv
    JcvPCA_joint_table.csv
    Natural_variability_table.csv
    Interpretation_table.csv
    PCA_stability_report.csv
    metadata.json
    plots/
```

---

## 10. Implementation Priority

The first implementation should not attempt to run every possible group, task, subject, and analysis level.

The first target is:

```text
one subject
six Part 1 repetitions:
  T1_P1_r1
  T1_P1_r2
  T2_P1_r1
  T2_P1_r2
  T3_P1_r1
  T3_P1_r2

Layer 2 continuous feature extraction for all six files

Layer 3 Group 4 cross-repetition comparison:
  T1 vs T2
  T1 vs T3
  T1_r1 vs T1_r2 natural variability

Layer 1 QC attached to the same Group 4 windows
```

Only after this first target is validated should Composer expand to:

```text
Group 5
single-repetition checks
task-level analysis
additional participants
```

---

## 11. Final Scientific Framing

The correct final framing is:

```text
Raw marker trajectories were used as a measurement-level quality-control layer. Final kinematic features were derived from Motive-solved global bone quaternions by computing parent-child relative joint rotations and mapping them to tangent-space rotation vectors. These continuous filtered relative rotation-vector features were segmented into manually verified Gaga movement windows and used for a JcvPCA-style analysis. The resulting joint contribution changes were interpreted relative to T1 repetition-level natural variability.
```

The method should not be framed as:

```text
direct anatomical joint-angle reconstruction from markers
direct replication of encoder-based JcvPCA measurement
direct measurement of muscle use
direct measurement of synchronization
proof of statistically significant change
```

---
