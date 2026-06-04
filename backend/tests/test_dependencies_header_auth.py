from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


def _build_app():
    from app.dependencies import get_current_user, require_admin

    app = FastAPI()

    @app.get("/me")
    def me(current_user_id: str = Depends(get_current_user)):
        return {"user_id": current_user_id}

    @app.get("/admin-only")
    def admin_only(current_user_id: str = Depends(require_admin)):
        return {"user_id": current_user_id}

    return app


def test_get_current_user_returns_gateway_user_id_header(user_id):
    client = TestClient(_build_app())

    response = client.get("/me", headers={"X-User-ID": user_id})

    assert response.status_code == 200
    assert response.json() == {"user_id": user_id}


def test_get_current_user_requires_gateway_user_id_header():
    client = TestClient(_build_app())

    response = client.get("/me")

    assert response.status_code == 401


def test_require_admin_allows_admin_role(user_id):
    client = TestClient(_build_app())

    response = client.get(
        "/admin-only",
        headers={"X-User-ID": user_id, "X-Roles": "admin"},
    )

    assert response.status_code == 200
    assert response.json() == {"user_id": user_id}


def test_require_admin_denies_user_role(user_id):
    client = TestClient(_build_app())

    response = client.get(
        "/admin-only",
        headers={"X-User-ID": user_id, "X-Roles": "user"},
    )

    assert response.status_code == 403


def test_require_admin_denies_missing_roles(user_id):
    client = TestClient(_build_app())

    response = client.get("/admin-only", headers={"X-User-ID": user_id})

    assert response.status_code == 403


def test_require_admin_allows_admin_among_multiple_roles(user_id):
    client = TestClient(_build_app())

    response = client.get(
        "/admin-only",
        headers={"X-User-ID": user_id, "X-Roles": "user,admin"},
    )

    assert response.status_code == 200
