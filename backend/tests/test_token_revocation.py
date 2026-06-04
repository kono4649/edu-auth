from datetime import datetime, timedelta, timezone

import pytest

from conftest import FakeRedis


def test_revoked_jti_is_rejected():
    from app.revocation import RedisTokenRevocationStore

    store = RedisTokenRevocationStore(redis=FakeRedis(existing_keys={"revoked:unique-token-id"}))

    with pytest.raises(Exception) as exc_info:
        store.ensure_not_revoked("unique-token-id")

    assert getattr(exc_info.value, "status_code", None) == 401


def test_non_revoked_jti_passes():
    from app.revocation import RedisTokenRevocationStore

    store = RedisTokenRevocationStore(redis=FakeRedis())

    assert store.ensure_not_revoked("unique-token-id") is None


def test_logout_writes_revoked_key_with_remaining_token_ttl():
    from app.revocation import RedisTokenRevocationStore

    redis = FakeRedis()
    store = RedisTokenRevocationStore(redis=redis)
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=123)

    store.revoke("unique-token-id", expires_at=exp, now=now)

    assert redis.set_calls == [
        {"key": "revoked:unique-token-id", "value": "1", "ex": 123}
    ]


def test_revocation_store_does_not_require_postgresql_refresh_tokens_table():
    from app.revocation import RedisTokenRevocationStore

    store = RedisTokenRevocationStore(redis=FakeRedis())

    assert "RefreshToken" not in repr(store)
