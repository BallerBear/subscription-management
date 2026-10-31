"""Small helpers shared by every service."""


class RuleError(Exception):
    """A business-rule problem a person can fix ("Quantity must be at least 3").

    Services raise this instead of FastAPI's HTTPException, so services never
    import FastAPI. main.py registers one handler that turns it into the
    standard {"message", "fields"} JSON body.
    """

    def __init__(self, message: str, status: int = 400, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.field = field


def not_found(what: str) -> RuleError:
    return RuleError(f"{what} not found", 404)


def paged(rows: list[dict], page: int, page_size: int) -> dict:
    """Shape a list of rows into the API's list envelope.

    Every list query selects `COUNT(*) OVER() AS total_count`, so the total
    comes back in the same single round trip as the rows.
    """
    total = rows[0]["total_count"] if rows else 0
    items = [{k: v for k, v in r.items() if k != "total_count"} for r in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
