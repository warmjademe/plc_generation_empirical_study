#!/usr/bin/env bash
set -uo pipefail

SOURCE_ROOT=/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes
METHOD_ROOT="$SOURCE_ROOT/our_method"
DEEPSEEK_OUTPUT="$METHOD_ROOT/runs/egbs_deepseek_v4_flash_agentic_context_v4_datasets50_20260811"
KIMI_OUTPUT="$METHOD_ROOT/runs/egbs_kimi_k3_agentic_context_v4_datasets50_20260811"
CONFIG="$METHOD_ROOT/configs/kimi_k3_agentic_context_v4.json"
DATASET="$SOURCE_ROOT/datasets_50"
KEY_FILE=/home/qyb/.config/plc-evidence-loop/kimi_api_key
CONTROLLER_LOG="$METHOD_ROOT/runs/kimi_v4_after_deepseek_controller.log"
RUN_LOG="$METHOD_ROOT/runs/egbs_kimi_k3_agentic_context_v4_workers12.log"

umask 077
exec >>"$CONTROLLER_LOG" 2>&1
echo "$(date -Is) Kimi v4 controller started"

while pgrep -f "[r]un_method_batch.py.*${DEEPSEEK_OUTPUT}" >/dev/null; do
  echo "$(date -Is) waiting for DeepSeek v4 to release the 12-core verifier host"
  sleep 30
done

if [[ -e "$KIMI_OUTPUT" ]]; then
  echo "$(date -Is) refusing to overwrite existing Kimi output: $KIMI_OUTPUT"
  exit 2
fi
if [[ ! -s "$KEY_FILE" ]]; then
  echo "$(date -Is) private Kimi key file is missing"
  exit 2
fi

export KIMI_API_KEY="$(<"$KEY_FILE")"
cd "$METHOD_ROOT"
echo "$(date -Is) starting official Kimi K3 with 12 task workers"
env PYTHONPATH="$METHOD_ROOT/src" python3 "$METHOD_ROOT/scripts/run_method_batch.py" \
  --config "$CONFIG" \
  --dataset-root "$DATASET" \
  --output "$KIMI_OUTPUT" \
  --method evidence \
  --workers 12 >"$RUN_LOG" 2>&1
status=$?
unset KIMI_API_KEY
echo "$(date -Is) official Kimi K3 run finished status=$status"
exit "$status"
