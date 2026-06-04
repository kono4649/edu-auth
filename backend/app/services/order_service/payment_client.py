"""Order Service to Payment Service request helpers."""

from __future__ import annotations


def build_payment_request_headers(inbound_headers: dict[str, str]) -> dict[str, str]:
    authorization = inbound_headers.get("Authorization")
    if authorization is None:
        raise ValueError("Authorization header is required")

    scheme, _, token = authorization.partition(" ")
    if scheme != "Bearer" or token == "":
        raise ValueError("Bearer token is required")

    return {"X-Forwarded-Token": token}
