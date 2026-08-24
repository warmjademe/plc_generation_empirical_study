#!/usr/bin/env bash
set -euo pipefail

tap_name=${KEMEI_WIN_TAP_NAME:-tap-kemei}
tap_owner=${KEMEI_WIN_TAP_OWNER:-ubuntu}
tap_group=${KEMEI_WIN_TAP_GROUP:-libvirt}
host_address=${KEMEI_WIN_HOST_ADDRESS:-10.0.2.2/24}
guest_address=${KEMEI_WIN_GUEST_ADDRESS:-10.0.2.15}
guest_mac=${KEMEI_WIN_GUEST_MAC:-52:54:00:12:34:56}
runtime_dir=${KEMEI_WIN_NETWORK_RUNTIME:-/run/kemei-win11-network}

install -d -m 0750 "$runtime_dir"

if ! ip link show dev "$tap_name" >/dev/null 2>&1; then
  ip tuntap add dev "$tap_name" mode tap user "$tap_owner" group "$tap_group"
fi
ip address replace "$host_address" dev "$tap_name"
ip link set dev "$tap_name" up

rm -f "$runtime_dir/dnsmasq.pid" "$runtime_dir/dnsmasq.leases"
exec /usr/sbin/dnsmasq \
  --keep-in-foreground \
  --interface="$tap_name" \
  --bind-interfaces \
  --except-interface=lo \
  --port=0 \
  --no-resolv \
  --no-hosts \
  --dhcp-authoritative \
  --dhcp-range="$guest_address,$guest_address,255.255.255.0,12h" \
  --dhcp-host="$guest_mac,$guest_address" \
  --dhcp-option=3 \
  --dhcp-option=6 \
  --pid-file="$runtime_dir/dnsmasq.pid" \
  --dhcp-leasefile="$runtime_dir/dnsmasq.leases"
