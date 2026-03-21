"""
データベース接続設定
SQLAlchemy を使って PostgreSQL に接続する
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# データベースエンジンの作成
engine = create_engine(settings.database_url)

# セッションファクトリ
# autocommit=False: 明示的なcommit()が必要（トランザクション管理）
# autoflush=False: flush()を手動で制御
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルの基底クラス
Base = declarative_base()


def get_db():
    """
    FastAPI の依存性注入で使うデータベースセッションの生成器
    リクエストごとにセッションを作成し、終了後に必ずcloseする
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
