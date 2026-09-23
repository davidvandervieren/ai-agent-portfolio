# Mirror the whole RegBase project into a Google Drive (or any synced) folder.
#
# Harvests write to local disk - a sync client that locks or re-uploads
# files while thousands are being written is why the project left OneDrive.
# This script copies the finished result afterwards, so Drive holds a
# complete, current copy and GitHub is optional. It owns one subfolder of
# the destination, RegBase\, and touches nothing else there:
#
#   <Destination>\RegBase\        the project: tools, registry, docs, web,
#                                 people, and corpus\text, manifest, index
#   <Destination>\RegBase\raw\    the raw downloads (REGBASE_RAW)
#
# Files the project no longer has are removed from the mirror, so a
# re-harvest that replaces per-section files with chapters is reflected.
# .git, caches and update packages are not copied.
#
#   .\regbase\tools\sync-drive.ps1
#   .\regbase\tools\sync-drive.ps1 -Destination "G:\My Drive\Datum Power\Repos\Regulations"
#   .\regbase\tools\sync-drive.ps1 -RawOnly

param(
    [string]$Destination = "G:\My Drive\Datum Power\Repos\Regulations",
    [switch]$RawOnly
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$corpus = if ($env:REGBASE_CORPUS) { $env:REGBASE_CORPUS } else { Join-Path $repo "regbase\corpus" }
$raw = if ($env:REGBASE_RAW) { $env:REGBASE_RAW } else { Join-Path $corpus "raw" }
$target = Join-Path $Destination "RegBase"

if (-not (Test-Path -LiteralPath $Destination)) {
    Write-Host "Destination does not exist: $Destination"
    Write-Host "Create it in Drive first, or pass -Destination with the right path."
    exit 1
}
if (-not (Test-Path -LiteralPath $raw)) {
    Write-Host "Raw corpus not found at $raw (set REGBASE_RAW if it lives elsewhere)."
    exit 1
}
New-Item -ItemType Directory -Force -Path $target | Out-Null

function Mirror($from, $to, $label, $extraArgs) {
    Write-Host ""
    Write-Host "== $label"
    Write-Host "   $from  ->  $to"
    # /MIR mirrors (adds, updates, deletes); /FFT tolerates Drive's 2-second
    # timestamps; /R /W keep a locked file from stalling the run; /NP /NFL /NDL
    # keep the output to the summary table; /XJ skips junctions.
    $args = @($from, $to, "/MIR", "/FFT", "/R:2", "/W:3", "/NP", "/NFL", "/NDL", "/XJ") + $extraArgs
    & robocopy @args
    $code = $LASTEXITCODE
    if ($code -ge 8) {
        Write-Host "   robocopy reported errors (exit $code) - see above."
        return $false
    }
    return $true
}

$ok = $true
if (-not $RawOnly) {
    # The project, minus version control, caches, the raw folder if it happens
    # to sit inside the repo, and the update packages that get unpacked here.
    $skipDirs = @(".git", "__pycache__", ".venv", "node_modules", ".pytest_cache", "raw", "_updates")
    $skipFiles = @("*.zip", "*.pyc")
    $ok = Mirror $repo $target "project (code, registry, docs, corpus text, index)" `
        (@("/XD") + $skipDirs + @("/XF") + $skipFiles)
}
$ok = (Mirror $raw (Join-Path $target "raw") "raw source files" @()) -and $ok

Write-Host ""
if ($ok) { Write-Host "Mirror complete: $target" } else { Write-Host "Mirror finished with errors."; exit 1 }
