param(
    [string]$UnlockedSave = "C:\Users\codex\Documents\TND_X7_Current_unlocked.eep",
    [string]$ExpectedCurrentMd5 = "92B9D768EFB3829E0C2A1A1916E42D89",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

function Get-Md5($Path) {
    (Get-FileHash -Algorithm MD5 -LiteralPath $Path).Hash.ToUpperInvariant()
}

if (-not (Test-Path -LiteralPath $UnlockedSave)) {
    throw "Unlocked save not found: $UnlockedSave"
}

$unlockedInfo = Get-Item -LiteralPath $UnlockedSave
if ($unlockedInfo.Length -ne 512) {
    throw "Unlocked save should be 512 bytes for EEPROM 4K, got $($unlockedInfo.Length): $UnlockedSave"
}

$roots = Get-PSDrive -PSProvider FileSystem |
    Where-Object {
        $_.Root -and (Test-Path -LiteralPath (Join-Path $_.Root "ED64"))
    } |
    Select-Object -ExpandProperty Root

if (-not $roots) {
    throw "No filesystem root with an ED64 folder is mounted. Insert the EverDrive SD card and rerun."
}

$matches = @()
foreach ($root in $roots) {
    foreach ($subdir in @("ED64\gamedata", "ED64\save")) {
        $dir = Join-Path $root $subdir
        if (-not (Test-Path -LiteralPath $dir)) {
            continue
        }
        Get-ChildItem -LiteralPath $dir -File -Include *.eep -ErrorAction SilentlyContinue |
            ForEach-Object {
                $hash = Get-Md5 $_.FullName
                if ($hash -eq $ExpectedCurrentMd5) {
                    $matches += [pscustomobject]@{
                        Path = $_.FullName
                        Length = $_.Length
                        Md5 = $hash
                    }
                }
            }
    }
}

if (-not $matches) {
    Write-Host "No exact MD5 match for the Bazaar-only save was found."
    Write-Host "Searched ED64\gamedata and ED64\save under: $($roots -join ', ')"
    Write-Host "Known current-save MD5: $ExpectedCurrentMd5"
    exit 2
}

Write-Host "Found matching X7 TND save file(s):"
$matches | Format-Table -AutoSize

if (-not $Apply) {
    Write-Host ""
    Write-Host "Dry run only. Rerun with -Apply to back up and replace the matching file(s)."
    exit 0
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
foreach ($match in $matches) {
    $backup = "$($match.Path).bak_$stamp"
    Copy-Item -LiteralPath $match.Path -Destination $backup
    Copy-Item -LiteralPath $UnlockedSave -Destination $match.Path -Force
    $newHash = Get-Md5 $match.Path
    Write-Host "Patched: $($match.Path)"
    Write-Host "Backup:  $backup"
    Write-Host "New MD5: $newHash"
}
