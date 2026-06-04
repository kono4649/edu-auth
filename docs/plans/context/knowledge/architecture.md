# アーキテクチャ知識

## 構造・設計

**ファイル分割**

| 基準           | 判定 |
|--------------|------|
| 1ファイル200行超   | 分割を検討 |
| 1ファイル300行超   | Warning。分割を提案 |
| 1ファイルに複数の責務  | REJECT |
| 関連性の低いコードが同居 | REJECT |

行数は設計レビューや doctor で扱う警告観点であり、unit test や snapshot test の pass/fail 条件にしない。

**モジュール構成**

- 高凝集: 関連する機能がまとまっているか
- 低結合: モジュール間の依存が最小限か
- 循環依存がないか
- 適切なディレクトリ階層か

**操作の一覧性**

同じ汎用関数への呼び出しがコードベースに散在すると、システムが何をしているか把握できなくなる。操作には目的に応じた名前を付けて関数化し、関連する操作を1つのモジュールにまとめる。そのモジュールを読めば「このシステムが行う操作の全体像」がわかる状態にする。

| 判定 | 基準 |
|------|------|
| REJECT | 同じ汎用関数が目的の異なる3箇所以上から直接呼ばれている |
| REJECT | 呼び出し元を全件 grep しないとシステムの操作一覧がわからない |
| OK | 目的ごとに名前付き関数が定義され、1モジュールに集約されている |

**パブリック API の公開範囲**

パブリック API が公開するのは、ドメインの操作に対応する関数・型のみ。インフラの実装詳細（特定プロバイダーの関数、内部パーサー等）を公開しない。

| 判定 | 基準 |
|------|------|
| REJECT | インフラ層の関数がパブリック API からエクスポートされている |
| REJECT | 内部実装の関数が外部から直接呼び出し可能になっている |
| OK | 外部消費者がドメインレベルの抽象のみを通じて対話する |

**関数設計**

- 1関数1責務になっているか
- 30行を超える関数は分割を検討
- 副作用が明確か

**レイヤー設計**

- 依存の方向: 上位層 → 下位層（逆方向禁止）
- Controller → Service → Repository の流れが守られているか
- 1インターフェース = 1責務（巨大なServiceクラス禁止）

**ディレクトリ構造**

構造パターンの選択:

| パターン | 適用場面 | 例 |
|---------|---------|-----|
| レイヤード | 小規模、CRUD中心 | `controllers/`, `services/`, `repositories/` |
| Vertical Slice | 中〜大規模、機能独立性が高い | `features/auth/`, `features/order/` |
| ハイブリッド | 共通基盤 + 機能モジュール | `core/` + `features/` |

Vertical Slice Architecture（機能単位でコードをまとめる構造）:

```
backend/app/
├── features/
│   ├── auth/
│   │   ├── commands.py
│   │   ├── handlers.py
│   │   ├── repository.py
│   │   └── test_auth.py
│   └── order/
│       ├── commands.py
│       ├── handlers.py
│       └── ...
└── shared/           # 複数featureで共有
    ├── database/
    └── middleware/
```

Vertical Slice の判定基準:

| 基準 | 判定 |
|------|------|
| 1機能が3ファイル以上のレイヤーに跨る | Slice化を検討 |
| 機能間の依存がほぼない | Slice化推奨 |
| 共通処理が50%以上 | レイヤード維持 |
| チームが機能別に分かれている | Slice化必須 |

禁止パターン:

| パターン | 問題 |
|---------|------|
| `utils/` の肥大化 | 責務不明の墓場になる |
| `common/` への安易な配置 | 依存関係が不明確になる |
| 深すぎるネスト（4階層超） | ナビゲーション困難 |
| 機能とレイヤーの混在 | `features/services/` は禁止 |

**責務の分離**

- 読み取りと書き込みの責務が分かれているか
- データ取得はルート（View/Controller）で行い、子に渡しているか
- エラーハンドリングが一元化されているか（各所でtry-except禁止）
- ビジネスロジックがController/Viewに漏れていないか

## 境界での解決

設定、Option、provider、権限、パスのような値は、境界で解決してから内部へ渡す。メイン処理は「何が解決済みか」を前提に組み立て、各所で設定ソースを問い合わせない。

| 基準 | 判定 |
|------|------|
| 入口で `ExecutionContext` や `ResolvedOptions` のような解決済みオブジェクトを作る | OK |
| オーケストレーション層が解決済みの値だけを扱う | OK |
| 下位層が global/project/env を再読込して同じ値を再解決する | REJECT |
| 表示用と実行用で別々の解決関数を持つ | REJECT |
| 未解決の options を深い層まで運び、先で `or fallback` 解決する | REJECT |

```python
# REJECT - 実行層が設定ソースを直接知っている
def execute_workflow(options):
    engine = WorkflowEngine({
        "provider": options.provider or global_config.provider,
    })


class AgentRunner:
    def run(self, step, options):
        provider = options.provider or resolve_provider_from_config()
        return get_provider(provider).call()


# OK - 境界で解決し、内部は解決済み値を使う
def execute_workflow(options):
    context = resolve_execution_context(options)
    engine = WorkflowEngine(context)


class AgentRunner:
    def run(self, step, options):
        return get_provider(options.resolved_provider).call()
```

### Tell, Don't Ask

下位層に設定ソースを問い合わせさせるのではなく、上位層が「これを使え」と解決済みの値を渡す。値の選択責務と実行責務を分離する。

| パターン | 判定 |
|---------|------|
| 上位層が `resolvedProvider` のような値を渡す | OK |
| 下位層が `options` を覗いて自前で解決する | REJECT |
| 実行オブジェクトが `setup(config)` 後は `run()` だけ公開する | OK |
| 実行中に `getGlobalConfig()` を呼んで分岐する | REJECT |

### 腐敗防止層

優先順位解決や外部設定形式の吸収は、境界の専用層に閉じ込める。内部モデルへは正規化済みの値だけを渡す。

| パターン | 判定 |
|---------|------|
| YAML/env/CLI 差分を resolver/adapter に閉じ込める | OK |
| ドメイン層が env 名や設定キー文字列を直接扱う | REJECT |
| 外部形式から内部形式への変換が1箇所に集約されている | OK |
| 同じ正規化ロジックが複数箇所にコピーされている | REJECT |

### フェーズ分離

入力、解釈、実行、出力を段階で分ける。反復処理は、できる限り「解釈済みの入力をまとめて受け取り、実行だけを繰り返す」構造にする。

| 基準 | 判定 |
|------|------|
| 入口で raw input を `Resolved*` 型へ変換してから本処理に渡す | OK |
| ループ本体が解決済みデータに対する実行だけを担う | OK |
| ループ内で毎回 config/env/option を解釈する | REJECT |
| 反復ごとに「入力取得→解釈→実行→出力」を1関数に詰め込む | REJECT |
| 最適化で逐次処理が必要でも、解釈フェーズを専用メソッドに隔離している | OK |

```python
# REJECT - 各反復が入力解釈まで担う
for item in items:
    resolved = resolve_item(item, raw_options, config)
    result = execute(resolved)
    output(result)

# OK - 先に解釈し、反復は実行だけ
resolved_items = [
    resolve_item(item, raw_options, config)
    for item in items
]

for item in resolved_items:
    result = execute(item)
    output(result)
```

逐次解釈が必要なケースでも、`nextRawInput()` と `resolveInput()` と `executeResolved()` の責務は分ける。性能要件でフェーズを近づけても、責務まで混ぜない。

## コード品質の検出手法

**説明コメント（What/How）の検出基準**

コードの動作をそのまま言い換えているコメントを検出する。

| 判定 | 基準 |
|------|------|
| REJECT | コードの動作をそのまま自然言語で言い換えている |
| REJECT | 関数名・変数名から明らかなことを繰り返している |
| REJECT | docstring が関数名の言い換えだけで情報を追加していない |
| OK | なぜその実装を選んだかの設計判断を説明している |
| OK | 一見不自然に見える挙動の理由を説明している |
| 最良 | コメントなしでコード自体が意図を語っている |

```python
# REJECT - コードの言い換え（What）
# If interrupted, abort immediately
if status == "interrupted":
    return ABORT_STEP

# REJECT - ループの存在を言い換えただけ
# Check transitions in order
for transition in step.transitions:
    ...

# REJECT - 関数名の繰り返し
def matches_condition(status, condition):
    """Check if status matches transition condition."""
    ...

# OK - 設計判断の理由（Why）
# ユーザー中断はワークフロー定義のトランジションより優先する
if status == "interrupted":
    return ABORT_STEP

# OK - 一見不自然な挙動の理由
# stay はループを引き起こす可能性があるが、ユーザーが明示的に指定した場合のみ使われる
return step.name
```

**状態の直接変更の検出基準**

配列やオブジェクトの直接変更（ミューテーション）を検出する。

```python
# REJECT - 配列の直接変更
steps = get_steps()
steps.append(new_step)              # 元の配列を破壊
del steps[index]                    # 元の配列を破壊
steps[0]["status"] = "done"         # ネストされたオブジェクトも直接変更

# OK - 新しいリストを返す
with_new = [*steps, new_step]
without = [step for i, step in enumerate(steps) if i != index]
updated = [
    {**step, "status": "done"} if i == 0 else step
    for i, step in enumerate(steps)
]

# REJECT - オブジェクトの直接変更
def update_config(config):
    config["log_level"] = "debug"       # 引数を直接変更
    config["steps"].append(new_step)    # ネストも直接変更
    return config

# OK - 新しいオブジェクトを返す
def update_config(config):
    return {
        **config,
        "log_level": "debug",
        "steps": [*config["steps"], new_step],
    }
```

## セキュリティ（基本チェック）

- インジェクション対策（SQL, コマンド, XSS）
- ユーザー入力の検証
- 機密情報のハードコーディング

## テスタビリティ

- 依存性注入が可能な設計か
- モック可能か
- テストが書かれているか

## アンチパターン検出

以下のパターンを見つけたら REJECT:

| アンチパターン | 問題 |
|---------------|------|
| God Class/Component | 1つのクラスが多くの責務を持っている |
| Feature Envy | 他モジュールのデータを頻繁に参照している |
| Shotgun Surgery | 1つの変更が複数ファイルに波及する構造 |
| 過度な汎用化 | 今使わないバリアントや拡張ポイント |
| 隠れた依存 | 子コンポーネントが暗黙的にAPIを呼ぶ等 |
| 非イディオマティック | 言語・FWの作法を無視した独自実装 |

## 抽象化レベルの評価

**条件分岐の肥大化検出**

| パターン | 判定 |
|---------|------|
| 同じif-elseパターンが3箇所以上 | ポリモーフィズムで抽象化 → REJECT |
| switch/caseが5分岐以上 | Strategy/Mapパターンを検討 |
| フラグ引数で挙動を変える | 別関数に分割 → REJECT |
| 型による分岐（instanceof/typeof） | ポリモーフィズムに置換 → REJECT |
| ネストした条件分岐（3段以上） | 早期リターンまたは抽出 → REJECT |

**抽象度の不一致検出**

| パターン | 問題 | 修正案 |
|---------|------|--------|
| 高レベル処理の中に低レベル詳細 | 読みにくい | 詳細を関数に抽出 |
| 1関数内で抽象度が混在 | 認知負荷 | 同じ粒度に揃える |
| ビジネスロジックにDB操作が混在 | 責務違反 | Repository層に分離 |
| 設定値と処理ロジックが混在 | 変更困難 | 設定を外部化 |

**良い抽象化の例**

```python
# 条件分岐の肥大化
def process(kind: str):
    if kind == "A":
        process_a()
    elif kind == "B":
        process_b()
    elif kind == "C":
        process_c()
    # ...続く

# dictパターンで抽象化
processors = {
    "A": process_a,
    "B": process_b,
    "C": process_c,
}

def process(kind: str):
    processors[kind]()
```

```python
# 抽象度の混在
def create_user(data):
    # 高レベル: ビジネスロジック
    validate_user(data)
    # 低レベル: DB操作の詳細
    conn = pool.get_connection()
    conn.execute("INSERT INTO users ...")
    conn.close()

# 抽象度を揃える
def create_user(data):
    validate_user(data)
    user_repository.save(data)  # 詳細は隠蔽
```

## その場しのぎの検出

「とりあえず動かす」ための妥協を見逃さない。

| パターン | 例 |
|---------|-----|
| 不要なパッケージ追加 | 動かすためだけに入れた謎のライブラリ |
| テストの削除・スキップ | `@Disabled`、`.skip()`、コメントアウト |
| 空実装・スタブ放置 | `return None`、`# TODO: implement`、`pass` |
| モックデータの本番混入 | ハードコードされたダミーデータ |
| エラー握りつぶし | 空の `catch {}`、`rescue nil` |
| マジックナンバー | 説明なしの `if (status == 3)` |

## 未完成コードの検出

未完成コードの判定基準はコーディングポリシーに従う。アーキテクチャレビューでは、TODO/FIXME、空実装、スタブが設計上必要な境界・認可・バリデーション・契約更新の代替になっていないかを見る。

Issue番号・外部制約・除去条件のない TODO/FIXME は REJECT。

```python
# REJECT - 認可チェックをTODOで先送り
# TODO: 施設IDによる認可チェックを追加
def delete_custom_holiday(holiday_id: str):
    delete_custom_holiday_input_port.execute(input_data)

# APPROVE - 今実装する
def delete_custom_holiday(holiday_id: str):
    current_user_facility_id = get_current_user_facility_id()
    holiday = find_holiday_by_id(holiday_id)
    if holiday.facility_id != current_user_facility_id:
        raise PermissionError("Cannot delete holiday from another facility")
    delete_custom_holiday_input_port.execute(input_data)
```

TODO/FIXMEが許容されるケース:

| 条件 | 例 | 判定 |
|------|-----|------|
| 外部依存で今は実装不可 + Issue化済み + 除去条件あり | `// TODO(#123): APIキー取得後に実装` | 許容 |
| 技術的制約で回避不可 + Issue化済み + 除去条件あり | `// TODO(#456): ライブラリバグ修正待ち` | 許容 |
| 「将来実装」「後で追加」 | `// TODO: バリデーション追加` | REJECT |
| 「時間がないので」 | `// TODO: リファクタリング` | REJECT |

正しい対処:
- 今必要 → 今実装する
- 今不要 → コードを削除する
- 外部要因で不可 → Issue化してチケット番号をコメントに入れる

## DRY違反の検出

基本的に重複は排除する。本質的に同じロジックであり、まとめるべきと判断したら DRY にする。回数で機械的に判断しない。

| パターン | 判定 |
|---------|------|
| 本質的に同じロジックの重複 | REJECT - 関数/メソッドに抽出 |
| 同じバリデーションの重複 | REJECT - バリデーター関数に抽出 |
| 本質的に同じ構造のコンポーネント | REJECT - 共通コンポーネント化 |
| コピペで派生したコード | REJECT - パラメータ化または抽象化 |

DRY にしないケース:
- ドメインが異なる重複は抽象化しない（例: 顧客用バリデーションと管理者用バリデーションは別物）
- 表面的に似ているが、変更理由が異なるコードは別物として扱う

## 仕様準拠の検証

契約変更の整合性はコーディングポリシーに従う。アーキテクチャレビューでは、変更が文書化された仕様、型、スキーマ、設定形式と矛盾していないかを見る。

検証対象:

| 対象 | 確認内容 |
|------|---------|
| CLAUDE.md / README.md | スキーマ定義、設計原則、制約に従っているか |
| 型定義・Pydanticスキーマ | 新しいフィールドがスキーマに反映されているか |
| YAML/JSON設定ファイル | 文書化されたフォーマットに従っているか |

具体的なチェック:

1. 設定ファイル（YAML等）を変更・追加した場合:
   - CLAUDE.md等に記載されたスキーマ定義と突合する
   - 無視されるフィールドや無効なフィールドが含まれていないか
   - 必須フィールドが欠落していないか

2. 型定義やインターフェースを変更した場合:
   - ドキュメントのスキーマ説明が更新されているか
   - 既存の設定ファイルが新しいスキーマと整合するか

このパターンを見つけたら REJECT:

| パターン | 問題 |
|---------|------|
| 仕様に存在しないフィールドの使用 | 無視されるか予期しない動作 |
| 仕様上無効な値の設定 | 実行時エラーまたは無視される |
| 文書化された制約への違反 | 設計意図に反する |

## 呼び出しチェーン検証

契約変更の配線漏れはコーディングポリシーに従う。アーキテクチャレビューでは、新しいパラメータ・フィールドが変更ファイル内だけで完結しておらず、実際の呼び出し元・生成元・読み取り側まで届いているかを見る。

検証手順:
1. 新しいオプショナルパラメータやスキーマフィールドを見つけたら、全呼び出し元を検索
2. 全呼び出し元が新しいパラメータを渡しているか確認
3. フォールバック値（`or default`、`.get(..., default)`）がある場合、フォールバックが使われるケースが意図通りか確認

危険パターン:

| パターン | 問題 | 検出方法 |
|---------|------|---------|
| `options.xxx or fallback` で全呼び出し元が `xxx` を省略 | 機能が実装されているのに常にフォールバック | 呼び出し元を確認 |
| テストがモックで直接値をセット | 実際の呼び出しチェーンを経由しない | テストの構築方法を確認 |
| `executeXxx()` が内部で使う `options` を引数で受け取らない | 上位から値を渡す口がない | 関数シグネチャを確認 |

```python
# 配線漏れ: project_cwd を受け取る口がない
def execute_workflow(config, cwd, task):
    engine = WorkflowEngine(config, cwd, task)  # options なし

# 配線済み: project_cwd を渡せる
def execute_workflow(config, cwd, task, options=None):
    engine = WorkflowEngine(config, cwd, task, options)
```

呼び出し元の制約による論理的デッドコード:

呼び出しチェーンの検証は「配線漏れ」だけでなく、逆方向——呼び出し元が既に保証している条件に対する不要な防御コード——にも適用する。

| パターン | 問題 | 検出方法 |
|---------|------|---------|
| 呼び出し元がTTY必須なのに関数内でTTYチェック | 到達しない分岐が残る | 全呼び出し元の前提条件を確認 |
| 呼び出し元がnullチェック済みなのに再度nullガード | 冗長な防御 | 呼び出し元の制約を追跡 |
| 呼び出し元がスキーマや型で制約しているのにランタイムチェック | 入力契約を信頼していない | Pydantic モデルや型制約を確認 |

検証手順:
1. 防御的な条件分岐（TTYチェック、nullガード等）を見つけたら、全呼び出し元を確認
2. 全呼び出し元がその条件を既に保証しているなら、防御は不要 → REJECT
3. 一部の呼び出し元が保証していない場合は、防御を残す

## 品質特性

| 特性 | 確認観点 |
|------|---------|
| Scalability | 負荷増加に対応できる設計か |
| Maintainability | 変更・修正が容易か |
| Observability | ログ・監視が可能な設計か |

## 大局観

細かい「クリーンコード」の指摘に終始しない。

確認すべきこと:
- このコードは将来どう変化するか
- スケーリングの必要性は考慮されているか
- 技術的負債を生んでいないか
- ビジネス要件と整合しているか
- 命名がドメインと一貫しているか

## 変更スコープの評価

変更スコープを確認し、レポートに記載する（ブロッキングではない）。

| スコープサイズ | 変更行数 | 対応 |
|---------------|---------|------|
| Small | 〜200行 | そのままレビュー |
| Medium | 200-500行 | そのままレビュー |
| Large | 500行以上 | レビューは継続。分割可能か提案を付記 |

大きな変更が必要なタスクもある。行数だけでREJECTしない。

確認すること:
- 変更が論理的にまとまっているか（無関係な変更が混在していないか）
- Coderのスコープ宣言と実際の変更が一致しているか

提案として記載すること（ブロッキングではない）:
- 分割可能な場合は分割案を提示
