#!/bin/bash
# CivicSense Demo Startup Script
# Starts PostgreSQL, applies migrations, seeds data, and launches backend + dashboard.
#
# Usage:
#   ./scripts/start_demo.sh              # Full demo startup
#   ./scripts/start_demo.sh --skip-seed  # Skip seeding
#   ./scripts/start_demo.sh --reset      # Reset and re-seed database

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SKIP_SEED=false
RESET=false

for arg in "$@"; do
    case $arg in
        --skip-seed) SKIP_SEED=true ;;
        --reset) RESET=true ;;
    esac
done

echo ""
echo "============================================"
echo "  CivicSense Demo Startup"
echo "============================================"
echo ""

# 1. Check Docker
echo "[1/6] Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "  ERROR: Docker is not running."
    exit 1
fi
echo "  Docker is running."

# 2. Start PostgreSQL
echo "[2/6] Starting PostgreSQL..."
cd "$PROJECT_ROOT"
docker compose up -d

echo "  Waiting for PostgreSQL..."
for i in $(seq 1 30); do
    if docker exec civicsense-postgres pg_isready -U postgres -d civicsense 2>/dev/null | grep -q "accepting connections"; then
        echo "  PostgreSQL is ready."
        break
    fi
    sleep 1
done

# 3. Set environment
echo "[3/6] Setting environment..."
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/civicsense"
echo "  DATABASE_URL set."

# 4. Apply migrations
echo "[4/6] Applying database migrations..."
cd "$PROJECT_ROOT/backend"
python -m alembic upgrade head
echo "  Migrations applied."

# 5. Seed database
if [ "$SKIP_SEED" = false ]; then
    echo "[5/6] Seeding pilot dataset..."
    cd "$PROJECT_ROOT"
    if [ "$RESET" = true ]; then
        python scripts/seed_pilot_dataset.py --seed-db --reset
    else
        python scripts/seed_pilot_dataset.py --seed-db
    fi
    echo "  Pilot dataset seeded."
else
    echo "[5/6] Skipping seed."
fi

# 6. Start backend
echo "[6/6] Starting backend server..."
echo ""
echo "============================================"
echo "  Backend: http://localhost:8000"
echo "  Health:  http://localhost:8000/health"
echo "  Docs:    http://localhost:8000/docs"
echo "============================================"
echo ""

if [ "$BACKEND_ONLY" != "true" ]; then
    echo "Starting dashboard in background..."
    cd "$PROJECT_ROOT/dashboard"
    npm run dev &
    echo "  Dashboard starting at http://localhost:5173"
    echo ""
fi

cd "$PROJECT_ROOT/backend"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
