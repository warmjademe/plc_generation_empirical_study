#!/usr/bin/env bash
set -Eeuo pipefail

vm_root=/data/vm/win11
runtime_dir=/run/kemei-win11
tpm_state_dir=/var/lib/libvirt/swtpm/kemei-win11
tpm_runtime_dir=/run/libvirt/qemu/swtpm
tpm_log=/var/log/swtpm/libvirt/qemu/kemei-win11.log
install_iso="$vm_root/iso/Win11_25H2_Chinese_Simplified_x64_v2.iso"
answer_iso="$vm_root/autounattend.iso"
vm_uuid=$(<"$vm_root/vm.uuid")

rm -f "$runtime_dir/qmp.sock" "$runtime_dir/qemu.pid" \
  "$tpm_runtime_dir/kemei-win11.sock" "$tpm_runtime_dir/kemei-win11.pid"

/usr/bin/swtpm socket \
  --tpm2 \
  --tpmstate "dir=$tpm_state_dir,mode=0600" \
  --ctrl "type=unixio,path=$tpm_runtime_dir/kemei-win11.sock,mode=0600" \
  --pid "file=$tpm_runtime_dir/kemei-win11.pid" \
  --log "file=$tpm_log,level=1" \
  --terminate \
  --daemon

for _ in {1..50}; do
  [[ -S "$tpm_runtime_dir/kemei-win11.sock" ]] && break
  sleep 0.1
done
[[ -S "$tpm_runtime_dir/kemei-win11.sock" ]] || { echo "swtpm socket did not become ready" >&2; exit 1; }

qemu_args=(
  -name guest=kemei-win11,process=kemei-win11
  -uuid "$vm_uuid"
  -enable-kvm
  -machine q35,accel=kvm,smm=on
  -cpu host,hv_relaxed=on,hv_vapic=on,hv_spinlocks=0x1fff,hv_time=on
  -smp 8,sockets=1,cores=8,threads=1
  -m 16384
  -global ICH9-LPC.disable_s3=1
  -global ICH9-LPC.disable_s4=1
  -rtc base=localtime,clock=host,driftfix=slew
  -drive if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd
  -drive if=pflash,format=raw,unit=1,file="$vm_root/OVMF_VARS_4M.ms.fd"
  -drive if=none,id=osdisk,file="$vm_root/win11.qcow2",format=qcow2,cache=none,aio=native,discard=unmap
  -device ide-hd,drive=osdisk,bus=ide.0,bootindex=2
  -chardev socket,id=chrtpm,path="$tpm_runtime_dir/kemei-win11.sock"
  -tpmdev emulator,id=tpm0,chardev=chrtpm
  -device tpm-crb,tpmdev=tpm0
  -netdev tap,id=net0,ifname=tap-kemei,script=no,downscript=no
  -device e1000e,netdev=net0,mac=52:54:00:12:34:56
  -device qemu-xhci,id=xhci
  -device usb-tablet,bus=xhci.0
  -vga std
  -display none
  -vnc 127.0.0.1:11,share=force-shared
  -qmp "unix:$runtime_dir/qmp.sock,server=on,wait=off"
  -pidfile "$runtime_dir/qemu.pid"
)

if [[ ! -e "$vm_root/install.complete" ]]; then
  [[ -r "$install_iso" ]] || { echo "missing Windows installation ISO: $install_iso" >&2; exit 1; }
  [[ -r "$answer_iso" ]] || { echo "missing unattended answer ISO: $answer_iso" >&2; exit 1; }
  qemu_args+=(
    -drive if=none,id=installcd,file="$install_iso",format=raw,media=cdrom,readonly=on
    -device ide-cd,drive=installcd,bus=ide.1,bootindex=1
    -drive if=none,id=answercd,file="$answer_iso",format=raw,media=cdrom,readonly=on
    -device ide-cd,drive=answercd,bus=ide.2,bootindex=3
  )
fi

exec /usr/bin/qemu-system-x86_64 "${qemu_args[@]}"
