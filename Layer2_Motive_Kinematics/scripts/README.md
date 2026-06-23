# Layer 2 pipeline — run commands

Copy-paste commands for running stages **00–08** on Motive CSV sessions.

**Prerequisite** (once per machine, from repo root):

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

After that, either keep the venv activated or use `.venv/bin/layer2-motive` / the helper script below.

---

## Helper script (recommended)

From repo root:

```bash
chmod +x scripts/run_layer2_pipeline.sh   # once
./scripts/run_layer2_pipeline.sh --help
```

### One session — full pipeline (00 → 08)

```bash
./scripts/run_layer2_pipeline.sh full --input "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv"
```

Output folder is chosen automatically:

`outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001`

### One session — run up to a stage (00 → NN)

```bash
./scripts/run_layer2_pipeline.sh until --input "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv" --stage 06
```

### One session — single stage only

Re-run Stage 07 then 08 after a config change:

```bash
./scripts/run_layer2_pipeline.sh stage --input "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv" --stage 07
./scripts/run_layer2_pipeline.sh stage --input "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv" --stage 08
```

### All CSVs in a folder — full batch

```bash
./scripts/run_layer2_pipeline.sh batch --input-dir data/671
```

### Export Layer 2 session bundles (after Stage 08)

```bash
./scripts/run_layer2_pipeline.sh export --force
```

Filter one subject/session:

```bash
./scripts/run_layer2_pipeline.sh export --run-pattern 671_T1_P1_R1 --force
```

---

## Direct CLI (copy-paste)

Use **one line** per command (avoids `\` line-continuation bugs).  
If `\` must be last on the line — **no spaces after it**.

Set paths once:

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics
source .venv/bin/activate

INPUT="data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv"
OUT="outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001"
CFG="configs/default_layer2_config.yaml"
```

### Full pipeline (00 → 08)

```bash
layer2-motive run-until --input "$INPUT" --stage 08 --output-dir "$OUT" --config "$CFG"
```

Or without variables:

```bash
layer2-motive run-until --input "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv" --stage 08 --output-dir outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001 --config configs/default_layer2_config.yaml
```

### Partial — run from 00 up to stage NN

| Goal | Command |
|------|---------|
| Through joint mapping (01) | `layer2-motive run-until --input "$INPUT" --stage 01 --output-dir "$OUT" --config "$CFG"` |
| Through timing QC (03) | `layer2-motive run-until --input "$INPUT" --stage 03 --output-dir "$OUT" --config "$CFG"` |
| Through relative quats (06) | `layer2-motive run-until --input "$INPUT" --stage 06 --output-dir "$OUT" --config "$CFG"` |
| Through rotvecs + QC (07) | `layer2-motive run-until --input "$INPUT" --stage 07 --output-dir "$OUT" --config "$CFG"` |
| Through filtering (08) | `layer2-motive run-until --input "$INPUT" --stage 08 --output-dir "$OUT" --config "$CFG"` |

### Partial — one stage only

```bash
layer2-motive run-stage --input "$INPUT" --stage 07 --output-dir "$OUT" --config "$CFG"
layer2-motive run-stage --input "$INPUT" --stage 08 --output-dir "$OUT" --config "$CFG"
```

Stage IDs: `00` parse · `01` joints · `02` component order · `03` frame/time · `04` quaternion QC · `05` sign continuity · `06` relative quats · `07` rotation vectors · `08` filtering

### Batch — all files in `data/671`

Run in order (`--force` re-runs existing outputs):

```bash
layer2-motive batch-run --input-dir data/671 --output-root outputs --force --config configs/default_layer2_config.yaml
layer2-motive batch-run-stage02 --input-dir data/671 --output-root outputs --force --config configs/default_layer2_config.yaml
layer2-motive batch-run-stage03 --input-dir data/671 --output-root outputs --force --config configs/default_layer2_config.yaml
layer2-motive batch-run-stage04 --input-dir data/671 --output-root outputs --force --config configs/default_layer2_config.yaml
layer2-motive batch-run-stage05 --input-dir data/671 --output-root outputs --force --config configs/default_layer2_config.yaml
layer2-motive batch-run-stage06 --input-dir data/671 --output-root outputs --force --config configs/default_layer2_config.yaml
layer2-motive batch-run-stage07 --input-dir data/671 --output-root outputs --force --config configs/default_layer2_config.yaml
layer2-motive batch-run-stage08 --input-dir data/671 --output-root outputs --force --config configs/default_layer2_config.yaml
```

### Export for segmentation notebook

```bash
layer2-motive export-layer2-sessions --output-root outputs --export-root outputs/layer2_exports --force
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found: layer2-motive` | `source .venv/bin/activate` or use `.venv/bin/layer2-motive` |
| `unrecognized arguments:` (empty) | Remove trailing spaces after `\` on continued lines; use one-line commands |
| `run-all` fails | Not implemented — use `run-until --stage 08` instead |
| Arrow `sysctlbyname` warnings | Harmless on macOS; pipeline can still succeed |

---

## Where outputs go

```text
outputs/<session_name>/
  00_parse/ … 08_filtered_rotvecs/
outputs/layer2_exports/<session_name>/   # after export
```

Reports to check after a full run:

- `07_rotation_vectors/report.md`
- `08_filtered_rotvecs/report.md`
- `08_filtered_rotvecs/assumptions_and_limitations.md`
