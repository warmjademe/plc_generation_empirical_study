#!/usr/bin/env bash
set -Eeuo pipefail

: "${KEMEI_WIN_VM_NAME:?KEMEI_WIN_VM_NAME is required}"
: "${KEMEI_WIN_VM_ROOT:?KEMEI_WIN_VM_ROOT is required}"
: "${KEMEI_WIN_TAP_NAME:?KEMEI_WIN_TAP_NAME is required}"
: "${KEMEI_WIN_GUEST_MAC:?KEMEI_WIN_GUEST_MAC is required}"

vm_name=$KEMEI_WIN_VM_NAME
vm_root=$KEMEI_WIN_VM_ROOT
runtime_dir=${KEMEI_WIN_RUNTIME_DIR:-/run/$vm_name}
tpm_state_dir=${KEMEI_WIN_TPM_STATE_DIR:-/var/lib/libvirt/swtpm/$vm_name}
tpm_runtime_dir=${KEMEI_WIN_TPM_RUNTIME_DIR:-/run/libvirt/qemu/swtpm}
vnc_display=${KEMEI_WIN_VNC_DISPLAY:-12}
memory_mb=${KEMEI_WIN_MEMORY_MB:-16384}
vcpu=${KEMEI_WIN_VCPU:-8}
vm_uuid=$(<"$vm_root/vm.uuid")

install -d -m 0750 "$runtime_dir" "$tpm_runtime_dir"
install -d -m 0700 "$tpm_state_dir"
rm -f "$runtime_dir/qmp.sock" "$runtime_dir/qemu.pid" \
  "$tpm_runtime_dir/$vm_name.sock" "$tpm_runtime_dir/$vm_name.pid"

/usr/bin/swtpm socket --tpm2 --tpmstate "dir=$tpm_state_dir,mode=0600" \
  --ctrl "type=unixio,path=$tpm_runtime_dir/$vm_name.sock,mode=0600" \
  --terminate --daemon

for _ in {1..50}; do
  [[ -S "$tpm_runtime_dir/$vm_name.sock" ]] && break
  sleep 0.1
done
[[ -S "$tpm_runtime_dir/$vm_name.sock" ]]

exec /usr/bin/qemu-system-x86_64 \
  -name "guest=$vm_name,process=$vm_name" -uuid "$vm_uuid" -enable-kvm \
  -machine q35,accel=kvm,smm=on \
  -cpu host,hv_relaxed=on,hv_vapic=on,hv_spinlocks=0x1fff,hv_time=on \
  -smp "$vcpu",sockets=1,cores="$vcpu",threads=1 -m "$memory_mb" \
  -global ICH9-LPC.disable_s3=1 -global ICH9-LPC.disable_s4=1 \
  -rtc base=localtime,clock=host,driftfix=slew \
  -drive if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd \
  -drive if=pflash,format=raw,unit=1,file="$vm_root/OVMF_VARS_4M.ms.fd" \
  -drive if=none,id=osdisk,file="$vm_root/win11.qcow2",format=qcow2,cache=none,aio=native,discard=unmap \
  -device ide-hd,drive=osdisk,bus=ide.0,bootindex=2 \
  -chardev "socket,id=chrtpm,path=$tpm_runtime_dir/$vm_name.sock" \
  -tpmdev emulator,id=tpm0,chardev=chrtpm -device tpm-crb,tpmdev=tpm0 \
  -netdev "tap,id=net0,ifname=$KEMEI_WIN_TAP_NAME,script=no,downscript=no" \
  -device "e1000e,netdev=net0,mac=$KEMEI_WIN_GUEST_MAC" \
  -device qemu-xhci,id=xhci -device usb-tablet,bus=xhci.0 \
  -vga std -display none -vnc "127.0.0.1:$vnc_display,share=force-shared" \
  -qmp "unix:$runtime_dir/qmp.sock,server=on,wait=off" -pidfile "$runtime_dir/qemu.pid"
