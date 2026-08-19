param(
    [string]$OutputRoot = "\\tsclient\codex\ispsoft_source_discovery"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$roots = @(
    "$env:ProgramData\Delta Industrial Automation",
    "${env:ProgramFiles(x86)}\Delta Industrial Automation",
    "$env:USERPROFILE\Documents",
    "$env:PUBLIC\Documents"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

$files = foreach ($root in $roots) {
    Get-ChildItem -LiteralPath $root -Recurse -File -Filter *.src -ErrorAction SilentlyContinue |
        Select-Object FullName, Length, LastWriteTime
}

$files |
    Sort-Object FullName -Unique |
    ConvertTo-Json -Depth 4 |
    Set-Content -LiteralPath (Join-Path $OutputRoot "source_units.json") -Encoding UTF8

$summary = [ordered]@{
    captured_at = (Get-Date).ToString("o")
    computer = $env:COMPUTERNAME
    user = $env:USERNAME
    ispsoft = @(Get-Process -Name ISPSoft -ErrorAction SilentlyContinue | Select-Object Id, MainWindowTitle)
    commgr = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match "COMMGR|DVP" } | Select-Object Id, ProcessName, MainWindowTitle)
    source_unit_count = @($files).Count
}
$summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $OutputRoot "summary.json") -Encoding UTF8
