"""RS256 / JWKS access token verifier for the API Gateway boundary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import HTTPException, status
from jose import JWTError, jwk, jwt


class JWKSJWTVerifier:
    def __init__(
        self,
        jwks_client,
        issuer: str,
        audience: str,
        cache_ttl_seconds: int = 300,
        now: Callable[[], datetime] | None = None,
    ):
        self._jwks_client = jwks_client
        self._issuer = issuer
        self._audience = audience
        self._keys_by_kid: dict[str, dict] = {}
        self._cache_expires_at: datetime | None = None
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._now = now or (lambda: datetime.now(timezone.utc))

    def verify_access_token(self, token: str) -> dict:
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as exc:
            raise self._unauthorized() from exc

        if header.get("alg") != "RS256":
            raise self._unauthorized()

        kid = header.get("kid")
        if not kid:
            raise self._unauthorized()

        key_data = self._get_key(kid)
        try:
            public_key = jwk.construct(key_data).to_pem().decode("ascii")
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
            )
        except JWTError as exc:
            raise self._unauthorized() from exc

        if not claims.get("jti"):
            raise self._unauthorized()
        return claims

    def _get_key(self, kid: str) -> dict:
        if self._cache_is_expired() or kid not in self._keys_by_kid:
            self._refresh_keys()
        if kid not in self._keys_by_kid:
            raise self._unauthorized()
        return self._keys_by_kid[kid]

    def _cache_is_expired(self) -> bool:
        return self._cache_expires_at is None or self._now() >= self._cache_expires_at

    def _refresh_keys(self) -> None:
        jwks = self._jwks_client.fetch()
        refreshed_keys = {key["kid"]: key for key in jwks.get("keys", []) if "kid" in key}
        if refreshed_keys:
            self._keys_by_kid = refreshed_keys
        self._cache_expires_at = self._now() + self._cache_ttl

    def _unauthorized(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT が無効です",
        )
