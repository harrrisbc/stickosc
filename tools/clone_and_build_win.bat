@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Clone StickOSC from GitHub and build StickOSC.exe on Windows.
REM
REM One-shot (PowerShell):
REM   irm https://raw.githubusercontent.com/harrrisbc/stickosc/cursor/gui-standalone-app-5a6a/tools/clone_and_build_win.ps1 | iex
REM
REM Or from cmd (after git clone / existing checkout):
REM   tools\clone_and_build_win.bat
REM
REM Needs:
REM   - git
REM   - Python 3.9-3.13  (recommended: winget install Python.Python.3.12)
REM
REM Env overrides (optional):
REM   set REPO_URL=https://github.com/harrrisbc/stickosc.git
REM   set BRANCH=cursor/gui-standalone-app-5a6a
REM   set DEST=%USERPROFILE%\stickosc

if not defined REPO_URL set "REPO_URL=https://github.com/harrrisbc/stickosc.git"
if not defined BRANCH set "BRANCH=cursor/gui-standalone-app-5a6a"
if not defined DEST set "DEST=%USERPROFILE%\stickosc"

echo ==^> StickOSC clone + Windows build
echo     repo:   %REPO_URL%
echo     branch: %BRANCH%
echo     dest:   %DEST%

where git >nul 2>&1
if errorlevel 1 (
  echo error: git not found. Install Git for Windows:
  echo   winget install Git.Git
  exit /b 1
)

REM Soft check for Python 3.14
where python >nul 2>&1
if not errorlevel 1 (
  for /f "delims=" %%V in ('python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2^>nul') do set "PYVER=%%V"
  if "!PYVER!"=="3.14" (
    echo.
    echo warning: default python is 3.14 — pygame will fail.
    echo Install 3.12:
    echo   winget install Python.Python.3.12
    echo then re-run this script.
    where py >nul 2>&1
    if errorlevel 1 (
      echo error: Python launcher "py" not found either.
      exit /b 1
    )
  )
)

if exist "%DEST%\.git" (
  echo ==^> Repo exists — fetching / updating
  git -C "%DEST%" fetch --prune origin
  if errorlevel 1 exit /b 1
  git -C "%DEST%" checkout "%BRANCH%"
  if errorlevel 1 exit /b 1
  git -C "%DEST%" pull --ff-only origin "%BRANCH%"
  if errorlevel 1 exit /b 1
) else (
  if exist "%DEST%" (
    echo error: %DEST% exists but is not a git repo. Set DEST=... to another folder.
    exit /b 1
  )
  echo ==^> Cloning
  git clone --branch "%BRANCH%" --single-branch "%REPO_URL%" "%DEST%"
  if errorlevel 1 exit /b 1
)

cd /d "%DEST%"

REM Drop broken 3.14 venv from previous attempt
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if (3,9)<=sys.version_info[:2]<=(3,13) else 1)" 2>nul
  if errorlevel 1 (
    echo ==^> Removing old incompatible .venv
    rmdir /s /q .venv
  )
)

call tools\build_win.bat
if errorlevel 1 exit /b 1

echo.
echo Done. App path:
echo   %DEST%\dist\StickOSC.exe
echo.
echo Run:
echo   start "" "%DEST%\dist\StickOSC.exe"
exit /b 0
