param(
    [string]$ProjectRoot = 'C:\ProgramData\Delta Industrial Automation\ISPSoft_New\Projects\DVP_CLEAN',
    [string]$OutputRoot = '\\tsclient\dvp\ispsoft_native_ld_probe'
)

$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

$files = @(
    Get-ChildItem -LiteralPath $ProjectRoot -Recurse -File -ErrorAction Stop |
        Sort-Object FullName |
        ForEach-Object {
            $relative = $_.FullName.Substring($ProjectRoot.Length).TrimStart('\')
            [ordered]@{
                relative_path = $relative
                length = $_.Length
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                last_write_time = $_.LastWriteTime.ToString('o')
            }
        }
)

[ordered]@{
    schema_version = 1
    captured_at = (Get-Date).ToString('o')
    computer = $env:COMPUTERNAME
    ispsoft_version = '3.24'
    project_root = $ProjectRoot
    files = $files
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputRoot 'inventory.json') -Encoding UTF8

$copyRoot = Join-Path $OutputRoot 'project'
New-Item -ItemType Directory -Path $copyRoot -Force | Out-Null
$arguments = @(
    ('"{0}"' -f $ProjectRoot), ('"{0}"' -f $copyRoot),
    '/E', '/R:1', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP'
)
$process = Start-Process -FilePath 'robocopy.exe' -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
if ($process.ExitCode -gt 7) {
    throw "robocopy failed with exit $($process.ExitCode)."
}

[ordered]@{
    status = 'pass'
    project_root = $ProjectRoot
    copied_file_count = $files.Count
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $OutputRoot 'status.json') -Encoding UTF8
