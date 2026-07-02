param(
    [string]$RepoRoot = "C:\Users\codex\Documents\GitHub\TND6480i",
    [string]$QuarantineBase = "C:\Users\codex\Documents",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Get-TreeSize {
    param([string]$Path)

    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        return (Get-Item -LiteralPath $Path).Length
    }

    $sum = (Get-ChildItem -LiteralPath $Path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    if ($null -eq $sum) {
        return 0
    }
    return [int64]$sum
}

function Assert-UnderPath {
    param(
        [string]$Child,
        [string]$Parent,
        [string]$Label
    )

    $childFull = [System.IO.Path]::GetFullPath($Child)
    $parentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd("\") + "\"
    if (-not $childFull.StartsWith($parentFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label is outside the expected root. Value: $childFull Root: $parentFull"
    }
}

$repo = (Resolve-Path -LiteralPath $RepoRoot).Path
if ($repo -ne "C:\Users\codex\Documents\GitHub\TND6480i") {
    throw "Refusing cleanup for unexpected repo root: $repo"
}

$quarantineBaseFull = [System.IO.Path]::GetFullPath($QuarantineBase)
if ($quarantineBaseFull -ne "C:\Users\codex\Documents") {
    throw "Refusing cleanup for unexpected quarantine base: $quarantineBaseFull"
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$quarantineRoot = Join-Path $quarantineBaseFull "TND6480i_cleanup_quarantine_$stamp"
$quarantineRoot = [System.IO.Path]::GetFullPath($quarantineRoot)
Assert-UnderPath -Child $quarantineRoot -Parent $quarantineBaseFull -Label "quarantine root"

$moves = New-Object System.Collections.Generic.List[object]

function Queue-Move {
    param(
        [string]$Source,
        [string]$Reason
    )

    if (-not (Test-Path -LiteralPath $Source)) {
        return
    }

    $src = (Resolve-Path -LiteralPath $Source).Path
    Assert-UnderPath -Child $src -Parent $repo -Label "source"

    $repoPrefix = $repo.TrimEnd("\") + "\"
    $rel = $src.Substring($repoPrefix.Length)
    if ($rel.StartsWith("..") -or [System.IO.Path]::IsPathRooted($rel)) {
        throw "Computed unsafe relative path: $rel"
    }

    $dst = [System.IO.Path]::GetFullPath((Join-Path $quarantineRoot $rel))
    Assert-UnderPath -Child $dst -Parent $quarantineRoot -Label "destination"

    $moves.Add([PSCustomObject]@{
        Source = $src
        Destination = $dst
        Reason = $Reason
        Bytes = Get-TreeSize -Path $src
    }) | Out-Null
}

# Generated route/probe directories are reproducible from scripts and reports.
$generatedRoot = Join-Path $repo "artifacts\generated"
if (Test-Path -LiteralPath $generatedRoot) {
    Get-ChildItem -LiteralPath $generatedRoot -Directory | ForEach-Object {
        Queue-Move -Source $_.FullName -Reason "generated probe/route directory"
    }

    $keepGeneratedZ64 = @(
        "g1mcfix4.z64",
        "TND6480i_current_g1mcfix4.z64"
    )

    Get-ChildItem -LiteralPath $generatedRoot -File -Filter "*.z64" | Where-Object {
        $keepGeneratedZ64 -notcontains $_.Name
    } | ForEach-Object {
        Queue-Move -Source $_.FullName -Reason "superseded generated candidate ROM"
    }
}

# Keep the final/recent credits evidence and small captures. Stage only bulky old videos.
$videoRoot = Join-Path $repo "diagnostics\captures\videos"
if (Test-Path -LiteralPath $videoRoot) {
    $keepVideoNames = @(
        "ge480i_credits_reference_gvusb2_20260519_172355.mkv",
        "ge480i_credits_reference_continuation_gvusb2_20260519_173012.mkv",
        "g1mcfix4_credits_analysis_gvusb2_20260519_174358.mkv",
        "ge480i_live_end_credits_20260519.mp4"
    )

    Get-ChildItem -LiteralPath $videoRoot -File | Where-Object {
        $_.Length -gt 100MB -and
        $keepVideoNames -notcontains $_.Name -and
        $_.Name -notlike "*g1mcfix4*"
    } | ForEach-Object {
        Queue-Move -Source $_.FullName -Reason "bulky superseded hardware/capture video"
    }
}

$totalBytes = [int64](($moves | Measure-Object Bytes -Sum).Sum)
$summary = [PSCustomObject]@{
    Repo = $repo
    QuarantineRoot = $quarantineRoot
    DryRun = [bool]$DryRun
    FileOrDirectoryCount = $moves.Count
    TotalGB = [math]::Round($totalBytes / 1GB, 3)
    TotalMB = [math]::Round($totalBytes / 1MB, 1)
    GeneratedItems = ($moves | Where-Object { $_.Source -like "*\artifacts\generated\*" }).Count
    VideoItems = ($moves | Where-Object { $_.Source -like "*\diagnostics\captures\videos\*" }).Count
}

if ($DryRun) {
    $summary | ConvertTo-Json -Depth 4
    $moves | Sort-Object Bytes -Descending | Select-Object -First 30 Source,Destination,Reason,@{Name="MB";Expression={[math]::Round($_.Bytes / 1MB, 1)}} | Format-Table -AutoSize
    exit 0
}

New-Item -ItemType Directory -Force -Path $quarantineRoot | Out-Null

foreach ($move in $moves) {
    $parent = Split-Path -Parent $move.Destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Move-Item -LiteralPath $move.Source -Destination $move.Destination
}

$manifest = [PSCustomObject]@{
    Summary = $summary
    Moves = $moves
}

$manifestPath = Join-Path $quarantineRoot "manifest.json"
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

$summary | ConvertTo-Json -Depth 4
Write-Host "Manifest: $manifestPath"
