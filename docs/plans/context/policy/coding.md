# コーディングポリシー

速さより丁寧さ、実装の楽さよりコードの正確さを優先する。

## 原則

| 原則 | 基準 |
|------|------|
| Simple > Easy | 書きやすさより読みやすさを優先 |
| DRY | 本質的な重複は排除する |
| コメント | Why のみ。What/How は書かない |
| 関数サイズ | 1関数1責務。30行目安 |
| ファイルサイズ | 目安として300行。タスクに応じて柔軟に |
| ボーイスカウト | 触った箇所は少し改善して去る |
| Fail Fast | エラーは早期に検出。握りつぶさない |
| プロジェクトスクリプト優先 | ツール実行はプロジェクト定義のスクリプトを使う。直接実行は最後の手段 |
| 状態の正規化 | 同じ事実を複数の状態として保持しない |

## フォールバック・デフォルト引数の禁止

値の流れを不明瞭にするコードは書かない。ロジックを追わないと値が分からないのは悪いコード。

### 禁止パターン

| パターン | 例 | 問題 |
|---------|-----|------|
| 必須データへのフォールバック | `user.id if user else "unknown"` | エラーになるべき状態で処理が進む |
| デフォルト引数の濫用 | `def f(x="default")` で全呼び出し元が省略 | 値がどこから来るか分からない |
| フォールバックで渡す口がない | `options.get("cwd") or Path.cwd()` で上位から渡す経路なし | 常にフォールバックになる（意味がない） |
| try-except で空値返却 | `except Exception: return ""` | エラーを握りつぶす |
| 不整合な値のサイレントスキップ | `if value != expected: return None` | 設定ミスが実行時に黙って無視される |

### 正しい実装

```python
# ❌ 禁止 - 必須データへのフォールバック
user_id = user.id if user else "unknown"
process_user(user_id)  # "unknown" で処理が進んでしまう

# ✅ 正しい - Fail Fast
if user is None or not user.id:
    raise ValueError("User ID is required")
process_user(user.id)

# ❌ 禁止 - デフォルト引数で全呼び出し元が省略
def load_config(path="./config.json"):
    ...
# 全呼び出し元: load_config()  ← path を渡していない

# ✅ 正しい - 必須引数にして明示的に渡す
def load_config(path: str):
    ...
# 呼び出し元: load_config("./config.json")  ← 明示的

# ❌ 禁止 - フォールバックで渡す口がない
class Engine:
    def __init__(self, config, options=None):
        self.cwd = (options or {}).get("cwd") or Path.cwd()
        # 問題: options に cwd を渡す経路がない場合、常に Path.cwd() になる

# ✅ 正しい - 上位から渡せるようにする
def create_engine(config, cwd: Path):
    return Engine(config, {"cwd": cwd})
```

### 許容されるケース

- 外部入力（ユーザー入力、API応答）のバリデーション時のデフォルト値
- 設定ファイルのオプショナル値（明示的に省略可能と設計されている）
- 一部の呼び出し元のみがデフォルト引数を使用（全員が省略している場合は禁止）

### 判断基準

1. **必須データか？** → フォールバックせず、エラーにする
2. **全呼び出し元が省略しているか？** → デフォルト引数を削除し、必須にする
3. **上位から値を渡す経路があるか？** → なければ引数・フィールドを追加
4. **関連する値に不変条件があるか？** → ロード・セットアップ時にクロスバリデーションする

## 解決責務の一元化

設定、Option、provider、パス、権限のような「早い段階で決められる値」は、境界で一度だけ解決する。同じ値を複数の層で再解決しない。

| パターン | 判定 | 理由 |
|---------|------|------|
| 入口で解決した値を下位層へ明示的に渡す | OK | 値の出所が追える |
| 解決専用のメソッド/オブジェクトに委譲する | OK | SSOTが保たれる |
| 上位と下位で同じ設定を別々に解決する | REJECT | 優先順位のズレを生む |
| ログ表示用と実行用で別々に解決する | REJECT | 表示と挙動が乖離する |
| メイン処理内で `if` を重ねて設定解決する | REJECT | オーケストレーションに詳細が漏れる |

```python
# REJECT - 各層がそれぞれ設定を解決
def execute_task(options):
    provider = options.provider or load_global_config().provider
    return run_agent({
        "provider": provider,
        "step_provider": resolve_provider_for_step(options.step),
    })


def run_agent(options):
    provider = options.get("provider") or resolve_provider_from_config()
    return get_provider(provider).call()


# OK - 境界で解決し、以降は解決済みの値だけを使う
def execute_task(options):
    resolved = resolve_execution_context(options)
    return run_agent({
        "resolved_provider": resolved.provider,
        "resolved_model": resolved.model,
    })


def run_agent(options):
    return get_provider(options["resolved_provider"]).call()
```

判断基準:
1. この値は実行前に確定できるか？ → できるなら境界で解決する
2. 同じ優先順位ロジックが2箇所以上にあるか？ → 専用メソッド/オブジェクトに集約する
3. 下位層が設定ソースそのものを知っているか？ → 解決済みの値だけを渡す
4. 表示・実行・保存で別々に解決しているか？ → 同じ解決結果を共有する

## フェーズ分離

入力の収集、解釈・正規化、実行、出力・副作用は段階で分ける。ループやメイン処理の途中で未解決の入力を受け取り直して、その場で解釈しない。

| パターン | 判定 | 理由 |
|---------|------|------|
| `RawOptions -> ResolvedOptions -> ExecutionContext` の順で段階を分ける | OK | 各段階の責務が明確 |
| ループ前に入力をまとめて正規化する | OK | 各反復が同じ前提で動く |
| ループ内で毎回 `options or config or env` を解決する | REJECT | 各反復の前提が揺れる |
| 反復ごとに入力解釈と実行ロジックが混在する | REJECT | 処理の意図が読めない |
| 1件ずつ「入力→解釈→実行→出力」を繰り返すしかない場合でも、解釈処理を専用メソッドに隔離する | OK | 最低限の責務分離を保てる |

```python
# REJECT - ループ内で毎回入力を解釈
for step in steps:
    provider = (
        options.provider
        or step.provider
        or project_config.provider
        or global_config.provider
    )
    result = execute_step(step, {"provider": provider})
    print_result(result)

# OK - 先に解決し、ループ内は実行だけ
context = resolve_execution_context(raw_options, steps)

for step in context.steps:
    result = execute_step(step, {
        "resolved_provider": step.resolved_provider,
    })
    print_result(result)
```

判断基準:
1. ループ内の分岐は「業務判断」か「入力解釈」か？ → 入力解釈ならループ外へ出す
2. 同じ入力解釈が各反復で繰り返されているか？ → 先にまとめて正規化する
3. 実行関数が raw input を直接受け取っているか？ → `Resolved*` 型へ変換してから渡す
4. 最適化で逐次処理が必要か？ → 解釈だけでも先に関数へ抽出する

## 抽象化

### 条件分岐を追加する前に考える

- 同じ条件が他にもあるか → あればパターンで抽象化
- 今後も分岐が増えそうか → Strategy/Mapパターンを使う
- 型で分岐しているか → ポリモーフィズムで置換

```python
# ❌ 条件分岐を増やす
if kind == "A":
    ...
elif kind == "B":
    ...
elif kind == "C":
    ...  # また増えた

# ✅ dictで抽象化
handlers = {"A": handle_a, "B": handle_b, "C": handle_c}
handlers[kind]()
```

### 抽象化しすぎない

抽象化は重複や変更軸を減らすだけでなく、概念に名前を与えて理解しやすくするためにも使う。ただし、数件の具体処理を「設定オブジェクト + 関数オブジェクト + ループ」に変換して、業務上の違いが読みづらくなるだけなら抽象化ではない。

| 基準 | 判定 |
|------|------|
| 少数の分岐がイベント種別・状態・業務概念ごとに異なる | `when` / `switch` で明示する |
| 同じ処理を同じ引数構造で3箇所以上繰り返す | 抽象化を検討 |
| 1箇所でしか使わない設定配列・関数オブジェクト | REJECT。まず明示分岐 |
| 設定オブジェクトを読まないと副作用や削除対象が分からない | REJECT |
| Strategy が業務概念に名前を与え、複数実装の差し替え点を明確にしている | OK |
| 分岐名がドメイン概念として読める | OK |

```python
# ❌ 過剰抽象化 - 何が起きるかを設定配列とループの両方から読む必要がある
operations = [
    {"kind": "create", "normalize": ["owner"], "remove": []},
    {"kind": "revise", "normalize": ["owner"], "remove": ["legacy_owner"]},
]
for operation in operations:
    apply_operation(record, operation)

# ✅ 分岐ごとの意味が重要なら明示する
if record.kind == "create":
    normalize_owner(record)
elif record.kind == "revise":
    remove_legacy_owner(record)
    normalize_owner(record)
```

### 抽象度を揃える

1つの関数内では同じ粒度の処理を並べる。詳細な処理は別関数に切り出す。「何をするか」と「どうやるか」を混ぜない。

```python
# ❌ 抽象度が混在
def process_order(order):
    validate_order(order)           # 高レベル
    conn = pool.get_connection()    # 低レベル詳細
    conn.execute("INSERT ...")      # 低レベル詳細

# ✅ 抽象度を揃える
def process_order(order):
    validate_order(order)
    save_order(order)  # 詳細は隠蔽
```

オーケストレーション関数（Step 1 → Step 2 → Step 3 と処理を並べる関数）では特に注意する。あるStepの内部に条件分岐が膨らんでいたら、そのStepを関数に抽出する。判定基準は分岐の数ではなく、**その分岐がその関数の抽象レベルに合っているか**。

```python
# ❌ オーケストレーション関数に詳細な分岐が露出
def execute_pipeline(options):
    task = resolve_task(options)      # Step 1: 高レベル ✅

    # Step 2: 低レベル詳細が露出 ❌
    exec_cwd = cwd
    if options.create_worktree:
        result = confirm_and_create_worktree(cwd, task, True)
        exec_cwd = result.exec_cwd
        branch = result.branch
    elif not options.skip_git:
        base_branch = get_current_branch(cwd)
        branch = generate_branch_name(config, options.issue_number)
        create_branch(cwd, branch)

    execute_task({"cwd": exec_cwd, ...})  # Step 3: 高レベル ✅

# ✅ 詳細を関数に抽出し、抽象度を揃える
def execute_pipeline(options):
    task = resolve_task(options)
    ctx = resolve_execution_context(options)
    execute_task({"cwd": ctx.exec_cwd, ...})
```

### 言語・フレームワークの作法に従う

- Pythonなら Pythonic に、KotlinならKotlinらしく
- フレームワークの推奨パターンを使う
- 独自の書き方より標準的な書き方を選ぶ
- 不明なときはリサーチする。推測で実装しない

### インターフェース設計

インターフェースは利用側の都合で設計する。実装側の内部構造を露出しない。

| 原則 | 基準 |
|------|------|
| 利用者視点 | 呼び出し側が必要としないものを押し付けない |
| 構成と実行の分離 | 「何を使うか」はセットアップ時に決定し、実行APIはシンプルに保つ |
| メソッド増殖の禁止 | 同じことをする複数メソッドは構成の違いで吸収する |

```python
# ❌ メソッド増殖 — 構成の違いを呼び出し側に押し付けている
class NotificationService:
    def send_email(self, to, subject, body): ...
    def send_sms(self, to, message): ...
    def send_push(self, to, title, body): ...
    def send_slack(self, channel, message): ...

# ✅ 構成と実行の分離
class NotificationService:
    def setup(self, config):
        return Channel(config)


class Channel:
    def send(self, message):
        ...
```

### 抽象化の漏れ

特定実装が汎用層に現れたら抽象化が漏れている。汎用層はインターフェースだけを知り、分岐は実装側で吸収する。

```python
# ❌ 汎用層に特定実装のインポートと分岐
from app.aws.s3 import upload_to_s3

if config.storage == "s3":
    return upload_to_s3(config.bucket, file, options)

# ✅ 汎用層はインターフェースのみ。非対応は生成時にエラー
storage = create_storage(config)
return storage.upload(file, options)
```

## 構造

### 分割の基準

- 独自のstateを持つ → 分離
- 50行超のUI/ロジック → 分離
- 複数の責務がある → 分離

### 機能追加時の到達経路

新しい機能や画面を追加したら、実装と同じ変更セットで利用者が到達する経路も更新する。フレームワーク固有の配線方法は各ドメイン知識に従う。

| 基準 | 判定 |
|------|------|
| 新機能の実装だけ追加し、呼び出し側・導線・到達経路の更新を忘れる | REJECT |
| 利用者がどこから到達するか未定義のまま公開機能を追加する | REJECT |
| 実装追加と同じ変更セットで導線と到達経路を更新する | OK |
| 一時導線を追加した場合、その用途と除去条件を記録する | OK |

### 依存の方向

- 上位層 → 下位層（逆方向禁止）
- データ取得はルート（View/Controller）で行い、子に渡す
- 子は親のことを知らない

### 実行条件と依存条件の一致

依存やトリガーは、実際にその処理を再実行したい条件と一致させる。静的ルールや実装都合のためだけに依存を増やし、意図しない再実行を起こさない。

| 基準 | 判定 |
|------|------|
| lint や実装都合だけで依存やトリガーを増やし、再実行ループを生む | REJECT |
| 無関係な state 変化や callback 再生成で初期処理が再実行される | REJECT |
| 再実行条件が URL・フィルタ・明示的更新操作などの仕様に対応している | OK |
| 初期化と再取得のトリガーを分けて設計している | OK |

## 契約変更の整合性

型、インターフェース、API、設定スキーマ、永続化形式、イベント、ファイル形式など、他のコードや利用者が依存する契約を変更する場合は、定義側・生成側・利用側・検証側を同じ変更で整合させる。

| 基準 | 判定 |
|------|------|
| 契約定義だけを変更し、呼び出し元・生成元・読み取り側を更新していない | REJECT |
| 新しい引数・フィールド・設定値を追加したが、利用側へ値を渡す経路がない | REJECT |
| 文書化されたスキーマや設定形式に存在しないフィールド・値を使っている | REJECT |
| モック、fixture、テストデータが実際の契約と異なる形を返している | REJECT |
| 契約変更と呼び出し元・生成元・テスト更新が同じ変更で行われている | OK |

## 状態管理

- 状態は使う場所に閉じ込める
- 子は状態を直接変更しない（イベントを親に通知）
- 状態の流れは単方向
- 正規状態から計算できる派生値を、独立した状態として保持しない
- 複数フィールド間に常時同期が必要なら、状態モデルを見直す

| 基準 | 判定 |
|------|------|
| ある状態から常に計算できる値を別の状態として保持している | REJECT |
| 複数の状態間に「常に一致すべき」不変条件がある | REJECT |
| 保存・送信・差分判定が派生値に依存している | REJECT |
| 正規状態だけを保持し、派生値は利用箇所や境界で生成している | OK |

## 未完成コード

TODO/FIXME、空実装、スタブ、コメントアウトされた旧実装を、完成した実装の代わりに残さない。今必要な処理は今実装し、不要な処理は削除する。

| 基準 | 判定 |
|------|------|
| Issue番号・外部制約・除去条件のない TODO/FIXME | REJECT |
| 認可、バリデーション、永続化、エラー処理を TODO で先送りしている | REJECT |
| 空実装、`return None`、`pass`、コメントアウトされた旧実装が残っている | REJECT |
| 外部依存や既知バグにより今は実装不能で、Issue番号と除去条件が明記されている | 許容 |
| 将来拡張のためだけの TODO | REJECT |

TDDのテスト作成フェーズでは、未実装 import や失敗テストを解消するためのプロダクションコード側スタブを追加しない。期待失敗はテスト作成レポートに記録し、実装フェーズで解消する。

## 機密情報の扱い

パスワード、トークン、APIキー、セッションID、認証ヘッダ、個人情報などの機密情報をコード、ログ、エラーレスポンス、テスト出力に露出させない。

| 基準 | 判定 |
|------|------|
| 機密情報をソースコードや設定ファイルにハードコードしている | REJECT |
| ログ、例外、エラーレスポンス、テストスナップショットに機密情報が含まれる | REJECT |
| リクエストやDTO全体をログ出力し、機密フィールドが混入しうる | REJECT |
| 機密フィールドを明示的に除外またはマスクしている | OK |
| デバッグログに個人情報が含まれるが本番では無効化される想定 | 警告。設定ミスで露出しないか確認 |

## エラーハンドリング

エラーは一元管理する。各所でtry-exceptしない。

```python
# ❌ 各所でtry-except
def create_user(data):
    try:
        user = user_service.create(data)
        return user
    except Exception as exc:
        logger.exception("ユーザー作成に失敗しました")
        raise RuntimeError("ユーザー作成に失敗しました") from exc

# ✅ 上位層で一元処理
# Controller/Handler層でまとめてキャッチ
# または FastAPI の exception handler で処理
def create_user(data):
    return user_service.create(data)  # 例外はそのまま上に投げる
```

### エラー処理の配置

| 層 | 責務 |
|----|------|
| ドメイン/サービス層 | ビジネスルール違反時に例外をスロー |
| Controller/Handler層 | 例外をキャッチしてレスポンスに変換 |
| グローバルハンドラ | 共通例外（NotFound, 認証エラー等）を処理 |

## 変換処理の配置

変換メソッドはDTO側に持たせる。

```python
# ✅ Request/Response DTOに変換メソッド
class CreateUserRequest(BaseModel):
    name: str
    email: str

    def to_use_case_input(self):
        return CreateUserInput(name=self.name, email=self.email)


# Controller
input_data = request.to_use_case_input()
output = use_case.execute(input_data)
return UserResponse.from_output(output)
```

変換の方向:
```
Request → toInput() → UseCase/Service → Output → Response.from()
```

## 共通化の判断

基本的に重複は排除する。本質的に同じロジックであり、まとめるべきと判断したら DRY にする。回数で機械的に判断しない。

### 共通化すべきもの

- 本質的に同じロジックの重複
- 同じスタイル/UIパターン
- 同じバリデーションロジック
- 同じフォーマット処理

### 共通化すべきでないもの

- ドメインが異なる重複（例: 顧客用バリデーションと管理者用バリデーションは別物）
- 表面的に似ているが変更理由が異なるコード
- 「将来使うかも」という予測に基づくもの

```python
# ❌ 過度な汎用化
def format_value(value, kind, options):
    if kind == "currency":
        ...
    elif kind == "date":
        ...
    elif kind == "percentage":
        ...

# ✅ 用途別に関数を分ける
def format_currency(amount: Decimal) -> str: ...
def format_date(value: date) -> str: ...
def format_percentage(value: Decimal) -> str: ...
```

## 同一実装の別名関数（DRY 違反）

AIは同じ処理を異なる関数名で複数定義しがちである。

| パターン | 例 | 判定 |
|---------|-----|------|
| 同一実装の別名関数 | `copyFacets()` と `placeFacetFiles()` が同じ処理 | REJECT |
| 引数シグネチャが同一で本体も同一 | 2つの関数が同じパラメータを受け取り同じ処理を行う | REJECT |

```python
# REJECT - 同じ実装が別名で存在
def copy_files(src: Path, dest: Path) -> None:
    for file in src.iterdir():
        shutil.copy2(file, dest / file.name)


def place_files(src: Path, dest: Path) -> None:
    for file in src.iterdir():
        shutil.copy2(file, dest / file.name)


# OK - 1つの関数にまとめる
def copy_files(src: Path, dest: Path) -> None:
    for file in src.iterdir():
        shutil.copy2(file, dest / file.name)
```

検証アプローチ:
1. 新規追加された関数の本体が、既存関数と同一または酷似していないか確認
2. 同じファイル内の関数同士、および同じモジュール内の関数同士を比較
3. 重複があれば1つにまとめ、呼び出し元を統一

## Stateful Regex の危険なパターン

`/g` フラグ付き正規表現はステートフル（`lastIndex` を保持する）。モジュールスコープに定義して `test()` と `replace()` を混用すると予期しない結果になる。

| パターン | 例 | 判定 |
|---------|-----|------|
| 状態を持つ正規表現オブジェクトを共有して検索位置を変える | `RE.search(s, pos)` の `pos` を共有状態で更新 | REJECT |
| 同じ正規表現オブジェクトに用途別の状態を持たせる | 検出用と置換用の状態を同じオブジェクトで管理 | REJECT |

```python
# REJECT - 検索位置を共有状態として持つ
PATTERN = re.compile(r"\{\{facet:(\w+)\}\}")
last_pos = 0

def has_facet_ref(text: str) -> bool:
    global last_pos
    match = PATTERN.search(text, last_pos)
    if match:
        last_pos = match.end()
    return match is not None

# OK - 呼び出しごとに独立して判定し、置換も副作用なしで行う
PATTERN_CHECK = re.compile(r"\{\{facet:(\w+)\}\}")
PATTERN_REPLACE = re.compile(r"\{\{facet:(\w+)\}\}")

def has_facet_ref(text: str) -> bool:
    return PATTERN_CHECK.search(text) is not None


def replace_facet_refs(text: str) -> str:
    return PATTERN_REPLACE.sub(replace_match, text)
```

検証アプローチ:
1. 正規表現の検索位置や一時状態をモジュールスコープで共有していないか確認
2. 検出と置換で用途の異なる状態を同じオブジェクトに持たせていないか確認
3. 複数呼び出しで結果が変わらないことをテストする

## 禁止事項

- **フォールバックは原則禁止** - `or "unknown"`、`.get("key", "default")`、`try-except` で握りつぶすフォールバックを書かない。エラーは上位に伝播させる。どうしても必要な場合はコメントで理由を明記する
- **説明コメント** - コードで意図を表現する。What/How のコメントは書かない
- **未使用コード** - 「念のため」のコードは書かない
- **未完成コード** - Issue番号・外部制約・除去条件のない TODO/FIXME、空実装、コメントアウト旧実装を残さない
- **型の無効化** - `Any` や過度に広い型で契約を曖昧にしない
- **オブジェクト/配列の直接変更** - 既存オブジェクトを破壊せず、新しい dict/list を返す
- **printデバッグ** - 本番コードに残さない
- **機密情報の露出** - ハードコード、ログ、エラーレスポンス、テスト出力に機密情報を含めない
- **契約文字列のハードコード散在** - ファイル名・設定キー名は定数で1箇所管理。リテラルの散在は禁止
- **各所でのtry-except** - エラーは上位層で一元処理
- **後方互換・Legacy対応の自発的追加** - 明示的な指示がない限り不要
- **内部実装のパブリック API エクスポート** - 公開するのはドメイン操作の関数・型のみ。インフラ層の関数や内部クラスをエクスポートしない
- **リファクタリング後の旧コード残存** - 置き換えたコード・エクスポートは削除する。明示的に残すよう指示されない限り残さない
- **安全機構を迂回するワークアラウンド** - 根本修正が正しいなら追加の迂回は不要
- **プロジェクトスクリプトを迂回するツール直接実行** - 直接実行は lockfile や requirements を迂回しバージョン不一致を起こす。プロジェクトが定義したスクリプト（Makefile、pytest 設定、package scripts 等）を探して使う。見つからない場合のみ直接実行を検討する
- **配線忘れ** - 新しいパラメータやフィールドを追加したら、呼び出しチェーン全体を検索して確認する。呼び出し元が値を渡していないと `options.xxx or fallback` で常にフォールバックが使われる
- **冗長な条件分岐** - if/else で同一関数を呼び出し引数の差異のみの場合、先に引数を組み立てて呼び出しを1箇所にする
- **コピペパターン** - 新しいコードを書く前に同種の既存実装を検索し、既存パターンに合わせる。独自の書き方を持ち込まない
