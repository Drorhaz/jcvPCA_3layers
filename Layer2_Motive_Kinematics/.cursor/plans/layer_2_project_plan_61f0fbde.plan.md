---
name: Layer 2 Project Plan
overview: "Plan for an independent Layer 2 Python package that parses Motive mixed CSV global bone quaternions, produces filtered parent-child relative rotation-vector features with stage-based audit reports, and defers Layer 3 entirely. Priority: v5.1 correction addendum over v5 spec over scope addendum over MASTER_PLAN."
todos:
  - id: review-plan
    content: User reviews plan and answers validation items (sample CSV for M1, distal/toe rules, thresholds)
    status: pending
  - id: milestone-0
    content: "Milestone 0: scaffold src/layer2_motive package, pyproject.toml, configs, tests, docs — no algorithms"
    status: completed
  - id: milestone-1
    content: "Milestone 1: Stages 00–01 parser + joint mapping on representative Motive CSV; stop for validation"
    status: pending
  - id: milestone-2-3
    content: "Milestones 2–3: Stages 02–05 component order, timing, quaternion QC, sign continuity"
    status: pending
  - id: milestone-4-5
    content: "Milestones 4–5: Stages 06–08 relative quats, rotvecs, filtering, final manifests"
    status: pending
  - id: milestone-6
    content: "Milestone 6: scale to six Part 1 repetitions; verify feature consistency"
    status: pending
isProject: false
---

# Layer 2 Motive Kinematics — Planning Summary

## Known from documents

### Project purpose

Layer 2 is an **independent** research-code project (not Layer 1 Motive_QC) that transforms **Motive-solved global bone quaternions** from a **mixed Motive CSV export** into **filtered parent-child relative joint rotation-vector features** (`joint_rx`, `joint_ry`, `joint_rz` per selected joint).

Central math (documented, not invented):

```text
q_joint(t) = inverse(q_parent_global(t)) * q_child_global(t)
→ relative quaternion sign-continuity (Stage 06, per joint, before log-map)
→ scipy Rotation.as_rotvec()
→ Butterworth sosfiltfilt on rotvec components (not quaternion components)
```

**Resolved:** Relative quaternion sign-continuity is **required** in Stage 06 — applied per joint after relative quaternion computation and **before** Stage 07 log-map / rotation-vector conversion. Same rule as Stage 05 (flip if `dot(q[t], q[t-1]) < 0`), on relative joint quaternions.

Scientific framing (required in all reports):

- **Say:** filtered parent-child relative rotation-vector features derived from Motive-solved global bone quaternions
- **Do not say:** validated anatomical joint angles, encoder-equivalent measurement, JcvPCA results

Layer 2 must **not** import Layer 1 code, depend on Layer 1 outputs, use raw marker XYZ, or implement Layer 3 (PCA, JcvPCA, JRW, segmentation, T1/T2 comparison, statistical inference).

### Document priority (when conflicts arise)

```text
1. 08_LAYER2_SPEC_V5_1_CORRECTION_ADDENDUM.md   (highest)
2. 00–07 Layer 2 v5 specification files
3. MASTER_PLAN_V5_1_CURSOR_SCOPE_ADDENDUM.md
4. MASTER_PLAN.md
```

### Required inputs

| Input | Source | Notes |
|-------|--------|-------|
| Mixed Motive CSV | User-provided path via CLI | Must contain `Type=Bone`, `Property=Rotation`, components `X/Y/Z/W` |
| Metadata in CSV | Parsed dynamically | `Rotation Type`, `Coordinate Space`, frame rates, `Total Frames`, `Length Units` |
| Parent hierarchy | Parsed from CSV `Parent` row | Not assumed from external file in V0 |
| Optional config (later) | `configs/default_layer2_config.yaml` | Filter params, exclusion keywords, joint selection overrides |
| Optional CLI flags | e.g. `--cutoff-hz 10`, `--filter-order 4`, `--allow-short-gap-interpolation` | v5.1: interpolation **off by default** |

**Hard stops before computation** (fail loudly):

- `Rotation Type` not Quaternion or unverifiable
- `Coordinate Space` not Global or unverifiable
- Cannot detect Frame/Time columns
- Cannot group Bone Rotation X/Y/Z/W per bone
- Cannot build parent-child hierarchy

### Required outputs

**Primary deliverables** (continuous time-series, full recording — no segmentation):

```text
outputs/08_filtering/relative_rotation_vectors_filtered.parquet
outputs/08_filtering/relative_rotation_vectors_filtered.csv
```

Columns: `frame`, `time`, plus `{joint}_rx`, `{joint}_ry`, `{joint}_rz` for each selected relative joint. Feature naming documented in `outputs/07_rotvec_conversion/rotvec_feature_map.csv`.

**Master-plan downstream artifacts** (also required per scope addendum):

```text
layer2_feature_table_continuous.parquet   # alias/wrapper of filtered features + frame/time
layer3_feature_manifest.csv               # stable feature order for Layer 3
layer2_metadata.json
layer2_final_validation_report.csv        # end-of-pipeline summary
```

**Stage audit tree** (under user-specified `--output-dir`, default `outputs/`):

```text
outputs/
  00_csv_structure/       # header detection, column inventory
  01_joint_mapping/       # hierarchy, candidate/selected joints, excluded_distal_bones.csv
  02_quaternion_detection/  # component-order + SciPy compatibility (not full convention proof)
  03_frame_timing/        # monotonicity, sampling rate
  04_quaternion_qc/       # missingness, norms, gap reports (pre/post mitigation)
  05_sign_continuity/     # global bone sign-flip correction
  06_local_relative_validation/  # relative quats + broad reconstruction test
  07_rotvec_conversion/   # unfiltered rotvecs, jump + continuity reports
  08_filtering/           # filter report, full + 2-sec zoom plots
  assumptions_log.md
  run_summary.md
```

**v5.1 additions** to the contract:

- `excluded_distal_bones.csv` (replaces `excluded_finger_bones.csv`)
- `candidate_joint_map.csv`, `selected_joint_map_v0.csv`, `joint_selection_summary.md`
- `relative_rotation_reconstruction_report.csv`, `relative_rotation_reconstruction_summary.md`
- `rotvec_continuity_report.csv`, `rotvec_continuity_summary.md`
- `filtering_validation_report.md`
- `before_after_filter_plot_zoom_2sec.png`
- Default gap behavior: **detect and stop**; interpolation only with explicit flag

### Pipeline stages (v5 spec numbering — authoritative for implementation)

```mermaid
flowchart LR
  csv[MotiveMixedCSV] --> s00[Stage00_CSVAudit]
  s00 --> s01[Stage01_JointMapping]
  s01 --> s02[Stage02_ComponentOrder]
  s02 --> s03[Stage03_FrameTiming]
  s03 --> s04[Stage04_QuaternionQC]
  s04 --> s05[Stage05_SignContinuity]
  s05 --> s06[Stage06_RelativeQuats]
  s06 --> s07[Stage07_RotVecLogMap]
  s07 --> s08[Stage08_ButterworthFilter]
  s08 --> out[FilteredFeatureTable]
```

Key implementation rules (documented):

- **No Pandas MultiIndex headers** — manual header block parse, flat column map, `pd.read_csv(skiprows=..., names=...)`
- **SciPy Rotation** for all quaternion multiplication (`r_parent.inv() * r_child`)
- **Flat dicts/tables** for hierarchy — no OO skeleton tree
- **NumPy-vectorized** sign continuity over frames (loop over bones OK)
- **Filter defaults:** order 4, cutoff 10 Hz, rate inferred from Time column (~120 Hz expected)
- **Cutoff validation:** `cutoff_hz < 0.45 * sampling_rate_hz`
- **Agent workflow:** stop after each stage for human review; **script:** non-interactive `run-stage` / `run-until` / `run-all`, exit on failure

### Proposed repository structure

Greenfield repo today contains **only 11 spec markdown files**. Recommended structure (v5.1 + scope addendum, reconciled):

```text
layer2_motive_kinematics/          # repo root (current dir)
  README.md                        # project entry (not the 00_ spec copy)
  pyproject.toml                   # package + dev tooling
  src/
    layer2_motive/
      __init__.py
      cli.py                       # typer or argparse: run-stage, run-until, run-all
      config.py
      parsing.py                   # Stage 00–01 header/column discovery
      metadata.py                  # Rotation Type, Coordinate Space, frame rates
      hierarchy.py                 # prefix strip, Root handling, joint selection heuristics
      quaternions.py               # norm QC, sign continuity, SciPy Rotation helpers
      relative_rotation.py         # Stage 06 + reconstruction tests
      rotvec.py                    # log-map, jump/continuity checks
      filtering.py                 # sosfiltfilt + pre-filter validation
      validation.py                # shared stop/fail helpers, thresholds
      reporting.py                 # report.md writers, assumptions_log
      io.py                        # parquet/csv I/O, output path helpers
      stages/                      # optional: stage00.py … stage08.py orchestration
  tests/
    fixtures/                      # minimal synthetic Motive header snippets (no real subject data in git)
    test_header_detection.py
    test_frame_time_detection.py
    test_prefix_stripping.py
    test_quaternion_component_order.py
    test_quaternion_normalization.py
    test_sign_continuity.py
    test_relative_reconstruction.py
    test_gap_detection.py
    test_filtering_validation.py
  configs/
    default_layer2_config.yaml     # cutoff, filter order, exclusion keywords, thresholds
    selected_body_joints_template.yaml
  docs/
    specs/                         # symlink or copy of 00–08 + MASTER_PLAN docs (optional)
    PROJECT_SCOPE.md
    VALIDATION_PROTOCOL.md
    DECISION_LOG.md
    ASSUMPTIONS_LOG_TEMPLATE.md
  examples/
    README.md                      # how to run against a local Motive CSV (not committed)
  outputs/
    .gitkeep
```

Keep the existing numbered spec files at repo root (or move to `docs/specs/`) — they are the specification source of truth.

### Minimal Python / dev tooling

**Runtime dependencies** (required):

```text
python >= 3.10
numpy
pandas
scipy
pyarrow
matplotlib        # required PNG diagnostics per 03/06; v5.1 lists optional but plots are mandatory outputs
pyyaml            # config files per v5.1
```

**Dev dependencies** (required from project start per v5.1):

```text
pytest
ruff
pyright or basedpyright
```

**Optional** (add only when needed):

```text
plotly    # optional HTML diagnostics; PNG still required
rich      # nicer CLI output
typer     # CLI ergonomics (or stdlib argparse for minimalism)
seaborn   # heatmaps only
polars    # not needed for V0
```

**Explicitly excluded:** scikit-learn, tensorflow, pytorch, GUI/dashboard frameworks, Layer 1 imports.

**CLI sketch** (v5.1 preferred over single loose script):

```bash
layer2-motive run-stage --stage 00 --input path/to/motive.csv --output-dir outputs/run1
layer2-motive run-until --stage 06 --input ... --output-dir ...
layer2-motive run-all --input ... --output-dir ... --cutoff-hz 10 --filter-order 4
# interpolation OFF by default; enable explicitly:
layer2-motive run-all ... --allow-short-gap-interpolation
```

### Conflicts, ambiguities, and missing decisions

| Issue | Documents involved | Resolution per priority |
|-------|-------------------|----------------------|
| `excluded_finger_bones.csv` vs `excluded_distal_bones.csv` | 02/03 vs 08 | Use **`excluded_distal_bones.csv`** only |
| Single script vs `src/` package | 05/06 vs 08/scope addendum | Use **`src/layer2_motive/` package** |
| Gap interpolation default | v5 spec vs 08 | **No interpolation by default**; flag required |
| `parent_child_joint_map.csv` as input vs derived | MASTER_PLAN vs 02/08 | **Derive from CSV hierarchy** in V0; heuristic → user validation → optional config freeze later |
| Relative quaternion sign-continuity | MASTER_PLAN §3.2; 02 Stage 06 text not yet explicit | **Resolved:** required in Stage 06 after relative quat computation, before log-map. Sync `02_LAYER2_STAGE_BY_STAGE_IMPLEMENTATION_SPEC.md` + output contract at M0 doc pass |
| Reconstruction test scope | 02 (1 random frame) vs 08 (all joints, 100 frames) | Follow **08**: broad mandatory test, `max_error_deg <= 1e-5` default |
| Reconstruction report filename | 02 vs 08 | Use **`relative_rotation_reconstruction_report.csv`** |
| Stage numbering in 08 Phase 1 | 08 §11 vs 02 | Follow **02 stage numbers** (00–08); treat 08 Phase 1 as coarse grouping only |
| `layer2_feature_table_continuous.parquet` location | MASTER_PLAN flat vs stage tree | Emit at **output root** (or `08_filtering/`) and document in `layer2_metadata.json` |
| matplotlib required vs optional | 06 vs 08 §10 | **Required** — PNG plots are contract outputs |
| Notebooks | MASTER_PLAN §6 | **Out of scope for V0** standalone package; optional later wrapper notebook |
| Near-zero norm threshold | mentioned, not numeric | **Needs validation** (e.g. `norm < 1e-8`) |
| "Many invalid quaternions" stop threshold | 04 stop condition | **Needs validation** (count/% threshold) |
| Distal exclusion keywords | listed heuristically | **Needs user validation** on real Gaga skeleton export |
| Toe inclusion/exclusion | configurable per docs | **Needs validation** for 19-joint body set vs foot endpoints |
| Root bone handling | exclude from relative joints by default | **Needs validation** whether Pelvis/Chest trunk joint is desired |
| Sample Motive CSV | referenced but **not present in repo** | **Needs user to provide** representative file before Milestone 1 |
| Subject prefix pattern | `split(':')[-1]` | **Needs validation** if exports use non-colon prefixes |
| Sampling rate source of truth | Time column vs metadata | Derive from Time, cross-check metadata; **flag mismatch** |

### Staged implementation milestones

**Milestone 0 — Project skeleton (no algorithms)**

- `pyproject.toml`, `src/layer2_motive/` empty modules, `configs/`, `tests/` skeleton, `docs/`, README
- Output directory contract helpers and `assumptions_log.md` template
- **Stop for review**

**Milestone 1 — Parser & structure (Stages 00–01)**

- Manual header parse, metadata detection, flat column map, bone rotation grouping
- Hierarchy table, prefix stripping, Root handling, distal exclusion heuristics → `candidate_joint_map.csv`, `excluded_distal_bones.csv`
- Synthetic header unit tests
- **Stop for review** — requires real Motive CSV from user

**Milestone 2 — Component order & timing (Stages 02–03)**

- Component-order + SciPy compatibility report (conservative language)
- Frame/time load, monotonicity, sampling rate inference, timing plot
- **Stop for review**

**Milestone 3 — Quaternion safety (Stages 04–05)**

- Missing/invalid/zero-norm detection, gap reports, default **stop** (no interpolation)
- Normalization, global sign-continuity (vectorized)
- **Stop for review**

**Milestone 4 — Relative rotations (Stage 06)**

- SciPy relative quat computation for selected joints
- **Relative quaternion sign-continuity** (per joint, before any log-map)
- Broad reconstruction test (all joints, ≥100 frames)
- Export `relative_joint_quaternions.parquet` (post sign-continuity)
- **Stop for review**

**Milestone 5 — Features & filtering (Stages 07–08)**

- Log-map, rotvec continuity/jump reports, near-pi flags
- Filter pre-validation, Butterworth sosfiltfilt, full + 2-sec zoom plots
- Final parquet/csv + `layer3_feature_manifest.csv` + `layer2_metadata.json`
- **Stop for review**

**Milestone 6 — Scale to six Part 1 repetitions** (after single-file validation)

- T1/T2/T3 × r1/r2 per MASTER_PLAN priority
- Verify identical feature names/order across runs
- **Stop for review**

---

## Assumptions

(Things implied but not fully specified — will be documented in `assumptions_log.md`, not hidden in code)

- Motive exports use colon-separated subject prefixes strippable via `split(':')[-1]`
- Quaternion component labels are `X, Y, Z, W` matching SciPy `[x,y,z,w]` order (detected, not silently assumed)
- Default filter: 4th-order Butterworth, 10 Hz cutoff, zero-phase `sosfiltfilt`
- V0 joint set = all non-root parent-child pairs minus distal-keyword exclusions
- Root (`Parent == Root`) bones are excluded as relative-joint children unless config overrides
- Reconstruction pass threshold: `max_error_deg <= 1e-5` unless decision log documents relaxation
- Near-pi warning threshold: `pi - 0.10` rad (configurable)
- Gap repair: **disabled** unless `--allow-short-gap-interpolation` is passed
- Relative quaternion sign-continuity: **required** in Stage 06 before log-map (user-confirmed)

---

## Needs validation

Before writing algorithm code, confirm with user/scientist:

1. **Representative Motive mixed CSV** path(s) for Gaga Part 1 — **required before Milestone 1**, not Milestone 0
2. **Distal exclusion rules** — keyword list, toe handling, whether `Hand` stays in body set
3. **Expected joint count/names** for V0 (heuristic output vs fixed 19-joint list)
4. **Near-zero norm threshold** and **invalid-quaternion stop thresholds** (counts/percentages)
5. **Interpolation policy** — confirm default=no interpolation aligns with data quality expectations
6. **Filter parameters** — is 10 Hz / order 4 appropriate for ~120 Hz Gaga captures?
7. **Subject prefix pattern** — verify on real exports
8. **Output layout** — stage subfolders vs flat `layer2_solved_skeleton_kinematics/` (MASTER_PLAN) — propose stage tree + top-level manifest files
9. **Repo naming** — keep current directory name `Layer2_Motive_Kinematics` or rename to `layer2_motive_kinematics`?

---

## Proposed next actions

1. **User reviews this plan** and answers remaining validation items (sample CSV path for M1, distal/toe rules, thresholds)
2. **Milestone 0 only:** scaffold package, `pyproject.toml`, configs, test skeleton, docs templates; **sync spec docs** so Stage 06 explicitly includes relative quaternion sign-continuity (`02`, `03`, `00` pipeline list if needed) — no algorithm code until approved
3. **Organize specs:** optionally move `00_`–`08_` + MASTER_PLAN files into `docs/specs/` with root README pointing to them
4. **Milestone 1:** implement parser against user-provided sample CSV; produce Stage 00–01 reports; stop for validation per [04_AGENT_STOP_AND_VALIDATE_PROTOCOL.md](04_AGENT_STOP_AND_VALIDATE_PROTOCOL.md)
5. **Record decisions** in `docs/DECISION_LOG.md` as each ambiguity is resolved

**Do not proceed to implementation until this plan and open validation items are approved.**
