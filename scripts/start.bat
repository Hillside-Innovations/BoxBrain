@echo off
REM Run the PowerShell start script. Use this from CMD (or double-click).
REM Do not run start.ps1 in Git Bash — it will fail. Use this .bat or PowerShell.
REM Pass -VerboseOutput for verbose (e.g. start.bat -VerboseOutput).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
