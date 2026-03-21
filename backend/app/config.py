"""
アプリケーション設定
環境変数から設定を読み込む
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # データベース設定
    database_url: str = "postgresql://user:password@db:5432/ecommerce"

    # JWT設定
    # SECRET_KEY: JWTトークンの署名に使う秘密鍵（本番環境では必ず強力なランダム文字列に変更）
    secret_key: str = "super-secret-key-change-in-production"
    # ALGORITHM: JWTの署名アルゴリズム（HS256 = HMAC + SHA-256）
    algorithm: str = "HS256"
    # アクセストークンの有効期限（短く設定することでセキュリティを高める）
    access_token_expire_minutes: int = 30
    # リフレッシュトークンの有効期限（長く設定してUXを維持）
    refresh_token_expire_days: int = 7

    class Config:
        env_file = ".env"


settings = Settings()
