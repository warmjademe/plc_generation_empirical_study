param(
    [string]$OutputPath = '\\tsclient\dvp\host_inventory.json'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$statusPath = [System.IO.Path]::ChangeExtension($OutputPath, '.status.json')
trap {
    [ordered]@{
        status = 'error'
        captured_at = (Get-Date).ToString('o')
        message = $_.Exception.Message
        exception_type = $_.Exception.GetType().FullName
        position = $_.InvocationInfo.PositionMessage
        stack = $_.ScriptStackTrace
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
    exit 1
}
[ordered]@{ status = 'running'; captured_at = (Get-Date).ToString('o') } |
    ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8

$programRoots = @(
    "$env:ProgramFiles\Delta Industrial Automation",
    "${env:ProgramFiles(x86)}\Delta Industrial Automation",
    "$env:ProgramData\Delta Industrial Automation"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

$deltaExecutables = foreach ($root in $programRoots) {
    Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match '^(NewISPSoft|ISPSoft|COMMGR|DVP.*Simulator).*\.exe$' -or
            $_.FullName -match 'Delta Industrial Automation.*(ISPSoft|COMMGR)'
        } |
        Select-Object -First 200 FullName, Length, LastWriteTime,
            @{Name='FileVersion'; Expression={$_.VersionInfo.FileVersion}},
            @{Name='ProductVersion'; Expression={$_.VersionInfo.ProductVersion}}
}

$uninstallRoots = @(
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
$installedDelta = foreach ($path in $uninstallRoots) {
    Get-ItemProperty -Path $path -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -match 'Delta|ISPSoft|COMMGR' } |
        Select-Object DisplayName, DisplayVersion, Publisher, InstallLocation, UninstallString
}

$requiredPaths = @(
    'C:\Program Files (x86)\Delta Industrial Automation\ISPSoft 3.24\NewISPSoft.exe',
    'C:\DeltaPLCValidation\templates\DVP_CLEAN\DVP_CLEAN.isp',
    'C:\DeltaPLCValidation\worker\Run-DvpValidationWorker.ps1',
    'C:\ProgramData\Delta Industrial Automation\ISPSoft_New\Projects\DVP_CLEAN\DVP_CLEAN.isp'
)

$inventory = [ordered]@{
    captured_at = (Get-Date).ToString('o')
    computer = $env:COMPUTERNAME
    user = $env:USERNAME
    user_domain = $env:USERDOMAIN
    os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture, TotalVisibleMemorySize, FreePhysicalMemory
    powershell = $PSVersionTable.PSVersion.ToString()
    interactive_session = [Environment]::UserInteractive
    screen = [ordered]@{
        width = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width
        height = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height
    }
    required_paths = @($requiredPaths | ForEach-Object {
        [ordered]@{ path = $_; exists = Test-Path -LiteralPath $_ }
    })
    installed_delta_products = @($installedDelta)
    delta_executables = @($deltaExecutables)
    relevant_processes = @(Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ProcessName -match 'ISPSoft|COMMGR|DVP' } |
        Select-Object Id, ProcessName, MainWindowTitle, SessionId)
}

# The redirected-drive destination is provisioned by the Linux bridge.  Avoid
# New-Item on its UNC parent because Windows PowerShell 5.1 rejects some
# \tsclient paths even though Set-Content to the file itself works.
$inventory | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
[ordered]@{ status = 'complete'; captured_at = (Get-Date).ToString('o') } |
    ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
