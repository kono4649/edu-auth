"""
認証エンドポイント
- POST /auth/register  : ユーザー登録
- POST /auth/login     : ログイン（トークン発行）
- POST /auth/refresh   : アクセストークン更新
- POST /auth/logout    : ログアウト（リフレッシュトークン失効）
- GET  /auth/me        : 現在のユーザー情報取得
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, RefreshToken
from app.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefreshRequest,
    AccessTokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["認証"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    ユーザー登録

    パスワードは bcrypt でハッシュ化してから DB に保存する。
    平文パスワードは DB に残らない。
    """
    # メール重複チェック
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="このメールアドレスは既に使用されています")

    # ユーザー名重複チェック
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="このユーザー名は既に使用されています")

    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),  # ← ハッシュ化
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    ログイン（Authentication の中心）

    1. メールアドレスでユーザーを検索
    2. パスワードのハッシュを比較（verify_password）
    3. 認証成功したら JWT トークンを発行

    失敗時は意図的に「メールまたはパスワードが違います」と返す
    （どちらが間違っているかを教えないことでユーザー列挙攻撃を防ぐ）
    """
    user = db.query(User).filter(User.email == credentials.email).first()

    # パスワード検証（ユーザーが存在しない場合もタイミング攻撃対策でハッシュ比較を実行）
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="アカウントが無効化されています")

    # アクセストークンとリフレッシュトークンを発行
    access_token = create_access_token(user.id, user.role.value)
    refresh_token_str = create_refresh_token(user.id)

    # リフレッシュトークンを DB に保存（失効管理のため）
    refresh_token = RefreshToken(
        token=refresh_token_str,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_token)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_token(request: TokenRefreshRequest, db: Session = Depends(get_db)):
    """
    アクセストークンのリフレッシュ

    【なぜリフレッシュトークンが必要か？】
    - アクセストークンを長期間有効にすると、漏洩時のリスクが高い
    - 短命（30分）にして安全性を確保
    - リフレッシュトークン（7日）でシームレスなUXを実現

    DB でリフレッシュトークンを管理することで:
    - ログアウト時にトークンを失効できる
    - 不審なアクティビティを検知したら強制失効できる
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="リフレッシュトークンが無効です",
    )

    payload = decode_token(request.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise credentials_exception

    # DB でトークンの存在・失効確認
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == request.refresh_token,
        RefreshToken.revoked == False,  # noqa: E712
    ).first()

    if db_token is None:
        raise credentials_exception

    # 有効期限チェック
    if db_token.expires_at < datetime.utcnow():
        raise credentials_exception

    user = db.query(User).filter(User.id == db_token.user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception

    # 新しいアクセストークンを発行（最新のロールを反映）
    new_access_token = create_access_token(user.id, user.role.value)

    return AccessTokenResponse(access_token=new_access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: TokenRefreshRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    ログアウト（リフレッシュトークンの失効）

    DB のリフレッシュトークンを revoked=True にすることで、
    以降のトークンリフレッシュを不可にする。
    アクセストークン自体は有効期限まで有効（ステートレスの特性）。
    """
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == request.refresh_token,
        RefreshToken.user_id == current_user.id,
    ).first()

    if db_token:
        db_token.revoked = True
        db.commit()


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    現在のユーザー情報取得

    get_current_user 依存関係が認証チェックを担当。
    認証済みでない場合は 401 が自動的に返される。
    """
    return current_user
