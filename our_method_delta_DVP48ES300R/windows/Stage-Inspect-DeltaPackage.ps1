param(
    [Parameter(Mandatory = $true)]
    [string]$SourceArchive,
    [string]$ValidationRoot = 'C:\DeltaPLCValidation',
    [string]$StatusPath = '\\tsclient\dvp\package_inspection.status.json'
)

$ErrorActionPreference = 'Stop'
$installerRoot = Join-Path $ValidationRoot 'installers'
$archivePath = Join-Path $installerRoot ([IO.Path]::GetFileName($SourceArchive))
$extractRoot = Join-Path $installerRoot ([IO.Path]::GetFileNameWithoutExtension($SourceArchive))

New-Item -ItemType Directory -Force -Path $installerRoot | Out-Null
Copy-Item -LiteralPath $SourceArchive -Destination $archivePath -Force
if (Test-Path -LiteralPath $extractRoot) {
    Remove-Item -LiteralPath $extractRoot -Recurse -Force
}
Expand-Archive -LiteralPath $archivePath -DestinationPath $extractRoot -Force

$executables = Get-ChildItem -LiteralPath $extractRoot -Recurse -File -ErrorAction Stop |
    Where-Object { $_.Extension -in @('.exe', '.msi') }
$signatures = foreach ($file in $executables) {
    $signature = if ($file.Extension -eq '.exe') {
        Get-AuthenticodeSignature -LiteralPath $file.FullName
    } else {
        $null
    }
    [ordered]@{
        path = $file.FullName
        length = $file.Length
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        signature_status = if ($null -eq $signature) { 'not_checked_msi' } else { [string]$signature.Status }
        signer = if ($null -eq $signature -or $null -eq $signature.SignerCertificate) { $null } else { $signature.SignerCertificate.Subject }
    }
}

$result = [ordered]@{
    status = 'package_inspected'
    archive_path = $archivePath
    archive_length = (Get-Item -LiteralPath $archivePath).Length
    archive_sha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    extract_root = $extractRoot
    executable_count = @($executables).Count
    executables = @($signatures)
}
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $StatusPath -Encoding UTF8
