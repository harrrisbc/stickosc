# Clone StickOSC from GitHub and build StickOSC.exe on Windows.
#
# One-shot (PowerShell):
#   irm https://raw.githubusercontent.com/harrrisbc/stickosc/cursor/gui-standalone-app-5a6a/tools/clone_and_build_win.ps1 | iex
#
# Or:
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\tools\clone_and_build_win.ps1
#
# Needs Python 3.9-3.13 (NOT 3.14):
#   winget install Python.Python.3.12
#   winget install Git.Git

$ErrorActionPreference = "Stop"

if ($env:OS -notlike "*Windows*") {
    Write-Error "This script must run on Windows."
}

$RepoUrl = if ($env:REPO_URL) { $env:REPO_URL } else { "https://github.com/harrrisbc/stickosc.git" }
$Branch  = if ($env:BRANCH)   { $env:BRANCH }   else { "cursor/gui-standalone-app-5a6a" }
$Dest    = if ($env:DEST)     { $env:DEST }     else { Join-Path $HOME "stickosc" }

Write-Host "==> StickOSC clone + Windows build"
Write-Host "    repo:   $RepoUrl"
Write-Host "    branch: $Branch"
Write-Host "    dest:   $Dest"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git not found. Install: winget install Git.Git"
}

if (Test-Path (Join-Path $Dest ".git")) {
    Write-Host "==> Repo exists — fetching / updating"
    git -C $Dest fetch --prune origin
    git -C $Dest checkout $Branch
    git -C $Dest pull --ff-only origin $Branch
} else {
    if (Test-Path $Dest) {
        Write-Error "$Dest exists but is not a git repo. Set DEST to another folder."
    }
    Write-Host "==> Cloning"
    git clone --branch $Branch --single-branch $RepoUrl $Dest
}

Set-Location $Dest

$venvPython = Join-Path $Dest ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython -c "import sys; raise SystemExit(0 if (3,9)<=sys.version_info[:2]<=(3,13) else 1)" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "==> Removing old incompatible .venv"
        Remove-Item -Recurse -Force (Join-Path $Dest ".venv")
    }
}

$buildBat = Join-Path $Dest "tools\build_win.bat"
if (-not (Test-Path $buildBat)) {
    Write-Error "Missing $buildBat — wrong branch?"
}

Write-Host "==> Building"
& cmd.exe /c "`"$buildBat`""
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$exe = Join-Path $Dest "dist\StickOSC.exe"
Write-Host ""
Write-Host "Done. App path:"
Write-Host "  $exe"
Write-Host ""
Write-Host "Run:"
Write-Host "  start `"`" `"$exe`""
