"""Dropdown data for staff forms (plans, products, terms, discounts) in ONE round trip.

The admin-only /catalog routes manage these tables; staff only need to pick
from them when building a subscription, so this is read-only and active-only.
"""

from app.core.db import connection


def get_lookups() -> dict:
    with connection() as conn:
        plans = conn.execute(
            "SELECT id, name, price, billing_period, min_quantity, available_from, available_to "
            "FROM plans WHERE is_active ORDER BY name"
        ).fetchall()
        products = conn.execute(
            """
            SELECT p.id, p.name, p.type, p.sales_price,
                   COALESCE((SELECT json_agg(json_build_object(
                               'id', v.id, 'label', v.attribute || ': ' || v.value,
                               'extra_price', v.extra_price) ORDER BY v.id)
                               FROM product_variants v WHERE v.product_id = p.id AND v.is_active),
                            '[]'::json) AS variants
              FROM products p WHERE p.is_active ORDER BY p.name
            """
        ).fetchall()
        terms = conn.execute("SELECT id, name, days FROM payment_terms ORDER BY days").fetchall()
        discounts = conn.execute(
            "SELECT id, name, type, value FROM discounts WHERE is_active ORDER BY name"
        ).fetchall()
    return {"plans": plans, "products": products, "payment_terms": terms, "discounts": discounts}
