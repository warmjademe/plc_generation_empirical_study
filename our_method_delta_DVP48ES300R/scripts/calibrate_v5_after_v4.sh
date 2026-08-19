#!/usr/bin/env bash
set -euo pipefail

METHOD=/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes/our_method
DATASET=/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes/datasets_50
V4_OUTPUT="$METHOD/runs/egbs_deepseek_v4_flash_agentic_context_v4_datasets50_20260811"
V5_CONFIG="$METHOD/configs/deepseek_v4_flash_agentic_context_v5.json"
STAGED_RUNNER="$METHOD/scripts/openplc_container_runner.v5.py"
STAGED_TEST="$METHOD/tests/harness_v5.staged.py"
CALIBRATION="$METHOD/runs/calibration_agentic_context_v5_full50_20260812"
V5_OUTPUT="$METHOD/runs/egbs_deepseek_v4_flash_agentic_context_v5_datasets50_20260812"
SECRET_ENV=/home/qyb/.config/agents4plc/deepseek.env
LOG="$METHOD/runs/calibration_agentic_context_v5_full50_20260812.controller.log"

exec >>"$LOG" 2>&1
echo "$(date -Is) waiting for v4 batch"
while python3 - "$V4_OUTPUT" <<'PY'
import os, sys
needle=sys.argv[1]
for name in os.listdir('/proc'):
    if not name.isdigit():
        continue
    try:
        cmd=open(f'/proc/{name}/cmdline','rb').read().replace(b'\0',b' ').decode('utf-8','replace')
    except OSError:
        continue
    if 'run_method_batch.py' in cmd and needle in cmd:
        raise SystemExit(0)
raise SystemExit(1)
PY
do
  sleep 30
done

if [[ ! -f "$V4_OUTPUT/batch_summary.json" ]]; then
  echo "$(date -Is) v4 process ended without batch_summary.json; refusing calibration"
  exit 2
fi
if [[ ! -f "$STAGED_RUNNER" ]]; then
  echo "$(date -Is) staged v5 OpenPLC runner is missing"
  exit 4
fi
install -m 755 "$STAGED_RUNNER" "$METHOD/scripts/openplc_container_runner.py"
if [[ -f "$STAGED_TEST" ]]; then
  install -m 644 "$STAGED_TEST" "$METHOD/tests/test_harness.py"
fi
echo "$(date -Is) promoted v5 OpenPLC visible-prefix runner"
if [[ -d "$CALIBRATION" ]] && find "$CALIBRATION" -mindepth 1 -print -quit | grep -q .; then
  echo "$(date -Is) non-empty calibration output already exists; refusing overwrite"
  exit 3
fi

echo "$(date -Is) starting v5 reference calibration"
export PYTHONPATH="$METHOD/src"
python3 "$METHOD/scripts/calibrate_method_config.py" \
  --config "$V5_CONFIG" \
  --dataset-root "$DATASET" \
  --output "$CALIBRATION" \
  --workers 12
echo "$(date -Is) v5 reference calibration completed"

python3 - "$CALIBRATION/calibration_summary.json" <<'PY'
import json, sys
value=json.load(open(sys.argv[1], encoding='utf-8'))
if value.get('task_count') != 50 or value.get('pass_count') != 50 or value.get('success') is not True:
    raise SystemExit('v5 calibration did not pass all 50 reference programs')
PY

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
if [[ -d "$V5_OUTPUT" ]] && find "$V5_OUTPUT" -mindepth 1 -print -quit | grep -q .; then
  echo "$(date -Is) non-empty v5 output already exists; refusing overwrite"
  exit 7
fi

echo "$(date -Is) starting five-task v5 mechanism pilot"
python3 "$METHOD/scripts/run_method_batch.py" \
  --config "$V5_CONFIG" \
  --dataset-root "$DATASET" \
  --output "$V5_OUTPUT" \
  --method evidence \
  --workers 5 \
  --include C01_B04_composite \
  --include C03_B08_composite \
  --include C04_S08_lean_composite \
  --include C05_B03_composite \
  --include C06_W07_lean_composite
cp "$V5_OUTPUT/batch_summary.json" "$V5_OUTPUT/pilot_summary.json"
echo "$(date -Is) pilot completed; resuming the same immutable task runs into full50"
python3 "$METHOD/scripts/run_method_batch.py" \
  --config "$V5_CONFIG" \
  --dataset-root "$DATASET" \
  --output "$V5_OUTPUT" \
  --method evidence \
  --workers 12
echo "$(date -Is) v5 full50 completed"
