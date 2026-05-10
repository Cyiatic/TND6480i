param(
    [Parameter(Mandatory = $true)]
    [string]$VideoPath,
    [int]$DurationSeconds = 75,
    [string]$DeviceName = 'GV-USB2, Analog Capture',
    [int]$LeadInSeconds = 2
)

$ErrorActionPreference = 'Stop'

$resolvedVideo = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($VideoPath)
New-Item -ItemType Directory -Force -Path (Split-Path $resolvedVideo) | Out-Null

$job = Start-Job -ScriptBlock {
    param($outVideo, $durationSeconds, $deviceName)
    ffmpeg -hide_banner -loglevel error -y -f dshow -i "video=$deviceName" -t $durationSeconds -c:v ffv1 $outVideo
    exit $LASTEXITCODE
} -ArgumentList $resolvedVideo, $DurationSeconds, $DeviceName

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
