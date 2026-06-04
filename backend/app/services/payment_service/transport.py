"""Payment Service transport-level authorization."""

from fastapi import HTTPException, status


def assert_mtls_peer(client_certificate) -> None:
    if client_certificate is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="mTLS peer certificate is required",
        )
