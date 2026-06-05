"""Payment Service transport-level authorization."""

from fastapi import HTTPException, status


def assert_mtls_peer(client_certificate) -> None:
    # X-Forwarded-Token の受信ロジックは未実装。現状は mTLS peer のみを確認する。
    if client_certificate is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="mTLS peer certificate is required",
        )
