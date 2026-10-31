from fastapi import HTTPException, status


def require_role(*allowed_roles: str):
    """Placeholder dependency until authenticated request principals are defined."""

    def dependency() -> None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Role authorization is not configured for: {', '.join(allowed_roles)}",
        )

    return dependency
