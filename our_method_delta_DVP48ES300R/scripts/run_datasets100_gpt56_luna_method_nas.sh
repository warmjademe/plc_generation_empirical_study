#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT=/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes
METHOD="$SOURCE_ROOT/our_method"
DATASET="$SOURCE_ROOT/datasets_100"
CONFIG="$METHOD/configs/teamorouter_gpt_5_6_luna_agentic_context_v5_2.json"
CALIBRATION="$DATASET/evidence/exact_revalidation/calibration_summary.json"
OUTPUT="$METHOD/runs/egbs_gpt_5_6_luna_agentic_context_v5_2_datasets100_20260812_v1"
KEY_FILE=/home/qyb/.config/plc-evidence-loop/teamorouter_api_key
LOG="$METHOD/runs/egbs_gpt_5_6_luna_agentic_context_v5_2_datasets100_20260812_v1.controller.log"
WORKERS=12

umask 077
exec >>"$LOG" 2>&1
echo "$(date -Is) datasets100 GPT-5.6 Luna method controller started"

for required in "$DATASET/manifest.jsonl" "$CALIBRATION" "$CONFIG" "$KEY_FILE"; do
  if [[ ! -s "$required" ]]; then
    echo "$(date -Is) missing required input: $required"
    exit 2
  fi
done

python3 - "$CALIBRATION" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf-8"))
if summary.get("success") is not True or summary.get("task_count") != 100 or summary.get("pass_count") != 100:
    raise SystemExit("reference calibration did not pass 100/100 tasks")
PY
echo "$(date -Is) exact reference calibration passed 100/100"

if [[ -d "$OUTPUT" ]] && find "$OUTPUT" -mindepth 1 -print -quit | grep -q .; then
  echo "$(date -Is) refusing non-empty output: $OUTPUT"
  exit 3
fi

export TEAMOROUTER_API_KEY
TEAMOROUTER_API_KEY=$(<"$KEY_FILE")
export PYTHONPATH="$METHOD/src"

echo "$(date -Is) starting datasets100 GPT-5.6 Luna method run workers=$WORKERS"
python3 "$METHOD/scripts/run_method_batch.py" \
  --config "$CONFIG" \
  --dataset-root "$DATASET" \
  --output "$OUTPUT" \
  --method evidence \
  --workers "$WORKERS"
unset TEAMOROUTER_API_KEY
echo "$(date -Is) datasets100 GPT-5.6 Luna method run finished"
