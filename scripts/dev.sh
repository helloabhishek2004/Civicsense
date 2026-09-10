#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cmd="${1:-help}"

case "$cmd" in
  install)
    echo "==> Installing Backend dependencies..."
    (cd "$ROOT_DIR/backend" && python -m pip install -e ".[dev]")
    echo "==> Installing Mobile dependencies..."
    (cd "$ROOT_DIR/mobile" && npm install)
    ;;
  dev)
    echo "==> Starting CivicSense FastAPI Backend on http://localhost:8000..."
    (cd "$ROOT_DIR/backend" && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000)
    ;;
  test)
    echo "==> Running Backend test suite..."
    (cd "$ROOT_DIR/backend" && python -m pytest tests -v)
    ;;
  lint)
    echo "==> Running Backend Ruff checks..."
    (cd "$ROOT_DIR/backend" && python -m ruff check app tests && python -m ruff format --check app tests)
    ;;
  format)
    echo "==> Formatting Backend code with Ruff..."
    (cd "$ROOT_DIR/backend" && python -m ruff check --fix app tests && python -m ruff format app tests)
    ;;
  typecheck)
    echo "==> Running Backend mypy typecheck..."
    (cd "$ROOT_DIR/backend" && python -m mypy app)
    echo "==> Running Mobile TypeScript typecheck..."
    (cd "$ROOT_DIR/mobile" && npm run typecheck)
    ;;
  db-up)
    echo "==> Starting local PostgreSQL via Docker Compose..."
    (cd "$ROOT_DIR" && docker compose up -d)
    ;;
  db-down)
    echo "==> Stopping local PostgreSQL..."
    (cd "$ROOT_DIR" && docker compose down)
    ;;
  db-migrate)
    echo "==> Running Alembic migrations to latest head..."
    (cd "$ROOT_DIR/backend" && python -m alembic upgrade head)
    ;;
  *)
    echo "CivicSense Developer Commands:"
    echo "  ./scripts/dev.sh install    - Install backend and mobile dependencies"
    echo "  ./scripts/dev.sh dev        - Start backend development server"
    echo "  ./scripts/dev.sh test       - Run backend automated test suite"
    echo "  ./scripts/dev.sh lint       - Run ruff linter"
    echo "  ./scripts/dev.sh format     - Auto-format code with ruff"
    echo "  ./scripts/dev.sh typecheck  - Run mypy and tsc typecheck"
    echo "  ./scripts/dev.sh db-up      - Start PostgreSQL via docker-compose"
    echo "  ./scripts/dev.sh db-down    - Stop PostgreSQL container"
    echo "  ./scripts/dev.sh db-migrate - Apply Alembic migrations"
    ;;
esac
