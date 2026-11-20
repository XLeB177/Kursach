@echo off
cd /d "%~dp0"
set "SHOP_PY=python"
if exist ".venv\Scripts\python.exe" set "SHOP_PY=.venv\Scripts\python.exe"
if exist ".postgres\PG_VERSION" (
    "%SHOP_PY%" -m scripts.local_postgres start
    if errorlevel 1 goto failed
)
"%SHOP_PY%" main.py
if not errorlevel 1 exit /b 0
:failed
pause
exit /b 1
