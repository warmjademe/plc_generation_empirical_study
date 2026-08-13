#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT=/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes
METHOD="$SOURCE_ROOT/our_method"
RQ2="$SOURCE_ROOT/RQ2"
DATASET="$SOURCE_ROOT/datasets_100"
CALIBRATION="$DATASET/evidence/exact_revalidation/calibration_summary.json"
KEY_FILE=/home/qyb/.config/plc-evidence-loop/deepseek_api_key
M01_CONFIG="$METHOD/configs/deepseek_v4_flash_rq2_M01_without_component_1.json"
M10_CONFIG="$METHOD/configs/deepseek_v4_flash_rq2_M10_without_component_2.json"
M01_OUTPUT="$METHOD/runs/rq2_M01_without_component_1_deepseek_v4_flash_datasets100_20260813_v1"
M10_OUTPUT="$METHOD/runs/rq2_M10_without_component_2_deepseek_v4_flash_datasets100_20260813_v1"
M01_LOG="$RQ2/M01.controller.log"
M10_LOG="$RQ2/M10.controller.log"
CONTROLLER_LOG="$RQ2/controller.log"
WORKERS_PER_ARM=6

umask 077
mkdir -p "$RQ2"
exec >>"$CONTROLLER_LOG" 2>&1
echo "$(date -Is) RQ2 controller started"

python3 - "$CALIBRATION" "$M01_CONFIG" "$M10_CONFIG" <<'PY'
import hashlib
import json
import sys

calibration = json.load(open(sys.argv[1], encoding="utf-8"))
if not (
    calibration.get("success") is True
    and calibration.get("task_count") == 100
    and calibration.get("pass_count") == 100
):
    raise SystemExit("Balanced-100 exact reference calibration is not 100/100 pass")

def digest_validators(path):
    document = json.load(open(path, encoding="utf-8"))
    encoded = json.dumps(
        document["validators"], ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), document

expected_hash, _ = digest_validators(
    "/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/"
    "source_codes/datasets_100/evidence/exact_revalidation/validator_config.json"
)
expected = {
    "M01_without_component_1": (False, True),
    "M10_without_component_2": (True, False),
}
for path in sys.argv[2:]:
    observed_hash, document = digest_validators(path)
    if observed_hash != expected_hash:
        raise SystemExit(f"validator configuration drift: {path}")
    experiment = document["experiment"]
    ablation = experiment.get("ablation_id")
    flags = (
        experiment.get("core_component_1_enabled"),
        experiment.get("core_component_2_enabled"),
    )
    if expected.get(ablation) != flags:
        raise SystemExit(f"invalid ablation flags: {path}: {ablation} {flags}")
    if document["provider"].get("requested_model") != "deepseek-v4-flash":
        raise SystemExit(f"model drift: {path}")
PY

if [[ ! -s "$KEY_FILE" ]]; then
  echo "$(date -Is) private DeepSeek key file is missing"
  exit 3
fi
export DEEPSEEK_API_KEY
DEEPSEEK_API_KEY=$(<"$KEY_FILE")
export PYTHONPATH="$METHOD/src"

python3 "$METHOD/scripts/run_method_batch.py" \
  --config "$M01_CONFIG" \
  --dataset-root "$DATASET" \
  --output "$M01_OUTPUT" \
  --method raw_repair \
  --workers "$WORKERS_PER_ARM" >"$M01_LOG" 2>&1 &
M01_PID=$!

python3 "$METHOD/scripts/run_method_batch.py" \
  --config "$M10_CONFIG" \
  --dataset-root "$DATASET" \
  --output "$M10_OUTPUT" \
  --method evidence \
  --workers "$WORKERS_PER_ARM" >"$M10_LOG" 2>&1 &
M10_PID=$!

printf '%s\n' "$M01_PID" >"$RQ2/M01.pid"
printf '%s\n' "$M10_PID" >"$RQ2/M10.pid"
echo "$(date -Is) launched M01=$M01_PID M10=$M10_PID workers_per_arm=$WORKERS_PER_ARM"

status=0
wait "$M01_PID" || status=1
echo "$(date -Is) M01 exited"
wait "$M10_PID" || status=1
echo "$(date -Is) M10 exited"
unset DEEPSEEK_API_KEY

if [[ "$status" -ne 0 ]]; then
  echo "$(date -Is) at least one RQ2 arm failed"
  exit "$status"
fi
echo "$(date -Is) RQ2 controller completed"
