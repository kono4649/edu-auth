def _route_exists(app_or_router, method, path, prefix=""):
    for route in app_or_router.routes:
        route_path = f"{prefix}{getattr(route, 'path', '')}"
        if route_path == path and method in getattr(route, "methods", set()):
            return True
        if hasattr(route, "routes") and _route_exists(route, method, path, prefix=route_path):
            return True
    return False


def _route_paths(app_or_router, prefix=""):
    paths = set()
    for route in app_or_router.routes:
        route_path = f"{prefix}{getattr(route, 'path', '')}"
        if hasattr(route, "routes"):
            paths.update(_route_paths(route, prefix=route_path))
        else:
            paths.add(route_path)
    return paths


def test_legacy_auth_mutation_endpoints_are_removed():
    from app.main import app

    assert not _route_exists(app, "POST", "/auth/login")
    assert not _route_exists(app, "POST", "/auth/refresh")
    assert not _route_exists(app, "POST", "/auth/logout")


def test_auth_me_is_not_served_by_legacy_auth_router():
    from app.main import app

    assert "/auth/me" not in _route_paths(app)
