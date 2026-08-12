#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT=/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes
RUNS_ROOT="$SOURCE_ROOT/RQ1/runs"
DATASET="$SOURCE_ROOT/datasets_100"
QUALIFICATION="$DATASET/evidence/exact_revalidation/calibration_summary.json"
CORPUS="$SOURCE_ROOT/datasets/IEC_ST_CORE.md"
CONFIG="$SOURCE_ROOT/our_method/configs/deepseek_v4_flash_external_baselines.json"
KEY_FILE=/home/qyb/.config/plc-evidence-loop/deepseek_api_key
LOG_ROOT="$RUNS_ROOT/logs_datasets100_deepseek_20260812_v1"
CONTROLLER_LOG="$LOG_ROOT/controller.log"
WORKERS_PER_BASELINE=5

mkdir -p "$RUNS_ROOT" "$LOG_ROOT"
umask 077
exec >>"$CONTROLLER_LOG" 2>&1
echo "$(date -Is) datasets100 DeepSeek baseline controller started"

for required in "$DATASET/manifest.jsonl" "$QUALIFICATION" "$CORPUS" "$CONFIG" "$KEY_FILE"; do
  if [[ ! -s "$required" ]]; then
    echo "$(date -Is) missing required input: $required"
    exit 2
  fi
done

export DEEPSEEK_API_KEY
DEEPSEEK_API_KEY=$(<"$KEY_FILE")

scripts=(baseline1_llm4plc.py baseline2_agents4plc.py baseline3_chatdev.py)
prefixes=(baseline1_llm4plc baseline2_agents4plc baseline3_chatdev)
pids=()

for index in 0 1 2; do
  output="$RUNS_ROOT/${prefixes[$index]}_deepseek_v4_flash_datasets100_20260812_v1"
  log="$LOG_ROOT/${prefixes[$index]}.log"
  if [[ -d "$output" ]] && find "$output" -mindepth 1 -print -quit | grep -q .; then
    echo "$(date -Is) refusing non-empty output: $output"
    exit 3
  fi
  python3 "$SOURCE_ROOT/${scripts[$index]}" \
    --config "$CONFIG" \
    --dataset-root "$DATASET" \
    --qualification "$QUALIFICATION" \
    --output "$output" \
    --workers "$WORKERS_PER_BASELINE" \
    --public-corpus "$CORPUS" >"$log" 2>&1 &
  pids+=("$!")
  echo "$(date -Is) started ${prefixes[$index]} pid=${pids[-1]} workers=$WORKERS_PER_BASELINE"
done

failed=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    echo "$(date -Is) baseline pid=$pid exited nonzero"
    failed=1
  fi
done
unset DEEPSEEK_API_KEY

echo "$(date -Is) datasets100 DeepSeek baseline controller finished failed=$failed"
exit "$failed"
