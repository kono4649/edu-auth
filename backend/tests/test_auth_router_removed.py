def _route_exists(app, method, path):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return True
    return False


def test_legacy_auth_mutation_endpoints_are_removed():
    from app.main import app

    assert not _route_exists(app, "POST", "/auth/login")
    assert not _route_exists(app, "POST", "/auth/refresh")
    assert not _route_exists(app, "POST", "/auth/logout")


def test_auth_me_is_not_served_by_legacy_auth_router():
    from app.main import app

    route_paths = {route.path for route in app.routes}

    assert "/auth/me" not in route_paths
