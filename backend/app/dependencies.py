"""Gateway が注入した認証ヘッダーを読む FastAPI 依存関係。"""

from __future__ import annotations

from typing import List, Optional

from fastapi import Depends, Header, HTTPException, status

from app.models import UserRole

USER_ID_HEADER = "X-User-ID"
ROLES_HEADER = "X-Roles"
SCOPE_HEADER = "X-Scope"


def _parse_csv_header(value: Optional[str]) -> List[str]:
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def get_current_user(
    x_user_id: Optional[str] = Header(default=None, alias=USER_ID_HEADER),
) -> str:
    if x_user_id is None or x_user_id == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gateway 認証ヘッダーがありません",
        )
    return x_user_id


def get_current_active_user(current_user_id: str = Depends(get_current_user)) -> str:
    return current_user_id


def get_current_roles(
    x_roles: Optional[str] = Header(default=None, alias=ROLES_HEADER),
) -> List[str]:
    return _parse_csv_header(x_roles)


def require_admin(
    current_user_id: str = Depends(get_current_user),
    roles: List[str] = Depends(get_current_roles),
) -> str:
    if UserRole.ADMIN.value not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です",
        )
    return current_user_id


def get_optional_user(
    x_user_id: Optional[str] = Header(default=None, alias=USER_ID_HEADER),
) -> Optional[str]:
    if x_user_id is None or x_user_id == "":
        return None
    return x_user_id
