#!/usr/bin/env bash
# Run Layer 2 Motive pipeline stages (00–08) for one session or batch.
# See scripts/README.md for copy-paste examples.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CONFIG="${LAYER2_CONFIG:-configs/default_layer2_config.yaml}"
OUTPUT_ROOT="${LAYER2_OUTPUT_ROOT:-outputs}"

resolve_cli() {
  if [[ -x "$ROOT/.venv/bin/layer2-motive" ]]; then
    echo "$ROOT/.venv/bin/layer2-motive"
  elif command -v layer2-motive >/dev/null 2>&1; then
    echo "layer2-motive"
  else
    echo "ERROR: layer2-motive not found." >&2
    echo "From repo root: python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'" >&2
    exit 1
  fi
}

safe_output_name() {
  local stem
  stem="$(basename "${1%.csv}")"
  echo "$stem" | sed -E 's/[^A-Za-z0-9._-]+/_/g' | sed -E 's/_+/_/g' | sed -E 's/^_|_$//g'
}

usage() {
  cat <<'EOF'
Usage:
  ./scripts/run_layer2_pipeline.sh full   --input PATH/to/session.csv
  ./scripts/run_layer2_pipeline.sh until    --input PATH/to/session.csv --stage NN
  ./scripts/run_layer2_pipeline.sh stage    --input PATH/to/session.csv --stage NN
  ./scripts/run_layer2_pipeline.sh batch    --input-dir PATH [--pattern '*.csv']
  ./scripts/run_layer2_pipeline.sh export   [--run-pattern SUBSTRING] [--force]

Environment (optional):
  LAYER2_CONFIG       YAML config (default: configs/default_layer2_config.yaml)
  LAYER2_OUTPUT_ROOT  Output root     (default: outputs)

Options for full / until / stage:
  --input PATH        Motive mixed CSV (required)
  --output-dir PATH   Override auto output folder under outputs/
  --stage NN          Required for until/stage (e.g. 03, 07, 08)

Options for batch:
  --input-dir PATH    Directory of CSV files (default: data/671)
  --pattern GLOB      File glob (default: *.csv)

Options for export:
  --run-pattern STR   Filter run folder names (e.g. 671_T1_P1_R1)
  --force             Overwrite existing export folders

Examples:
  ./scripts/run_layer2_pipeline.sh full --input "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv"
  ./scripts/run_layer2_pipeline.sh stage --input "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv" --stage 08
  ./scripts/run_layer2_pipeline.sh batch --input-dir data/671
  ./scripts/run_layer2_pipeline.sh export --run-pattern 671_T1_P1_R1 --force
EOF
}

require_input() {
  if [[ -z "${INPUT:-}" ]]; then
    echo "ERROR: --input is required." >&2
    usage
    exit 1
  fi
  if [[ ! -f "$INPUT" ]]; then
    echo "ERROR: Input CSV not found: $INPUT" >&2
    exit 1
  fi
}

require_stage() {
  if [[ -z "${STAGE:-}" ]]; then
    echo "ERROR: --stage is required (e.g. 08)." >&2
    usage
    exit 1
  fi
}

default_output_dir() {
  echo "$OUTPUT_ROOT/$(safe_output_name "$INPUT")"
}

run_full() {
  require_input
  local out="${OUTPUT_DIR:-$(default_output_dir)}"
  echo "==> run-until --stage 08"
  echo "    input:  $INPUT"
  echo "    output: $out"
  "$CLI" run-until --input "$INPUT" --stage 08 --output-dir "$out" --config "$CONFIG"
}

run_until() {
  require_input
  require_stage
  local out="${OUTPUT_DIR:-$(default_output_dir)}"
  echo "==> run-until --stage $STAGE"
  echo "    input:  $INPUT"
  echo "    output: $out"
  "$CLI" run-until --input "$INPUT" --stage "$STAGE" --output-dir "$out" --config "$CONFIG"
}

run_stage_only() {
  require_input
  require_stage
  local out="${OUTPUT_DIR:-$(default_output_dir)}"
  echo "==> run-stage --stage $STAGE"
  echo "    input:  $INPUT"
  echo "    output: $out"
  "$CLI" run-stage --input "$INPUT" --stage "$STAGE" --output-dir "$out" --config "$CONFIG"
}

run_batch() {
  local input_dir="${INPUT_DIR:-data/671}"
  local pattern="${PATTERN:-*.csv}"
  if [[ ! -d "$input_dir" ]]; then
    echo "ERROR: Input directory not found: $input_dir" >&2
    exit 1
  fi
  echo "==> batch-run (stages 00–01) on $input_dir"
  "$CLI" batch-run --input-dir "$input_dir" --pattern "$pattern" --output-root "$OUTPUT_ROOT" --force --config "$CONFIG"
  for s in 02 03 04 05 06 07 08; do
    echo "==> batch-run-stage$s on $input_dir"
    "$CLI" "batch-run-stage$s" --input-dir "$input_dir" --pattern "$pattern" --output-root "$OUTPUT_ROOT" --force --config "$CONFIG"
  done
}

run_export() {
  local extra=()
  [[ -n "${RUN_PATTERN:-}" ]] && extra+=(--run-pattern "$RUN_PATTERN")
  [[ "${FORCE:-0}" -eq 1 ]] && extra+=(--force)
  echo "==> export-layer2-sessions"
  "$CLI" export-layer2-sessions --output-root "$OUTPUT_ROOT" --export-root "$OUTPUT_ROOT/layer2_exports" "${extra[@]}"
}

# --- parse globals ---
CLI="$(resolve_cli)"
MODE="${1:-}"
shift || true

INPUT=""
OUTPUT_DIR=""
STAGE=""
INPUT_DIR=""
PATTERN=""
RUN_PATTERN=""
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --stage) STAGE="$2"; shift 2 ;;
    --input-dir) INPUT_DIR="$2"; shift 2 ;;
    --pattern) PATTERN="$2"; shift 2 ;;
    --run-pattern) RUN_PATTERN="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

case "$MODE" in
  full) run_full ;;
  until) run_until ;;
  stage) run_stage_only ;;
  batch|batch-all) run_batch ;;
  export) run_export ;;
  ""|-h|--help|help) usage ;;
  *)
    echo "ERROR: Unknown mode: $MODE" >&2
    usage
    exit 1
    ;;
esac

echo "Done."
