# Brightloop

Subscription billing demo application scaffold.

## Local development

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Install backend dependencies: `cd backend && python3 -m pip install -r requirements.txt`.
3. Start PostgreSQL and Mailpit: `make db-up`.
4. Run migrations: `make migrate`.
5. Start the API and frontend in separate terminals with `make api` and `make web`.

Mailpit is available at http://localhost:8025. The API listens on http://localhost:8000 and exposes its OpenAPI docs at `/docs`.

## Project status

This repository is a scaffold. Billing rules, authentication flows, demo records, and UI screens are intentionally not implemented yet.
