param(
    [Parameter(Mandatory = $true)]
    [string]$VideoPath,
    [int]$DurationSeconds = 75,
    [string]$DeviceName = 'GV-USB2, Analog Capture',
    [ValidateSet('h264_amf', 'libx264', 'ffv1')]
    [string]$Encoder = 'h264_amf',
    [string]$Bitrate = '12M',
    [string]$Maxrate = '20M',
    [string]$Bufsize = '24M',
    [int]$Crf = 18,
    [int]$LeadInSeconds = 2
)

$ErrorActionPreference = 'Stop'

$resolvedVideo = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($VideoPath)
New-Item -ItemType Directory -Force -Path (Split-Path $resolvedVideo) | Out-Null

$job = Start-Job -ScriptBlock {
    param($outVideo, $durationSeconds, $deviceName, $encoder, $bitrate, $maxrate, $bufsize, $crf)
    $args = @(
        '-hide_banner',
        '-loglevel', 'warning',
        '-y',
        '-rtbufsize', '256M',
        '-f', 'dshow',
        '-video_size', '720x480',
        '-framerate', '29.97',
        '-i', "video=$deviceName",
        '-t', $durationSeconds
    )
    if ($encoder -eq 'h264_amf') {
        $args += @(
            '-c:v', 'h264_amf',
            '-usage', 'lowlatency',
            '-quality', 'balanced',
            '-b:v', $bitrate,
            '-maxrate', $maxrate,
            '-bufsize', $bufsize,
            '-pix_fmt', 'yuv420p'
        )
    } elseif ($encoder -eq 'libx264') {
        $args += @(
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', $crf,
            '-pix_fmt', 'yuv420p'
        )
    } elseif ($encoder -eq 'ffv1') {
        $args += @('-c:v', 'ffv1')
    }
    $args += @($outVideo)
    ffmpeg @args
    exit $LASTEXITCODE
} -ArgumentList $resolvedVideo, $DurationSeconds, $DeviceName, $Encoder, $Bitrate, $Maxrate, $Bufsize, $Crf

Start-Sleep -Seconds $LeadInSeconds
& "$PSScriptRoot\cycle_kasa_n64.ps1" | Out-Host
Wait-Job $job | Out-Null
$ffmpegOutput = Receive-Job $job 2>&1
Remove-Job $job

if ($ffmpegOutput) {
    $ffmpegOutput | ForEach-Object { Write-Output $_ }
}

if (-not (Test-Path $resolvedVideo)) {
    throw "Capture file was not created: $resolvedVideo"
}

Get-Item $resolvedVideo | Select-Object FullName, Length, LastWriteTime
