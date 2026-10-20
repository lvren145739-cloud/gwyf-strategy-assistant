@echo off
setlocal
cd /d "%~dp0"
for %%V in (315 314 313 312 311) do (
 if exist ".venv-py%%V\gwyf-ready.json" (
  ".venv-py%%V\Scripts\python.exe" app.py
  if errorlevel 1 goto failed
  exit /b 0
 )
)
echo Run Setup-Windows.bat first. Python 3.11-3.15 x64 is supported.
pause
exit /b 1
:failed
echo App startup failed. Check the message above and the WebView2 runtime:
echo https://developer.microsoft.com/microsoft-edge/webview2/
pause
exit /b 1
