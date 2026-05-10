param(
    [int]$OffSeconds = 4,
    [int]$OnSeconds = 8,
    [int]$WindowX = 0,
    [int]$WindowY = 0,
    [int]$WindowWidth = 1270,
    [int]$WindowHeight = 840
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win32KasaN64 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
}
'@

$proc = Get-Process |
    Where-Object { $_.ProcessName -like 'KasaSmartControl*' -and $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1

if (-not $proc) {
    throw 'KasaSmartControl window not found'
}

[Win32KasaN64]::ShowWindow($proc.MainWindowHandle, 9) | Out-Null
[Win32KasaN64]::MoveWindow($proc.MainWindowHandle, $WindowX, $WindowY, $WindowWidth, $WindowHeight, $true) | Out-Null
[Win32KasaN64]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 600

function ClickAt([int]$x, [int]$y) {
    [Win32KasaN64]::SetCursorPos($x, $y) | Out-Null
    Start-Sleep -Milliseconds 150
    [Win32KasaN64]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [Win32KasaN64]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 300
}

ClickAt 112 180
ClickAt 1075 132
Start-Sleep -Seconds $OffSeconds
ClickAt 958 132
Start-Sleep -Seconds $OnSeconds

Write-Output "Kasa N64 cycle attempted"
