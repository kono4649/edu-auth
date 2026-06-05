import pytest


def test_order_to_payment_request_propagates_forwarded_token():
    from app.services.order_service.payment_client import build_payment_request_headers

    headers = build_payment_request_headers(inbound_headers={"Authorization": "Bearer original.jwt"})

    assert headers["X-Forwarded-Token"] == "original.jwt"


def test_payment_service_rejects_east_west_call_without_mtls_peer():
    from app.services.payment_service.transport import assert_mtls_peer

    with pytest.raises(Exception) as exc_info:
        assert_mtls_peer(client_certificate=None)

    assert getattr(exc_info.value, "status_code", None) == 403
