#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT=/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes
RUNS_ROOT="$SOURCE_ROOT/our_method/runs"
OUTPUT_ROOT="$SOURCE_ROOT/RQ4/results/all_models_frozen_trace_20260813_v3"

declare -A RUNS=(
  [deepseek-v4-flash]=egbs_deepseek_v4_flash_agentic_context_v5_2_datasets100_20260812_v1
  [gpt-5.6-luna]=egbs_gpt_5_6_luna_agentic_context_v5_2_datasets100_20260812_v1
  [gemini-3.5-flash-lite]=egbs_gemini_3_5_flash_lite_agentic_context_v5_2_datasets100_20260812_v1
  [claude-sonnet-5]=egbs_claude_sonnet_5_agentic_context_v5_2_datasets100_20260812_v1
)

mkdir -p "$OUTPUT_ROOT"
for model in "${!RUNS[@]}"; do
  output="$OUTPUT_ROOT/$model"
  if [[ -e "$output" ]]; then
    echo "refusing to overwrite existing output: $output" >&2
    exit 1
  fi
  python3 "$SOURCE_ROOT/RQ4/analyze_budget_efficiency.py" \
    --run-root "$RUNS_ROOT/${RUNS[$model]}" \
    --output "$output" \
    --model-id "$model" \
    --budgets 1,3,5,7,10 \
    --omit-api-cost \
    > "$OUTPUT_ROOT.$model.log" &
done
wait
