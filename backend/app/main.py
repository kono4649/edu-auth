"""
FastAPI アプリケーションのエントリポイント
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import auth, products, orders, admin

# DB テーブルの自動作成（開発用）
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Auth-NZ ECサイト学習アプリ",
    description="""
## Authentication & Authorization 学習用 ECサイト

### 認証 (Authentication)
誰であるかを確認するプロセス。JWT を使用。

### 認可 (Authorization)
何を許可するかを確認するプロセス。ロールベースアクセス制御（RBAC）を使用。

### ロール
- **user**: 商品閲覧・注文が可能
- **admin**: 商品管理・全注文閲覧・ユーザー管理が可能

### トークン
- **アクセストークン**: 30分間有効、API アクセスに使用
- **リフレッシュトークン**: 7日間有効、アクセストークン更新に使用
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
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(admin.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
