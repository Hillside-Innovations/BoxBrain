# Start backend and frontend for local development (Windows).
# Run with PowerShell only (e.g. "powershell -File .\scripts\start.ps1" or run scripts\start.bat).
# Do not run this file in Git Bash or sh — you'll get "command not found" / syntax errors.
# Optional: -VerboseOutput or -Verbose to show health-check attempts and backend output on failure.

param([switch]$VerboseOutput)
if ($VerbosePreference -eq "Continue") { $VerboseOutput = $true }

$ErrorActionPreference = "Stop"
# Project root: parent of the folder containing this script (works when run via -File or .bat)
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyScript.Path }
if (-not $ScriptDir) {
    Write-Host "Could not determine script directory. Run from PowerShell with: powershell -File .\scripts\start.ps1"
    exit 1
}
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

$BackendDir = Join-Path $Root "backend"
$BackendVenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$BackendVenvPip = Join-Path $BackendDir ".venv\Scripts\pip.exe"

# Ensure backend venv exists and deps are installed
if (-not (Test-Path $BackendVenvPython)) {
    Write-Host "Backend venv not found. Creating venv and installing dependencies..."
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        Write-Host "Python not found. Install Python 3.11+ and ensure python is on PATH."
        exit 1
    }
    & $py.Source -m venv (Join-Path $BackendDir ".venv")
    if (-not (Test-Path $BackendVenvPip)) {
        Write-Host "venv creation failed."
        exit 1
    }
    & $BackendVenvPip install -r (Join-Path $BackendDir "requirements.txt")
    Write-Host "Backend venv ready."
}
# Upgrade pip in the venv (venv often ships with an old bundled pip)
Write-Host "Upgrading pip in venv..."
& $BackendVenvPython -m pip install --upgrade pip
# Ensure dependencies are installed (e.g. if venv existed but packages were missing)
Write-Host "Ensuring backend dependencies (pip install -r requirements.txt)..."
& $BackendVenvPython -m pip install -r (Join-Path $BackendDir "requirements.txt")

Write-Host "Starting backend (http://127.0.0.1:8000) ..."
$pyVersion = & $BackendVenvPython --version 2>&1
Write-Host "  Python: $pyVersion"
Write-Host "  (Using real vision model: BLIP. First video upload may download ~1GB if not cached.)"
# Use venv's python.exe; run via Start-Process with stdout and stderr to files so we can show raw output on failure (no PowerShell wrapping).
# Only stderr was captured before — uvicorn/Python often write startup and errors to stdout; both streams can be buffered, so we capture both and use PYTHONUNBUFFERED.
$VenvPython = (Resolve-Path $BackendVenvPython).Path
$BackendStdoutFile = Join-Path $env:TEMP "boxbrain-backend-stdout.txt"
$BackendStderrFile = Join-Path $env:TEMP "boxbrain-backend-stderr.txt"
$env:PYTHONUNBUFFERED = "1"
$BackendProcess = Start-Process -FilePath $VenvPython -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $BackendDir -NoNewWindow -PassThru -RedirectStandardOutput $BackendStdoutFile -RedirectStandardError $BackendStderrFile

try {
    # Wait for backend to be up
    $max = 5
    $ok = $false
    for ($i = 1; $i -le $max; $i++) {
        if ($VerboseOutput) { Write-Host "  Waiting for backend... attempt $i/$max" }
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { $ok = $true; break }
        } catch {
            if ($VerboseOutput) { Write-Host "    $($_.Exception.Message)" }
        }
    }
    if (-not $ok) {
        Write-Host "Backend did not start in time. Check backend/README.md"
        Write-Host ""
        Write-Host "Backend stdout (uvicorn/Python startup):"
        if (Test-Path $BackendStdoutFile) {
            Get-Content $BackendStdoutFile | ForEach-Object { Write-Host "  $_" }
        } else { Write-Host "  (none)" }
        Write-Host ""
        Write-Host "Backend stderr (errors/tracebacks):"
        if (Test-Path $BackendStderrFile) {
            Get-Content $BackendStderrFile | ForEach-Object { Write-Host "  $_" }
        } else { Write-Host "  (none)" }
        if ($BackendProcess -and -not $BackendProcess.HasExited) { Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue }
        exit 1
    }
    Write-Host "Backend ready at http://127.0.0.1:8000"

    # LAN IP for phone testing (try Get-NetIPAddress, fallback to ipconfig)
    $addr = $null
    try {
        $nic = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.InterfaceAlias -notmatch "Loopback" -and $_.IPAddress -notmatch "^169\.254" } |
            Select-Object -First 1
        if ($nic -and $nic.IPAddress) { $addr = $nic.IPAddress }
    } catch {}
    if (-not $addr) {
        $ipconfig = ipconfig 2>$null
        foreach ($line in ($ipconfig -split "`n")) {
            if ($line -match "IPv4 Address[^:]*:\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})") {
                $a = $Matches[1]
                if ($a -notmatch "^127\.|^169\.254") { $addr = $a; break }
            }
        }
    }
    if ($addr) {
        Write-Host ""
        Write-Host "  Your IP on this network: $addr"
        Write-Host "  Frontend (e.g. on your phone, same WiFi): http://${addr}:5173"
        Write-Host "  Backend API: http://${addr}:8000"
        Write-Host ""
    }

    $FrontendDir = Join-Path $Root "frontend"
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npm) {
        Write-Host "npm not found on PATH. Install Node.js and ensure npm is available."
        if ($BackendProcess -and -not $BackendProcess.HasExited) { Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue }
        exit 1
    }
    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Host "Frontend deps not found. Running npm install..."
        Set-Location $FrontendDir
        & npm install
        Set-Location $Root
        Write-Host "Frontend deps ready."
    }

    Write-Host "Starting frontend (http://localhost:5173) ..."
    Write-Host "Press Ctrl+C to stop both."
    Set-Location $FrontendDir
    & npm run dev -- --host
} finally {
    if ($BackendProcess -and -not $BackendProcess.HasExited) { Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue }
}
