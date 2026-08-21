@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Build StickOSC.exe on Windows.
REM
REM Usage (from repo root):
REM   tools\build_win.bat
REM
REM Needs Python 3.9-3.13 (NOT 3.14+). pygame has no 3.14 wheels yet.
REM   winget install Python.Python.3.12
REM   set PYTHON=py -3.12
REM   tools\build_win.bat
REM
REM Output: dist\StickOSC.exe

cd /d "%~dp0.."
set "ROOT=%CD%"

echo ==^> StickOSC Windows build
echo     repo: %ROOT%

call :pick_python
if errorlevel 1 (
  echo.
  echo error: need Python 3.9-3.13 for pygame wheels.
  echo Install Python 3.12, then re-run:
  echo   winget install Python.Python.3.12
  echo   rmdir /s /q "%ROOT%\.venv" 2^>nul
  echo   tools\build_win.bat
  exit /b 1
)

echo     python: %PYEXE%
%PYEXE% --version

REM Recreate venv if missing / wrong version
if not "%NO_VENV%"=="1" (
  if exist "%ROOT%\.venv\Scripts\python.exe" (
    "%ROOT%\.venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if (3,9)<=sys.version_info[:2]<=(3,13) else 1)" 2>nul
    if errorlevel 1 (
      echo ==^> Removing incompatible .venv
      rmdir /s /q "%ROOT%\.venv"
    )
  )
  if not exist "%ROOT%\.venv\Scripts\python.exe" (
    echo ==^> Creating .venv
    %PYEXE% -m venv "%ROOT%\.venv"
    if errorlevel 1 exit /b 1
  )
  set "PYEXE=%ROOT%\.venv\Scripts\python.exe"
  echo     venv: %ROOT%\.venv
)

echo ==^> Installing dependencies
"%PYEXE%" -m pip install --upgrade pip wheel
if errorlevel 1 exit /b 1
"%PYEXE%" -m pip install -r requirements.txt -r requirements-dev.txt
if errorlevel 1 (
  echo.
  echo error: pip install failed.
  echo If pygame failed, use Python 3.12:
  echo   winget install Python.Python.3.12
  echo   rmdir /s /q .venv
  echo   tools\build_win.bat
  exit /b 1
)

echo ==^> Cleaning previous build
if exist "build\windows" rmdir /s /q "build\windows"
if exist "dist\StickOSC.exe" del /f /q "dist\StickOSC.exe"
if exist "dist\StickOSC" rmdir /s /q "dist\StickOSC"

echo ==^> Running PyInstaller
"%PYEXE%" -m PyInstaller --noconfirm --clean --distpath dist --workpath build\windows stickosc.spec
if errorlevel 1 exit /b 1

if not exist "dist\StickOSC.exe" (
  echo error: dist\StickOSC.exe was not created
  dir dist
  exit /b 1
)

echo.
echo Built: %ROOT%\dist\StickOSC.exe
echo.
echo Run:
echo   start "" "%ROOT%\dist\StickOSC.exe"
echo.
echo Config after first run: %USERPROFILE%\.stickosc\mapping.yaml
exit /b 0

:pick_python
REM Prefer explicit PYTHON env, then py -3.12 ... launcher, then python
if defined PYTHON (
  call :check_python %PYTHON%
  if not errorlevel 1 (
    set "PYEXE=%PYTHON%"
    exit /b 0
  )
)

for %%V in (3.12 3.11 3.13 3.10 3.9) do (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -%%V -c "import sys" >nul 2>&1
    if not errorlevel 1 (
      py -%%V -c "import sys; raise SystemExit(0 if (3,9)<=sys.version_info[:2]<=(3,13) else 1)" >nul 2>&1
      if not errorlevel 1 (
        set "PYEXE=py -%%V"
        exit /b 0
      )
    )
  )
)

where python >nul 2>&1
if not errorlevel 1 (
  python -c "import sys; raise SystemExit(0 if (3,9)<=sys.version_info[:2]<=(3,13) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "PYEXE=python"
    exit /b 0
  )
)

where python3 >nul 2>&1
if not errorlevel 1 (
  python3 -c "import sys; raise SystemExit(0 if (3,9)<=sys.version_info[:2]<=(3,13) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "PYEXE=python3"
    exit /b 0
  )
)

exit /b 1

:check_python
%* -c "import sys; raise SystemExit(0 if (3,9)<=sys.version_info[:2]<=(3,13) else 1)" >nul 2>&1
exit /b %ERRORLEVEL%
