#!/usr/bin/env bash
set -uo pipefail

SOURCE_ROOT=${SOURCE_ROOT:-/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes}
RUN_ROOT=${RUN_ROOT:-$SOURCE_ROOT/RQ1/runs}
DATASET=${DATASET:-$SOURCE_ROOT/datasets_100}
QUALIFICATION=${QUALIFICATION:-$DATASET/evidence/exact_revalidation/calibration_summary.json}
CORPUS=${CORPUS:-$SOURCE_ROOT/datasets/IEC_ST_CORE.md}
CONFIG=${CONFIG:-$SOURCE_ROOT/our_method/configs/teamorouter_claude_sonnet5_external_baselines.json}
KEY_FILE=${KEY_FILE:-$HOME/.config/plc-evidence-loop/teamorouter_api_key}
WORKERS_PER_BASELINE=${WORKERS_PER_BASELINE:-4}
RUN_TAG=${RUN_TAG:-20260812_v1}
POLL_SECONDS=${POLL_SECONDS:-60}

GEMINI_PREFIXES=(
  baseline1_llm4plc_gemini_3_5_flash_lite_datasets100_20260812_v1
  baseline2_agents4plc_gemini_3_5_flash_lite_datasets100_20260812_v1
  baseline3_chatdev_gemini_3_5_flash_lite_datasets100_20260812_v1
)
CLAUDE_PREFIXES=(
  baseline1_llm4plc_claude_sonnet_5_datasets100_$RUN_TAG
  baseline2_agents4plc_claude_sonnet_5_datasets100_$RUN_TAG
  baseline3_chatdev_claude_sonnet_5_datasets100_$RUN_TAG
)
SCRIPTS=(baseline1_llm4plc.py baseline2_agents4plc.py baseline3_chatdev.py)
LOG_ROOT=$RUN_ROOT/logs_datasets100_claude_sonnet5_$RUN_TAG
CONTROLLER_LOG=$LOG_ROOT/controller.log

mkdir -p "$RUN_ROOT" "$LOG_ROOT"
exec >>"$CONTROLLER_LOG" 2>&1
echo "$(date -Is) waiting for all Gemini baselines"

while true; do
  if python3 - "$RUN_ROOT" "${GEMINI_PREFIXES[@]}" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
ready = True
for name in sys.argv[2:]:
    path = root / name / "baseline_summary.json"
    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
        complete = int(summary.get("task_count", 0)) == 100
    except (OSError, ValueError, TypeError):
        complete = False
    print(f"{name}: complete={complete}")
    ready = ready and complete
raise SystemExit(0 if ready else 1)
PY
  then
    break
  fi
  sleep "$POLL_SECONDS"
done

echo "$(date -Is) all Gemini baselines completed; preparing Claude Sonnet 5"
for required in "$DATASET/manifest.jsonl" "$QUALIFICATION" "$CORPUS" "$CONFIG" "$KEY_FILE"; do
  if [[ ! -s "$required" ]]; then
    echo "$(date -Is) missing required input: $required"
    exit 2
  fi
done
for prefix in "${CLAUDE_PREFIXES[@]}"; do
  output=$RUN_ROOT/$prefix
  if [[ -d "$output" ]] && find "$output" -mindepth 1 -print -quit | grep -q .; then
    echo "$(date -Is) refusing non-empty output: $output"
    exit 3
  fi
done

export TEAMOROUTER_API_KEY
TEAMOROUTER_API_KEY=$(<"$KEY_FILE")
pids=()
for index in 0 1 2; do
  output=$RUN_ROOT/${CLAUDE_PREFIXES[$index]}
  log=$LOG_ROOT/${CLAUDE_PREFIXES[$index]}.log
  python3 "$SOURCE_ROOT/${SCRIPTS[$index]}" \
    --config "$CONFIG" \
    --dataset-root "$DATASET" \
    --qualification "$QUALIFICATION" \
    --output "$output" \
    --workers "$WORKERS_PER_BASELINE" \
    --public-corpus "$CORPUS" >"$log" 2>&1 &
  pids+=("$!")
  echo "$(date -Is) started ${CLAUDE_PREFIXES[$index]} pid=${pids[-1]} workers=$WORKERS_PER_BASELINE"
done

failed=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    echo "$(date -Is) baseline pid=$pid exited nonzero"
    failed=1
  fi
done
unset TEAMOROUTER_API_KEY
echo "$(date -Is) Claude Sonnet 5 baseline controller finished failed=$failed"
exit "$failed"
