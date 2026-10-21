@echo off
setlocal
cd /d "%~dp0"
title GWYF Vision 0.3.2 - Setup
echo GWYF Vision 0.3.2 - Python 3.11 through 3.15 x64
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
 py -3 tools\setup_runtime.py
 goto result
)
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
 python tools\setup_runtime.py
 goto result
)
echo Install Python 3.11-3.15 x64 with the Python Launcher first:
echo https://www.python.org/downloads/windows/
echo Use the standard build, not free-threaded Python.
pause
exit /b 1
:result
if errorlevel 1 (
 echo Setup failed. Read the error above. Existing environments and game history are preserved.
 pause
 exit /b 1
)
echo Setup complete. Run Start-Windows.bat.
pause
