"""Product Service fine-grained authorization."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.dependencies import ROLES_HEADER, parse_csv_header
from app.models import UserRole


def assert_product_write_allowed(headers: dict[str, str], operation: str) -> None:
    roles = parse_csv_header(headers.get(ROLES_HEADER))
    if UserRole.ADMIN.value not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"商品{operation}には管理者権限が必要です",
        )
