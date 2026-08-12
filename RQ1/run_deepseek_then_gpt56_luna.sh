#!/usr/bin/env bash
set -uo pipefail

SOURCE_ROOT=/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes
RUNS_ROOT="$SOURCE_ROOT/RQ1/runs"
QUALIFICATION="$SOURCE_ROOT/our_method/runs/calibration_agentic_context_v3_full50_20260811/calibration_summary.json"
DATASET="$SOURCE_ROOT/datasets_50"
CORPUS="$SOURCE_ROOT/datasets/IEC_ST_CORE.md"
DEEPSEEK_CONFIG="$SOURCE_ROOT/our_method/configs/deepseek_v4_flash_external_baselines.json"
LUNA_CONFIG="$SOURCE_ROOT/our_method/configs/teamorouter_gpt_5_6_luna_external_baselines.json"
PRIVATE_ROOT=/home/qyb/.config/plc-evidence-loop
CONTROLLER_LOG="$RUNS_ROOT/deepseek_then_gpt56_luna_controller.log"

mkdir -p "$RUNS_ROOT"
umask 077
exec >>"$CONTROLLER_LOG" 2>&1
echo "$(date -Is) controller started"

run_stage() {
  local stage=$1
  local config=$2
  local key_env=$3
  local key_file=$4
  local suffix=$5
  local scripts=(baseline1_llm4plc.py baseline2_agents4plc.py baseline3_chatdev.py)
  local prefixes=(baseline1_llm4plc baseline2_agents4plc baseline3_chatdev)
  local pids=()

  if [[ ! -s "$key_file" ]]; then
    echo "$(date -Is) $stage missing private key file"
    return 1
  fi
  export "$key_env=$(<"$key_file")"
  echo "$(date -Is) $stage starting"
  for index in 0 1 2; do
    local output="$RUNS_ROOT/${prefixes[$index]}_${suffix}_datasets50_20260811"
    local log="$output/huashuo_workers4.log"
    mkdir -p "$output"
    python3 "$SOURCE_ROOT/${scripts[$index]}" \
      --config "$config" \
      --dataset-root "$DATASET" \
      --qualification "$QUALIFICATION" \
      --output "$output" \
      --workers 4 \
      --public-corpus "$CORPUS" >"$log" 2>&1 &
    pids+=("$!")
    echo "$(date -Is) $stage ${prefixes[$index]} pid=${pids[-1]}"
  done

  local failed=0
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      failed=1
      echo "$(date -Is) $stage pid=$pid exited nonzero"
    fi
  done
  unset "$key_env"
  echo "$(date -Is) $stage finished failed=$failed"
  return "$failed"
}

deepseek_failed=0
run_stage "DeepSeek-V4-Flash" "$DEEPSEEK_CONFIG" DEEPSEEK_API_KEY \
  "$PRIVATE_ROOT/deepseek_api_key" deepseek_v4_flash || deepseek_failed=1

luna_failed=0
run_stage "GPT-5.6-Luna" "$LUNA_CONFIG" TEAMOROUTER_API_KEY \
  "$PRIVATE_ROOT/teamorouter_api_key" gpt_5_6_luna || luna_failed=1

echo "$(date -Is) controller finished deepseek_failed=$deepseek_failed luna_failed=$luna_failed"
exit $(( deepseek_failed || luna_failed ))
