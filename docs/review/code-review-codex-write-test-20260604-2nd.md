# コードレビュー（再レビュー）: codex-write-test-20260604

**対象:** ブランチ `codex-write-test-20260604` 全変更ファイル
**日付:** 2026-06-04
**前回レビュー:** `code-review-codex-write-test-20260604.md`

---

## 前回指摘の解消状況

| # | 状態 | 内容 |
|---|------|------|
| 1 | ✅ 解消 | `write-code.md` パスを `./instruction/implement.md`（単数形）に修正 |
| 2–10 | ✅ 解消 | docs指摘すべて対応済み（review report記録あり） |

---

## 総合判定

10件の指摘（CONFIRMED 3件 / PLAUSIBLE 7件）

---

## 対応結果

**対応日:** 2026-06-04
**ステータス:** 全10件対応済み

| # | 状態 | 対応内容 |
|---|------|----------|
| 1 | 対応済み | `backend/app/routers/users.py` を追加し、`GET /users/me` を `main.py` に登録 |
| 2 | 対応済み | `frontend/src/api/oidc.ts` の `sessionStorage.removeItem` を state / PKCE 検証後へ移動 |
| 3 | 対応済み | `GatewayPolicy` に支払い write 操作用のサブパス判定を追加し、`POST` / `PUT` / `PATCH` / `DELETE` の `/api/payments` 配下で `payments:write` を必須化 |
| 4 | 対応済み | `revocation.py` で timezone-naive な `datetime` を UTC として扱う `_as_utc()` を追加 |
| 5 | 対応済み | `JWKSJWTVerifier` に JWKS キャッシュTTLを追加し、期限後はJWKSを再取得して廃止kidを信頼し続けないよう修正 |
| 6 | 対応済み | Gateway のユーザーIDを `uuid.UUID` で正規化する `parse_gateway_user_uuid()` を追加し、自己ロール変更ガードで使用 |
| 7 | 対応済み | スコープ用の `parse_scope_header()` を追加し、スペース区切り契約をコード上で明示 |
| 8 | 対応済み | `_parse_csv_header` を公開ヘルパー `parse_csv_header()` に改名し、Product Service の手書きロール分割を共通化 |
| 9 | 対応済み | 追加保証を持たない `get_current_active_user` を削除 |
| 10 | 対応済み | `revocation.py` の `RefreshToken = None` センチネルを削除 |

**追加テスト:**
- 支払いサブパスの `payments:write` 必須化
- timezone-naive `expires_at` の失効登録
- JWKS TTL切れ後の再取得と廃止kid拒否
- UUID大文字/コンパクト形式での自己変更ガード
- ロールCSV・スコープスペース区切り契約
- `get_current_active_user` / `RefreshToken` 削除確認
- `GET /users/me` ルート登録確認

**検証:**
- `/Users/kono/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python -m compileall backend/app backend/tests` 通過
- `/Users/kono/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python -m pytest backend/tests` → 63 passed
- `git diff --check` 通過

**未実施:**
- フロントエンドビルドは、実行環境に `npm` / `tsc` が存在しないため未実施

---

## 指摘一覧

### 🔴 CONFIRMED（確実な問題）

#### 1. `frontend/src/api/client.ts:75` — `/users/me` エンドポイントが存在しない

`userApi.me()` は `GET /api/users/me` を呼ぶが、バックエンドに `/users/` ルーターは存在しない。旧 `/auth/me` は auth ルーターごと削除されており、代替エンドポイントが未実装。

```typescript
export const userApi = {
  me: () => apiClient.get<User>('/users/me'),  // ❌ 対応するバックエンドルートなし
}
```

`main.py` に登録されているルーター: `products`, `orders`, `admin` のみ。

**影響:** ユーザープロフィール表示・ロール判定が全て 404 で失敗する。

---

#### 2. `frontend/src/api/oidc.ts:112` — sessionStorage削除が検証より前に実行される

PKCE verifier と state の削除が、値の検証より先に行われる。state が不一致の場合、sessionStorage はすでに空になっており、リトライ不可能。

```typescript
const expectedState = sessionStorage.getItem(OIDC_STATE_KEY)
const codeVerifier  = sessionStorage.getItem(PKCE_VERIFIER_KEY)
sessionStorage.removeItem(OIDC_STATE_KEY)      // ← 検証前に削除
sessionStorage.removeItem(PKCE_VERIFIER_KEY)   // ← 検証前に削除

if (state !== expectedState || !codeVerifier) { // 削除後に検証
    throw new Error('OIDC state or PKCE verifier is invalid')
}
```

**影響:** state 不一致発生時（ネットワーク障害・リプレイ攻撃）、ページリロードしても `expectedState === null` となり永久に認証不能。

---

#### 3. `backend/app/gateway/policy.py:34` — 支払いサブパスがスコープチェックをバイパスする

支払いのスコープ検証は `path == "/api/payments"`（完全一致）のみ。管理者チェックが `startswith` を使うのと不整合。

```python
# 支払い: 完全一致のみ
if normalized_method == "POST" and path == "/api/payments":
    ...scope check...

# 管理者: サブパスも対象
or (method == "DELETE" and path.startswith("/api/products/"))
or path.startswith("/api/admin/")
```

**影響:** `DELETE /api/payments/123`（キャンセル）や将来追加される `/api/payments/refund` などはスコープ検証なしで認証済みユーザー全員がアクセス可能になる。

---

### 🟡 PLAUSIBLE（現実的な問題）

#### 4. `backend/app/revocation.py:30` — timezone-naive な `expires_at` で TypeError

`revoke()` の `current_time` は常に timezone-aware（`datetime.now(timezone.utc)`）。一方 `models.py` の `DateTime` カラムは `default=datetime.utcnow`（naive）で作られる。DB 由来の日時を `expires_at` に渡すと `TypeError` で 500 になる。

```python
current_time = datetime.now(timezone.utc)  # aware
ttl = int((expires_at - current_time).total_seconds())  # naiveとの減算 → TypeError
```

**影響:** ログアウト/失効エンドポイントが DB DateTime から `expires_at` を取得するケースで 500 クラッシュ。

---

#### 5. `backend/app/gateway/jwt.py:46` — JWKSキャッシュが鍵ローテーション後も古い鍵を信頼し続ける

`_keys_by_kid` は一度キャッシュした kid を永続保持し、無効化しない。kid が存在する限り JWKS の再取得は行われない。

**影響:** IdP が署名鍵をローテーション（古い kid を廃止）した後も、漏洩した古い秘密鍵で署名されたトークンがキャッシュ内の旧公開鍵で検証成功する。プロセス再起動まで継続。

---

#### 6. `backend/app/routers/admin.py:39` — UUID大文字/コンパクト形式で自己変更ガードがバイパス

```python
if str(user_id) == admin_user_id:  # str(uuid.UUID) → 小文字ダッシュ付き形式
```

Gateway が UUID を大文字や区切りなし形式（例: `550E8400E29B41D4A716446655440000`）で転送すると一致しない。管理者が自分自身のロールを変更できてしまう。

---

#### 7. `backend/app/services/payment_service/authorization.py:13` — スコープの区切り文字が未定義（将来的な認証バイパスリスク）

スコープはスペース区切り（`.split()`）で分割するが、ロールはカンマ区切り。この違いがドキュメント化されておらず、将来 `_parse_csv_header`（カンマ分割）をスコープに流用すると全ユーザーが 403 になる。

---

#### 8. `backend/app/services/product_service/authorization.py:12` — `_parse_csv_header` のロジックを手書きで複製

`dependencies.py` に `_parse_csv_header` があるにもかかわらず、同一ロジックをインラインで再実装。

```python
# dependencies.py に既存
def _parse_csv_header(value): ...

# product_service/authorization.py で複製
roles = [role.strip() for role in headers.get(ROLES_HEADER, "").split(",") if role.strip()]
```

**影響:** 区切り文字仕様変更時に `_parse_csv_header` のみ修正されると product サービスのロールチェックが壊れる。

---

#### 9. `backend/app/dependencies.py:33` — `get_current_active_user` が実質何もしない偽の安全保証

```python
def get_current_active_user(current_user_id: str = Depends(get_current_user)) -> str:
    return current_user_id  # 何もしない
```

`get_current_user` と同一の動作で `is_active` チェックも失効チェックも行わないが、関数名が追加の保証を示唆する。

**影響:** 「アクティブユーザー」チェックが必要なエンドポイントでこの依存を使っても停止済みユーザーが通過する。

---

#### 10. `backend/app/revocation.py:11` — `RefreshToken = None` 意味不明なセンチネル

```python
RefreshToken = None  # なぜここにあるか不明
```

コーディングポリシーのスタブ禁止ルールに違反。将来の開発者を誤解させる。

---

## 変更ファイル一覧

| ファイル | 主な指摘 |
|---------|---------|
| `frontend/src/api/client.ts` | #1 |
| `frontend/src/api/oidc.ts` | #2 |
| `backend/app/gateway/policy.py` | #3 |
| `backend/app/revocation.py` | #4, #10 |
| `backend/app/gateway/jwt.py` | #5 |
| `backend/app/routers/admin.py` | #6 |
| `backend/app/services/payment_service/authorization.py` | #7 |
| `backend/app/services/product_service/authorization.py` | #8 |
| `backend/app/dependencies.py` | #9 |
