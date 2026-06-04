## 対応結果

**対応日:** 2026-06-04
**ステータス:** 全3件対応済み

| # | 状態 | 対応内容 |
|---|------|----------|
| 1 | 対応済み | `JWKSJWTVerifier._refresh_keys()` で空JWKSレスポンス時に既存キャッシュを保持し、非空JWKS時のみ鍵セットを置換するよう修正 |
| 2 | 対応済み | `RedisTokenRevocationStore.revoke()` のTTL計算を `math.ceil()` に変更し、残り1秒未満の有効トークンも `ex=1` で失効登録できるよう修正 |
| 3 | 対応済み | `parse_scope_header()` を `value.split()` に簡略化 |

**追加テスト:**
- 空JWKS refresh 時に既存キャッシュを保持し、TTL内の後続リクエストで再fetchしないこと
- 非空JWKS refresh で旧kidが拒否されること
- 残り1秒未満のTTLが1秒に切り上げられること

**検証:**
- `/Users/kono/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python -m compileall backend/app backend/tests` 通過
- `/Users/kono/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python -m pytest backend/tests` → 65 passed
- `git diff --check` 通過

---

## 新規指摘

### 🔴 CONFIRMED

#### 1. `backend/app/gateway/jwt.py:71` — JWKSが空を返すとTTL期間中ずっと全鍵消滅・毎リクエストfetchループ

`_refresh_keys()` が `self._keys_by_kid = {}` で全置換するため、JWKSが空レスポンスを返した場合に既存の有効な鍵がすべて消える。その後のリクエストは `_cache_is_expired() = False` だが `kid not in {}` が常にTrueとなり、TTL期間（デフォルト5分）の間、毎リクエスト `_refresh_keys()` を呼び続ける。

```python
def _refresh_keys(self) -> None:
    jwks = self._jwks_client.fetch()
    self._keys_by_kid = {key["kid"]: key ...}  # ← 全置換。空なら全鍵消滅
    self._cache_expires_at = self._now() + self._cache_ttl
```

旧実装の `.update()` は既存鍵を保持しており、JWKS一時障害時もキャッシュヒットを維持できていた。

**影響:** JWKSエンドポイントが503を無音で `{}` 返しするクライアント実装の場合、または鍵ローテーション中に旧鍵がJWKSから削除されるタイミングで、全トークン認証失敗＋JWKSへの連続ポーリングが発生する。

---

### 🟡 PLAUSIBLE

#### 2. `backend/app/revocation.py:29` — `int()` 切り捨てで残り1秒未満のトークン失効が拒否される

```python
ttl = int((_as_utc(expires_at) - _as_utc(current_time)).total_seconds())
if ttl <= 0:
    raise HTTPException(status_code=400, detail="期限切れトークンは失効登録できません")
```

残り0.9秒の場合: `int(0.9) = 0` → `ttl <= 0` → 400エラー。トークンはまだ有効だが失効登録を拒否される。`math.ceil()` または `max(1, int(...))` が正しい。

現状はlogoutエンドポイント未実装のため到達不能だが、`revoke()` を配線した時点で顕在化する。

---

### 🔵 CONFIRMED（簡略化）

#### 3. `backend/app/dependencies.py:26` — `parse_scope_header` の comprehension ガードが冗長

```python
return [scope.strip() for scope in value.split() if scope.strip()]
```

`str.split()`（引数なし）は空白区切りで分割し、空文字列を返さず、各トークンは既にstrip済みが保証される。`.strip()` と `if scope.strip()` は両方デッドコード。

```python
return value.split()  # 等価でシンプル
```

---

## 変更ファイル一覧

| ファイル                                                | 新規指摘 |
| ------------------------------------------------------- | -------- |
| `backend/app/gateway/jwt.py`                            | #1       |
| `backend/app/revocation.py`                             | #2       |
| `backend/app/dependencies.py`                           | #3       |
| `frontend/src/api/oidc.ts`                              | —        |
| `backend/app/gateway/policy.py`                         | —        |
| `backend/app/routers/admin.py`                          | —        |
| `backend/app/routers/users.py`                          | —        |
| `backend/app/services/payment_service/authorization.py` | —        |
| `backend/app/services/product_service/authorization.py` | —        |
