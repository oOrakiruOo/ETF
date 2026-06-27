# Codex light task templates

Codexの使用量を抑えるため、依頼はこの形に寄せます。
毎回、全体説明ではなく必要ファイルと完了条件だけ渡します。

## ETF修正用

```text
今回の作業範囲は1点だけです。

対象ファイル:
- <file>
- <test_file>

目的:
<何を直すかを1文で書く>

制約:
- 投資ルールは変えない
- 実売買、自動発注は実装しない
- 他ファイルは変更しない
- data/, reports/, logs/, tmp/, .venv/ は読まない
- 関連テストだけ実行

Done-when:
- <期待する表示または挙動>
- 対象テストが通る
- 変更ファイルを短く報告
```

## ドキュメントだけ直す用

```text
今回の作業範囲はドキュメント1点だけです。

対象ファイル:
- <doc_file>

目的:
<説明をどう改善するか>

制約:
- コードは変更しない
- 他ファイルは変更しない
- テストは不要
- data/, reports/, logs/, tmp/, .venv/ は読まない

Done-when:
- 文章が短く、実運用で迷わない
- 変更箇所を短く報告
```

## ChatGPTからCodexへ戻す用

```text
ChatGPTで方針整理済みです。
Codexでは実装だけ行ってください。

今回の作業範囲:
<1点だけ>

対象ファイル:
- <file>
- <test_file>

実装内容:
- <変更1>
- <変更2>

変更禁止:
- 投資ルールの変更
- 自動売買
- 無関係ファイル
- data/, reports/, logs/, tmp/, .venv/ の探索

検証:
- <relevant pytest command>
```

## 副業リポジトリ用

最初の軽い雛形は以下で作れます。

```powershell
.\scripts\create_side_project_scaffold.ps1
```

別の場所に作る場合:

```powershell
.\scripts\create_side_project_scaffold.ps1 -ProjectPath D:\Codex\ai-content-factory
```

```text
新規の軽いリポジトリで作業します。
ETFシステムの文脈は使わないでください。

目的:
小さなPython CLIツールのv0.1を作る。

制約:
- mock first
- まだ外部API接続しない
- --mock で固定テキストを出力
- README, requirements.txt, .env.example を作る
- outputs/ にMarkdownを保存
- 過剰設計しない

Done-when:
- CLIが1コマンドで動く
- サンプル出力が保存される
- 次にAPI接続を差し込める形になっている
```
