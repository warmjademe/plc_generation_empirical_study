param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
$result = [ordered]@{
    captured_at = (Get-Date).ToString("o")
    status = "inconclusive"
    program = "M1 := M0"
    address_semantics = "COMMGR logical M index"
    trials = @()
}
$setup = $null
$comm = $null
try {
    if (-not [Environment]::Is64BitOperatingSystem -or [Environment]::Is64BitProcess) {
        throw "Run this script with SysWOW64 Windows PowerShell (32-bit)"
    }
    $sdkRoot = "C:\Program Files (x86)\Delta Industrial Automation\ISPSoft 3.24\DIACommission\DataTracer"
    [Environment]::CurrentDirectory = $sdkRoot
    foreach ($file in (Get-ChildItem -LiteralPath $sdkRoot -Filter "*.dll" -File | Sort-Object Name)) {
        try { [void][Reflection.Assembly]::LoadFrom($file.FullName) } catch {}
    }
    $helper = [DeltaIA.DIAStudio.Communication.Commgr.CommgrHelper]::SharedInstance
    $setup = [DeltaIA.DIAStudio.Communication.Setup.Commgr.ModbusCommgrSetup]::CreateWithHelper($helper)
    $data = New-Object "DeltaIA.DIAStudio.Communication.Setup.Commgr.ModbusCommgrSetupData" -ArgumentList 0, 3000
    $data.DriverName = "DVP48ES300R_SIM"
    $data.StationNumber = 0
    $data.ReceiveTimeout = 3000
    $setup.SetupData = $data
    [void]$setup.Apply()
    $comm = $setup.ModbusComm
    $comm.Connect()

    foreach ($value in @($false, $true, $false)) {
        $writeException = [byte]0
        $writeOk = $comm.TrySetCoil(0, $value, [ref]$writeException)
        Start-Sleep -Milliseconds 20
        $buffer = New-Object byte[] 1
        $readException = [byte]0
        $readOk = $comm.TryGetCoilStatus(1, 1, [ref]$buffer, [ref]$readException)
        $result.trials += [ordered]@{
            M0 = $value
            write_ok = $writeOk
            write_exception = $writeException
            M1 = [bool]$buffer[0]
            read_ok = $readOk
            read_exception = $readException
        }
    }
    $result.status = if (
        $result.trials.Count -eq 3 -and
        $result.trials[0].M1 -eq $false -and
        $result.trials[1].M1 -eq $true -and
        $result.trials[2].M1 -eq $false -and
        @($result.trials | Where-Object { -not $_.write_ok -or -not $_.read_ok }).Count -eq 0
    ) { "pass" } else { "fail" }
} catch {
    $result.status = "inconclusive"
    $result.error_type = $_.Exception.GetType().FullName
    $result.error = $_.Exception.Message
} finally {
    if ($null -ne $comm) { try { $comm.Disconnect() } catch {} }
    if ($null -ne $setup) { try { $setup.Dispose() } catch {} }
}

$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
if ($result.status -eq "pass") { exit 0 }
if ($result.status -eq "fail") { exit 2 }
exit 3
