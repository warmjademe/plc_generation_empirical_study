#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT=/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes
RUN_ROOT="$SOURCE_ROOT/our_method/runs/egbs_deepseek_v4_flash_agentic_context_v5_2_datasets100_20260812_v1"
OUTPUT="$SOURCE_ROOT/RQ4/results/deepseek_v4_flash_frozen_trace_20260813_v2"

python3 "$SOURCE_ROOT/RQ4/analyze_budget_efficiency.py" \
  --run-root "$RUN_ROOT" \
  --output "$OUTPUT" \
  --budgets 1,3,5,7,10 \
  --price-date 2026-08-13 \
  --price-source https://api-docs.deepseek.com/quick_start/pricing \
  --cache-hit-usd-per-million 0.0028 \
  --cache-miss-usd-per-million 0.14 \
  --output-usd-per-million 0.28
