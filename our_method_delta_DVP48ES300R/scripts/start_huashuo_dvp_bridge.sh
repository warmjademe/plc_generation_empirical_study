#!/usr/bin/env bash
set -euo pipefail

method_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
private_env=${DELTAPLC_PRIVATE_ENV:-"$HOME/.config/plc-dvp/private.env"}
bridge_root=${DELTAPLC_BRIDGE_ROOT:-"$method_root/dvp_bridge"}
display_number=${DELTAPLC_RDP_DISPLAY:-:94}
rdp_target=${DELTAPLC_RDP_TARGET:-nas.qyb.name:33389}
state_root="$bridge_root/state"

test -f "$private_env"
set -a
# shellcheck disable=SC1090
. "$private_env"
set +a
: "${WINDOWS_RDP_PASSWORD:?WINDOWS_RDP_PASSWORD is required}"

mkdir -p "$bridge_root/dvp-spool/pending" "$bridge_root/dvp-spool/results" "$state_root"
install -m 600 "$method_root/windows/Run-DvpValidationWorker.ps1" "$bridge_root/Run-DvpValidationWorker.ps1"
install -m 600 "$method_root/windows/Invoke-DvpRuntimeCase.ps1" "$bridge_root/Invoke-DvpRuntimeCase.ps1"
install -m 600 "$method_root/windows/Start-DvpValidationWorkerFromRdp.ps1" "$bridge_root/Start-DvpValidationWorkerFromRdp.ps1"

if [[ -f "$state_root/supervisor.pid" ]]; then
    old_pid=$(<"$state_root/supervisor.pid")
    if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
        echo "DVP bridge supervisor is already running as PID $old_pid" >&2
        exit 1
    fi
fi
echo $$ > "$state_root/supervisor.pid"
cleanup() {
    rm -f "$state_root/supervisor.pid"
}
trap cleanup EXIT

display_id=${display_number#:}
if ! pgrep -f "Xvfb :${display_id}( |$)" >/dev/null; then
    Xvfb "$display_number" -screen 0 1600x1000x24 -nolisten tcp \
        >"$state_root/xvfb.log" 2>&1 &
    echo $! > "$state_root/xvfb.pid"
fi

for _ in $(seq 1 50); do
    if DISPLAY="$display_number" xdpyinfo >/dev/null 2>&1; then break; fi
    sleep 0.1
done
DISPLAY="$display_number" xdpyinfo >/dev/null

(
    printf '%s\n' "$WINDOWS_RDP_PASSWORD" |
        DISPLAY="$display_number" xfreerdp3 \
            /v:"$rdp_target" /u:qyb /d:QYBD2EE /from-stdin:force \
            /cert:ignore /size:1500x900 /drive:dvp,"$bridge_root" /auto-reconnect
) >"$state_root/xfreerdp.log" 2>&1 &
rdp_pid=$!
echo "$rdp_pid" > "$state_root/xfreerdp.pid"

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

DISPLAY="$display_number" xdotool windowfocus "$rdp_window"
DISPLAY="$display_number" xdotool key --clearmodifiers super+r
sleep 2
DISPLAY="$display_number" xdotool key ctrl+a
DISPLAY="$display_number" xdotool type --delay 1 \
    'powershell -NoProfile -ExecutionPolicy Bypass -File \\tsclient\dvp\Start-DvpValidationWorkerFromRdp.ps1'
DISPLAY="$display_number" xdotool key Return

echo "DVP bridge started: display=$display_number rdp_pid=$rdp_pid spool=$bridge_root/dvp-spool"
wait "$rdp_pid"
