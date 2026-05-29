@echo off
cd /d "%~dp0"

echo [1] Detecting Python...
where py >nul 2>&1
if %errorlevel%==0 (
    echo Using: py
    py --version
    echo.
    echo [2] Starting server...
    py server.py
    goto end
)

where python >nul 2>&1
if %errorlevel%==0 (
    echo Using: python
    python --version
    echo.
    echo [2] Starting server...
    python server.py
    goto end
)

echo.
echo [ERROR] Python not found in PATH.
echo Please install Python 3 from https://www.python.org/downloads/
echo During install, check "Add Python to PATH".

:end
echo.
echo --- server exited (code %errorlevel%) ---
pause
