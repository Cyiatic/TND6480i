param(
    [int]$OffSeconds = 4,
    [int]$OnSeconds = 12,
    [switch]$StatusOnly,
    [switch]$OffOnly,
    [switch]$OnOnly
)

$ErrorActionPreference = 'Stop'

Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;

public class KasaButtonWin32 {
  public delegate bool EnumWindowProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr hWnd, EnumWindowProc callback, IntPtr lParam);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
  [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr hWnd, UInt32 msg, IntPtr wParam, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, UInt32 msg, IntPtr wParam, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(UInt32 dwFlags, UInt32 dx, UInt32 dy, UInt32 dwData, UIntPtr dwExtraInfo);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
'@

function Get-KasaWindow {
    $proc = Get-Process |
        Where-Object {
            $_.ProcessName -like 'KasaSmartControl*' -and
            $_.MainWindowHandle -ne 0 -and
            $_.MainWindowTitle -eq 'Kasa Smart Control - Smart Plugs/Smart Bulb'
        } |
        Select-Object -First 1

    if (-not $proc) {
        throw 'KasaSmartControl window not found'
    }

    return $proc.MainWindowHandle
}

function Get-WindowRectObject {
    param([IntPtr]$Hwnd)

    $rect = New-Object KasaButtonWin32+RECT
    [void][KasaButtonWin32]::GetWindowRect($Hwnd, [ref]$rect)
    return $rect
}

function Get-KasaDevicesRect {
    param([IntPtr]$Window)

    $script:KasaDevicesRect = $null
    [KasaButtonWin32]::EnumChildWindows($Window, {
        param($hWnd, $lParam)

        $text = New-Object System.Text.StringBuilder 256
        [void][KasaButtonWin32]::GetWindowText($hWnd, $text, $text.Capacity)
        if ($text.ToString() -ne 'Devices') {
            return $true
        }

        $rect = New-Object KasaButtonWin32+RECT
        [void][KasaButtonWin32]::GetWindowRect($hWnd, [ref]$rect)
        $script:KasaDevicesRect = $rect
        return $false
    }, [IntPtr]::Zero) | Out-Null

    if ($script:KasaDevicesRect) {
        return $script:KasaDevicesRect
    }

    throw 'Could not locate Kasa Devices panel'
}

function Get-KasaDeviceList {
    param([IntPtr]$Window)

    $script:KasaDeviceList = [IntPtr]::Zero
    [KasaButtonWin32]::EnumChildWindows($Window, {
        param($hWnd, $lParam)

        $class = New-Object System.Text.StringBuilder 256
        [void][KasaButtonWin32]::GetClassName($hWnd, $class, $class.Capacity)
        if ($class.ToString() -like '*SysListView32*') {
            $script:KasaDeviceList = $hWnd
            return $false
        }

        return $true
    }, [IntPtr]::Zero) | Out-Null

    if ($script:KasaDeviceList -ne [IntPtr]::Zero) {
        return $script:KasaDeviceList
    }

    throw 'Could not locate Kasa device list'
}

function Select-KasaN64Tile {
    param([IntPtr]$Window)

    # The plug tiles are custom-drawn inside the Devices panel, so they do not
    # expose button handles. Send a click to the first list item, which is N64.
    [void][KasaButtonWin32]::ShowWindow($Window, 9)
    [void][KasaButtonWin32]::SetForegroundWindow($Window)

    $list = Get-KasaDeviceList -Window $Window
    $x = 68
    $y = 70
    $lParam = [IntPtr](($y -shl 16) -bor $x)
    [void][KasaButtonWin32]::PostMessage($list, 0x0201, [IntPtr]1, $lParam)
    Start-Sleep -Milliseconds 60
    [void][KasaButtonWin32]::PostMessage($list, 0x0202, [IntPtr]0, $lParam)
    Start-Sleep -Milliseconds 800
}

function Get-KasaTopButtons {
    param([IntPtr]$Window)

    $windowRect = Get-WindowRectObject -Hwnd $Window
    $windowWidth = $windowRect.Right - $windowRect.Left
    $buttons = New-Object System.Collections.Generic.List[object]
    [KasaButtonWin32]::EnumChildWindows($Window, {
        param($hWnd, $lParam)

        $text = New-Object System.Text.StringBuilder 256
        [void][KasaButtonWin32]::GetWindowText($hWnd, $text, $text.Capacity)
        $label = $text.ToString()
        if ($label -notin @('On', 'Off')) {
            return $true
        }

        $rect = New-Object KasaButtonWin32+RECT
        [void][KasaButtonWin32]::GetWindowRect($hWnd, [ref]$rect)

        # Restrict to the selected plug control strip, not hidden settings widgets.
        $relX = $rect.Left - $windowRect.Left
        $relY = $rect.Top - $windowRect.Top
        if ($relX -lt ($windowWidth * 0.62) -or $relX -gt ($windowWidth * 0.96) -or $relY -lt 80 -or $relY -gt 160) {
            return $true
        }

        $buttons.Add([pscustomobject]@{
            Label = $label
            Hwnd = $hWnd
            Enabled = [KasaButtonWin32]::IsWindowEnabled($hWnd)
            Visible = [KasaButtonWin32]::IsWindowVisible($hWnd)
            X = $rect.Left
            Y = $rect.Top
            W = $rect.Right - $rect.Left
            H = $rect.Bottom - $rect.Top
        })

        return $true
    }, [IntPtr]::Zero) | Out-Null

    $on = $buttons | Where-Object { $_.Label -eq 'On' -and $_.Visible } | Select-Object -First 1
    $off = $buttons | Where-Object { $_.Label -eq 'Off' -and $_.Visible } | Select-Object -First 1
    if (-not $on -or -not $off) {
        throw 'Could not find visible Kasa N64 On/Off buttons in the selected-device strip'
    }

    return [pscustomobject]@{ On = $on; Off = $off }
}

function Show-KasaState {
    param($Buttons)

    [pscustomobject]@{
        OnEnabled = [KasaButtonWin32]::IsWindowEnabled($Buttons.On.Hwnd)
        OffEnabled = [KasaButtonWin32]::IsWindowEnabled($Buttons.Off.Hwnd)
        OnHwnd = $Buttons.On.Hwnd.ToInt64()
        OffHwnd = $Buttons.Off.Hwnd.ToInt64()
    }
}

function Click-KasaButton {
    param($Button)

    if (-not [KasaButtonWin32]::IsWindowEnabled($Button.Hwnd)) {
        throw "Kasa button '$($Button.Label)' is not enabled"
    }

    [void][KasaButtonWin32]::SendMessage($Button.Hwnd, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)
}

$window = Get-KasaWindow
try {
    $buttons = Get-KasaTopButtons -Window $window
} catch {
    Select-KasaN64Tile -Window $window
    $buttons = Get-KasaTopButtons -Window $window
}
$initial = Show-KasaState -Buttons $buttons
if (-not $initial.OnEnabled -and -not $initial.OffEnabled) {
    Select-KasaN64Tile -Window $window
    $buttons = Get-KasaTopButtons -Window $window
    $initial = Show-KasaState -Buttons $buttons
}

if ($StatusOnly) {
    $initial
    exit
}

if ($OnOnly) {
    if ($initial.OnEnabled) {
        Click-KasaButton -Button $buttons.On
        Start-Sleep -Seconds $OnSeconds
    }
    $buttons = Get-KasaTopButtons -Window $window
    [pscustomobject]@{
        InitialOnEnabled = $initial.OnEnabled
        InitialOffEnabled = $initial.OffEnabled
        FinalOnEnabled = [KasaButtonWin32]::IsWindowEnabled($buttons.On.Hwnd)
        FinalOffEnabled = [KasaButtonWin32]::IsWindowEnabled($buttons.Off.Hwnd)
        Message = 'Kasa N64 OnOnly attempted through WinForms buttons'
    }
    exit
}

if ($initial.OffEnabled) {
    Click-KasaButton -Button $buttons.Off
    Start-Sleep -Seconds $OffSeconds
}

$buttons = Get-KasaTopButtons -Window $window
$afterOff = Show-KasaState -Buttons $buttons
if ($OffOnly) {
    [pscustomobject]@{
        InitialOnEnabled = $initial.OnEnabled
        InitialOffEnabled = $initial.OffEnabled
        FinalOnEnabled = $afterOff.OnEnabled
        FinalOffEnabled = $afterOff.OffEnabled
        Message = 'Kasa N64 OffOnly attempted through WinForms buttons'
    }
    exit
}

if (-not $afterOff.OnEnabled) {
    throw 'Kasa N64 On button did not become enabled after Off click'
}

Click-KasaButton -Button $buttons.On
Start-Sleep -Seconds $OnSeconds

$buttons = Get-KasaTopButtons -Window $window
[pscustomobject]@{
    InitialOnEnabled = $initial.OnEnabled
    InitialOffEnabled = $initial.OffEnabled
    AfterOffOnEnabled = $afterOff.OnEnabled
    AfterOffOffEnabled = $afterOff.OffEnabled
    FinalOnEnabled = [KasaButtonWin32]::IsWindowEnabled($buttons.On.Hwnd)
    FinalOffEnabled = [KasaButtonWin32]::IsWindowEnabled($buttons.Off.Hwnd)
    Message = 'Kasa N64 cycle attempted through WinForms buttons'
}
