#!/usr/bin/env bash
set -euo pipefail

METHOD=/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes/our_method
DATASET=/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes/datasets_50
CONFIG="$METHOD/configs/deepseek_v4_flash_agentic_context_v5_2.json"
CALIBRATION="$METHOD/runs/calibration_agentic_context_v5_2_full50_20260812"
OUTPUT="$METHOD/runs/egbs_deepseek_v4_flash_agentic_context_v5_2_datasets50_20260812"
SECRET_ENV=/home/qyb/.config/agents4plc/deepseek.env
LOG="$METHOD/runs/calibration_agentic_context_v5_2_full50_20260812.controller.log"

exec >>"$LOG" 2>&1
echo "$(date -Is) validating v5.2 harness"
export PYTHONPATH="$METHOD/src"
python3 -m unittest discover -s "$METHOD/tests" -p 'test_harness.py' -v

if [[ -d "$CALIBRATION" ]] && find "$CALIBRATION" -mindepth 1 -print -quit | grep -q .; then
  echo "$(date -Is) non-empty calibration output already exists; refusing overwrite"
  exit 3
fi
if [[ -d "$OUTPUT" ]] && find "$OUTPUT" -mindepth 1 -print -quit | grep -q .; then
  echo "$(date -Is) non-empty experiment output already exists; refusing overwrite"
  exit 4
fi

echo "$(date -Is) starting exact 50-task reference calibration"
python3 "$METHOD/scripts/calibrate_method_config.py" \
  --config "$CONFIG" \
  --dataset-root "$DATASET" \
  --output "$CALIBRATION" \
  --workers 12

python3 - "$CALIBRATION/calibration_summary.json" <<'PY'
import json, sys
value=json.load(open(sys.argv[1], encoding='utf-8'))
if value.get('task_count') != 50 or value.get('pass_count') != 50 or value.get('success') is not True:
    raise SystemExit('v5.2 calibration did not pass all 50 reference programs')
PY
echo "$(date -Is) v5.2 reference calibration passed 50/50"

if [[ ! -f "$SECRET_ENV" ]]; then
  echo "$(date -Is) private DeepSeek environment file is missing"
  exit 5
fi
set -a
# shellcheck disable=SC1090
source "$SECRET_ENV"
set +a
if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "$(date -Is) DEEPSEEK_API_KEY is missing from the private environment"
  exit 6
fi

echo "$(date -Is) starting five-task v5.2 mechanism pilot"
python3 "$METHOD/scripts/run_method_batch.py" \
  --config "$CONFIG" \
  --dataset-root "$DATASET" \
  --output "$OUTPUT" \
  --method evidence \
  --workers 5 \
  --include C01_B04_composite \
  --include C03_B08_composite \
  --include C04_S08_lean_composite \
  --include C05_B03_composite \
  --include C06_W07_lean_composite
cp "$OUTPUT/batch_summary.json" "$OUTPUT/pilot_summary.json"

echo "$(date -Is) pilot completed; resuming immutable task runs into full50"
python3 "$METHOD/scripts/run_method_batch.py" \
  --config "$CONFIG" \
  --dataset-root "$DATASET" \
  --output "$OUTPUT" \
  --method evidence \
  --workers 12
echo "$(date -Is) v5.2 full50 completed"
