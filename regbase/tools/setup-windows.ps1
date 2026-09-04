<#
.SYNOPSIS
    Set up RegBase on Windows.

.DESCRIPTION
    Installs the Python dependencies, points the raw corpus at a local
    (non-synced) folder so OneDrive does not try to sync tens of gigabytes of
    source PDFs, and builds the search index.

    Run from the project root:
        cd "C:\Users\david\OneDrive\Desktop\WES Reg Project"
        powershell -ExecutionPolicy Bypass -File .\regbase\tools\setup-windows.ps1

.PARAMETER RawCorpus
    Where downloaded PDFs and HTML go. Defaults to C:\RegBaseCorpus\raw, which
    is deliberately OUTSIDE OneDrive. Extracted text stays in the project.

.PARAMETER SkipInstall
    Skip pip install (use when the dependencies are already in place).
#>
param(
    [string]$RawCorpus = "C:\RegBaseCorpus\raw",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "RegBase setup" -ForegroundColor Cyan
Write-Host "  project root : $root"
Write-Host "  raw corpus   : $RawCorpus"
Write-Host ""

# --- locate Python -----------------------------------------------------------
$py = $null
foreach ($candidate in @("py", "python", "python3")) {
    try {
        $v = & $candidate --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $v -match "Python 3\.(\d+)") {
            if ([int]$Matches[1] -ge 9) { $py = $candidate; break }
            Write-Host "  found $v - RegBase needs Python 3.9 or newer" -ForegroundColor Yellow
        }
    } catch { }
}
if (-not $py) {
    Write-Host "Python 3.9+ not found." -ForegroundColor Red
    Write-Host "Install it from https://www.python.org/downloads/ and tick"
    Write-Host "'Add python.exe to PATH', then re-run this script."
    exit 1
}
Write-Host "  python       : $py ($(& $py --version 2>&1))" -ForegroundColor Green

# --- dependencies ------------------------------------------------------------
if (-not $SkipInstall) {
    Write-Host "`nInstalling dependencies..." -ForegroundColor Cyan
    & $py -m pip install --quiet --upgrade pip
    & $py -m pip install --quiet -r (Join-Path $root "regbase\tools\requirements.txt")
    if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed" -ForegroundColor Red; exit 1 }
    Write-Host "  done" -ForegroundColor Green
}

# --- raw corpus outside OneDrive --------------------------------------------
New-Item -ItemType Directory -Force -Path $RawCorpus | Out-Null
[Environment]::SetEnvironmentVariable("REGBASE_RAW", $RawCorpus, "User")
$env:REGBASE_RAW = $RawCorpus
Write-Host "`nREGBASE_RAW set for your user account -> $RawCorpus" -ForegroundColor Green
Write-Host "  (extracted text still lives in the project, so it stays synced and diffable)"

# --- identify yourself to the sites you are about to crawl -------------------
if (-not [Environment]::GetEnvironmentVariable("REGBASE_UA", "User")) {
    $ua = "RegBase/1.0 (oil-and-gas regulatory research; contact: davidvandervieren@gmail.com)"
    [Environment]::SetEnvironmentVariable("REGBASE_UA", $ua, "User")
    $env:REGBASE_UA = $ua
    Write-Host "REGBASE_UA set (identifies you to the sites being crawled)" -ForegroundColor Green
}

# --- verify ------------------------------------------------------------------
Write-Host "`nVerifying..." -ForegroundColor Cyan
Push-Location $root
try {
    & $py "regbase\tools\build_registry_json.py" --indent 1
    & $py "regbase\tools\build_index.py" --rebuild
} finally { Pop-Location }

Write-Host "`nReady. Try:" -ForegroundColor Cyan
Write-Host "  $py regbase\tools\query.py stack --state CO --county Weld --asset compressor_station"
Write-Host "  $py regbase\tools\harvest.py --dry-run --state CO"
Write-Host "`nOpen the KML tool by double-clicking regbase\web\pre-project-review.html"
Write-Host "(or serve it: $py -m http.server 8000 --directory regbase\web)"
Write-Host "`nNOTE: open a NEW terminal before the environment variables take effect." -ForegroundColor Yellow
