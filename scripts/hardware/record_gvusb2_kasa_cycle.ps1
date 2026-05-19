param(
    [Parameter(Mandatory = $true)]
    [string]$Output,
    [int]$Seconds = 90,
    [int]$PreRollSeconds = 2,
    [int]$OffSeconds = 5,
    [int]$OnSeconds = 12,
    [int]$Crf = 18,
    [ValidateSet('h264_amf', 'libx264', 'ffv1')]
    [string]$Encoder = 'h264_amf',
    [string]$Bitrate = '12M',
    [string]$Maxrate = '20M',
    [string]$Bufsize = '24M',
    [string]$AmfQuality = 'balanced',
    [string]$AmfUsage = 'lowlatency',
    [string]$VideoSize = '720x480',
    [string]$FrameRate = '29.97',
    [switch]$NoCycle
)

$ErrorActionPreference = 'Stop'

if ([System.IO.Path]::IsPathRooted($Output)) {
    $outPath = $Output
} else {
    $outPath = Join-Path (Get-Location) $Output
}

$outDir = Split-Path -Parent $outPath
if ($outDir) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}

$job = Start-Job -ScriptBlock {
    param(
        $JobOutput,
        $JobSeconds,
        $JobCrf,
        $JobEncoder,
        $JobBitrate,
        $JobMaxrate,
        $JobBufsize,
        $JobAmfQuality,
        $JobAmfUsage,
        $JobVideoSize,
        $JobFrameRate
    )

    $args = @(
        '-hide_banner',
        '-loglevel', 'warning',
        '-y',
        '-rtbufsize', '256M',
        '-f', 'dshow',
        '-video_size', $JobVideoSize,
        '-framerate', $JobFrameRate,
        '-i', 'video=GV-USB2, Analog Capture',
        '-t', $JobSeconds
    )

    if ($JobEncoder -eq 'h264_amf') {
        $args += @(
            '-c:v', 'h264_amf',
            '-usage', $JobAmfUsage,
            '-quality', $JobAmfQuality,
            '-b:v', $JobBitrate,
            '-maxrate', $JobMaxrate,
            '-bufsize', $JobBufsize,
            '-pix_fmt', 'yuv420p'
        )
    } elseif ($JobEncoder -eq 'libx264') {
        $args += @(
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', $JobCrf,
            '-pix_fmt', 'yuv420p'
        )
    } elseif ($JobEncoder -eq 'ffv1') {
        $args += @('-c:v', 'ffv1')
    }

    $args += @($JobOutput)

    & ffmpeg @args

    if ($LASTEXITCODE -ne 0) {
        throw "ffmpeg exited with $LASTEXITCODE"
    }
} -ArgumentList $outPath, $Seconds, $Crf, $Encoder, $Bitrate, $Maxrate, $Bufsize, $AmfQuality, $AmfUsage, $VideoSize, $FrameRate

try {
    Start-Sleep -Seconds $PreRollSeconds

    if (-not $NoCycle) {
        & (Join-Path $PSScriptRoot 'cycle_kasa_n64_buttons.ps1') -OffSeconds $OffSeconds -OnSeconds $OnSeconds | Out-Host
    }

    $timeout = [Math]::Max($Seconds + $PreRollSeconds + $OffSeconds + $OnSeconds + 20, 30)
    if (-not (Wait-Job -Job $job -Timeout $timeout)) {
        Stop-Job -Job $job
        throw "ffmpeg job did not finish within $timeout seconds"
    }

    Receive-Job -Job $job
    if (-not (Test-Path -LiteralPath $outPath)) {
        throw "Expected capture file was not created: $outPath"
    }

    Get-Item -LiteralPath $outPath | Select-Object FullName, Length, LastWriteTime
} finally {
    Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
}
