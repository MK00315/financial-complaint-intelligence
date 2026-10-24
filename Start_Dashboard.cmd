@echo off
setlocal
cd /d "%~dp0"
if exist ".dashboard-env\Scripts\python.exe" (
  ".dashboard-env\Scripts\python.exe" "launch_dashboard.py"
) else if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "launch_dashboard.py"
) else if exist "..\..\work\financial-complaint-intelligence\.venv\Scripts\python.exe" (
  "..\..\work\financial-complaint-intelligence\.venv\Scripts\python.exe" "launch_dashboard.py"
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 "launch_dashboard.py"
  ) else (
    python "launch_dashboard.py"
  )
)
if errorlevel 1 pause
endlocal
