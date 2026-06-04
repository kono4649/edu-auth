"""Payment Service fine-grained authorization."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.dependencies import SCOPE_HEADER

PAYMENTS_WRITE_SCOPE = "payments:write"


def assert_payment_write_allowed(headers: dict[str, str]) -> None:
    scopes = headers.get(SCOPE_HEADER, "").split()
    if PAYMENTS_WRITE_SCOPE not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="決済実行には payments:write スコープが必要です",
        )
