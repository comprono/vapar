from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.preprocessing import StandardScaler

from backend.backtest.data_loader import DataLoader


TRAIN_SYMBOL = "BTC-USD"
EVAL_SYMBOLS = [
    "ETH-USD",
    "SOL-USD",
    "BNB-USD",
    "XRP-USD",
    "ADA-USD",
    "DOGE-USD",
    "TRX-USD",
    "AVAX-USD",
    "DOT-USD",
    "LINK-USD",
    "LTC-USD",
]

TRADE_COST_BPS = 10.0
TRADE_COST_RATE = TRADE_COST_BPS / 10000.0
YEARS = 7

MIN_TRAIN_SAMPLES = 365
MIN_TEST_SAMPLES = 8
TRAIN_LOOKBACK_DAYS = 365 * 4
CALIBRATION_LOOKBACK_DAYS = 365
MIN_CALIBRATION_SAMPLES = 60
AUTORESEARCH_MONTH_STRIDE = 2

ACCEPTANCE_THRESHOLDS = {
    "must_beat_buyhold": True,
    "min_sharpe": 0.60,
    "min_sortino": 0.80,
    "max_drawdown": 0.45,
}

DEFAULT_CONFIGS = [
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0010,
        "threshold": 0.0020,
        "max_iter": 160,
        "trade_mode": "long_short",
        "model_kind": "regression",
    },
    {
        "hidden_layers": [96, 48],
        "alpha": 0.0005,
        "learning_rate_init": 0.0008,
        "threshold": 0.0025,
        "max_iter": 180,
        "trade_mode": "long_only",
        "model_kind": "regression",
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0010,
        "learning_rate_init": 0.0009,
        "threshold": 0.0600,
        "max_iter": 150,
        "trade_mode": "long_only",
        "model_kind": "classification",
    },
    {
        "hidden_layers": [96, 48],
        "alpha": 0.0010,
        "learning_rate_init": 0.0007,
        "threshold": 0.0750,
        "max_iter": 170,
        "trade_mode": "long_short",
        "model_kind": "classification",
    },
]


@dataclass
class ModelBundle:
    scaler: StandardScaler
    model: Any
    model_kind: str


def _calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def _prepare_feature_frame(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    frame = df.copy().sort_index()
    if "Close" not in frame.columns:
        raise ValueError("Data frame must include Close column")

    close = frame["Close"].astype(float)
    volume = frame["Volume"].astype(float) if "Volume" in frame.columns else pd.Series(1.0, index=frame.index)

    ret_1 = close.pct_change()
    ema_fast = close.ewm(span=10, adjust=False).mean()
    ema_slow = close.ewm(span=30, adjust=False).mean()
    vol_mean = volume.rolling(20).mean()
    vol_std = volume.rolling(20).std()

    feat = pd.DataFrame(index=frame.index)
    feat["ret_1"] = ret_1
    feat["ret_2"] = close.pct_change(2)
    feat["ret_3"] = close.pct_change(3)
    feat["ret_5"] = close.pct_change(5)
    feat["ret_10"] = close.pct_change(10)
    feat["ret_20"] = close.pct_change(20)
    feat["vol_5"] = ret_1.rolling(5).std()
    feat["vol_20"] = ret_1.rolling(20).std()
    feat["mom_10"] = close / close.shift(10) - 1.0
    feat["mom_20"] = close / close.shift(20) - 1.0
    feat["ema_spread"] = ema_fast / ema_slow - 1.0
    feat["rsi_14"] = _calc_rsi(close, period=14) / 100.0
    feat["volume_z20"] = (volume - vol_mean) / vol_std.replace(0.0, np.nan)

    # Target is next-day close-to-close return; this keeps training strictly one-step-ahead.
    feat["target"] = ret_1.shift(-1)
    feat["close"] = close

    feature_cols = [
        "ret_1",
        "ret_2",
        "ret_3",
        "ret_5",
        "ret_10",
        "ret_20",
        "vol_5",
        "vol_20",
        "mom_10",
        "mom_20",
        "ema_spread",
        "rsi_14",
        "volume_z20",
    ]

    feat = feat.replace([np.inf, -np.inf], np.nan).dropna().copy()
    feat.index = pd.to_datetime(feat.index).tz_localize(None)
    return feat, feature_cols


def _first_of_month(ts: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(year=ts.year, month=ts.month, day=1)


def _iter_month_starts(index: pd.DatetimeIndex) -> List[pd.Timestamp]:
    starts = sorted({_first_of_month(ts) for ts in index})
    return starts


def _fit_model(train_df: pd.DataFrame, feature_cols: List[str], config: Dict[str, Any]) -> ModelBundle:
    x_train = train_df[feature_cols].to_numpy(dtype=float)
    y_train_raw = train_df["target"].to_numpy(dtype=float)

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)

    hidden_layers = tuple(config["hidden_layers"])
    model_kind = config["model_kind"]

    if model_kind == "classification":
        y_train = (y_train_raw > 0.0).astype(int)
        model = MLPClassifier(
            hidden_layer_sizes=hidden_layers,
            alpha=float(config["alpha"]),
            learning_rate_init=float(config["learning_rate_init"]),
            max_iter=int(config["max_iter"]),
            early_stopping=True,
            n_iter_no_change=12,
            validation_fraction=0.12,
            random_state=42,
        )
        model.fit(x_train_scaled, y_train)
    else:
        model = MLPRegressor(
            hidden_layer_sizes=hidden_layers,
            alpha=float(config["alpha"]),
            learning_rate_init=float(config["learning_rate_init"]),
            max_iter=int(config["max_iter"]),
            early_stopping=True,
            n_iter_no_change=12,
            validation_fraction=0.12,
            random_state=42,
        )
        model.fit(x_train_scaled, y_train_raw)

    return ModelBundle(scaler=scaler, model=model, model_kind=model_kind)


def _predict_scores(bundle: ModelBundle, feature_df: pd.DataFrame, feature_cols: List[str]) -> np.ndarray:
    x = feature_df[feature_cols].to_numpy(dtype=float)
    x_scaled = bundle.scaler.transform(x)

    if bundle.model_kind == "classification":
        probs = bundle.model.predict_proba(x_scaled)[:, 1]
        return (probs - 0.5) * 2.0

    return bundle.model.predict(x_scaled)


def _score_to_position(score: float, threshold: float, trade_mode: str, position_scale: float) -> float:
    if trade_mode == "long_only":
        return float(position_scale) if score > threshold else 0.0
    if score > threshold:
        return float(position_scale)
    if score < -threshold:
        return -float(position_scale)
    return 0.0


def _simulate_from_positions(
    returns: np.ndarray,
    positions: np.ndarray,
    trade_cost_rate: float,
) -> Dict[str, Any]:
    n = len(returns)
    daily = np.zeros(n, dtype=float)
    turnover = np.zeros(n, dtype=float)
    prev_pos = 0.0
    trades = 0

    for i in range(n):
        pos = float(positions[i])
        tcost = abs(pos - prev_pos) * trade_cost_rate
        turnover[i] = abs(pos - prev_pos)
        if turnover[i] > 1e-12:
            trades += 1
        daily[i] = pos * float(returns[i]) - tcost
        prev_pos = pos

    equity = np.cumprod(1.0 + daily)
    return {
        "daily_returns": daily,
        "equity": equity,
        "trade_count": int(trades),
        "turnover": turnover,
    }


def _to_monthly_yearly(daily_returns: np.ndarray, index: pd.DatetimeIndex) -> Tuple[Dict[str, float], Dict[str, float]]:
    s = pd.Series(daily_returns, index=index)
    monthly = ((1.0 + s).groupby(s.index.strftime("%Y-%m")).prod() - 1.0).to_dict()
    yearly = ((1.0 + s).groupby(s.index.strftime("%Y")).prod() - 1.0).to_dict()
    return {k: float(v) for k, v in monthly.items()}, {k: float(v) for k, v in yearly.items()}


def _metrics_from_returns(
    daily_returns: np.ndarray,
    index: pd.DatetimeIndex,
    trade_count: int = 0,
    active_positions: np.ndarray | None = None,
    underlying_returns: np.ndarray | None = None,
) -> Dict[str, Any]:
    if len(daily_returns) == 0:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "trade_count": int(trade_count),
            "win_rate": 0.0,
            "daily_hit_rate": 0.0,
            "monthly_returns": {},
            "yearly_returns": {},
        }

    s = pd.Series(daily_returns, index=index)
    equity = (1.0 + s).cumprod()
    total_return = float(equity.iloc[-1] - 1.0)
    n = len(s)

    if total_return <= -0.999999:
        cagr = -1.0
    else:
        cagr = float((1.0 + total_return) ** (252.0 / max(n, 1)) - 1.0)

    vol = float(s.std())
    sharpe = float((s.mean() / vol) * math.sqrt(252.0)) if vol > 1e-12 else 0.0

    downside = s[s < 0.0]
    downside_std = float(downside.std()) if len(downside) > 0 else 0.0
    sortino = float((s.mean() / downside_std) * math.sqrt(252.0)) if downside_std > 1e-12 else 0.0

    drawdown = (equity / equity.cummax()) - 1.0
    max_drawdown = float(abs(drawdown.min()))

    win_rate = float((s > 0.0).mean())

    daily_hit_rate = 0.0
    if active_positions is not None and underlying_returns is not None and len(active_positions) == len(underlying_returns):
        active = np.abs(active_positions) > 1e-12
        if np.any(active):
            signed = np.sign(active_positions[active]) * np.sign(underlying_returns[active])
            daily_hit_rate = float((signed > 0).mean())

    monthly, yearly = _to_monthly_yearly(daily_returns, index)

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "trade_count": int(trade_count),
        "win_rate": win_rate,
        "daily_hit_rate": daily_hit_rate,
        "monthly_returns": monthly,
        "yearly_returns": yearly,
    }


def _oracle_best_path(returns: np.ndarray, trade_cost_rate: float) -> Dict[str, Any]:
    n = len(returns)
    if n == 0:
        return {"positions": np.array([], dtype=float), "daily_returns": np.array([], dtype=float), "trade_count": 0}

    states = np.array([-1.0, 0.0, 1.0], dtype=float)
    state_count = len(states)

    dp = np.full((n, state_count), -np.inf, dtype=float)
    parent = np.zeros((n, state_count), dtype=int)

    # Start from flat position at t=-1.
    for s_idx, s in enumerate(states):
        gross = 1.0 + s * returns[0] - trade_cost_rate * abs(s - 0.0)
        dp[0, s_idx] = math.log(max(gross, 1e-12))
        parent[0, s_idx] = 1  # index of state 0.0

    for t in range(1, n):
        r = float(returns[t])
        for s_idx, s in enumerate(states):
            best_score = -np.inf
            best_prev = 1
            for p_idx, p in enumerate(states):
                gross = 1.0 + s * r - trade_cost_rate * abs(s - p)
                score = dp[t - 1, p_idx] + math.log(max(gross, 1e-12))
                if score > best_score:
                    best_score = score
                    best_prev = p_idx
            dp[t, s_idx] = best_score
            parent[t, s_idx] = best_prev

    best_last = int(np.argmax(dp[n - 1]))
    pos_idx = np.zeros(n, dtype=int)
    pos_idx[-1] = best_last

    for t in range(n - 1, 0, -1):
        pos_idx[t - 1] = parent[t, pos_idx[t]]

    positions = states[pos_idx]
    sim = _simulate_from_positions(returns=returns, positions=positions, trade_cost_rate=trade_cost_rate)
    return {
        "positions": positions,
        "daily_returns": sim["daily_returns"],
        "trade_count": sim["trade_count"],
    }


def _score_validation(
    model_metrics: Dict[str, Any],
    buyhold_metrics: Dict[str, Any],
    gap: Dict[str, float],
) -> float:
    excess = float(model_metrics["total_return"] - buyhold_metrics["total_return"])
    return (
        excess
        + 0.35 * float(model_metrics["sharpe"])
        + 0.20 * float(model_metrics["sortino"])
        - 1.10 * float(model_metrics["max_drawdown"])
        - 0.05 * float(abs(gap["capture_ratio"]))
    )


def _calibration_candidates(base_threshold: float) -> List[Tuple[float, float, str]]:
    thresholds = sorted({0.0, base_threshold * 0.5, base_threshold, base_threshold * 1.5, base_threshold * 2.0, 0.0015, 0.0030, 0.0060})
    scales = [0.50, 0.75, 1.00]
    modes = ["long_only", "long_short"]
    candidates: List[Tuple[float, float, str]] = []
    for th in thresholds:
        for sc in scales:
            for md in modes:
                candidates.append((float(th), float(sc), md))
    return candidates


def _calibrate_coin(
    coin_df: pd.DataFrame,
    month_start: pd.Timestamp,
    scores_history: np.ndarray,
    base_config: Dict[str, Any],
) -> Dict[str, Any]:
    cal_start = month_start - pd.Timedelta(days=CALIBRATION_LOOKBACK_DAYS)
    mask = (coin_df.index >= cal_start) & (coin_df.index < month_start)
    cal_df = coin_df.loc[mask]
    if len(cal_df) < MIN_CALIBRATION_SAMPLES:
        return {
            "threshold": float(base_config["threshold"]),
            "position_scale": 1.0,
            "trade_mode": str(base_config["trade_mode"]),
            "calibration_score": -999.0,
            "samples": int(len(cal_df)),
            "used_default": True,
        }

    cal_scores = scores_history[mask]
    cal_returns = cal_df["target"].to_numpy(dtype=float)
    idx = cal_df.index

    best = None
    for threshold, scale, mode in _calibration_candidates(float(base_config["threshold"])):
        positions = np.array([_score_to_position(s, threshold, mode, scale) for s in cal_scores], dtype=float)
        sim = _simulate_from_positions(cal_returns, positions, TRADE_COST_RATE)
        perf = _metrics_from_returns(
            daily_returns=sim["daily_returns"],
            index=idx,
            trade_count=sim["trade_count"],
            active_positions=positions,
            underlying_returns=cal_returns,
        )
        objective = (
            float(perf["total_return"])
            + 0.25 * float(perf["sharpe"])
            + 0.10 * float(perf["sortino"])
            - 0.90 * float(perf["max_drawdown"])
            - 0.02 * float(sim["trade_count"]) / max(len(idx), 1)
        )
        if best is None or objective > best["objective"]:
            best = {
                "objective": objective,
                "threshold": float(threshold),
                "position_scale": float(scale),
                "trade_mode": str(mode),
                "samples": int(len(cal_df)),
                "used_default": False,
            }

    if best is None:
        return {
            "threshold": float(base_config["threshold"]),
            "position_scale": 1.0,
            "trade_mode": str(base_config["trade_mode"]),
            "calibration_score": -999.0,
            "samples": int(len(cal_df)),
            "used_default": True,
        }

    return {
        "threshold": best["threshold"],
        "position_scale": best["position_scale"],
        "trade_mode": best["trade_mode"],
        "calibration_score": float(best["objective"]),
        "samples": best["samples"],
        "used_default": False,
    }


def _build_buyhold_metrics(returns: np.ndarray, index: pd.DatetimeIndex) -> Tuple[Dict[str, Any], np.ndarray]:
    positions = np.ones(len(returns), dtype=float)
    sim = _simulate_from_positions(returns, positions, TRADE_COST_RATE)
    metrics = _metrics_from_returns(
        daily_returns=sim["daily_returns"],
        index=index,
        trade_count=sim["trade_count"],
        active_positions=positions,
        underlying_returns=returns,
    )
    return metrics, sim["daily_returns"]


def _build_pooled_train_frame(
    prepared: Dict[str, pd.DataFrame],
    train_symbols: List[str],
    month_start: pd.Timestamp,
) -> pd.DataFrame:
    train_start = month_start - pd.Timedelta(days=TRAIN_LOOKBACK_DAYS)
    frames: List[pd.DataFrame] = []

    for symbol in train_symbols:
        if symbol not in prepared:
            continue
        sdf = prepared[symbol]
        part = sdf[(sdf.index < month_start) & (sdf.index >= train_start)]
        if len(part) < MIN_TEST_SAMPLES:
            continue
        frames.append(part)

    if not frames:
        return pd.DataFrame()

    pooled = pd.concat(frames, axis=0).sort_index()
    return pooled


def _merge_metric_dicts(metric_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not metric_rows:
        return _metrics_from_returns(np.array([]), pd.DatetimeIndex([]))

    keys = ["total_return", "cagr", "sharpe", "sortino", "max_drawdown", "trade_count", "win_rate", "daily_hit_rate"]
    out = {}
    for key in keys:
        out[key] = float(np.mean([float(m[key]) for m in metric_rows]))
    out["monthly_returns"] = {}
    out["yearly_returns"] = {}
    return out


def _run_multi_coin_walkforward_for_config(
    prepared: Dict[str, pd.DataFrame],
    train_symbols: List[str],
    eval_symbols: List[str],
    feature_cols: List[str],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    ref_symbol = train_symbols[0]
    month_starts = _iter_month_starts(prepared[ref_symbol].index)

    model_metric_rows: List[Dict[str, Any]] = []
    buyhold_metric_rows: List[Dict[str, Any]] = []
    symbol_day_counts: Dict[str, int] = {s: 0 for s in eval_symbols}

    for month_idx, month_start in enumerate(month_starts):
        if month_idx % AUTORESEARCH_MONTH_STRIDE != 0:
            continue
        month_end = month_start + pd.offsets.MonthBegin(1)
        pooled_train = _build_pooled_train_frame(prepared, train_symbols, month_start)
        if len(pooled_train) < MIN_TRAIN_SAMPLES:
            continue

        bundle = _fit_model(pooled_train, feature_cols, config)

        for symbol in eval_symbols:
            coin_df = prepared[symbol]
            month_df = coin_df[(coin_df.index >= month_start) & (coin_df.index < month_end)]
            if len(month_df) < MIN_TEST_SAMPLES:
                continue

            scores = _predict_scores(bundle, month_df, feature_cols)
            returns = month_df["target"].to_numpy(dtype=float)
            index = month_df.index

            positions = np.array(
                [
                    _score_to_position(
                        float(scores[i]),
                        float(config["threshold"]),
                        str(config["trade_mode"]),
                        1.0,
                    )
                    for i in range(len(scores))
                ],
                dtype=float,
            )
            model_sim = _simulate_from_positions(returns, positions, TRADE_COST_RATE)
            model_metrics = _metrics_from_returns(
                daily_returns=model_sim["daily_returns"],
                index=index,
                trade_count=model_sim["trade_count"],
                active_positions=positions,
                underlying_returns=returns,
            )
            buyhold_metrics, _ = _build_buyhold_metrics(returns, index)

            model_metric_rows.append(model_metrics)
            buyhold_metric_rows.append(buyhold_metrics)
            symbol_day_counts[symbol] += int(len(month_df))

    if not model_metric_rows:
        return {
            "score": -999.0,
            "model_validation": _metrics_from_returns(np.array([]), pd.DatetimeIndex([])),
            "buyhold_validation": _metrics_from_returns(np.array([]), pd.DatetimeIndex([])),
            "oracle_validation": {},
            "gap_validation": {
                "excess_vs_buyhold": 0.0,
                "relative_capture_vs_buyhold": 0.0,
                "outperform_rate": 0.0,
            },
            "days_scored": 0,
            "symbols_used": 0,
        }

    model_validation = _merge_metric_dicts(model_metric_rows)
    buyhold_validation = _merge_metric_dicts(buyhold_metric_rows)

    model_totals = np.array([float(m["total_return"]) for m in model_metric_rows], dtype=float)
    buy_totals = np.array([float(m["total_return"]) for m in buyhold_metric_rows], dtype=float)
    excess = model_totals - buy_totals
    outperform_rate = float(np.mean(excess > 0.0))

    denom = np.maximum(np.abs(buy_totals), 1e-9)
    relative_capture = float(np.mean(model_totals / denom))
    gap_validation = {
        "excess_vs_buyhold": float(np.mean(excess)),
        "relative_capture_vs_buyhold": relative_capture,
        "outperform_rate": outperform_rate,
    }

    score = (
        float(gap_validation["excess_vs_buyhold"])
        + 0.35 * float(model_validation["sharpe"])
        + 0.20 * float(model_validation["sortino"])
        - 1.10 * float(model_validation["max_drawdown"])
        + 0.50 * float(outperform_rate)
    )

    return {
        "score": float(score),
        "model_validation": model_validation,
        "buyhold_validation": buyhold_validation,
        "oracle_validation": {},
        "gap_validation": gap_validation,
        "days_scored": int(sum(symbol_day_counts.values())),
        "symbols_used": int(sum(1 for _, c in symbol_day_counts.items() if c > 0)),
    }


def _run_karpathy_autoresearch(
    prepared: Dict[str, pd.DataFrame],
    train_symbols: List[str],
    eval_symbols: List[str],
    feature_cols: List[str],
    configs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    experiments = []
    best_trial = None

    for trial_idx, cfg in enumerate(configs, start=1):
        result = _run_multi_coin_walkforward_for_config(
            prepared=prepared,
            train_symbols=train_symbols,
            eval_symbols=eval_symbols,
            feature_cols=feature_cols,
            config=cfg,
        )
        row = {
            "trial": trial_idx,
            "config": cfg,
            "model_validation": result["model_validation"],
            "buyhold_validation": result["buyhold_validation"],
            "oracle_validation": result["oracle_validation"],
            "gap_validation": result["gap_validation"],
            "days_scored": result["days_scored"],
            "symbols_used": result["symbols_used"],
            "score": result["score"],
        }
        experiments.append(row)
        if best_trial is None or row["score"] > best_trial["score"]:
            best_trial = row

    if best_trial is None:
        raise RuntimeError("AutoResearch produced no valid trial")

    return {
        "best_config": best_trial["config"],
        "best_score": float(best_trial["score"]),
        "month_stride_for_selection": int(AUTORESEARCH_MONTH_STRIDE),
        "experiments": experiments,
        "anti_cheat_note": "Oracle trades are used only for verification/scoring, never as training targets.",
    }


def _coin_acceptance(model_metrics: Dict[str, Any], buyhold_metrics: Dict[str, Any]) -> Dict[str, Any]:
    beat_buyhold = float(model_metrics["total_return"]) > float(buyhold_metrics["total_return"])
    sharpe_ok = float(model_metrics["sharpe"]) >= float(ACCEPTANCE_THRESHOLDS["min_sharpe"])
    sortino_ok = float(model_metrics["sortino"]) >= float(ACCEPTANCE_THRESHOLDS["min_sortino"])
    drawdown_ok = float(model_metrics["max_drawdown"]) <= float(ACCEPTANCE_THRESHOLDS["max_drawdown"])

    accepted = (
        (beat_buyhold if ACCEPTANCE_THRESHOLDS["must_beat_buyhold"] else True)
        and sharpe_ok
        and sortino_ok
        and drawdown_ok
    )

    return {
        "accepted": bool(accepted),
        "checks": {
            "beat_buyhold": bool(beat_buyhold),
            "sharpe_ok": bool(sharpe_ok),
            "sortino_ok": bool(sortino_ok),
            "drawdown_ok": bool(drawdown_ok),
        },
        "thresholds": ACCEPTANCE_THRESHOLDS,
    }


def _summarize_calibration(calibration_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not calibration_rows:
        return {
            "months_calibrated": 0,
            "default_used_months": 0,
            "avg_threshold": 0.0,
            "avg_position_scale": 0.0,
            "long_short_months": 0,
            "long_only_months": 0,
        }

    thresholds = [float(r["threshold"]) for r in calibration_rows]
    scales = [float(r["position_scale"]) for r in calibration_rows]
    default_months = sum(1 for r in calibration_rows if bool(r.get("used_default")))
    ls_months = sum(1 for r in calibration_rows if r.get("trade_mode") == "long_short")
    lo_months = sum(1 for r in calibration_rows if r.get("trade_mode") == "long_only")

    return {
        "months_calibrated": int(len(calibration_rows)),
        "default_used_months": int(default_months),
        "avg_threshold": float(np.mean(thresholds)),
        "avg_position_scale": float(np.mean(scales)),
        "long_short_months": int(ls_months),
        "long_only_months": int(lo_months),
    }


def run_crypto_7y_autoresearch() -> Dict[str, Any]:
    np.random.seed(42)

    today = date.today()
    end_date = (today + timedelta(days=1)).isoformat()
    start_date = (today - timedelta(days=YEARS * 365)).isoformat()

    loader = DataLoader(cache_dir="data/cache")
    symbols = [TRAIN_SYMBOL] + EVAL_SYMBOLS
    raw_data = loader.load_multiple(symbols=symbols, start_date=start_date, end_date=end_date, interval="1d")

    if TRAIN_SYMBOL not in raw_data:
        raise RuntimeError(f"Missing required training symbol data: {TRAIN_SYMBOL}")

    prepared: Dict[str, pd.DataFrame] = {}
    feature_cols: List[str] = []

    for sym in symbols:
        if sym not in raw_data:
            continue
        feat, cols = _prepare_feature_frame(raw_data[sym])
        if len(feat) < MIN_TRAIN_SAMPLES:
            continue
        prepared[sym] = feat
        if not feature_cols:
            feature_cols = cols

    if TRAIN_SYMBOL not in prepared:
        raise RuntimeError(f"Prepared feature set is missing training symbol: {TRAIN_SYMBOL}")

    available_eval = [s for s in EVAL_SYMBOLS if s in prepared]
    if not available_eval:
        raise RuntimeError("No evaluation symbols have enough feature data")

    train_symbols = [s for s in [TRAIN_SYMBOL] + available_eval if s in prepared]
    btc_df = prepared[TRAIN_SYMBOL]
    auto = _run_karpathy_autoresearch(
        prepared=prepared,
        train_symbols=train_symbols,
        eval_symbols=available_eval,
        feature_cols=feature_cols,
        configs=DEFAULT_CONFIGS,
    )
    best_config = auto["best_config"]

    month_starts = _iter_month_starts(btc_df.index)

    per_coin_rows: Dict[str, List[Dict[str, Any]]] = {sym: [] for sym in available_eval}
    per_coin_calibrations: Dict[str, List[Dict[str, Any]]] = {sym: [] for sym in available_eval}

    for month_start in month_starts:
        month_end = month_start + pd.offsets.MonthBegin(1)
        pooled_train = _build_pooled_train_frame(prepared, train_symbols, month_start)
        if len(pooled_train) < MIN_TRAIN_SAMPLES:
            continue

        bundle = _fit_model(pooled_train, feature_cols, best_config)

        for symbol in available_eval:
            coin_df = prepared[symbol]
            month_df = coin_df[(coin_df.index >= month_start) & (coin_df.index < month_end)]
            if len(month_df) < MIN_TEST_SAMPLES:
                continue

            all_scores = _predict_scores(bundle, coin_df, feature_cols)
            calibration = _calibrate_coin(coin_df=coin_df, month_start=month_start, scores_history=all_scores, base_config=best_config)
            per_coin_calibrations[symbol].append(
                {
                    "month": month_start.strftime("%Y-%m"),
                    "threshold": calibration["threshold"],
                    "position_scale": calibration["position_scale"],
                    "trade_mode": calibration["trade_mode"],
                    "calibration_score": calibration["calibration_score"],
                    "samples": calibration["samples"],
                    "used_default": calibration["used_default"],
                }
            )

            test_scores = all_scores[(coin_df.index >= month_start) & (coin_df.index < month_end)]
            for i, dt in enumerate(month_df.index):
                per_coin_rows[symbol].append(
                    {
                        "date": dt,
                        "close": float(month_df.iloc[i]["close"]),
                        "target_return": float(month_df.iloc[i]["target"]),
                        "prediction_score": float(test_scores[i]),
                        "threshold": float(calibration["threshold"]),
                        "position_scale": float(calibration["position_scale"]),
                        "trade_mode": str(calibration["trade_mode"]),
                    }
                )

    timestamp_tag = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    verification_dir = reports_dir / f"verification_{timestamp_tag}"
    verification_dir.mkdir(parents=True, exist_ok=True)

    results_by_symbol = []
    summary_rows = []

    for symbol in available_eval:
        rows = per_coin_rows.get(symbol, [])
        if not rows:
            continue

        sdf = pd.DataFrame(rows).sort_values("date")
        sdf = sdf.drop_duplicates(subset=["date"], keep="last")
        sdf.index = pd.to_datetime(sdf["date"])

        returns = sdf["target_return"].to_numpy(dtype=float)
        scores = sdf["prediction_score"].to_numpy(dtype=float)

        model_positions = np.array(
            [
                _score_to_position(
                    score=float(scores[i]),
                    threshold=float(sdf.iloc[i]["threshold"]),
                    trade_mode=str(sdf.iloc[i]["trade_mode"]),
                    position_scale=float(sdf.iloc[i]["position_scale"]),
                )
                for i in range(len(sdf))
            ],
            dtype=float,
        )

        model_sim = _simulate_from_positions(returns, model_positions, TRADE_COST_RATE)
        model_metrics = _metrics_from_returns(
            daily_returns=model_sim["daily_returns"],
            index=sdf.index,
            trade_count=model_sim["trade_count"],
            active_positions=model_positions,
            underlying_returns=returns,
        )

        buyhold_metrics, buyhold_daily = _build_buyhold_metrics(returns, sdf.index)

        oracle = _oracle_best_path(returns, TRADE_COST_RATE)
        oracle_metrics = _metrics_from_returns(
            daily_returns=oracle["daily_returns"],
            index=sdf.index,
            trade_count=oracle["trade_count"],
            active_positions=oracle["positions"],
            underlying_returns=returns,
        )

        oracle_total = float(oracle_metrics["total_return"])
        model_total = float(model_metrics["total_return"])
        capture_ratio = model_total / oracle_total if abs(oracle_total) > 1e-12 else 0.0
        action_match_rate = float(np.mean(model_positions == oracle["positions"])) if len(model_positions) else 0.0

        gap = {
            "return_gap": float(oracle_total - model_total),
            "capture_ratio": float(capture_ratio),
            "action_match_rate": float(action_match_rate),
            "avg_daily_return_gap": float(np.mean(oracle["daily_returns"] - model_sim["daily_returns"])) if len(model_sim["daily_returns"]) else 0.0,
        }

        acceptance = _coin_acceptance(model_metrics, buyhold_metrics)
        calibration_summary = _summarize_calibration(per_coin_calibrations[symbol])

        verify_df = pd.DataFrame(
            {
                "date": sdf.index.strftime("%Y-%m-%d"),
                "close": sdf["close"].to_numpy(dtype=float),
                "target_return": returns,
                "prediction_score": scores,
                "threshold": sdf["threshold"].to_numpy(dtype=float),
                "position_scale": sdf["position_scale"].to_numpy(dtype=float),
                "trade_mode": sdf["trade_mode"].to_numpy(),
                "model_position": model_positions,
                "oracle_position": oracle["positions"],
                "model_return": model_sim["daily_returns"],
                "buyhold_return": buyhold_daily,
                "oracle_return": oracle["daily_returns"],
                "oracle_minus_model": oracle["daily_returns"] - model_sim["daily_returns"],
            }
        )
        verify_path = verification_dir / f"{symbol}_daily_verification.csv"
        verify_df.to_csv(verify_path, index=False)

        results_by_symbol.append(
            {
                "symbol": symbol,
                "samples_evaluated": int(len(sdf)),
                "model_walkforward": model_metrics,
                "buy_and_hold": buyhold_metrics,
                "oracle_best_possible": oracle_metrics,
                "gap": gap,
                "acceptance": acceptance,
                "calibration_summary": calibration_summary,
                "daily_verification_path": str(verify_path),
            }
        )

        summary_rows.append(
            {
                "symbol": symbol,
                "samples": len(sdf),
                "model_total_return": model_metrics["total_return"],
                "buyhold_total_return": buyhold_metrics["total_return"],
                "oracle_total_return": oracle_metrics["total_return"],
                "return_gap": gap["return_gap"],
                "capture_ratio": gap["capture_ratio"],
                "model_sharpe": model_metrics["sharpe"],
                "model_sortino": model_metrics["sortino"],
                "model_max_drawdown": model_metrics["max_drawdown"],
                "buyhold_sharpe": buyhold_metrics["sharpe"],
                "acceptance_pass": acceptance["accepted"],
            }
        )

    if not results_by_symbol:
        raise RuntimeError("No symbol produced walk-forward evaluation results")

    accepted_count = sum(1 for r in results_by_symbol if r["acceptance"]["accepted"])
    summary = {
        "symbols_evaluated": int(len(results_by_symbol)),
        "symbols_accepted": int(accepted_count),
        "acceptance_rate": float(accepted_count / max(len(results_by_symbol), 1)),
        "avg_model_total_return": float(np.mean([r["model_walkforward"]["total_return"] for r in results_by_symbol])),
        "avg_buyhold_total_return": float(np.mean([r["buy_and_hold"]["total_return"] for r in results_by_symbol])),
        "avg_excess_vs_buyhold": float(
            np.mean([r["model_walkforward"]["total_return"] - r["buy_and_hold"]["total_return"] for r in results_by_symbol])
        ),
        "avg_oracle_total_return": float(np.mean([r["oracle_best_possible"]["total_return"] for r in results_by_symbol])),
        "avg_return_gap": float(np.mean([r["gap"]["return_gap"] for r in results_by_symbol])),
        "avg_capture_ratio": float(np.mean([r["gap"]["capture_ratio"] for r in results_by_symbol])),
        "avg_model_sharpe": float(np.mean([r["model_walkforward"]["sharpe"] for r in results_by_symbol])),
        "avg_buyhold_sharpe": float(np.mean([r["buy_and_hold"]["sharpe"] for r in results_by_symbol])),
        "trade_cost_bps": float(TRADE_COST_BPS),
    }

    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "train_symbol": TRAIN_SYMBOL,
        "years": YEARS,
        "date_range": {"start": start_date, "end": end_date},
        "pipeline": {
            "global_model_policy": "Single pooled multi-coin model retrained monthly, reused across all coins",
            "walk_forward_mode": "Monthly strict out-of-sample",
            "per_coin_calibration": "Enabled (threshold, trade mode, position scale) using trailing historical window only",
            "autorresearch_objective": "Maximize excess return vs buy-and-hold with risk penalties across all evaluation coins",
            "acceptance_thresholds": ACCEPTANCE_THRESHOLDS,
        },
        "autorresearch": auto,
        "evaluation_symbols": available_eval,
        "results_by_symbol": results_by_symbol,
        "summary": summary,
        "anti_cheat_note": (
            "Oracle path is computed from future returns and used only for verification. "
            "Training and calibration use historical data only."
        ),
    }

    summary_df = pd.DataFrame(summary_rows).sort_values("symbol")
    report_path = reports_dir / f"crypto_autoresearch_7y_{timestamp_tag}.json"
    summary_csv_path = reports_dir / f"crypto_autoresearch_7y_{timestamp_tag}.csv"

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    summary_df.to_csv(summary_csv_path, index=False)

    report["report_path"] = str(report_path)
    report["summary_csv_path"] = str(summary_csv_path)
    report["verification_dir"] = str(verification_dir)

    # Keep paths inside persisted JSON as well.
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report
