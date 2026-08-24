#!/usr/bin/env bash
set -euo pipefail

project_root=${PLC_PROJECT_ROOT:-/opt/plc-generation/app}
spool_root=${PLC_DVP_SPOOL_ROOT:-/opt/plc-generation/dvp-bridge/dvp-spool}
run_root=${1:?output directory is required}
shift
targets=("$@")
if [[ ${#targets[@]} -eq 0 ]]; then
  targets=(DVP48ES300R AS228T-A)
fi

install -d -o ubuntu -g ubuntu -m 0750 "$run_root"
pids=()
for target in "${targets[@]}"; do
  case "$target" in
    DVP48ES300R|AS228T-A) ;;
    *) printf 'unsupported target: %s\n' "$target" >&2; exit 64 ;;
  esac
  for kind in good bad; do
    if [[ "$kind" == good ]]; then
      candidate=reference.st
    else
      candidate=known_bad.st
    fi
    case_dir="$run_root/${target}_${kind}"
    install -d -o ubuntu -g ubuntu -m 0750 "$case_dir"
    runuser -u ubuntu --preserve-environment -- \
      bash -c 'cd "$1" && exec "$2" "$3" --candidate "$4" --task-dir "$5" --case-role all --target "$6" --spool-root "$7" --timeout-seconds 2400 > result.json' \
      _ "$case_dir" \
      /home/ubuntu/miniforge3/envs/plc_generation/bin/python \
      "$project_root/scripts/dvp48es300r_validator.py" \
      "$project_root/fixtures/smoke_task/SMOKE_MOTOR/$candidate" \
      "$project_root/fixtures/smoke_task/SMOKE_MOTOR" \
      "$target" "$spool_root" &
    pids+=("$!")
  done
done

exit_code=0
for pid in "${pids[@]}"; do
  wait "$pid" || exit_code=1
done

/home/ubuntu/miniforge3/envs/plc_generation/bin/python - "$run_root" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
print(json.dumps({
    path.parent.name: json.loads(path.read_text(encoding="utf-8-sig")).get("status")
    for path in sorted(root.glob("*/result.json"))
}, sort_keys=True))
PY
exit "$exit_code"
