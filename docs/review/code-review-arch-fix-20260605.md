# Code Review: arch-review-fix (2026-06-05)

**対象:** `git diff HEAD~1` — アーキテクチャレビュー指摘対応コミット  
**日時:** 2026-06-05  
**判定:** 本番コードにバグなし。テストコードに低〜中優先度の指摘7件。

---

## サマリー

本番コード側の変更（定数化・共有関数への統一・不要クラス削除）はいずれも等価リファクタリングであり、機能的バグは検出されなかった。`parse_gateway_user_uuid` は削除された `_parse_user_uuid` と実装が完全一致することを確認。

新規追加の `test_arch_review_fix_contract.py` に、テストの信頼性・完全性に関わる指摘が集中している。

---

## Findings

### 🟡 F1 — `parse_scope_header` のコンマ区切りスコープ拒否テストが削除された

| 項目 | 内容 |
|------|------|
| **ファイル** | `backend/app/dependencies.py`, line 23 |
| **優先度** | MEDIUM |

`parse_scope_header` は `.split()`（空白区切り）を使用している。`test_payment_service_rejects_comma_separated_scope_header` はコンマ区切り `"openid,payments:write"` を送ると `payments:write` が単一トークンとして解釈され認可が拒否されることを確認する唯一のガードだったが、今回の削除で失われた。

`parse_scope_header` は `dependencies.py` に残存しており、将来のルートに接続されると同動作になる。

**再現手順:** `X-Scope: openid,payments:write` → `parse_scope_header` → `["openid,payments:write"]`（単一トークン）→ `"payments:write" not in scopes` → HTTP 403

---

### 🟡 F2 — `next()` にデフォルト値がなく `RuntimeError` になる

| 項目 | 内容 |
|------|------|
| **ファイル** | `backend/tests/test_arch_review_fix_contract.py`, line 137 |
| **優先度** | LOW-MEDIUM |

```python
gateway_policy_class = next(
    node
    for node in tree.body
    if isinstance(node, ast.ClassDef) and node.name == "GatewayPolicy"
)
```

`GatewayPolicy` がリネームされた場合、Python 3.7+ では `StopIteration` が `RuntimeError: generator raised StopIteration` に変換される。pytest は ERROR として報告し、何のコントラクトが壊れたか分からない。

**修正案:** `next(..., None)` + `assert gateway_policy_class is not None, "GatewayPolicy not found"`

---

### 🟡 F3 — `ast.FunctionDef` チェックが `async def` を見逃す

| 項目 | 内容 |
|------|------|
| **ファイル** | `backend/tests/test_arch_review_fix_contract.py`, line 26 |
| **優先度** | LOW |

```python
function_names = {
    node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
}
assert "_parse_user_uuid" not in function_names
```

`ast.AsyncFunctionDef` は `ast.FunctionDef` の派生ではないため、`async def _parse_user_uuid` を再導入しても検出されない。FastAPI では async ルートが標準的なパターン。

**修正案:** `isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))`

---

### 🟡 F4 — `PAYMENT_WRITE_METHODS` が可変 `set`

| 項目 | 内容 |
|------|------|
| **ファイル** | `backend/app/gateway/policy.py`, line 14 |
| **優先度** | LOW |

```python
PAYMENT_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
```

モジュールレベル定数として `frozenset` が適切。テストセットアップや monkey-patch で `.add()` / `.clear()` されると同プロセス内の全リクエストに影響する。

**修正案:** `PAYMENT_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})`

---

### 🟡 F5 — forbidden-import スキャンがテストファイル自身しか除外しない

| 項目 | 内容 |
|------|------|
| **ファイル** | `backend/tests/test_arch_review_fix_contract.py`, line 56 |
| **優先度** | LOW |

```python
if path == Path(__file__).resolve():
    continue
```

将来 `app.audit` の非存在を `ModuleNotFoundError` で確認するテストを書くと、そのファイルが offender として誤検知される。

**修正案:** tests/ ディレクトリ全体を除外する
`if path.is_relative_to(BACKEND_ROOT / "tests"): continue`

---

### 🟡 F6 — `from app import audit` スタイルが forbidden-import チェックを通過する

| 項目 | 内容 |
|------|------|
| **ファイル** | `backend/tests/test_arch_review_fix_contract.py`, line 60 |
| **優先度** | LOW |

`from app import audit` の場合 `node.module == "app"`（`forbidden_imports` に含まれない）のためスルーされる。

---

### 🟡 F7 — `test_gateway_policy_api_paths_are_defined_as_module_constants` が `_module_ast` を再実装している

| 項目 | 内容 |
|------|------|
| **ファイル** | `backend/tests/test_arch_review_fix_contract.py`, line 119 |
| **優先度** | LOW |

```python
policy_path = BACKEND_ROOT / "app/gateway/policy.py"
tree = ast.parse(policy_path.read_text(), filename=str(policy_path))
```

モジュール定義済みの `_module_ast("app/gateway/policy.py")` と同等のコードを再実装している。`_module_ast` に変更（エンコーディング指定、エラーコンテキスト等）が加わった場合にここだけ取り残される。

---

## 確認済み・問題なし

| 項目 | 結果 |
|------|------|
| `parse_gateway_user_uuid` vs 削除された `_parse_user_uuid` | **完全一致**（`uuid.UUID(user_id)` + ValueError → 401） |
| 削除スキーマクラスへの stale import | **なし**（テストファイル内の文字列のみ） |
| `app.audit` / `app.revocation` への残存 import | **なし** |
| トークン失効の不在 | **設計通り**（Gateway 責務・README に明記） |
| `transport.py` の残存 | **意図的**（mTLS transport 検証、authorization モジュールとは別物） |
