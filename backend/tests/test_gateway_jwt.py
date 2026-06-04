from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt


class CountingJWKSClient:
    def __init__(self, jwks):
        self.jwks = jwks
        self.fetch_count = 0

    def fetch(self):
        self.fetch_count += 1
        return self.jwks


def _verifier(jwks):
    from app.gateway.jwt import JWKSJWTVerifier

    return JWKSJWTVerifier(
        jwks_client=CountingJWKSClient(jwks),
        issuer="https://idp.example.com",
        audience="api-gateway",
    )


def test_valid_rs256_jwt_is_accepted(jwks, make_rs256_token, user_id):
    verifier = _verifier(jwks)

    claims = verifier.verify_access_token(make_rs256_token())

    assert claims["sub"] == user_id
    assert claims["realm_access"]["roles"] == ["user"]
    assert claims["scope"] == "openid profile orders:read"


@pytest.mark.parametrize(
    ("claim_overrides", "expected_status"),
    [
        ({"exp": int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())}, 401),
        ({"iss": "https://evil-idp.example.com"}, 401),
        ({"aud": ["other-gateway"]}, 401),
    ],
)
def test_invalid_claims_are_rejected(jwks, make_rs256_token, claim_overrides, expected_status):
    verifier = _verifier(jwks)

    with pytest.raises(Exception) as exc_info:
        verifier.verify_access_token(make_rs256_token(**claim_overrides))

    assert getattr(exc_info.value, "status_code", None) == expected_status


def test_hs256_token_is_rejected_even_with_matching_claims(jwks, user_id):
    verifier = _verifier(jwks)
    token = jwt.encode(
        {
            "iss": "https://idp.example.com",
            "sub": user_id,
            "aud": ["api-gateway"],
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "jti": "unique-token-id",
            "realm_access": {"roles": ["user"]},
            "scope": "openid profile orders:read",
        },
        "shared-secret",
        algorithm="HS256",
        headers={"kid": "target-key"},
    )

    with pytest.raises(Exception) as exc_info:
        verifier.verify_access_token(token)

    assert getattr(exc_info.value, "status_code", None) == 401


def test_missing_jti_claim_is_rejected(jwks, make_rs256_token):
    verifier = _verifier(jwks)

    with pytest.raises(Exception) as exc_info:
        verifier.verify_access_token(make_rs256_token(jti=None))

    assert getattr(exc_info.value, "status_code", None) == 401


def test_jwks_is_cached_for_second_token_with_same_kid(jwks, make_rs256_token):
    jwks_client = CountingJWKSClient(jwks)
    from app.gateway.jwt import JWKSJWTVerifier

    verifier = JWKSJWTVerifier(
        jwks_client=jwks_client,
        issuer="https://idp.example.com",
        audience="api-gateway",
    )

    verifier.verify_access_token(make_rs256_token(jti="first-token"))
    verifier.verify_access_token(make_rs256_token(jti="second-token"))

    assert jwks_client.fetch_count == 1


def test_jwks_cache_refreshes_after_ttl_and_rejects_removed_kid(jwks, make_rs256_token):
    from app.gateway.jwt import JWKSJWTVerifier

    current_time = datetime(2026, 6, 4, tzinfo=timezone.utc)
    jwks_client = CountingJWKSClient(jwks)
    verifier = JWKSJWTVerifier(
        jwks_client=jwks_client,
        issuer="https://idp.example.com",
        audience="api-gateway",
        cache_ttl_seconds=60,
        now=lambda: current_time,
    )

    verifier.verify_access_token(make_rs256_token(jti="before-rotation"))
    jwks_client.jwks = {"keys": [{**jwks["keys"][0], "kid": "rotated-key"}]}
    current_time = current_time + timedelta(seconds=61)

    with pytest.raises(Exception) as exc_info:
        verifier.verify_access_token(make_rs256_token(jti="after-rotation"))

    assert getattr(exc_info.value, "status_code", None) == 401
    assert jwks_client.fetch_count == 2


def test_jwks_empty_refresh_keeps_existing_cache_until_next_ttl(jwks, make_rs256_token):
    from app.gateway.jwt import JWKSJWTVerifier

    current_time = datetime(2026, 6, 4, tzinfo=timezone.utc)
    jwks_client = CountingJWKSClient(jwks)
    verifier = JWKSJWTVerifier(
        jwks_client=jwks_client,
        issuer="https://idp.example.com",
        audience="api-gateway",
        cache_ttl_seconds=60,
        now=lambda: current_time,
    )

    verifier.verify_access_token(make_rs256_token(jti="before-empty-jwks"))
    jwks_client.jwks = {"keys": []}
    current_time = current_time + timedelta(seconds=61)

    verifier.verify_access_token(make_rs256_token(jti="during-empty-jwks"))
    verifier.verify_access_token(make_rs256_token(jti="cache-hit-after-empty-jwks"))

    assert jwks_client.fetch_count == 2
