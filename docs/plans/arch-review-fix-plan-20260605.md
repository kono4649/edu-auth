# アーキテクチャレビュー 対応計画

**参照レビュー:** `docs/review/arch-review-codex-write-test-20260604.md`  
**作成日:** 2026-06-05  
**対象:** REJECT 2件 / WARN 4件

---

## 対応サマリー

| ID | 分類 | 内容 | 方針 |
|----|------|------|------|
| R1 | 🔴 REJECT | `orders.py` の `_parse_user_uuid` DRY 違反 | `parse_gateway_user_uuid` に統一 |
| R2 | 🔴 REJECT | `AuditLogger` / `RedisTokenRevocationStore` が未接続 | 削除・Gateway 責務として明記 |
| W1 | 🟡 WARN | `schemas.py` 未使用 5 クラス残存 | 削除 |
| W2 | 🟡 WARN | `services/*/authorization.py` がルーター未接続 | 削除・router 直接実装に一本化 |
| W3 | 🟡 WARN | `payment_client.py` / `transport.py` の east-west 契約不整合 | サンプルとして明示 |
| W4 | 🟡 WARN | `gateway/policy.py` パスリテラルの型安全性なし | 定数化 |

---

## R1: `orders.py` の `_parse_user_uuid` DRY 違反を解消

**対象ファイル:** `app/routers/orders.py`

**対処:**
1. `orders.py` の `_parse_user_uuid` ローカル定義（行 29–36）を削除する
2. `from app.dependencies import parse_gateway_user_uuid` を追加する
3. ファイル内の `_parse_user_uuid` 呼び出しをすべて `parse_gateway_user_uuid` に置き換える

**検証条件:**
- `orders.py` に `_parse_user_uuid` が存在しないこと
- `parse_gateway_user_uuid` が import・使用されていること
- 既存テストが通ること

---

## R2: `AuditLogger` / `RedisTokenRevocationStore` を削除

**方針:** 削除する。監査ログおよびトークン失効は Gateway 側の責務とし、バックエンドには実装しない。

**削除対象:**
- `app/audit.py`
- `app/revocation.py`
- 上記を import しているすべてのファイルから import 文を除去
- 対応するテストファイル（`tests/test_audit.py`、`tests/test_revocation.py` 等）

**ドキュメント更新:**
- `README.md` に以下を追記する:
  > 監査ログおよびトークン失効（JTI ブラックリスト）はAPIゲートウェイ側の責務として設計しています。バックエンドはゲートウェイが検証済みのヘッダーを信頼するのみで、独自の失効管理は行いません。

**検証条件:**
- `app/audit.py`、`app/revocation.py` がコードベースに存在しないこと
- これらへの import 参照がコードベースに残っていないこと
- テストが通ること
- README に方針が明記されていること

---

## W1: `schemas.py` 未使用 5 クラスを削除

**対象ファイル:** `app/schemas.py`

**削除対象クラス（行 14–37 付近）:**
- `UserRegister`
- `UserLogin`
- `TokenResponse`
- `TokenRefreshRequest`
- `AccessTokenResponse`

**対処:**
1. 上記 5 クラスをすべて削除する
2. コードベース全体で参照がないことを確認し、参照が見つかった場合はその行も削除する

**検証条件:**
- `schemas.py` に上記 5 クラスが存在しないこと
- コードベース上に参照が残っていないこと

---

## W2: `services/*/authorization.py` を全削除

**方針:** router 内の直接認可実装を正とし、`services/` 認可モジュールを削除して二重管理を解消する。

**削除対象:**
- `services/order_service/authorization.py`
- `services/product_service/authorization.py`
- `services/payment_service/authorization.py`
- `services/user_service/authorization.py`
- 上記に対応するテストファイル

**対処:**
1. 上記ファイルをすべて削除する
2. 削除後、router 側の直接認可実装に漏れがないか確認する
   - `orders.py`: 注文所有者チェックが機能していること
   - `products.py`・`users.py`・payments 系: router 側の実装が認可要件を完全にカバーしていること
3. 削除したモジュールへの import 参照がある場合は除去する

**検証条件:**
- `services/*/authorization.py` が 1 ファイルも存在しないこと
- router 側の認可実装に漏れがないこと
- テストが通ること

---

## W3: `payment_client.py` / `transport.py` をサンプルとして明示

**対象ファイル:**
- `services/order_service/payment_client.py`
- `services/payment_service/transport.py`

**対処:**
1. `payment_client.py` のファイル先頭にモジュール docstring を追加する:
   ```
   サンプル実装: east-west 認証チェーン（Bearer → X-Forwarded-Token 伝播）
   このモジュールは現在呼び出し元がなく、production 利用には以下の対応が必要:
   - payment_service 側での X-Forwarded-Token 受信ロジックの実装
   - または mTLS のみで east-west 認証を完結させる設計への変更
   ```
2. `transport.py` に、`X-Forwarded-Token` の受信ロジックが未実装である旨のコメントを追加する

**検証条件:**
- 両ファイルに設計意図を説明するコメント/docstring が存在すること

---

## W4: `gateway/policy.py` パスリテラルを定数化

**対象ファイル:** `gateway/policy.py`

**対処:**
1. `_requires_admin`・`_requires_payment_write_scope` 等で使用しているパスリテラルをファイル先頭に定数として集約する
2. メソッド内のリテラルをこれらの定数参照に置き換える

**検証条件:**
- パスリテラルが定数として集約されていること
- 挙動が変わっていないこと（既存テスト通過）

---

## 実施順序

影響範囲が小さいものから着手し、削除系を後半に配置する。

```
1. R1  orders.py DRY解消（単純な import 置き換え）
2. W1  schemas.py クリーンアップ（単純削除）
3. W4  gateway/policy.py 定数化（挙動変更なし）
4. W3  payment_client.py / transport.py コメント追加
5. W2  services/*/authorization.py 全削除（テスト削除を伴う）
6. R2  audit.py / revocation.py 削除 + README 更新
```
