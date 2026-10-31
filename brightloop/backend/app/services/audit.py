"""Audit log reader (the database triggers write the rows)."""

from app.core.db import connection
from app.services.common import paged


def list_audit(page: int, page_size: int, table_name: str | None = None) -> dict:
    where, params = "", []
    if table_name:
        where, params = "WHERE a.table_name = %s", [table_name]
    with connection() as conn:
        rows = conn.execute(
            f"SELECT a.id, a.table_name, a.row_id, a.action, a.old_data, a.new_data, a.changed_at, "
            f"u.name AS changed_by_name, COUNT(*) OVER() AS total_count FROM audit_log a "
            f"LEFT JOIN users u ON u.id = a.changed_by {where} "
            f"ORDER BY a.changed_at DESC, a.id DESC LIMIT %s OFFSET %s",
            params + [page_size, (page - 1) * page_size],
        ).fetchall()
    return paged(rows, page, page_size)
