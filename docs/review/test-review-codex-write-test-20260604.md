# テストレビュー: codex-write-test-20260604

**対象:** `backend/tests/` (ブランチ `codex-write-test-20260604`)
**日付:** 2026-06-04

---

## 総合判定

10件の指摘（CONFIRMED 2件 / PLAUSIBLE 8件）

---

## 指摘一覧

### 🔴 CONFIRMED（確実な問題）

#### 1. `test_models_target_contract.py:21` — UUID isinstance チェックが常に失敗する

`isinstance(id_column.type, UUID)` は必ず `False` を返す。`app/models.py` の `User.id` は `Column(Integer, ...)` であり、PostgreSQL UUID 型ではない。テストは現在のスキーマに対して実行すると AssertionError で失敗する。

```python
# test_models_target_contract.py:21
assert isinstance(id_column.type, UUID)  # User.id は Integer → 常に失敗
```

#### 2. `test_gateway_policy.py:49` — payments:write スコープの正常系テストがない

`test_payments_write_requires_scope` は拒否ケースのみを検証している。正しいスコープを持つリクエストが許可されることを確認するテストがないため、POST /api/payments を常に 403 返すバグのあるポリシーでもテストスイートはグリーンになる。

```python
# 不足しているテスト例:
# decision = policy.authorize("POST", "/api/payments", user_id="user-uuid",
#                             roles=["user"], scopes=["payments:write"])
# assert decision.allowed is True
```

---

### 🟡 PLAUSIBLE（現実的な問題）

#### 3. `test_auth_router_removed.py:3` — `app.routes` はマウントされたサブアプリのルートを見えない

`_route_exists` は `app.routes` を走査するが、`app.mount()` で追加されたルートは `Mount` オブジェクトとして格納されるため、内部のルートが見えない。レガシールーターが `include_router` ではなく `mount` で再追加された場合、テストはフォールスグリーンになる。

#### 4. `test_gateway_jwt.py:35` — `jti` クレームが欠落したトークンのテストがない

`jti` が存在しないトークンを検証した場合の動作がテストされていない。実装が `claims.get("jti")` で `None` を取得して `redis.exists("revoked:None")` を呼ぶと、失効チェックが常にパスしてしまうリボケーションバイパスが発生しうる。

#### 5. `test_dependencies_header_auth.py:50` — 未認証ユーザーが admin エンドポイントを叩くケースがない

`X-User-ID` ヘッダーなしで `/admin-only` にアクセスするケースがテストされていない。`require_admin` が `X-User-ID` の存在確認より先にロールチェックを行う実装だと、未認証リクエストが 401 ではなく例外または 200 を返す可能性がある。

#### 6. `test_token_revocation.py:30` — 既に期限切れのトークンを `revoke()` するケースがない

`expires_at <= now` の場合（TTL が 0 または負）のテストがない。Redis は `ex=0` を拒否し、負の値はクライアントエラーになる可能性があり、この場合 JTI が Redis に保存されずリプレイ攻撃を防げない。

#### 7. `conftest.py:24` — `rsa_keypair` フィクスチャが function スコープで毎テスト RSA 鍵生成

スコープ指定なし（デフォルト function スコープ）のため、`jwks` や `make_rs256_token` を使う全テストで毎回 2048-bit RSA 鍵ペアを生成する（~50–100ms/回）。`scope="session"` に変更しても正確性は変わらない。

#### 8. `conftest.py:70` — `jti` のデフォルトが `"unique-token-id"` に固定

`make_rs256_token()` を上書きなしで呼ぶと全テストが同一 JTI を持つトークンを生成する。リプレイ防止機能が実装された場合、JTI の重複により無関係なテストが非決定論的に失敗する。

#### 9. `test_services_fine_grained_auth.py:68` — 同一テスト内で正常系・異常系の両アサーションを実行

`test_payment_service_requires_payments_write_scope` は1つのテスト関数内で成功呼び出しと失敗呼び出しを連続して行う。実装がモジュールレベルの状態（監査ログ、レートリミッター等）を持つ場合、1回目の呼び出しの副作用が2回目の結果に影響する可能性がある。

#### 10. `test_token_revocation.py:44` — `repr(store)` の文字列チェックは DB 依存の有無を実証しない

`assert "RefreshToken" not in repr(store)` は文字列表現を見るだけで、実際に DB 接続なしで動作することを確認していない。`__repr__` のカスタマイズやモデル名変更でアサーションが空振りする可能性がある。

---

## 対象ファイル一覧

| ファイル | テスト数 | 主な指摘 |
|---------|---------|---------|
| `conftest.py` | - (fixtures) | #7, #8 |
| `test_audit_log.py` | 5 (parametrize) | - |
| `test_auth_router_removed.py` | 2 | #3 |
| `test_dependencies_header_auth.py` | 6 | #5 |
| `test_gateway_jwt.py` | 5 | #4 |
| `test_gateway_policy.py` | 6 | #2 |
| `test_models_target_contract.py` | 3 | #1 |
| `test_services_fine_grained_auth.py` | 9 | #9 |
| `test_token_revocation.py` | 4 | #6, #10 |
