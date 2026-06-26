# Codex token budget

ETFシステムでCodex使用量を増やしすぎないための運用ルールです。
機能は削らず、Codexに読ませる範囲だけを絞ります。

## 基本方針

1. ETFシステムと副業開発は別リポジトリで扱う
2. ETF側では1回1タスクに絞る
3. 指定ファイル制を基本にする
4. 生成物フォルダは必要な時だけ読む
5. 詳細設計は必要時だけ参照する

## 読まないフォルダ

通常作業では以下を読まない。

- `data/`
- `reports/`
- `logs/`
- `tmp/`
- `.venv/`
- `.pytest_cache/`
- `raw/`

必要な場合は、フォルダ全体ではなく対象ファイルだけ指定する。

## ETFシステムでCodexに投げる形

```text
今回の作業範囲は1点だけ。

対象ファイル:
- src/report_engine.py
- tests/test_report_engine.py

目的:
LINE判断ブリーフのDEFENSE文言だけを改善する。

制約:
- 投資ルールは変えない
- 他ファイルは変更しない
- data/reports/logs/tmp は読まない
- 関連テストだけ実行

Done-when:
- 対象テストが通る
- 変更ファイルを短く報告
```

## 副業開発でCodexに投げる形

ETFリポジトリではなく、別リポジトリで始める。

```text
新規の小さなPython CLIツールを作る。

重要:
- まだ外部API接続はしない
- --mock で固定テキストを出力する
- 変更は最小限
- README、requirements.txt、.env.example だけ用意
```

## 運用リズム

- ETF修正: 週1から2回、必要な時だけ
- 副業開発: 別リポジトリで軽く進める
- ETFの長い相談: `docs/chatgpt_handoff_prompt.md` を使ってChatGPT側へ逃がす
- Codexへ戻す時: 1ファイルから数ファイルの実装タスクに分解する

## 判断

ETFシステムは本運用観察フェーズに入っているため、今後は新機能追加よりも以下を優先する。

1. 日次LINEが届くか
2. 週次PDCAが届くか
3. 自己確認ログが週次PDCAに反映されるか
4. 実際に買い急ぎを止められたか
