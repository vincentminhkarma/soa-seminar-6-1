@echo off
rem Cai dat va chay AI Booking Service tren Windows: nhap dup file nay, hoac go .\start.bat
rem Tuy chon: --setup-only (chi cai dat, khong chay), --no-open (khong mo trinh duyet), --models (danh sach model)
cd /d "%~dp0"
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if not errorlevel 1 (
  py -3 start.py %*
  goto end
)
python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if not errorlevel 1 (
  python start.py %*
  goto end
)
echo [LOI] Can Python 3.11 tro len. Tai o https://www.python.org/downloads/
echo Khi cai nho tich "Add python.exe to PATH", sau do mo lai cua so moi.
:end
pause
