# Start backend and frontend for local development (Windows).
# Run with PowerShell only (e.g. "powershell -File .\scripts\start.ps1" or run scripts\start.bat).
# Do not run this file in Git Bash or sh — you'll get "command not found" / syntax errors.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyScript.Path)
Set-Location $Root

$BackendVenvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $BackendVenvPython)) {
    Write-Host "Backend venv not found. Run: cd backend; python -m venv .venv; pip install -r requirements.txt"
    exit 1
}

Write-Host "Starting backend (http://127.0.0.1:8000) ..."
Write-Host "  (Using real vision model: BLIP. First video upload may download ~1GB if not cached.)"
$BackendDir = Join-Path $Root "backend"
$BackendJob = Start-Job -ScriptBlock {
    & $using:BackendVenvPython -m uvicorn main:app --host 0.0.0.0 --port 8000
} -WorkingDirectory $BackendDir

try {
    # Wait for backend to be up
    $max = 10
    $ok = $false
    for ($i = 1; $i -le $max; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { $ok = $true; break }
        } catch {}
    }
    if (-not $ok) {
        Write-Host "Backend did not start in time. Check backend/README.md"
        Stop-Job $BackendJob; Remove-Job $BackendJob
        exit 1
    }
    Write-Host "Backend ready at http://127.0.0.1:8000"

    # LAN IP (optional)
    try {
        $addr = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch "Loopback" -and $_.IPAddress -notmatch "^169\.254" } | Select-Object -First 1).IPAddress
        if ($addr) {
            Write-Host ""
            Write-Host "  Your IP on this network: $addr"
            Write-Host "  On your phone (same WiFi), open: http://${addr}:5173"
            Write-Host "  (Backend API for the app: http://${addr}:8000)"
            Write-Host ""
        }
    } catch {}

    $FrontendDir = Join-Path $Root "frontend"
    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Host "Frontend deps not installed. Run: cd frontend; npm install"
        Stop-Job $BackendJob; Remove-Job $BackendJob
        exit 1
    }

    Write-Host "Starting frontend (http://localhost:5173) ..."
    Write-Host "Press Ctrl+C to stop both."
    Set-Location $FrontendDir
    & npm run dev -- --host
} finally {
    Stop-Job $BackendJob -ErrorAction SilentlyContinue
    Remove-Job $BackendJob -ErrorAction SilentlyContinue
}
