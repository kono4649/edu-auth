import pytest


@pytest.fixture
def policy():
    from app.gateway.policy import GatewayPolicy

    return GatewayPolicy()


def test_public_products_list_passes_without_authentication(policy):
    decision = policy.authorize("GET", "/api/products", user_id=None, roles=[], scopes=[])

    assert decision.allowed is True


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/products"),
        ("DELETE", "/api/products/123"),
        ("GET", "/api/admin/users"),
    ],
)
def test_admin_routes_require_admin_role(policy, method, path):
    decision = policy.authorize(method, path, user_id="user-uuid", roles=["user"], scopes=[])

    assert decision.allowed is False
    assert decision.status_code == 403


@pytest.mark.parametrize("roles", [["user"], ["admin"]])
def test_orders_list_requires_any_authenticated_user(policy, roles):
    decision = policy.authorize("GET", "/api/orders", user_id="user-uuid", roles=roles, scopes=[])

    assert decision.allowed is True


def test_orders_list_denies_anonymous_user(policy):
    decision = policy.authorize("GET", "/api/orders", user_id=None, roles=[], scopes=[])

    assert decision.allowed is False
    assert decision.status_code == 401


def test_payments_write_requires_scope(policy):
    decision = policy.authorize(
        "POST",
        "/api/payments",
        user_id="user-uuid",
        roles=["user"],
        scopes=["openid", "profile"],
    )

    assert decision.allowed is False
    assert decision.status_code == 403


def test_headers_are_injected_from_verified_claims(user_id):
    from app.gateway.headers import build_downstream_headers

    headers = build_downstream_headers(
        {
            "sub": user_id,
            "realm_access": {"roles": ["user", "admin"]},
            "scope": "openid profile payments:write",
        }
    )

    assert headers == {
        "X-User-ID": user_id,
        "X-Roles": "user,admin",
        "X-Scope": "openid profile payments:write",
    }
