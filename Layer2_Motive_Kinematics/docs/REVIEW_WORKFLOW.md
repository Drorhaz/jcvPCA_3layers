# Layer 2 Review Workflow

## Purpose

Separate **domain-correct kinematics** from **research/documentation rigor**. No reviewer replaces project specifications, inspected files, or explicit user decisions.

## Document authority

When documents conflict:

1. `08_LAYER2_SPEC_V5_1_CORRECTION_ADDENDUM.md`
2. Layer 2 specification files `00`–`07`
3. `MASTER_PLAN_V5_1_CURSOR_SCOPE_ADDENDUM.md`
4. `MASTER_PLAN.md`

## Reviewers

### Primary — Kinematics Reviewer

**Source:** [`KINEMATICS_REVIEWER_PROMPT.md`](KINEMATICS_REVIEWER_PROMPT.md)

**Use for:** quaternion handling, parent-child relative rotations, relative sign-continuity (Stage 06), rotation-vector conversion, filtering safety, Motive parser boundaries, Layer 2 vs Layer 3 scope, stage stop conditions.

**Required on:** every stage gate before proceeding (per `04_AGENT_STOP_AND_VALIDATE_PROTOCOL.md`).

**Output sections:** Known from inspected files · Known from project docs · Assumptions · Risks · Required tests · Stop conditions · Recommended changes · Proceed / revise / stop.

### Secondary (optional) — ARA Rigor Reviewer

**Source:** External skill `ara-rigor-reviewer` from [orchestra-research/AI-research-SKILLs](https://github.com/orchestra-research/AI-research-SKILLs) (`22-agent-native-research-artifact/rigor-reviewer/`). Install manually if used; do not install the full 98-skill library.

**Use for:** evidence discipline, falsifiability of stop conditions, scope/overclaiming checks, assumption explicitness, whether written reports support stated conclusions.

**Do NOT use for:** biomechanics, quaternion math, Motive CSV structure, code correctness, or replacing the Kinematics Reviewer.

**Adapted mode only:** Review stage reports and `outputs/assumptions_log.md`; do not require a full ARA directory.

**Suggested on:** Stages 04, 06, 08, or before milestone sign-off — **after** Kinematics Reviewer.

## Review order

1. Implement stage → write reports to `outputs/NN_*/`
2. **Kinematics Reviewer** (mandatory)
3. **ARA Rigor Reviewer** (optional, methodological pass)
4. Scientist validation per `04_AGENT_STOP_AND_VALIDATE_PROTOCOL.md`
5. Proceed to next stage only if stop conditions are clear

## Evidence rules (all reviewers)

All conclusions must separate:

- known evidence from inspected files
- known evidence from project documentation
- assumptions
- risks
- required tests
- stop conditions
- recommended changes

Reviewers must not invent Motive structure, bone names, thresholds, or scientific claims. Mark unknowns as **Needs validation**.

## Dispute resolution

- Kinematics/math/filter conflicts → Kinematics Reviewer + specs win
- Overclaiming / undocumented assumptions → ARA Rigor findings + specs win
- Neither reviewer authorizes skipping human stage validation
