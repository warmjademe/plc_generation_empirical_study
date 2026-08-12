#!/usr/bin/env bash
set -uo pipefail

SOURCE_ROOT=${SOURCE_ROOT:-/home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes}
DATASET=${DATASET:-$SOURCE_ROOT/datasets_100}
QUALIFICATION=${QUALIFICATION:-$DATASET/evidence/exact_revalidation/calibration_summary.json}
RUN_ROOT=${RUN_ROOT:-$SOURCE_ROOT/RQ1/runs}
WORKERS=${WORKERS:-4}
RUN_TAG=${RUN_TAG:-20260812_v4_independent_pass_at_10}
TEAMOROUTER_KEY_FILE=${TEAMOROUTER_KEY_FILE:-$HOME/.config/plc-evidence-loop/teamorouter_api_key}

BASELINE5_OUTPUT=${BASELINE5_OUTPUT:-$RUN_ROOT/baseline5_codex_gpt_5_6_luna_datasets100_$RUN_TAG}
BASELINE4_OUTPUT=${BASELINE4_OUTPUT:-$RUN_ROOT/baseline4_claude_code_sonnet5_datasets100_$RUN_TAG}
LOG_ROOT=${LOG_ROOT:-$RUN_ROOT/logs_baseline5_then_baseline4_$RUN_TAG}
CONTROLLER_LOG=$LOG_ROOT/controller.log
BASELINE5_LOG=$LOG_ROOT/baseline5_codex.log
BASELINE4_LOG=$LOG_ROOT/baseline4_claude_code.log

mkdir -p "$RUN_ROOT" "$LOG_ROOT"
exec >>"$CONTROLLER_LOG" 2>&1

echo "$(date -Is) sequential controller started workers=$WORKERS"
for required in \
  "$SOURCE_ROOT/baseline5_codex.py" \
  "$SOURCE_ROOT/baseline4_claude_code.py" \
  "$SOURCE_ROOT/our_method/configs/codex_gpt_5_6_luna_external_baseline.json" \
  "$SOURCE_ROOT/our_method/configs/claude_code_sonnet5_external_baseline.json" \
  "$SOURCE_ROOT/our_method/configs/common_external_judges.json" \
  "$DATASET/manifest.jsonl" \
  "$QUALIFICATION" \
  "$TEAMOROUTER_KEY_FILE"; do
  if [[ ! -s "$required" ]]; then
    echo "$(date -Is) missing required input: $required"
    exit 2
  fi
done

export PATH="$HOME/.npm-global/bin:$PATH"
for executable in codex claude; do
  if ! command -v "$executable" >/dev/null 2>&1; then
    echo "$(date -Is) missing executable: $executable"
    exit 2
  fi
done

for output in "$BASELINE5_OUTPUT" "$BASELINE4_OUTPUT"; do
  if [[ -d "$output" ]] && find "$output" -mindepth 1 -print -quit | grep -q .; then
    echo "$(date -Is) refusing non-empty output: $output"
    exit 3
  fi
done

echo "$(date -Is) baseline5 starting output=$BASELINE5_OUTPUT"
export TEAMOROUTER_API_KEY
TEAMOROUTER_API_KEY=$(<"$TEAMOROUTER_KEY_FILE")
python3 "$SOURCE_ROOT/baseline5_codex.py" \
  --config "$SOURCE_ROOT/our_method/configs/codex_gpt_5_6_luna_external_baseline.json" \
  --dataset-root "$DATASET" \
  --qualification "$QUALIFICATION" \
  --output "$BASELINE5_OUTPUT" \
  --workers "$WORKERS" >"$BASELINE5_LOG" 2>&1
baseline5_rc=$?
unset TEAMOROUTER_API_KEY
echo "$(date -Is) baseline5 finished rc=$baseline5_rc"

echo "$(date -Is) baseline4 starting output=$BASELINE4_OUTPUT"
python3 "$SOURCE_ROOT/baseline4_claude_code.py" \
  --config "$SOURCE_ROOT/our_method/configs/claude_code_sonnet5_external_baseline.json" \
  --dataset-root "$DATASET" \
  --qualification "$QUALIFICATION" \
  --output "$BASELINE4_OUTPUT" \
  --workers "$WORKERS" >"$BASELINE4_LOG" 2>&1
baseline4_rc=$?
echo "$(date -Is) baseline4 finished rc=$baseline4_rc"

python3 - "$BASELINE5_OUTPUT" "$BASELINE4_OUTPUT" "$baseline5_rc" "$baseline4_rc" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

records = []
for label, directory, returncode in (
    ("baseline5", Path(sys.argv[1]), int(sys.argv[3])),
    ("baseline4", Path(sys.argv[2]), int(sys.argv[4])),
):
    summary = directory / "baseline_summary.json"
    payload = json.loads(summary.read_text(encoding="utf-8")) if summary.is_file() else {}
    records.append({
        "baseline": label,
        "returncode": returncode,
        "output": str(directory),
        "task_count": payload.get("task_count"),
        "success_count": payload.get("success_count"),
        "protocol_ok": payload.get("protocol_ok"),
    })
document = {
    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    "runs": records,
}
(Path(sys.argv[1]).parent / "baseline5_then_baseline4_status.json").write_text(
    json.dumps(document, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

echo "$(date -Is) sequential controller finished baseline5_rc=$baseline5_rc baseline4_rc=$baseline4_rc"
exit "$baseline4_rc"
