param(
    [string]$RedirectedDrive = '\\tsclient\dvp',
    [string]$CommgrExe = 'C:\Program Files (x86)\Delta Industrial Automation\DIAStudio\DIATools\COMMGR 2.11\COMMGR.exe'
)

$ErrorActionPreference = 'Stop'
$statusPath = Join-Path $RedirectedDrive 'simulator_status.json'
$currentSessionId = (Get-Process -Id $PID).SessionId
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class DvpBootstrapWin32 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int command);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int x, int y, int cx, int cy, uint flags);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extraInfo);
}
'@

function Write-SimulatorStatus([string]$Status, [string]$Message = '') {
    [ordered]@{
        status = $Status
        captured_at = (Get-Date).ToString('o')
        message = $Message
        commgr_running = [bool](Get-Process COMMGR -ErrorAction SilentlyContinue)
        dvp_simulator_running = [bool](Get-Process DVPSimulator_ES3 -ErrorAction SilentlyContinue)
        as200_simulator_running = [bool](Get-Process AS200Simulator -ErrorAction SilentlyContinue)
        interactive_session_id = $currentSessionId
        commgr_session_ids = @(
            Get-Process COMMGR -ErrorAction SilentlyContinue | ForEach-Object { $_.SessionId }
        )
        drivers = @('DVP48ES300R_SIM', 'AS228T_SIM')
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
}

function Stop-NamedProcesses([string[]]$Names) {
    $processes = @($Names | ForEach-Object { Get-Process $_ -ErrorAction SilentlyContinue })
    foreach ($process in $processes) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        $remaining = @($Names | ForEach-Object { Get-Process $_ -ErrorAction SilentlyContinue })
        if ($remaining.Count -eq 0) { return }
        Start-Sleep -Milliseconds 250
    }
    throw "Processes did not stop before simulator bootstrap: $($Names -join ', ')."
}

trap {
    Write-SimulatorStatus 'error' $_.Exception.Message
    exit 1
}

if (-not (Test-Path -LiteralPath $CommgrExe)) {
    throw "COMMGR executable is missing: $CommgrExe"
}

# This is a dedicated validation desktop.  Windows Settings can remain as the
# foreground owner after a manual power/network check and refuse later GUI
# activation requests.  Closing only that nonessential shell window prevents
# it from intercepting calibrated COMMGR clicks; no user document is affected.
Get-Process SystemSettings -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue

function Find-InteractiveCommgr {
    foreach ($process in @(Get-Process COMMGR -ErrorAction SilentlyContinue |
        Where-Object { $_.SessionId -eq $currentSessionId })) {
        $process.Refresh()
        if ($process.MainWindowHandle -ne [IntPtr]::Zero -and
            $process.MainWindowTitle -match '(?i)COMMGR') {
            return $process
        }
    }
    return $null
}

$commgr = Find-InteractiveCommgr
# COMMGR is a per-desktop GUI application.  After an RDP disconnect Windows can
# leave a process in the old session with MainWindowHandle=0.  Reusing it makes
# the worker appear alive while no UI automation is possible.  Recreate the
# complete simulator stack in this interactive session whenever that happens.
$foreignCommgr = @(Get-Process COMMGR -ErrorAction SilentlyContinue |
    Where-Object { $_.SessionId -ne $currentSessionId })
if ($null -eq $commgr -or $foreignCommgr.Count -gt 0) {
    Stop-NamedProcesses @('DVPSimulator_ES3', 'AS200Simulator', 'COMMGR')
    Start-Process -FilePath $CommgrExe | Out-Null
}
$deadline = (Get-Date).AddSeconds(20)
while ($null -eq $commgr -and (Get-Date) -lt $deadline) {
    $commgr = Find-InteractiveCommgr
    Start-Sleep -Milliseconds 250
}
if ($null -eq $commgr) {
    # The first invocation initializes the tray resident process on a clean
    # session.  A second invocation is COMMGR's supported way to reveal the
    # manager window after the splash screen has closed.
    Start-Process -FilePath $CommgrExe | Out-Null
    $deadline = (Get-Date).AddSeconds(30)
    while ($null -eq $commgr -and (Get-Date) -lt $deadline) {
        $commgr = Find-InteractiveCommgr
        Start-Sleep -Milliseconds 250
    }
}
if ($null -eq $commgr) {
    throw 'COMMGR tray process started, but its stable manager window did not appear.'
}

function Start-SavedSimulator([string]$ProcessName, [int]$DriverRowY) {
    $existing = @(Get-Process $ProcessName -ErrorAction SilentlyContinue)
    $current = @($existing | Where-Object { $_.SessionId -eq $currentSessionId })
    foreach ($process in @($existing | Where-Object { $_.SessionId -ne $currentSessionId })) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
    if ($current.Count -gt 0) { return }
    [void][DvpBootstrapWin32]::ShowWindow($commgr.MainWindowHandle, 3)
    # SetForegroundWindow alone is commonly denied after an RDP reconnect when
    # another application (for example Windows Settings) owns the foreground.
    # Temporarily put COMMGR above it, click the safe title-bar area to transfer
    # foreground ownership, and verify the handle before using calibrated rows.
    [void][DvpBootstrapWin32]::SetWindowPos(
        $commgr.MainWindowHandle, [IntPtr](-1), 0, 0, 0, 0, 0x0043
    )
    [void][DvpBootstrapWin32]::BringWindowToTop($commgr.MainWindowHandle)
    [void][DvpBootstrapWin32]::SetForegroundWindow($commgr.MainWindowHandle)
    $shell = New-Object -ComObject WScript.Shell
    [void]$shell.AppActivate($commgr.Id)
    Start-Sleep -Milliseconds 500
    [void][DvpBootstrapWin32]::SetCursorPos(750, 18)
    [DvpBootstrapWin32]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    [DvpBootstrapWin32]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 500
    $foregroundProcessId = [uint32]0
    [void][DvpBootstrapWin32]::GetWindowThreadProcessId(
        [DvpBootstrapWin32]::GetForegroundWindow(), [ref]$foregroundProcessId
    )
    # The simulator process checks below remain the authoritative confirmation.
    # Some COMMGR builds report an owned helper window as foreground, so a PID
    # mismatch here is diagnostic rather than a reason to skip the actual click.
    [void][DvpBootstrapWin32]::SetCursorPos(120, $DriverRowY)
    [DvpBootstrapWin32]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    [DvpBootstrapWin32]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 500
    [void][DvpBootstrapWin32]::SetCursorPos(408, 63)
    [DvpBootstrapWin32]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    [DvpBootstrapWin32]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 500
    [void][DvpBootstrapWin32]::SetWindowPos(
        $commgr.MainWindowHandle, [IntPtr](-2), 0, 0, 0, 0, 0x0043
    )
}

# COMMGR sorts the two frozen production driver names lexically.  The row
# coordinates are calibrated for the fixed 1500x900 worker desktop, and the
# process/readiness checks below fail closed if the saved profile changes.
Start-SavedSimulator 'AS200Simulator' 143
Start-SavedSimulator 'DVPSimulator_ES3' 164

$deadline = (Get-Date).AddSeconds(30)
while (-not (Get-Process DVPSimulator_ES3 -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 250
}
if (-not (Get-Process DVPSimulator_ES3 -ErrorAction SilentlyContinue)) {
    throw 'DVP-ES3 simulator did not start; verify the saved DVP48ES300R_SIM COMMGR driver.'
}

$deadline = (Get-Date).AddSeconds(30)
while (-not (Get-Process AS200Simulator -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 250
}
if (-not (Get-Process AS200Simulator -ErrorAction SilentlyContinue)) {
    throw 'AS200 simulator did not start; verify the saved AS228T_SIM COMMGR driver.'
}

Write-SimulatorStatus 'ready' 'COMMGR, DVP-ES3, and AS200 simulators are running.'
exit 0
