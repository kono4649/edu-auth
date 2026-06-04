"""
アプリケーション設定
環境変数から設定を読み込む
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # データベース設定
    database_url: str = "postgresql://user:password@db:5432/ecommerce"

    class Config:
        env_file = ".env"


settings = Settings()
