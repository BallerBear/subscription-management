# Brightloop

Subscription billing workspace for managing products, plans, customers, subscriptions and recurring invoices.

## Local development

1. Copy `.env.example` to `.env` and adjust values.
2. Install backend dependencies: `cd backend && python3 -m pip install -r requirements.txt`.
3. Start PostgreSQL and Mailpit: `make db-up`.
4. Run migrations: `make migrate`.
5. Start the API and frontend in separate terminals with `make api` and `make web`.

### Windows (no `make`, no Docker needed)

`make` and `python3` are not available on Windows by default, so run the commands directly in PowerShell:

```powershell
copy .env.example .env          # then paste the shared DATABASE_URL (ask Soorya) into .env
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# second terminal
cd frontend
npm install
npm run dev
```

Do NOT run migrations or the seed against the shared database: the schema and demo data already exist there, and only one person applies migrations.
Password-reset emails need Mailpit; without it the reset link is printed in the API terminal.

Mailpit is available at http://localhost:8025. The API listens on http://localhost:8000 and exposes its OpenAPI docs at `/docs`.

## First admin account

Set a long, one-time `ADMIN_BOOTSTRAP_TOKEN` in your local `.env`, then call `POST /auth/bootstrap-admin` with that token, the admin email, name and a strong password. The endpoint refuses to create another admin once one exists. Remove the token from the environment after bootstrapping.

Customer self-registration is available at `POST /auth/register` (with `/auth/signup` retained as a compatibility alias). Admins can create internal staff accounts at `POST /auth/staff`.

The API supports bearer access tokens for programmatic clients and an HttpOnly `brightloop_token` cookie for browser sessions. Configure `COOKIE_SECURE=true` when using HTTPS.

## Project status

The database schema and core backend scaffolding are in place. Authentication, role enforcement, admin catalog APIs, recurring billing services, discounts, payments, reports and the simulated application clock have initial implementations. Subscription lifecycle workflows, password reset email delivery, customer portal screens and broader UI integration remain under development.

See [API conventions](docs/api-conventions.md) for request conventions, authentication, pagination and catalog endpoints.
