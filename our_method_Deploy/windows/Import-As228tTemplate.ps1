param(
    [string]$RedirectedDrive = '\\tsclient\dvp',
    [Parameter(Mandatory = $true)]
    [string]$ExpectedProjectSha256
)

$ErrorActionPreference = 'Stop'
$source = Join-Path $RedirectedDrive 'as228t_import'
$projectRoot = 'C:\ProgramData\Delta Industrial Automation\ISPSoft_New\Projects\AS228T_CLEAN'
$templateRoot = 'C:\DeltaPLCValidation\templates\AS228T_CLEAN'
$statusPath = Join-Path $RedirectedDrive 'as228t_import_status.json'

function Get-Sha256([string]$Path) {
    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            return ([System.BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
        } finally {
            $sha.Dispose()
        }
    } finally {
        $stream.Dispose()
    }
}

function Copy-Tree([string]$Source, [string]$Destination) {
    [System.IO.Directory]::CreateDirectory($Destination) | Out-Null
    foreach ($file in [System.IO.Directory]::GetFiles(
        $Source, '*', [System.IO.SearchOption]::AllDirectories
    )) {
        $relative = $file.Substring($Source.Length).TrimStart('\')
        $target = Join-Path $Destination $relative
        [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($target)) | Out-Null
        [System.IO.File]::WriteAllBytes($target, [System.IO.File]::ReadAllBytes($file))
    }
}

function Write-Status([System.Collections.IDictionary]$Document) {
    $json = ConvertTo-Json -InputObject $Document
    [System.IO.File]::WriteAllText($statusPath, $json, [System.Text.Encoding]::UTF8)
}

try {
    $sourceProject = Join-Path $source 'AS228T_CLEAN.isp'
    if (-not (Test-Path -LiteralPath $sourceProject)) {
        throw "Migrated AS228T project is missing: $sourceProject"
    }
    $sourceHash = Get-Sha256 $sourceProject
    if ($sourceHash -ne $ExpectedProjectSha256.ToLowerInvariant()) {
        throw 'Migrated AS228T project hash does not match the qualified source.'
    }
    foreach ($process in @(Get-Process NewISPSoft -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $process.Id -Force
    }
    foreach ($destination in @($projectRoot, $templateRoot)) {
        Copy-Tree $source $destination
        $copiedProject = Join-Path $destination 'AS228T_CLEAN.isp'
        $copiedHash = Get-Sha256 $copiedProject
        if ($copiedHash -ne $sourceHash) {
            throw "AS228T project hash differs after copy to $destination"
        }
    }
    Write-Status ([ordered]@{
        status = 'ready'
        captured_at = (Get-Date).ToString('o')
        project_sha256 = $sourceHash
    })
} catch {
    Write-Status ([ordered]@{
        status = 'error'
        captured_at = (Get-Date).ToString('o')
        message = $_.Exception.Message
    })
    exit 1
}
