"""
FastAPI 依存性注入（Dependency Injection）による認証・認可ミドルウェア

【学習ポイント】
FastAPI の Depends() を使って、エンドポイントに認証・認可チェックを注入する。
これにより：
1. 認証ロジックを一箇所に集約できる
2. ルーター関数は「認証済みユーザー」を前提に処理を書ける
3. テスト時に差し替えが容易
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth import decode_token
from app.database import get_db
from app.models import User, UserRole

# Bearer トークンの抽出
# Authorization: Bearer <token> ヘッダーから自動的にトークンを取り出す
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    【Authentication 依存関係】
    リクエストの JWT アクセストークンを検証し、現在のユーザーを返す。

    失敗ケース:
    - トークンなし → 401 Unauthorized
    - トークン不正・期限切れ → 401 Unauthorized
    - type が "access" でない → 401 Unauthorized（リフレッシュトークンで API 呼び出しを防ぐ）
    - ユーザーが存在しない → 401 Unauthorized
    - ユーザーが無効化されている → 403 Forbidden
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報が無効です",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise credentials_exception

    # トークン種別チェック: リフレッシュトークンで API アクセスさせない
    if payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="アカウントが無効化されています",
        )

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    アクティブなユーザーのみを返す依存関係
    （get_current_user のラッパー、明示的な用途分けのため）
    """
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    【Authorization 依存関係】
    管理者ロールを持つユーザーのみアクセスを許可する。

    通常ユーザーが管理者エンドポイントにアクセスしようとすると 403 Forbidden を返す。
    これが「認可（Authorization）」の本質：
      - 認証済み（誰かは分かった）でも、
      - ロールが不足していればアクセス拒否
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です",
        )
    return current_user


def get_optional_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> User | None:
    """
    任意認証: トークンがあれば検証、なくても OK（商品一覧など）
    """
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None
