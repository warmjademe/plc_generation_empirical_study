#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT=${SOURCE_ROOT:-/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes}
METHOD=$SOURCE_ROOT/our_method
DATASET=$SOURCE_ROOT/datasets_100
CONFIG=$METHOD/configs/teamorouter_claude_sonnet5_agentic_context_v5_2.json
CALIBRATION=$DATASET/evidence/exact_revalidation/calibration_summary.json
RUN_ROOT=$SOURCE_ROOT/RQ1/runs
BASELINE_RUN_TAG=${BASELINE_RUN_TAG:-20260812_v4_independent_pass_at_10}
BASELINE5_SUMMARY=$RUN_ROOT/baseline5_codex_gpt_5_6_luna_datasets100_$BASELINE_RUN_TAG/baseline_summary.json
BASELINE4_SUMMARY=$RUN_ROOT/baseline4_claude_code_sonnet5_datasets100_$BASELINE_RUN_TAG/baseline_summary.json
OUTPUT=${OUTPUT:-$METHOD/runs/egbs_claude_sonnet_5_agentic_context_v5_2_datasets100_20260812_v1}
KEY_FILE=${KEY_FILE:-$HOME/.config/plc-evidence-loop/teamorouter_api_key}
LOG=${LOG:-$METHOD/runs/egbs_claude_sonnet_5_agentic_context_v5_2_datasets100_20260812_v1.controller.log}
WORKERS=${WORKERS:-12}
WAIT_CONTROLLER_PID=${WAIT_CONTROLLER_PID:-}
POLL_SECONDS=${POLL_SECONDS:-30}

umask 077
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1
echo "$(date -Is) Sonnet 5 method successor started; wait_pid=${WAIT_CONTROLLER_PID:-none}"

for value in "$WORKERS" "$POLL_SECONDS"; do
  if ! [[ "$value" =~ ^[1-9][0-9]*$ ]]; then
    echo "$(date -Is) WORKERS and POLL_SECONDS must be positive integers"
    exit 2
  fi
done

if [[ -n "$WAIT_CONTROLLER_PID" ]]; then
  if ! [[ "$WAIT_CONTROLLER_PID" =~ ^[1-9][0-9]*$ ]]; then
    echo "$(date -Is) WAIT_CONTROLLER_PID must be a positive integer"
    exit 2
  fi
  while kill -0 "$WAIT_CONTROLLER_PID" 2>/dev/null; do
    command_line=$(tr '\0' ' ' <"/proc/$WAIT_CONTROLLER_PID/cmdline" 2>/dev/null || true)
    if [[ "$command_line" != *run_baseline5_then_baseline4_nas.sh* ]]; then
      echo "$(date -Is) PID $WAIT_CONTROLLER_PID no longer belongs to the baseline4/5 controller"
      exit 3
    fi
    sleep "$POLL_SECONDS"
  done
fi

for required in \
  "$DATASET/manifest.jsonl" \
  "$CALIBRATION" \
  "$CONFIG" \
  "$KEY_FILE" \
  "$BASELINE5_SUMMARY" \
  "$BASELINE4_SUMMARY"; do
  if [[ ! -s "$required" ]]; then
    echo "$(date -Is) missing required input after baseline controller exit: $required"
    exit 4
  fi
done

python3 - "$CALIBRATION" "$BASELINE5_SUMMARY" "$BASELINE4_SUMMARY" <<'PY'
import json
import sys

calibration = json.load(open(sys.argv[1], encoding="utf-8"))
if not (
    calibration.get("success") is True
    and calibration.get("task_count") == 100
    and calibration.get("pass_count") == 100
):
    raise SystemExit("reference calibration did not pass 100/100 tasks")

expected = (
    (sys.argv[2], "gpt-5.6-luna"),
    (sys.argv[3], "claude-sonnet-5"),
)
for path, expected_model in expected:
    summary = json.load(open(path, encoding="utf-8"))
    if summary.get("task_count") != 100:
        raise SystemExit(f"incomplete prerequisite batch: {path}")
    if summary.get("protocol_ok") is not True:
        raise SystemExit(f"prerequisite protocol audit failed: {path}")
    if summary.get("requested_model") != expected_model:
        raise SystemExit(
            f"prerequisite model mismatch in {path}: "
            f"{summary.get('requested_model')!r} != {expected_model!r}"
        )
PY
echo "$(date -Is) baseline4/5 completed 100/100 with protocol audits passing"

if [[ -d "$OUTPUT" ]] && find "$OUTPUT" -mindepth 1 -print -quit | grep -q .; then
  echo "$(date -Is) refusing non-empty output: $OUTPUT"
  exit 5
fi

export TEAMOROUTER_API_KEY
TEAMOROUTER_API_KEY=$(<"$KEY_FILE")
export PYTHONPATH=$METHOD/src

echo "$(date -Is) starting datasets100 Sonnet 5 EGBS run workers=$WORKERS output=$OUTPUT"
python3 "$METHOD/scripts/run_method_batch.py" \
  --config "$CONFIG" \
  --dataset-root "$DATASET" \
  --output "$OUTPUT" \
  --method evidence \
  --workers "$WORKERS"
unset TEAMOROUTER_API_KEY
echo "$(date -Is) datasets100 Sonnet 5 EGBS run finished"
