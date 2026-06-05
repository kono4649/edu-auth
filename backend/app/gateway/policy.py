"""Gateway レベルの粗粒度 ACL。"""

from __future__ import annotations

from dataclasses import dataclass


PUBLIC_PRODUCTS_PATH = "/api/products"
PRODUCTS_PATH_PREFIX = "/api/products/"
ADMIN_PATH_PREFIX = "/api/admin/"
ORDERS_PATH = "/api/orders"
PAYMENTS_PATH = "/api/payments"
PAYMENTS_PATH_PREFIX = "/api/payments/"
PAYMENT_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


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

        if normalized_method == "GET" and path == PUBLIC_PRODUCTS_PATH:
            return PolicyDecision(allowed=True)

        if self._requires_admin(normalized_method, path):
            return self._require_authenticated_role(user_id, roles, "admin")

        if normalized_method == "GET" and path == ORDERS_PATH:
            return self._require_authenticated(user_id)

        if self._requires_payment_write_scope(normalized_method, path):
            authn_decision = self._require_authenticated(user_id)
            if not authn_decision.allowed:
                return authn_decision
            allowed = "payments:write" in scopes
            return PolicyDecision(allowed=allowed, status_code=None if allowed else 403)

        return self._require_authenticated(user_id)

    def _requires_admin(self, method: str, path: str) -> bool:
        return (
            (method == "POST" and path == PUBLIC_PRODUCTS_PATH)
            or (method == "DELETE" and path.startswith(PRODUCTS_PATH_PREFIX))
            or path.startswith(ADMIN_PATH_PREFIX)
        )

    def _requires_payment_write_scope(self, method: str, path: str) -> bool:
        payment_path = path == PAYMENTS_PATH or path.startswith(PAYMENTS_PATH_PREFIX)
        return payment_path and method in PAYMENT_WRITE_METHODS

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
