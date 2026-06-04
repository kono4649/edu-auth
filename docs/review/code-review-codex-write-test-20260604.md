# コードレビュー: codex-write-test-20260604

**対象:** `docs/plans/context/` 配下（ブランチ `codex-write-test-20260604`）
**日付:** 2026-06-04
**注記:** テストディレクトリを除く全変更ファイルはすべてMarkdownドキュメント

---

## 総合判定

10件の指摘（CONFIRMED 4件 / PLAUSIBLE 6件）

---

## 対応結果

**対応日:** 2026-06-04
**ステータス:** 全10件対応済み

| # | 状態 | 対応内容 |
|---|------|----------|
| 1 | 対応済み | `write-code.md` の参照を `./instruction/implement.md` に修正 |
| 2 | 対応済み | `write-code.md` に `./instruction/write-tests-first.md` を登録 |
| 3 | 対応済み | `write-code.md` に `./output_contracts/test-report.md` を登録し、TDDフェーズの必須出力として参照 |
| 4 | 対応済み | `implement.md` のインライン出力契約テンプレートを削除し、`coder-scope.md` / `coder-decisions.md` 参照へ一本化 |
| 5 | 対応済み | `implement.md` にTDDフェーズからの失敗テスト・未実装 import エラーの引き継ぎルールを追加 |
| 6 | 対応済み | `coder.md` に、指摘がセキュリティ・データ破壊・要件違反を招く場合は停止して判断を仰ぐ優先ルールを追加 |
| 7 | 対応済み | `write-tests-first.md` と `coding.md` に、TDDフェーズではプロダクションコード側スタブを追加しないことを明記 |
| 8 | 対応済み | `unit-testing.md`、`testing.md`、`coding.md`、`architecture.md`、`e2e-testing.md` のTypeScript/Kotlin寄りコード例をPython/FastAPI向けに置換 |
| 9 | 対応済み | `coder.md` の削除禁止ルールを「タスク内でリファクタリングして置き換えたコード」に限定し、タスク外機能削除との境界を明確化 |
| 10 | 対応済み | `implement.md` と `testing.md` にPython向け静的検証として `python -m compileall backend/app backend/tests`、テストとして `pytest` を明記 |

**追加調整:**
- `output_contracts/coder-scope.md` のサンプルパスを `backend/app/*.py` 形式へ更新
- マニフェスト経由で読まれるナレッジ文書内のTS/JS固有表現（`vi.fn()`、`Partial<T>`、`??`、`.ts` 例など）をPython表現へ統一

**検証:**
- `write-code.md` の相対参照先がすべて実在することを確認
- TS/JS/Kotlin固有パターンの残存検索を実施
- `git diff --check` 通過

---

## 指摘一覧

### 🔴 CONFIRMED（確実な問題）

#### 1. `write-code.md:18` — マニフェストのパス参照が壊れており実装指示書がロードされない

`# 指示` セクションが `./instructions/implement.md`（複数形）を参照しているが、実際のディレクトリ名は `instruction/`（単数形）。ファイルパスが一致しないため、実装指示書は一切ロードされない。

```
# 指示
./instructions/implement.md   ← ❌ ディレクトリ名が間違い
```

実際のパス: `./instruction/implement.md`

**影響:** ビルド/テストゲート、自己チェックリスト、出力契約がすべてロードされないままエージェントが動作する。

---

#### 2. `write-code.md` — `write-tests-first.md` がマニフェストに未登録でTDDフェーズが到達不能

`instruction/write-tests-first.md`（TDD事前テスト作成指示）が `write-code.md` に記載されていない。TDDフェーズを使うマニフェストが存在しないため、このファイルはどのエージェントにもロードされない。

**影響:** TDD設計が意図された場合でも、エージェントはテストファーストをスキップして直接プロダクションコードを書く。

---

#### 3. `write-code.md` — `test-report.md` がマニフェストに未登録で出力契約が無効

`output_contracts/test-report.md`（テスト作成レポートのフォーマット契約）が `write-code.md` に記載されていない。`write-tests-first.md` の出力フォーマットを定義するファイルだが、いかなるマニフェストからも参照されていない。

**影響:** TDDフェーズの出力が非構造化になり、後続の検証が機能しない。

---

#### 4. `instruction/implement.md:13` — 出力契約テンプレートが `output_contracts/` と二重定義

Scope と Decisions のテンプレートが `implement.md` 内にインラインで定義され、かつ `output_contracts/coder-scope.md` と `output_contracts/coder-decisions.md` にも同一内容で存在する。プロジェクト自身の `coding.md` が定めるDRY原則に違反している。

**影響:** 一方を更新して他方を更新し忘れると、エージェントが古いテンプレートに従って互換性のない出力を生成する。

---

### 🟡 PLAUSIBLE（現実的な問題）

#### 5. `write-tests-first.md:33` vs `implement.md:10` — TDDフェーズと実装フェーズでテスト結果の期待値が矛盾

`write-tests-first.md` はテスト失敗を「想定内」と明示している。一方、`implement.md` + `testing.md` はビルド失敗を REJECT と定義している。2フェーズ間の引き継ぎシグナルが定義されていない。

| フェーズ | ドキュメント | テスト失敗の扱い |
|---------|------------|----------------|
| TDDフェーズ | `write-tests-first.md` | 想定内（OK） |
| 実装フェーズ | `implement.md` + `testing.md` | REJECT |

**影響:** `implement.md` 適用時に既存の失敗テスト（TDD由来）をREJECT条件と誤解し、テストを削除してスイートをグリーンにしようとする可能性がある。

---

#### 6. `persona/coder.md:29` — 「反論せず従え」と「不明点は報告せよ」が矛盾、優先ルールなし

`coder.md` は次の2つの矛盾する指示を持つ:
- **絶対従順:** 「レビュワーの指摘は絶対。あなたの認識が間違っている。反論せず、まず従う」
- **報告義務:** 「要件の解釈（不明点は報告する）」

優先ルールが定義されていないため、レビュワーの指摘が誤り（またはセキュリティ上危険）な場合の判断が不定になる。

**影響:** 「トークン有効期限チェックを削除せよ」という誤った指摘に対し、絶対従順ルールがセキュリティガードの削除を引き起こす可能性がある。

---

#### 7. `policy/coding.md:385` — スタブ禁止ポリシーとTDDフェーズが衝突

`coding.md` の「空実装・スタブ放置 → 禁止」ルールは、`write-tests-first.md` のTDDフェーズと衝突する。TDDフェーズでは未実装モジュールへのインポートを含むテストファイルを作成することが前提だが、スタブ禁止ルールを適用するとエージェントがプロダクションコードを書いてフェーズ境界を崩す可能性がある。

**影響:** `write-tests-first.md` の「プロダクションコードは作成・変更しないでください」制約が無効化される。

---

#### 8. `knowledge/unit-testing.md` 他 — 全コード例がTypeScriptだがプロジェクトはPython

`unit-testing.md`、`testing.md`、`coding.md` のコード例はすべて TypeScript（`vi.fn()`、`vi.spyOn()`、`Partial<T>`、型アノテーション等）を使用している。プロジェクトのバックエンドは Python/FastAPI（pytest、conftest.py、jose 等）であり、TypeScript のパターンは適用できない。

**影響:** バックエンドのPythonコードに `vi.fn()` モックや `Partial<User>` ファクトリが生成され、ビルドが失敗する。あるいはエージェントが誤ったパターンに誘導される。

---

#### 9. `persona/coder.md:38` — 「既存機能を削除するな」と「置き換えたコードを削除せよ」が矛盾

`coder.md` と `coding.md` に相反するルールが存在する:

| ドキュメント | ルール |
|------------|-------|
| `coder.md:38` | タスク指示書にない既存機能の削除 → 禁止 |
| `coding.md` | リファクタリングで置き換えたコードは削除 → 必須（残すよう指示されない限り） |

適用シナリオが異なるが（タスク外機能 vs タスク内で置き換えたコード）、境界が明示されていない。

**影響:** タスク内でリファクタリングした既存機能を削除する際に2つのルールが衝突し、エージェントが誤って削除する・または削除しないという不定動作を招く。

---

#### 10. `instruction/implement.md:9` — 「ビルド（型チェック）必須」だがPythonでの実行コマンドが未定義

「ビルド確認は必須。実装完了後、ビルド（型チェック）を実行し、型エラーがないことを確認」という指示はTypeScriptのビルドステップを想定した記述になっているが、Pythonプロジェクトに対応するコマンド（mypy、ruff、pyright等）が定義されていない。

**影響:** Pythonコードを実装したエージェントが「ビルド」の実行方法を知らずにステップをスキップするか、TypeScript向けのコマンド（tsc等）を実行して誤った結果を報告する。

---

## 変更ファイル一覧

| ファイル | 主な指摘 |
|---------|---------|
| `write-code.md` | #1, #2, #3 |
| `instruction/implement.md` | #4, #10 |
| `instruction/write-tests-first.md` | #5, #7 |
| `persona/coder.md` | #6, #9 |
| `policy/coding.md` | #7, #9 |
| `knowledge/unit-testing.md` | #8 |
| `policy/testing.md` | #8 |
| `output_contracts/test-report.md` | #3 |
