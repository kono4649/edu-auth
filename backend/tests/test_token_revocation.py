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


def test_logout_accepts_timezone_naive_expiry_as_utc():
    from app.revocation import RedisTokenRevocationStore

    redis = FakeRedis()
    store = RedisTokenRevocationStore(redis=redis)
    now = datetime(2026, 6, 4, 12, 0, 0, tzinfo=timezone.utc)
    exp = datetime(2026, 6, 4, 12, 2, 3)

    store.revoke("unique-token-id", expires_at=exp, now=now)

    assert redis.set_calls == [
        {"key": "revoked:unique-token-id", "value": "1", "ex": 123}
    ]


def test_revoke_rounds_subsecond_ttl_up_to_one_second():
    from app.revocation import RedisTokenRevocationStore

    redis = FakeRedis()
    store = RedisTokenRevocationStore(redis=redis)
    now = datetime(2026, 6, 4, 12, 0, 0, 100000, tzinfo=timezone.utc)
    exp = datetime(2026, 6, 4, 12, 0, 1, tzinfo=timezone.utc)

    store.revoke("unique-token-id", expires_at=exp, now=now)

    assert redis.set_calls == [
        {"key": "revoked:unique-token-id", "value": "1", "ex": 1}
    ]


@pytest.mark.parametrize("seconds_until_expiry", [0, -30])
def test_revoke_rejects_already_expired_token(seconds_until_expiry):
    from app.revocation import RedisTokenRevocationStore

    redis = FakeRedis()
    store = RedisTokenRevocationStore(redis=redis)
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=seconds_until_expiry)

    with pytest.raises(Exception) as exc_info:
        store.revoke("unique-token-id", expires_at=exp, now=now)

    assert getattr(exc_info.value, "status_code", None) == 400
    assert redis.set_calls == []


def test_revocation_module_has_no_refresh_token_sentinel():
    import app.revocation as revocation

    assert not hasattr(revocation, "RefreshToken")
