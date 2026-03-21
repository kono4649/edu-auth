"""
認証・認可のコアロジック
JWT トークンの生成・検証、パスワードハッシュ化

【学習ポイント】
Authentication（認証）= 「あなたは誰ですか？」を確認する
Authorization（認可）  = 「あなたには何が許可されていますか？」を確認する
"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ─── パスワードハッシュ化 ─────────────────────────────────────────────────────
# bcrypt: パスワードハッシュ化アルゴリズム
# - ソルト自動付与（同じパスワードでも毎回異なるハッシュ）
# - 計算コストが高い（ブルートフォース攻撃に強い）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    パスワードをbcryptでハッシュ化する
    DBには必ずこのハッシュ値を保存する（平文保存は絶対にしない）
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    入力パスワードとDBのハッシュを比較する
    passlib が自動的にソルトを考慮して比較してくれる
    """
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT トークン ────────────────────────────────────────────────────────────
"""
JWT (JSON Web Token) の構造:
  Header.Payload.Signature

  Header: {"alg": "HS256", "typ": "JWT"}
  Payload: {"sub": "user_id", "role": "user", "exp": timestamp, "type": "access"}
  Signature: HMAC-SHA256(base64(header) + "." + base64(payload), SECRET_KEY)

  ※ Payload は base64 エンコードされているだけで暗号化ではない（誰でも読める）
  ※ SECRET_KEY がないと Signature の偽造ができないため、改ざんを検知できる
"""


def create_access_token(user_id: int, role: str) -> str:
    """
    アクセストークンを生成する

    ペイロードに含める情報:
    - sub (subject): ユーザーID
    - role: ユーザーのロール（認可チェックに使用）
    - exp (expiration): 有効期限
    - type: トークン種別（アクセストークンとリフレッシュトークンを区別）
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: int) -> str:
    """
    リフレッシュトークンを生成する

    アクセストークンより長い有効期限を設定。
    ロール情報を含めない（アクセストークン更新時に最新ロールを再取得するため）
    """
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> Optional[dict]:
    """
    JWT トークンをデコード・検証する

    検証内容:
    1. 署名の正当性（SECRET_KEY による検証）
    2. 有効期限（exp クレームの確認）
    3. アルゴリズム（指定以外のアルゴリズムによる署名を拒否）
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        # 署名不正・有効期限切れ・不正なトークン形式など
        return None


def get_user_id_from_token(token: str) -> Optional[int]:
    """トークンからユーザーIDを取得"""
    payload = decode_token(token)
    if payload is None:
        return None
    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError):
        return None


def get_role_from_token(token: str) -> Optional[str]:
    """トークンからロールを取得（認可チェックに使用）"""
    payload = decode_token(token)
    if payload is None:
        return None
    return payload.get("role")
