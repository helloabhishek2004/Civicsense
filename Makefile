.PHONY: install dev test lint format typecheck db-up db-down db-migrate help

help:
	@echo "CivicSense Developer Automation Commands:"
	@echo "  make install    - Install backend and mobile dependencies"
	@echo "  make dev        - Start backend API on http://localhost:8000"
	@echo "  make test       - Run pytest test suite"
	@echo "  make lint       - Run ruff linter"
	@echo "  make format     - Auto-format with ruff"
	@echo "  make typecheck  - Run mypy and tsc"
	@echo "  make db-up      - Launch PostgreSQL with Docker Compose"
	@echo "  make db-down    - Stop PostgreSQL container"
	@echo "  make db-migrate - Apply Alembic migrations"

install:
	cd backend && python -m pip install -e ".[dev]"
	cd mobile && npm install

dev:
	cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && python -m pytest tests -v

lint:
	cd backend && python -m ruff check app tests && python -m ruff format --check app tests

format:
	cd backend && python -m ruff check --fix app tests && python -m ruff format app tests

typecheck:
	cd backend && python -m mypy app
	cd mobile && npm run typecheck

db-up:
	docker compose up -d

db-down:
	docker compose down

db-migrate:
	cd backend && python -m alembic upgrade head
