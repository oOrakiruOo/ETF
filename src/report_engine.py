from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .utils import PROJECT_ROOT, ensure_dir


DISPLAY_COLUMNS = [
    "ETF",
    "テーマ",
    "ETFスコア",
    "テーマスコア",
    "テーマリスク",
    "テーマリスクスコア",
    "ステージ",
    "現在価格",
    "第1買い",
    "第1買いまで%",
    "第2買い",
    "第3買い",
    "保守目標",
    "強気目標",
    "停止価格",
    "RR",
    "判定",
    "テーマリスク理由",
    "テーマ予防策",
]

SCORE_SUMMARY_COLUMNS = [
    "ETF",
    "テーマ",
    "ETFスコア",
    "テーマスコア",
    "判定",
    "現在価格",
    "第1買いまで%",
    "RR",
    "テーマリスク",
    "ステージ",
]


def build_signal_table(rows: list[dict[str, object]]) -> pd.DataFrame:
    table = pd.DataFrame(rows)
    if table.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)
    return table.loc[:, DISPLAY_COLUMNS].sort_values(["ETFスコア", "テーマスコア"], ascending=False)


def write_daily_report(
    signal_table: pd.DataFrame,
    theme_scores: dict[str, float],
    allocation_text: str = "Core 60% / Satellite 25% / Cash 15%",
    portfolio: pd.DataFrame | None = None,
    theme_risk_table: pd.DataFrame | None = None,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"daily_report_{date:%Y-%m-%d}.md"
    buy_candidates = signal_table[signal_table["判定"].isin(["強気買い候補", "買い候補"])]
    watch = signal_table[signal_table["判定"].eq("押し目待ち")]
    profit = signal_table[signal_table["判定"].eq("利確候補")]
    sell = signal_table[signal_table["判定"].eq("売却候補")]
    theme_ranking = pd.DataFrame(
        [{"テーマ": theme, "テーマスコア": score} for theme, score in theme_scores.items()]
    ).sort_values("テーマスコア", ascending=False)
    portfolio_table = "保有なし"
    if portfolio is not None and not portfolio.empty:
        visible_columns = [
            "ticker",
            "theme",
            "quantity",
            "avg_price",
            "current_price",
            "market_value",
            "weight_pct",
            "unrealized_pnl_pct",
            "stop_price",
            "target_price",
            "status",
            "portfolio_action",
            "portfolio_reason",
        ]
        existing_columns = [column for column in visible_columns if column in portfolio.columns]
        portfolio_table = portfolio.loc[:, existing_columns].to_markdown(index=False)
    theme_risk_text = "評価なし"
    if theme_risk_table is not None and not theme_risk_table.empty:
        risk_path = PROJECT_ROOT / "data" / "processed" / "signals" / f"theme_rotation_risks_{date:%Y-%m-%d}.csv"
        risk_path.parent.mkdir(parents=True, exist_ok=True)
        theme_risk_table.to_csv(risk_path, index=False)
        theme_risk_text = theme_risk_table.head(15).to_markdown(index=False)
    score_summary_columns = [column for column in SCORE_SUMMARY_COLUMNS if column in signal_table.columns]
    score_summary = signal_table.loc[:, score_summary_columns].head(12) if score_summary_columns else pd.DataFrame()
    content = [
        f"# daily_report {date:%Y-%m-%d}",
        "",
        "## 1. 今日の市場ステージ",
        "自動判定の初期版です。QQQ/SPYと対象ETFの相対強度をもとに、個別ETFのステージを確認してください。",
        "",
        "## 2. Core/Satellite/Cash推奨比率",
        f"{allocation_text} を現在の検証済み候補として使います。ドローダウン条件に達した場合はSatelliteを縮小します。",
        "",
        "## 3. テーマスコアランキング",
        theme_ranking.to_markdown(index=False),
        "",
        "## 4. ETFスコアランキング 要約",
        score_summary.to_markdown(index=False) if not score_summary.empty else "評価なし",
        "",
        "## 4b. ETFスコアランキング 詳細",
        signal_table.to_markdown(index=False),
        "",
        "## 5. 買い候補",
        buy_candidates.to_markdown(index=False) if not buy_candidates.empty else "該当なし",
        "",
        "## 6. 押し目待ち",
        watch.to_markdown(index=False) if not watch.empty else "該当なし",
        "",
        "## 7. 利確候補",
        profit.to_markdown(index=False) if not profit.empty else "該当なし",
        "",
        "## 8. 売却候補",
        sell.to_markdown(index=False) if not sell.empty else "該当なし",
        "",
        "## 9. 保有ETF評価",
        portfolio_table,
        "",
        "## 10. テーマ交代リスクと予防策",
        theme_risk_text,
        "",
        "## 11-13. 価格差・目標価格・RR・今日やること",
        "上表の第1買いまで%、保守目標、強気目標、停止価格、RRを確認し、条件到達時のみMASATOが最終判断します。",
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def _mobile_value(value: object) -> str:
    if pd.isna(value):
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def write_mobile_summary(
    signal_table: pd.DataFrame,
    readiness: pd.DataFrame | None = None,
    manual_decision_summary: pd.DataFrame | None = None,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
    max_rows: int = 8,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"mobile_summary_{date:%Y-%m-%d}.txt"
    go_hold = "GO（手動確認後）"
    if readiness is not None and not readiness.empty and readiness["状態"].eq("Block").any():
        go_hold = "HOLD"
    manual_text = "手動判断: 未評価"
    if manual_decision_summary is not None and not manual_decision_summary.empty:
        manual = manual_decision_summary.iloc[0]
        manual_text = (
            f"手動判断: {_mobile_value(manual.get('状態'))} "
            f"対象{_mobile_value(manual.get('対象件数'))} "
            f"判断済{_mobile_value(manual.get('判断済み件数'))} "
            f"未判断{_mobile_value(manual.get('未判断件数'))}"
        )
    lines = [
        f"ETF Rotation {date:%Y-%m-%d}",
        f"GO/HOLD: {go_hold}",
        manual_text,
        "",
        "上位ETF:",
    ]
    top = signal_table.head(max_rows) if not signal_table.empty else pd.DataFrame()
    if top.empty:
        lines.append("評価なし")
    for index, row in enumerate(top.to_dict("records"), start=1):
        lines.append(
            f"{index}. {_mobile_value(row.get('ETF'))} "
            f"ETF{_mobile_value(row.get('ETFスコア'))} "
            f"テーマ{_mobile_value(row.get('テーマスコア'))} "
            f"{_mobile_value(row.get('判定'))} "
            f"RR{_mobile_value(row.get('RR'))} "
            f"リスク{_mobile_value(row.get('テーマリスク'))}"
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def write_weekly_line_summary(
    action_label_history: pd.DataFrame | None = None,
    portfolio: pd.DataFrame | None = None,
    output_dir: str | Path = "reports/weekly",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"weekly_line_summary_{date:%Y-%m-%d}.txt"
    defense_days = 0
    buy_days = 0
    wait_days = 0
    sell_days = 0
    weekly_label = "🟡 WAIT"
    weekly_text = "待機中心の週でした。"
    if action_label_history is not None and not action_label_history.empty:
        labels = action_label_history.copy()
        labels["日数"] = pd.to_numeric(labels["日数"], errors="coerce").fillna(0)
        label_days = dict(zip(labels["行動ラベル"].astype(str), labels["日数"].astype(int), strict=False))
        defense_days = int(label_days.get("🔴 DEFENSE", 0))
        buy_days = int(label_days.get("🟢 CHECK BUY", 0))
        wait_days = int(label_days.get("🟡 WAIT", 0))
        sell_days = int(label_days.get("🟣 CHECK SELL", 0))
        if defense_days > buy_days:
            weekly_label = "🔴 DEFENSE"
            weekly_text = "買い急ぎを抑える週でした。"
        elif buy_days:
            weekly_label = "🟢 CHECK BUY"
            weekly_text = "買い候補を手動確認する週でした。"
        elif sell_days:
            weekly_label = "🟣 CHECK SELL"
            weekly_text = "保有確認を優先する週でした。"
        else:
            weekly_label = "🟡 WAIT"
            weekly_text = "待機中心の週でした。"
    else:
        weekly_label = "🟡 WAIT"
        weekly_text = "週次データは未集計です。"

    reference_rows = []
    if portfolio is not None and not portfolio.empty:
        frame = portfolio.copy()
        frame["weight_pct"] = pd.to_numeric(frame.get("weight_pct", pd.Series(dtype=float)), errors="coerce")
        for row in frame.sort_values("weight_pct", ascending=False).to_dict("records"):
            scope = _portfolio_scope(row)
            weight = row.get("weight_pct")
            if scope == "reference" and pd.notna(weight) and float(weight) >= 10.0:
                reference_rows.append(f"{_holding_name(row)}: {float(weight):.1f}%")

    lines = [
        f"ETF Rotation Weekly {date:%Y-%m-%d}",
        "",
        weekly_label,
        weekly_text,
        "",
        "今週やったこと:",
        "✅ 毎朝の信号を確認",
        "✅ DEFENSE中は新規買いを抑制",
        "❌ 飛びつき買い禁止",
        "❌ ナンピン禁止",
        "",
        "週次サマリー:",
        f"DEFENSE: {defense_days}日",
        f"CHECK BUY: {buy_days}日",
        f"CHECK SELL: {sell_days}日",
        f"WAIT: {wait_days}日",
        "",
        "参考保有の注意:",
    ]
    if reference_rows:
        lines.extend(reference_rows[:4])
        lines.append("ETF信号とは別枠。買い増しは個別に確認。")
    else:
        lines.append("10%以上の参考保有なし")
    lines.extend(
        [
            "",
            "来週の方針:",
            "DEFENSE中は新規買い禁止。",
            "買い候補は必ず手動確認。",
            "コア積立は通常ルール優先。",
            "",
            "※これは投資助言ではありません。最終判断はご自身で行ってください。",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def write_user_friction_simulation_report(
    friction_table: pd.DataFrame,
    output_dir: str | Path = "reports/pdca",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"user_friction_simulation_{date:%Y-%m-%d}.md"
    high_or_mid = (
        friction_table[friction_table["深刻度"].isin(["高", "中"])]
        if not friction_table.empty and "深刻度" in friction_table.columns
        else pd.DataFrame()
    )
    next_action = "現行表示を維持"
    if not high_or_mid.empty:
        next_action = str(high_or_mid.iloc[0].get("修正案", "改善候補を確認"))
    content = [
        f"# user_friction_simulation {date:%Y-%m-%d}",
        "",
        "30年分の利用体験を高速エミュレートし、テストユーザーが感じる不満を抽出します。",
        "これは未来予測ではなく、過去/直近の判定分布を長期利用体験へ拡大したUX検証です。",
        "",
        "## 不満シナリオ",
        friction_table.to_markdown(index=False) if not friction_table.empty else "不満シナリオなし",
        "",
        "## 次の修正候補",
        next_action,
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def _format_signal_row(row: dict[str, object]) -> str:
    return (
        f"{_mobile_value(row.get('ETF'))}: {_mobile_value(row.get('判定'))} "
        f"/ {_mobile_value(row.get('ステージ')).replace('ステージ', 'S')} "
        f"/ 買い差{_mobile_value(row.get('第1買いまで%'))}% "
        f"/ RR{_mobile_value(row.get('RR'))} "
        f"/ リスク{_mobile_value(row.get('テーマリスク'))}"
    )


def _stage_label(stage: object) -> str:
    text = _mobile_value(stage)
    if "ステージ4" in text:
        return "過熱"
    if "ステージ5" in text:
        return "失速"
    if "ステージ3" in text:
        return "加速"
    if "ステージ2" in text:
        return "初動"
    if "ステージ1" in text:
        return "構想"
    return text


def _short_detail(row: dict[str, object]) -> str:
    stage = _mobile_value(row.get("ステージ")).replace("ステージ", "S")
    return (
        f"{_mobile_value(row.get('ETF'))}: {stage} / "
        f"RR{_mobile_value(row.get('RR'))} / "
        f"買い差 {_mobile_value(row.get('第1買いまで%'))}% / "
        f"リスク{_mobile_value(row.get('テーマリスク'))}"
    )


def _numeric_series(table: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if table.empty or column not in table.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(table[column], errors="coerce").fillna(default)


def _market_score(signal_table: pd.DataFrame) -> int:
    if signal_table.empty:
        return 0
    score = 75.0
    buy_count = int(signal_table["判定"].isin(["強気買い候補", "買い候補"]).sum())
    wait_count = int(signal_table["判定"].eq("押し目待ち").sum())
    risk_count = int(signal_table["判定"].isin(["利確候補", "売却候補", "リスク削減"]).sum())
    hot_late_count = int(signal_table["ステージ"].astype(str).str.contains("ステージ4|ステージ5", na=False).sum())
    high_risk_count = int(signal_table["テーマリスク"].astype(str).eq("高").sum())
    score += min(buy_count * 10, 20)
    score += min(wait_count * 4, 12)
    score -= min(risk_count * 3, 18)
    score -= min(hot_late_count * 2, 18)
    score -= min(high_risk_count * 3, 12)
    rr = _numeric_series(signal_table, "RR")
    if not rr.empty:
        score += min(float((rr >= 1.5).sum()) * 2, 8)
    return int(round(max(0.0, min(score, 100.0))))


def _buy_distance_label(row: dict[str, object]) -> str:
    signal = _mobile_value(row.get("判定"))
    stage = _mobile_value(row.get("ステージ"))
    risk = _mobile_value(row.get("テーマリスク"))
    try:
        gap = abs(float(row.get("第1買いまで%", 99.0)))
    except (TypeError, ValueError):
        gap = 99.0
    try:
        rr = float(row.get("RR", 0.0))
    except (TypeError, ValueError):
        rr = 0.0
    if signal in {"強気買い候補", "買い候補"}:
        return "条件到達"
    if "ステージ5" in stage or risk == "高":
        return "遠い"
    if "ステージ4" in stage:
        return "中距離" if gap <= 5 and rr >= 0.8 else "遠い"
    if gap <= 2:
        return "近い"
    if gap <= 5:
        return "中距離"
    return "遠い"


def _buy_distance_detail(row: dict[str, object]) -> str:
    label = _buy_distance_label(row)
    try:
        gap = float(row.get("第1買いまで%", 0.0))
    except (TypeError, ValueError):
        gap = 0.0
    if label == "条件到達":
        return "条件到達"
    if gap < 0:
        return f"{label} / あと{abs(gap):.1f}%"
    return f"{label} / 条件付近"


def _estimate_signal_distance(candidates: pd.DataFrame) -> str:
    if candidates.empty:
        return "未定"
    labels = [_buy_distance_label(row) for row in candidates.to_dict("records")]
    if "条件到達" in labels:
        return "条件到達"
    if "近い" in labels:
        return "近い（目安1〜3日）"
    if "中距離" in labels:
        return "中距離（目安3〜12日）"
    return "遠い（2週間以上または条件悪化）"


def _watch_candidates(signal_table: pd.DataFrame, limit: int = 3) -> pd.DataFrame:
    if signal_table.empty:
        return signal_table
    excluded = {"利確候補", "売却候補", "リスク削減"}
    candidates = signal_table[~signal_table["判定"].isin(excluded)].copy()
    if candidates.empty:
        return candidates
    candidates["_distance_rank"] = candidates.apply(
        lambda row: {"条件到達": 0, "近い": 1, "中距離": 2, "遠い": 3}.get(_buy_distance_label(row.to_dict()), 4),
        axis=1,
    )
    return (
        candidates.sort_values(["_distance_rank", "ETFスコア", "テーマスコア"], ascending=[True, False, False])
        .head(limit)
        .drop(columns=["_distance_rank"])
    )


def _core_recovery_candidates(core: pd.DataFrame, market_score: int, defense: bool, limit: int = 3) -> pd.DataFrame:
    if core.empty:
        return core.head(0)
    candidates = core.copy()
    candidates["_buy_gap"] = pd.to_numeric(candidates.get("第1買いまで%", 99.0), errors="coerce").fillna(99.0)
    candidates["_etf_score"] = pd.to_numeric(candidates.get("ETFスコア", 0.0), errors="coerce").fillna(0.0)
    candidates["_rr"] = pd.to_numeric(candidates.get("RR", 0.0), errors="coerce").fillna(0.0)
    stage = candidates["ステージ"].astype(str)
    signal = candidates["判定"].astype(str)
    short_crash_recovery = (
        ((market_score <= 45) | defense)
        & (candidates["_buy_gap"] >= -5.0)
        & (candidates["_etf_score"] >= 55.0)
        & (~signal.isin({"利確候補", "売却候補", "リスク削減"}))
    )
    long_crash_recovery = (
        stage.str.contains("ステージ1|ステージ2", na=False)
        & (candidates["_buy_gap"] >= -8.0)
        & (candidates["_etf_score"] >= 35.0)
        & (candidates["_rr"] >= 3.0)
        & (~signal.isin({"利確候補", "リスク削減"}))
    )
    candidates = candidates[
        (short_crash_recovery | long_crash_recovery)
        & (candidates["テーマリスク"].astype(str).ne("高"))
        & (~stage.str.contains("ステージ5", na=False))
    ]
    if candidates.empty:
        return candidates.drop(columns=[column for column in ["_buy_gap", "_etf_score", "_rr"] if column in candidates])
    return (
        candidates.sort_values(["_buy_gap", "_etf_score", "_rr"], ascending=[False, False, False])
        .head(limit)
        .drop(columns=["_buy_gap", "_etf_score", "_rr"])
    )


def _readiness_reason(readiness: pd.DataFrame | None, item: str) -> str:
    if readiness is None or readiness.empty:
        return ""
    rows = readiness[readiness["判定項目"].astype(str).eq(item)]
    if rows.empty:
        return ""
    return _mobile_value(rows.iloc[0].get("理由"))


def _filter_rows(signal_table: pd.DataFrame, tickers: set[str] | None = None) -> pd.DataFrame:
    if signal_table.empty:
        return signal_table
    if tickers is None:
        return signal_table
    return signal_table[signal_table["ETF"].isin(tickers)]


def _portfolio_scope(row: dict[str, object]) -> str:
    scope = _mobile_value(row.get("signal_scope")).strip()
    if scope:
        return scope
    asset_class = _mobile_value(row.get("asset_class")).strip().lower()
    ticker = _mobile_value(row.get("ticker")).upper()
    if asset_class in {"fund", "index", "401k"}:
        return "core"
    if asset_class in {"stock", "jp_stock"}:
        return "reference"
    if ticker in {"VT", "VTI", "SPY", "QQQ"}:
        return "etf_signal"
    if ticker in {"SOFI", "TDK", "401K_FOREIGN_INDEX", "ORCAN"}:
        return "reference"
    return "etf_signal"


def _holding_name(row: dict[str, object]) -> str:
    display_name = _mobile_value(row.get("display_name")).strip()
    if display_name and display_name != "-":
        return display_name
    fallback_names = {
        "401K_FOREIGN_INDEX": "401k 外国株式インデックス",
        "ORCAN": "NISA オルカン",
        "TDK": "TDK",
        "SOFI": "SOFI",
        "QQQ": "QQQ",
    }
    ticker = _mobile_value(row.get("ticker")).upper()
    return fallback_names.get(ticker, _mobile_value(row.get("ticker")))


def _action_label_meaning(action_label: str) -> str:
    meanings = {
        "🔴 DEFENSE": "危険だから買わない。資金を守る日。",
        "🟡 WAIT": "危険ではないが条件未達。買い場を待つ日。",
        "🟢 CHECK BUY": "候補あり。価格と保有比率を手動確認する日。",
        "🟣 CHECK SELL": "新規買いより保有の利確/売却確認を優先する日。",
    }
    return meanings.get(action_label, "自己判断のために確認する日。")


def _modern_market_guard_lines(
    signal_table: pd.DataFrame,
    portfolio: pd.DataFrame | None = None,
    limit: int = 4,
) -> list[str]:
    lines: list[str] = []
    if not signal_table.empty:
        stage_text = signal_table["ステージ"].astype(str)
        hot_rows = signal_table[
            stage_text.str.contains("ステージ4", na=False)
            & (pd.to_numeric(signal_table["ETFスコア"], errors="coerce").fillna(0.0) >= 75.0)
        ]
        if not hot_rows.empty:
            names = hot_rows["ETF"].astype(str).head(3).tolist()
            lines.append(f"急騰テーマ注意: {', '.join(names)} は飛びつき禁止。")
        high_risk_rows = signal_table[signal_table["テーマリスク"].astype(str).eq("高")]
        if not high_risk_rows.empty:
            names = high_risk_rows["ETF"].astype(str).head(3).tolist()
            lines.append(f"テーマ交代注意: {', '.join(names)} はCore優先で確認。")
        ai_rows = signal_table[
            signal_table["テーマ"].astype(str).str.contains("AI|半導体|テクノロジ", case=False, na=False)
            & stage_text.str.contains("ステージ3|ステージ4", na=False)
        ]
        if len(ai_rows) >= 2:
            lines.append("AI/半導体集中注意: 追加は一括ではなく上限確認。")
    if portfolio is not None and not portfolio.empty and "weight_pct" in portfolio.columns:
        weights = pd.to_numeric(portfolio["weight_pct"], errors="coerce").fillna(0.0)
        reference_rows = portfolio.loc[
            [
                _portfolio_scope(row) not in {"etf_signal", "core"}
                for row in portfolio.to_dict("records")
            ]
        ].copy()
        if not reference_rows.empty:
            reference_rows["weight_pct"] = weights.loc[reference_rows.index]
            large_reference = reference_rows[reference_rows["weight_pct"] >= 10.0]
            if not large_reference.empty:
                names = [_holding_name(row) for row in large_reference.head(3).to_dict("records")]
                lines.append(f"個別株誘惑注意: {', '.join(names)} はETF信号で買い増ししない。")
    return lines[:limit]


def _future_action_guard_lines(
    signal_table: pd.DataFrame,
    market_score: int,
    defense: bool = False,
    limit: int = 4,
) -> list[str]:
    if signal_table.empty:
        return []
    lines: list[str] = []
    stage_text = signal_table["ステージ"].astype(str)
    theme_text = signal_table["テーマ"].astype(str)
    ticker_text = signal_table["ETF"].astype(str)
    hot_count = int(stage_text.str.contains("ステージ4", na=False).sum())
    late_count = int(stage_text.str.contains("ステージ5", na=False).sum())
    ai_count = int(theme_text.str.contains("AI|半導体|テクノロジ", case=False, na=False).sum())
    defensive_theme_count = int(theme_text.str.contains("金融|電力|ヘルスケア|債券", na=False).sum())
    bond_like_count = int(ticker_text.str.contains("IEF|TLT|SHY", case=False, na=False).sum())
    high_risk_count = int(signal_table["テーマリスク"].astype(str).eq("高").sum())
    if defense or market_score <= 35 or late_count >= 2:
        lines.append("流動性ショック想定: 新規買いより現金余力を優先。")
    if defensive_theme_count + bond_like_count >= 2 and high_risk_count >= 1:
        lines.append("金利ショック想定: 金融/債券/公益の連鎖リスクを確認。")
    if ai_count >= 2 and hot_count >= 1:
        lines.append("AI集中相場想定: サテライト上限を超えて追わない。")
    if hot_count >= 3:
        lines.append("急反発相場想定: 置いていかれ不安で成行買いしない。")
    if not lines:
        lines.append("未来ショック想定: ルール外の買い増しをしない。")
    return lines[:limit]


def write_decision_brief(
    signal_table: pd.DataFrame,
    readiness: pd.DataFrame | None = None,
    portfolio: pd.DataFrame | None = None,
    defense_streak_days: int | None = None,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"decision_brief_{date:%Y-%m-%d}.txt"
    core_tickers = {"VT", "VTI", "SPY", "QQQ"}
    buy_signals = {"強気買い候補", "買い候補"}
    wait_signals = {"押し目待ち"}
    risk_signals = {"利確候補", "売却候補", "リスク削減"}
    core = _filter_rows(signal_table, core_tickers)
    satellite = signal_table[~signal_table["ETF"].isin(core_tickers)] if not signal_table.empty else signal_table
    core_buy = core[core["判定"].isin(buy_signals)]
    core_wait = core[core["判定"].isin(wait_signals)]
    satellite_buy = satellite[satellite["判定"].isin(buy_signals)]
    satellite_wait = satellite[satellite["判定"].isin(wait_signals)]
    risk_review = signal_table[signal_table["判定"].isin(risk_signals)]
    hot_or_late = signal_table[
        signal_table["ステージ"].astype(str).str.contains("ステージ4|ステージ5", na=False)
    ]
    watch_candidates = _watch_candidates(signal_table)
    market_score = _market_score(signal_table)
    distance_text = _estimate_signal_distance(watch_candidates)
    held_tickers: set[str] = set()
    if portfolio is not None and not portfolio.empty and "ticker" in portfolio.columns:
        held_tickers = set(portfolio["ticker"].dropna().astype(str).str.upper())
    held_risk_review = (
        risk_review[risk_review["ETF"].astype(str).str.upper().isin(held_tickers)]
        if held_tickers and not risk_review.empty
        else pd.DataFrame()
    )
    defense = False
    if readiness is not None and not readiness.empty:
        defense = readiness["状態"].eq("Block").any()
    data_stale_reason = _readiness_reason(readiness, "データ鮮度")
    data_stale = bool(data_stale_reason) and "当日分" not in data_stale_reason
    defense = defense or market_score <= 35
    core_recovery = _core_recovery_candidates(core, market_score, defense and not data_stale)

    has_buy = not core_buy.empty or not satellite_buy.empty
    has_core_recovery = not core_recovery.empty and core_buy.empty
    if has_core_recovery and not risk_review.empty:
        recovery_tickers = set(core_recovery["ETF"].astype(str).str.upper())
        risk_review = risk_review[~risk_review["ETF"].astype(str).str.upper().isin(recovery_tickers)]
        held_risk_review = (
            risk_review[risk_review["ETF"].astype(str).str.upper().isin(held_tickers)]
            if held_tickers and not risk_review.empty
            else pd.DataFrame()
        )
    has_sell_check = not risk_review.empty
    if defense:
        action_label = "🔴 DEFENSE"
        action_text = "新規買いは慎重判断。リスク確認を優先してください。"
    elif has_sell_check:
        action_label = "🟣 CHECK SELL"
        action_text = "今日は新規買いより、保有ETFの確認を優先。"
    elif has_buy or has_core_recovery:
        action_label = "🟢 CHECK BUY"
        action_text = (
            "コア分割買い候補があります。少額前提で手動確認してください。"
            if has_core_recovery and not has_buy
            else "買い候補があります。手動確認してください。"
        )
    else:
        action_label = "🟡 WAIT"
        action_text = "本日の新規買い候補はありません。"

    buy_names = pd.concat([core_buy, satellite_buy])["ETF"].astype(str).head(3).tolist() if has_buy else []
    sell_names = risk_review["ETF"].astype(str).head(3).tolist() if has_sell_check else []
    held_sell_names = held_risk_review["ETF"].astype(str).head(3).tolist() if not held_risk_review.empty else []
    today_actions = []
    mistake_guard_lines = ["上がっても飛びつかない。", "下がってもナンピンしない。"]
    if defense:
        today_actions.append("✅ 積立だけ通常ルールで継続")
        if has_core_recovery:
            recovery_names = core_recovery["ETF"].astype(str).head(3).tolist()
            today_actions.append(f"✅ コアだけ少額分割を手動検討: {', '.join(recovery_names)}")
        if held_sell_names:
            today_actions.append(f"✅ 保有ETFを確認: {', '.join(held_sell_names)}")
        elif has_sell_check:
            today_actions.append(f"✅ 市場リスク対象を確認: {', '.join(sell_names)}")
        elif has_buy:
            today_actions.append(f"✅ 買い候補は少額/見送り前提で手動確認: {', '.join(buy_names)}")
        today_actions.append("❌ 新規買い禁止")
        if has_core_recovery:
            today_actions[-1] = "❌ サテライト新規買い禁止"
        today_actions.append("❌ ナンピン禁止")
        today_actions.append("❌ 過熱・失速銘柄の追い買い禁止")
    elif has_sell_check:
        if has_core_recovery:
            recovery_names = core_recovery["ETF"].astype(str).head(3).tolist()
            today_actions.append(f"✅ コアだけ少額分割を手動検討: {', '.join(recovery_names)}")
        if held_sell_names:
            today_actions.append(f"✅ 保有ETFを確認: {', '.join(held_sell_names)}")
        else:
            today_actions.append(f"✅ 市場リスク対象を確認: {', '.join(sell_names)}")
        today_actions.append("❌ サテライト新規買い禁止" if has_core_recovery else "❌ 新規買いは見送り")
        today_actions.append("❌ ナンピン禁止")
    elif has_buy or has_core_recovery:
        if has_core_recovery and not has_buy:
            recovery_names = core_recovery["ETF"].astype(str).head(3).tolist()
            today_actions.append(f"✅ コアだけ少額分割を手動検討: {', '.join(recovery_names)}")
            today_actions.append("❌ サテライト新規買い禁止")
        else:
            today_actions.append(f"✅ 買い候補を手動確認: {', '.join(buy_names)}")
            today_actions.append("❌ 成行飛びつき禁止")
        mistake_guard_lines[0] = "買う場合も成行で飛びつかない。"
    else:
        today_actions.append("✅ 積立だけ通常ルールで継続")
        today_actions.append("❌ 新規買いは見送り")
        today_actions.append("❌ ナンピン禁止")

    reason_lines = []
    if not has_buy:
        reason_lines.append("買い候補なし")
    if not hot_or_late.empty:
        reason_lines.append("一部テーマは過熱または失速")
    if has_sell_check:
        reason_lines.append("新規買いより保有確認を優先")
    if defense:
        reason_lines.append("リスク確認を優先")
    if has_core_recovery:
        reason_lines.append("コアは少額分割の確認余地あり")
    if data_stale:
        reason_lines.append("データ鮮度に問題あり")
    portfolio_summary_lines: list[str] = []
    portfolio_signal_lines: list[str] = []
    portfolio_reference_lines: list[str] = []
    reference_alert_lines: list[str] = []
    reference_total_weight = 0.0
    reference_top_name = ""
    reference_top_weight = 0.0
    if portfolio is not None and not portfolio.empty:
        portfolio_frame = portfolio.copy()
        if "market_value" in portfolio_frame.columns:
            portfolio_frame["market_value"] = pd.to_numeric(portfolio_frame["market_value"], errors="coerce")
        if "weight_pct" in portfolio_frame.columns:
            portfolio_frame["weight_pct"] = pd.to_numeric(portfolio_frame["weight_pct"], errors="coerce")
        total_value = portfolio_frame.get("market_value", pd.Series(dtype=float)).dropna().sum()
        if total_value > 0:
            portfolio_summary_lines.append(f"評価額合計: {total_value:,.0f}円")
        all_reference_rows = [
            row
            for row in portfolio_frame.to_dict("records")
            if pd.notna(row.get("weight_pct")) and _portfolio_scope(row) not in {"etf_signal", "core"}
        ]
        if all_reference_rows:
            reference_total_weight = sum(float(row.get("weight_pct") or 0.0) for row in all_reference_rows)
            reference_top = max(all_reference_rows, key=lambda row: float(row.get("weight_pct") or 0.0))
            reference_top_name = _holding_name(reference_top)
            reference_top_weight = float(reference_top.get("weight_pct") or 0.0)
            if reference_total_weight >= 20.0 or reference_top_weight >= 10.0:
                mistake_guard_lines.append("参考保有はETF通知で買い増ししない。")
        top_holdings = portfolio_frame.sort_values("weight_pct", ascending=False).head(5)
        for row in top_holdings.to_dict("records"):
            holding_name = _holding_name(row)
            weight = row.get("weight_pct")
            if pd.notna(weight):
                portfolio_summary_lines.append(f"{holding_name}: {float(weight):.1f}%")
                scope = _portfolio_scope(row)
                if scope == "etf_signal":
                    portfolio_signal_lines.append(f"{holding_name}: ETF信号対象")
                elif scope == "core":
                    portfolio_reference_lines.append(f"{holding_name}: コア資産")
                else:
                    portfolio_reference_lines.append(f"{holding_name}: ETF信号の参考外")
                    if float(weight) >= 10.0:
                        portfolio_action = _mobile_value(row.get("portfolio_action"))
                        portfolio_reason = _mobile_value(row.get("portfolio_reason"))
                        reference_alert_lines.append(
                            f"{holding_name}: {float(weight):.1f}% / {portfolio_action} / {portfolio_reason}"
                        )
    modern_guard_lines = _modern_market_guard_lines(signal_table, portfolio)
    future_guard_lines = _future_action_guard_lines(signal_table, market_score, defense)

    lines = [
        f"ETF Rotation Daily {date:%Y-%m-%d}",
        "",
    ]
    if data_stale:
        lines.extend(
            [
                "⚠️ DATA STALE",
                data_stale_reason,
                "この通知は新規売買判断に使わないでください。",
                "",
            ]
        )
    lines.extend([
        "市場スコア",
        f"{market_score}/100",
        "",
        action_label,
        action_text,
        _action_label_meaning(action_label),
        "",
    ])
    if defense and defense_streak_days is not None:
        lines.extend(
            [
                "DEFENSE継続:",
                f"{defense_streak_days}日",
                "解除条件:",
                "市場スコア36以上、リスク対象減少、過熱/失速の改善",
                "",
            ]
        )
    lines.extend([
        "今日やること:",
        *today_actions,
        "",
        "ルール破り防止:",
        *mistake_guard_lines,
        "",
    ])
    if modern_guard_lines:
        lines.extend(["近年型リスク:", *modern_guard_lines, ""])
    if future_guard_lines:
        lines.extend(["未来ショック備え:", *future_guard_lines, ""])
    lines.extend([
        "今日の自己確認:",
        "守れた / 破った / 保留",
        "破った場合は週次PDCAで原因確認。",
        "",
        "買い判断:",
        f"新規買い: {'あり' if has_buy else 'コア分割のみ確認' if has_core_recovery else 'なし'}",
        f"コア買い: {'候補あり' if not core_buy.empty else '待ち'}",
        f"コア分割買い: {'候補あり' if has_core_recovery else '待ち'}",
        f"サテライト買い: {'候補あり' if not satellite_buy.empty else '待ち'}",
        f"利確/売却確認: {'あり' if has_sell_check else 'なし'}",
        "",
    ])
    if portfolio_summary_lines:
        lines.extend(["保有サマリー:", *portfolio_summary_lines, ""])
    if portfolio_signal_lines or portfolio_reference_lines:
        lines.extend(["保有の扱い:"])
        if portfolio_signal_lines:
            lines.extend(portfolio_signal_lines[:4])
        if portfolio_reference_lines:
            lines.extend(portfolio_reference_lines[:4])
        lines.append("")
    if reference_alert_lines:
        lines.extend(
            [
                "参考保有の注意:",
                f"参考保有合計: {reference_total_weight:.1f}%",
                f"最大: {reference_top_name} {reference_top_weight:.1f}%",
                *reference_alert_lines[:4],
                "ETF信号とは別枠。買い増しはETF通知で判断しない。",
                "",
            ]
        )
    lines.extend([
        "次の買い候補:",
    ])
    if watch_candidates.empty:
        lines.append("なし")
    else:
        for row in watch_candidates.to_dict("records"):
            lines.append(f"{_mobile_value(row.get('ETF'))}  買い条件まで{_buy_distance_detail(row)}")
    lines.extend(
        [
            "",
            "買いシグナル発生まで",
            distance_text,
            "",
        ]
    )
    lines.extend([
        "コア:",
    ])
    if has_core_recovery:
        lines.append("暴落後の回復確認。買う場合も一括ではなく少額分割。")
        lines.append("二番底リスクあり。試し玉以上に広げない。")
        for row in core_recovery.to_dict("records"):
            lines.append(f"{_mobile_value(row.get('ETF'))}: コア分割買い検討 / {_buy_distance_detail(row)}")
        lines.append("サテライトはまだ待つ。")
    elif core_buy.empty and core_wait.empty:
        lines.append("VT/VTI/SPY/QQQは待ち。")
        lines.append("積立は通常ルール優先。")
    for row in pd.concat([core_buy, core_wait]).head(4).to_dict("records"):
        lines.append(_format_signal_row(row))

    lines.extend(["", "サテライト:"])
    if satellite_buy.empty and satellite_wait.empty:
        lines.append("テーマETFの新規買い候補なし。")
        lines.append("過熱・失速銘柄は買い増ししない。")
    for row in pd.concat([satellite_buy, satellite_wait]).head(6).to_dict("records"):
        lines.append(_format_signal_row(row))

    if has_sell_check:
        lines.append("")
        lines.append("確認対象:")
        for row in risk_review.head(4).to_dict("records"):
            ticker = _mobile_value(row.get("ETF"))
            signal = _mobile_value(row.get("判定"))
            stage = _stage_label(row.get("ステージ"))
            if signal == "利確候補":
                action = "買い増ししない。保有継続/一部利確を手動確認。"
            elif signal == "売却候補":
                action = "新規買いしない。保有継続可否を手動確認。"
            else:
                action = "リスクを手動確認。"
            lines.extend([ticker, f"状態: {stage}", f"確認: {signal}", f"行動: {action}", ""])
        if lines[-1] == "":
            lines.pop()

    lines.extend(["", "理由:"])
    lines.extend([f"・{reason}" for reason in reason_lines[:4]])

    if has_sell_check:
        lines.extend(["", "詳細:"])
        for row in risk_review.head(4).to_dict("records"):
            lines.append(_short_detail(row))

    lines.extend(["", "※これは投資助言ではありません。最終判断はご自身で行ってください。"])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def write_signal_snapshot(
    signal_table: pd.DataFrame,
    output_dir: str | Path = "data/processed/signals",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"signals_{date:%Y-%m-%d}.csv"
    signal_table.to_csv(output_path, index=False)
    return output_path


def write_notification_report(
    notifications: pd.DataFrame,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"notification_candidates_{date:%Y-%m-%d}.md"
    if notifications.empty:
        notification_text = "通知候補なし"
    else:
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        sorted_notifications = notifications.copy()
        sorted_notifications["_priority_rank"] = sorted_notifications["優先度"].map(priority_order).fillna(9)
        sorted_notifications = sorted_notifications.sort_values(["_priority_rank", "ETF"]).drop(columns=["_priority_rank"])
        sections = []
        for priority, title in [("High", "High: 今日すぐ確認"), ("Medium", "Medium: 監視強化"), ("Low", "Low: 参考")]:
            subset = sorted_notifications[sorted_notifications["優先度"].eq(priority)]
            sections.extend(
                [
                    f"## {title}",
                    subset.to_markdown(index=False) if not subset.empty else "該当なし",
                    "",
                ]
            )
        notification_text = "\n".join(sections).strip()
    content = [
        f"# 通知候補 {date:%Y-%m-%d}",
        "",
        "実売買発注は行いません。MASATOの最終判断用アラート候補です。",
        "",
        notification_text,
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_notification_summary_report(
    priority_counts: pd.DataFrame,
    notification_summary: pd.DataFrame,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"notification_summary_{date:%Y-%m-%d}.md"
    counts_text = priority_counts.to_markdown(index=False) if not priority_counts.empty else "通知候補なし"
    summary_text = notification_summary.to_markdown(index=False) if not notification_summary.empty else "通知候補なし"
    content = [
        f"# notification_summary {date:%Y-%m-%d}",
        "",
        "通知アウトボックスを送信前に確認するための要約です。外部送信は行いません。",
        "",
        "## 優先度別件数",
        counts_text,
        "",
        "## 送信前確認リスト",
        summary_text,
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_notification_delivery_plan_report(
    delivery_plan: pd.DataFrame,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"notification_delivery_plan_{date:%Y-%m-%d}.md"
    plan_text = delivery_plan.to_markdown(index=False) if not delivery_plan.empty else "通知候補なし"
    content = [
        f"# notification_delivery_plan {date:%Y-%m-%d}",
        "",
        "外部送信は行いません。通知候補を送信先へ接続する前の配送計画です。",
        "",
        "## 配送ルール",
        "- High: manual_immediate。MASATOが当日すぐ確認",
        "- Medium: daily_digest。日次確認にまとめる",
        "- Low: archive_only。記録のみ",
        "",
        "## 配送計画",
        plan_text,
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_portfolio_check_report(
    issues: pd.DataFrame,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"portfolio_check_{date:%Y-%m-%d}.md"
    if issues.empty:
        issues_text = "評価なし"
    else:
        issues_text = issues.to_markdown(index=False)
    has_error = not issues.empty and issues["severity"].eq("Error").any()
    status_text = "要修正" if has_error else "確認OK"
    content = [
        f"# portfolio_check {date:%Y-%m-%d}",
        "",
        f"判定: {status_text}",
        "",
        "日次レポート前に、保有CSVの入力漏れや数値ミスを確認します。",
        "",
        issues_text,
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_manual_decision_sheet(
    delivery_plan: pd.DataFrame,
    output_dir: str | Path = "reports/daily",
    processed_output_dir: str | Path = "data/processed/decisions",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    processed_dir = ensure_dir(processed_output_dir)
    output_path = PROJECT_ROOT / directory / f"manual_decision_sheet_{date:%Y-%m-%d}.md"
    csv_path = processed_dir / f"manual_decision_sheet_{date:%Y-%m-%d}.csv"
    base_columns = ["優先度", "ETF", "配送先", "確認タイミング", "カテゴリ", "シグナル", "推奨行動"]
    input_columns = ["判断日", "判断者", "判断", "数量", "指値", "実行価格", "実行時刻", "約定状態", "メモ"]
    existing_columns = [column for column in base_columns if column in delivery_plan.columns]
    decision_sheet = delivery_plan.loc[:, existing_columns].copy() if not delivery_plan.empty else pd.DataFrame()
    for column in input_columns:
        decision_sheet[column] = ""
    if csv_path.exists() and not decision_sheet.empty:
        previous = pd.read_csv(csv_path).fillna("")
        merge_keys = [column for column in ["ETF", "配送先", "カテゴリ", "シグナル", "推奨行動"] if column in decision_sheet.columns and column in previous.columns]
        if merge_keys:
            preserved_columns = merge_keys + [column for column in input_columns if column in previous.columns]
            decision_sheet = decision_sheet.merge(
                previous.loc[:, preserved_columns],
                on=merge_keys,
                how="left",
                suffixes=("", "_previous"),
            )
            for column in input_columns:
                previous_column = f"{column}_previous"
                if previous_column in decision_sheet.columns:
                    decision_sheet[column] = decision_sheet[previous_column].fillna(decision_sheet[column])
                    decision_sheet = decision_sheet.drop(columns=[previous_column])
    decision_sheet.to_csv(csv_path, index=False)
    content = [
        f"# manual_decision_sheet {date:%Y-%m-%d}",
        "",
        "実売買は自動実行しません。このシートにMASATOの最終判断と実行結果を記録します。",
        "",
        "判断は `buy` / `sell` / `hold` / `watch`、約定状態は `filled` / `partial` / `not_filled` を基本値として使います。",
        "",
        "入力欄: `判断`, `数量`, `指値`, `実行価格`, `実行時刻`, `約定状態`, `メモ`。判断しない行は週次PDCAとGO/HOLDで要確認になります。",
        "",
        decision_sheet.to_markdown(index=False) if not decision_sheet.empty else "判断対象なし",
        "",
        f"判断CSV: `{csv_path}`",
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_daily_health_report(
    health: pd.DataFrame,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"daily_health_{date:%Y-%m-%d}.md"
    has_missing = not health.empty and health["状態"].ne("OK").any()
    status_text = "要確認" if has_missing else "OK"
    content = [
        f"# daily_health {date:%Y-%m-%d}",
        "",
        f"判定: {status_text}",
        "",
        "日次運用に必要な成果物が揃っているかを確認します。",
        "",
        health.to_markdown(index=False) if not health.empty else "評価なし",
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_weekly_health_report(
    health: pd.DataFrame,
    output_dir: str | Path = "reports/weekly",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"weekly_health_{date:%Y-%m-%d}.md"
    has_missing = not health.empty and health["状態"].ne("OK").any()
    status_text = "要確認" if has_missing else "OK"
    content = [
        f"# weekly_health {date:%Y-%m-%d}",
        "",
        f"判定: {status_text}",
        "",
        "週次PDCAに必要な成果物が揃っているかを確認します。",
        "",
        health.to_markdown(index=False) if not health.empty else "評価なし",
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_operations_status_report(
    status: pd.DataFrame,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"operations_status_{date:%Y-%m-%d}.md"
    needs_attention = not status.empty and status["状態"].ne("OK").any()
    status_text = "要確認" if needs_attention else "OK"
    content = [
        f"# operations_status {date:%Y-%m-%d}",
        "",
        f"判定: {status_text}",
        "",
        "本運用に必要な日次・週次成果物の最新状態を確認します。",
        "",
        status.to_markdown(index=False) if not status.empty else "評価なし",
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_go_live_readiness_report(
    readiness: pd.DataFrame,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"go_live_readiness_{date:%Y-%m-%d}.md"
    has_block = not readiness.empty and readiness["状態"].eq("Block").any()
    status_text = "HOLD" if has_block else "GO（手動確認後）"
    content = [
        f"# go_live_readiness {date:%Y-%m-%d}",
        "",
        f"判定: {status_text}",
        "",
        "本運用の実行前に確認するGO/HOLD判定です。実売買は自動実行しません。",
        "",
        readiness.to_markdown(index=False) if not readiness.empty else "評価なし",
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_weekly_pdca_report(
    backtest_summary: pd.DataFrame,
    parameter_results: pd.DataFrame,
    regime_validation: pd.DataFrame,
    signal_history: pd.DataFrame | None = None,
    signal_accuracy: pd.DataFrame | None = None,
    evaluated_signals: pd.DataFrame | None = None,
    signal_improvement_proposals: list[str] | None = None,
    virtual_trades: pd.DataFrame | None = None,
    virtual_trade_summary: pd.DataFrame | None = None,
    avoid_outcomes: pd.DataFrame | None = None,
    avoid_summary: pd.DataFrame | None = None,
    avoid_policy_name: str = "current_all_avoid",
    manual_decision_summary: pd.DataFrame | None = None,
    self_check_summary: pd.DataFrame | None = None,
    output_dir: str | Path = "reports/weekly",
    processed_output_dir: str | Path = "data/processed/pdca",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"weekly_report_{date:%Y-%m-%d}.md"
    if evaluated_signals is not None and not evaluated_signals.empty:
        evaluated_path = PROJECT_ROOT / "data" / "processed" / "signals" / f"signal_forward_returns_{date:%Y-%m-%d}.csv"
        evaluated_path.parent.mkdir(parents=True, exist_ok=True)
        evaluated_signals.to_csv(evaluated_path, index=False)
    if virtual_trades is not None:
        virtual_path = PROJECT_ROOT / "data" / "processed" / "signals" / f"virtual_trades_{date:%Y-%m-%d}.csv"
        virtual_path.parent.mkdir(parents=True, exist_ok=True)
        virtual_trades.to_csv(virtual_path, index=False)
    if avoid_outcomes is not None:
        avoid_path = PROJECT_ROOT / "data" / "processed" / "signals" / f"avoid_outcomes_{date:%Y-%m-%d}.csv"
        avoid_path.parent.mkdir(parents=True, exist_ok=True)
        avoid_outcomes.to_csv(avoid_path, index=False)
    best_parameters = parameter_results.head(5) if not parameter_results.empty else pd.DataFrame()
    weak_regimes = (
        regime_validation.sort_values("vs_qqq_pct").head(3)
        if not regime_validation.empty and "vs_qqq_pct" in regime_validation.columns
        else pd.DataFrame()
    )
    action_items = []
    signal_text = "シグナル履歴なし"
    if signal_history is not None and not signal_history.empty:
        signal_counts = signal_history["判定"].value_counts().reset_index()
        signal_counts.columns = ["判定", "件数"]
        signal_text = signal_counts.to_markdown(index=False)
    accuracy_text = "判定精度データなし"
    if signal_accuracy is not None and not signal_accuracy.empty:
        accuracy_text = signal_accuracy.to_markdown(index=False)
    virtual_summary_text = "仮想売買ログなし"
    virtual_detail_text = "仮想売買ログなし"
    if virtual_trade_summary is not None and not virtual_trade_summary.empty:
        virtual_summary_text = virtual_trade_summary.to_markdown(index=False)
    if virtual_trades is not None and not virtual_trades.empty:
        virtual_detail_text = virtual_trades.tail(20).to_markdown(index=False)
    avoid_summary_text = "見送り評価ログなし"
    avoid_detail_text = "見送り評価ログなし"
    if avoid_summary is not None and not avoid_summary.empty:
        avoid_summary_text = avoid_summary.to_markdown(index=False)
    if avoid_outcomes is not None and not avoid_outcomes.empty:
        avoid_detail_text = avoid_outcomes.tail(20).to_markdown(index=False)
    manual_decision_text = "手動判断ログなし"
    if manual_decision_summary is not None and not manual_decision_summary.empty:
        manual_decision_text = manual_decision_summary.to_markdown(index=False)
    self_check_text = "自己確認ログなし"
    if self_check_summary is not None and not self_check_summary.empty:
        self_check_text = self_check_summary.to_markdown(index=False)
    if not best_parameters.empty:
        best = best_parameters.iloc[0]
        action_items.append(
            f"暫定候補は {best.get('score_profile', 'balanced')} / Satellite {float(best['satellite_weight_pct']):.0f}% / "
            f"上位{int(best['top_satellites'])} / DD停止 {float(best['drawdown_stop_pct']):.0f}%"
        )
    if not weak_regimes.empty:
        action_items.append("弱点局面のETF採用ログを確認し、半導体/AIの取り逃がし原因を継続監査")
    if backtest_summary.empty:
        action_items.append("バックテストサマリー未作成。`python -m src.main backtest` を実行")
    if signal_improvement_proposals:
        action_items.extend(signal_improvement_proposals)
    processed_directory = ensure_dir(processed_output_dir)
    action_path = processed_directory / f"weekly_action_items_{date:%Y-%m-%d}.csv"
    previous_action_files = [
        path
        for path in sorted(processed_directory.glob("weekly_action_items_*.csv"))
        if path.name != action_path.name
    ]
    previous_action_text = "前回Act項目なし"
    if previous_action_files:
        previous_actions = pd.read_csv(previous_action_files[-1])
        if "status" in previous_actions.columns:
            open_actions = previous_actions[
                ~previous_actions["status"].astype(str).str.lower().isin(["done", "closed"])
            ]
        else:
            open_actions = previous_actions
        previous_action_text = open_actions.to_markdown(index=False) if not open_actions.empty else "未完了Act項目なし"
    action_table = pd.DataFrame(
        [
            {
                "report_date": f"{date:%Y-%m-%d}",
                "item_id": index,
                "status": "open",
                "source": "weekly_pdca",
                "action_item": item,
            }
            for index, item in enumerate(action_items, start=1)
        ],
        columns=["report_date", "item_id", "status", "source", "action_item"],
    )
    action_table.to_csv(action_path, index=False)
    content = [
        f"# weekly_report {date:%Y-%m-%d}",
        "",
        "## 1. 今週の判定精度",
        "売買実績CSV未連携のため損益精度は未評価です。現段階ではシグナル分布を記録します。",
        "",
        signal_text,
        "",
        "### フォワードリターン評価",
        accuracy_text,
        "",
        "### 仮想売買ログ",
        virtual_summary_text,
        "",
        virtual_detail_text,
        "",
        "### 見送り・リスク削減の評価",
        f"現在の回避評価方針: `{avoid_policy_name}`",
        "",
        avoid_summary_text,
        "",
        avoid_detail_text,
        "",
        "### 手動判断ログ",
        manual_decision_text,
        "",
        "### 自己確認ログ",
        self_check_text,
        "",
        "## 2. ベンチマーク比較",
        backtest_summary.to_markdown(index=False) if not backtest_summary.empty else "バックテストサマリーなし",
        "",
        "## 3. 保有ETFの評価",
        "日次レポートの保有ETF評価セクションを参照してください。",
        "",
        "## 4. 来週の買い候補",
        "日次レポートの買い候補・押し目待ちを優先確認してください。",
        "",
        "## 5. 来週の売却候補",
        "日次レポートの売却候補と通知候補を優先確認してください。",
        "",
        "## 6. 改善提案",
        best_parameters.to_markdown(index=False) if not best_parameters.empty else "改善パラメータ結果なし",
        "",
        "## 7. バックテスト更新",
        "最新の10年バックテスト、総当たり、局面別検証を反映済みです。",
        "",
        "## PDCA: Act",
        *[f"- {item}" for item in action_items],
        "",
        f"Act項目CSV: `{action_path}`",
        "",
        "## 前回Act確認",
        previous_action_text,
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_replay_pdca_report(
    signal_history: pd.DataFrame,
    signal_accuracy: pd.DataFrame,
    virtual_trades: pd.DataFrame,
    virtual_trade_summary: pd.DataFrame,
    avoid_outcomes: pd.DataFrame,
    avoid_summary: pd.DataFrame,
    entry_parameter_results: pd.DataFrame | None = None,
    avoid_by_signal: pd.DataFrame | None = None,
    avoid_policy_results: pd.DataFrame | None = None,
    signal_execution_summary: pd.DataFrame | None = None,
    signal_execution_diagnostics: pd.DataFrame | None = None,
    signal_execution_grid: pd.DataFrame | None = None,
    hybrid_summary: pd.DataFrame | None = None,
    hybrid_diagnostics: pd.DataFrame | None = None,
    hybrid_grid: pd.DataFrame | None = None,
    hybrid_regime_validation: pd.DataFrame | None = None,
    hybrid_entry_guard_results: pd.DataFrame | None = None,
    hybrid_acceleration_mode_results: pd.DataFrame | None = None,
    hybrid_ticker_rule_results: pd.DataFrame | None = None,
    hybrid_theme_risk_mode_results: pd.DataFrame | None = None,
    theme_risk_overlay_comparison: pd.DataFrame | None = None,
    relaxed_theme_risk_overlay_comparison: pd.DataFrame | None = None,
    theme_risk_policy_mode_results: pd.DataFrame | None = None,
    theme_risk_overlay_blocks: pd.DataFrame | None = None,
    relaxed_theme_risk_overlay_blocks: pd.DataFrame | None = None,
    hybrid_trade_log: pd.DataFrame | None = None,
    hybrid_attribution_2024: pd.DataFrame | None = None,
    trade_plan_multipliers: dict[str, float] | None = None,
    avoid_policy_name: str = "current_all_avoid",
    action_label_history: pd.DataFrame | None = None,
    output_dir: str | Path = "reports/weekly",
    processed_output_dir: str | Path | None = None,
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"replay_pdca_report_{date:%Y-%m-%d}.md"
    processed_dir = ensure_dir(processed_output_dir or "data/processed/signals")
    signal_path = processed_dir / f"historical_signals_{date:%Y-%m-%d}.csv"
    forward_path = processed_dir / f"replay_signal_accuracy_{date:%Y-%m-%d}.csv"
    virtual_path = processed_dir / f"replay_virtual_trades_{date:%Y-%m-%d}.csv"
    avoid_path = processed_dir / f"replay_avoid_outcomes_{date:%Y-%m-%d}.csv"
    entry_search_path = processed_dir / f"replay_entry_parameter_search_{date:%Y-%m-%d}.csv"
    avoid_by_signal_path = processed_dir / f"replay_avoid_by_signal_{date:%Y-%m-%d}.csv"
    avoid_policy_path = processed_dir / f"replay_avoid_policy_search_{date:%Y-%m-%d}.csv"
    signal_execution_path = processed_dir / f"signal_execution_backtest_{date:%Y-%m-%d}.csv"
    signal_execution_diag_path = processed_dir / f"signal_execution_diagnostics_{date:%Y-%m-%d}.csv"
    signal_execution_grid_path = processed_dir / f"signal_execution_grid_{date:%Y-%m-%d}.csv"
    hybrid_path = processed_dir / f"hybrid_rotation_signal_backtest_{date:%Y-%m-%d}.csv"
    hybrid_diag_path = processed_dir / f"hybrid_rotation_signal_diagnostics_{date:%Y-%m-%d}.csv"
    hybrid_grid_path = processed_dir / f"hybrid_rotation_signal_grid_{date:%Y-%m-%d}.csv"
    hybrid_regime_path = processed_dir / f"hybrid_rotation_signal_regime_validation_{date:%Y-%m-%d}.csv"
    hybrid_entry_guard_path = processed_dir / f"hybrid_entry_guard_search_{date:%Y-%m-%d}.csv"
    hybrid_acceleration_mode_path = processed_dir / f"hybrid_acceleration_mode_search_{date:%Y-%m-%d}.csv"
    hybrid_ticker_rule_path = processed_dir / f"hybrid_ticker_rule_search_{date:%Y-%m-%d}.csv"
    hybrid_theme_risk_mode_path = processed_dir / f"hybrid_theme_risk_mode_search_{date:%Y-%m-%d}.csv"
    theme_risk_overlay_path = processed_dir / f"theme_risk_overlay_comparison_{date:%Y-%m-%d}.csv"
    relaxed_theme_risk_overlay_path = processed_dir / f"relaxed_theme_risk_overlay_comparison_{date:%Y-%m-%d}.csv"
    theme_risk_policy_mode_path = processed_dir / f"theme_risk_policy_mode_search_{date:%Y-%m-%d}.csv"
    theme_risk_blocks_path = processed_dir / f"theme_risk_overlay_blocks_{date:%Y-%m-%d}.csv"
    relaxed_theme_risk_blocks_path = processed_dir / f"relaxed_theme_risk_overlay_blocks_{date:%Y-%m-%d}.csv"
    hybrid_trade_log_path = processed_dir / f"hybrid_trade_log_{date:%Y-%m-%d}.csv"
    hybrid_attribution_2024_path = processed_dir / f"hybrid_attribution_2024_{date:%Y-%m-%d}.csv"
    action_label_history_path = processed_dir / f"action_label_history_{date:%Y-%m-%d}.csv"
    signal_history.to_csv(signal_path, index=False)
    signal_accuracy.to_csv(forward_path, index=False)
    virtual_trades.to_csv(virtual_path, index=False)
    avoid_outcomes.to_csv(avoid_path, index=False)
    if entry_parameter_results is not None:
        entry_parameter_results.to_csv(entry_search_path, index=False)
    if avoid_by_signal is not None:
        avoid_by_signal.to_csv(avoid_by_signal_path, index=False)
    if avoid_policy_results is not None:
        avoid_policy_results.to_csv(avoid_policy_path, index=False)
    if signal_execution_summary is not None:
        signal_execution_summary.to_csv(signal_execution_path, index=False)
    if signal_execution_diagnostics is not None:
        signal_execution_diagnostics.to_csv(signal_execution_diag_path, index=False)
    if signal_execution_grid is not None:
        signal_execution_grid.to_csv(signal_execution_grid_path, index=False)
    if hybrid_summary is not None:
        hybrid_summary.to_csv(hybrid_path, index=False)
    if hybrid_diagnostics is not None:
        hybrid_diagnostics.to_csv(hybrid_diag_path, index=False)
    if hybrid_grid is not None:
        hybrid_grid.to_csv(hybrid_grid_path, index=False)
    if hybrid_regime_validation is not None:
        hybrid_regime_validation.to_csv(hybrid_regime_path, index=False)
    if hybrid_entry_guard_results is not None:
        hybrid_entry_guard_results.to_csv(hybrid_entry_guard_path, index=False)
    if hybrid_acceleration_mode_results is not None:
        hybrid_acceleration_mode_results.to_csv(hybrid_acceleration_mode_path, index=False)
    if hybrid_ticker_rule_results is not None:
        hybrid_ticker_rule_results.to_csv(hybrid_ticker_rule_path, index=False)
    if hybrid_theme_risk_mode_results is not None:
        hybrid_theme_risk_mode_results.to_csv(hybrid_theme_risk_mode_path, index=False)
    if theme_risk_overlay_comparison is not None:
        theme_risk_overlay_comparison.to_csv(theme_risk_overlay_path, index=False)
    if relaxed_theme_risk_overlay_comparison is not None:
        relaxed_theme_risk_overlay_comparison.to_csv(relaxed_theme_risk_overlay_path, index=False)
    if theme_risk_policy_mode_results is not None:
        theme_risk_policy_mode_results.to_csv(theme_risk_policy_mode_path, index=False)
    if theme_risk_overlay_blocks is not None:
        theme_risk_overlay_blocks.to_csv(theme_risk_blocks_path, index=False)
    if relaxed_theme_risk_overlay_blocks is not None:
        relaxed_theme_risk_overlay_blocks.to_csv(relaxed_theme_risk_blocks_path, index=False)
    if hybrid_trade_log is not None:
        hybrid_trade_log.to_csv(hybrid_trade_log_path, index=False)
    if hybrid_attribution_2024 is not None:
        hybrid_attribution_2024.to_csv(hybrid_attribution_2024_path, index=False)
    if action_label_history is not None:
        action_label_history.to_csv(action_label_history_path, index=False)

    trade_plan_settings = trade_plan_multipliers or {
        "entry_multiplier": 1.0,
        "stop_multiplier": 1.0,
        "target_multiplier": 1.0,
    }
    trade_plan_settings_text = "\n".join(
        [
            f"- 第1買い倍率: x{float(trade_plan_settings.get('entry_multiplier', 1.0)):.2f}",
            f"- 停止価格倍率: x{float(trade_plan_settings.get('stop_multiplier', 1.0)):.2f}",
            f"- 目標価格倍率: x{float(trade_plan_settings.get('target_multiplier', 1.0)):.2f}",
            "- 買い価格・停止価格の総当たりは、上記設定反映後の価格に対する追加検証倍率です。",
        ]
    )

    signal_counts = "履歴シグナルなし"
    theme_risk_signal_counts = "テーマリスク列なし"
    if not signal_history.empty:
        counts = signal_history["判定"].value_counts().reset_index()
        counts.columns = ["判定", "件数"]
        signal_counts = counts.to_markdown(index=False)
        if {"テーマリスク", "判定"}.issubset(signal_history.columns):
            risk_counts = (
                signal_history.groupby(["テーマリスク", "判定"])
                .size()
                .reset_index(name="件数")
                .sort_values(["テーマリスク", "件数"], ascending=[True, False])
            )
            theme_risk_signal_counts = risk_counts.to_markdown(index=False)
    action_items: list[str] = []
    if not virtual_trade_summary.empty:
        summary_row = virtual_trade_summary.iloc[0]
        filled = float(summary_row.get("約定件数", 0.0) or 0.0)
        total = float(summary_row.get("対象件数", 0.0) or 0.0)
        average_return = summary_row.get("平均損益%", None)
        fill_rate = filled / total * 100 if total > 0 else 0.0
        if pd.notna(average_return) and float(average_return) < 0:
            action_items.append("買い系シグナルの仮想損益がマイナス。第1買い条件、停止価格、目標価格を次回パラメータ検証で再調整")
        if total > 0 and fill_rate < 40:
            action_items.append("第1買い未到達が多い。押し目待ち価格が深すぎないか、約定率とリスクのバランスを検証")
    if not avoid_summary.empty:
        avoid_row = avoid_summary.iloc[0]
        accuracy = avoid_row.get("正解率", None)
        average_avoid_return = avoid_row.get("平均20日後リターン%", None)
        if pd.notna(accuracy) and float(accuracy) < 50:
            action_items.append("見送り・売却候補の正解率が50%未満。上昇局面では売却候補を即売りではなく監視/リスク削減に弱める案を検証")
        if pd.notna(average_avoid_return) and float(average_avoid_return) > 0:
            action_items.append("回避後の平均リターンがプラス。過熱控除とテーマスコア60割れの売却判定が強すぎないか確認")
    if not action_items:
        action_items.append("履歴再生では大きな偏りなし。日次シグナル蓄積と週次評価を継続")
    if entry_parameter_results is not None and not entry_parameter_results.empty:
        best = entry_parameter_results.iloc[0]
        action_items.append(
            f"買い価格追加検証候補: 第1買いx{float(best['entry_multiplier']):.2f} / 停止価格x{float(best['stop_multiplier']):.2f} を次回バックテスト候補に追加"
        )
    if avoid_policy_results is not None and not avoid_policy_results.empty:
        best_policy = avoid_policy_results.iloc[0]
        action_items.append(f"回避方針候補: {best_policy['policy']} を売却/見送りルール検証候補に追加")
    if signal_execution_summary is not None and not signal_execution_summary.empty:
        signal_row = signal_execution_summary[signal_execution_summary["strategy"].eq("MASATO Signal Execution")]
        if not signal_row.empty:
            signal_annual = float(signal_row.iloc[0]["annual_return_pct"])
            action_items.append(f"シグナル実行BT: 年率{signal_annual:.2f}% を確認。月次ローテーション本体との統合可否を次回検証")
    if signal_execution_grid is not None and not signal_execution_grid.empty:
        best_signal = signal_execution_grid.iloc[0]
        action_items.append(
            f"補助シグナル候補: entry x{float(best_signal['entry_multiplier']):.2f} / stop x{float(best_signal['stop_multiplier']):.2f} / 保有{int(best_signal['max_holding_days'])}日 / {int(best_signal['max_positions'])}枠"
        )
    if hybrid_summary is not None and not hybrid_summary.empty:
        hybrid_row = hybrid_summary[hybrid_summary["strategy"].eq("MASATO Hybrid Rotation+Signal")]
        if not hybrid_row.empty:
            hybrid_annual = float(hybrid_row.iloc[0]["annual_return_pct"])
            action_items.append(f"ハイブリッドBT: 年率{hybrid_annual:.2f}% を確認。現行月次ローテーションとの優劣を比較")
    if hybrid_grid is not None and not hybrid_grid.empty:
        best_hybrid = hybrid_grid.iloc[0]
        min_etf_score = best_hybrid.get("min_etf_score", best_hybrid.get("min_score", 0.0))
        min_theme_score = best_hybrid.get("min_theme_score", best_hybrid.get("min_score", 0.0))
        action_items.append(
            f"ハイブリッド候補: {best_hybrid.get('candidate_policy', 'strict_buy')} / 加速局面{best_hybrid.get('acceleration_overlay_mode', 'normal')} / 補助枠{float(best_hybrid['signal_overlay_weight_pct']):.0f}% / entry x{float(best_hybrid['entry_multiplier']):.2f} / stop x{float(best_hybrid['stop_multiplier']):.2f} / 保有{int(best_hybrid['max_holding_days'])}日 / {int(best_hybrid['max_signal_positions'])}枠 / ETF{float(min_etf_score):.0f}+ テーマ{float(min_theme_score):.0f}+ RR{float(best_hybrid.get('min_rr', 0.0)):.1f}+"
        )
    if hybrid_regime_validation is not None and not hybrid_regime_validation.empty:
        weak_hybrid = hybrid_regime_validation.sort_values("vs_rotation_pct").head(1).iloc[0]
        action_items.append(
            f"ハイブリッド局面別: 最弱局面は{weak_hybrid['regime']}、現行比{float(weak_hybrid['vs_rotation_pct']):.2f}%"
        )
    if hybrid_entry_guard_results is not None and not hybrid_entry_guard_results.empty:
        best_guard = hybrid_entry_guard_results.iloc[0]
        best_guard_loss = float(best_guard["max_entry_day_loss_pct"])
        if best_guard_loss <= -99:
            action_items.append("急落日ガード: 成績改善なし。現時点では採用不要")
        else:
            action_items.append(f"急落日ガード候補: 当日下落{best_guard_loss:.0f}%以下の即エントリー禁止")
    if hybrid_acceleration_mode_results is not None and not hybrid_acceleration_mode_results.empty:
        best_acceleration_mode = hybrid_acceleration_mode_results.iloc[0]
        action_items.append(
            f"加速局面モード候補: {best_acceleration_mode['acceleration_overlay_mode']} / 年率{float(best_acceleration_mode['annual_return_pct']):.2f}%"
        )
    if hybrid_ticker_rule_results is not None and not hybrid_ticker_rule_results.empty:
        best_ticker_rule = hybrid_ticker_rule_results.iloc[0]
        relaxed_tickers = str(best_ticker_rule.get("relaxed_signal_tickers", "") or "")
        relaxed_text = ""
        if relaxed_tickers:
            relaxed_text = (
                f" / 限定緩和{relaxed_tickers} "
                f"ETF{float(best_ticker_rule.get('relaxed_min_etf_score', 0.0)):.0f}+"
                f" テーマ{float(best_ticker_rule.get('relaxed_min_theme_score', 0.0)):.0f}+"
                f" RR{float(best_ticker_rule.get('relaxed_min_rr', 0.0)):.1f}+"
            )
        action_items.append(
            f"ハイブリッドETF別制限候補: {best_ticker_rule['rule_name']} / 年率{float(best_ticker_rule['annual_return_pct']):.2f}% / URA補助{int(best_ticker_rule['ura_signal_trade_count'])}件{relaxed_text}"
        )
    if hybrid_theme_risk_mode_results is not None and not hybrid_theme_risk_mode_results.empty:
        best_hybrid_theme_risk_mode = hybrid_theme_risk_mode_results.iloc[0]
        action_items.append(
            f"ハイブリッド本体テーマリスクモード候補: {best_hybrid_theme_risk_mode['theme_risk_mode']} / 年率{float(best_hybrid_theme_risk_mode['annual_return_pct']):.2f}% / DD{float(best_hybrid_theme_risk_mode['max_drawdown_pct']):.2f}%"
        )
    if theme_risk_overlay_comparison is not None and not theme_risk_overlay_comparison.empty:
        buy_row = theme_risk_overlay_comparison[theme_risk_overlay_comparison["指標"].eq("買い系シグナル数")]
        return_row = theme_risk_overlay_comparison[theme_risk_overlay_comparison["指標"].eq("仮想売買 平均リターン%")]
        if not buy_row.empty and not return_row.empty:
            action_items.append(
                f"テーマリスク抑制: 買い系{int(buy_row.iloc[0]['リスク抑制なし'])}件→{int(buy_row.iloc[0]['リスク抑制あり'])}件 / 仮想平均{float(return_row.iloc[0]['リスク抑制あり']):.2f}%"
            )
    if relaxed_theme_risk_overlay_comparison is not None and not relaxed_theme_risk_overlay_comparison.empty:
        relaxed_buy_row = relaxed_theme_risk_overlay_comparison[
            relaxed_theme_risk_overlay_comparison["指標"].eq("買い系シグナル数")
        ]
        if not relaxed_buy_row.empty:
            action_items.append(
                f"緩和条件ストレス: 買い系{int(relaxed_buy_row.iloc[0]['リスク抑制なし'])}件→{int(relaxed_buy_row.iloc[0]['リスク抑制あり'])}件"
            )
    if theme_risk_policy_mode_results is not None and not theme_risk_policy_mode_results.empty:
        best_theme_risk_mode = theme_risk_policy_mode_results.iloc[0]
        action_items.append(
            f"テーマリスク防御モード候補: {best_theme_risk_mode['mode']} / 仮想平均{float(best_theme_risk_mode['仮想売買 平均リターン%']):.2f}% / ブロック{int(best_theme_risk_mode['ブロック/弱化件数'])}件"
        )
    if relaxed_theme_risk_overlay_blocks is not None and not relaxed_theme_risk_overlay_blocks.empty:
        action_items.append(f"緩和条件でテーマリスク抑制が{len(relaxed_theme_risk_overlay_blocks)}件の判定を弱めた")
    if hybrid_attribution_2024 is not None and not hybrid_attribution_2024.empty:
        worst_etf = hybrid_attribution_2024.iloc[0]
        action_items.append(
            f"2024補助ETF要因: 最弱は{worst_etf['ETF']}、合計{float(worst_etf['total_return_pct']):.2f}%"
        )

    content = [
        f"# 履歴再生PDCA {date:%Y-%m-%d}",
        "",
        "過去データ上で日次判定を月次復元し、仮想売買と見送り評価を再計算します。実売買発注は行いません。",
        "",
        "## 売買計画設定",
        trade_plan_settings_text,
        "",
        "## 回避評価方針",
        f"- 現在の回避評価方針: `{avoid_policy_name}`",
        "- `sell_only` の場合、見送りは監視扱いに寄せ、売却候補だけを回避成否評価の主対象にします。",
        "",
        "## シグナル分布",
        signal_counts,
        "",
        "## テーマリスク別シグナル分布",
        theme_risk_signal_counts,
        "",
        "## テーマリスク抑制 有無比較",
        theme_risk_overlay_comparison.to_markdown(index=False)
        if theme_risk_overlay_comparison is not None and not theme_risk_overlay_comparison.empty
        else "評価なし",
        "",
        "## 緩和条件ストレス テーマリスク抑制比較",
        relaxed_theme_risk_overlay_comparison.to_markdown(index=False)
        if relaxed_theme_risk_overlay_comparison is not None and not relaxed_theme_risk_overlay_comparison.empty
        else "評価なし",
        "",
        "## テーマリスク防御モード 総当たり",
        theme_risk_policy_mode_results.to_markdown(index=False)
        if theme_risk_policy_mode_results is not None and not theme_risk_policy_mode_results.empty
        else "評価なし",
        "",
        "## テーマリスク抑制 ブロック監査",
        theme_risk_overlay_blocks.head(20).to_markdown(index=False)
        if theme_risk_overlay_blocks is not None and not theme_risk_overlay_blocks.empty
        else "通常条件ではブロックなし",
        "",
        "## 緩和条件ストレス ブロック監査",
        relaxed_theme_risk_overlay_blocks.head(20).to_markdown(index=False)
        if relaxed_theme_risk_overlay_blocks is not None and not relaxed_theme_risk_overlay_blocks.empty
        else "緩和条件でもブロックなし",
        "",
        "## フォワードリターン評価",
        signal_accuracy.to_markdown(index=False) if not signal_accuracy.empty else "評価なし",
        "",
        "## LINE行動ラベル別の過去検証",
        action_label_history.to_markdown(index=False)
        if action_label_history is not None and not action_label_history.empty
        else "評価なし",
        "",
        "## 仮想売買サマリー",
        virtual_trade_summary.to_markdown(index=False) if not virtual_trade_summary.empty else "評価なし",
        "",
        "## 見送り・リスク削減サマリー",
        avoid_summary.to_markdown(index=False) if not avoid_summary.empty else "評価なし",
        "",
        "## 買い価格・停止価格 総当たり",
        entry_parameter_results.head(10).to_markdown(index=False)
        if entry_parameter_results is not None and not entry_parameter_results.empty
        else "評価なし",
        "",
        "## 見送り・売却候補 判定別評価",
        avoid_by_signal.to_markdown(index=False) if avoid_by_signal is not None and not avoid_by_signal.empty else "評価なし",
        "",
        "## 回避方針 総当たり",
        avoid_policy_results.to_markdown(index=False)
        if avoid_policy_results is not None and not avoid_policy_results.empty
        else "評価なし",
        "",
        "## シグナル実行バックテスト",
        signal_execution_summary.to_markdown(index=False)
        if signal_execution_summary is not None and not signal_execution_summary.empty
        else "評価なし",
        "",
        "## シグナル実行 診断",
        signal_execution_diagnostics.to_markdown(index=False)
        if signal_execution_diagnostics is not None and not signal_execution_diagnostics.empty
        else "診断なし",
        "",
        "## シグナル実行 総当たり",
        signal_execution_grid.head(10).to_markdown(index=False)
        if signal_execution_grid is not None and not signal_execution_grid.empty
        else "評価なし",
        "",
        "## ハイブリッド 月次ローテーション+補助シグナル",
        hybrid_summary.to_markdown(index=False)
        if hybrid_summary is not None and not hybrid_summary.empty
        else "評価なし",
        "",
        "## ハイブリッド 診断",
        hybrid_diagnostics.to_markdown(index=False)
        if hybrid_diagnostics is not None and not hybrid_diagnostics.empty
        else "診断なし",
        "",
        "## ハイブリッド 総当たり",
        hybrid_grid.head(10).to_markdown(index=False)
        if hybrid_grid is not None and not hybrid_grid.empty
        else "評価なし",
        "",
        "## ハイブリッド 局面別検証",
        hybrid_regime_validation.to_markdown(index=False)
        if hybrid_regime_validation is not None and not hybrid_regime_validation.empty
        else "評価なし",
        "",
        "## ハイブリッド 急落日ガード検証",
        hybrid_entry_guard_results.to_markdown(index=False)
        if hybrid_entry_guard_results is not None and not hybrid_entry_guard_results.empty
        else "評価なし",
        "",
        "## ハイブリッド 加速局面モード検証",
        hybrid_acceleration_mode_results.to_markdown(index=False)
        if hybrid_acceleration_mode_results is not None and not hybrid_acceleration_mode_results.empty
        else "評価なし",
        "",
        "## ハイブリッド ETF別補助エントリー制限検証",
        hybrid_ticker_rule_results.to_markdown(index=False)
        if hybrid_ticker_rule_results is not None and not hybrid_ticker_rule_results.empty
        else "評価なし",
        "",
        "## ハイブリッド テーマリスクモード検証",
        hybrid_theme_risk_mode_results.to_markdown(index=False)
        if hybrid_theme_risk_mode_results is not None and not hybrid_theme_risk_mode_results.empty
        else "評価なし",
        "",
        "## ハイブリッド 2024 ETF別要因",
        hybrid_attribution_2024.to_markdown(index=False)
        if hybrid_attribution_2024 is not None and not hybrid_attribution_2024.empty
        else "評価なし",
        "",
        "## ハイブリッド 取引ログ",
        hybrid_trade_log.to_markdown(index=False)
        if hybrid_trade_log is not None and not hybrid_trade_log.empty
        else "ログなし",
        "",
        "## 仮想売買ログ 直近20件",
        virtual_trades.tail(20).to_markdown(index=False) if not virtual_trades.empty else "ログなし",
        "",
        "## 見送り評価ログ 直近20件",
        avoid_outcomes.tail(20).to_markdown(index=False) if not avoid_outcomes.empty else "ログなし",
        "",
        "## PDCA: Act",
        *[f"- {item}" for item in action_items],
        "",
        "## 出力ファイル",
        f"- 履歴シグナルCSV: `{signal_path}`",
        f"- 判定精度CSV: `{forward_path}`",
        f"- 仮想売買CSV: `{virtual_path}`",
        f"- 見送り評価CSV: `{avoid_path}`",
        f"- 買い価格総当たりCSV: `{entry_search_path}`",
        f"- 見送り判定別CSV: `{avoid_by_signal_path}`",
        f"- 回避方針総当たりCSV: `{avoid_policy_path}`",
        f"- シグナル実行BT CSV: `{signal_execution_path}`",
        f"- シグナル実行診断CSV: `{signal_execution_diag_path}`",
        f"- シグナル実行総当たりCSV: `{signal_execution_grid_path}`",
        f"- ハイブリッドBT CSV: `{hybrid_path}`",
        f"- ハイブリッド診断CSV: `{hybrid_diag_path}`",
        f"- ハイブリッド総当たりCSV: `{hybrid_grid_path}`",
        f"- ハイブリッド局面別CSV: `{hybrid_regime_path}`",
        f"- ハイブリッド急落日ガードCSV: `{hybrid_entry_guard_path}`",
        f"- ハイブリッド加速局面モードCSV: `{hybrid_acceleration_mode_path}`",
        f"- ハイブリッドETF別補助制限CSV: `{hybrid_ticker_rule_path}`",
        f"- ハイブリッドテーマリスクモードCSV: `{hybrid_theme_risk_mode_path}`",
        f"- テーマリスク抑制比較CSV: `{theme_risk_overlay_path}`",
        f"- 緩和条件テーマリスク抑制比較CSV: `{relaxed_theme_risk_overlay_path}`",
        f"- テーマリスク防御モード総当たりCSV: `{theme_risk_policy_mode_path}`",
        f"- テーマリスク抑制ブロック監査CSV: `{theme_risk_blocks_path}`",
        f"- 緩和条件テーマリスク抑制ブロック監査CSV: `{relaxed_theme_risk_blocks_path}`",
        f"- ハイブリッド取引ログCSV: `{hybrid_trade_log_path}`",
        f"- ハイブリッド2024 ETF別要因CSV: `{hybrid_attribution_2024_path}`",
        f"- LINE行動ラベル別検証CSV: `{action_label_history_path}`",
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_backtest_report(
    summary: pd.DataFrame,
    diagnostics: pd.DataFrame,
    strategy_curve: pd.Series,
    config_label: str = "default",
    output_dir: str | Path = "reports/weekly",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    report_path = PROJECT_ROOT / directory / f"backtest_report_{date:%Y-%m-%d}.md"
    summary_csv = PROJECT_ROOT / "data" / "backtest" / f"backtest_summary_{date:%Y-%m-%d}.csv"
    curve_csv = PROJECT_ROOT / "data" / "backtest" / f"equity_curve_{date:%Y-%m-%d}.csv"
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_csv, index=False)
    strategy_curve.to_frame("equity").to_csv(curve_csv)
    best_benchmark = summary[summary["strategy"] != "MASATO Rotation"].sort_values(
        "annual_return_pct",
        ascending=False,
    ).head(1)
    masato = summary[summary["strategy"] == "MASATO Rotation"].iloc[0]
    benchmark_text = "比較対象なし"
    if not best_benchmark.empty:
        best = best_benchmark.iloc[0]
        diff = float(masato["annual_return_pct"]) - float(best["annual_return_pct"])
        benchmark_text = (
            f"最強ベンチマークは {best['strategy']}。"
            f"年率差は {diff:.2f}% です。"
        )
    pdca_actions = []
    if float(masato["max_drawdown_pct"]) <= -12:
        pdca_actions.append("DDが大きいため、Satellite比率またはDD停止条件の再検証")
    if not best_benchmark.empty and float(masato["annual_return_pct"]) < float(best_benchmark.iloc[0]["annual_return_pct"]):
        pdca_actions.append("ベンチマーク未達のため、テーマ選定スコアとリバランス頻度の再検証")
    if not pdca_actions:
        pdca_actions.append("現行ルールを維持し、候補ETFの拡張だけを次回検証")
    content = [
        f"# 10年バックテストレポート {date:%Y-%m-%d}",
        "",
        "## 検証ルール",
        f"- 使用プロファイル: {config_label}",
        "- 実売買発注なし。研究用シミュレーションです。",
        "",
        "## ベンチマーク比較",
        summary.to_markdown(index=False),
        "",
        "## 判定",
        benchmark_text,
        "",
        "## 診断",
        diagnostics.to_markdown(index=False),
        "",
        "## PDCA: Check",
        f"- 年率リターン: {float(masato['annual_return_pct']):.2f}%",
        f"- 累積リターン: {float(masato['cumulative_return_pct']):.2f}%",
        f"- 最大DD: {float(masato['max_drawdown_pct']):.2f}%",
        f"- シャープレシオ: {float(masato['sharpe_ratio']):.2f}",
        "",
        "## PDCA: Act",
        *[f"- {item}" for item in pdca_actions],
        "",
        "## 出力ファイル",
        f"- サマリーCSV: `{summary_csv}`",
        f"- エクイティカーブCSV: `{curve_csv}`",
    ]
    report_path.write_text("\n".join(content), encoding="utf-8")
    return report_path


def write_parameter_search_report(
    grid_results: pd.DataFrame,
    baseline_summary: pd.DataFrame,
    output_dir: str | Path = "reports/weekly",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    report_path = PROJECT_ROOT / directory / f"parameter_search_report_{date:%Y-%m-%d}.md"
    csv_path = PROJECT_ROOT / "data" / "backtest" / f"parameter_search_{date:%Y-%m-%d}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    grid_results.to_csv(csv_path, index=False)
    top_results = grid_results.head(10)
    best = grid_results.iloc[0]
    baseline = baseline_summary[baseline_summary["strategy"] == "MASATO Rotation"].iloc[0]
    annual_diff = float(best["annual_return_pct"]) - float(baseline["annual_return_pct"])
    dd_diff = float(best["max_drawdown_pct"]) - float(baseline["max_drawdown_pct"])
    calmar_diff = float(best["calmar_ratio"]) - float(baseline["calmar_ratio"])
    recommended_actions = [
        (
            f"Satellite比率を {float(best['satellite_weight_pct']):.0f}%、"
            f"上位ETF数を {int(best['top_satellites'])}、"
            f"リバランスを {best['rebalance_frequency']}、"
            f"DD停止を {float(best['drawdown_stop_pct']):.0f}%、"
            f"最低スコアを {float(best['min_satellite_score']):.0f}、"
            f"スコアを {best.get('score_profile', 'balanced')} にしたルールを候補にする"
        )
    ]
    if annual_diff > 0 and dd_diff >= -3:
        recommended_actions.append("リターン改善があり、DD悪化も限定的なので次回はこの候補を詳細バックテスト")
    elif annual_diff > 0:
        recommended_actions.append("リターンは改善。ただしDD悪化を許容できるか、保有上限と停止条件を追加検証")
    else:
        recommended_actions.append("現行ルールから大きく変えず、ETFユニバースやスコア重みの改善を優先")
    content = [
        f"# 改善パラメータ総当たりPDCA {date:%Y-%m-%d}",
        "",
        "## Plan",
        "- Satellite比率、上位ETF数、リバランス頻度、DD停止ライン、最低スコアを総当たり検証",
        "- 評価は年率リターンだけでなく、最大DD、Sharpe、Calmarを含める",
        "- 実売買発注なし。研究用検証です。",
        "",
        "## Do",
        f"- 検証本数: {len(grid_results)}",
        "- ベースライン: Core SPY 30% / QQQ 30% / Satellite 25% / Cash 15%、月次、上位3ETF、DD -8%",
        "",
        "## Check: 上位10設定",
        top_results.to_markdown(index=False),
        "",
        "## Check: ベースラインとの差",
        f"- ベースライン年率: {float(baseline['annual_return_pct']):.2f}%",
        f"- 最良設定年率: {float(best['annual_return_pct']):.2f}%",
        f"- 年率差: {annual_diff:.2f}%",
        f"- ベースライン最大DD: {float(baseline['max_drawdown_pct']):.2f}%",
        f"- 最良設定最大DD: {float(best['max_drawdown_pct']):.2f}%",
        f"- DD差: {dd_diff:.2f}%",
        f"- Calmar差: {calmar_diff:.2f}",
        "",
        "## Act",
        *[f"- {item}" for item in recommended_actions],
        "",
        "## 出力ファイル",
        f"- 総当たりCSV: `{csv_path}`",
    ]
    report_path.write_text("\n".join(content), encoding="utf-8")
    return report_path


def write_regime_validation_report(
    validation: pd.DataFrame,
    config_label: str,
    output_dir: str | Path = "reports/weekly",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    report_path = PROJECT_ROOT / directory / f"regime_validation_report_{date:%Y-%m-%d}.md"
    csv_path = PROJECT_ROOT / "data" / "backtest" / f"regime_validation_{date:%Y-%m-%d}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    validation.to_csv(csv_path, index=False)
    wins_spy = int((validation["vs_spy_pct"] > 0).sum()) if not validation.empty else 0
    wins_qqq = int((validation["vs_qqq_pct"] > 0).sum()) if not validation.empty else 0
    wins_smh = int((validation["vs_smh_pct"] > 0).sum()) if not validation.empty else 0
    weak_rows = validation.sort_values("vs_qqq_pct").head(2) if not validation.empty else pd.DataFrame()
    act_items = []
    if wins_qqq < max(1, len(validation) // 2):
        act_items.append("QQQに負ける局面が多いため、AI/半導体の加速期はモメンタム重みを強める別モードを検証")
    if not weak_rows.empty:
        weak_names = "、".join(str(item) for item in weak_rows["regime"].tolist())
        act_items.append(f"弱点局面は {weak_names}。この期間の採用ETFと停止条件を重点確認")
    if wins_spy >= max(1, len(validation) - 1):
        act_items.append("SPY比較では安定しているため、Core-Satelliteの守り方針は維持")
    if not act_items:
        act_items.append("局面別でも大きな弱点は限定的。次はスコア重みの改善へ進む")
    content = [
        f"# 局面別検証PDCA {date:%Y-%m-%d}",
        "",
        "## Plan",
        f"- 検証対象: {config_label}",
        "- 10年全体の最良設定が、各相場局面でも安定しているか確認",
        "",
        "## Do",
        validation.to_markdown(index=False) if not validation.empty else "検証対象データなし",
        "",
        "## Check",
        f"- SPYに勝った局面数: {wins_spy}/{len(validation)}",
        f"- QQQに勝った局面数: {wins_qqq}/{len(validation)}",
        f"- SMHに勝った局面数: {wins_smh}/{len(validation)}",
        "",
        "## Act",
        *[f"- {item}" for item in act_items],
        "",
        "## 出力ファイル",
        f"- 局面別CSV: `{csv_path}`",
    ]
    report_path.write_text("\n".join(content), encoding="utf-8")
    return report_path


def write_selection_audit_report(
    audits: dict[str, pd.DataFrame],
    output_dir: str | Path = "reports/weekly",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    report_path = PROJECT_ROOT / directory / f"selection_audit_report_{date:%Y-%m-%d}.md"
    output_folder = PROJECT_ROOT / "data" / "backtest"
    output_folder.mkdir(parents=True, exist_ok=True)
    content = [
        f"# 弱点局面ETF採用監査 {date:%Y-%m-%d}",
        "",
        "## 目的",
        "- 2020回復局面と2023 AI初動で、どのETFを選んでいたか確認",
        "- QQQ/SMHに負けた原因が、採用遅れか、分散しすぎか、DD停止かを切り分ける",
    ]
    for name, audit in audits.items():
        csv_path = output_folder / f"selection_audit_{name}_{date:%Y-%m-%d}.csv"
        audit.to_csv(csv_path, index=False)
        content.extend(
            [
                "",
                f"## {name}",
                audit.to_markdown(index=False) if not audit.empty else "採用ログなし",
                "",
                f"CSV: `{csv_path}`",
            ]
        )
    content.extend(
        [
            "",
            "## Act",
            "- SMH/SOXXが上位にいるのに採用比率が薄い場合は、半導体テーマの上限を別枠で検証",
            "- SMH/SOXXが上位に出ていない場合は、モメンタム重みと相対強度重みを強めるスコア版を検証",
            "- Noneが多い場合は、最低スコア45またはDD停止条件が厳しすぎる可能性を検証",
        ]
    )
    report_path.write_text("\n".join(content), encoding="utf-8")
    return report_path
