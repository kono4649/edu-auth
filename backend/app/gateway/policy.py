"""Gateway レベルの粗粒度 ACL。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    status_code: int | None = None


class GatewayPolicy:
    def authorize(
        self,
        method: str,
        path: str,
        user_id: str | None,
        roles: list[str],
        scopes: list[str],
    ) -> PolicyDecision:
        normalized_method = method.upper()

        if normalized_method == "GET" and path == "/api/products":
            return PolicyDecision(allowed=True)

        if self._requires_admin(normalized_method, path):
            return self._require_authenticated_role(user_id, roles, "admin")

        if normalized_method == "GET" and path == "/api/orders":
            return self._require_authenticated(user_id)

        if normalized_method == "POST" and path == "/api/payments":
            authn_decision = self._require_authenticated(user_id)
            if not authn_decision.allowed:
                return authn_decision
            allowed = "payments:write" in scopes
            return PolicyDecision(allowed=allowed, status_code=None if allowed else 403)

        return self._require_authenticated(user_id)

    def _requires_admin(self, method: str, path: str) -> bool:
        return (
            (method == "POST" and path == "/api/products")
            or (method == "DELETE" and path.startswith("/api/products/"))
            or path.startswith("/api/admin/")
        )

    def _require_authenticated(self, user_id: str | None) -> PolicyDecision:
        if user_id is None:
            return PolicyDecision(allowed=False, status_code=401)
        return PolicyDecision(allowed=True)

    def _require_authenticated_role(
        self,
        user_id: str | None,
        roles: list[str],
        role: str,
    ) -> PolicyDecision:
        authn_decision = self._require_authenticated(user_id)
        if not authn_decision.allowed:
            return authn_decision
        return PolicyDecision(allowed=role in roles, status_code=None if role in roles else 403)
