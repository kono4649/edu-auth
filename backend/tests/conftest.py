import base64
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from jose import jwt


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def user_id():
    return "2db09e4f-9f32-4d21-9b44-e5e0bb74a0f1"


@pytest.fixture
def rsa_keypair():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return private_key, private_pem


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


@pytest.fixture
def jwks(rsa_keypair):
    private_key, _ = rsa_keypair
    numbers = private_key.public_key().public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "target-key",
                "alg": "RS256",
                "n": _b64url_uint(numbers.n),
                "e": _b64url_uint(numbers.e),
            }
        ]
    }


@pytest.fixture
def make_rs256_token(rsa_keypair, user_id):
    _, private_pem = rsa_keypair

    def _make_token(**overrides):
        now = datetime.now(timezone.utc)
        claims = {
            "iss": "https://idp.example.com",
            "sub": user_id,
            "aud": ["api-gateway"],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "jti": "unique-token-id",
            "realm_access": {"roles": ["user"]},
            "scope": "openid profile orders:read",
        }
        claims.update(overrides)
        return jwt.encode(
            claims,
            private_pem,
            algorithm="RS256",
            headers={"kid": "target-key"},
        )

    return _make_token


class FakeRedis:
    def __init__(self, existing_keys=None):
        self.existing_keys = set(existing_keys or [])
        self.set_calls = []

    def exists(self, key):
        return key in self.existing_keys

    def set(self, key, value, ex=None):
        self.set_calls.append({"key": key, "value": value, "ex": ex})
        return True
