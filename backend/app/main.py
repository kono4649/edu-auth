"""
FastAPI アプリケーションのエントリポイント
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import products, orders, admin, users

# DB テーブルの自動作成（開発用）
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Auth-NZ ECサイト学習アプリ",
    description="""
## Authentication & Authorization 学習用 ECサイト

認証は IdP / API Gateway が担当し、アプリケーションは Gateway が注入した
`X-User-ID`, `X-Roles`, `X-Scope` をもとに細粒度認可を行う。
    """,
    version="1.0.0",
)

# CORS 設定（フロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(admin.router)
app.include_router(users.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
