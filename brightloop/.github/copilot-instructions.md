# Copilot Instructions

Follow the shared project rules in `CLAUDE.md`. Keep HTTP routers thin, put business logic and SQL in `backend/app/services/`, and use versioned PostgreSQL migrations. Do not invent billing rules or API contracts; leave clear TODOs until requirements are agreed. Keep secrets in local `.env` files only, never commit them.
