"""Staff accounts and customers. All SQL for both lives here."""

from app.core.db import connection, transaction
from app.services.common import not_found, paged

# ---------------------------------------------------------------- users ----


def list_users(page: int, page_size: int) -> dict:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, name, email, role, is_active, created_at, COUNT(*) OVER() AS total_count "
            "FROM users WHERE role IN ('ADMIN', 'STAFF') ORDER BY role, name LIMIT %s OFFSET %s",
            (page_size, (page - 1) * page_size),
        ).fetchall()
    return paged(rows, page, page_size)


def set_user_active(admin_id: int, user_id: int, is_active: bool) -> dict:
    with transaction(user_id=admin_id) as conn:
        row = conn.execute(
            "UPDATE users SET is_active = %s WHERE id = %s AND role = 'STAFF' "
            "RETURNING id, name, email, role, is_active, created_at",
            (is_active, user_id),
        ).fetchone()
    if not row:
        raise not_found("Staff account")
    return row


# ------------------------------------------------------------ customers ----

_CUSTOMER_COLS = (
    "company_name", "contact_name", "email", "phone", "address_line",
    "city", "state", "postal_code", "gstin", "is_active",
)  # whitelist: column names are never taken from user input


def list_customers(q: str | None, page: int, page_size: int) -> dict:
    where, params = "", []
    if q:
        where = "WHERE c.company_name ILIKE %s OR c.contact_name ILIKE %s OR c.email ILIKE %s"
        params = [f"%{q}%"] * 3
    with connection() as conn:
        rows = conn.execute(
            "SELECT c.id, c.company_name, c.contact_name, c.email, c.phone, c.city, c.state, "
            "c.gstin, c.is_active, "
            "(SELECT count(*) FROM subscriptions s WHERE s.customer_id = c.id AND s.status = 'ACTIVE') "
            "  AS active_subscriptions, "
            f"COUNT(*) OVER() AS total_count FROM customers c {where} "
            "ORDER BY c.company_name LIMIT %s OFFSET %s",
            params + [page_size, (page - 1) * page_size],
        ).fetchall()
    return paged(rows, page, page_size)


def get_customer(customer_id: int) -> dict:
    with connection() as conn:
        row = conn.execute("SELECT * FROM customers WHERE id = %s", (customer_id,)).fetchone()
    if not row:
        raise not_found("Customer")
    return row


def create_customer(user_id: int, data: dict) -> dict:
    cols = [c for c in _CUSTOMER_COLS if c in data and c != "is_active"]
    with transaction(user_id=user_id) as conn:
        return conn.execute(
            f"INSERT INTO customers ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING *",
            [data[c] for c in cols],
        ).fetchone()


def update_customer(user_id: int, customer_id: int, data: dict) -> dict:
    cols = [c for c in _CUSTOMER_COLS if c in data]
    if not cols:
        return get_customer(customer_id)
    with transaction(user_id=user_id) as conn:
        row = conn.execute(
            f"UPDATE customers SET {', '.join(c + ' = %s' for c in cols)}, updated_at = now() "
            "WHERE id = %s RETURNING *",
            [data[c] for c in cols] + [customer_id],
        ).fetchone()
    if not row:
        raise not_found("Customer")
    return row


def customer_for_user(user_id: int) -> dict:
    """The customers row owned by this login (portal routes use this, never a URL id)."""
    with connection() as conn:
        row = conn.execute("SELECT * FROM customers WHERE user_id = %s", (user_id,)).fetchone()
    if not row:
        raise not_found("Customer profile")
    return row
