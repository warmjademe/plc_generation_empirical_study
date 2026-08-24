param(
    [string]$OutputPath = '\\tsclient\dvp\delta_installer_inventory.json'
)

$ErrorActionPreference = 'Stop'
$statusPath = [System.IO.Path]::ChangeExtension($OutputPath, '.status.json')
trap {
    [ordered]@{
        status = 'error'
        captured_at = (Get-Date).ToString('o')
        message = $_.Exception.Message
        position = $_.InvocationInfo.PositionMessage
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
    exit 1
}

$roots = @(
    "$env:USERPROFILE\Downloads",
    "$env:USERPROFILE\Desktop",
    'C:\Users\Public\Downloads',
    'C:\Installers',
    'C:\Software'
) | Where-Object { Test-Path -LiteralPath $_ }

$files = foreach ($root in $roots) {
    Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Extension -match '^\.(exe|msi|zip|7z|rar)$' -and
            ($_.Name -match 'Delta|ISPSoft|COMMGR|DVP|Simulator' -or $root -match 'Installers|Software')
        } |
        Select-Object FullName, Length, LastWriteTime,
            @{Name='FileVersion'; Expression={$_.VersionInfo.FileVersion}},
            @{Name='ProductName'; Expression={$_.VersionInfo.ProductName}}
}

[ordered]@{
    status = 'complete'
    captured_at = (Get-Date).ToString('o')
    searched_roots = @($roots)
    files = @($files)
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
[ordered]@{ status = 'complete'; captured_at = (Get-Date).ToString('o') } |
    ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
