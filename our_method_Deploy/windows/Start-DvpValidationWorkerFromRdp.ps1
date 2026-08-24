param(
    [string]$RedirectedDrive = '\\tsclient\dvp',
    [string]$WorkerRoot = 'C:\DeltaPLCValidation\worker'
)

$ErrorActionPreference = 'Stop'
$statusPath = Join-Path $RedirectedDrive 'bootstrap_status.json'
trap {
    [ordered]@{
        status = 'error'
        captured_at = (Get-Date).ToString('o')
        message = $_.Exception.Message
        exception_type = $_.Exception.GetType().FullName
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
    exit 1
}
[ordered]@{
    status = 'starting'
    captured_at = (Get-Date).ToString('o')
} | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8

# This VM is a continuously available validation appliance.  Enforce the
# power policy on every bridge bootstrap so an administrator or Windows update
# cannot silently restore a sleep or hibernation timeout.
$powerPolicyWarnings = @()
foreach ($arguments in @(
    @('/change', 'standby-timeout-ac', '0'),
    @('/change', 'standby-timeout-dc', '0'),
    @('/change', 'monitor-timeout-ac', '0'),
    @('/change', 'monitor-timeout-dc', '0'),
    @('/hibernate', 'off')
)) {
    & powercfg.exe @arguments | Out-Null
    if ($LASTEXITCODE -ne 0) {
        # The non-elevated RDP worker can be denied only for `/hibernate off`.
        # QEMU also disables S3 and S4 at the virtual hardware layer, so keep
        # this visible as defense-in-depth evidence without blocking validation.
        $powerPolicyWarnings += "powercfg $($arguments -join ' ') exited $LASTEXITCODE"
    }
}

New-Item -ItemType Directory -Path $WorkerRoot -Force | Out-Null
$worker = Join-Path $WorkerRoot 'Run-DvpValidationWorker.ps1'
$runtime = Join-Path $WorkerRoot 'Invoke-DvpRuntimeCase.ps1'
$ensureSimulator = Join-Path $WorkerRoot 'Ensure-DvpSimulator.ps1'
$initializeAs228t = Join-Path $WorkerRoot 'Initialize-As228tTemplate.ps1'
$redirectedWorker = Join-Path $RedirectedDrive 'Run-DvpValidationWorker.ps1'
$redirectedRuntime = Join-Path $RedirectedDrive 'Invoke-DvpRuntimeCase.ps1'
$redirectedEnsureSimulator = Join-Path $RedirectedDrive 'Ensure-DvpSimulator.ps1'
$redirectedInitializeAs228t = Join-Path $RedirectedDrive 'Initialize-As228tTemplate.ps1'
$heartbeat = Join-Path $WorkerRoot 'Write-DvpWorkerHeartbeat.ps1'
$redirectedHeartbeat = Join-Path $RedirectedDrive 'Write-DvpWorkerHeartbeat.ps1'
$spool = Join-Path $RedirectedDrive 'dvp-spool'
$endpointPath = Join-Path $RedirectedDrive 'worker_endpoint.json'
$workerId = $env:COMPUTERNAME
if (Test-Path -LiteralPath $endpointPath) {
    $endpoint = Get-Content -LiteralPath $endpointPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$endpoint.worker_id) { $workerId = [string]$endpoint.worker_id }
}
$existing = @(Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object {
    $_.CommandLine -match 'Run-DvpValidationWorker\.ps1'
})
foreach ($process in $existing) {
    if ($process.CommandLine -like "*$spool*") {
        $sameWorker = (Test-Path -LiteralPath $worker) -and
            ((Get-FileHash -LiteralPath $worker -Algorithm SHA256).Hash -eq
             (Get-FileHash -LiteralPath $redirectedWorker -Algorithm SHA256).Hash)
        $sameRuntime = (Test-Path -LiteralPath $runtime) -and
            ((Get-FileHash -LiteralPath $runtime -Algorithm SHA256).Hash -eq
             (Get-FileHash -LiteralPath $redirectedRuntime -Algorithm SHA256).Hash)
        $sameEnsureSimulator = (Test-Path -LiteralPath $ensureSimulator) -and
            ((Get-FileHash -LiteralPath $ensureSimulator -Algorithm SHA256).Hash -eq
             (Get-FileHash -LiteralPath $redirectedEnsureSimulator -Algorithm SHA256).Hash)
        $sameHeartbeat = (Test-Path -LiteralPath $heartbeat) -and
            ((Get-FileHash -LiteralPath $heartbeat -Algorithm SHA256).Hash -eq
             (Get-FileHash -LiteralPath $redirectedHeartbeat -Algorithm SHA256).Hash)
        if ($sameWorker -and $sameRuntime -and $sameEnsureSimulator -and $sameHeartbeat) {
            # A worker belongs to the redirected drive of the RDP session that
            # created it.  The UNC text is identical after reconnect, but the
            # old process can no longer observe new Linux queue entries.  Always
            # rebind the serial worker to the current session.
            Stop-Process -Id $process.ProcessId -Force
            Wait-Process -Id $process.ProcessId -ErrorAction SilentlyContinue
            break
        }
        Stop-Process -Id $process.ProcessId -Force
        Wait-Process -Id $process.ProcessId -ErrorAction SilentlyContinue
        break
    }
    # A worker bound to a disconnected RDP drive can never observe the new
    # queue.  Stop only that exact worker process before rebinding the serial
    # simulator to this session's redirected drive.
    Stop-Process -Id $process.ProcessId -Force
    Wait-Process -Id $process.ProcessId -ErrorAction SilentlyContinue
}
Copy-Item -LiteralPath $redirectedWorker -Destination $worker -Force
Copy-Item -LiteralPath $redirectedRuntime -Destination $runtime -Force
Copy-Item -LiteralPath $redirectedEnsureSimulator -Destination $ensureSimulator -Force
Copy-Item -LiteralPath $redirectedInitializeAs228t -Destination $initializeAs228t -Force
Copy-Item -LiteralPath $redirectedHeartbeat -Destination $heartbeat -Force

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $initializeAs228t -RedirectedDrive $RedirectedDrive
if ($LASTEXITCODE -ne 0) {
    throw "AS228T-A clean-template bootstrap failed with exit $LASTEXITCODE."
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ensureSimulator -RedirectedDrive $RedirectedDrive
if ($LASTEXITCODE -ne 0) {
    throw "COMMGR/DVP-ES3 bootstrap failed with exit $LASTEXITCODE."
}

foreach ($name in @('pending', 'results')) {
    New-Item -ItemType Directory -Path (Join-Path $spool $name) -Force | Out-Null
}

[ordered]@{
    status = 'worker_started'
    captured_at = (Get-Date).ToString('o')
    spool = $spool
    power_policy = if ($powerPolicyWarnings.Count -eq 0) { 'enforced' } else { 'hardware_enforced_with_warning' }
    power_policy_warnings = $powerPolicyWarnings
} | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $worker -SpoolRoot $spool -WorkerId $workerId
exit $LASTEXITCODE
