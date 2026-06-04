import pytest


def test_user_service_allows_owner_profile_update(user_id):
    from app.services.user_service.authorization import can_update_profile

    assert can_update_profile(headers={"X-User-ID": user_id}, resource_user_id=user_id) is True


def test_user_service_denies_non_owner_profile_update(user_id):
    from app.services.user_service.authorization import can_update_profile

    assert can_update_profile(headers={"X-User-ID": user_id}, resource_user_id="other-user") is False


def test_order_service_allows_owner_order_access(user_id):
    from app.services.order_service.authorization import assert_order_access

    assert assert_order_access(headers={"X-User-ID": user_id}, owner_id=user_id) is None


def test_order_service_denies_non_owner_order_access(user_id):
    from app.services.order_service.authorization import assert_order_access

    with pytest.raises(Exception) as exc_info:
        assert_order_access(headers={"X-User-ID": user_id}, owner_id="other-user")

    assert getattr(exc_info.value, "status_code", None) == 403


def test_order_service_requires_gateway_user_header():
    from app.services.order_service.authorization import assert_order_access

    with pytest.raises(Exception) as exc_info:
        assert_order_access(headers={}, owner_id="user-uuid")

    assert getattr(exc_info.value, "status_code", None) == 401


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_product_service_allows_admin_write_operations(operation):
    from app.services.product_service.authorization import assert_product_write_allowed

    assert assert_product_write_allowed(headers={"X-Roles": "admin"}, operation=operation) is None


def test_product_service_denies_user_write_operations():
    from app.services.product_service.authorization import assert_product_write_allowed

    with pytest.raises(Exception) as exc_info:
        assert_product_write_allowed(headers={"X-Roles": "user"}, operation="create")

    assert getattr(exc_info.value, "status_code", None) == 403


def test_payment_service_allows_payments_write_scope():
    from app.services.payment_service.authorization import assert_payment_write_allowed

    assert assert_payment_write_allowed(headers={"X-Scope": "openid payments:write"}) is None


def test_payment_service_denies_missing_payments_write_scope():
    from app.services.payment_service.authorization import assert_payment_write_allowed

    with pytest.raises(Exception) as exc_info:
        assert_payment_write_allowed(headers={"X-Scope": "openid profile"})

    assert getattr(exc_info.value, "status_code", None) == 403


def test_order_to_payment_request_propagates_forwarded_token():
    from app.services.order_service.payment_client import build_payment_request_headers

    headers = build_payment_request_headers(inbound_headers={"Authorization": "Bearer original.jwt"})

    assert headers["X-Forwarded-Token"] == "original.jwt"


def test_payment_service_rejects_east_west_call_without_mtls_peer():
    from app.services.payment_service.transport import assert_mtls_peer

    with pytest.raises(Exception) as exc_info:
        assert_mtls_peer(client_certificate=None)

    assert getattr(exc_info.value, "status_code", None) == 403
