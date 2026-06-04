# タスク指示書: 認証・認可アーキテクチャ改修テストコード作成（全フェーズ）

## 目的

設計書に基づき、ターゲットアーキテクチャへの移行実装に先行するテストコードをプロジェクト内に作成する（TDD）。

## 参照資料

`/Users/kono/Documents/dev/105-edu-auth/docs/plans/auth-architecture-redesign.md`

この設計書が唯一のソース・オブ・トゥルース。

## プロジェクトルート

`/Users/kono/Documents/dev/105-edu-auth`

## 制約

- プロダクションコードは作成・変更しない（テストファイルのみ作成）
- 既存のテストパターン（命名規約・ディレクトリ構成・ヘルパー）に従う
- 外部依存（Redis, JWKS エンドポイント, Keycloak）はモック/フェイクで代替する
- 実装前のためテスト失敗・import エラーは想定内。既存モジュールの import パスミスは修正する

---

## Phase 1: IdP 導入（設計書 §5.1〜5.6, §3.2）

### `dependencies.py` 改修後テスト（設計書 §5.2）

**`get_current_user`**

- `X-User-ID` ヘッダーあり → ヘッダーのユーザーIDを返す
- `X-User-ID` ヘッダーなし → 401

**`require_admin`**

- `X-Roles: admin` → 通過
- `X-Roles: user` → 403
- `X-Roles` ヘッダーなし → 403
- `X-Roles: user,admin`（複数ロール）→ 通過

### JWT RS256 + JWKS 検証（設計書 §3.2, §3.3）

クレーム構造:

```json
{
  "iss": "https://idp.example.com",
  "sub": "user-uuid",
  "aud": ["api-gateway"],
  "exp": ...,
  "jti": "unique-token-id",
  "realm_access": { "roles": ["user"] },
  "scope": "openid profile orders:read"
}
```

- 有効な RS256 JWT → 検証通過
- `exp` 切れ → 401
- `iss` 不一致 → 401
- `aud` 不一致 → 401
- HS256 署名のトークン（アルゴリズム不一致）→ 401
- 同一 `kid` の2回目 JWKS 取得 → ネットワーク呼び出しなし（キャッシュ）

### User モデル変更（設計書 §5.4, §6.1）

- `hashed_password` フィールドが存在しない
- `is_active` フィールドが存在しない
- `id` は UUID 型
- `role` フィールドが存在し、デフォルト値 `user`
- `RefreshToken` モデルが存在しない

### `routers/auth.py` 削除後（設計書 §5.3）

- `POST /auth/login` が存在しない → 404
- `POST /auth/refresh` が存在しない → 404
- `POST /auth/logout` が存在しない → 404
- `GET /auth/me` が User Service に移管されている

---

## Phase 2: API Gateway 導入（設計書 §3.3）

### Gateway 粗粒度 RBAC（設計書 §3.3 認可マトリクス）

| エンドポイント           | 期待動作                              |
| ------------------------ | ------------------------------------- |
| `GET /api/products`      | 認証なしで通過                        |
| `POST /api/products`     | `admin` ロールなし → 403              |
| `DELETE /api/products/*` | `admin` ロールなし → 403              |
| `GET /api/orders`        | 認証済みなら通過（`user` or `admin`） |
| `GET /api/admin/*`       | `admin` ロールなし → 403              |
| `POST /api/payments`     | `payments:write` スコープなし → 403   |

### ヘッダー注入（設計書 §3.3）

- JWT 検証通過後に `X-User-ID`, `X-Roles`, `X-Scope` が下流に付与される
- 各ヘッダー値が JWT クレームの対応フィールドと一致する

---

## Phase 3: Redis トークン失効（設計書 §3.5.1）

キー設計: `revoked:<jti>`

- `revoked:<jti>` が Redis に存在 → 401（失効済み）
- `revoked:<jti>` が Redis に存在しない → 通過
- ログアウト時に `SET revoked:<jti> 1 EX <残りTTL>` が呼ばれる
- 書き込み TTL が `exp - 現在時刻` と一致する
- PostgreSQL の `refresh_tokens` テーブルへのアクセスが発生しない

---

## Phase 4: サービス分割・細粒度認可（設計書 §3.4）

各サービスは JWT を再検証しない。Gateway 注入ヘッダーのみを信頼する。

### User Service

- `X-User-ID` == `resource.user_id` → プロフィール更新可
- `X-User-ID` != `resource.user_id` → 403

### Order Service

- `X-User-ID` == 注文の `owner_id` → 200
- `X-User-ID` != 注文の `owner_id` → 403
- `X-User-ID` なし → 401

### Product Service

- `X-Roles: admin` → 作成・更新・削除可
- `X-Roles: user` → 403

### Payment Service（新規）

- `X-Scope` に `payments:write` 含む → 決済実行可
- `X-Scope` に `payments:write` 含まない → 403

### East-West 通信（設計書 §3.4）

- Order Service → Payment Service に `X-Forwarded-Token` が伝播される
- mTLS なし（証明書なし）の呼び出し → 拒否

---

## Phase 5: 運用インフラ（設計書 §3.5.4）

### 監査ログ構造検証

記録対象イベントごとに以下のフィールドが存在することを検証:

- `timestamp`（ISO8601）
- `event_type`（例: `auth.login.success`, `authz.deny`）
- `user_id`
- `ip_address`
- `resource`
- `result`

テストケース:

- ログイン成功 → `event_type: auth.login.success`
- ログイン失敗 → `event_type: auth.login.failure`
- トークン失効（ログアウト）→ `event_type: token.revoked`
- 認可拒否（403）→ `event_type: authz.deny`
- 管理者操作（ユーザー作成）→ `event_type: admin.user.create`
