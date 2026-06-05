# ユニットテスト知識

## テストダブルの使い分け

テストダブルは目的に応じて使い分ける。過剰なモックはテストの信頼性を下げる。

| 種類 | 目的 | 使用場面 |
|------|------|---------|
| Stub | 固定値を返す | 外部依存の出力を制御したい |
| Mock | 呼び出しを検証する | メソッド呼び出しの有無・引数を確認したい |
| Spy | 実装を残しつつ呼び出しを記録 | 副作用の検証をしたい |
| Fake | 簡易的な実装 | インメモリDBなど軽量な代替が必要 |

### モック粒度の判断

- テスト対象の直接の依存のみモックする（間接依存はモックしない）
- 「モックが多すぎる」はテスト対象の設計の問題を示唆する
- 純粋関数は依存がないのでモック不要

```python
# NG - 内部実装をモック（振る舞いではなく実装を検証している）
with patch.object(service, "_private_method") as private_method:
    service.execute()
    private_method.assert_called_once()

# OK - 外部依存をモックし、振る舞いを検証
repository = Mock()
repository.find_by_id.return_value = user
service = UserService(repository)
result = service.get_user("id")
assert result == user
```

## 境界値分析

境界値と同値分割はユニットテストの基本手法。

| 手法 | 内容 |
|------|------|
| 同値分割 | 入力を等価なグループに分け、各グループから1つずつテスト |
| 境界値分析 | 同値クラスの境界でテスト（境界、境界±1） |

```python
# NG - 正常系のみ
def test_validates_age():
    assert validate_age(25) is True


# OK - 境界値を含む
def test_validates_age_at_boundaries():
    assert validate_age(0) is True      # 下限
    assert validate_age(-1) is False    # 下限-1
    assert validate_age(150) is True    # 上限
    assert validate_age(151) is False   # 上限+1
```

## テストフィクスチャ設計

テストデータはファクトリ関数で管理する。

- ファクトリ関数で必要最小限のフィクスチャを生成する
- テストに無関係なフィールドはデフォルト値で埋める
- 共有フィクスチャを変更して使い回さない（テスト間の独立性を保つ）

```python
# NG - 全フィールドを毎回定義
user = {
    "id": "1",
    "name": "test",
    "email": "test@example.com",
    "role": "admin",
    "created_at": datetime.now(timezone.utc),
}


# OK - ファクトリ関数で必要最小限
def create_user(**overrides):
    data = {
        "id": "test-id",
        "name": "test-user",
        "email": "test@example.com",
        "role": "user",
    }
    data.update(overrides)
    return data


def test_admin_can_delete():
    admin = create_user(role="admin")
    # テストに関係するフィールドだけ明示
```

## テスト対象の分離

テスト容易性は設計品質の指標。テストしにくいコードは依存が密結合している。

### 依存注入パターン

| パターン | 使用場面 |
|---------|---------|
| コンストラクタ注入 | クラスベースの依存分離 |
| 関数引数 | 関数の依存を引数で受け取る |
| モジュール差し替え | テスト時にモジュール全体を差し替える |

```python
# NG - 直接依存を生成（テストでモック不可）
class OrderService:
    def __init__(self):
        self.repo = OrderRepository()

    def create(self, order):
        return self.repo.save(order)


# OK - コンストラクタ注入（テストでモック可能）
class OrderService:
    def __init__(self, repo):
        self.repo = repo

    def create(self, order):
        return self.repo.save(order)
```
