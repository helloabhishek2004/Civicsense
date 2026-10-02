<# 
  CivicSense Demo Startup Script
  Starts backend (FastAPI) and web dashboard (Vite/React) for live demonstration.
  Supports standalone SQLite (zero Docker required) and optional Docker PostgreSQL.
  Automatically detects current LAN Wi-Fi / Hotspot IP and configures Android endpoints.

  Usage:
    .\scripts\start_demo.ps1              # Full demo startup (SQLite, zero Docker needed)
    .\scripts\start_demo.ps1 -UseDocker   # Start with Docker PostgreSQL
    .\scripts\start_demo.ps1 -BackendOnly # Start backend only (no dashboard)
    .\scripts\start_demo.ps1 -Reset       # Reset and re-seed database
#>

param(
    [switch]$UseDocker,
    [switch]$SkipSeed,
    [switch]$Reset,
    [switch]$BackendOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       CivicSense - Demonstration Startup Script            " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Resolve Python executable
Write-Host "[1/6] Resolving Python environment..." -ForegroundColor Yellow
$PythonCandidates = @(
    "C:\Users\LOQ\civicsense_venv\Scripts\python.exe",
    "$ProjectRoot\.venv\Scripts\python.exe",
    "$env:USERPROFILE\civicsense_venv\Scripts\python.exe"
)

$PythonExe = $null
foreach ($candidate in $PythonCandidates) {
    if (Test-Path $candidate) {
        $PythonExe = $candidate
        break
    }
}

if (-not $PythonExe) {
    $sysPython = Get-Command python -ErrorAction SilentlyContinue
    if ($sysPython) {
        $PythonExe = $sysPython.Source
    } else {
        Write-Host "  ERROR: Python executable not found. Please activate your venv." -ForegroundColor Red
        exit 1
    }
}
Write-Host "  Using Python: $PythonExe" -ForegroundColor Green

# 2. Ensure Node.js & npm are on PATH
Write-Host "[2/6] Checking Node.js environment..." -ForegroundColor Yellow
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    if (Test-Path "C:\Program Files\nodejs") {
        $env:PATH = "C:\Program Files\nodejs;" + $env:PATH
        Write-Host "  Added C:\Program Files\nodejs to PATH." -ForegroundColor Green
    }
}
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVer = & node -v
    Write-Host "  Node.js: $nodeVer" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Node.js not detected on PATH. Dashboard may fail to launch." -ForegroundColor Yellow
}

# 3. Detect LAN IP and configure Android local.properties
Write-Host "[3/6] Detecting Wi-Fi / Hotspot LAN IP..." -ForegroundColor Yellow
$LanScript = Join-Path $PSScriptRoot "get_lan_ip.ps1"
$LanIp = "127.0.0.1"
$LanUrl = "http://localhost:8000"

if (Test-Path $LanScript) {
    try {
        & $LanScript -UpdateFiles | Out-Null
        $detected = & $LanScript
        if ($detected -match "Active LAN IPv4:\s+([0-9\.]+)") {
            $LanIp = $matches[1]
            $LanUrl = "http://${LanIp}:8000"
        }
        Write-Host "  Active LAN IP: $LanIp" -ForegroundColor Green
        Write-Host "  Android API URL: $LanUrl" -ForegroundColor Green

        # Auto-sync APK with current LAN IP
        $SyncApkScript = Join-Path $PSScriptRoot "sync_apk_lan_ip.py"
        if (Test-Path $SyncApkScript) {
            $syncRes = & $PythonExe $SyncApkScript --ip $LanIp 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  Synced and signed app-debug.apk for: $LanUrl" -ForegroundColor Green
            } else {
                Write-Host "  APK auto-signing skipped (Java not installed on PC)." -ForegroundColor DarkYellow
                Write-Host "  To connect Android phone: Profile -> Backend Server URL -> $LanUrl" -ForegroundColor DarkYellow
            }
        }

        # Auto-configure USB reverse forwarding if phone is plugged in
        $AdbCmd = Get-Command adb -ErrorAction SilentlyContinue
        $AdbExe = if ($AdbCmd) { $AdbCmd.Source } else { (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet" -Filter "adb.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName -First 1) }
        if ($AdbExe -and (Test-Path $AdbExe)) {
            $devs = & $AdbExe devices 2>&1
            if ($devs -match "\bdevice\b") {
                & $AdbExe reverse tcp:8000 tcp:8000 2>&1 | Out-Null
                Write-Host "  USB ADB reverse active: phone can reach backend via USB or Wi-Fi!" -ForegroundColor Green
            }
        }
    } catch {
        Write-Host "  Notice: Could not auto-detect LAN IP ($_); defaulting to localhost." -ForegroundColor Yellow
    }
}

# 4. Configure Database Layer
Write-Host "[4/6] Configuring Database layer..." -ForegroundColor Yellow
$SqliteDbPath = Join-Path $ProjectRoot "backend\civicsense.db"

if ($UseDocker) {
    Write-Host "  Mode: Docker PostgreSQL" -ForegroundColor Cyan
    try {
        docker info 2>&1 | Out-Null
        Write-Host "  Docker is running." -ForegroundColor Green
    } catch {
        Write-Host "  ERROR: Docker is not running. Please start Docker Desktop or run without -UseDocker to use SQLite." -ForegroundColor Red
        exit 1
    }

    Push-Location $ProjectRoot
    docker compose up -d
    Pop-Location

    $env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/civicsense"

    Push-Location "$ProjectRoot\backend"
    & $PythonExe -m alembic upgrade head
    Pop-Location

    if (-not $SkipSeed) {
        Push-Location $ProjectRoot
        if ($Reset) {
            & $PythonExe scripts/seed_pilot_dataset.py --seed-db --reset
        } else {
            & $PythonExe scripts/seed_pilot_dataset.py --seed-db
        }
        Pop-Location
    }
} else {
    Write-Host "  Mode: Portable SQLite ($SqliteDbPath)" -ForegroundColor Cyan
    $env:DATABASE_URL = "sqlite:///./civicsense.db"

    if ((Test-Path $SqliteDbPath) -and -not $Reset) {
        Write-Host "  SQLite database exists and is pre-seeded with demonstration data." -ForegroundColor Green
    } else {
        Write-Host "  Setting up SQLite database..." -ForegroundColor Yellow
        Push-Location "$ProjectRoot\backend"
        & $PythonExe -m alembic upgrade head
        Pop-Location

        if (-not $SkipSeed) {
            Push-Location $ProjectRoot
            & $PythonExe scripts/seed_pilot_dataset.py --seed-db
            Pop-Location
        }
    }
}

# 5. Launch Dashboard
if (-not $BackendOnly) {
    Write-Host "[5/6] Launching Dashboard in background..." -ForegroundColor Yellow
    $DashboardCmd = "`$env:PATH = 'C:\Program Files\nodejs;' + `$env:PATH; cd '$ProjectRoot\dashboard'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $DashboardCmd
    Write-Host "  Dashboard process launched (http://localhost:5173)." -ForegroundColor Green
} else {
    Write-Host "[5/6] Skipping dashboard launch (-BackendOnly flag)." -ForegroundColor Yellow
}

# 6. Launch Backend Server & Wi-Fi Port Forwarder
Write-Host "[6/6] Launching FastAPI Backend Server..." -ForegroundColor Yellow
$ForwarderScript = Join-Path $PSScriptRoot "port_forwarder.py"
if (Test-Path $ForwarderScript) {
    Start-Process $PythonExe -ArgumentList "`"$ForwarderScript`"" -WindowStyle Hidden
    Write-Host "  Wi-Fi Port 80 forwarder active (enables instant mobile sync)." -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  CivicSense Demonstration is LIVE!                         " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Web Authority Dashboard: http://localhost:5173" -ForegroundColor White
Write-Host "  Backend Local API:       http://localhost:8000" -ForegroundColor White
Write-Host "  Interactive API Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "  System Health Check:     http://localhost:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "  * Android Phone Connectivity *" -ForegroundColor Cyan
Write-Host "  Phone Wi-Fi Network:     Must be on the SAME network as this laptop" -ForegroundColor Yellow
Write-Host "  Phone Server URL:        $LanUrl" -ForegroundColor Yellow
Write-Host "  Phone Test URL:          $LanUrl/health" -ForegroundColor Yellow
Write-Host ""
Write-Host "  TIP: If your campus Wi-Fi isolates devices (phone cannot reach laptop)," -ForegroundColor DarkYellow
Write-Host "       turn on your phone's Mobile Hotspot, connect your laptop to it," -ForegroundColor DarkYellow
Write-Host "       run '.\scripts\start_demo.ps1', and use the new Hotspot IP." -ForegroundColor DarkYellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C in this terminal to stop the FastAPI backend." -ForegroundColor Gray
Write-Host ""

Push-Location "$ProjectRoot\backend"
& $PythonExe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Pop-Location
