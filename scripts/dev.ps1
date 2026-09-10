# CivicSense Windows Development Helper Script
param (
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("install", "dev", "test", "lint", "format", "typecheck", "db-up", "db-down", "db-migrate", "help")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot

switch ($Command) {
    "install" {
        Write-Host "==> Installing Backend dependencies..." -ForegroundColor Cyan
        Push-Location "$RootDir\backend"
        python -m pip install -e ".[dev]"
        Pop-Location

        Write-Host "==> Installing Mobile dependencies..." -ForegroundColor Cyan
        Push-Location "$RootDir\mobile"
        npm install
        Pop-Location
        Write-Host "==> All dependencies installed successfully!" -ForegroundColor Green
    }
    "dev" {
        Write-Host "==> Starting CivicSense FastAPI Backend on http://localhost:8000..." -ForegroundColor Cyan
        Push-Location "$RootDir\backend"
        python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        Pop-Location
    }
    "test" {
        Write-Host "==> Running Backend test suite..." -ForegroundColor Cyan
        Push-Location "$RootDir\backend"
        python -m pytest tests -v
        Pop-Location
    }
    "lint" {
        Write-Host "==> Running Backend Ruff checks..." -ForegroundColor Cyan
        Push-Location "$RootDir\backend"
        python -m ruff check app tests
        python -m ruff format --check app tests
        Pop-Location
    }
    "format" {
        Write-Host "==> Formatting Backend code with Ruff..." -ForegroundColor Cyan
        Push-Location "$RootDir\backend"
        python -m ruff check --fix app tests
        python -m ruff format app tests
        Pop-Location
    }
    "typecheck" {
        Write-Host "==> Running Backend mypy typecheck..." -ForegroundColor Cyan
        Push-Location "$RootDir\backend"
        python -m mypy app
        Pop-Location

        Write-Host "==> Running Mobile TypeScript typecheck..." -ForegroundColor Cyan
        Push-Location "$RootDir\mobile"
        npm run typecheck
        Pop-Location
    }
    "db-up" {
        Write-Host "==> Starting local PostgreSQL via Docker Compose..." -ForegroundColor Cyan
        Push-Location $RootDir
        docker compose up -d
        Pop-Location
    }
    "db-down" {
        Write-Host "==> Stopping local PostgreSQL..." -ForegroundColor Cyan
        Push-Location $RootDir
        docker compose down
        Pop-Location
    }
    "db-migrate" {
        Write-Host "==> Running Alembic migrations to latest head..." -ForegroundColor Cyan
        Push-Location "$RootDir\backend"
        python -m alembic upgrade head
        Pop-Location
    }
    "help" {
        Write-Host "CivicSense Developer Commands:" -ForegroundColor Yellow
        Write-Host "  .\scripts\dev.ps1 install    - Install backend and mobile dependencies"
        Write-Host "  .\scripts\dev.ps1 dev        - Start backend development server"
        Write-Host "  .\scripts\dev.ps1 test       - Run backend automated test suite"
        Write-Host "  .\scripts\dev.ps1 lint       - Run ruff linter"
        Write-Host "  .\scripts\dev.ps1 format     - Auto-format code with ruff"
        Write-Host "  .\scripts\dev.ps1 typecheck  - Run mypy and tsc typecheck"
        Write-Host "  .\scripts\dev.ps1 db-up      - Start PostgreSQL via docker-compose"
        Write-Host "  .\scripts\dev.ps1 db-down    - Stop PostgreSQL container"
        Write-Host "  .\scripts\dev.ps1 db-migrate - Apply Alembic migrations"
    }
}
