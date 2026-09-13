<# 
  CivicSense Demo Startup Script
  Starts PostgreSQL, applies migrations, seeds data, and launches backend + dashboard.
  
  Usage:
    .\scripts\start_demo.ps1              # Full demo startup
    .\scripts\start_demo.ps1 -SkipSeed    # Skip seeding (if already seeded)
    .\scripts\start_demo.ps1 -Reset       # Reset and re-seed database
    .\scripts\start_demo.ps1 -BackendOnly # Start backend only (no dashboard)
#>

param(
    [switch]$SkipSeed,
    [switch]$Reset,
    [switch]$BackendOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  CivicSense Demo Startup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Docker
Write-Host "[1/6] Checking Docker..." -ForegroundColor Yellow
try {
    docker info 2>&1 | Out-Null
    Write-Host "  Docker is running." -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# 2. Start PostgreSQL
Write-Host "[2/6] Starting PostgreSQL..." -ForegroundColor Yellow
Push-Location $ProjectRoot
docker compose up -d
Pop-Location

# Wait for PostgreSQL to be ready
Write-Host "  Waiting for PostgreSQL to be ready..."
$maxRetries = 30
$retries = 0
while ($retries -lt $maxRetries) {
    $ready = docker exec civicsense-postgres pg_isready -U postgres -d civicsense 2>&1
    if ($ready -match "accepting connections") {
        Write-Host "  PostgreSQL is ready." -ForegroundColor Green
        break
    }
    $retries++
    Start-Sleep -Seconds 1
}
if ($retries -ge $maxRetries) {
    Write-Host "  WARNING: PostgreSQL may not be fully ready. Continuing anyway." -ForegroundColor Yellow
}

# 3. Set environment
Write-Host "[3/6] Setting environment..." -ForegroundColor Yellow
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/civicsense"
Write-Host "  DATABASE_URL set." -ForegroundColor Green

# 4. Apply migrations
Write-Host "[4/6] Applying database migrations..." -ForegroundColor Yellow
Push-Location "$ProjectRoot\backend"
python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Migration failed." -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location
Write-Host "  Migrations applied." -ForegroundColor Green

# 5. Seed database
if (-not $SkipSeed) {
    Write-Host "[5/6] Seeding pilot dataset..." -ForegroundColor Yellow
    Push-Location $ProjectRoot
    if ($Reset) {
        python scripts/seed_pilot_dataset.py --seed-db --reset
    } else {
        python scripts/seed_pilot_dataset.py --seed-db
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  WARNING: Seed may have encountered issues. Check output above." -ForegroundColor Yellow
    } else {
        Write-Host "  Pilot dataset seeded." -ForegroundColor Green
    }
    Pop-Location
} else {
    Write-Host "[5/6] Skipping seed (--SkipSeed flag)." -ForegroundColor Yellow
}

# 6. Start backend
Write-Host "[6/6] Starting backend server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Backend: http://localhost:8000" -ForegroundColor Green
Write-Host "  Health:  http://localhost:8000/health" -ForegroundColor Green
Write-Host "  Docs:    http://localhost:8000/docs" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if (-not $BackendOnly) {
    Write-Host "Starting dashboard in a separate process..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot\dashboard'; npm run dev"
    Write-Host "  Dashboard starting at http://localhost:5173" -ForegroundColor Green
    Write-Host ""
}

Write-Host "Press Ctrl+C to stop the backend server." -ForegroundColor Yellow
Write-Host ""

Push-Location "$ProjectRoot\backend"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Pop-Location
