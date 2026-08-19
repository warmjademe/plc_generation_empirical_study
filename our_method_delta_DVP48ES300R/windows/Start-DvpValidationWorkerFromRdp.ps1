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
New-Item -ItemType Directory -Path $WorkerRoot -Force | Out-Null
$worker = Join-Path $WorkerRoot 'Run-DvpValidationWorker.ps1'
$runtime = Join-Path $WorkerRoot 'Invoke-DvpRuntimeCase.ps1'
$redirectedWorker = Join-Path $RedirectedDrive 'Run-DvpValidationWorker.ps1'
$redirectedRuntime = Join-Path $RedirectedDrive 'Invoke-DvpRuntimeCase.ps1'
$spool = Join-Path $RedirectedDrive 'dvp-spool'
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
        if ($sameWorker -and $sameRuntime) {
            [ordered]@{
                status = 'worker_already_running'
                captured_at = (Get-Date).ToString('o')
                spool = $spool
                process_id = $process.ProcessId
            } | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
            exit 0
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

foreach ($name in @('pending', 'results')) {
    New-Item -ItemType Directory -Path (Join-Path $spool $name) -Force | Out-Null
}

[ordered]@{
    status = 'worker_started'
    captured_at = (Get-Date).ToString('o')
    spool = $spool
} | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $worker -SpoolRoot $spool
exit $LASTEXITCODE
