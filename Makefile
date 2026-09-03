# RiskShield — Developer Convenience Commands
# Run from the repo root: make <target>

.PHONY: up down migrate seed test shell

## Start all services (DB + backend)
up:
	docker compose up --build

## Stop all services
down:
	docker compose down

## Run database migrations
migrate:
	PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head

## Seed development data
seed:
	PYTHONPATH=backend python backend/scripts/seed.py

## Run all tests
test:
	pytest

## Open a Python shell with app context
shell:
	PYTHONPATH=backend python -c "import asyncio; from app.core.config import settings; print(settings.SQLALCHEMY_DATABASE_URI)"
