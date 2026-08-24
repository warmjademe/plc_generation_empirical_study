param(
    [string]$RedirectedDrive = '\\tsclient\export'
)

$ErrorActionPreference = 'Stop'
$destination = Join-Path $RedirectedDrive 'as228t_export'
$statusPath = Join-Path $RedirectedDrive 'as228t_export_status.json'
$sources = @(
    'C:\DeltaPLCValidation\templates\AS228T_CLEAN',
    'C:\ProgramData\Delta Industrial Automation\ISPSoft_New\Projects\AS228T_CLEAN'
)

try {
    $source = $sources | Where-Object {
        Test-Path -LiteralPath (Join-Path $_ 'AS228T_CLEAN.isp')
    } | Select-Object -First 1
    if (-not $source) {
        throw 'No qualified AS228T_CLEAN ISPSoft project was found.'
    }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $destination -Recurse -Force
    $project = Join-Path $destination 'AS228T_CLEAN.isp'
    [ordered]@{
        status = 'ready'
        captured_at = (Get-Date).ToString('o')
        project_sha256 = (Get-FileHash -LiteralPath $project -Algorithm SHA256).Hash.ToLowerInvariant()
    } | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
} catch {
    [ordered]@{
        status = 'error'
        captured_at = (Get-Date).ToString('o')
        message = $_.Exception.Message
    } | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    exit 1
}
