from datetime import datetime

import pytest


class ListSink:
    def __init__(self):
        self.records = []

    def write(self, record):
        self.records.append(record)


@pytest.fixture
def audit_logger():
    from app.audit import AuditLogger

    sink = ListSink()
    return AuditLogger(sink=sink), sink


@pytest.mark.parametrize(
    ("method_name", "event_type", "result"),
    [
        ("login_success", "auth.login.success", "allow"),
        ("login_failure", "auth.login.failure", "deny"),
        ("token_revoked", "token.revoked", "allow"),
        ("authorization_denied", "authz.deny", "deny"),
        ("admin_user_created", "admin.user.create", "allow"),
    ],
)
def test_audit_events_are_structured(audit_logger, method_name, event_type, result):
    logger, sink = audit_logger

    getattr(logger, method_name)(
        user_id="user-uuid",
        ip_address="203.0.113.10",
        resource="/api/orders/123",
    )

    assert len(sink.records) == 1
    record = sink.records[0]
    assert set(record) >= {
        "timestamp",
        "event_type",
        "user_id",
        "ip_address",
        "resource",
        "result",
    }
    assert datetime.fromisoformat(record["timestamp"])
    assert record["event_type"] == event_type
    assert record["user_id"] == "user-uuid"
    assert record["ip_address"] == "203.0.113.10"
    assert record["resource"] == "/api/orders/123"
    assert record["result"] == result
