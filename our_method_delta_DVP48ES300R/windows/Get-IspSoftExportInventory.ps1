param(
    [string]$OutputPath = "\\tsclient\codex\official_exports\desktop_exports.json"
)

$ErrorActionPreference = "Stop"
$desktop = [Environment]::GetFolderPath("Desktop")
$files = @(
    Get-ChildItem -LiteralPath $desktop -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in @(".FBU", ".MPU") } |
        Sort-Object LastWriteTime -Descending |
        Select-Object Name, FullName, Length, LastWriteTime
)
[ordered]@{
    captured_at = (Get-Date).ToString("o")
    desktop = $desktop
    files = $files
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
