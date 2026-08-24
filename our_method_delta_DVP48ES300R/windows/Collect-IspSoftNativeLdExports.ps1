param(
    [string]$SourceRoot = 'C:\DVPW',
    [string]$OutputRoot = '\\tsclient\dvp\ISPSOFT_LD_EXPORTS'
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container)) {
    throw "ISPSoft export directory is missing: $SourceRoot"
}
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

$files = @(
    Get-ChildItem -LiteralPath $SourceRoot -Recurse -File |
        Where-Object { $_.Extension -in @('.FBU', '.MPU') } |
        Sort-Object FullName
)
foreach ($file in $files) {
    Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $OutputRoot $file.Name) -Force
}

[ordered]@{
    schema_version = 1
    captured_at = (Get-Date).ToString('o')
    source_root = $SourceRoot
    exports = @($files | ForEach-Object {
        [ordered]@{
            name = $_.Name
            length = $_.Length
            sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    })
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $OutputRoot 'inventory.json') -Encoding UTF8
