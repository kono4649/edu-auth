"""Order Service fine-grained authorization."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.dependencies import USER_ID_HEADER


def assert_order_access(headers: dict[str, str], owner_id: str) -> None:
    user_id = headers.get(USER_ID_HEADER)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gateway 認証ヘッダーがありません",
        )
    if user_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この注文にアクセスする権限がありません",
        )
