@echo off
REM Build StickOSC.exe on Windows.
cd /d "%~dp0.."
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m PyInstaller --noconfirm --clean stickosc.spec
echo Built: dist\StickOSC.exe
