#!/usr/bin/env bash
set -euo pipefail

tap_name=${KEMEI_WIN_TAP_NAME:-tap-kemei}

if ip link show dev "$tap_name" >/dev/null 2>&1; then
  ip link set dev "$tap_name" down || true
  ip tuntap del dev "$tap_name" mode tap
fi
