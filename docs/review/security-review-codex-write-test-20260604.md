# セキュリティレビュー: codex-write-test-20260604

**レビュー対象:** ブランチ `codex-write-test-20260604` 全変更ファイル
**日付:** 2026-06-04

---

## 概要

このブランチは、自己発行 HS256 JWT + パスワード認証による旧設計から、**IdP/APIゲートウェイが認証を担い、バックエンドはゲートウェイが注入したヘッダー（`X-User-ID`, `X-Roles`, `X-Scope`）を信頼して細粒度認可を行う**新設計へのアーキテクチャ移行を実装している。

8件の候補を調査し、いずれも信頼度スコアが 8 未満（実際には全て 2〜3）に留まったため、**報告対象となる高信頼度の脆弱性はなし**。

---

## 調査済み候補と棄却理由

| # | 候補 | 信頼度 | 判定 | 棄却理由 |
|---|------|--------|------|---------|
| 1 | ゲートウェイヘッダーの偽造による認証バイパス (`dependencies.py`) | 2/10 | REFUTED | ゲートウェイ信頼モデルは意図的な設計（AWS API Gateway + Lambda と同等の構造）。ネットワーク分離は実装層の外側の責務 |
| 2 | `X-Roles` ヘッダーのカンマ区切り操作によるロール昇格 | 2/10 | REFUTED | VULN-1 の派生。ゲートウェイが JWT クレームから構築するヘッダーの完全性はゲートウェイ層の責務 |
| 3 | JWKS 空レスポンス時の古い鍵キャッシュ保持 (`gateway/jwt.py`) | 2/10 | REFUTED | `if refreshed_keys:` ガードは意図的な可用性設計（テストで明示的に検証済み）。攻撃には JWKS エンドポイント制御が前提となり現実的でない |
| 4 | `ensure_not_revoked` が JWT 検証に配線されていない (`revocation.py`) | 2/10 | REFUTED | `RedisTokenRevocationStore` も `JWKSJWTVerifier` も本番コードに配線されておらず、logout エンドポイントも存在しない。未完成の機能であり攻撃可能なサーフェスなし |
| 5 | `GET /products/{id}` が `is_active` を確認しない (`routers/products.py`) | 3/10 | REFUTED | 公開カタログ情報の機能的非整合。セキュリティ上の秘密性を持たないデータへのアクセス。注文は `is_active` チェックで適切にブロック |
| 6 | Bearer トークンの Payment Service への転送 (`order_service/payment_client.py`) | 2/10 | REFUTED | 本番コードから呼び出しなし。Payment Service は mTLS (`assert_mtls_peer`) で保護。認可は `X-Scope` ヘッダーで実施 |
| 7 | DB ロールと JWT クレームの乖離 (`models.py`, `routers/admin.py`) | 2/10 | REFUTED | ステートレス JWT システムの一般的な動作。このブランチで新規に導入されたリスクではない |
| 8 | `can_update_profile` のヘッダーキー大文字小文字感度 (`user_service/authorization.py`) | 2/10 | REFUTED | 本番ルーターからの呼び出しなし。ミスマッチは認可バイパスではなく正規ユーザーへのアクセス拒否（機能的回帰）を引き起こす |

---

## 削除されたセキュリティ機能の確認

旧設計から以下のセキュリティ機能が削除されている。いずれも新設計への移行に伴う意図的な変更であり、ゲートウェイ層が同等の保証を提供する前提。

| 削除された機能 | 代替 |
|-------------|------|
| パスワードハッシュ (`bcrypt`) + `hashed_password` カラム | IdP 側でのパスワード管理（OIDC フロー） |
| HS256 JWT 自己発行・検証 | IdP 発行 RS256 JWT + JWKS 検証（`JWKSJWTVerifier`） |
| `is_active` フラグによるアカウント無効化 | IdP 側でのユーザー無効化 |
| リフレッシュトークン DB 管理 | IdP セッション管理 |
| `/auth/login`, `/auth/logout`, `/auth/refresh` エンドポイント | OIDC フロー（`frontend/src/api/oidc.ts` で実装済み） |

---

## 総合判定

**高信頼度の脆弱性: なし**

本レビューでは、信頼度 8/10 以上の脆弱性は検出されなかった。
