# API Conventions

## Authentication

Protected endpoints accept either authentication method:

- Bearer token: `Authorization: Bearer <access_token>`
- Browser session: an HttpOnly `brightloop_token` cookie set by signup or login.

- `POST /auth/register` creates a customer account and customer profile. `POST /auth/signup` remains as a compatibility alias.
- `POST /auth/login` returns the public user and bearer access token, and sets the HttpOnly cookie.
- `POST /auth/logout` clears the browser session cookie.
- `GET /auth/me` returns the authenticated user's public profile.
- `POST /auth/staff` creates a STAFF account (ADMIN only).
- `POST /auth/bootstrap-admin` creates the first ADMIN account only. It is disabled unless `ADMIN_BOOTSTRAP_TOKEN` is configured, and it cannot be used after an admin exists.

Access tokens expire after 12 hours. Passwords must be longer than eight characters, contain uppercase, lowercase and special characters, and fit bcrypt's 72-byte limit. Password hashes are stored; plaintext passwords are never returned.

Set `COOKIE_SECURE=true` when serving the application over HTTPS. Keep it false only for local HTTP development.

## Authorization

- ADMIN: catalog management and staff creation.
- STAFF: intended for internal subscription and billing operations.
- CUSTOMER: intended for their own customer portal data.

Catalog routes currently require ADMIN. Other domain routers will adopt the same dependency as they are implemented. Role and account status are re-read from the database for each authenticated request.

## Naming and money

- Resource paths are plural: `/catalog/products`, `/catalog/plans`, `/catalog/taxes`.
- Resource IDs are path parameters.
- Partial updates use PATCH; deactivation uses DELETE and sets `is_active = false`.
- Monetary values in API payloads are integer paise. For example, ₹2,560.00 is `256000`.
- Tax rates use integer basis points. For example, 18% is `1800`.

## Pagination and filtering

Collection endpoints accept `page` (default 1) and `page_size` (default 25, maximum 100). Paginated responses use:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 25
}
```

Product listing also accepts `q` for a name search and `active_only=true`. Taxes and plans accept `active_only=true`.

## Errors

Errors use a consistent JSON object with `message` and `fields`. Field-level validation messages are keyed by field name. Common statuses:

- 401: missing, invalid or expired token.
- 403: authenticated user lacks the required role.
- 404: requested resource does not exist.
- 409: duplicate unique value or database business rule.
- 422: request validation or check-constraint failure.

Database constraints remain the final authority for uniqueness, foreign keys, valid ranges and plan rules. The API translates common constraint failures into readable responses.

## Catalog endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET, POST | `/catalog/taxes` | List and create tax rules |
| PATCH, DELETE | `/catalog/taxes/{id}` | Edit or deactivate a tax |
| GET, POST | `/catalog/products` | List and create products |
| GET, PATCH, DELETE | `/catalog/products/{id}` | Read, edit or deactivate a product |
| GET, POST | `/catalog/products/{id}/variants` | List and create variants |
| PATCH, DELETE | `/catalog/products/{id}/variants/{variant_id}` | Edit or deactivate a variant |
| GET, POST | `/catalog/plans` | List and create plans |
| PATCH, DELETE | `/catalog/plans/{id}` | Edit or deactivate a plan |

## Notes

- Database-generated columns such as product margin and subscription line totals must not be supplied by clients.
- Existing catalog records are deactivated rather than physically deleted, preserving references from subscriptions and invoices.
- Password reset email delivery and refresh tokens remain follow-up work.
