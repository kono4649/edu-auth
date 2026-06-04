# 認証・認可アーキテクチャ 改修設計書

## 概要

本ドキュメントは、現行の FastAPI モノリス構成を、マイクロサービス型の認証・認可アーキテクチャへ改修するための設計書である。

---

## 1. 現状分析

### 1.1 現行スタック

| コンポーネント | 現行 |
|---|---|
| バックエンド | FastAPI（Python 3.12）単一サービス |
| フロントエンド | React 18 + TypeScript + Vite |
| データベース | PostgreSQL 16 |
| JWT アルゴリズム | HS256（共通鍵署名） |
| 認証方式 | FastAPI 内蔵（独自実装） |
| 認可方式 | dependencies.py の DI ベースインライン実装 |
| トークン失効 | PostgreSQL の `refresh_tokens` テーブル |
| サービス間通信 | なし（単一プロセス） |
| ポリシーエンジン | なし |
| 監査ログ | なし |
| シークレット管理 | 環境変数・設定ファイル直書き |

### 1.2 現行の認証・認可フロー

```
[Client]
  │ POST /auth/login (ID/Password)
  ▼
[FastAPI - auth.py]
  │ bcrypt 検証 → JWT(HS256) 発行
  │ access_token (30分) + refresh_token (7日)
  ▼
[FastAPI - dependencies.py]
  │ get_current_user: Bearer トークン検証
  │ require_admin: role == ADMIN チェック
  ▼
[各 Router]
  │ orders.py: user_id == current_user.id チェック（リソース所有者）
  ▼
[PostgreSQL]
```

### 1.3 現行の課題・制約

| # | 課題 | 影響 |
|---|---|---|
| 1 | HS256 共通鍵 → 鍵を知るサービスが増えるほど漏洩リスク増大 | スケール不可 |
| 2 | 認証ロジックがアプリ内部に閉じている → IdP としての機能なし | SSO・外部連携不可 |
| 3 | API Gateway 不在 → 認証検証が各サービスに分散する懸念 | マイクロサービス化時に重複実装 |
| 4 | トークン失効が PostgreSQL → レイテンシ高、スケール困難 | 高負荷時のボトルネック |
| 5 | ポリシーが Python コードにハードコード → 変更のたびにデプロイ必要 | 運用コスト高 |
| 6 | サービス間認証なし → 内部 API の不正呼び出しを防げない | East-West セキュリティ欠如 |
| 7 | 監査ログなし → 認証・認可イベントの追跡不可 | コンプライアンス不適合 |
| 8 | シークレットが config.py にハードコード | 本番運用不可 |

---

## 2. ターゲットアーキテクチャ

### 2.1 全体レイヤー構成

```
┌─────────────────────────────────────────────────────┐
│  CLIENT LAYER                                       │
│  Web/Mobile App        External System (BtoB)       │
└───────────────┬─────────────────────────────────────┘
                │ ① ログイン / トークン取得要求
┌───────────────▼─────────────────────────────────────┐
│  IdP LAYER (Identity Provider / Authorization Server)│
│  ┌─────────────────┐ ┌────────────┐ ┌────────────┐  │
│  │ 認証エンドポイント│ │ トークン発行│ │ ユーザーDB  │  │
│  │ OIDC / OAuth 2.0│ │ JWT RS256  │ │ Keycloak等 │  │
│  └─────────────────┘ └────────────┘ └────────────┘  │
└───────────────┬─────────────────────────────────────┘
                │ ② JWT Access Token をリクエストヘッダーに付与
┌───────────────▼─────────────────────────────────────┐
│  GATEWAY LAYER (North-South)                        │
│  ┌──────────────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ JWT 検証          │ │ 粗粒度認可│ │ Rate Limit  │ │
│  │ JWKs / expiry確認│ │ RBAC/OPA │ │ Routing/TLS │ │
│  └──────────────────┘ └──────────┘ └─────────────┘ │
└───────────────┬─────────────────────────────────────┘
                │ ③ X-User-ID / X-Roles ヘッダー付きで転送
┌───────────────▼─────────────────────────────────────┐
│  SERVICES LAYER (細粒度認可)                         │
│  ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌──────┐ │
│  │User Service│ │Order Svc  │ │Product   │ │Paymnt│ │
│  │所有者チェック│ │自分の注文 │ │管理者のみ │ │スコープ│ │
│  └─────┬─────┘ └─────┬─────┘ └────┬─────┘ └──┬───┘ │
│        └──────────── mTLS ─────────────────────┘     │
└───────────────┬─────────────────────────────────────┘
                │ ④ DB / 外部サービスアクセス
┌───────────────▼─────────────────────────────────────┐
│  SHARED INFRASTRUCTURE                              │
│  ┌──────────┐ ┌────────────┐ ┌────────┐ ┌────────┐ │
│  │ Audit Log│ │Secrets Mgr │ │Policy  │ │Token   │ │
│  │ ELK等    │ │Vault/AWS SM│ │Engine  │ │Revocatn│ │
│  └──────────┘ └────────────┘ │OPA等   │ │Redis   │ │
│                               └────────┘ └────────┘ │
└─────────────────────────────────────────────────────┘
```

### 2.2 ターゲット技術スタック

| レイヤー | 採用候補 | 選定理由 |
|---|---|---|
| IdP | Keycloak（OSS）または Auth0 / Cognito | OIDC/OAuth 2.0 準拠、RS256 対応、LDAP 連携 |
| API Gateway | Kong または AWS API Gateway | JWT 検証プラグイン、OPA 連携、Rate Limit |
| JWT 署名 | RS256（非対称鍵） | 公開鍵のみで検証可能 → サービスに秘密鍵不要 |
| ポリシーエンジン | OPA（Open Policy Agent） | ポリシーをコードから分離、Rego 言語で管理 |
| トークン失効 | Redis | 低レイテンシ、TTL 管理、スケーラブル |
| サービス間認証 | mTLS（SPIFFE/SPIRE または Istio） | 相互証明書認証 |
| 監査ログ | Fluentd + Elasticsearch（ELK） | 構造化ログ、全文検索 |
| シークレット管理 | HashiCorp Vault または AWS Secrets Manager | 動的シークレット、自動ローテーション |

---

## 3. 各レイヤーの詳細設計

### 3.1 Client Layer

#### 現行との差分

| 項目 | 現行 | ターゲット |
|---|---|---|
| 認証フロー | 独自 /auth/login | OIDC Authorization Code Flow |
| トークン保存 | localStorage | メモリ（Access）+ httpOnly Cookie（Refresh）推奨 |
| BtoB 連携 | なし | Client Credentials Flow |

#### クライアント種別と認証フロー

```
Web/Mobile App
  → Authorization Code Flow + PKCE
  → IdP でログイン → access_token（JWT, 5〜15分）+ refresh_token（数日）

External System（BtoB）
  → Client Credentials Flow
  → client_id / client_secret → access_token のみ
```

---

### 3.2 IdP Layer（Identity Provider）

#### 現行との差分

| 項目 | 現行 | ターゲット |
|---|---|---|
| 署名アルゴリズム | HS256（共通鍵） | RS256（非対称鍵、JWKs エンドポイント公開） |
| ユーザー管理 | PostgreSQL（独自） | Keycloak の内部 DB または外部 LDAP |
| SSO | 非対応 | OIDC で実現 |
| MFA | 非対応 | Keycloak で TOTP / WebAuthn |
| トークン構造 | `{sub, role, exp, type}` | OIDC 標準クレーム + カスタムクレーム |

#### JWT クレーム設計（ターゲット）

```json
{
  "iss": "https://idp.example.com",
  "sub": "user-uuid",
  "aud": ["api-gateway"],
  "exp": 1234567890,
  "iat": 1234567800,
  "jti": "unique-token-id",
  "email": "user@example.com",
  "realm_access": {
    "roles": ["user"]
  },
  "scope": "openid profile email orders:read orders:write"
}
```

#### 現行 access_token との対応

| 現行クレーム | ターゲットクレーム | 備考 |
|---|---|---|
| `sub` (user_id) | `sub` (UUID) | 変更なし（形式は UUID 化） |
| `role` | `realm_access.roles[]` | Keycloak 標準構造 |
| `type` | `jti` + 署名で代替 | refresh_token との区別は token_type ヘッダー |
| なし | `iss`, `aud`, `jti`, `scope` | 追加 |

---

### 3.3 API Gateway Layer（North-South 認証）

#### 現行との差分

| 項目 | 現行 | ターゲット |
|---|---|---|
| JWT 検証箇所 | 各 FastAPI Router の Depends | Gateway に集約 |
| 検証方法 | HS256 共通鍵で verify | JWKs エンドポイントから公開鍵取得して検証 |
| 粗粒度認可 | なし（サービス内に混在） | Gateway の OPA プラグイン |
| ヘッダー Inject | なし | X-User-ID, X-Roles, X-Scope をダウンストリームに付与 |
| Rate Limit | なし | Gateway で実装 |
| TLS 終端 | Docker 内部通信 | Gateway で TLS 終端 |

#### Gateway での JWT 検証フロー

```
1. Authorization: Bearer <JWT> を受け取る
2. JWT ヘッダーの kid を確認
3. IdP の JWKS エンドポイント（キャッシュ優先）から公開鍵取得
4. RS256 署名検証
5. exp / iss / aud クレームの検証
6. （任意）Redis でトークン失効チェック
7. 粗粒度 RBAC: ロールとエンドポイントの ACL 照合
8. 通過後: X-User-ID, X-Roles, X-Scope ヘッダーを付与して転送
```

#### 粗粒度認可マトリクス（Gateway レベル）

| エンドポイントパターン | 必要ロール | Gateway ACL |
|---|---|---|
| `GET /api/products` | なし（公開） | 認証不要 |
| `POST /api/products` | admin | RBAC チェック |
| `DELETE /api/products/*` | admin | RBAC チェック |
| `GET /api/orders` | user or admin | 認証のみ |
| `GET /api/admin/*` | admin | RBAC チェック |
| `POST /api/payments` | user or admin | スコープチェック（`payments:write`） |

---

### 3.4 Microservices Layer（細粒度認可）

#### サービス分割方針

現行の単一 FastAPI アプリを以下のサービスに分割する。

| サービス名 | 現行対応 | 細粒度認可ロジック |
|---|---|---|
| User Service | `app/routers/` 内のユーザー関連 | 自分のプロフィールのみ更新可（`X-User-ID == resource.user_id`） |
| Order Service | `app/routers/orders.py` | 自分の注文のみ参照可（現行の user_id チェックを踏襲） |
| Product Service | `app/routers/products.py` | 管理者のみ作成・更新・削除（X-Roles に admin を含むか） |
| Payment Service | 現行なし（新規） | スコープ `payments:write` を含む JWT のみ決済実行可 |

#### 細粒度認可の実装方針

各サービスは JWT を再検証**しない**。Gateway が付与した以下のヘッダーを信頼する。

```
X-User-ID: <sub クレームの値>
X-Roles: user,admin
X-Scope: openid profile orders:read orders:write
```

リソース所有者チェックはサービス内のビジネスロジックで実施する（現行 `orders.py` の実装を継承）。

#### サービス間通信（East-West）

```
Order Service → Payment Service
  ├─ mTLS で相互認証（SPIFFE/SPIRE によるワークロードアイデンティティ）
  └─ 元の JWT を X-Forwarded-Token で伝播
     または サービスアカウントトークン（Keycloak Client Credentials）に変換

Istio / Linkerd 利用時:
  └─ サイドカープロキシが mTLS を自動処理（アプリコード変更不要）
```

---

### 3.5 Shared Infrastructure Layer

#### 3.5.1 Token Revocation（Redis）

現行の PostgreSQL `refresh_tokens` テーブルを Redis に移行する。

| 項目 | 現行 | ターゲット |
|---|---|---|
| ストレージ | PostgreSQL | Redis |
| キー | token（文字列） | `revoked:<jti>` |
| TTL | expires_at 列で管理 | Redis TTL（トークンの exp と同じ値） |
| ログアウト処理 | `revoked = true` に UPDATE | `SET revoked:<jti> 1 EX <ttl>` |
| チェック | SELECT クエリ | `EXISTS revoked:<jti>`（O(1)） |

#### 3.5.2 Policy Engine（OPA）

```
現行: Python コード内の if 文でハードコード
ターゲット: Rego ポリシーファイルで管理 → Git 管理 → CI/CD で反映

ポリシーファイル構成例:
  policies/
    ├── gateway.rego          # 粗粒度 ACL（Gateway 用）
    ├── order_service.rego    # Order Service の細粒度ポリシー
    └── product_service.rego  # Product Service のポリシー
```

#### 3.5.3 Secrets Manager

| シークレット | 現行 | ターゲット |
|---|---|---|
| DB 接続文字列 | config.py にハードコード | Vault / AWS SM から動的取得 |
| JWT 署名鍵 | SECRET_KEY 環境変数 | IdP（Keycloak）が管理 → アプリ不要 |
| サービス間クレデンシャル | なし | Vault の動的シークレット |

#### 3.5.4 Audit Log

```
記録対象イベント:
  - ログイン成功 / 失敗
  - トークン発行 / 失効 / リフレッシュ
  - 認可拒否（403）
  - 管理者操作（ユーザー作成・削除・ロール変更）
  - サービス間通信の認証イベント

ログ構造（JSON）:
  {
    "timestamp": "ISO8601",
    "event_type": "auth.login.success",
    "user_id": "<sub>",
    "ip_address": "...",
    "resource": "/api/orders/123",
    "result": "allow"
  }

転送先: Fluentd → Elasticsearch → Kibana ダッシュボード
```

---

## 4. 典型的なコールフロー（ターゲット）

### 4.1 ログイン → API 呼び出し

```
[1] ログイン
  Client → IdP: POST /realms/{realm}/protocol/openid-connect/token
                 {grant_type: authorization_code, code: ..., PKCE}
  IdP → Client: {access_token (JWT RS256, 15分), refresh_token (7日), id_token}

[2] API リクエスト
  Client → Gateway: GET /api/orders
                     Authorization: Bearer <access_token>

[3] Gateway での認証
  Gateway: JWT ヘッダーの kid → JWKS キャッシュから公開鍵取得
  Gateway: RS256 署名検証 + exp/iss/aud 検証
  Gateway: Redis で jti の失効チェック（任意）
  Gateway: OPA で粗粒度 RBAC チェック
  Gateway → Order Service: GET /orders
                            X-User-ID: <sub>
                            X-Roles: user
                            X-Scope: orders:read

[4] サービスで細粒度認可
  Order Service: X-User-ID を使って DB で所有者確認
  Order Service → Client: 200 OK {orders: [...]}

[5] East-West 通信（例: Order → Payment）
  Order Service → Payment Service: mTLS + X-Forwarded-Token
  Payment Service: X-Scope に payments:write を確認

[6] トークンリフレッシュ
  Client: access_token 失効検知（401 or exp チェック）
  Client → IdP: POST /token {grant_type: refresh_token, refresh_token: ...}
  IdP: refresh_token 有効性確認 → 新 access_token 発行

[7] ログアウト
  Client → IdP: POST /logout {refresh_token: ...}
  IdP: Redis に jti を失効登録（TTL = token の残り有効期間）
```

---

## 5. 現行コードの改修方針

### 5.1 backend/app/auth.py

| 現行 | 改修内容 |
|---|---|
| `create_access_token` (HS256) | 削除（IdP に移管） |
| `create_refresh_token` (HS256) | 削除（IdP に移管） |
| `decode_token` (HS256 verify) | 削除（Gateway に移管） |
| `hash_password` / `verify_password` | 削除（IdP に移管） |

> このファイルは IdP 導入後、**完全に不要**となる。

### 5.2 backend/app/dependencies.py

| 現行 | 改修内容 |
|---|---|
| `get_current_user` (JWT 検証 + DB 参照) | Gateway 注入ヘッダー（`X-User-ID`）の読み取りに変更 |
| `require_admin` (role チェック) | `X-Roles` ヘッダーの参照に変更（DB アクセス不要） |

### 5.3 backend/app/routers/auth.py

| 現行エンドポイント | 改修内容 |
|---|---|
| `POST /auth/register` | IdP の Admin API で代替（Keycloak のユーザー作成 API） |
| `POST /auth/login` | IdP のトークンエンドポイントで代替（削除） |
| `POST /auth/refresh` | IdP のリフレッシュエンドポイントで代替（削除） |
| `POST /auth/logout` | IdP のログアウトエンドポイントで代替（削除） |
| `GET /auth/me` | User Service に移管 |

### 5.4 backend/app/models.py

| 現行モデル | 改修内容 |
|---|---|
| `User` (hashed_password, is_active 等) | `user_id`（外部 IdP の sub）, `role`, ビジネス属性のみ残す |
| `RefreshToken` | 削除（Redis + IdP に移管） |
| `Product`, `Order`, `OrderItem` | 変更なし（各サービスの DB に分割） |

### 5.5 frontend/src/api/client.ts

| 現行 | 改修内容 |
|---|---|
| 独自ログイン API 呼び出し | OIDC ライブラリ（oidc-client-ts）に置き換え |
| localStorage にトークン保存 | メモリ保持（Access）+ httpOnly Cookie（Refresh）に変更 |
| 独自リフレッシュロジック | OIDC ライブラリのサイレントリフレッシュに置き換え |

### 5.6 frontend/src/contexts/AuthContext.tsx

| 現行 | 改修内容 |
|---|---|
| 独自 `login()` / `logout()` | OIDC ライブラリの `signinRedirect()` / `signoutRedirect()` に置き換え |
| `user` オブジェクト（独自構造） | OIDC User オブジェクト（`profile.sub`, `profile.roles` 等）に変更 |

---

## 6. データベース設計の変更

### 6.1 Users テーブル

```sql
-- 現行（削除・縮小）
-- hashed_password → IdP に移管
-- is_active → IdP に移管
-- created_at → IdP に移管

-- ターゲット（IdP の sub を外部キーとして保持）
CREATE TABLE users (
  id          UUID PRIMARY KEY,          -- IdP の sub と同値
  email       VARCHAR(255) UNIQUE NOT NULL,
  username    VARCHAR(100) UNIQUE NOT NULL,
  role        user_role NOT NULL DEFAULT 'user',
  created_at  TIMESTAMPTZ DEFAULT NOW()
  -- hashed_password, is_active は削除
);
```

### 6.2 RefreshTokens テーブル

```
削除。Redis + Keycloak で管理。
```

---

## 7. 移行フェーズ計画

### Phase 1: IdP 導入（HS256 → RS256、認証の外出し）

- Keycloak をコンテナで起動（docker-compose に追加）
- Realm / Client / Role を設定
- 現行ユーザーを Keycloak にマイグレーション
- backend の JWT 検証を RS256 / JWKS に変更
- frontend を OIDC ライブラリに切り替え
- `auth.py`, `routers/auth.py` の大部分を削除

### Phase 2: API Gateway 導入

- Kong または同等の Gateway をコンテナで追加
- JWT 検証ロジックを Gateway プラグインに移管
- `dependencies.py` をヘッダー読み取り方式に変更
- 粗粒度 RBAC を Gateway の OPA プラグインで実装

### Phase 3: Redis 導入とトークン失効

- Redis をコンテナで追加
- `refresh_tokens` テーブルを廃止
- ログアウト処理を Redis ベースに変更

### Phase 4: サービス分割（マイクロサービス化）

- 各 Router を独立した FastAPI サービスに分割
- サービスごとに独立した PostgreSQL スキーマ / DB を割り当て
- East-West 通信に mTLS を適用（Istio サイドカー or SPIFFE/SPIRE）

### Phase 5: 運用インフラ整備

- OPA ポリシーファイルの管理体制確立
- Vault / AWS SM によるシークレット管理
- Fluentd + ELK による監査ログ基盤
- 監視・アラート（Prometheus + Grafana）

---

## 8. 変更影響範囲サマリ

| ファイル / コンポーネント | 変更種別 | フェーズ |
|---|---|---|
| `backend/app/auth.py` | 削除 | Phase 1 |
| `backend/app/routers/auth.py` | 大幅削減 | Phase 1 |
| `backend/app/dependencies.py` | 改修（ヘッダー読み取り方式へ） | Phase 2 |
| `backend/app/config.py` | 改修（JWT 設定削除、Vault 連携追加） | Phase 1, 5 |
| `backend/app/models.py` | 改修（User 縮小、RefreshToken 削除） | Phase 1, 3 |
| `frontend/src/api/client.ts` | 大幅改修 | Phase 1 |
| `frontend/src/contexts/AuthContext.tsx` | 大幅改修 | Phase 1 |
| `docker-compose.yml` | 大幅追加（Keycloak, Kong, Redis, OPA） | Phase 1〜3 |
| `backend/app/routers/*.py` | 各サービスとして分割 | Phase 4 |
| `policies/*.rego` | 新規作成 | Phase 2, 5 |

---

## 9. セキュリティ考慮事項

| 観点 | 現行 | ターゲット |
|---|---|---|
| JWT 署名鍵の漏洩リスク | HS256 共通鍵 → 全サービスに共有必要 | RS256 → 公開鍵のみ配布、秘密鍵は IdP のみ |
| トークン窃取後の影響 | access_token 30分間有効 | 5〜15分に短縮 + Token Introspection（高セキュリティ用途） |
| XSS によるトークン窃取 | localStorage（XSS で窃取可） | httpOnly Cookie（JS からアクセス不可） |
| 内部 API の不正アクセス | 防御なし | mTLS でサービス間を相互認証 |
| ポリシー変更時のリスク | コード変更 + デプロイ必要 | OPA ポリシー更新のみ（ホットリロード可） |
| シークレットの漏洩 | config.py / 環境変数 | Vault の動的シークレット + 自動ローテーション |
