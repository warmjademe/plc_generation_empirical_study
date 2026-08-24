param(
    [string]$RedirectedDrive = '\\tsclient\dvp',
    [string]$ProjectRoot = 'C:\ProgramData\Delta Industrial Automation\ISPSoft_New\Projects\AS228T_CLEAN',
    [string]$TemplateRoot = 'C:\DeltaPLCValidation\templates\AS228T_CLEAN'
)

$ErrorActionPreference = 'Stop'
$statusPath = Join-Path $RedirectedDrive 'as228t_template_status.json'
trap {
    [ordered]@{
        status = 'error'
        captured_at = (Get-Date).ToString('o')
        message = $_.Exception.Message
    } | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    exit 1
}

$projectFile = Join-Path $ProjectRoot 'AS228T_CLEAN.isp'
if (-not (Test-Path -LiteralPath $projectFile)) {
    throw "AS228T clean ISPSoft project is missing: $projectFile"
}
Get-Process NewISPSoft -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
New-Item -ItemType Directory -Path $TemplateRoot -Force | Out-Null
$process = Start-Process -FilePath 'robocopy.exe' -ArgumentList @(
    ('"{0}"' -f $ProjectRoot), ('"{0}"' -f $TemplateRoot),
    '/MIR', '/R:2', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP'
) -Wait -PassThru -WindowStyle Hidden
if ($process.ExitCode -gt 7) {
    throw "robocopy returned $($process.ExitCode) while creating the AS228T template"
}
$templateFile = Join-Path $TemplateRoot 'AS228T_CLEAN.isp'
if (-not (Test-Path -LiteralPath $templateFile)) {
    throw 'AS228T template project file was not copied.'
}
$projectHash = (Get-FileHash -LiteralPath $projectFile -Algorithm SHA256).Hash.ToLowerInvariant()
$templateHash = (Get-FileHash -LiteralPath $templateFile -Algorithm SHA256).Hash.ToLowerInvariant()
if ($projectHash -ne $templateHash) {
    throw 'AS228T template project hash differs after copy.'
}

[ordered]@{
    status = 'ready'
    captured_at = (Get-Date).ToString('o')
    target = 'AS228T-A'
    project_sha256 = $projectHash
    template = $templateFile
} | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
