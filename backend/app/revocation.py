"""Redis backed token revocation store."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

REVOKED_TOKEN_KEY_PREFIX = "revoked:"


class RedisTokenRevocationStore:
    def __init__(self, redis):
        self._redis = redis

    def ensure_not_revoked(self, jti: str) -> None:
        if self._redis.exists(self._key(jti)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="トークンは失効済みです",
            )

    def revoke(self, jti: str, expires_at: datetime, now: Optional[datetime] = None) -> None:
        current_time = now
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        remaining_seconds = (_as_utc(expires_at) - _as_utc(current_time)).total_seconds()
        if remaining_seconds <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="期限切れトークンは失効登録できません",
            )

        ttl = math.ceil(remaining_seconds)
        self._redis.set(self._key(jti), "1", ex=ttl)

    def _key(self, jti: str) -> str:
        return f"{REVOKED_TOKEN_KEY_PREFIX}{jti}"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
