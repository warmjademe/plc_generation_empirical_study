param(
    [Parameter(Mandatory = $true)]
    [string]$Source,
    [Parameter(Mandatory = $true)]
    [string]$Destination
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
    throw "ISPSoft export does not exist: $Source"
}
Copy-Item -LiteralPath $Source -Destination $Destination -Force
