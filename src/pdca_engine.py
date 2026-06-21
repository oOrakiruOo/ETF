from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from .utils import PROJECT_ROOT


VIRTUAL_TRADE_COLUMNS = [
    "snapshot",
    "ETF",
    "判定",
    "entry_price",
    "target_price",
    "stop_price",
    "entry_date",
    "exit_date",
    "status",
    "exit_reason",
    "return_pct",
]

AVOID_OUTCOME_COLUMNS = [
    "snapshot",
    "ETF",
    "判定",
    "20d_return_pct",
    "is_correct",
    "reason",
]

AVOID_POLICY_SIGNALS = {
    "current_all_avoid": {"見送り", "リスク削減", "売却候補"},
    "sell_only": {"売却候補"},
    "avoid_only": {"見送り"},
    "no_sell_candidate_avoid": {"見送り", "リスク削減"},
}

ACTION_LABEL_ORDER = ["🔴 DEFENSE", "🟣 CHECK SELL", "🟢 CHECK BUY", "🟡 WAIT"]
SELF_CHECK_COLUMNS = ["date", "status", "reason", "source"]
DEFAULT_SELF_CHECK_LOG_PATH = "data/processed/pdca/self_check_log.csv"
SELF_CHECK_STATUS_MAP = {
    "kept": "守れた",
    "broke": "破った",
    "pending": "保留",
    "守れた": "守れた",
    "破った": "破った",
    "保留": "保留",
}


def _numeric_series(table: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if table.empty or column not in table.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(table[column], errors="coerce").fillna(default)


def _product_market_score(snapshot_rows: pd.DataFrame) -> int:
    if snapshot_rows.empty:
        return 0
    signals = snapshot_rows["判定"].astype(str) if "判定" in snapshot_rows.columns else pd.Series(dtype=str)
    stages = snapshot_rows["ステージ"].astype(str) if "ステージ" in snapshot_rows.columns else pd.Series(dtype=str)
    risks = snapshot_rows["テーマリスク"].astype(str) if "テーマリスク" in snapshot_rows.columns else pd.Series(dtype=str)
    score = 75.0
    score += min(float(signals.isin(["強気買い候補", "買い候補"]).sum()) * 10, 20)
    score += min(float(signals.eq("押し目待ち").sum()) * 4, 12)
    score -= min(float(signals.isin(["利確候補", "売却候補", "リスク削減"]).sum()) * 3, 18)
    score -= min(float(stages.str.contains("ステージ4|ステージ5", na=False).sum()) * 2, 18)
    score -= min(float(risks.eq("高").sum()) * 3, 12)
    rr = _numeric_series(snapshot_rows, "RR")
    if not rr.empty:
        score += min(float((rr >= 1.5).sum()) * 2, 8)
    return int(round(max(0.0, min(score, 100.0))))


def summarize_manual_decisions(manual_decisions: pd.DataFrame) -> pd.DataFrame:
    if manual_decisions.empty:
        return pd.DataFrame(
            [
                {
                    "対象件数": 0,
                    "判断済み件数": 0,
                    "未判断件数": 0,
                    "buy件数": 0,
                    "sell件数": 0,
                    "hold件数": 0,
                    "watch件数": 0,
                    "約定件数": 0,
                    "一部約定件数": 0,
                    "未約定件数": 0,
                    "要確認件数": 0,
                    "状態": "OK",
                    "理由": "手動判断対象なし",
                }
            ]
        )
    decisions = (
        manual_decisions.get("判断", pd.Series("", index=manual_decisions.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )
    fills = (
        manual_decisions.get("約定状態", pd.Series("", index=manual_decisions.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )
    decided_count = int(decisions.ne("").sum())
    undecided_count = int(decisions.eq("").sum())
    partial_count = int(fills.eq("partial").sum())
    not_filled_count = int(fills.eq("not_filled").sum())
    needs_review_count = undecided_count + partial_count + not_filled_count
    reasons = []
    if undecided_count:
        reasons.append(f"未判断{undecided_count}件")
    if partial_count:
        reasons.append(f"一部約定{partial_count}件")
    if not_filled_count:
        reasons.append(f"未約定{not_filled_count}件")
    return pd.DataFrame(
        [
            {
                "対象件数": len(manual_decisions),
                "判断済み件数": decided_count,
                "未判断件数": undecided_count,
                "buy件数": int(decisions.eq("buy").sum()),
                "sell件数": int(decisions.eq("sell").sum()),
                "hold件数": int(decisions.eq("hold").sum()),
                "watch件数": int(decisions.eq("watch").sum()),
                "約定件数": int(fills.eq("filled").sum()),
                "一部約定件数": partial_count,
                "未約定件数": not_filled_count,
                "要確認件数": needs_review_count,
                "状態": "要確認" if needs_review_count else "OK",
                "理由": "、".join(reasons) if reasons else "確認漏れなし",
            }
        ]
    )


def normalize_self_check_status(status: str) -> str:
    normalized = str(status).strip().lower()
    if normalized not in SELF_CHECK_STATUS_MAP:
        raise ValueError("自己確認は kept/broke/pending または 守れた/破った/保留 を指定してください")
    return SELF_CHECK_STATUS_MAP[normalized]


def self_check_log_path(output_path: str | Path | None = None) -> Path:
    configured = output_path or os.environ.get("SELF_CHECK_LOG_PATH") or DEFAULT_SELF_CHECK_LOG_PATH
    path = Path(configured)
    return PROJECT_ROOT / path if not path.is_absolute() else path


def append_self_check_log(
    status: str,
    reason: str = "",
    source: str = "manual",
    log_date: str | None = None,
    output_path: str | Path | None = None,
) -> Path:
    path = self_check_log_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = pd.DataFrame(
        [
            {
                "date": log_date or pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d"),
                "status": normalize_self_check_status(status),
                "reason": reason,
                "source": source,
            }
        ],
        columns=SELF_CHECK_COLUMNS,
    )
    if path.exists():
        previous = pd.read_csv(path)
        combined = pd.concat([previous, row], ignore_index=True)
    else:
        combined = row
    combined.loc[:, SELF_CHECK_COLUMNS].to_csv(path, index=False)
    return path


def summarize_self_check_logs(self_checks: pd.DataFrame) -> pd.DataFrame:
    if self_checks.empty:
        return pd.DataFrame(
            [
                {
                    "対象日数": 0,
                    "守れた": 0,
                    "破った": 0,
                    "保留": 0,
                    "遵守率%": None,
                    "状態": "OK",
                    "理由": "自己確認ログなし",
                }
            ]
        )
    statuses = self_checks.get("status", pd.Series("", index=self_checks.index)).fillna("").astype(str)
    kept = int(statuses.eq("守れた").sum())
    broke = int(statuses.eq("破った").sum())
    pending = int(statuses.eq("保留").sum())
    decided = kept + broke
    compliance_rate = round(kept / decided * 100, 1) if decided else None
    reasons = []
    if broke:
        reasons.append(f"ルール破り{broke}日")
    if pending:
        reasons.append(f"保留{pending}日")
    return pd.DataFrame(
        [
            {
                "対象日数": len(self_checks),
                "守れた": kept,
                "破った": broke,
                "保留": pending,
                "遵守率%": compliance_rate,
                "状態": "要確認" if broke or pending else "OK",
                "理由": "、".join(reasons) if reasons else "ルール遵守",
            }
        ]
    )


def propose_pdca_action(benchmark_outperformed: bool, false_positive_count: int) -> list[str]:
    proposals: list[str] = []
    if not benchmark_outperformed:
        proposals.append("ベンチマーク未達のため、テーマスコアと相対強度の重みをバックテストで再検証")
    if false_positive_count >= 3:
        proposals.append("見送り条件と過熱控除の強化をバックテストで検証")
    if not proposals:
        proposals.append("現行ルールを維持し、次週も同条件で監視")
    return proposals


def load_cached_close(ticker: str, data_dir: str | Path = "data/raw") -> pd.Series:
    path = PROJECT_ROOT / data_dir / f"{ticker}_1d.csv"
    if not path.exists():
        return pd.Series(dtype=float)
    frame = pd.read_csv(path, index_col=0, parse_dates=True)
    column = "Adj Close" if "Adj Close" in frame.columns else "Close"
    if column not in frame.columns:
        return pd.Series(dtype=float)
    return frame[column].dropna().sort_index()


def load_cached_ohlc(ticker: str, data_dir: str | Path = "data/raw") -> pd.DataFrame:
    path = PROJECT_ROOT / data_dir / f"{ticker}_1d.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path, index_col=0, parse_dates=True).sort_index()
    required = ["High", "Low"]
    close_column = "Adj Close" if "Adj Close" in frame.columns else "Close"
    if close_column not in frame.columns or any(column not in frame.columns for column in required):
        return pd.DataFrame()
    return frame.loc[:, ["High", "Low", close_column]].rename(columns={close_column: "Close"}).dropna()


def calculate_forward_return(close: pd.Series, signal_date: pd.Timestamp, days: int) -> float | None:
    if close.empty:
        return None
    available = close.loc[close.index >= signal_date]
    if len(available) <= days:
        return None
    entry = float(available.iloc[0])
    future = float(available.iloc[days])
    if entry == 0:
        return None
    return round((future / entry - 1) * 100, 2)


def evaluate_signal_history(signal_history: pd.DataFrame, horizons: list[int] | None = None) -> pd.DataFrame:
    horizons = horizons or [1, 5, 20]
    if signal_history.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for row in signal_history.to_dict("records"):
        ticker = str(row.get("ETF", ""))
        snapshot = str(row.get("snapshot", ""))
        if not ticker or not snapshot:
            continue
        signal_date = pd.Timestamp(snapshot)
        close = load_cached_close(ticker)
        result: dict[str, object] = {
            "snapshot": snapshot,
            "ETF": ticker,
            "判定": row.get("判定", ""),
            "ETFスコア": row.get("ETFスコア", None),
            "テーマスコア": row.get("テーマスコア", None),
        }
        for days in horizons:
            result[f"{days}d_return_pct"] = calculate_forward_return(close, signal_date, days)
        rows.append(result)
    return pd.DataFrame(rows)


def evaluate_virtual_trades(
    signal_history: pd.DataFrame,
    max_holding_days: int = 20,
    entry_multiplier: float = 1.0,
    stop_multiplier: float = 1.0,
    target_multiplier: float = 1.0,
) -> pd.DataFrame:
    if signal_history.empty:
        return pd.DataFrame(columns=VIRTUAL_TRADE_COLUMNS)
    buy_signals = {"強気買い候補", "買い候補", "押し目待ち", "積立候補"}
    rows: list[dict[str, object]] = []
    for row in signal_history.to_dict("records"):
        signal = str(row.get("判定", ""))
        if signal not in buy_signals:
            continue
        ticker = str(row.get("ETF", ""))
        snapshot = str(row.get("snapshot", ""))
        if not ticker or not snapshot:
            continue
        base_entry_price = float(row.get("第1買い", 0.0) or 0.0)
        current_price = float(row.get("現在価格", 0.0) or 0.0)
        entry_price = base_entry_price * entry_multiplier
        if current_price > 0:
            entry_price = min(entry_price, current_price)
        target_price = float(row.get("保守目標", 0.0) or 0.0) * target_multiplier
        stop_price = float(row.get("停止価格", 0.0) or 0.0) * stop_multiplier
        if stop_price >= entry_price:
            stop_price = entry_price * 0.97
        if entry_price <= 0 or target_price <= 0 or stop_price <= 0:
            continue

        signal_date = pd.Timestamp(snapshot)
        ohlc = load_cached_ohlc(ticker)
        future = ohlc.loc[ohlc.index > signal_date].head(max_holding_days)
        trade: dict[str, object] = {
            "snapshot": snapshot,
            "ETF": ticker,
            "判定": signal,
            "entry_price": round(entry_price, 2),
            "target_price": round(target_price, 2),
            "stop_price": round(stop_price, 2),
            "entry_date": "",
            "exit_date": "",
            "status": "未約定",
            "exit_reason": "第1買い未到達",
            "return_pct": None,
        }
        entry_window = future[future["Low"] <= entry_price]
        if entry_window.empty:
            rows.append(trade)
            continue

        entry_date = entry_window.index[0]
        trade["entry_date"] = entry_date.date().isoformat()
        trade["status"] = "約定"
        after_entry = future.loc[future.index >= entry_date]
        exit_price = float(after_entry.iloc[-1]["Close"])
        exit_date = after_entry.index[-1]
        exit_reason = "20日保有"

        for date, bar in after_entry.iterrows():
            # 同日に目標と停止が両方触れた場合は、リスク管理優先で停止を先に評価する。
            if float(bar["Low"]) <= stop_price:
                exit_price = stop_price
                exit_date = date
                exit_reason = "停止価格"
                break
            if float(bar["High"]) >= target_price:
                exit_price = target_price
                exit_date = date
                exit_reason = "保守目標"
                break

        trade["exit_date"] = exit_date.date().isoformat()
        trade["exit_reason"] = exit_reason
        trade["return_pct"] = round((exit_price / entry_price - 1) * 100, 2)
        rows.append(trade)
    return pd.DataFrame(rows, columns=VIRTUAL_TRADE_COLUMNS)


def run_entry_parameter_search(
    signal_history: pd.DataFrame,
    entry_multipliers: list[float] | None = None,
    stop_multipliers: list[float] | None = None,
) -> pd.DataFrame:
    entry_multipliers = entry_multipliers or [1.0, 1.02, 1.04, 1.06]
    stop_multipliers = stop_multipliers or [0.95, 1.0, 1.03]
    rows: list[dict[str, object]] = []
    for entry_multiplier in entry_multipliers:
        for stop_multiplier in stop_multipliers:
            trades = evaluate_virtual_trades(
                signal_history,
                entry_multiplier=entry_multiplier,
                stop_multiplier=stop_multiplier,
            )
            summary = summarize_virtual_trades(trades).iloc[0]
            target_count = int(summary.get("対象件数", 0) or 0)
            filled_count = int(summary.get("約定件数", 0) or 0)
            average_return = summary.get("平均損益%", None)
            win_rate = summary.get("勝率", None)
            stop_count = int(summary.get("停止価格到達", 0) or 0)
            fill_rate = round(filled_count / target_count * 100, 2) if target_count else 0.0
            risk_adjusted_score = 0.0
            if pd.notna(average_return):
                risk_adjusted_score += float(average_return)
            if pd.notna(win_rate):
                risk_adjusted_score += float(win_rate) / 20
            risk_adjusted_score += fill_rate / 50
            risk_adjusted_score -= stop_count * 1.5
            rows.append(
                {
                    "entry_multiplier": entry_multiplier,
                    "stop_multiplier": stop_multiplier,
                    "対象件数": target_count,
                    "約定件数": filled_count,
                    "約定率": fill_rate,
                    "勝率": win_rate,
                    "平均損益%": average_return,
                    "停止価格到達": stop_count,
                    "risk_adjusted_score": round(risk_adjusted_score, 2),
                }
            )
    return pd.DataFrame(rows).sort_values("risk_adjusted_score", ascending=False).reset_index(drop=True)


def summarize_virtual_trades(virtual_trades: pd.DataFrame) -> pd.DataFrame:
    if virtual_trades.empty:
        return pd.DataFrame(
            [
                {
                    "対象件数": 0,
                    "約定件数": 0,
                    "未約定件数": 0,
                    "勝率": None,
                    "平均損益%": None,
                    "保守目標到達": 0,
                    "停止価格到達": 0,
                    "20日保有": 0,
                }
            ]
        )
    filled = virtual_trades[virtual_trades["status"].eq("約定")]
    returns = filled["return_pct"].dropna() if not filled.empty else pd.Series(dtype=float)
    return pd.DataFrame(
        [
            {
                "対象件数": len(virtual_trades),
                "約定件数": len(filled),
                "未約定件数": int(virtual_trades["status"].eq("未約定").sum()),
                "勝率": round(float((returns > 0).mean() * 100), 2) if not returns.empty else None,
                "平均損益%": round(float(returns.mean()), 2) if not returns.empty else None,
                "保守目標到達": int(virtual_trades["exit_reason"].eq("保守目標").sum()),
                "停止価格到達": int(virtual_trades["exit_reason"].eq("停止価格").sum()),
                "20日保有": int(virtual_trades["exit_reason"].eq("20日保有").sum()),
            }
        ]
    )


def evaluate_avoid_outcomes(signal_history: pd.DataFrame, horizon_days: int = 20) -> pd.DataFrame:
    if signal_history.empty:
        return pd.DataFrame(columns=AVOID_OUTCOME_COLUMNS)
    avoid_signals = AVOID_POLICY_SIGNALS["current_all_avoid"]
    return evaluate_avoid_outcomes_for_signals(signal_history, avoid_signals, horizon_days)


def evaluate_avoid_outcomes_for_signals(
    signal_history: pd.DataFrame,
    avoid_signals: set[str],
    horizon_days: int = 20,
) -> pd.DataFrame:
    if signal_history.empty:
        return pd.DataFrame(columns=AVOID_OUTCOME_COLUMNS)
    rows: list[dict[str, object]] = []
    for row in signal_history.to_dict("records"):
        signal = str(row.get("判定", ""))
        if signal not in avoid_signals:
            continue
        ticker = str(row.get("ETF", ""))
        snapshot = str(row.get("snapshot", ""))
        if not ticker or not snapshot:
            continue
        forward_return = calculate_forward_return(load_cached_close(ticker), pd.Timestamp(snapshot), horizon_days)
        is_correct = None if forward_return is None else forward_return <= 0
        reason = "評価データ不足"
        if is_correct is True:
            reason = "回避後に上昇せず"
        elif is_correct is False:
            reason = "回避後に上昇"
        rows.append(
            {
                "snapshot": snapshot,
                "ETF": ticker,
                "判定": signal,
                "20d_return_pct": forward_return,
                "is_correct": is_correct,
                "reason": reason,
            }
        )
    return pd.DataFrame(rows, columns=AVOID_OUTCOME_COLUMNS)


def summarize_avoid_outcomes(avoid_outcomes: pd.DataFrame) -> pd.DataFrame:
    if avoid_outcomes.empty:
        return pd.DataFrame(
            [
                {
                    "対象件数": 0,
                    "評価済み件数": 0,
                    "正解率": None,
                    "平均20日後リターン%": None,
                    "回避後上昇件数": 0,
                }
            ]
        )
    evaluated = avoid_outcomes.dropna(subset=["is_correct"])
    returns = evaluated["20d_return_pct"].dropna()
    return pd.DataFrame(
        [
            {
                "対象件数": len(avoid_outcomes),
                "評価済み件数": len(evaluated),
                "正解率": round(float(evaluated["is_correct"].mean() * 100), 2) if not evaluated.empty else None,
                "平均20日後リターン%": round(float(returns.mean()), 2) if not returns.empty else None,
                "回避後上昇件数": int((evaluated["is_correct"] == False).sum()) if not evaluated.empty else 0,
            }
        ]
    )


def summarize_avoid_outcomes_by_signal(avoid_outcomes: pd.DataFrame) -> pd.DataFrame:
    if avoid_outcomes.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for signal, group in avoid_outcomes.groupby("判定"):
        evaluated = group.dropna(subset=["is_correct"])
        returns = evaluated["20d_return_pct"].dropna()
        rows.append(
            {
                "判定": signal,
                "対象件数": len(group),
                "評価済み件数": len(evaluated),
                "正解率": round(float(evaluated["is_correct"].mean() * 100), 2) if not evaluated.empty else None,
                "平均20日後リターン%": round(float(returns.mean()), 2) if not returns.empty else None,
                "回避後上昇件数": int((evaluated["is_correct"] == False).sum()) if not evaluated.empty else 0,
            }
        )
    return pd.DataFrame(rows).sort_values(["正解率", "平均20日後リターン%"], ascending=[True, False])


def run_avoid_policy_search(avoid_outcomes: pd.DataFrame) -> pd.DataFrame:
    if avoid_outcomes.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for policy_name, signals in AVOID_POLICY_SIGNALS.items():
        subset = avoid_outcomes[avoid_outcomes["判定"].isin(signals)]
        summary = summarize_avoid_outcomes(subset).iloc[0]
        correct_rate = summary.get("正解率", None)
        average_return = summary.get("平均20日後リターン%", None)
        missed_upside = int(summary.get("回避後上昇件数", 0) or 0)
        evaluated_count = int(summary.get("評価済み件数", 0) or 0)
        score = 0.0
        if pd.notna(correct_rate):
            score += float(correct_rate)
        if pd.notna(average_return):
            score -= max(float(average_return), 0.0) * 10
        score -= missed_upside / max(evaluated_count, 1) * 20
        rows.append(
            {
                "policy": policy_name,
                "対象判定": ", ".join(sorted(signals)),
                "対象件数": int(summary.get("対象件数", 0) or 0),
                "評価済み件数": evaluated_count,
                "正解率": correct_rate,
                "平均20日後リターン%": average_return,
                "回避後上昇件数": missed_upside,
                "policy_score": round(score, 2),
            }
        )
    return pd.DataFrame(rows).sort_values("policy_score", ascending=False).reset_index(drop=True)


def summarize_signal_accuracy(evaluated: pd.DataFrame) -> pd.DataFrame:
    if evaluated.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for signal, group in evaluated.groupby("判定"):
        row: dict[str, object] = {"判定": signal, "件数": len(group)}
        for column in [item for item in evaluated.columns if item.endswith("_return_pct")]:
            valid = group[column].dropna()
            row[f"{column}_平均"] = round(float(valid.mean()), 2) if not valid.empty else None
            row[f"{column}_勝率"] = round(float((valid > 0).mean() * 100), 2) if not valid.empty else None
        rows.append(row)
    return pd.DataFrame(rows)


def _action_label_for_snapshot(snapshot_rows: pd.DataFrame) -> str:
    if snapshot_rows.empty:
        return "🟡 WAIT"
    signals = snapshot_rows["判定"].astype(str) if "判定" in snapshot_rows.columns else pd.Series(dtype=str)
    if _product_market_score(snapshot_rows) <= 35:
        return "🔴 DEFENSE"
    if signals.isin(["利確候補", "売却候補", "リスク削減"]).any():
        return "🟣 CHECK SELL"
    if signals.isin(["強気買い候補", "買い候補"]).any():
        return "🟢 CHECK BUY"
    return "🟡 WAIT"


def build_action_label_by_snapshot(signal_history: pd.DataFrame) -> pd.DataFrame:
    if signal_history.empty or "snapshot" not in signal_history.columns:
        return pd.DataFrame(columns=["snapshot", "行動ラベル"])
    rows = [
        {"snapshot": snapshot, "行動ラベル": _action_label_for_snapshot(group)}
        for snapshot, group in signal_history.groupby("snapshot")
    ]
    return pd.DataFrame(rows)


def _action_label_interpretation(label: str, avoid_rate: object, return_20d: object) -> str:
    if label == "🔴 DEFENSE":
        if pd.notna(avoid_rate) and float(avoid_rate) >= 55:
            return "新規買い抑制が機能しやすい局面"
        return "新規買いを抑え、データと保有確認を優先"
    if label == "🟣 CHECK SELL":
        return "新規買いより保有ETFの利確/売却確認を優先"
    if label == "🟢 CHECK BUY":
        if pd.notna(return_20d) and float(return_20d) > 0:
            return "買い候補の手動確認に値する局面"
        return "買い候補はあるが、条件とサイズを手動確認"
    return "何もしないことが基本方針"


def summarize_action_label_history(
    signal_history: pd.DataFrame,
    evaluated_signals: pd.DataFrame,
    avoid_outcomes: pd.DataFrame,
) -> pd.DataFrame:
    labels = build_action_label_by_snapshot(signal_history)
    if labels.empty:
        return pd.DataFrame()
    evaluated = evaluated_signals.merge(labels, on="snapshot", how="left") if not evaluated_signals.empty else pd.DataFrame()
    avoided = avoid_outcomes.merge(labels, on="snapshot", how="left") if not avoid_outcomes.empty else pd.DataFrame()
    rows: list[dict[str, object]] = []
    for label in ACTION_LABEL_ORDER:
        label_days = labels[labels["行動ラベル"].eq(label)]
        evaluated_group = evaluated[evaluated["行動ラベル"].eq(label)] if not evaluated.empty else pd.DataFrame()
        avoid_group = avoided[avoided["行動ラベル"].eq(label)] if not avoided.empty else pd.DataFrame()
        row: dict[str, object] = {
            "行動ラベル": label,
            "日数": int(label_days["snapshot"].nunique()) if not label_days.empty else 0,
            "ETF件数": len(evaluated_group),
        }
        for days in [1, 5, 20]:
            column = f"{days}d_return_pct"
            values = pd.to_numeric(evaluated_group.get(column, pd.Series(dtype=float)), errors="coerce").dropna()
            row[f"{days}日後平均%"] = round(float(values.mean()), 2) if not values.empty else None
            row[f"{days}日後勝率%"] = round(float((values > 0).mean() * 100), 2) if not values.empty else None
        evaluated_avoid = avoid_group.dropna(subset=["is_correct"]) if not avoid_group.empty else pd.DataFrame()
        row["回避評価件数"] = len(evaluated_avoid)
        row["回避正解率%"] = (
            round(float(evaluated_avoid["is_correct"].astype(bool).mean() * 100), 2)
            if not evaluated_avoid.empty
            else None
        )
        row["解釈"] = _action_label_interpretation(label, row["回避正解率%"], row["20日後平均%"])
        rows.append(row)
    return pd.DataFrame(rows)


def simulate_user_friction_pdca(
    action_label_history: pd.DataFrame,
    portfolio: pd.DataFrame | None = None,
    years: int = 30,
    trading_days_per_year: int = 252,
) -> pd.DataFrame:
    total_days = years * trading_days_per_year
    rows: list[dict[str, object]] = []
    if action_label_history.empty or "行動ラベル" not in action_label_history.columns:
        return pd.DataFrame(
            [
                {
                    "不満": "判定履歴が不足",
                    "深刻度": "高",
                    "30年換算": "",
                    "検証": "行動ラベル履歴なし",
                    "修正案": "replay-quickまたはweekly-line-summaryを先に実行",
                }
            ]
        )
    labels = action_label_history.copy()
    labels["日数"] = pd.to_numeric(labels.get("日数", 0), errors="coerce").fillna(0)
    observed_days = float(labels["日数"].sum())
    if observed_days <= 0:
        observed_days = 1.0

    def projected_days(label: str) -> int:
        count = float(labels.loc[labels["行動ラベル"].astype(str).eq(label), "日数"].sum())
        return int(round(count / observed_days * total_days))

    defense_days = projected_days("🔴 DEFENSE")
    buy_days = projected_days("🟢 CHECK BUY")
    wait_days = projected_days("🟡 WAIT")
    sell_days = projected_days("🟣 CHECK SELL")

    if defense_days / total_days >= 0.6:
        rows.append(
            {
                "不満": "待ての通知が多く、飽きる",
                "深刻度": "高",
                "30年換算": f"DEFENSE 約{defense_days:,}日",
                "検証": "防御判定が長期利用の大半を占める",
                "修正案": "連続DEFENSE日数と、次に解除される条件を通知に追加",
            }
        )
    if buy_days / total_days <= 0.05:
        rows.append(
            {
                "不満": "買い候補が少なすぎて使う意味が分かりにくい",
                "深刻度": "中",
                "30年換算": f"CHECK BUY 約{buy_days:,}日",
                "検証": "買い候補が出ない期間が長い",
                "修正案": "監視候補に、買い条件までの距離と解除条件を表示",
            }
        )
    if wait_days == 0:
        rows.append(
            {
                "不満": "WAITとDEFENSEの違いが体感しにくい",
                "深刻度": "中",
                "30年換算": "WAIT 0日",
                "検証": "中立待機の表示機会がない",
                "修正案": "DEFENSEは市場リスク、WAITは条件未達として説明を分ける",
            }
        )
    if sell_days / total_days >= 0.3:
        rows.append(
            {
                "不満": "売却確認が多く、毎回何を見ればよいか迷う",
                "深刻度": "中",
                "30年換算": f"CHECK SELL 約{sell_days:,}日",
                "検証": "保有確認の頻度が高い",
                "修正案": "実保有銘柄と市場リスク対象を分けて表示",
            }
        )

    if portfolio is not None and not portfolio.empty:
        portfolio_frame = portfolio.copy()
        portfolio_frame["weight_pct"] = pd.to_numeric(portfolio_frame.get("weight_pct", 0), errors="coerce").fillna(0)
        reference_weight = float(
            portfolio_frame.loc[
                portfolio_frame.get("signal_scope", pd.Series("", index=portfolio_frame.index)).astype(str).eq("reference"),
                "weight_pct",
            ].sum()
        )
        max_reference_weight = float(
            portfolio_frame.loc[
                portfolio_frame.get("signal_scope", pd.Series("", index=portfolio_frame.index)).astype(str).eq("reference"),
                "weight_pct",
            ].max()
            or 0.0
        )
        if reference_weight >= 20.0 or max_reference_weight >= 10.0:
            rows.append(
                {
                    "不満": "ETF信号対象外の保有が大きく、通知だけでは不安",
                    "深刻度": "中",
                    "30年換算": f"参考保有比率 {reference_weight:.1f}%",
                    "検証": "個別株・参考保有が一定比率を超える",
                    "修正案": "参考保有のサイズ注意と、買い増し別枠確認を表示",
                }
            )
    if not rows:
        rows.append(
            {
                "不満": "大きな不満シナリオなし",
                "深刻度": "低",
                "30年換算": f"対象 {total_days:,}営業日",
                "検証": "行動ラベルの偏りは許容範囲",
                "修正案": "現行表示を維持",
            }
        )
    return pd.DataFrame(rows)


def propose_signal_improvements(signal_accuracy: pd.DataFrame) -> list[str]:
    if signal_accuracy.empty:
        return ["シグナル履歴が不足。日次レポートを蓄積し、翌週に1日/5日/20日後リターンを再評価"]

    proposals: list[str] = []
    buy_rows = signal_accuracy[signal_accuracy["判定"].isin(["強気買い候補", "買い候補", "押し目待ち"])]
    avoid_rows = signal_accuracy[signal_accuracy["判定"].isin(["見送り", "リスク削減", "売却候補"])]

    def weighted_average(frame: pd.DataFrame, column: str) -> float | None:
        if frame.empty or column not in frame.columns or "件数" not in frame.columns:
            return None
        valid = frame.dropna(subset=[column])
        if valid.empty:
            return None
        total_weight = float(valid["件数"].sum())
        if total_weight <= 0:
            return None
        return round(float((valid[column] * valid["件数"]).sum() / total_weight), 2)

    buy_20d = weighted_average(buy_rows, "20d_return_pct_平均")
    buy_5d_win = weighted_average(buy_rows, "5d_return_pct_勝率")
    avoid_20d = weighted_average(avoid_rows, "20d_return_pct_平均")

    if buy_20d is not None and buy_20d < 0:
        proposals.append("買い系シグナルの20日後平均がマイナス。最低ETFスコア引き上げ、RSI上限、52週高値距離を次回バックテストで厳格化")
    elif buy_20d is not None and buy_20d >= 2.0:
        proposals.append("買い系シグナルの20日後平均が良好。現行の買い条件を維持し、購入割合の上限だけ慎重に再検証")

    if buy_5d_win is not None and buy_5d_win < 45:
        proposals.append("買い系シグナルの短期勝率が低い。第1買い価格をさらに深くする押し目待ち版をバックテスト")

    if avoid_20d is not None and avoid_20d > 1.0:
        proposals.append("見送り/リスク削減銘柄が20日後に上昇。過熱控除が強すぎないか、半導体/AI局面だけ別枠で検証")
    elif avoid_20d is not None and avoid_20d <= 0:
        proposals.append("見送り/リスク削減判定は概ね機能。高値追い禁止とDD優先ルールを維持")

    if not proposals:
        proposals.append("フォワード評価は中立。日次シグナル履歴を継続蓄積し、次週も同じ基準で確認")
    return proposals
