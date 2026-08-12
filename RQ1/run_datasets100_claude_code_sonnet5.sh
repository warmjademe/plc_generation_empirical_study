#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT=${PLC_SOURCE_ROOT:-/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes}
DATASET=${PLC_DATASET_ROOT:-$SOURCE_ROOT/datasets_100}
QUALIFICATION=${PLC_QUALIFICATION:-$DATASET/evidence/exact_revalidation/calibration_summary.json}
CONFIG=${PLC_BASELINE4_CONFIG:-$SOURCE_ROOT/our_method/configs/claude_code_sonnet5_external_baseline.json}
OUTPUT=${PLC_BASELINE4_OUTPUT:-$SOURCE_ROOT/RQ1/runs/baseline4_claude_code_sonnet5_datasets100}
WORKERS=${PLC_BASELINE4_WORKERS:-2}

for required in "$DATASET/manifest.jsonl" "$QUALIFICATION" "$CONFIG"; do
  if [[ ! -s "$required" ]]; then
    echo "missing required input: $required" >&2
    exit 2
  fi
done

if ! command -v claude >/dev/null 2>&1; then
  echo "Claude Code CLI is not installed or is absent from PATH" >&2
  exit 2
fi

python3 "$SOURCE_ROOT/baseline4_claude_code.py" \
  --config "$CONFIG" \
  --dataset-root "$DATASET" \
  --qualification "$QUALIFICATION" \
  --output "$OUTPUT" \
  --workers "$WORKERS"
