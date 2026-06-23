# Layer 2 Motive Kinematics

Independent **Layer 2** pipeline: Motive-solved **global bone quaternions** → filtered **parent-child relative rotation-vector features** (`joint_rx`, `joint_ry`, `joint_rz`) for later Layer 3 JcvPCA analysis.

**Not in scope:** Layer 1 imports, Layer 3 (PCA/JcvPCA/segmentation), validated anatomical joint angles.

## Specification (source of truth)

Numbered specs remain at repository root:

| Priority | Document |
|----------|----------|
| 1 | `08_LAYER2_SPEC_V5_1_CORRECTION_ADDENDUM.md` |
| 2 | `00`–`07` Layer 2 v5 files |
| 3 | `MASTER_PLAN_V5_1_CURSOR_SCOPE_ADDENDUM.md` |
| 4 | `MASTER_PLAN.md` |

Start with [`00_README_LAYER2_OVERVIEW.md`](00_README_LAYER2_OVERVIEW.md).

## Project layout

```text
Layer2_Motive_Kinematics/
  src/layer2_motive/     # Python package (stubs in Milestone 0)
  configs/               # default_layer2_config.yaml + templates
  docs/                  # scope, validation, reviewers
  tests/                 # pytest skeleton
  outputs/               # generated run artifacts (gitignored except .gitkeep)
  examples/              # usage notes (no sample data in repo)
```

## Milestone status

- **Milestone 0:** project skeleton, configs, docs, test placeholders.
- **Milestone 1:** Stage 00–01 parser, provisional joint maps, structural population reports.
- **Milestone 2+:** quaternion convention, timing, QC, relative features, filtering.

## Development (after dependencies are installed)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest
ruff check src tests
```

**Run the pipeline:** see [`scripts/README.md`](scripts/README.md) for copy-paste commands and `./scripts/run_layer2_pipeline.sh`.

```bash
layer2-motive run-until --input /path/to/motive.csv --stage 08 --output-dir outputs/session_name
layer2-motive batch-run --input-dir data --output-root outputs --index outputs/stage00_01_report_index
```

See [`docs/FEATURE_SELECTION_BOUNDARY.md`](docs/FEATURE_SELECTION_BOUNDARY.md) for how provisional
joint maps relate to final Layer 3 feature selection.

## Review workflow

See [`docs/REVIEW_WORKFLOW.md`](docs/REVIEW_WORKFLOW.md) and [`docs/KINEMATICS_REVIEWER_PROMPT.md`](docs/KINEMATICS_REVIEWER_PROMPT.md).

## Scientific framing

```text
filtered parent-child relative rotation-vector features derived from Motive-solved global bone quaternions
```
