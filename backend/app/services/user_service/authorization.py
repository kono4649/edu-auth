"""User Service fine-grained authorization."""

from __future__ import annotations

from app.dependencies import USER_ID_HEADER


def can_update_profile(headers: dict[str, str], resource_user_id: str) -> bool:
    return headers.get(USER_ID_HEADER) == resource_user_id
