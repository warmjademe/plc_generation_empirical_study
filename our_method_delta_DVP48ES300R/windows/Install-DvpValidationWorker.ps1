param(
    [string]$RedirectedDrive = '\\tsclient\dvp',
    [string]$ValidationRoot = 'C:\DeltaPLCValidation',
    [string]$StatusPath = '\\tsclient\dvp\worker_install.status.json'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
trap {
    [ordered]@{
        status = 'error'
        captured_at = (Get-Date).ToString('o')
        message = $_.Exception.Message
        position = $_.InvocationInfo.PositionMessage
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatusPath -Encoding UTF8
    exit 1
}

$workerRoot = Join-Path $ValidationRoot 'worker'
$templateRoot = Join-Path $ValidationRoot 'templates\DVP_CLEAN'
New-Item -ItemType Directory -Path $workerRoot -Force | Out-Null
New-Item -ItemType Directory -Path $templateRoot -Force | Out-Null

$files = @(
    'Run-DvpValidationWorker.ps1',
    'Invoke-DvpRuntimeCase.ps1',
    'Start-DvpValidationWorkerFromRdp.ps1'
)
foreach ($name in $files) {
    $source = Join-Path $RedirectedDrive $name
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing redirected worker file: $source"
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $workerRoot $name) -Force
}

$screenWidth = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width
$screenHeight = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height
$ispSoftPath = 'C:\Program Files (x86)\Delta Industrial Automation\ISPSoft 3.24\NewISPSoft.exe'
$templatePath = Join-Path $templateRoot 'DVP_CLEAN.isp'

$manifest = [ordered]@{
    status = 'worker_installed'
    captured_at = (Get-Date).ToString('o')
    computer = $env:COMPUTERNAME
    validation_root = $ValidationRoot
    worker_root = $workerRoot
    worker_files = @($files | ForEach-Object {
        $path = Join-Path $workerRoot $_
        [ordered]@{
            path = $path
            sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    })
    screen = [ordered]@{
        width = $screenWidth
        height = $screenHeight
        calibrated = ($screenWidth -eq 1500 -and $screenHeight -eq 900)
    }
    prerequisites = [ordered]@{
        ispsoft_3_24 = Test-Path -LiteralPath $ispSoftPath
        dvp_clean_template = Test-Path -LiteralPath $templatePath
    }
    ready_for_validation = (
        $screenWidth -eq 1500 -and
        $screenHeight -eq 900 -and
        (Test-Path -LiteralPath $ispSoftPath) -and
        (Test-Path -LiteralPath $templatePath)
    )
}

$manifest | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $ValidationRoot 'deployment.json') -Encoding UTF8
$manifest | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $StatusPath -Encoding UTF8
