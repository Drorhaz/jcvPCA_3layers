# Assumptions Log Template

Copy to `outputs/assumptions_log.md` at the start of each pipeline run.

## Run metadata

- input_csv:
- output_dir:
- config_file:
- stage:

## Assumptions

| ID | Assumption | Source | Validation status |
|----|------------|--------|-------------------|
| A001 | | detected / config / user | pending / validated / rejected |

## Example entries (delete when running)

```text
Assumption A001: Coordinate Space detected as Global from metadata row.
Assumption A002: Quaternion source order detected as X/Y/Z/W for SciPy [x,y,z,w].
Assumption A003: Subject prefixes stripped via colon_suffix rule.
Assumption A004: Distal exclusion heuristics applied; awaiting scientist validation.
Assumption A005: Relative sign-continuity applied in Stage 06 before log-map.
Assumption A006: Gap interpolation disabled (default).
```

## Interpolation / repairs

Record every repair explicitly:

| joint_or_bone | frames | method | logged_in |
|---------------|--------|--------|-----------|

## Excluded joints / bones

Reference `excluded_distal_bones.csv` and note scientist sign-off.
