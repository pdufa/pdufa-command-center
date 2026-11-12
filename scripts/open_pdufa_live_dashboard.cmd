@echo off
setlocal
cd /d "%~dp0.."
if errorlevel 1 (
  echo Cannot find PDUFA working directory.
  pause
  exit /b 1
)
echo Opening your local PDUFA live coding dashboard...
echo The coding worker will keep running if you close this window.
py -3.13 scripts\windows_local_agent_dashboard.py --open
if errorlevel 1 (
  echo Dashboard could not start. Check whether port 8765 is already in use.
  pause
  exit /b 1
)
endlocal
