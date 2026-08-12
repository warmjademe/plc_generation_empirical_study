#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT=${SOURCE_ROOT:-/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes}
DATASET=${DATASET:-$SOURCE_ROOT/datasets_100}
QUALIFICATION=${QUALIFICATION:-$DATASET/evidence/exact_revalidation/calibration_summary.json}
CONFIG=${CONFIG:-$SOURCE_ROOT/our_method/configs/codex_gpt_5_6_luna_external_baseline.json}
OUTPUT=${OUTPUT:-$SOURCE_ROOT/RQ1/runs/baseline5_codex_gpt_5_6_luna_datasets100_independent_pass_at_10_v2}
WORKERS=${WORKERS:-4}
TEAMOROUTER_KEY_FILE=${TEAMOROUTER_KEY_FILE:-$HOME/.config/plc-evidence-loop/teamorouter_api_key}

for required in "$DATASET/manifest.jsonl" "$QUALIFICATION" "$CONFIG" "$TEAMOROUTER_KEY_FILE"; do
  if [[ ! -s "$required" ]]; then
    echo "missing required input: $required" >&2
    exit 2
  fi
done

if [[ -d "$OUTPUT" ]] && find "$OUTPUT" -mindepth 1 -print -quit | grep -q .; then
  echo "refusing non-empty output: $OUTPUT" >&2
  exit 3
fi

export TEAMOROUTER_API_KEY
TEAMOROUTER_API_KEY=$(<"$TEAMOROUTER_KEY_FILE")
exec python3 "$SOURCE_ROOT/baseline5_codex.py" \
  --config "$CONFIG" \
  --dataset-root "$DATASET" \
  --qualification "$QUALIFICATION" \
  --output "$OUTPUT" \
  --workers "$WORKERS"
