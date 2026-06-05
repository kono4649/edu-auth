"""Gateway がサービスへ転送する認証ヘッダーを組み立てる。"""

from __future__ import annotations


def build_downstream_headers(claims: dict) -> dict[str, str]:
    user_id = claims.get("sub")
    if not user_id:
        raise ValueError("sub claim is required")

    roles = claims.get("realm_access", {}).get("roles", [])
    scope = claims.get("scope")
    if scope is None:
        raise ValueError("scope claim is required")

    return {
        "X-User-ID": user_id,
        "X-Roles": ",".join(roles),
        "X-Scope": scope,
    }
