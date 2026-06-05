# auth-nz — Authentication & Authorization 学習 ECサイト

[![CI](https://github.com/kono4649/edu-auth/actions/workflows/ci.yml/badge.svg)](https://github.com/kono4649/edu-auth/actions/workflows/ci.yml)

**Authentication（認証）** と **Authorization（認可）** をソースコードを通じて理解するための、学習目的の ECサイトです。

## 技術スタック

| 役割 | 技術 |
|------|------|
| フロントエンド | React 18 + TypeScript + Vite |
| バックエンド | FastAPI (Python) |
| データベース | PostgreSQL 16 |
| 認証・認可 | JWT (JSON Web Token) |
| コンテナ | Docker / Docker Compose |

---

## 起動方法

```bash
docker compose up --build
```

| サービス | URL |
|----------|-----|
| フロントエンド | http://localhost:5173 |
| バックエンド API | http://localhost:8000 |
| API ドキュメント | http://localhost:8000/docs |

### テストアカウント（シードデータ）

| ロール | メール | パスワード |
|--------|--------|------------|
| 管理者 | admin@example.com | admin123 |
| 一般ユーザー | user@example.com | user123 |

---

## Authentication（認証）の仕組み

> **「あなたは誰ですか？」を確認するプロセス**

### JWT (JSON Web Token)

JWT は `Header.Payload.Signature` の3部から成るトークンです。

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9   ← Header (Base64)
.eyJzdWIiOiIxIiwicm9sZSI6InVzZXIiLCJleHAiOjE3MDAwMDAwMDB9  ← Payload (Base64)
.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c  ← Signature (HMAC-SHA256)
```

- **Payload は暗号化されていない**（Base64 デコードで誰でも読める）
- **SECRET_KEY がないと Signature を偽造できない**（改ざん検知）

### アクセストークン vs リフレッシュトークン

```
ログイン
  └→ アクセストークン（30分）   ← API 呼び出しに使用
  └→ リフレッシュトークン（7日）← アクセストークンの更新に使用
            │
            ↓ アクセストークン期限切れ
      POST /auth/refresh
            │
            ↓ 新しいアクセストークン発行
        API 呼び出し再開
```

**なぜ2種類あるか？**
- アクセストークンを長期間有効にすると漏洩リスクが高い
- 短命（30分）にして安全性を確保しつつ、リフレッシュトークンでシームレスな UX を実現

### パスワードハッシュ化

```python
# backend/app/auth.py

# ❌ 絶対にやってはいけない
db.save(plain_password)

# ✅ bcrypt でハッシュ化して保存
hashed = hash_password(plain_password)  # "$2b$12$..." の形式
db.save(hashed)

# 検証: ハッシュ同士を比較（平文に戻せない一方向ハッシュ）
verify_password(input_password, hashed)
```

**bcrypt の特徴：**
- ソルト自動付与（同じパスワードでも毎回異なるハッシュ）
- 計算コストが高い（ブルートフォース攻撃に強い）

---

## Authorization（認可）の仕組み

> **「あなたには何が許可されていますか？」を確認するプロセス**

### ロールベースアクセス制御 (RBAC)

```
UserRole
├── user   → 商品閲覧、自分の注文の作成・閲覧
└── admin  → 上記すべて + 商品管理 + 全注文管理 + ユーザー管理
```

### FastAPI の依存性注入による認可

```python
# backend/app/dependencies.py

def get_current_user(...) -> User:
    """Authentication: JWT を検証してユーザーを返す"""
    ...

def require_admin(current_user = Depends(get_current_user)) -> User:
    """Authorization: admin ロールかチェック"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(403, "管理者権限が必要です")
    return current_user
```

```python
# backend/app/routers/products.py

# ✅ 管理者のみ（認証 + 認可）
@router.post("/products")
def create_product(admin: User = Depends(require_admin)):
    ...

# ✅ 全員閲覧可（認証不要）
@router.get("/products")
def list_products():
    ...
```

### アクセス権限マトリクス

| エンドポイント | 未認証 | user | admin |
|----------------|--------|------|-------|
| GET /products | ✅ | ✅ | ✅ |
| POST /products | ❌ 401 | ❌ 403 | ✅ |
| DELETE /products/:id | ❌ 401 | ❌ 403 | ✅ |
| GET /orders（自分の）| ❌ 401 | ✅ | ✅ |
| GET /orders（全員の）| ❌ 401 | ❌ | ✅ |
| POST /orders | ❌ 401 | ✅ | ✅ |
| PUT /orders/:id/status | ❌ 401 | ❌ 403 | ✅ |
| GET /admin/users | ❌ 401 | ❌ 403 | ✅ |

> **401 Unauthorized** = 認証されていない（誰かわからない）
> **403 Forbidden** = 認証済みだが権限が不足（誰かはわかるが許可されていない）

### リソースレベルの認可

認可はロールだけでなく、「誰のデータか」でも制御します。

```python
# backend/app/routers/orders.py

@router.get("/orders/{order_id}")
def get_order(order_id: int, current_user: User = Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == order_id).first()

    # 自分の注文でも管理者でもない場合は 403
    if current_user.role != UserRole.ADMIN and order.user_id != current_user.id:
        raise HTTPException(403, "この注文にアクセスする権限がありません")
```

### Gateway 境界の責務

監査ログおよびトークン失効（JTI ブラックリスト）はAPIゲートウェイ側の責務として設計しています。バックエンドはゲートウェイが検証済みのヘッダーを信頼するのみで、独自の失効管理は行いません。

---

## フロントエンドの認証・認可

### トークン管理（Axios インターセプター）

```typescript
// frontend/src/api/client.ts

// リクエスト: 全 API 呼び出しに JWT を自動付与
apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// レスポンス: 401 時に自動でトークンリフレッシュ
apiClient.interceptors.response.use(null, async (error) => {
  if (error.response?.status === 401) {
    // refresh_token で新しい access_token を取得してリトライ
  }
})
```

### ルートガード（PrivateRoute）

```tsx
// frontend/src/components/PrivateRoute.tsx

// 未認証 → /login にリダイレクト
if (!isAuthenticated) return <Navigate to="/login" />

// 管理者以外 → /forbidden にリダイレクト
if (requireAdmin && !isAdmin) return <Navigate to="/forbidden" />
```

> ⚠️ **重要**: フロントエンドの認可は UX 目的のみ。
> ユーザーは開発者ツールや curl で直接 API を叩けるため、
> **セキュリティの本質はバックエンドの認可にある。**

---

## CI / GitHub Actions

プッシュ・プルリクエスト時に自動でバックエンドのテストを実行します。

| ワークフロー | トリガー | 内容 |
|-------------|---------|------|
| `CI` | push / pull_request | バックエンドの pytest を実行 |

ワークフローの定義: `.github/workflows/ci.yml`

---

## ディレクトリ構成

```
auth-nz/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI エントリポイント
│   │   ├── config.py        # 設定（JWT 秘密鍵・有効期限など）
│   │   ├── database.py      # DB 接続・セッション
│   │   ├── models.py        # SQLAlchemy モデル（User, Product, Order...）
│   │   ├── schemas.py       # Pydantic スキーマ（リクエスト/レスポンス型）
│   │   ├── auth.py          # JWT 生成・検証、パスワードハッシュ ★
│   │   ├── dependencies.py  # 認証・認可の依存関係 ★
│   │   └── routers/
│   │       ├── auth.py      # 登録・ログイン・リフレッシュ・ログアウト
│   │       ├── products.py  # 商品 CRUD
│   │       ├── orders.py    # 注文管理
│   │       └── admin.py     # 管理者専用操作
│   ├── seed.py              # 開発用シードデータ
│   └── requirements.txt
└── frontend/
    └── src/
        ├── api/
        │   └── client.ts    # Axios クライアント（JWT インターセプター） ★
        ├── contexts/
        │   └── AuthContext.tsx  # 認証状態のグローバル管理 ★
        ├── components/
        │   ├── Navbar.tsx       # ロールによる表示切り替え
        │   └── PrivateRoute.tsx # ルートガード ★
        └── pages/
            ├── Home.tsx     # 概念説明・権限マトリクス
            ├── Login.tsx
            ├── Register.tsx
            ├── Products.tsx # 公開ページ（管理者UI切り替え）
            ├── Orders.tsx   # 要認証（管理者は全件表示）
            ├── Admin.tsx    # 要管理者権限
            └── Forbidden.tsx
```

★ = 認証・認可の学習に特に重要なファイル

---

## 学習のポイントとなるコード箇所

| 学習テーマ | ファイル |
|------------|----------|
| JWT 生成・検証 | `backend/app/auth.py` |
| 依存性注入による認可 | `backend/app/dependencies.py` |
| ログイン・トークン発行 | `backend/app/routers/auth.py` |
| リソースレベル認可 | `backend/app/routers/orders.py` |
| Axios JWT インターセプター | `frontend/src/api/client.ts` |
| 認証状態管理 | `frontend/src/contexts/AuthContext.tsx` |
| フロントエンドのルートガード | `frontend/src/components/PrivateRoute.tsx` |
