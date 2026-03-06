@echo off
REM Run the PowerShell start script. Use this from CMD (or double-click).
REM Do not run start.ps1 in Git Bash — it will fail. Use this .bat or PowerShell.

echo.
echo [BoxBrain] Starting backend and frontend...
echo [BoxBrain] Running scripts\start.ps1
echo [BoxBrain] Pass -VerboseOutput to see health-check attempts and backend errors.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
