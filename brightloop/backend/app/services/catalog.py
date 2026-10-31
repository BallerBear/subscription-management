"""Admin catalog operations. All money values are integer paise."""

from psycopg import Connection

from app.core.db import connection, transaction


def _page(page: int, page_size: int) -> tuple[int, int]:
    if page < 1 or page_size < 1 or page_size > 100:
        raise ValueError("Page must be positive and page_size must be between 1 and 100")
    return (page - 1) * page_size, page_size


def list_taxes(page: int = 1, page_size: int = 25, active_only: bool = False) -> dict:
    offset, limit = _page(page, page_size)
    where = "WHERE is_active" if active_only else ""
    with connection() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS total FROM taxes {where}").fetchone()["total"]
        rows = conn.execute(
            f"SELECT * FROM taxes {where} ORDER BY name LIMIT %s OFFSET %s",
            (limit, offset),
        ).fetchall()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


def create_tax(user_id: int, data: dict) -> dict:
    with transaction(user_id=user_id) as conn:
        return conn.execute(
            "INSERT INTO taxes (name, rate_bps) VALUES (%s, %s) RETURNING *",
            (data["name"], data["rate_bps"]),
        ).fetchone()


def update_tax(user_id: int, tax_id: int, data: dict) -> dict:
    return _update(user_id, "taxes", tax_id, data, ("name", "rate_bps"))


def deactivate_tax(user_id: int, tax_id: int) -> dict:
    with transaction(user_id=user_id) as conn:
        row = conn.execute(
            "UPDATE taxes SET is_active = FALSE WHERE id = %s RETURNING *",
            (tax_id,),
        ).fetchone()
    if row is None:
        raise LookupError("Tax rule not found")
    return row


def list_products(
    page: int = 1, page_size: int = 25, q: str | None = None, active_only: bool = False
) -> dict:
    offset, limit = _page(page, page_size)
    filters, params = [], []
    if active_only:
        filters.append("p.is_active")
    if q:
        filters.append("p.name ILIKE %s")
        params.append(f"%{q.strip()}%")
    where = "WHERE " + " AND ".join(filters) if filters else ""
    with connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS total FROM products p {where}", tuple(params)
        ).fetchone()["total"]
        rows = conn.execute(
            f"""
            SELECT p.*, t.name AS tax_name, t.rate_bps AS tax_rate_bps
              FROM products p JOIN taxes t ON t.id = p.tax_id
              {where}
             ORDER BY p.name
             LIMIT %s OFFSET %s
            """,
            (*params, limit, offset),
        ).fetchall()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


def get_product(product_id: int) -> dict:
    with connection() as conn:
        product = conn.execute(
            """
            SELECT p.*, t.name AS tax_name, t.rate_bps AS tax_rate_bps
              FROM products p JOIN taxes t ON t.id = p.tax_id
             WHERE p.id = %s
            """,
            (product_id,),
        ).fetchone()
        if product is None:
            raise LookupError("Product not found")
        variants = conn.execute(
            "SELECT * FROM product_variants WHERE product_id = %s ORDER BY attribute, value",
            (product_id,),
        ).fetchall()
    return {**product, "variants": variants}


def create_product(user_id: int, data: dict) -> dict:
    with transaction(user_id=user_id) as conn:
        return conn.execute(
            """
            INSERT INTO products (name, type, sales_price, cost_price, notes, tax_id)
            VALUES (%(name)s, %(type)s, %(sales_price)s, %(cost_price)s, %(notes)s, %(tax_id)s)
            RETURNING *
            """,
            data,
        ).fetchone()


def update_product(user_id: int, product_id: int, data: dict) -> dict:
    return _update(
        user_id, "products", product_id, data,
        ("name", "type", "sales_price", "cost_price", "notes", "tax_id"),
    )


def deactivate_product(user_id: int, product_id: int) -> dict:
    with transaction(user_id=user_id) as conn:
        row = conn.execute(
            "UPDATE products SET is_active = FALSE WHERE id = %s RETURNING *",
            (product_id,),
        ).fetchone()
    if row is None:
        raise LookupError("Product not found")
    return row


def list_variants(product_id: int) -> list[dict]:
    with connection() as conn:
        if conn.execute("SELECT 1 FROM products WHERE id = %s", (product_id,)).fetchone() is None:
            raise LookupError("Product not found")
        return conn.execute(
            "SELECT * FROM product_variants WHERE product_id = %s ORDER BY attribute, value",
            (product_id,),
        ).fetchall()


def create_variant(user_id: int, product_id: int, data: dict) -> dict:
    with transaction(user_id=user_id) as conn:
        return conn.execute(
            """
            INSERT INTO product_variants (product_id, attribute, value, extra_price)
            VALUES (%s, %s, %s, %s) RETURNING *
            """,
            (product_id, data["attribute"], data["value"], data["extra_price"]),
        ).fetchone()


def update_variant(user_id: int, product_id: int, variant_id: int, data: dict) -> dict:
    with transaction(user_id=user_id) as conn:
        row = _update_on_connection(
            conn, "product_variants", variant_id, data,
            ("attribute", "value", "extra_price"),
            "product_id = %s", (product_id,),
        )
    if row is None:
        raise LookupError("Variant not found")
    return row


def deactivate_variant(user_id: int, product_id: int, variant_id: int) -> dict:
    with transaction(user_id=user_id) as conn:
        row = conn.execute(
            """
            UPDATE product_variants SET is_active = FALSE
             WHERE id = %s AND product_id = %s RETURNING *
            """,
            (variant_id, product_id),
        ).fetchone()
    if row is None:
        raise LookupError("Variant not found")
    return row


def list_plans(page: int = 1, page_size: int = 25, active_only: bool = False) -> dict:
    offset, limit = _page(page, page_size)
    where = "WHERE p.is_active" if active_only else ""
    with connection() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS total FROM plans p {where}").fetchone()["total"]
        rows = conn.execute(
            f"""
            SELECT p.*, t.name AS tax_name, t.rate_bps AS tax_rate_bps
              FROM plans p LEFT JOIN taxes t ON t.id = p.tax_id
              {where}
             ORDER BY p.name LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


def create_plan(user_id: int, data: dict) -> dict:
    with transaction(user_id=user_id) as conn:
        return conn.execute(
            """
            INSERT INTO plans (
                name, price, billing_period, min_quantity, available_from, available_to,
                tax_id, auto_close, allow_early_close, allow_pause, allow_renew
            ) VALUES (
                %(name)s, %(price)s, %(billing_period)s, %(min_quantity)s,
                %(available_from)s, %(available_to)s, %(tax_id)s, %(auto_close)s,
                %(allow_early_close)s, %(allow_pause)s, %(allow_renew)s
            ) RETURNING *
            """,
            data,
        ).fetchone()


def update_plan(user_id: int, plan_id: int, data: dict) -> dict:
    return _update(
        user_id, "plans", plan_id, data,
        (
            "name", "price", "billing_period", "min_quantity", "available_from",
            "available_to", "tax_id", "auto_close", "allow_early_close",
            "allow_pause", "allow_renew",
        ),
    )


def deactivate_plan(user_id: int, plan_id: int) -> dict:
    with transaction(user_id=user_id) as conn:
        row = conn.execute(
            "UPDATE plans SET is_active = FALSE WHERE id = %s RETURNING *",
            (plan_id,),
        ).fetchone()
    if row is None:
        raise LookupError("Plan not found")
    return row


def _update(user_id: int, table: str, row_id: int, data: dict, allowed: tuple[str, ...]) -> dict:
    if not data:
        raise ValueError("Provide at least one field to update")
    with transaction(user_id=user_id) as conn:
        row = _update_on_connection(conn, table, row_id, data, allowed)
    if row is None:
        raise LookupError(f"{table[:-1].capitalize()} not found")
    return row


def _update_on_connection(
    conn: Connection, table: str, row_id: int, data: dict, allowed: tuple[str, ...],
    extra_where: str = "", extra_params: tuple = (),
) -> dict | None:
    fields = [(key, value) for key, value in data.items() if key in allowed]
    if not fields:
        raise ValueError("Provide at least one field to update")
    assignments = ", ".join(f"{key} = %s" for key, _ in fields)
    where = "id = %s" + (f" AND {extra_where}" if extra_where else "")
    params = tuple(value for _, value in fields) + (row_id,) + extra_params
    return conn.execute(
        f"UPDATE {table} SET {assignments} WHERE {where} RETURNING *", params
    ).fetchone()
