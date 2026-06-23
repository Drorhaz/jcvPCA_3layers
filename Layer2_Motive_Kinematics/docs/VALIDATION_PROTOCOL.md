# Layer 2 Validation Protocol

## Stage gates

Follow [`04_AGENT_STOP_AND_VALIDATE_PROTOCOL.md`](../04_AGENT_STOP_AND_VALIDATE_PROTOCOL.md) at repository root.

After each stage:

1. Write all required reports and plots under `outputs/NN_*/`
2. Update `outputs/assumptions_log.md`
3. Run **Kinematics Reviewer** (see `docs/KINEMATICS_REVIEWER_PROMPT.md`)
4. Optional: adapted **ARA Rigor** pass (see `docs/REVIEW_WORKFLOW.md`)
5. Scientist validates listed checkpoints before the next stage

## Reviewers

| Reviewer | When | Document |
|----------|------|----------|
| Kinematics Reviewer | Every stage gate | `docs/KINEMATICS_REVIEWER_PROMPT.md` |
| ARA Rigor (optional) | Stages 04, 06, 08 | `docs/REVIEW_WORKFLOW.md` |

## Evidence categories

All reviews must separate:

- Known from inspected files
- Known from project documentation
- Assumptions
- Risks
- Required tests
- Stop conditions
- Recommended changes

## Config validation

Provisional thresholds in `configs/default_layer2_config.yaml` marked `VALIDATION_REQUIRED` must be confirmed before Stage 04 on a representative Motive CSV.

## Feature selection boundary

Stage 00–01 documents native skeleton structure and writes provisional joint maps (`frozen = false`).
Final analysis feature selection for Layer 3 happens **after** Layer 2 output validation and **before** Layer 3.

Provisional Stage 01 artifacts (not final, not Layer 3-ready):

- `selected_joint_map_v0.csv` — heuristic preview (`frozen = false`)
- `selected_body_bones.csv` — provisional convenience subset only; **not** the final body joint set

See [`FEATURE_SELECTION_BOUNDARY.md`](FEATURE_SELECTION_BOUNDARY.md) and [`DECISION_LOG.md`](DECISION_LOG.md) (D005–D009).
