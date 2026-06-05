"""サンプル実装: east-west 認証チェーン（Bearer → X-Forwarded-Token 伝播）

このモジュールは現在呼び出し元がなく、production 利用には以下の対応が必要:
- payment_service 側での X-Forwarded-Token 受信ロジックの実装
- または mTLS のみで east-west 認証を完結させる設計への変更
"""

from __future__ import annotations


def build_payment_request_headers(inbound_headers: dict[str, str]) -> dict[str, str]:
    authorization = inbound_headers.get("Authorization")
    if authorization is None:
        raise ValueError("Authorization header is required")

    scheme, _, token = authorization.partition(" ")
    if scheme != "Bearer" or token == "":
        raise ValueError("Bearer token is required")

    return {"X-Forwarded-Token": token}
