#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  printf 'run as root\n' >&2
  exit 77
fi

app_root=/opt/plc-generation/app
python=/home/ubuntu/miniforge3/envs/plc_generation/bin/python
report_root=/opt/plc-generation/data/release-tests/rolling-worker-restart
install -d -o ubuntu -g ubuntu -m 0700 "$report_root"

for node in 01 02 03 04; do
  bridge_root="/opt/plc-generation/dvp-bridge-$node"
  if [[ -e "$bridge_root/active_user_job.json" ]]; then
    printf 'node %s has an active lease; rolling restart stopped\n' "$node" >&2
    exit 75
  fi
  systemctl restart "plc-dvp-bridge@$node.service"
  systemctl is-active --quiet "plc-dvp-bridge@$node.service"
  sudo -u ubuntu -E "$python" "$app_root/scripts/run_vendor_long_lease.py" \
    --spool-root "$bridge_root/dvp-spool" \
    --cycles 1 \
    --report "$report_root/node-$node.json"
done

printf 'all validation nodes restarted and passed both-target canaries\n'
