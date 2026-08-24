#!/usr/bin/env bash
set -euo pipefail

project_root=${PLC_PROJECT_ROOT:-/opt/plc-generation/app}
bridge_root=${PLC_DVP_BRIDGE_ROOT:-/opt/plc-generation/dvp-bridge}
display_number=${PLC_DVP_RDP_DISPLAY:-:97}
rdp_target=${PLC_DVP_RDP_TARGET:-10.0.2.15:3389}
worker_id=${PLC_DVP_WORKER_ID:-vps_windows}
rdp_user=${PLC_DVP_RDP_USER:-qyb}
rdp_domain=${PLC_DVP_RDP_DOMAIN:-}
: "${WINDOWS_RDP_PASSWORD:?WINDOWS_RDP_PASSWORD is required}"

# Production validation is intentionally bound to the private host-only KVM
# network.  Never fall back to DDNS or a public RDP forward: doing so would make
# a network outage silently change the validation trust boundary.
rdp_host=${rdp_target%:*}
rdp_port=${rdp_target##*:}
if ! python3 - "$rdp_host" "$rdp_port" <<'PY'
import ipaddress, sys
host, port = sys.argv[1], sys.argv[2]
try:
    valid = ipaddress.ip_address(host).is_private and int(port) == 3389
except ValueError:
    valid = False
raise SystemExit(0 if valid else 1)
PY
then
  printf 'refusing non-private Windows validation target: %s\n' "$rdp_target" >&2
  exit 64
fi

# Windows Update can hold the guest in a reboot phase for several minutes.
# Keep the bridge process alive and observable instead of creating a noisy
# systemd restart loop while RDP is not yet listening.
rdp_ready=false
for _ in $(seq 1 "${PLC_DVP_RDP_STARTUP_CHECKS:-180}"); do
  if timeout 1 bash -c "</dev/tcp/$rdp_host/$rdp_port" 2>/dev/null; then
    rdp_ready=true
    break
  fi
  sleep 2
done
if ! $rdp_ready; then
  printf 'private Windows validation endpoint did not become ready: %s\n' "$rdp_target" >&2
  exit 69
fi

state_root="$bridge_root/state"
export HOME="$bridge_root/home"
export XDG_RUNTIME_DIR="$state_root/runtime"
mkdir -p "$bridge_root/dvp-spool/pending" "$bridge_root/dvp-spool/results" "$state_root" "$HOME" "$XDG_RUNTIME_DIR"
chmod 700 "$HOME" "$XDG_RUNTIME_DIR"
install -m 600 "$project_root/windows/Run-DvpValidationWorker.ps1" "$bridge_root/Run-DvpValidationWorker.ps1"
install -m 600 "$project_root/windows/Invoke-DvpRuntimeCase.ps1" "$bridge_root/Invoke-DvpRuntimeCase.ps1"
install -m 600 "$project_root/windows/Ensure-DvpSimulator.ps1" "$bridge_root/Ensure-DvpSimulator.ps1"
install -m 600 "$project_root/windows/Initialize-As228tTemplate.ps1" "$bridge_root/Initialize-As228tTemplate.ps1"
install -m 600 "$project_root/windows/Write-DvpWorkerHeartbeat.ps1" "$bridge_root/Write-DvpWorkerHeartbeat.ps1"
install -m 600 "$project_root/windows/Start-DvpValidationWorkerFromRdp.ps1" "$bridge_root/Start-DvpValidationWorkerFromRdp.ps1"
rm -f "$bridge_root/bootstrap_status.json" "$bridge_root/simulator_status.json" \
  "$bridge_root/bridge_heartbeat.json" "$bridge_root/worker_heartbeat.json" \
  "$bridge_root/worker_state.json"
python3 - "$bridge_root/worker_endpoint.json" "$worker_id" "$rdp_host" "$rdp_port" <<'PY'
import json, pathlib, sys
path, worker_id, host, port = sys.argv[1:]
pathlib.Path(path).write_text(json.dumps({
    "worker_id": worker_id, "address": host, "port": int(port)
}, separators=(",", ":")) + "\n", encoding="utf-8")
PY

display_id=${display_number#:}
xvfb_pid=''
rdp_pid=''
cleanup() {
  [[ -z "$rdp_pid" ]] || kill "$rdp_pid" 2>/dev/null || true
  [[ -z "$xvfb_pid" ]] || kill "$xvfb_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# A crashed/restarted bridge can leave its private Xvfb behind briefly.  Since
# every pool member has a unique display, reclaim only this instance's server
# and start a fresh one owned by the current systemd process.
while read -r stale_xvfb_pid; do
  [[ -z "$stale_xvfb_pid" ]] || kill "$stale_xvfb_pid" 2>/dev/null || true
done < <(pgrep -f "^Xvfb :${display_id}( |$)" || true)
for _ in $(seq 1 20); do
  pgrep -f "^Xvfb :${display_id}( |$)" >/dev/null || break
  sleep 0.1
done
rm -f "/tmp/.X${display_id}-lock" "/tmp/.X11-unix/X${display_id}"
Xvfb "$display_number" -screen 0 1600x1000x24 -nolisten tcp >"$state_root/xvfb.log" 2>&1 &
xvfb_pid=$!
for _ in $(seq 1 50); do
  DISPLAY="$display_number" xdpyinfo >/dev/null 2>&1 && break
  sleep 0.1
done
DISPLAY="$display_number" xdpyinfo >/dev/null

rdp_client=$(command -v xfreerdp3 || command -v xfreerdp)
rdp_arguments=(
  /v:"$rdp_target" /u:"$rdp_user" /from-stdin:force
  /cert:ignore /size:1500x900 /drive:dvp,"$bridge_root" /auto-reconnect
)
if [[ -n "$rdp_domain" ]]; then
  rdp_arguments+=(/d:"$rdp_domain")
fi
(
  printf '%s\n' "$WINDOWS_RDP_PASSWORD" |
    DISPLAY="$display_number" "$rdp_client" "${rdp_arguments[@]}"
) >"$state_root/xfreerdp.log" 2>&1 &
rdp_pid=$!
printf '%s\n' "$rdp_pid" >"$state_root/xfreerdp.pid"

rdp_window=''
for _ in $(seq 1 120); do
  rdp_window=$(DISPLAY="$display_number" xdotool search --onlyvisible --name 'FreeRDP' 2>/dev/null | head -n 1 || true)
  [[ -n "$rdp_window" ]] && break
  kill -0 "$rdp_pid" 2>/dev/null || {
    tail -n 80 "$state_root/xfreerdp.log" >&2
    exit 1
  }
  sleep 0.5
done
[[ -n "$rdp_window" ]]

# FreeRDP builds do not consistently emit a redirected-drive registration log
# at their default log level.  Give Explorer a short bounded settle period;
# the bootstrap command below performs the authoritative Test-Path retry in
# the Windows session instead of treating a missing Linux log line as offline.
for _ in $(seq 1 "${PLC_DVP_DESKTOP_READY_CHECKS:-20}"); do
  kill -0 "$rdp_pid" 2>/dev/null || exit 1
  grep -q 'device_announce.*registered.*dvp' "$state_root/xfreerdp.log" 2>/dev/null && break
  sleep 0.5
done
sleep "${PLC_DVP_DESKTOP_SETTLE_SECONDS:-2}"

launch_windows_worker() {
  # Xvfb has no window manager, so target the FreeRDP window explicitly.  The
  # same bounded bootstrap is reused when the independent worker heartbeat
  # proves that PowerShell stopped while the RDP transport stayed connected.
  rdp_window=$(DISPLAY="$display_number" xdotool search --onlyvisible --name 'FreeRDP' 2>/dev/null | tail -n 1 || true)
  [[ -n "$rdp_window" ]] || return 1
  DISPLAY="$display_number" xdotool windowfocus --sync "$rdp_window" || true
  DISPLAY="$display_number" xdotool mousemove --window "$rdp_window" 750 450 click 1
  sleep 1
  DISPLAY="$display_number" xdotool key --window "$rdp_window" --clearmodifiers super+r
  sleep 2
  DISPLAY="$display_number" xdotool key --window "$rdp_window" --clearmodifiers ctrl+a
  local bootstrap_command
  bootstrap_command="powershell -NoProfile -ExecutionPolicy Bypass -Command \"\$p='\\\\tsclient\dvp\Start-DvpValidationWorkerFromRdp.ps1'; for(\$i=0;\$i -lt 120;\$i++){if(Test-Path \$p){& \$p; exit}; Start-Sleep -Seconds 1}; exit 1\""
  DISPLAY="$display_number" xdotool type --window "$rdp_window" --delay 1 \
    "$bootstrap_command"
  DISPLAY="$display_number" xdotool key --window "$rdp_window" Return
}

# Use a normal Explorer-backed RDP session and launch the bootstrap explicitly.
# FreeRDP's Alternate Shell support was intermittent across cloned Windows 11
# guests and could leave a connected session without starting the worker.
launch_windows_worker

bootstrap_ready=false
for _ in $(seq 1 180); do
  if [[ -f "$bridge_root/bootstrap_status.json" ]]; then
    bootstrap_status=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8-sig")).get("status", ""))' "$bridge_root/bootstrap_status.json" 2>/dev/null || true)
    case "$bootstrap_status" in
      worker_started|worker_already_running) bootstrap_ready=true; break ;;
      error)
        [[ ! -f "$bridge_root/as228t_template_status.json" ]] || cat "$bridge_root/as228t_template_status.json" >&2
        cat "$bridge_root/bootstrap_status.json" >&2
        exit 1
        ;;
    esac
  fi
  kill -0 "$rdp_pid" 2>/dev/null || exit 1
  sleep 1
done
$bootstrap_ready

stale_worker_checks=0
while kill -0 "$rdp_pid" 2>/dev/null; do
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  temporary="$bridge_root/bridge_heartbeat.json.tmp"
  printf '{"status":"connected","captured_at":"%s","rdp_pid":%s}\n' "$now" "$rdp_pid" >"$temporary"
  mv -f "$temporary" "$bridge_root/bridge_heartbeat.json"
  if [[ -f "$bridge_root/worker_heartbeat.json" ]] && \
     (( $(date +%s) - $(stat -c %Y "$bridge_root/worker_heartbeat.json") <= 30 )); then
    stale_worker_checks=0
  else
    stale_worker_checks=$((stale_worker_checks + 1))
    if (( stale_worker_checks >= 4 )); then
      launch_windows_worker
      stale_worker_checks=0
    fi
  fi
  sleep 15
done
wait "$rdp_pid"
