# アーキテクチャレビュー: codex-write-test-20260604

**対象:** ブランチ全変更  
**日付:** 2026-06-04  
**レビュアー:** Architecture Review Agent

---

## 総合評価

**WARN** — Gateway 移行の方向性は正しく、RS256/JWKS・JTI 強制・Redis 失効・監査ログ・PKCE OIDC フロントエンドという設計判断は全て適切。ただし、UUID パース重複・`services/` 認可モジュールの未接続・`schemas.py` の死んだスキーマ・`AuditLogger`/`RedisTokenRevocationStore` の wire-up 未実装という具体的な欠陥が残っており、本番投入前に解消が必要。

---

## アーキテクチャ設計

### 評価できる点

1. **信頼境界の明確化** — Gateway が RS256/JWKS で検証済みの `X-User-ID / X-Roles / X-Scope` を注入し、バックエンドはそのヘッダーを無条件に信頼する構造になっている。認証責務と細粒度認可責務が cleanly 分離されている。

2. **JWKSJWTVerifier の設計品質** — kid 単位キャッシュ + TTL 付き自動再フェッチ + 空レスポンス時の旧キャッシュ維持という実用的なフォールバック戦略を持つ。`now` パラメータで時計を注入可能にしており、テスタビリティが高い。alg: RS256 固定チェックと jti 必須チェックにより algorithm confusion および jti-less token 攻撃の両方を防いでいる。

3. **二層認可モデル** — `gateway/policy.py`（粗粒度 ACL）と `services/*/authorization.py`（細粒度）の二層構成は、サービスメッシュ移行を見越した合理的なモデル。

4. **RedisTokenRevocationStore** — TTL を `math.ceil(remaining_seconds)` で切り上げる実装により、Redis の TTL 精度に起因するトークン延命を防いでいる。`_as_utc` によるタイムゾーン正規化も正確。

5. **User モデルの UUID 移行** — `id: int` から `Uuid(as_uuid=True)` への変更と `hashed_password` / `is_active` の削除は、IdP への認証委譲後の正しいスキーマ方向。

6. **フロントエンド OIDC PKCE 実装** — `crypto.subtle` による SHA-256 計算、state 検証、PKCE verifier/challenge の正確な実装。oidc ライブラリ依存を避けた軽量な手書き実装で、学習用途の明示性も高い。

---

### 指摘事項

#### 🔴 REJECT

**[R1] `_parse_user_uuid` の DRY 違反: `orders.py` にローカル定義、`dependencies.py` に `parse_gateway_user_uuid` が存在し実装が重複**

`app/routers/orders.py:29-36` に `_parse_user_uuid` がローカル定義されているが、`app/dependencies.py:40-47` に全く同じロジックの `parse_gateway_user_uuid` が既に存在する。`admin.py` と `users.py` は後者を使っているが、`orders.py` だけが重複定義を持つ。

- 影響: 同一の認証バリデーションロジックが 2 箇所に存在するため、一方だけが変更された場合に動作が乖離する。
- 対処: `orders.py` の `_parse_user_uuid` を削除し、`parse_gateway_user_uuid` を import して使用する。

**[R2] `AuditLogger` と `RedisTokenRevocationStore` が wire-up されていない**

`app/audit.py` の `AuditLogger` および `app/revocation.py` の `RedisTokenRevocationStore` はクラスが実装されテストも通っているが、FastAPI アプリケーションのいかなる箇所からも利用されていない。`main.py` への DI 登録がなく、ルーターや依存関係への接続もない。

- 影響: 認証イベントの監査ログが記録されない。ログアウト・トークン失効 API が存在しないため、`RedisTokenRevocationStore.revoke()` を呼ぶエンドポイントがない。`JWKSJWTVerifier` が JTI チェックを行っても、失効済み JTI が `ensure_not_revoked` に渡されることがない。
- 対処: ログアウトエンドポイントを実装するか、あるいはこれらが外部（ゲートウェイ側）に委ねるコンポーネントであることをドキュメントに明示し、内部コードからの参照を削除する。実行されないコードをコードベースに残すことは REJECT。

#### 🟡 WARN

**[W1] `schemas.py` に認証関連の死んだスキーマが 5 クラス残存**

`auth.py` ルーターが削除された一方、`schemas.py` の `UserRegister`, `UserLogin`, `TokenResponse`, `TokenRefreshRequest`, `AccessTokenResponse` がそのまま残っている（行 14-37）。これらを使用するコードはコードベース上に存在しない。

- 影響: 読み手が「これらを使う API が存在するのか」と誤解する。将来誰かが誤って参照する可能性。
- 対処: 5 クラスすべてを削除する。

**[W2] `services/*/authorization.py` が実際のルーター・エンドポイントから呼び出されていない**

`services/order_service/authorization.py:assert_order_access`、`services/product_service/authorization.py:assert_product_write_allowed`、`services/user_service/authorization.py:can_update_profile`、`services/payment_service/authorization.py:assert_payment_write_allowed` の全ての細粒度認可関数がテストのみから参照されており、実際のルーター (`orders.py`, `products.py`, `users.py`) からは呼び出されていない。

- 影響: 設計上は「router → services/*/authorization で細粒度認可」という二層の意図があるが、現状は router が直接 `dependencies.py` の依存関係のみで認可を行っており、`services/` 層が迂回されている。`assert_order_access` が呼ばれないため、注文所有者チェックは `orders.py:81` の `order.user_id != _parse_user_uuid(current_user_id)` が直接実装しているが、`services/order_service/authorization.py` と二重管理になっている。
- 対処: `services/*/authorization.py` を実際に呼び出すか、router での直接実装を正とし `services/` 認可モジュールを削除してアーキテクチャを一本化するか、どちらかに統一する。

**[W3] `build_payment_request_headers` が `Authorization: Bearer` ヘッダーを下流に `X-Forwarded-Token` として転送する設計が未定義**

`services/order_service/payment_client.py` は受信した Bearer トークンを `X-Forwarded-Token` として payment service に転送するが、payment service 側の `transport.py` は mTLS peer のみをチェックし、`X-Forwarded-Token` を読まない。二モジュール間でトークン伝播の契約が不整合。また、`payment_client.py` も同様に wire-up されていない。

- 影響: east-west 認証チェーンの設計が不完全のまま。
- 対処: 二サービス間のトークン伝播契約を決定し、payment_service 側の受信ロジックを実装するか、`payment_client.py` をドキュメント的サンプルとして明示する。

**[W4] `GatewayPolicy` のパスマッチングが文字列リテラルのみで型安全性がない**

`gateway/policy.py` の `_requires_admin` および `_requires_payment_write_scope` は `/api/products`, `/api/admin/`, `/api/payments` 等の文字列リテラルで判定している。FastAPI ルーター側のパス定義（`/products`, `/admin/`, `/orders`）にはプレフィックス `/api` が含まれないため、ゲートウェイがどのパスを受け取るかの前提が実装上どこにも明示されていない。

- 影響: ゲートウェイのルーティング設定変更時に policy.py の変更漏れが発生しやすい。
- 対処: パス定数を `policy.py` の先頭に集約するか、設計上「このクラスは API Gateway インフラ側のコード」であることを明示したコメントを加える。

#### 🔵 INFO

**[I1] テスト補助関数 `_route_exists` が 2 ファイルにコピーされている**

`test_auth_router_removed.py:1-8` と `test_users_router.py:6-12` で同一の `_route_exists` 実装が重複している。`conftest.py` に移動すれば DRY。

**[I2] `AuthContext.register` が `login` と同一の OIDC redirect を呼び出している**

`frontend/src/contexts/AuthContext.tsx:53-55` の `register` は `oidcClient.signinRedirect()` を呼ぶだけで `login` と区別がない。この設計（IdP の登録フロー = サインイン開始）が意図的であれば `register` 関数を削除して `login` だけ公開すべき。

**[I3] フロントエンドのアクセストークンがインメモリ変数のみで永続化されていない**

`client.ts:5` の `let accessToken: string | null = null` はページリロード時に消える。`sessionStorage` または `localStorage` への保存がないため、リロードのたびに OIDC 認証ループが必要になる（または silent refresh が必要）。学習用途なら許容範囲だが、`AuthContext` の `useEffect` がリロード時に `userApi.me()` を試みても認証ヘッダーが消えている。

**[I4] `JWKSJWTVerifier` が `fastapi.HTTPException` に直接依存している**

`gateway/jwt.py` は「Gateway 境界での検証器」という位置づけだが、FastAPI の `HTTPException` を直接 raise している。Gateway は FastAPI と別デプロイになる可能性があり、その場合この依存は問題になる。現在の文脈（同一 FastAPI アプリ内）では動作するが、境界コンポーネントとして見ると結合が漏れている。

---

## レイヤー設計

### 境界・レイヤー構成

```
フロントエンド (OIDC PKCE)
    ↓ Bearer Token
[API Gateway 境界]
  gateway/jwt.py       ← RS256/JWKS 検証
  gateway/policy.py    ← 粗粒度 ACL
  gateway/headers.py   ← ヘッダー組み立て
    ↓ X-User-ID / X-Roles / X-Scope
[FastAPI バックエンド]
  dependencies.py      ← ヘッダー読み取り・ロール依存関係
  routers/             ← エンドポイント + 細粒度認可 (直接実装)
  services/*/authorization.py  ← 細粒度認可 (未接続)
  models.py / schemas.py
    ↓
  Database (PostgreSQL)
[横断的関心事]
  audit.py             ← 監査ログ (未接続)
  revocation.py        ← JTI 失効 (未接続)
```

**評価:** Gateway 層と Application 層の分離は明確。ただし `services/*/authorization.py` と `routers/` 内の直接認可実装が並存しており、「どちらが正の認可実装か」が曖昧。

### 依存方向

- `gateway/` モジュール群は `app.` を import しない → 境界分離として正しい
- `services/order_service/authorization.py` が `app.dependencies` を import → サービス層がインフラ層（ヘッダー定数）に依存。定数のみの import は許容範囲だが、結合の起点になりうる
- `services/payment_service/authorization.py` も同様

---

## モジュール設計

### `gateway/` パッケージ

| モジュール | 責務 | 評価 |
|---|---|---|
| `jwt.py` | RS256/JWKS 検証 | 単一責務・高凝集 |
| `policy.py` | 粗粒度 ACL | 単一責務。ただしパスリテラルのベタ書きは変更耐性が低い |
| `headers.py` | クレーム → ヘッダー変換 | 単一責務・薄い変換層として適切 |

### `services/` パッケージ

各サービス (`order_service`, `product_service`, `payment_service`, `user_service`) が `authorization.py` を持つ構造は Vertical Slice に向かう設計として評価できる。ただし実際のサービスロジック（コマンド・クエリ・リポジトリ）を持たず、現時点では認可関数のみが存在するため「サービス」の名前に対して実装が薄い。

### `dependencies.py`

旧実装（DB アクセス + JWT デコード）から Gateway ヘッダー読み取りへの刷新は設計として正しい。`parse_gateway_user_uuid` がここに定義されているのは適切。ただし `orders.py` が `_parse_user_uuid` をローカルに重複定義している（[R1] 参照）。

### `schemas.py`

`UserRegister`, `UserLogin`, `TokenResponse`, `TokenRefreshRequest`, `AccessTokenResponse` の 5 クラスは削除対象（[W1] 参照）。

---

## 未実装・スタブ確認

| 対象 | 状態 | 判定 |
|---|---|---|
| `audit.py:AuditLogger` | 実装済み・テスト済み・DI 未接続 | 🔴 REJECT — 実行されないコード |
| `revocation.py:RedisTokenRevocationStore` | 実装済み・テスト済み・DI 未接続・ログアウト API なし | 🔴 REJECT — 実行されないコード |
| `services/order_service/authorization.py` | 実装済み・テスト済み・ルーター未使用 | 🟡 WARN — 死んだパス |
| `services/product_service/authorization.py` | 実装済み・テスト済み・ルーター未使用 | 🟡 WARN — 死んだパス |
| `services/payment_service/authorization.py` | 実装済み・テスト済み・ルーター未使用 | 🟡 WARN — 死んだパス |
| `services/user_service/authorization.py` | 実装済み・テスト済み・ルーター未使用 | 🟡 WARN — 死んだパス |
| `services/order_service/payment_client.py` | 実装済み・テスト済み・呼び出し元なし | 🟡 WARN — 死んだパス |
| `services/payment_service/transport.py:assert_mtls_peer` | 実装済み・テスト済み・ルーター未使用 | 🟡 WARN — 死んだパス |
| `schemas.py:UserRegister` 等 5 クラス | 実装済み・使用箇所なし | 🟡 WARN — 死んだコード |

TODO/FIXME コメント: 差分内に未解決の TODO/FIXME は存在しない。

---

## 総括

### 設計判断として正しいもの

- HS256 + 共有秘密鍵モデルから RS256 + JWKS モデルへの移行は、マルチサービス・マルチテナント対応の基盤として正しい方向。
- User モデルから `hashed_password` を除去し `is_active` を IdP に委ねる変更は、責務分離の観点で一貫している。
- `jti` 必須チェックにより、ステートレス JWT でも失効管理の口が確保されている（ただし現時点では `RedisTokenRevocationStore` が未接続）。
- PKCE + state 検証のフロントエンド OIDC 実装は、認可コード横取り攻撃対策として適切。

### 本番投入前に必須の修正

1. **[R1]** `orders.py` の `_parse_user_uuid` を削除し `parse_gateway_user_uuid` を使用する。
2. **[R2]** `AuditLogger` と `RedisTokenRevocationStore` を wire-up するか、これらをコードベースから除去して外部責務であることを明示する。ログアウトエンドポイントの実装有無を決定する。

### 推奨修正（WARN 解消）

3. **[W1]** `schemas.py` の未使用 5 クラスを削除する。
4. **[W2]** `services/*/authorization.py` をルーターから呼び出すか、router 内の直接実装を正として `services/` 認可モジュールを削除し、二重管理を解消する。
5. **[W3]** east-west `X-Forwarded-Token` / mTLS 伝播契約を定義する。
