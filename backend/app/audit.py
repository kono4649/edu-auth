"""Structured audit log events."""

from datetime import datetime, timezone


class AuditLogger:
    def __init__(self, sink):
        self._sink = sink

    def login_success(self, user_id: str, ip_address: str, resource: str) -> None:
        self._write("auth.login.success", "allow", user_id, ip_address, resource)

    def login_failure(self, user_id: str, ip_address: str, resource: str) -> None:
        self._write("auth.login.failure", "deny", user_id, ip_address, resource)

    def token_revoked(self, user_id: str, ip_address: str, resource: str) -> None:
        self._write("token.revoked", "allow", user_id, ip_address, resource)

    def authorization_denied(self, user_id: str, ip_address: str, resource: str) -> None:
        self._write("authz.deny", "deny", user_id, ip_address, resource)

    def admin_user_created(self, user_id: str, ip_address: str, resource: str) -> None:
        self._write("admin.user.create", "allow", user_id, ip_address, resource)

    def _write(
        self,
        event_type: str,
        result: str,
        user_id: str,
        ip_address: str,
        resource: str,
    ) -> None:
        self._sink.write(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "ip_address": ip_address,
                "resource": resource,
                "result": result,
            }
        )
