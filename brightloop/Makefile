.PHONY: db-up migrate seed reset-db api web test

PYTHON ?= python3

# Start local PostgreSQL and Mailpit services.
db-up:
	docker compose up -d postgres mailpit

migrate:
	cd database && $(PYTHON) migrate.py

seed:
	cd database && $(PYTHON) seed/seed.py

# Destructive: removes the local database volume and recreates it.
reset-db:
	docker compose down -v
	docker compose up -d postgres mailpit
	cd database && $(PYTHON) migrate.py
	cd database && $(PYTHON) seed/seed.py

api:
	cd backend && $(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd frontend && npm run dev

test:
	cd backend && $(PYTHON) -m pytest
