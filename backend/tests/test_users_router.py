import uuid

import pytest


def _route_exists(app_or_router, method, path, prefix=""):
    for route in app_or_router.routes:
        route_path = f"{prefix}{getattr(route, 'path', '')}"
        if route_path == path and method in getattr(route, "methods", set()):
            return True
        if hasattr(route, "routes") and _route_exists(route, method, path, prefix=route_path):
            return True
    return False


def test_users_me_route_is_registered():
    from app.main import app

    assert _route_exists(app, "GET", "/users/me")


def test_parse_gateway_user_uuid_accepts_compact_uppercase_uuid(user_id):
    from app.dependencies import parse_gateway_user_uuid

    compact_uppercase_user_id = uuid.UUID(user_id).hex.upper()

    assert parse_gateway_user_uuid(compact_uppercase_user_id) == uuid.UUID(user_id)


def test_parse_gateway_user_uuid_rejects_invalid_uuid():
    from app.dependencies import parse_gateway_user_uuid

    with pytest.raises(Exception) as exc_info:
        parse_gateway_user_uuid("not-a-uuid")

    assert getattr(exc_info.value, "status_code", None) == 401
