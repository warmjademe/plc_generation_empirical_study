param(
    [Parameter(Mandatory = $true)]
    [string]$SpoolRoot,

    [string]$TemplateRoot = 'C:\DeltaPLCValidation\templates\DVP_CLEAN',
    [string]$ProjectRoot = 'C:\ProgramData\Delta Industrial Automation\ISPSoft_New\Projects\DVP_CLEAN',
    [string]$WorkerRoot = 'C:\DeltaPLCValidation\worker',
    [int]$PollSeconds = 2,
    [switch]$Once
)

$ErrorActionPreference = 'Stop'
$toolVersion = 'ISPSoft-3.24+COMMGR-2.11+DVP-ES3+serial-worker-v3-native-ld'
$ispSoftExe = 'C:\Program Files (x86)\Delta Industrial Automation\ISPSoft 3.24\NewISPSoft.exe'
$runtimeRunner = Join-Path $WorkerRoot 'Invoke-DvpRuntimeCase.ps1'
$projectFile = Join-Path $ProjectRoot 'DVP_CLEAN.isp'
$templateProjectFile = Join-Path $TemplateRoot 'DVP_CLEAN.isp'

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
    foreach ($name in @('candidate.ld.json','candidate.ispsoft.ld.src')) {
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
    $deadline = (Get-Date).AddSeconds(40)
    $main = $null
    do {
        $matches = @(Get-TopWindows -ClassName 'TMainFrm' -VisibleOnly)
        if ($matches.Count -gt 0) { $main = $matches[0]; break }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    if ($null -eq $main) { throw 'ISPSoft did not expose its main project window.' }
    Activate-Window $main.hwnd -Maximize
    $titleDeadline = (Get-Date).AddSeconds(30)
    while ($main.title -notlike 'DVP_CLEAN*' -and (Get-Date) -lt $titleDeadline) {
        Start-Sleep -Milliseconds 250
        $windows = @(Get-TopWindows -ClassName 'TMainFrm' -VisibleOnly)
        if ($windows.Count -gt 0) { $main = $windows[0] }
    }
    if ($main.title -notlike 'DVP_CLEAN*') { throw "ISPSoft opened an unexpected project: $($main.title)" }
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

function Import-IspSoftUnit([IntPtr]$MainHandle, [ValidateSet('function','program')]$Kind, [string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "ISPSoft import unit is missing: $Path" }
    Activate-Window $MainHandle -Maximize
    # Before either unit is imported, the clean template has no visible MAIN
    # child: Programs is at y=358 and Function Blocks is at y=374.  Import the
    # FBU first; importing MAIN later expands Programs and shifts the tree.
    $folderY = if ($Kind -eq 'function') { 374 } else { 358 }
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
    # This script is intentionally BOM-less UTF-8, while Windows PowerShell
    # 5.1 parses it through the active ANSI code page.  Construct the two CJK
    # words from code points so the parser does not depend on source encoding.
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
        '-OutputPath', ('"{0}"' -f $resultPath)
    )
    $process = Start-Process -FilePath $exe -ArgumentList $arguments -Wait -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    if (-not (Test-Path -LiteralPath $resultPath)) { throw "COMMGR runner returned no result for case $CaseId (exit $($process.ExitCode))." }
    return Get-Content -LiteralPath $resultPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function New-BaseResult([object]$Manifest) {
    return [ordered]@{
        schema_version = 1
        job_id = [string]$Manifest.job_id
        task_id = [string]$Manifest.task_id
        role = [string]$Manifest.role
        candidate_sha256 = [string]$Manifest.candidate_sha256
        image_identity_sha256 = [string]$Manifest.image_identity_sha256
        target = 'DVP48ES300R'
        status = 'inconclusive'
        public_summary = 'DVP48ES300R validation did not complete'
        tool_version = $toolVersion
        gates = @(
            [ordered]@{name='ispsoft_compile'; status='inconclusive'},
            [ordered]@{name='commgr_connect'; status='inconclusive'},
            [ordered]@{name='dvp_es3_runtime'; status='inconclusive'}
        )
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

function Invoke-OneJob([string]$SharedJob, [string]$LocalJob) {
    $jobId = Split-Path -Leaf $SharedJob
    $localJob = $LocalJob
    $manifestPath = Join-Path $localJob 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'Claimed job has no manifest.' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $result = New-BaseResult $manifest
    try {
        if ($manifest.job_id -ne $jobId -or $manifest.target -ne 'DVP48ES300R') { throw 'Job identity or target is invalid.' }
        Write-WorkerLog "job $jobId verifying immutable input hashes"
        $suite = Test-JobHashes $localJob $manifest
        # ISPSoft's Delphi import dialog truncates long file names.  Stage the
        # already hash-verified packages at fixed short paths; the worker is
        # serial, so these scratch names cannot overlap another job.
        $importRoot = 'C:\DVPW'
        New-Item -ItemType Directory -Path $importRoot -Force | Out-Null
        $shortFunction = Join-Path $importRoot 'C.FBU'
        # ISPSoft also caches an extracted source unit by the outer package
        # path across process restarts.  A content-addressed short file name
        # prevents an old FBU or MPU from being replayed for a later job.
        $shortProgram = Join-Path $importRoot (
            'P' + ([string]$manifest.program_unit_sha256).Substring(0, 12) + '.MPU'
        )
        Copy-Item -LiteralPath (Join-Path $localJob 'candidate.FBU') -Destination $shortFunction -Force
        Copy-Item -LiteralPath (Join-Path $localJob 'MAIN.MPU') -Destination $shortProgram -Force
        if ((Get-FileHash -LiteralPath $shortFunction -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.function_unit_sha256 -or
            (Get-FileHash -LiteralPath $shortProgram -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.program_unit_sha256) {
            throw 'Short-path import staging changed a source-unit package.'
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
        Write-WorkerLog "job $jobId restoring clean ISPSoft project"
        $main = Open-IspSoftProject
        if ([string]$manifest.candidate_language -eq 'ld') {
            Write-WorkerLog "job $jobId importing generated native-LD function block"
            Import-IspSoftUnit $main.hwnd 'function' $shortFunction
            # ISPSoft extracts every protected source unit under this fixed
            # name.  Remove the first import's cache before loading MAIN so the
            # program import cannot replay the LD function block.
            if (Test-Path -LiteralPath $extractionCache) {
                Remove-Item -LiteralPath $extractionCache -Force
            }
        }
        Write-WorkerLog "job $jobId importing candidate harness MAIN and assigning periodic task"
        Import-IspSoftUnit $main.hwnd 'program' $shortProgram
        Assign-MainToPeriodicTask $main.hwnd
        Write-WorkerLog "job $jobId compiling with ISPSoft"
        $compile = Compile-IspSoftProject $main.hwnd $localJob
        $result.compile = $compile
        if ($compile.errors -ne 0) {
            $result.status = 'fail'
            $result.public_summary = 'ISPSoft rejected the generated DVP48ES300R program'
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
        foreach ($case in @($suite.cases)) {
            $caseId = [string]$case.id
            Write-WorkerLog "job $jobId downloading fresh image for case $caseId"
            Invoke-DownloadAndRun $main.hwnd $localJob $caseId
            Write-WorkerLog "job $jobId executing COMMGR case $caseId"
            $caseResult = Invoke-RuntimeCase (Join-Path $localJob 'suite.json') $caseId $localJob
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
                $result.public_summary = 'DVP48ES300R runtime requirements were violated'
                $result.gates[2].status = 'fail'
                $result.evidence = @($runtimeEvidence)
                return $result
            }
            foreach ($requirement in @($caseResult.requirement_ids)) { [void]$passedRequirements.Add([string]$requirement) }
        }
        $result.status = 'pass'
        $result.public_summary = 'ISPSoft compile and DVP48ES300R simulator evaluation passed'
        $result.gates[2].status = 'pass'
        $result.passed_requirement_ids = @($passedRequirements | Sort-Object)
        $result.evidence = @($runtimeEvidence)
        return $result
    } catch {
        $result.status = 'inconclusive'
        $result.public_summary = 'DVP48ES300R validation infrastructure did not complete'
        $result.evidence = @([ordered]@{
            kind='tool_error'; summary=$_.Exception.Message; exception_type=$_.Exception.GetType().FullName
            oracle_status='unconfirmed'
        })
        try { Save-Screenshot (Join-Path $localJob 'infrastructure_error.png') } catch {}
        return $result
    } finally {
        Write-WorkerLog "job $jobId finished"
    }
}

if (-not (Test-Path -LiteralPath $ispSoftExe)) { throw "ISPSoft is missing: $ispSoftExe" }
if (-not (Test-Path -LiteralPath $runtimeRunner)) { throw "COMMGR runtime runner is missing: $runtimeRunner" }
New-Item -ItemType Directory -Path $WorkerRoot -Force | Out-Null
foreach ($name in @('pending','results')) {
    New-Item -ItemType Directory -Path (Join-Path $SpoolRoot $name) -Force | Out-Null
}
Write-WorkerLog "worker started; spool=$SpoolRoot"

while ($true) {
    $localCompletedRoot = Join-Path $WorkerRoot 'completed'
    New-Item -ItemType Directory -Path $localCompletedRoot -Force | Out-Null
    $pending = @(Get-ChildItem -LiteralPath (Join-Path $SpoolRoot 'pending') -Directory -ErrorAction SilentlyContinue |
        Where-Object { -not (Test-Path -LiteralPath (Join-Path $localCompletedRoot ($_.Name + '.json'))) } |
        Sort-Object Name)
    if ($pending.Count -eq 0) {
        if ($Once) { break }
        Start-Sleep -Seconds ([Math]::Max(1, $PollSeconds))
        continue
    }
    $sharedJob = $pending[0].FullName
    $jobId = $pending[0].Name
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
    Publish-Result $localJobForPublish $document
    if ($Once) { break }
}
