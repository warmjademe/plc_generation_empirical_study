param(
    [string]$ProjectPath = "C:\ProgramData\Delta Industrial Automation\ISPSoft_New\Projects\DVP48ES300R_MinimalValidation\DVP48ES300R_MinimalValidation.isp"
)

$ErrorActionPreference = "Stop"
Get-Process -Name "NewISPSoft" -ErrorAction SilentlyContinue |
    Where-Object { $_.SessionId -eq (Get-Process -Id $PID).SessionId } |
    Stop-Process -Force
Start-Sleep -Seconds 2

$ispSoft = "C:\Program Files (x86)\Delta Industrial Automation\ISPSoft 3.24\NewISPSoft.exe"
if (-not (Test-Path -LiteralPath $ispSoft)) {
    throw "ISPSoft 3.24 executable is missing."
}

if (Test-Path -LiteralPath $ProjectPath) {
    Start-Process -FilePath $ispSoft -ArgumentList ('"{0}"' -f $ProjectPath)
} else {
    Start-Process -FilePath $ispSoft
}
