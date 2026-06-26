# AGENTS.md

## Project

ETF Rotation System.
Python-based daily decision support for ETF buying, waiting, and holding.
No automatic order execution. Final investment decisions are made by the user.

## Language

- チャットでは必ず日本語で応答してください。
- コミットメッセージも日本語で記述してください。

## Core Principle

The system should help prevent FOMO, panic buying, averaging down, and emotional trading.
`DEFENSE` and `WAIT` are valuable outputs.

## Token Budget Rules

- Do not explore the whole repository unless explicitly asked.
- Before editing, identify the minimum files needed for the task.
- Do not read generated or heavy folders unless the user names a specific file.
- Heavy folders: `data/`, `reports/`, `logs/`, `tmp/`, `.venv/`, `.pytest_cache/`, `raw/`.
- Prefer `docs/codex_context_map.md` for orientation instead of rereading large docs.
- For normal changes, run only relevant tests first; run the full suite only when risk is broad.

## Do Not

- Do not implement automatic trading or order execution.
- Do not change investment rules without explicit instruction.
- Do not expose, print, or commit `.env` or secrets.
- Do not rewrite unrelated files.
- Do not delete existing tests.
- Do not push directly to `main`.

## Workflow

1. Use a feature branch.
2. Make the smallest change that satisfies the task.
3. Run relevant validation.
4. Open and merge a Pull Request when ready.

## Local Commands

- Git: `C:\Program Files\Git\cmd\git.exe`
- GitHub CLI: `C:\Program Files\GitHub CLI\gh.exe`
- Python tests: `.venv\Scripts\python.exe -m pytest --basetemp .\tmp\pytest`
