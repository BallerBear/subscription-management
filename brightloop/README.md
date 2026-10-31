# Brightloop

Subscription billing workspace for managing products, plans, customers, subscriptions and recurring invoices.

## Local development

1. Copy \`.env.example\` to \`.env\` and adjust values.
2. Install backend dependencies: \`cd backend && python3 -m pip install -r requirements.txt\`.
3. Start PostgreSQL and Mailpit: \`make db-up\`.
4. Run migrations: \`make migrate\`.
5. Start the API and frontend in separate terminals with \`make api\` and \`make web\`.

Mailpit is available at http://localhost:8025. The API listens on http://localhost:8000 and exposes its OpenAPI docs at \`/docs\`.

## First admin account

Set a long, one-time \`ADMIN_BOOTSTRAP_TOKEN\` in your local \`.env\`, then call \`POST /auth/bootstrap-admin\` with that token, the admin email, name and a strong password. The endpoint refuses to create another admin once one exists. Remove the token from the environment after bootstrapping.

Customer self-registration is available at \`POST /auth/register\`. Admins can create internal staff accounts at \`POST /auth/staff\`.

## Project status

The database schema and core backend scaffolding are in place. Authentication, role enforcement and admin catalog APIs are implemented. Subscription lifecycle, billing services, reporting, customer portal screens, password reset email delivery and the main UI remain under development.

See [API conventions](docs/api-conventions.md) for request conventions, authentication, pagination and catalog endpoints.
