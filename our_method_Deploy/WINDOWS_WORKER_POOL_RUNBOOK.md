# Windows ISPSoft/COMMGR Worker Pool Runbook

## Purpose and admission rule

The production pool runs one serial ISPSoft/COMMGR desktop per Windows VM. A VM is not added to `PLC_DVP_SPOOL_ROOTS` merely because RDP is reachable. It must first pass the positive/negative canary for both DVP48ES300R and AS228T-A and then complete the resumable 100-job soak with no polarity error, identity mismatch, stale-image replay, or inconclusive result.

## Capacity layout

The 32-vCPU, 123-GiB Kemei host runs four validation VMs at 8 vCPU and 16 GiB each. CPU is bounded at the host scheduler while each VM retains enough memory for ISPSoft, COMMGR and both simulators. The isolated instances are:

| Worker | Private network | TAP | Bridge root | X display |
|---|---|---|---|---|
| `vps_windows_01` | `10.0.2.0/24`, guest `.15` | `tap-kemei-01` | `/opt/plc-generation/dvp-bridge-01` | `:97` |
| `vps_windows_02` | `10.0.3.0/24`, guest `.15` | `tap-kemei-02` | `/opt/plc-generation/dvp-bridge-02` | `:98` |
| `vps_windows_03` | `10.0.4.0/24`, guest `.15` | `tap-kemei-03` | `/opt/plc-generation/dvp-bridge-03` | `:99` |
| `vps_windows_04` | `10.0.5.0/24`, guest `.15` | `tap-kemei-04` | `/opt/plc-generation/dvp-bridge-04` | `:100` |

Each instance requires a unique QEMU UUID, MAC address, TPM state, OVMF variable store, runtime directory, VNC display, worker ID, spool and RDP redirected drive. Sharing a spool or TPM state is prohibited.

## Golden-image procedure

1. Drain the current worker and confirm that its pending queue is empty.
2. Run both model-free positive/negative canaries and archive their immutable results.
3. Stop the RDP bridge and the source VM during a maintenance window. Never copy the actively written qcow2 file.
4. Freeze the source disk as a read-only golden qcow2 image, create four independent writable overlays, copy four OVMF variable stores and four TPM state directories, and generate distinct VM UUIDs and MAC addresses.
5. Start each clone on its private TAP network. Assign its configured worker ID through the bridge, confirm the fixed 1500x900 desktop, disable sleep/hibernation, and verify ISPSoft 3.24, COMMGR 2.11, DVP-ES3 and AS200 versions.
6. Run the four-job dual-target polarity canary, followed by `plc-dvp-soak.service` with 25 cycles (100 official jobs). Any failure leaves `health_status.json` in `quarantined` and the node must not enter the pool.
7. Add only qualified spool roots to `PLC_DVP_SPOOL_ROOTS`. Restart the task worker and confirm that `/api/validation-status` reports four distinct worker IDs, endpoints and queue depths.
8. Submit four vendor validation jobs concurrently. Confirm that the generation-job lease pins each user to one VM, all four execute in parallel, a fifth user waits without sharing a VM, and every result matches its manifest worker ID, job ID and artifact hashes.

## Long-running operation

- The bridge restarts a stopped Windows worker when its independent heartbeat is stale.
- ISPSoft starts from a byte-identical clean project for every job. After every 25 jobs, the Windows worker drains and recycles ISPSoft, COMMGR and both simulators.
- A daily dual-target positive/negative canary controls `ready` versus `quarantined` admission.
- Virtual machines are rebooted one at a time during a maintenance window; at least three qualified workers remain online.
- Windows Update is applied only during the rolling maintenance window. Sleep, hibernation and automatic unattended reboots remain disabled outside that window.
- Queue depth, heartbeat age, canary polarity, inconclusive rate, validation duration and VM restarts are monitored. A stale heartbeat, polarity error or result-identity mismatch removes only that worker from scheduling; it never converts a job to success.
