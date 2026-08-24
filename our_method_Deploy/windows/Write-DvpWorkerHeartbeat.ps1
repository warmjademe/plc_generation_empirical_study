param(
    [Parameter(Mandatory = $true)]
    [string]$HeartbeatPath,
    [Parameter(Mandatory = $true)]
    [string]$StatePath,
    [Parameter(Mandatory = $true)]
    [int]$ParentProcessId,
    [string]$WorkerId = $env:COMPUTERNAME,
    [int]$IntervalSeconds = 5
)

$ErrorActionPreference = 'Stop'
while (Get-Process -Id $ParentProcessId -ErrorAction SilentlyContinue) {
    $state = @{}
    try {
        if (Test-Path -LiteralPath $StatePath) {
            $state = Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        }
    } catch {
        $state = @{}
    }
    $document = [ordered]@{
        status = 'connected'
        state = if ($state.state) { [string]$state.state } else { 'starting' }
        job_id = if ($state.job_id) { [string]$state.job_id } else { '' }
        phase = if ($state.phase) { [string]$state.phase } else { '' }
        target = if ($state.target) { [string]$state.target } else { '' }
        case_index = if ($state.case_index) { [int]$state.case_index } else { 0 }
        case_total = if ($state.case_total) { [int]$state.case_total } else { 0 }
        captured_at = (Get-Date).ToUniversalTime().ToString('o')
        process_id = $ParentProcessId
        worker_id = $WorkerId
    }
    try {
        # The shared spool is an RDP redirected drive.  Move-Item -Force is
        # not atomic there and can leave the heartbeat absent after removing
        # its destination.  Directly overwrite this small telemetry file; the
        # Linux reader retries transient partial JSON and uses its fresh cache.
        $document | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $HeartbeatPath -Encoding UTF8
    } catch {
        # A transient redirected-drive write must not kill the liveness probe.
        Start-Sleep -Seconds 1
    }
    Start-Sleep -Seconds ([Math]::Max(1, $IntervalSeconds))
}
