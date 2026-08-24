param(
    [Parameter(Mandatory = $true)]
    [string]$SpoolRoot,

    [string]$TemplateRoot = 'C:\DeltaPLCValidation\templates\DVP_CLEAN',
    [string]$ProjectRoot = 'C:\ProgramData\Delta Industrial Automation\ISPSoft_New\Projects\DVP_CLEAN',
    [string]$WorkerRoot = 'C:\DeltaPLCValidation\worker',
    [string]$WorkerId = $env:COMPUTERNAME,
    [int]$PollSeconds = 2,
    [ValidateRange(40, 300)]
    [int]$IspSoftStartupTimeoutSeconds = 120,
    [int]$RuntimeCaseTimeoutSeconds = 90,
    [switch]$Once
)

$ErrorActionPreference = 'Stop'
$toolVersion = 'ISPSoft-3.24+COMMGR-2.11+Delta-simulators+serial-worker-v4-deployment-project'
$ispSoftExe = 'C:\Program Files (x86)\Delta Industrial Automation\ISPSoft 3.24\NewISPSoft.exe'
$runtimeRunner = Join-Path $WorkerRoot 'Invoke-DvpRuntimeCase.ps1'
$projectFile = Join-Path $ProjectRoot 'DVP_CLEAN.isp'
$templateProjectFile = Join-Path $TemplateRoot 'DVP_CLEAN.isp'
$expectedProjectTitle = 'DVP_CLEAN'
$expectedDriver = 'DVP48ES300R_SIM'
$runtimeGate = 'dvp_es3_runtime'
$targetSimulator = 'DVP-ES3'
$placeholderMainY = 378
$deploymentMainY = 378
$placeholderFunctionY = 0
$programFolderY = 358
$functionFolderY = 374
$workerHeartbeatPath = Join-Path (Split-Path -Parent $SpoolRoot) 'worker_heartbeat.json'
$workerStatePath = Join-Path (Split-Path -Parent $SpoolRoot) 'worker_state.json'
$heartbeatRunner = Join-Path $WorkerRoot 'Write-DvpWorkerHeartbeat.ps1'
$metricsPath = Join-Path $WorkerRoot 'worker_metrics.json'

function Write-WorkerHeartbeat(
    [string]$State,
    [string]$JobId = '',
    [string]$Phase = '',
    [string]$Target = '',
    [int]$CaseIndex = 0,
    [int]$CaseTotal = 0
) {
    $document = [ordered]@{
        state = $State
        job_id = $JobId
        phase = $Phase
        target = $Target
        case_index = $CaseIndex
        case_total = $CaseTotal
        captured_at = (Get-Date).ToUniversalTime().ToString('o')
        process_id = $PID
        worker_id = $WorkerId
    }
    try {
        # RDP redirected drives do not implement ReplaceFile/Move-Item with
        # local-disk semantics.  A failed replacement used to remove the
        # destination and leave many .tmp files, making a healthy worker look
        # offline.  Write the small telemetry document directly; the Linux
        # reader retries a transient partial read and retains its last fresh
        # document during that short window.
        $document | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $workerStatePath -Encoding UTF8
        if ($JobId -and $Phase) {
            $sharedJob = Join-Path (Join-Path $SpoolRoot 'pending') $JobId
            if (Test-Path -LiteralPath $sharedJob) {
                [ordered]@{
                    job_id = $JobId
                    phase = $Phase
                    target = $Target
                    case_index = $CaseIndex
                    case_total = $CaseTotal
                    captured_at = $document.captured_at
                } | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $sharedJob 'worker_progress.jsonl') -Encoding UTF8
            }
        }
    } catch {
        # Telemetry must never terminate the validation worker.  The companion
        # heartbeat and Linux readiness gate will expose a prolonged failure.
        try { Write-WorkerLog "worker-state telemetry failed: $($_.Exception.Message)" } catch {}
    }
}

function Set-TargetConfiguration([string]$Target) {
    if ($Target -eq 'DVP48ES300R') {
        $script:TemplateRoot = 'C:\DeltaPLCValidation\templates\DVP_CLEAN'
        $script:ProjectRoot = 'C:\ProgramData\Delta Industrial Automation\ISPSoft_New\Projects\DVP_CLEAN'
        $script:projectFile = Join-Path $script:ProjectRoot 'DVP_CLEAN.isp'
        $script:templateProjectFile = Join-Path $script:TemplateRoot 'DVP_CLEAN.isp'
        $script:expectedProjectTitle = 'DVP_CLEAN'
        $script:expectedDriver = 'DVP48ES300R_SIM'
        $script:runtimeGate = 'dvp_es3_runtime'
        $script:targetSimulator = 'DVP-ES3'
        $script:placeholderMainY = 378
        $script:deploymentMainY = 378
        $script:placeholderFunctionY = 0
        $script:programFolderY = 358
        $script:functionFolderY = 374
        return
    }
    if ($Target -eq 'AS228T-A') {
        $script:TemplateRoot = 'C:\DeltaPLCValidation\templates\AS228T_CLEAN'
        $script:ProjectRoot = 'C:\ProgramData\Delta Industrial Automation\ISPSoft_New\Projects\AS228T_CLEAN'
        $script:projectFile = Join-Path $script:ProjectRoot 'AS228T_CLEAN.isp'
        $script:templateProjectFile = Join-Path $script:TemplateRoot 'AS228T_CLEAN.isp'
        $script:expectedProjectTitle = 'AS228T_CLEAN'
        $script:expectedDriver = 'AS228T_SIM'
        $script:runtimeGate = 'as200_runtime'
        $script:targetSimulator = 'AS200'
        # AS projects expose Program, Function Block, then the placeholder MAIN
        # as the first expanded POU child.  The former 393 coordinate selected
        # the Function Block folder and left its context menu open; 410 targets
        # the actual MAIN row on the calibrated 1500x900 desktop.
        $script:placeholderMainY = 410
        # Once the imported candidate FB expands the lower tree, the executed
        # MAIN remains the child directly below Program at this calibrated row.
        $script:deploymentMainY = 394
        # The qualified AS template also carries one inert calibration FB so
        # ISPSoft can preserve the Function Block tree.  Remove it from every
        # disposable project before importing the hash-verified candidate.
        $script:placeholderFunctionY = 426
        $script:programFolderY = 378
        $script:functionFolderY = 397
        return
    }
    throw "Unsupported Delta validation target: $Target"
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class DvpWorkerWin32 {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr hWnd, EnumWindowsProc callback, IntPtr lParam);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
  [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern bool SetWindowText(IntPtr hWnd, string text);
  [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetClassName(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int command);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extraInfo);
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool IsWindowUnicode(IntPtr hWnd);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr OpenProcess(uint access, bool inherit, uint processId);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr VirtualAllocEx(IntPtr process, IntPtr address, int size, uint allocationType, uint protect);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool VirtualFreeEx(IntPtr process, IntPtr address, int size, uint freeType);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool WriteProcessMemory(IntPtr process, IntPtr address, byte[] buffer, int size, out IntPtr written);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool ReadProcessMemory(IntPtr process, IntPtr address, byte[] buffer, int size, out IntPtr read);
  [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr handle);
}
'@

function Write-WorkerLog([string]$Message) {
    $line = '{0} {1}' -f (Get-Date).ToString('o'), $Message
    Add-Content -LiteralPath (Join-Path $WorkerRoot 'worker.log') -Value $line -Encoding UTF8
}

function Copy-TreeWithRobocopy([string]$Source, [string]$Destination, [switch]$Mirror) {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    $arguments = @(
        ('"{0}"' -f $Source), ('"{0}"' -f $Destination),
        $(if ($Mirror) { '/MIR' } else { '/E' }),
        '/R:2', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP'
    )
    $process = Start-Process -FilePath 'robocopy.exe' -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -gt 7) {
        throw "robocopy failed from $Source to $Destination with exit $($process.ExitCode)."
    }
}

function Copy-OneFileWithCmd([string]$Source, [string]$Destination) {
    & $env:ComSpec /d /c copy /b /y $Source $Destination | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "cmd copy failed from $Source to $Destination with exit $LASTEXITCODE." }
}

function Copy-SharedJobToLocal([string]$SharedJob, [string]$LocalJob) {
    New-Item -ItemType Directory -Path $LocalJob -Force | Out-Null
    foreach ($name in @('manifest.json','candidate.st','candidate.FBU','MAIN.MPU','suite.json')) {
        Copy-OneFileWithCmd (Join-Path $SharedJob $name) (Join-Path $LocalJob $name)
    }
    foreach ($name in @(
        'candidate.ld.json','candidate.ispsoft.ld.src','deployment.MPU',
        'deployment_main.st','engineering_mapping.json'
    )) {
        $optional = Join-Path $SharedJob $name
        if (Test-Path -LiteralPath $optional) {
            Copy-OneFileWithCmd $optional (Join-Path $LocalJob $name)
        }
    }
}

function Get-WindowTextValue([IntPtr]$Handle) {
    $buffer = New-Object Text.StringBuilder 4096
    [void][DvpWorkerWin32]::GetWindowText($Handle, $buffer, $buffer.Capacity)
    return $buffer.ToString()
}

function Get-WindowClassValue([IntPtr]$Handle) {
    $buffer = New-Object Text.StringBuilder 256
    [void][DvpWorkerWin32]::GetClassName($Handle, $buffer, $buffer.Capacity)
    return $buffer.ToString()
}

function Get-WindowRectangle([IntPtr]$Handle) {
    $rect = New-Object DvpWorkerWin32+RECT
    if (-not [DvpWorkerWin32]::GetWindowRect($Handle, [ref]$rect)) {
        throw 'GetWindowRect failed.'
    }
    return $rect
}

function Get-IspSoftProcessIds {
    return @(Get-Process NewISPSoft -ErrorAction SilentlyContinue | ForEach-Object { [uint32]$_.Id })
}

function Get-TopWindows([string]$ClassName = '', [switch]$VisibleOnly) {
    $ids = @(Get-IspSoftProcessIds)
    $script:dvpTopWindows = New-Object System.Collections.ArrayList
    $callback = [DvpWorkerWin32+EnumWindowsProc]{
        param([IntPtr]$hWnd, [IntPtr]$lParam)
        $owner = [uint32]0
        [void][DvpWorkerWin32]::GetWindowThreadProcessId($hWnd, [ref]$owner)
        if ($ids -contains $owner) {
            $class = Get-WindowClassValue $hWnd
            $isVisible = [DvpWorkerWin32]::IsWindowVisible($hWnd)
            if ((-not $ClassName -or $class -eq $ClassName) -and (-not $VisibleOnly -or $isVisible)) {
                [void]$script:dvpTopWindows.Add([ordered]@{
                    hwnd = $hWnd
                    pid = $owner
                    class = $class
                    title = Get-WindowTextValue $hWnd
                    visible = $isVisible
                })
            }
        }
        return $true
    }
    [void][DvpWorkerWin32]::EnumWindows($callback, [IntPtr]::Zero)
    return @($script:dvpTopWindows)
}

function Get-ChildWindows([IntPtr]$Parent, [string]$ClassName = '', [switch]$VisibleOnly) {
    $script:dvpChildWindows = New-Object System.Collections.ArrayList
    $callback = [DvpWorkerWin32+EnumWindowsProc]{
        param([IntPtr]$hWnd, [IntPtr]$lParam)
        $class = Get-WindowClassValue $hWnd
        $isVisible = [DvpWorkerWin32]::IsWindowVisible($hWnd)
        if ((-not $ClassName -or $class -eq $ClassName) -and (-not $VisibleOnly -or $isVisible)) {
            $rect = Get-WindowRectangle $hWnd
            [void]$script:dvpChildWindows.Add([ordered]@{
                hwnd = $hWnd
                class = $class
                title = Get-WindowTextValue $hWnd
                visible = $isVisible
                left = $rect.Left
                top = $rect.Top
                right = $rect.Right
                bottom = $rect.Bottom
            })
        }
        return $true
    }
    [void][DvpWorkerWin32]::EnumChildWindows($Parent, $callback, [IntPtr]::Zero)
    return @($script:dvpChildWindows)
}

function Wait-TopWindow([string]$ClassName, [int]$TimeoutSeconds = 30) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $windows = @(Get-TopWindows -ClassName $ClassName -VisibleOnly)
        if ($windows.Count -gt 0) { return $windows[0] }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for visible ISPSoft window class $ClassName."
}

function Wait-WindowClosed([IntPtr]$Handle, [int]$TimeoutSeconds = 30) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $stillOpen = $false
        foreach ($window in @(Get-TopWindows)) {
            if ($window.hwnd -eq $Handle -and $window.visible) { $stillOpen = $true; break }
        }
        if (-not $stillOpen) { return }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $deadline)
    throw 'Timed out waiting for an ISPSoft window to close.'
}

function Reject-IspSoftRecovery([object]$Dialog) {
    # ISPSoft displays this localized prompt after the disposable project from
    # the previous validation job was force-closed.  Keyboard accelerators are
    # unreliable over a reconnected RDP session, so select the rightmost (No)
    # button by geometry and verify that the modal window actually disappears.
    Activate-Window $Dialog.hwnd
    $buttons = @(Get-ChildWindows $Dialog.hwnd -VisibleOnly |
        Where-Object { $_.class -in @('TcxButton', 'Button') } |
        Sort-Object left)
    if ($buttons.Count -ge 2) {
        $noButton = $buttons[$buttons.Count - 1]
        Click-Screen ([int](($noButton.left + $noButton.right) / 2)) ([int](($noButton.top + $noButton.bottom) / 2))
    } else {
        $rect = Get-WindowRectangle $Dialog.hwnd
        Click-Screen ($rect.Right - 66) ($rect.Bottom - 28)
    }
    Wait-WindowClosed $Dialog.hwnd 15
}

function Activate-Window([IntPtr]$Handle, [switch]$Maximize) {
    if ($Maximize) { [void][DvpWorkerWin32]::ShowWindow($Handle, 3) }
    [void][DvpWorkerWin32]::BringWindowToTop($Handle)
    [void][DvpWorkerWin32]::SetForegroundWindow($Handle)
    Start-Sleep -Milliseconds 250
}

function Send-Keys([string]$Keys) {
    [System.Windows.Forms.SendKeys]::SendWait($Keys)
    Start-Sleep -Milliseconds 250
}

function Click-Screen([int]$X, [int]$Y, [switch]$Right) {
    [void][DvpWorkerWin32]::SetCursorPos($X, $Y)
    Start-Sleep -Milliseconds 100
    if ($Right) {
        [DvpWorkerWin32]::mouse_event(0x0008, 0, 0, 0, [UIntPtr]::Zero)
        [DvpWorkerWin32]::mouse_event(0x0010, 0, 0, 0, [UIntPtr]::Zero)
    } else {
        [DvpWorkerWin32]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
        [DvpWorkerWin32]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
    }
    Start-Sleep -Milliseconds 250
}

function Save-Screenshot([string]$Path) {
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

function Stop-IspSoft {
    Get-Process NewISPSoft -ErrorAction SilentlyContinue | Stop-Process -Force
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Process NewISPSoft -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 250
    }
    if (Get-Process NewISPSoft -ErrorAction SilentlyContinue) {
        throw 'ISPSoft did not terminate before project restoration.'
    }
    Start-Sleep -Seconds 1
}

function Stop-IspSoftWithoutSaving {
    $processes = @(Get-Process NewISPSoft -ErrorAction SilentlyContinue)
    if ($processes.Count -eq 0) { return }
    $mainWindows = @(Get-TopWindows -ClassName 'TMainFrm' -VisibleOnly)
    if ($mainWindows.Count -gt 0) {
        $main = $mainWindows[0]
        Activate-Window $main.hwnd
        Send-Keys '%{F4}'
        $deadline = (Get-Date).AddSeconds(10)
        while ((Get-Process NewISPSoft -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) {
            $dialogs = @(Get-TopWindows -ClassName '#32770' -VisibleOnly)
            if ($dialogs.Count -gt 0) {
                $dialog = $dialogs[0]
                Activate-Window $dialog.hwnd
                $buttons = @(Get-ChildWindows $dialog.hwnd -VisibleOnly |
                    Where-Object { $_.class -in @('TcxButton', 'Button') } |
                    Sort-Object left)
                $discard = @($buttons | Where-Object {
                    $_.title -match '^(No|否|不保存|Don.t Save)'
                }) | Select-Object -First 1
                if ($null -eq $discard -and $buttons.Count -ge 3) {
                    $discard = $buttons[$buttons.Count - 2]
                } elseif ($null -eq $discard -and $buttons.Count -ge 2) {
                    $discard = $buttons[$buttons.Count - 1]
                }
                if ($null -ne $discard) {
                    Click-Screen ([int](($discard.left + $discard.right) / 2)) ([int](($discard.top + $discard.bottom) / 2))
                }
            }
            Start-Sleep -Milliseconds 250
        }
    }
    if (Get-Process NewISPSoft -ErrorAction SilentlyContinue) {
        Write-WorkerLog 'graceful ISPSoft close did not finish; using bounded forced termination'
        Stop-IspSoft
    }
}

function Restore-CleanProject {
    Stop-IspSoft
    if (-not (Test-Path -LiteralPath $templateProjectFile)) {
        throw "Clean ISPSoft template is missing: $templateProjectFile"
    }
    Copy-TreeWithRobocopy $TemplateRoot $ProjectRoot -Mirror
    if (-not (Test-Path -LiteralPath $projectFile)) { throw 'Restored ISPSoft project file is missing.' }
    $sourceHash = (Get-FileHash -LiteralPath $templateProjectFile -Algorithm SHA256).Hash
    $targetHash = (Get-FileHash -LiteralPath $projectFile -Algorithm SHA256).Hash
    if ($sourceHash -ne $targetHash) { throw 'Restored project hash differs from the clean template.' }
}

function Open-IspSoftProject([switch]$DoNotRestore) {
    if (-not $DoNotRestore) { Restore-CleanProject } else { Stop-IspSoft }
    # ISPSoft 3.24 does not consistently bind Ctrl+O to the project-open
    # dialog when its main window has only just appeared.  Opening the .isp
    # document through its registered file association is deterministic and
    # also makes the intended project explicit at process launch.
    $process = Start-Process -FilePath $projectFile -PassThru
    $startedAt = Get-Date
    $deadline = $startedAt.AddSeconds($IspSoftStartupTimeoutSeconds)
    $nextDiagnosticAt = $startedAt.AddSeconds(10)
    $main = $null
    do {
        $matches = @(Get-TopWindows -ClassName 'TMainFrm' -VisibleOnly)
        if ($matches.Count -gt 0) { $main = $matches[0]; break }
        if ((Get-Date) -ge $nextDiagnosticAt) {
            $elapsed = [int]((Get-Date) - $startedAt).TotalSeconds
            $processCount = @(Get-Process NewISPSoft -ErrorAction SilentlyContinue).Count
            $windowSummary = @(
                Get-TopWindows | ForEach-Object {
                    '{0}:{1}:visible={2}' -f $_.class, $_.title, $_.visible
                }
            ) -join '; '
            if (-not $windowSummary) { $windowSummary = 'none' }
            Write-WorkerLog (
                "ISPSoft startup pending after ${elapsed}s; processes=$processCount; windows=$windowSummary"
            )
            $nextDiagnosticAt = (Get-Date).AddSeconds(10)
        }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    if ($null -eq $main) {
        $elapsed = [int]((Get-Date) - $startedAt).TotalSeconds
        $processCount = @(Get-Process NewISPSoft -ErrorAction SilentlyContinue).Count
        throw "ISPSoft did not expose its main project window within ${elapsed}s (processes=$processCount)."
    }
    Write-WorkerLog (
        'ISPSoft main project window became ready after {0:N1}s' -f ((Get-Date) - $startedAt).TotalSeconds
    )
    Activate-Window $main.hwnd -Maximize
    # Stop-IspSoft deliberately terminates the previous disposable project so
    # every job can restore the byte-identical clean template.  ISPSoft may
    # consequently offer to recover the interrupted edit on the next launch.
    # Reject that stale recovery and continue opening the explicit .isp path.
    $titleDeadline = (Get-Date).AddSeconds(30)
    while ($main.title -notlike "$expectedProjectTitle*" -and (Get-Date) -lt $titleDeadline) {
        # The main frame can become visible a few seconds before the recovery
        # dialog.  Poll both until the requested project title is observable.
        $dialogs = @(Get-TopWindows -ClassName '#32770' -VisibleOnly)
        if ($main.title -eq 'Delta ISPSoft' -and $dialogs.Count -eq 1) {
            $dialog = $dialogs[0]
            Activate-Window $dialog.hwnd
            Reject-IspSoftRecovery $dialog
        }
        Start-Sleep -Milliseconds 250
        $windows = @(Get-TopWindows -ClassName 'TMainFrm' -VisibleOnly)
        if ($windows.Count -gt 0) { $main = $windows[0] }
    }
    # Recovery can restore a previous project having the same display title.
    # Reject a recovery prompt even when the title already matches; otherwise
    # a prior imported POU can survive the byte-identical template restore.
    foreach ($dialog in @(Get-TopWindows -ClassName '#32770' -VisibleOnly)) {
        $texts = @(Get-ChildWindows $dialog.hwnd -VisibleOnly |
            Where-Object { $_.title } | ForEach-Object { $_.title })
        if (($texts -join ' ') -match 'recover|recovery|恢复|復原') {
            Reject-IspSoftRecovery $dialog
        }
    }
    if ($main.title -notlike "$expectedProjectTitle*") { throw "ISPSoft opened an unexpected project: $($main.title)" }
    Activate-Window $main.hwnd -Maximize
    $size = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    if ($size.Width -ne 1500 -or $size.Height -ne 900) {
        throw "Worker requires the calibrated 1500x900 interactive desktop, found $($size.Width)x$($size.Height)."
    }
    return $main
}

function Get-VisibleUnexpectedDialog {
    $dialogs = @(Get-TopWindows -ClassName '#32770' -VisibleOnly)
    if ($dialogs.Count -eq 0) { return $null }
    $dialog = $dialogs[0]
    $texts = @(Get-ChildWindows $dialog.hwnd -VisibleOnly | Where-Object { $_.title } | ForEach-Object { $_.title })
    return [ordered]@{ hwnd=$dialog.hwnd; title=$dialog.title; texts=$texts }
}

function Remove-PlaceholderMain([IntPtr]$MainHandle, [int]$TreeY = $placeholderMainY) {
    Activate-Window $MainHandle -Maximize
    # The calibrated DVP_CLEAN template contains one placeholder MAIN so that
    # ISPSoft can create and save the project initially.  Delete that exact POU
    # before importing the content-addressed executable MAIN for this job.
    Click-Screen 115 $TreeY -Right
    Send-Keys 'd'
    try {
        $confirm = Wait-TopWindow '#32770' 3
    } catch {
        # On a busy remote desktop the context menu can receive the right-click
        # before it accepts the mnemonic.  Close it, reopen it, and click the
        # calibrated third menu row (Delete).  The worker already enforces the
        # fixed 1500x900 desktop used by these project-tree coordinates.
        Send-Keys '{ESC}'
        Click-Screen 115 $TreeY -Right
        Start-Sleep -Milliseconds 500
        Click-Screen 190 ($TreeY + 62)
        $confirm = Wait-TopWindow '#32770' 15
    }
    $texts = @(Get-ChildWindows $confirm.hwnd -VisibleOnly |
        Where-Object { $_.title } | ForEach-Object { $_.title })
    if (($texts -join ' ') -notmatch 'POU') {
        throw "ISPSoft exposed an unexpected dialog while deleting placeholder MAIN: $($texts -join ' | ')"
    }
    Activate-Window $confirm.hwnd
    Send-Keys '{ENTER}'
    Wait-WindowClosed $confirm.hwnd 15
    Activate-Window $MainHandle
    Send-Keys '^{s}'
    Start-Sleep -Seconds 1
}

function Remove-PlaceholderFunction([IntPtr]$MainHandle) {
    if ($placeholderFunctionY -le 0) { return }
    Activate-Window $MainHandle -Maximize
    Click-Screen 115 $placeholderFunctionY -Right
    Send-Keys 'd'
    $confirm = Wait-TopWindow '#32770' 15
    $texts = @(Get-ChildWindows $confirm.hwnd -VisibleOnly |
        Where-Object { $_.title } | ForEach-Object { $_.title })
    $message = $texts -join ' | '
    if ($message -notmatch 'DVP_VALIDATION_CANARY|POU') {
        throw "ISPSoft exposed an unexpected dialog while deleting the AS placeholder FB: $message"
    }
    Activate-Window $confirm.hwnd
    Send-Keys '{ENTER}'
    Wait-WindowClosed $confirm.hwnd 15
    Activate-Window $MainHandle
    Send-Keys '^{s}'
    Start-Sleep -Seconds 1
}

function Select-DeltaCommunicationDriver([IntPtr]$MainHandle) {
    Activate-Window $MainHandle -Maximize
    # Delta's documented workflow binds an ISPSoft project to a COMMGR driver
    # through Tools -> Communication Settings.  Restoring the clean project can
    # clear that binding, so make it explicit and verify the dialog readback for
    # every immutable job.
    # The localized Delphi menu does not consistently honor Alt+T after an AS
    # project opens.  Use the calibrated Tools -> Communication Settings item
    # on the fixed worker desktop, then verify the exact dialog class below.
    Click-Screen 340 40
    Start-Sleep -Milliseconds 300
    Click-Screen 380 64
    $dialog = Wait-TopWindow 'Tfrm_SelComDriver' 15
    Activate-Window $dialog.hwnd
    $driverEdits = @(Get-ChildWindows $dialog.hwnd -ClassName 'TcxCustomComboBoxInnerEdit' -VisibleOnly |
        Where-Object { $_.top -lt 320 } | Sort-Object top, left)
    if ($driverEdits.Count -ne 1) {
        throw "ISPSoft communication settings exposed $($driverEdits.Count) driver edits instead of one."
    }
    $driverValue = ([System.Windows.Automation.AutomationElement]::FromHandle(
        $driverEdits[0].hwnd
    )).Current.Name
    if ($driverValue -ne $expectedDriver) {
        Click-Screen 790 300
        Start-Sleep -Milliseconds 300
        Send-Keys '{HOME}'
        # The production profile is frozen to exactly two lexically sorted
        # drivers: AS228T_SIM then DVP48ES300R_SIM.  Commit the selection before
        # reading the edit control; this DevExpress combo keeps exposing the old
        # value through UI Automation while its drop-down remains open.
        if ($expectedDriver -eq 'DVP48ES300R_SIM') {
            Send-Keys '{DOWN}'
        }
        Send-Keys '{ENTER}'
        Start-Sleep -Milliseconds 500
        $driverEdits = @(Get-ChildWindows $dialog.hwnd -ClassName 'TcxCustomComboBoxInnerEdit' -VisibleOnly |
            Where-Object { $_.top -lt 320 } | Sort-Object top, left)
        if ($driverEdits.Count -eq 1) {
            $driverValue = ([System.Windows.Automation.AutomationElement]::FromHandle(
                $driverEdits[0].hwnd
            )).Current.Name
        }
    }
    if ($driverEdits.Count -ne 1 -or $driverValue -ne $expectedDriver) {
        throw "ISPSoft did not select the required COMMGR driver $expectedDriver."
    }
    $buttons = @(Get-ChildWindows $dialog.hwnd -ClassName 'TcxButton' -VisibleOnly | Sort-Object left)
    if ($buttons.Count -lt 3) { throw 'ISPSoft communication settings buttons were not found.' }
    # The middle button is the calibrated confirmation control at 1500x900.
    # A direct pointer click is required because this DevExpress button does
    # not expose a stable InvokePattern through UI Automation.
    Click-Screen 670 486
    Wait-WindowClosed $dialog.hwnd 15
    Start-Sleep -Seconds 2
    Activate-Window $MainHandle
}

function Import-IspSoftUnit([IntPtr]$MainHandle, [ValidateSet('function','program')]$Kind, [string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "ISPSoft import unit is missing: $Path" }
    Activate-Window $MainHandle -Maximize
    $folderY = if ($Kind -eq 'function') { $functionFolderY } else { $programFolderY }
    Click-Screen 76 $folderY -Right
    Send-Keys '{END}{ENTER}'
    $dialog = Wait-TopWindow '#32770' 15
    Activate-Window $dialog.hwnd
    # Windows PowerShell 5.1 reads a BOM-less UTF-8 script through the active
    # ANSI code page.  Build the localized title fragment from Unicode code
    # points so this guard remains reliable without embedding CJK literals.
    $expectedTitleFragment = if ($Kind -eq 'function') {
        -join ([char[]](0x529F, 0x80FD, 0x5757))
    } else {
        -join ([char[]](0x7A0B, 0x5E8F))
    }
    if ($dialog.title -notlike "*$expectedTitleFragment*") {
        throw "ISPSoft opened the wrong import dialog for ${Kind}: $($dialog.title)"
    }
    # The standard dialog does not reliably focus its file-name edit.  Setting
    # the lower visible Edit control explicitly prevents the previous path
    # from being re-imported when the function and program packages are loaded
    # consecutively.
    $fileEdits = @(Get-ChildWindows $dialog.hwnd -ClassName 'Edit' -VisibleOnly |
        Where-Object { $_.top -gt 450 } | Sort-Object top, left)
    if ($fileEdits.Count -ne 1) { throw "ISPSoft import dialog exposed $($fileEdits.Count) file-name edits instead of one." }
    Click-Screen 780 523
    Send-Keys '^a'
    # Clipboard redirection is disabled for the worker session.  Pasting the
    # absolute ASCII path therefore bypasses the active Chinese IME, which can
    # otherwise retain "M.MPU" as an uncommitted composition in this dialog.
    [System.Windows.Forms.Clipboard]::Clear()
    [System.Windows.Forms.Clipboard]::SetText($Path)
    if ([System.Windows.Forms.Clipboard]::GetText() -ne $Path) {
        throw 'Windows clipboard readback differs from the requested import path.'
    }
    Send-Keys '^v'
    Start-Sleep -Milliseconds 300
    # The Delphi file picker paints its Open button without a stable child
    # HWND, so click the calibrated default-button position relative to the
    # dialog rectangle after verifying the file-name edit above.
    Send-Keys '%o'
    Wait-WindowClosed $dialog.hwnd 15
    Start-Sleep -Seconds 3
    $unexpected = Get-VisibleUnexpectedDialog
    if ($null -ne $unexpected) {
        throw "ISPSoft rejected the $Kind import: $($unexpected.title) $($unexpected.texts -join ' | ')"
    }
    Activate-Window $MainHandle
    Send-Keys '^{s}'
    Start-Sleep -Seconds 2
}

function Enable-StartupCheckbox([IntPtr]$Handle) {
    try {
        $element = [System.Windows.Automation.AutomationElement]::FromHandle($Handle)
        $patternObject = $null
        if ($element.TryGetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern, [ref]$patternObject)) {
            $toggle = [System.Windows.Automation.TogglePattern]$patternObject
            if ($toggle.Current.ToggleState -eq [System.Windows.Automation.ToggleState]::Off) { $toggle.Toggle() }
        }
    } catch {
        Write-WorkerLog "startup checkbox state could not be read: $($_.Exception.Message)"
    }
}

function Assign-MainToPeriodicTask([IntPtr]$MainHandle) {
    Activate-Window $MainHandle -Maximize
    Click-Screen 76 230 -Right
    Send-Keys '{HOME}{ENTER}'
    $dialog = Wait-TopWindow 'Tfrm_Task' 15
    Activate-Window $dialog.hwnd
    $innerLists = @(Get-ChildWindows $dialog.hwnd -ClassName 'TcxInnerListBox' -VisibleOnly | Sort-Object left)
    if ($innerLists.Count -ne 2) { throw "Work manager exposed $($innerLists.Count) POU lists instead of two." }
    $unassigned = $innerLists[0]
    $rightButtons = @(Get-ChildWindows $dialog.hwnd -ClassName 'TcxButton' -VisibleOnly | Where-Object { $_.title -eq '>' })
    $leftButtons = @(Get-ChildWindows $dialog.hwnd -ClassName 'TcxButton' -VisibleOnly | Where-Object { $_.title -eq '<' })
    if ($rightButtons.Count -ne 1 -or $leftButtons.Count -ne 1) { throw 'Work manager assignment buttons were not found.' }
    Click-Screen ($unassigned.left + 20) ($unassigned.top + 14)
    Start-Sleep -Milliseconds 300
    if (-not [DvpWorkerWin32]::IsWindowEnabled($rightButtons[0].hwnd)) {
        throw 'MAIN was not exposed as an unassigned POU after import.'
    }
    Click-Screen ($rightButtons[0].left + 12) ($rightButtons[0].top + 12)
    Start-Sleep -Milliseconds 500
    # TcxButton keeps reporting enabled after the only POU visibly moves to
    # the assigned list.  Do not infer state from that unreliable flag; the
    # later image-identity handshake proves that MAIN actually executes.
    $checkboxes = @(Get-ChildWindows $dialog.hwnd -ClassName 'TcxCheckBox' -VisibleOnly)
    if ($checkboxes.Count -gt 0) { Enable-StartupCheckbox $checkboxes[0].hwnd }
    $buttons = @(Get-ChildWindows $dialog.hwnd -ClassName 'TcxButton' -VisibleOnly | Where-Object { $_.top -lt 300 } | Sort-Object top, left)
    if ($buttons.Count -eq 0) { throw 'Work manager confirmation button was not found.' }
    $confirm = $buttons[0]
    Click-Screen ([int](($confirm.left + $confirm.right) / 2)) ([int](($confirm.top + $confirm.bottom) / 2))
    Wait-WindowClosed $dialog.hwnd 15
    Activate-Window $MainHandle
    Send-Keys '^{s}'
}

function Set-UInt32([byte[]]$Buffer, [int]$Offset, [uint32]$Value) {
    [BitConverter]::GetBytes($Value).CopyTo($Buffer, $Offset)
}

function Read-RemoteListText([IntPtr]$ListView, [int]$Item, [int]$SubItem) {
    $owner = [uint32]0
    [void][DvpWorkerWin32]::GetWindowThreadProcessId($ListView, [ref]$owner)
    $process = [DvpWorkerWin32]::OpenProcess(0x0438, $false, $owner)
    if ($process -eq [IntPtr]::Zero) { throw "OpenProcess failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }
    $textBytes = 4096
    $structBytes = 60
    $remoteText = [DvpWorkerWin32]::VirtualAllocEx($process, [IntPtr]::Zero, $textBytes, 0x3000, 0x04)
    $remoteStruct = [DvpWorkerWin32]::VirtualAllocEx($process, [IntPtr]::Zero, $structBytes, 0x3000, 0x04)
    try {
        if ($remoteText -eq [IntPtr]::Zero -or $remoteStruct -eq [IntPtr]::Zero) { throw 'VirtualAllocEx failed.' }
        if ($remoteText.ToInt64() -gt [uint32]::MaxValue) { throw 'x86 text allocation exceeded pointer range.' }
        $itemBuffer = New-Object byte[] $structBytes
        Set-UInt32 $itemBuffer 0 1
        Set-UInt32 $itemBuffer 4 $Item
        Set-UInt32 $itemBuffer 8 $SubItem
        Set-UInt32 $itemBuffer 20 ([uint32]$remoteText.ToInt64())
        Set-UInt32 $itemBuffer 24 ($textBytes / 2)
        $written = [IntPtr]::Zero
        if (-not [DvpWorkerWin32]::WriteProcessMemory($process, $remoteStruct, $itemBuffer, $itemBuffer.Length, [ref]$written)) {
            throw 'WriteProcessMemory failed.'
        }
        $unicode = [DvpWorkerWin32]::IsWindowUnicode($ListView)
        $message = if ($unicode) { [uint32]0x1073 } else { [uint32]0x102D }
        [void][DvpWorkerWin32]::SendMessage($ListView, $message, [IntPtr]$Item, $remoteStruct)
        $textBuffer = New-Object byte[] $textBytes
        $read = [IntPtr]::Zero
        if (-not [DvpWorkerWin32]::ReadProcessMemory($process, $remoteText, $textBuffer, $textBuffer.Length, [ref]$read)) {
            throw 'ReadProcessMemory failed.'
        }
        $encoding = if ($unicode) { [Text.Encoding]::Unicode } else { [Text.Encoding]::GetEncoding(936) }
        return $encoding.GetString($textBuffer).Split([char]0)[0]
    } finally {
        if ($remoteStruct -ne [IntPtr]::Zero) { [void][DvpWorkerWin32]::VirtualFreeEx($process, $remoteStruct, 0, 0x8000) }
        if ($remoteText -ne [IntPtr]::Zero) { [void][DvpWorkerWin32]::VirtualFreeEx($process, $remoteText, 0, 0x8000) }
        [void][DvpWorkerWin32]::CloseHandle($process)
    }
}

function Read-CompileSummary([IntPtr]$MainHandle) {
    $lists = @(Get-ChildWindows $MainHandle -ClassName 'TListView')
    $diagnostics = New-Object System.Collections.ArrayList
    $errorWord = -join ([char[]](0x9519, 0x8BEF))
    $warningWord = -join ([char[]](0x8B66, 0x544A))
    foreach ($list in $lists) {
        $count = [DvpWorkerWin32]::SendMessage($list.hwnd, 0x1004, [IntPtr]::Zero, [IntPtr]::Zero).ToInt32()
        $rows = @()
        if ($count -gt 0) {
            $rows = @(for ($index = 0; $index -lt $count; $index++) { Read-RemoteListText $list.hwnd $index 0 })
        }
        [void]$diagnostics.Add([ordered]@{ hwnd=[string]$list.hwnd; count=$count; rows=@($rows) })
        if ($count -lt 2) { continue }
        $errorCount = $null
        $warningCount = $null
        foreach ($row in $rows) {
            $countMatch = [regex]::Match([string]$row, '^\s*(\d+)')
            if (-not $countMatch.Success) { continue }
            if ([string]$row -match [regex]::Escape($errorWord) -or [string]$row -match '(?i)errors?') {
                $errorCount = [int]$countMatch.Groups[1].Value
            }
            if ([string]$row -match [regex]::Escape($warningWord) -or [string]$row -match '(?i)warnings?') {
                $warningCount = [int]$countMatch.Groups[1].Value
            }
        }
        if ($null -ne $errorCount -and $null -ne $warningCount) {
            return [ordered]@{
                errors = $errorCount
                warnings = $warningCount
                rows = @($rows)
            }
        }
    }
    throw ('ISPSoft compile summary was not machine-readable: ' + (
        $diagnostics | ConvertTo-Json -Depth 5 -Compress
    ))
}

function Compile-IspSoftProject([IntPtr]$MainHandle, [string]$EvidenceRoot) {
    Activate-Window $MainHandle -Maximize
    Send-Keys '^{F7}'
    Start-Sleep -Seconds 6
    Save-Screenshot (Join-Path $EvidenceRoot 'ispsoft_compile.png')
    $summary = Read-CompileSummary $MainHandle
    return $summary
}

function Invoke-DownloadAndRun([IntPtr]$MainHandle, [string]$EvidenceRoot, [string]$CaseId) {
    Activate-Window $MainHandle -Maximize
    Send-Keys '^{F12}'
    $confirm = Wait-TopWindow '#32770' 15
    Activate-Window $confirm.hwnd
    Send-Keys '{ENTER}'
    Wait-WindowClosed $confirm.hwnd 15
    Start-Sleep -Seconds 2

    Activate-Window $MainHandle
    Send-Keys '^{F8}'
    $download = Wait-TopWindow 'TForm_UpDownloader' 30
    Activate-Window $download.hwnd
    $buttons = @(Get-ChildWindows $download.hwnd -ClassName 'TcxButton' -VisibleOnly | Sort-Object left)
    if ($buttons.Count -lt 2) { throw 'ISPSoft download window has fewer than two buttons.' }
    [ordered]@{
        captured_at = (Get-Date).ToString('o')
        window = $download
        buttons = @($buttons)
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (
        Join-Path $EvidenceRoot ("download_ui_{0}.json" -f $CaseId)
    ) -Encoding UTF8
    Save-Screenshot (Join-Path $EvidenceRoot ("ispsoft_download_{0}_before.png" -f $CaseId))
    # EnumChildWindows returns these DevExpress controls in z-order rather
    # than screen order.  On ISPSoft 3.24 that put "Close" before "Start
    # transfer" and silently left the simulator running the previous image.
    # Select the calibrated left/right controls by their numeric coordinates.
    $orderedButtons = @($buttons | Sort-Object { [int]$_.left })
    $transferButton = $orderedButtons[0]
    $closeButton = $orderedButtons[$orderedButtons.Count - 1]
    # DevExpress TcxButton controls do not consistently honor BM_CLICK when
    # ISPSoft is reached through an interactive RDP session.  A real pointer
    # click is required for the downloader to start its transfer state machine.
    Click-Screen ([int](($transferButton.left + $transferButton.right) / 2)) ([int](($transferButton.top + $transferButton.bottom) / 2))
    # TcxButton exposes neither its caption nor its enabled transition reliably
    # through Win32/UI Automation.  The DVP simulator transfer for this bounded
    # project takes under ten seconds in calibration.  Keep the dialog open for
    # a conservative stabilization window; a still-running transfer cannot be
    # closed and is therefore rejected by Wait-WindowClosed below.
    $deadline = (Get-Date).AddSeconds(15)
    do {
        $unexpected = Get-VisibleUnexpectedDialog
        if ($null -ne $unexpected) {
            throw "ISPSoft download reported a dialog: $($unexpected.title) $($unexpected.texts -join ' | ')"
        }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    Save-Screenshot (Join-Path $EvidenceRoot ("ispsoft_download_{0}_after.png" -f $CaseId))
    Click-Screen ([int](($closeButton.left + $closeButton.right) / 2)) ([int](($closeButton.top + $closeButton.bottom) / 2))
    Wait-WindowClosed $download.hwnd 15

    Activate-Window $MainHandle
    Send-Keys '^{F11}'
    $runConfirm = Wait-TopWindow '#32770' 15
    Activate-Window $runConfirm.hwnd
    Send-Keys '{ENTER}'
    Wait-WindowClosed $runConfirm.hwnd 15
    Start-Sleep -Seconds 2
}

function Invoke-RuntimeCase([string]$SuitePath, [string]$CaseId, [string]$EvidenceRoot) {
    $resultPath = Join-Path $EvidenceRoot ("runtime_{0}.json" -f $CaseId)
    $stdoutPath = Join-Path $EvidenceRoot ("runtime_{0}.stdout.log" -f $CaseId)
    $stderrPath = Join-Path $EvidenceRoot ("runtime_{0}.stderr.log" -f $CaseId)
    $exe = 'C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
    $arguments = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"{0}"' -f $runtimeRunner),
        '-SuitePath', ('"{0}"' -f $SuitePath), '-CaseId', $CaseId,
        '-OutputPath', ('"{0}"' -f $resultPath), '-Target', ([string]$script:currentTarget),
        '-DriverName', $expectedDriver
    )
    $process = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    if (-not $process.WaitForExit([Math]::Max(10, $RuntimeCaseTimeoutSeconds) * 1000)) {
        try { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue } catch {}
        throw "COMMGR runner timed out after $RuntimeCaseTimeoutSeconds seconds for case $CaseId."
    }
    # Flush asynchronously redirected stdout/stderr before reading the result.
    $process.WaitForExit()
    $process.Refresh()
    if (-not (Test-Path -LiteralPath $resultPath)) { throw "COMMGR runner returned no result for case $CaseId (exit $($process.ExitCode))." }
    return Get-Content -LiteralPath $resultPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function New-BaseResult([object]$Manifest) {
    $gates = @(
        [ordered]@{name='ispsoft_compile'; status='inconclusive'},
        [ordered]@{name='commgr_connect'; status='inconclusive'},
        [ordered]@{name=$runtimeGate; status='inconclusive'}
    )
    if ([string]$Manifest.delivery_mode -eq 'downloadable_project') {
        $gates += ,[ordered]@{name='deployment_compile'; status='inconclusive'}
    }
    return [ordered]@{
        schema_version = 1
        worker_id = if ($Manifest.worker_id) { [string]$Manifest.worker_id } else { $WorkerId }
        job_id = [string]$Manifest.job_id
        task_id = [string]$Manifest.task_id
        role = [string]$Manifest.role
        candidate_sha256 = [string]$Manifest.candidate_sha256
        image_identity_sha256 = [string]$Manifest.image_identity_sha256
        target = [string]$Manifest.target
        status = 'inconclusive'
        public_summary = "$($Manifest.target) validation did not complete"
        tool_version = $toolVersion
        gates = $gates
        passed_requirement_ids = @()
        evidence = @()
        started_at = (Get-Date).ToString('o')
    }
}

function Test-JobHashes([string]$JobRoot, [object]$Manifest) {
    $pairs = @(
        @('candidate.st', [string]$Manifest.candidate_sha256),
        @('candidate.FBU', [string]$Manifest.function_unit_sha256),
        @('MAIN.MPU', [string]$Manifest.program_unit_sha256),
        @('suite.json', [string]$Manifest.suite_sha256)
    )
    if ([string]$Manifest.candidate_language -eq 'ld') {
        $pairs += ,@('candidate.ld.json', [string]$Manifest.ladder_ir_sha256)
        $pairs += ,@('candidate.ispsoft.ld.src', [string]$Manifest.native_ld_source_sha256)
    }
    if ([string]$Manifest.delivery_mode -eq 'downloadable_project') {
        $pairs += ,@('deployment.MPU', [string]$Manifest.deployment_program_sha256)
        $pairs += ,@('engineering_mapping.json', [string]$Manifest.engineering_mapping_sha256)
        if (-not $Manifest.project_name) { throw 'Deployment project name is missing.' }
    }
    foreach ($pair in $pairs) {
        $path = Join-Path $JobRoot $pair[0]
        if (-not (Test-Path -LiteralPath $path)) { throw "Job artifact is missing: $($pair[0])" }
        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $pair[1]) { throw "Job artifact hash mismatch: $($pair[0])" }
    }
    $suite = Get-Content -LiteralPath (Join-Path $JobRoot 'suite.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$suite.dvp_mapping.image_identity.sha256 -ne [string]$Manifest.image_identity_sha256) {
        throw 'Suite image identity differs from the immutable job manifest.'
    }
    return $suite
}

function Publish-Result([string]$LocalJob, [object]$Result) {
    $Result.finished_at = (Get-Date).ToString('o')
    $localResult = Join-Path $LocalJob 'result.json'
    $Result | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $localResult -Encoding UTF8
    $resultRoot = Join-Path $SpoolRoot 'results'
    New-Item -ItemType Directory -Path $resultRoot -Force | Out-Null
    $destination = Join-Path $resultRoot $Result.job_id
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Write-WorkerLog "publishing $($Result.job_id) to the shared result directory"
    $evidenceFiles = @(Get-ChildItem -LiteralPath $LocalJob -File | Where-Object {
        $_.Name -eq 'manifest.json' -or
        $_.Name -in @(
            'downloadable_project.zip','engineering_mapping.json',
            'deployment_main.st','field_acceptance_checklist.json'
        ) -or
        $_.Extension -eq '.png' -or $_.Name -like 'runtime_*.json' -or
        $_.Name -like 'runtime_*.log' -or $_.Name -like 'download_ui_*.json'
    } | Sort-Object Name)
    foreach ($file in $evidenceFiles) {
        Copy-OneFileWithCmd $file.FullName (Join-Path $destination $file.Name)
    }
    # A direct copy can expose result.json before the redirected-drive transfer
    # has finished.  Publish under a private name and rename only after all
    # bytes are present, so result.json is the actual completion marker.
    $temporaryResult = Join-Path $destination ('result.json.tmp-' + [Guid]::NewGuid().ToString('N'))
    try {
        Copy-OneFileWithCmd $localResult $temporaryResult
        Move-Item -LiteralPath $temporaryResult -Destination (Join-Path $destination 'result.json') -Force
    } finally {
        if (Test-Path -LiteralPath $temporaryResult) {
            Remove-Item -LiteralPath $temporaryResult -Force
        }
    }
    $localCompletedRoot = Join-Path $WorkerRoot 'completed'
    New-Item -ItemType Directory -Path $localCompletedRoot -Force | Out-Null
    $Result | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $localCompletedRoot ($Result.job_id + '.json')) -Encoding UTF8
}

function Complete-JobMaintenance {
    $completed = 0
    try {
        if (Test-Path -LiteralPath $metricsPath) {
            $metrics = Get-Content -LiteralPath $metricsPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $completed = [int]$metrics.completed_jobs
        }
    } catch { $completed = 0 }
    $completed += 1
    [ordered]@{
        completed_jobs = $completed
        last_completed_at = (Get-Date).ToUniversalTime().ToString('o')
        process_id = $PID
        worker_id = $WorkerId
    } | ConvertTo-Json | Set-Content -LiteralPath $metricsPath -Encoding UTF8

    # ISPSoft itself is recreated from a byte-identical clean project for every
    # job.  Also recycle the persistent COMMGR/simulator desktop periodically,
    # so leaked GUI handles cannot accumulate indefinitely in a long-lived VM.
    if (($completed % 25) -eq 0) {
        Write-WorkerHeartbeat 'draining' '' 'scheduled_application_recycle'
        Write-WorkerLog "completed $completed jobs; recycling COMMGR and simulator processes"
        Stop-IspSoft
        Get-Process DVPSimulator_ES3,AS200Simulator,COMMGR -ErrorAction SilentlyContinue |
            Stop-Process -Force -ErrorAction SilentlyContinue
        exit 75
    }
}

function Invoke-OneJob([string]$SharedJob, [string]$LocalJob) {
    $jobId = Split-Path -Leaf $SharedJob
    $localJob = $LocalJob
    $manifestPath = Join-Path $localJob 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'Claimed job has no manifest.' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Set-TargetConfiguration ([string]$manifest.target)
    # Never reuse the mutable ISPSoft project directory across jobs.  The
    # clean template remains immutable while every job receives a disposable
    # project copy, preventing POU and recovery-state contamination.
    $projectLeaf = Split-Path -Leaf $script:templateProjectFile
    $script:ProjectRoot = Join-Path (Join-Path (Join-Path $WorkerRoot 'projects') ([string]$manifest.target)) $jobId
    $script:projectFile = Join-Path $script:ProjectRoot $projectLeaf
    $script:currentTarget = [string]$manifest.target
    $result = New-BaseResult $manifest
    try {
        if ($manifest.job_id -ne $jobId -or $manifest.target -notin @('DVP48ES300R', 'AS228T-A')) { throw 'Job identity or target is invalid.' }
        Write-WorkerHeartbeat 'processing' $jobId 'input_check' ([string]$manifest.target)
        Write-WorkerLog "job $jobId verifying immutable input hashes"
        $suite = Test-JobHashes $localJob $manifest
        # ISPSoft's Delphi import dialog truncates long file names.  Stage the
        # already hash-verified packages at fixed short paths; the worker is
        # serial, so these scratch names cannot overlap another job.
        $importRoot = 'C:\DeltaPLCValidation\import'
        New-Item -ItemType Directory -Path $importRoot -Force | Out-Null
        $shortFunction = Join-Path $importRoot 'C.FBU'
        # ISPSoft also caches an extracted source unit by the outer package
        # path across process restarts.  A content-addressed short file name
        # prevents an old FBU or MPU from being replayed for a later job.
        $shortProgram = Join-Path $importRoot (
            'P' + ([string]$manifest.program_unit_sha256).Substring(0, 12) + '.MPU'
        )
        $shortDeployment = $null
        Copy-Item -LiteralPath (Join-Path $localJob 'candidate.FBU') -Destination $shortFunction -Force
        Copy-Item -LiteralPath (Join-Path $localJob 'MAIN.MPU') -Destination $shortProgram -Force
        if ([string]$manifest.delivery_mode -eq 'downloadable_project') {
            $shortDeployment = Join-Path $importRoot (
                'D' + ([string]$manifest.deployment_program_sha256).Substring(0, 12) + '.MPU'
            )
            Copy-Item -LiteralPath (Join-Path $localJob 'deployment.MPU') -Destination $shortDeployment -Force
        }
        if ((Get-FileHash -LiteralPath $shortFunction -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.function_unit_sha256 -or
            (Get-FileHash -LiteralPath $shortProgram -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.program_unit_sha256) {
            throw 'Short-path import staging changed a source-unit package.'
        }
        if ($null -ne $shortDeployment -and
            (Get-FileHash -LiteralPath $shortDeployment -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.deployment_program_sha256) {
            throw 'Short-path deployment package hash mismatch.'
        }
        $extractionCache = Join-Path $importRoot 'Unzipped.src'
        if (Test-Path -LiteralPath $extractionCache) {
            Remove-Item -LiteralPath $extractionCache -Force
        }
        if (Test-Path -LiteralPath $extractionCache) {
            throw 'ISPSoft extraction cache could not be cleared before import.'
        }
        # ISPSoft caches the extracted Unzipped.src member using the outer
        # package timestamp.  Copy-Item preserves the two source files' nearly
        # identical times, which can make the later MPU import replay the FBU
        # even after ISPSoft is restarted.  Give the staged packages distinct
        # timestamps while retaining their hash-verified bytes.
        $functionPackageTime = Get-Date
        (Get-Item -LiteralPath $shortFunction).LastWriteTime = $functionPackageTime
        (Get-Item -LiteralPath $shortProgram).LastWriteTime = $functionPackageTime.AddSeconds(4)
        if ($null -ne $shortDeployment) {
            (Get-Item -LiteralPath $shortDeployment).LastWriteTime = $functionPackageTime.AddSeconds(8)
        }
        Write-WorkerHeartbeat 'processing' $jobId 'project_load' ([string]$manifest.target)
        Write-WorkerLog "job $jobId restoring clean ISPSoft project"
        $main = Open-IspSoftProject
        Write-WorkerHeartbeat 'processing' $jobId 'communication_setup' ([string]$manifest.target)
        Select-DeltaCommunicationDriver $main.hwnd
        Remove-PlaceholderFunction $main.hwnd
        Remove-PlaceholderMain $main.hwnd
        Write-WorkerHeartbeat 'processing' $jobId 'program_import' ([string]$manifest.target)
        Write-WorkerLog "job $jobId importing generated $($manifest.candidate_language) function block"
        Import-IspSoftUnit $main.hwnd 'function' $shortFunction
        if (Test-Path -LiteralPath $extractionCache) {
            Remove-Item -LiteralPath $extractionCache -Force
        }
        Write-WorkerLog "job $jobId importing candidate harness MAIN and assigning periodic task"
        Import-IspSoftUnit $main.hwnd 'program' $shortProgram
        Assign-MainToPeriodicTask $main.hwnd
        Write-WorkerHeartbeat 'processing' $jobId 'ispsoft_compile' ([string]$manifest.target)
        Write-WorkerLog "job $jobId compiling with ISPSoft"
        $compile = Compile-IspSoftProject $main.hwnd $localJob
        $result.compile = $compile
        if ($compile.errors -ne 0) {
            $result.status = 'fail'
            $result.public_summary = "ISPSoft rejected the generated $($manifest.target) program"
            $result.gates[0].status = 'fail'
            $result.evidence = @([ordered]@{
                kind='ispsoft_compile_error'; summary=("ISPSoft reported {0} errors and {1} warnings" -f $compile.errors, $compile.warnings)
                diagnostics=@($compile.rows); oracle_status='confirmed_candidate_defect'
            })
            return $result
        }
        $result.gates[0].status = 'pass'
        $passedRequirements = New-Object System.Collections.Generic.HashSet[string]
        $runtimeEvidence = New-Object System.Collections.ArrayList
        $runtimeCases = @($suite.cases)
        $caseIndex = 0
        foreach ($case in $runtimeCases) {
            $caseIndex += 1
            if (Test-Path -LiteralPath (Join-Path $SharedJob 'cancelled.json')) {
                throw "Linux validator cancelled job $jobId before the next COMMGR case."
            }
            $caseId = [string]$case.id
            Write-WorkerHeartbeat 'processing' $jobId 'controller_download' ([string]$manifest.target) $caseIndex $runtimeCases.Count
            Write-WorkerLog "job $jobId downloading fresh image for case $caseId"
            Invoke-DownloadAndRun $main.hwnd $localJob $caseId
            Write-WorkerHeartbeat 'processing' $jobId 'commgr_runtime' ([string]$manifest.target) $caseIndex $runtimeCases.Count
            Write-WorkerLog "job $jobId executing COMMGR case $caseId"
            $caseResult = Invoke-RuntimeCase (Join-Path $localJob 'suite.json') $caseId $localJob
            Write-WorkerHeartbeat 'processing' $jobId 'oracle_evaluation' ([string]$manifest.target) $caseIndex $runtimeCases.Count
            [void]$runtimeEvidence.Add($caseResult)
            if ($caseResult.status -eq 'inconclusive') {
                if ([string]$caseResult.error -match 'COMMGR|connection|connect') {
                    $result.gates[1].status = 'inconclusive'
                } else {
                    $result.gates[1].status = 'pass'
                }
                $result.gates[2].status = 'inconclusive'
                $result.evidence = @($runtimeEvidence)
                return $result
            }
            $result.gates[1].status = 'pass'
            if ($caseResult.status -eq 'fail') {
                $result.status = 'fail'
                $result.public_summary = "$($manifest.target) runtime requirements were violated"
                $result.gates[2].status = 'fail'
                $result.evidence = @($runtimeEvidence)
                return $result
            }
            foreach ($requirement in @($caseResult.requirement_ids)) { [void]$passedRequirements.Add([string]$requirement) }
        }
        # Runtime evidence is already complete at this point.  Preserve that
        # conclusion if the separate deployment-project compile later becomes
        # inconclusive because of GUI or packaging infrastructure.
        $result.gates[2].status = 'pass'
        $result.passed_requirement_ids = @($passedRequirements | Sort-Object)
        if ([string]$manifest.delivery_mode -eq 'downloadable_project') {
            Write-WorkerHeartbeat 'processing' $jobId 'deployment_compile' ([string]$manifest.target)
            Write-WorkerLog "job $jobId replacing the test harness with the confirmed physical-I/O MAIN"
            Remove-PlaceholderMain $main.hwnd $deploymentMainY
            if (Test-Path -LiteralPath $extractionCache) {
                Remove-Item -LiteralPath $extractionCache -Force
            }
            Import-IspSoftUnit $main.hwnd 'program' $shortDeployment
            Assign-MainToPeriodicTask $main.hwnd
            $deploymentCompile = Compile-IspSoftProject $main.hwnd $localJob
            $result.deployment_compile = $deploymentCompile
            if ($deploymentCompile.errors -ne 0) {
                $result.status = 'fail'
                $result.public_summary = 'ISPSoft rejected the target-bound deployment project'
                $result.gates[3].status = 'fail'
                $result.evidence = @([ordered]@{
                    kind='deployment_compile_error'
                    summary=("ISPSoft deployment compile reported {0} errors and {1} warnings" -f $deploymentCompile.errors, $deploymentCompile.warnings)
                    diagnostics=@($deploymentCompile.rows)
                    oracle_status='confirmed_candidate_defect'
                })
                return $result
            }
            $result.gates[3].status = 'pass'
            Activate-Window $main.hwnd
            Send-Keys '^{s}'
            Start-Sleep -Seconds 2
            Stop-IspSoftWithoutSaving
            Write-WorkerHeartbeat 'processing' $jobId 'project_package' ([string]$manifest.target)
            $projectArchive = Join-Path $localJob 'downloadable_project.zip'
            if (Test-Path -LiteralPath $projectArchive) { Remove-Item -LiteralPath $projectArchive -Force }
            Compress-Archive -Path (Join-Path $script:ProjectRoot '*') -DestinationPath $projectArchive -CompressionLevel Optimal
            if (-not (Test-Path -LiteralPath $projectArchive)) {
                throw 'ISPSoft deployment project archive was not created.'
            }
            [ordered]@{
                schema_version = 1
                target = [string]$manifest.target
                project_name = [string]$manifest.project_name
                status = 'requires_physical_commissioning'
                required_checks = @(
                    'Verify every terminal and signal polarity against the cabinet wiring drawing.',
                    'Test every input and output with actuator power isolated.',
                    'Verify emergency stop and safety circuits independently of the standard PLC program.',
                    'Test power-cycle, retained data, communication loss, and safe restart behavior.',
                    'Record real PLC firmware and final ISPSoft compile/download evidence.'
                )
            } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $localJob 'field_acceptance_checklist.json') -Encoding UTF8
            $result.delivery = [ordered]@{
                status = 'compiled_downloadable_project'
                project_name = [string]$manifest.project_name
                project_sha256 = (Get-FileHash -LiteralPath $projectArchive -Algorithm SHA256).Hash.ToLowerInvariant()
                requires_physical_commissioning = $true
            }
        }
        $result.status = 'pass'
        $result.public_summary = "ISPSoft compile and $($manifest.target) $targetSimulator evaluation passed"
        $result.gates[2].status = 'pass'
        $result.passed_requirement_ids = @($passedRequirements | Sort-Object)
        $result.evidence = @($runtimeEvidence)
        return $result
    } catch {
        $result.status = 'inconclusive'
        $result.public_summary = "$($manifest.target) validation infrastructure did not complete"
        $result.evidence = @([ordered]@{
            kind='tool_error'; summary=$_.Exception.Message; exception_type=$_.Exception.GetType().FullName
            oracle_status='unconfirmed'
        })
        try { Save-Screenshot (Join-Path $localJob 'infrastructure_error.png') } catch {}
        return $result
    } finally {
        try { Stop-IspSoftWithoutSaving } catch {
            Write-WorkerLog "job $jobId ISPSoft cleanup failed: $($_.Exception.Message)"
            try { Stop-IspSoft } catch {}
        }
        try {
            $projectPool = Join-Path $WorkerRoot 'projects'
            if ($script:ProjectRoot.StartsWith($projectPool, [System.StringComparison]::OrdinalIgnoreCase) -and
                (Test-Path -LiteralPath $script:ProjectRoot)) {
                Remove-Item -LiteralPath $script:ProjectRoot -Recurse -Force
            }
        } catch {
            Write-WorkerLog "job $jobId disposable project removal failed: $($_.Exception.Message)"
        }
        Write-WorkerLog "job $jobId finished"
    }
}

if (-not (Test-Path -LiteralPath $ispSoftExe)) { throw "ISPSoft is missing: $ispSoftExe" }
if (-not (Test-Path -LiteralPath $runtimeRunner)) { throw "COMMGR runtime runner is missing: $runtimeRunner" }
if (-not (Test-Path -LiteralPath $heartbeatRunner)) { throw "worker heartbeat runner is missing: $heartbeatRunner" }
New-Item -ItemType Directory -Path $WorkerRoot -Force | Out-Null
foreach ($name in @('pending','results')) {
    New-Item -ItemType Directory -Path (Join-Path $SpoolRoot $name) -Force | Out-Null
}
Write-WorkerLog "worker started; spool=$SpoolRoot"
Write-WorkerHeartbeat 'idle'
$heartbeatArguments = @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"{0}"' -f $heartbeatRunner),
    '-HeartbeatPath', ('"{0}"' -f $workerHeartbeatPath),
    '-StatePath', ('"{0}"' -f $workerStatePath),
    '-ParentProcessId', $PID,
    '-WorkerId', $WorkerId
)
[void](Start-Process -FilePath 'powershell.exe' -ArgumentList $heartbeatArguments -WindowStyle Hidden -PassThru)

while ($true) {
    try {
        Write-WorkerHeartbeat 'polling'
        $localCompletedRoot = Join-Path $WorkerRoot 'completed'
        $sharedResultRoot = Join-Path $SpoolRoot 'results'
        New-Item -ItemType Directory -Path $localCompletedRoot -Force | Out-Null
        $pending = @(Get-ChildItem -LiteralPath (Join-Path $SpoolRoot 'pending') -Directory -ErrorAction Stop |
            Where-Object {
                $sharedCompletion = Join-Path (Join-Path $sharedResultRoot $_.Name) 'result.json'
                -not (Test-Path -LiteralPath $sharedCompletion) -and
                -not (Test-Path -LiteralPath (Join-Path $_.FullName 'cancelled.json'))
            } |
            Sort-Object Name)
        if ($pending.Count -eq 0) {
            if ($Once) { break }
            Start-Sleep -Seconds ([Math]::Max(1, $PollSeconds))
            continue
        }
        $sharedJob = $pending[0].FullName
        $jobId = $pending[0].Name
        if (Test-Path -LiteralPath (Join-Path $sharedJob 'cancelled.json')) {
            Write-WorkerLog "skipping cancelled shared job $jobId"
            continue
        }
        $completedPath = Join-Path $localCompletedRoot ($jobId + '.json')
        $completedJob = Join-Path (Join-Path $WorkerRoot 'jobs') $jobId
        if ((Test-Path -LiteralPath $completedPath) -and (Test-Path -LiteralPath $completedJob)) {
            Write-WorkerHeartbeat 'republishing' $jobId
            Write-WorkerLog "shared result missing for completed job $jobId; republishing immutable local result"
            $completedDocument = Get-Content -LiteralPath $completedPath -Raw -Encoding UTF8 | ConvertFrom-Json
            Publish-Result $completedJob $completedDocument
            Write-WorkerHeartbeat 'idle'
            continue
        }
        Write-WorkerHeartbeat 'processing' $jobId
        Write-WorkerLog "selected immutable shared job $jobId"
        $localRoot = Join-Path $WorkerRoot 'jobs'
        New-Item -ItemType Directory -Path $localRoot -Force | Out-Null
        $localJobForPublish = Join-Path $localRoot $jobId
        if (Test-Path -LiteralPath $localJobForPublish) {
            $archiveRoot = Join-Path $WorkerRoot 'archive'
            New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
            Move-Item -LiteralPath $localJobForPublish -Destination (Join-Path $archiveRoot ($jobId + '_' + (Get-Date -Format 'yyyyMMdd_HHmmss')))
        }
        Write-WorkerLog "copying shared job $jobId to the local worker directory"
        Copy-SharedJobToLocal $sharedJob $localJobForPublish
        Write-WorkerLog "shared job $jobId is local"
        $manifest = Get-Content -LiteralPath (Join-Path $localJobForPublish 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        $localJobForPublish = Join-Path (Join-Path $WorkerRoot 'jobs') $manifest.job_id
        try {
            $document = Invoke-OneJob $sharedJob $localJobForPublish
        } catch {
            $document = New-BaseResult $manifest
            $document.evidence = @([ordered]@{kind='tool_error'; summary=$_.Exception.Message; oracle_status='unconfirmed'})
        }
        Write-WorkerHeartbeat 'processing' $jobId 'result_publish' ([string]$manifest.target)
        Publish-Result $localJobForPublish $document
        Complete-JobMaintenance
        Write-WorkerHeartbeat 'idle'
        if ($Once) { break }
    } catch {
        Write-WorkerLog "polling loop recovered from infrastructure error: $($_.Exception.Message)"
        Write-WorkerHeartbeat 'recovering'
        if ($Once) { throw }
        Start-Sleep -Seconds ([Math]::Max(2, $PollSeconds))
    }
}
