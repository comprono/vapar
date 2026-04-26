from __future__ import annotations

import json
import math
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.preprocessing import StandardScaler

from backend.backtest.data_loader import DataLoader

UTC = timezone.utc


TRAIN_SYMBOL = "BTC-USD"
TRAIN_SYMBOLS: List[str] | None = None
AUTORESEARCH_EVAL_SYMBOLS: List[str] | None = None
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
_FINAL_WALKFORWARD_CONTEXT: Dict[str, Any] = {}
AUTORESEARCH_MONTH_STRIDE = 2

ACCEPTANCE_THRESHOLDS = {
    "must_beat_buyhold": True,
    "min_sharpe": 0.25,
    "min_sortino": 0.35,
    "max_drawdown": 0.50,
    "max_trade_rate": 0.55,
    "max_turnover_per_day": 0.65,
    "max_active_rate": 0.85,
}

DEFAULT_CONFIGS = [
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0450,
        "threshold": 0.0010,
        "max_iter": 240,
        "trade_mode": "long_short",
        "model_kind": "gbt_oracle_portfolio",
        "top_k": 1,
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
        "objective": "oracle_portfolio_selector",
    },
    {
        "hidden_layers": [96, 48],
        "alpha": 0.0005,
        "learning_rate_init": 0.0010,
        "threshold": 0.0010,
        "max_iter": 200,
        "trade_mode": "long_short",
        "model_kind": "oracle_portfolio",
        "top_k": 1,
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
        "objective": "oracle_portfolio_selector",
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0450,
        "threshold": 0.0,
        "max_iter": 220,
        "trade_mode": "long_short",
        "model_kind": "gbt_oracle_action",
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
        "objective": "oracle_action_labels",
    },
    {
        "hidden_layers": [96, 48],
        "alpha": 0.0005,
        "learning_rate_init": 0.0010,
        "threshold": 0.0,
        "max_iter": 180,
        "trade_mode": "long_short",
        "model_kind": "oracle_action",
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
        "objective": "oracle_action_labels",
    },
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
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0500,
        "threshold": 0.0030,
        "max_iter": 220,
        "trade_mode": "long_only",
        "model_kind": "gbt_regression",
        "trend_filter": True,
        "trend_min": 0.0000,
        "momentum_min": 0.0000,
        "max_vol_20": 0.0600,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0400,
        "threshold": 0.0600,
        "max_iter": 240,
        "trade_mode": "long_only",
        "model_kind": "gbt_classification",
        "trend_filter": True,
        "trend_min": 0.0000,
        "momentum_min": 0.0000,
        "max_vol_20": 0.0600,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0500,
        "threshold": 1.0e9,
        "max_iter": 80,
        "trade_mode": "flat",
        "model_kind": "gbt_regression",
        "trend_filter": False,
        "trend_min": 0.0000,
        "momentum_min": 0.0000,
        "max_vol_20": None,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0100,
        "threshold": 0.0350,
        "max_iter": 80,
        "trade_mode": "long_only",
        "model_kind": "trend_following",
        "trend_filter": True,
        "trend_min": 0.0000,
        "momentum_min": 0.0000,
        "max_vol_20": 0.0900,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0100,
        "threshold": 0.0750,
        "max_iter": 80,
        "trade_mode": "long_only",
        "model_kind": "trend_following",
        "trend_filter": True,
        "trend_min": 0.0020,
        "momentum_min": 0.0050,
        "max_vol_20": 0.0750,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0100,
        "threshold": 0.0,
        "max_iter": 80,
        "trade_mode": "long_only",
        "model_kind": "buy_hold",
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0100,
        "threshold": 0.0,
        "max_iter": 80,
        "trade_mode": "long_only",
        "model_kind": "xmom_topk",
        "top_k": 1,
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0100,
        "threshold": 0.0,
        "max_iter": 80,
        "trade_mode": "long_only",
        "model_kind": "xmom_topk",
        "top_k": 2,
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0100,
        "threshold": 0.0,
        "max_iter": 80,
        "trade_mode": "long_only",
        "model_kind": "xmom_topk",
        "top_k": 4,
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0100,
        "threshold": 0.0,
        "max_iter": 80,
        "trade_mode": "long_only",
        "model_kind": "trend_120",
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0100,
        "threshold": 0.08,
        "max_iter": 80,
        "trade_mode": "long_only",
        "model_kind": "trend_120",
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0100,
        "threshold": 0.0,
        "max_iter": 80,
        "trade_mode": "long_only",
        "model_kind": "xmom_topk",
        "top_k": 3,
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
    },
    {
        "hidden_layers": [64, 32],
        "alpha": 0.0001,
        "learning_rate_init": 0.0100,
        "threshold": 0.0,
        "max_iter": 80,
        "trade_mode": "long_only",
        "model_kind": "xmom_topk",
        "top_k": 5,
        "trend_filter": False,
        "trend_min": 0.0,
        "momentum_min": 0.0,
        "max_vol_20": None,
    },
]


@dataclass
class ModelBundle:
    scaler: StandardScaler
    model: Any
    model_kind: str
    edge_model: Any | None = None
    size_model: Any | None = None
    cost_model: Any | None = None


ORACLE_ACTION_MODEL_KINDS = {"oracle_action", "gbt_oracle_action", "oracle_portfolio", "gbt_oracle_portfolio"}
ORACLE_PORTFOLIO_MODEL_KINDS = {"oracle_portfolio", "gbt_oracle_portfolio"}


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
    feat["mom_60"] = close / close.shift(60) - 1.0
    feat["mom_120"] = close / close.shift(120) - 1.0
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
        "mom_60",
        "mom_120",
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


def _state_turnover(prev_state: Tuple[str, float], next_state: Tuple[str, float]) -> float:
    prev_symbol, prev_side = prev_state
    next_symbol, next_side = next_state
    if prev_symbol == next_symbol:
        return abs(float(next_side) - float(prev_side))
    return abs(float(prev_side)) + abs(float(next_side))


def _add_cross_sectional_features(prepared: Dict[str, pd.DataFrame], feature_cols: List[str]) -> List[str]:
    source_cols = ["ret_1", "mom_20", "mom_60", "mom_120", "ema_spread", "vol_20"]
    added_cols = [f"cs_rank_{col}" for col in source_cols]
    if not prepared:
        return feature_cols

    for col, out_col in zip(source_cols, added_cols):
        pieces = []
        for symbol, frame in prepared.items():
            if col not in frame.columns:
                continue
            s = frame[col].rename(symbol)
            pieces.append(s)
        if not pieces:
            continue

        wide = pd.concat(pieces, axis=1).sort_index()
        ranks = wide.rank(axis=1, pct=True).fillna(0.5)
        for symbol, frame in prepared.items():
            if symbol in ranks.columns:
                frame[out_col] = ranks[symbol].reindex(frame.index).fillna(0.5).astype(float)
            else:
                frame[out_col] = 0.5

    return list(dict.fromkeys(feature_cols + added_cols))


def _oracle_portfolio_label_rows(
    returns_by_date: Dict[pd.Timestamp, Dict[str, float]],
    symbols: List[str],
    trade_cost_rate: float,
) -> Dict[str, Dict[pd.Timestamp, Dict[str, Any]]]:
    available = [symbol for symbol in symbols if any(symbol in row for row in returns_by_date.values())]
    all_dates = sorted(returns_by_date)
    label_rows: Dict[str, Dict[pd.Timestamp, Dict[str, Any]]] = {symbol: {} for symbol in available}
    if not available or not all_dates:
        return label_rows

    states: List[Tuple[str, float]] = [("CASH", 0.0)]
    for symbol in available:
        states.append((symbol, -1.0))
        states.append((symbol, 1.0))

    n = len(all_dates)
    state_count = len(states)
    cash_idx = 0
    dp = np.full((n, state_count), -np.inf, dtype=float)
    parent = np.zeros((n, state_count), dtype=int)

    for s_idx, state in enumerate(states):
        symbol, side = state
        gross_edge = 0.0 if symbol == "CASH" else side * returns_by_date[all_dates[0]].get(symbol, 0.0)
        switch_cost = trade_cost_rate * _state_turnover(states[cash_idx], state)
        dp[0, s_idx] = math.log(max(1.0 + gross_edge - switch_cost, 1e-12))
        parent[0, s_idx] = cash_idx

    for t in range(1, n):
        day_returns = returns_by_date[all_dates[t]]
        for s_idx, state in enumerate(states):
            symbol, side = state
            gross_edge = 0.0 if symbol == "CASH" else side * day_returns.get(symbol, 0.0)
            best_score = -np.inf
            best_prev = cash_idx
            for p_idx, prev_state in enumerate(states):
                switch_cost = trade_cost_rate * _state_turnover(prev_state, state)
                net_edge = gross_edge - switch_cost
                score = dp[t - 1, p_idx] + math.log(max(1.0 + net_edge, 1e-12))
                if score > best_score:
                    best_score = score
                    best_prev = p_idx
            dp[t, s_idx] = best_score
            parent[t, s_idx] = best_prev

    path_idx = np.zeros(n, dtype=int)
    path_idx[-1] = int(np.argmax(dp[-1]))
    for t in range(n - 1, 0, -1):
        path_idx[t - 1] = parent[t, path_idx[t]]

    prev_state = states[cash_idx]
    for t, dt in enumerate(all_dates):
        state = states[int(path_idx[t])]
        selected_symbol, selected_side = state
        day_returns = returns_by_date[dt]
        switch_cost = trade_cost_rate * _state_turnover(prev_state, state)
        gross_edge = 0.0 if selected_symbol == "CASH" else selected_side * day_returns.get(selected_symbol, 0.0)
        net_edge = gross_edge - switch_cost

        for symbol in available:
            action = selected_side if symbol == selected_symbol else 0.0
            label_rows[symbol][dt] = {
                "oracle_selected_symbol": selected_symbol,
                "oracle_action": float(action),
                "oracle_action_label": int(action + 1.0),
                "oracle_is_selected": bool(symbol == selected_symbol),
                "oracle_gross_edge": float(gross_edge if symbol == selected_symbol else 0.0),
                "oracle_expected_edge": float(net_edge if symbol == selected_symbol else 0.0),
                "oracle_position_size": float(1.0 if symbol == selected_symbol else 0.0),
                "oracle_switching_cost": float(switch_cost if symbol == selected_symbol else 0.0),
            }
        prev_state = state

    return label_rows


def _add_oracle_action_labels(
    prepared: Dict[str, pd.DataFrame],
    symbols: List[str],
    trade_cost_rate: float,
) -> None:
    available = [symbol for symbol in symbols if symbol in prepared]
    if not available:
        return

    returns_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
    for symbol in available:
        frame = prepared[symbol]
        for dt, row in frame.iterrows():
            if pd.notna(row.get("target")):
                returns_by_date.setdefault(pd.Timestamp(dt), {})[symbol] = float(row["target"])

    label_rows = _oracle_portfolio_label_rows(returns_by_date, available, trade_cost_rate)

    for symbol in available:
        labels = pd.DataFrame.from_dict(label_rows[symbol], orient="index")
        prepared[symbol] = prepared[symbol].join(labels, how="left")
        prepared[symbol]["oracle_selected_symbol"] = prepared[symbol]["oracle_selected_symbol"].fillna("CASH")
        numeric_defaults = {
            "oracle_action": 0.0,
            "oracle_action_label": 1,
            "oracle_gross_edge": 0.0,
            "oracle_expected_edge": 0.0,
            "oracle_position_size": 0.0,
            "oracle_switching_cost": 0.0,
        }
        for col, default in numeric_defaults.items():
            prepared[symbol][col] = prepared[symbol][col].fillna(default)
        prepared[symbol]["oracle_is_selected"] = prepared[symbol]["oracle_is_selected"].fillna(False).astype(bool)


def _fit_model(train_df: pd.DataFrame, feature_cols: List[str], config: Dict[str, Any]) -> ModelBundle:
    x_train = train_df[feature_cols].to_numpy(dtype=float)
    y_train_raw = train_df["target"].to_numpy(dtype=float)

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)

    hidden_layers = tuple(config["hidden_layers"])
    model_kind = str(config["model_kind"])

    if model_kind in {"trend_following", "trend_120", "xmom_topk", "buy_hold"}:
        model = None
    elif model_kind in ORACLE_ACTION_MODEL_KINDS:
        if "oracle_action_label" in train_df.columns:
            y_action = train_df["oracle_action_label"].to_numpy(dtype=int)
            y_gross_edge = train_df["oracle_gross_edge"].to_numpy(dtype=float)
            y_size = train_df["oracle_position_size"].to_numpy(dtype=float)
            y_switch_cost = train_df["oracle_switching_cost"].to_numpy(dtype=float)
            sample_weight = 1.0 + 4.0 * train_df["oracle_is_selected"].astype(float).to_numpy()
        else:
            y_action = np.where(y_train_raw > TRADE_COST_RATE, 2, np.where(y_train_raw < -TRADE_COST_RATE, 0, 1))
            y_gross_edge = np.abs(y_train_raw)
            y_size = (y_action != 1).astype(float)
            y_switch_cost = np.where(y_action != 1, TRADE_COST_RATE, 0.0)
            sample_weight = 1.0 + 2.0 * (y_action != 1).astype(float)

        if len(np.unique(y_action)) < 2:
            action_model = DummyClassifier(strategy="most_frequent")
            action_model.fit(x_train_scaled, y_action)
        elif model_kind in {"gbt_oracle_action", "gbt_oracle_portfolio"}:
            action_model = HistGradientBoostingClassifier(
                learning_rate=float(config["learning_rate_init"]),
                max_iter=int(config["max_iter"]),
                max_depth=3,
                min_samples_leaf=20,
                l2_regularization=float(config["alpha"]),
                random_state=42,
            )
            action_model.fit(x_train_scaled, y_action, sample_weight=sample_weight)
        else:
            action_model = MLPClassifier(
                hidden_layer_sizes=hidden_layers,
                alpha=float(config["alpha"]),
                learning_rate_init=float(config["learning_rate_init"]),
                max_iter=int(config["max_iter"]),
                early_stopping=True,
                n_iter_no_change=12,
                validation_fraction=0.12,
                random_state=42,
            )
            action_model.fit(x_train_scaled, y_action)

        def fit_regressor(y: np.ndarray) -> Any:
            if float(np.nanstd(y)) <= 1e-12:
                reg = DummyRegressor(strategy="mean")
                reg.fit(x_train_scaled, y)
                return reg
            reg = HistGradientBoostingRegressor(
                learning_rate=float(config["learning_rate_init"]),
                max_iter=int(config["max_iter"]),
                max_depth=3,
                min_samples_leaf=20,
                l2_regularization=float(config["alpha"]),
                random_state=42,
            )
            reg.fit(x_train_scaled, y, sample_weight=sample_weight)
            return reg

        model = action_model
        edge_model = fit_regressor(y_gross_edge)
        size_model = fit_regressor(y_size)
        cost_model = fit_regressor(y_switch_cost)
        return ModelBundle(
            scaler=scaler,
            model=model,
            model_kind=model_kind,
            edge_model=edge_model,
            size_model=size_model,
            cost_model=cost_model,
        )
    elif model_kind == "classification":
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
    elif model_kind == "gbt_classification":
        y_train = (y_train_raw > 0.0).astype(int)
        model = HistGradientBoostingClassifier(
            learning_rate=float(config["learning_rate_init"]),
            max_iter=int(config["max_iter"]),
            max_depth=3,
            min_samples_leaf=20,
            l2_regularization=float(config["alpha"]),
            random_state=42,
        )
        model.fit(x_train_scaled, y_train)
    elif model_kind == "gbt_regression":
        model = HistGradientBoostingRegressor(
            learning_rate=float(config["learning_rate_init"]),
            max_iter=int(config["max_iter"]),
            max_depth=3,
            min_samples_leaf=20,
            l2_regularization=float(config["alpha"]),
            random_state=42,
        )
        model.fit(x_train_scaled, y_train_raw)
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
    if bundle.model_kind == "trend_following":
        mom_120 = feature_df.get("mom_120", pd.Series(0.0, index=feature_df.index)).to_numpy(dtype=float)
        mom_60 = feature_df.get("mom_60", pd.Series(0.0, index=feature_df.index)).to_numpy(dtype=float)
        mom_20 = feature_df.get("mom_20", pd.Series(0.0, index=feature_df.index)).to_numpy(dtype=float)
        ema = feature_df.get("ema_spread", pd.Series(0.0, index=feature_df.index)).to_numpy(dtype=float)
        vol = feature_df.get("vol_20", pd.Series(0.0, index=feature_df.index)).to_numpy(dtype=float)
        return (0.45 * mom_120) + (0.30 * mom_60) + (0.15 * mom_20) + (0.10 * ema) - (0.25 * vol)
    if bundle.model_kind == "buy_hold":
        return np.ones(len(feature_df), dtype=float)
    if bundle.model_kind == "trend_120":
        return feature_df.get("mom_120", pd.Series(0.0, index=feature_df.index)).to_numpy(dtype=float)
    if bundle.model_kind == "xmom_topk":
        return feature_df.get("mom_120", pd.Series(0.0, index=feature_df.index)).to_numpy(dtype=float)

    x = feature_df[feature_cols].to_numpy(dtype=float)
    x_scaled = bundle.scaler.transform(x)

    if bundle.model_kind in ORACLE_ACTION_MODEL_KINDS:
        probs = bundle.model.predict_proba(x_scaled)
        classes = list(getattr(bundle.model, "classes_", []))
        p_short = probs[:, classes.index(0)] if 0 in classes else np.zeros(len(feature_df), dtype=float)
        p_long = probs[:, classes.index(2)] if 2 in classes else np.zeros(len(feature_df), dtype=float)
        gross_edge = np.maximum(bundle.edge_model.predict(x_scaled), 0.0) if bundle.edge_model is not None else 0.0
        position_size = bundle.size_model.predict(x_scaled) if bundle.size_model is not None else 1.0
        switch_cost = np.maximum(bundle.cost_model.predict(x_scaled), 0.0) if bundle.cost_model is not None else 0.0
        position_size = np.clip(position_size, 0.0, 1.0)
        net_edge = np.maximum(gross_edge - switch_cost, 0.0)
        return (p_long - p_short) * net_edge * position_size

    if bundle.model_kind in {"classification", "gbt_classification"}:
        probs = bundle.model.predict_proba(x_scaled)[:, 1]
        return (probs - 0.5) * 2.0

    return bundle.model.predict(x_scaled)


def _passes_trade_filter(position: float, feature_row: pd.Series | None, config: Dict[str, Any] | None) -> bool:
    if feature_row is None or config is None:
        return True

    max_vol_20 = config.get("max_vol_20")
    if max_vol_20 is not None and float(feature_row.get("vol_20", 0.0)) > float(max_vol_20):
        return False

    if not bool(config.get("trend_filter", False)):
        return True

    ema_spread = float(feature_row.get("ema_spread", 0.0))
    momentum = float(feature_row.get("mom_20", 0.0))
    trend_min = float(config.get("trend_min", 0.0))
    momentum_min = float(config.get("momentum_min", 0.0))

    if position > 0.0:
        return ema_spread >= trend_min and momentum >= momentum_min
    if position < 0.0:
        return ema_spread <= -trend_min and momentum <= -momentum_min
    return True


def _score_to_position(
    score: float,
    threshold: float,
    trade_mode: str,
    position_scale: float,
    feature_row: pd.Series | None = None,
    config: Dict[str, Any] | None = None,
) -> float:
    if trade_mode == "flat" or position_scale <= 0.0:
        return 0.0

    pos = 0.0
    if trade_mode == "long_only":
        pos = float(position_scale) if score > threshold else 0.0
    elif score > threshold:
        pos = float(position_scale)
    elif score < -threshold:
        pos = -float(position_scale)

    if pos == 0.0 or _passes_trade_filter(pos, feature_row, config):
        return pos
    return 0.0


def _positions_from_scores(
    scores: np.ndarray,
    feature_df: pd.DataFrame,
    threshold: float,
    trade_mode: str,
    position_scale: float,
    config: Dict[str, Any] | None,
) -> np.ndarray:
    return np.array(
        [
            _score_to_position(
                score=float(scores[i]),
                threshold=float(threshold),
                trade_mode=str(trade_mode),
                position_scale=float(position_scale),
                feature_row=feature_df.iloc[i],
                config=config,
            )
            for i in range(len(scores))
        ],
        dtype=float,
    )


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
    turnover: np.ndarray | None = None,
) -> Dict[str, Any]:
    if len(daily_returns) == 0:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "trade_count": int(trade_count),
            "trade_rate": 0.0,
            "avg_turnover_per_day": 0.0,
            "total_turnover": 0.0,
            "active_rate": 0.0,
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
    trade_rate = float(trade_count / max(n, 1))

    daily_hit_rate = 0.0
    active_rate = 0.0
    if active_positions is not None and underlying_returns is not None and len(active_positions) == len(underlying_returns):
        active = np.abs(active_positions) > 1e-12
        active_rate = float(np.mean(active))
        if np.any(active):
            signed = np.sign(active_positions[active]) * np.sign(underlying_returns[active])
            daily_hit_rate = float((signed > 0).mean())

    turnover_arr = None
    if turnover is not None and len(turnover) == len(daily_returns):
        turnover_arr = np.asarray(turnover, dtype=float)
    elif active_positions is not None and len(active_positions) == len(daily_returns):
        pos = np.asarray(active_positions, dtype=float)
        turnover_arr = np.abs(pos - np.concatenate(([0.0], pos[:-1])))

    avg_turnover_per_day = float(np.mean(turnover_arr)) if turnover_arr is not None else 0.0
    total_turnover = float(np.sum(turnover_arr)) if turnover_arr is not None else 0.0

    monthly, yearly = _to_monthly_yearly(daily_returns, index)

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "trade_count": int(trade_count),
        "trade_rate": trade_rate,
        "avg_turnover_per_day": avg_turnover_per_day,
        "total_turnover": total_turnover,
        "active_rate": active_rate,
        "win_rate": win_rate,
        "daily_hit_rate": daily_hit_rate,
        "monthly_returns": monthly,
        "yearly_returns": yearly,
    }


def _bounded_metric(value: float, limit: float = 3.0) -> float:
    value = float(value)
    if not math.isfinite(value):
        return 0.0
    return float(max(-limit, min(limit, value)))


def _oracle_best_path(returns: np.ndarray, trade_cost_rate: float) -> Dict[str, Any]:
    n = len(returns)
    if n == 0:
        return {
            "positions": np.array([], dtype=float),
            "daily_returns": np.array([], dtype=float),
            "turnover": np.array([], dtype=float),
            "trade_count": 0,
        }

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
        "turnover": sim["turnover"],
        "trade_count": sim["trade_count"],
    }


def _score_validation(
    model_metrics: Dict[str, Any],
    buyhold_metrics: Dict[str, Any],
    gap: Dict[str, float] | None = None,
) -> float:
    excess = float(model_metrics["total_return"] - buyhold_metrics["total_return"])
    trade_rate = float(model_metrics.get("trade_rate", 0.0))
    avg_turnover = float(model_metrics.get("avg_turnover_per_day", 0.0))
    active_rate = float(model_metrics.get("active_rate", 0.0))
    return (
        excess
        + 0.45 * _bounded_metric(float(model_metrics["sharpe"]))
        + 0.25 * _bounded_metric(float(model_metrics["sortino"]))
        - 1.10 * float(model_metrics["max_drawdown"])
        - 0.25 * trade_rate
        - 0.40 * avg_turnover
        - 0.20 * max(active_rate - 0.82, 0.0)
    )


def _calibration_candidates(base_threshold: float) -> List[Tuple[float, float, str]]:
    base = max(float(base_threshold), 0.0020)
    thresholds = sorted(
        {
            base * 0.75,
            base,
            base * 1.5,
            base * 2.0,
            base * 2.75,
            0.0030,
            0.0050,
            0.0080,
            0.0120,
        }
    )
    scales = [0.35, 0.50, 0.75, 1.00]
    modes = ["long_only", "long_short"]
    candidates: List[Tuple[float, float, str]] = []
    for th in thresholds:
        for sc in scales:
            for md in modes:
                candidates.append((float(th), float(sc), md))
    candidates.append((1.0e9, 0.0, "flat"))
    return candidates


def _calibrate_coin(
    coin_df: pd.DataFrame,
    month_start: pd.Timestamp,
    scores_history: np.ndarray,
    base_config: Dict[str, Any],
) -> Dict[str, Any]:
    if str(base_config.get("model_kind")) in ORACLE_PORTFOLIO_MODEL_KINDS:
        return {
            "threshold": float(base_config.get("threshold", 0.0)),
            "position_scale": 1.0,
            "trade_mode": str(base_config.get("trade_mode", "long_short")),
            "calibration_score": 0.0,
            "samples": 0,
            "used_default": False,
        }

    if str(base_config.get("model_kind")) == "buy_hold":
        return {
            "threshold": 0.0,
            "position_scale": 1.0,
            "trade_mode": "long_only",
            "calibration_score": 0.0,
            "samples": 0,
            "used_default": False,
        }

    if str(base_config.get("trade_mode")) == "flat":
        return {
            "threshold": 1.0e9,
            "position_scale": 0.0,
            "trade_mode": "flat",
            "calibration_score": 0.0,
            "samples": 0,
            "used_default": False,
        }

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
        positions = _positions_from_scores(
            scores=cal_scores,
            feature_df=cal_df,
            threshold=threshold,
            trade_mode=mode,
            position_scale=scale,
            config=base_config,
        )
        sim = _simulate_from_positions(cal_returns, positions, TRADE_COST_RATE)
        perf = _metrics_from_returns(
            daily_returns=sim["daily_returns"],
            index=idx,
            trade_count=sim["trade_count"],
            active_positions=positions,
            underlying_returns=cal_returns,
            turnover=sim["turnover"],
        )
        trade_rate = float(perf.get("trade_rate", 0.0))
        avg_turnover = float(perf.get("avg_turnover_per_day", 0.0))
        active_rate = float(perf.get("active_rate", 0.0))
        total_return = float(perf["total_return"])
        negative_return_penalty = 1.5 * abs(min(total_return, 0.0))
        objective = (
            total_return
            + 0.08 * _bounded_metric(float(perf["sharpe"]), limit=2.0)
            + 0.04 * _bounded_metric(float(perf["sortino"]), limit=2.0)
            - 1.20 * float(perf["max_drawdown"])
            - 0.20 * trade_rate
            - 0.45 * avg_turnover
            - 0.20 * max(active_rate - 0.80, 0.0)
            - negative_return_penalty
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
        turnover=sim["turnover"],
    )
    return metrics, sim["daily_returns"]


def _build_pooled_train_frame(
    prepared: Dict[str, pd.DataFrame],
    train_symbols: List[str],
    month_start: pd.Timestamp,
) -> pd.DataFrame:
    train_start = month_start - pd.Timedelta(days=TRAIN_LOOKBACK_DAYS)
    frames_by_symbol: Dict[str, pd.DataFrame] = {}

    for symbol in train_symbols:
        if symbol not in prepared:
            continue
        sdf = prepared[symbol]
        part = sdf[(sdf.index < month_start) & (sdf.index >= train_start)]
        if len(part) < MIN_TEST_SAMPLES:
            continue
        frames_by_symbol[symbol] = part.copy()

    if not frames_by_symbol:
        return pd.DataFrame()

    returns_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
    for symbol, frame in frames_by_symbol.items():
        for dt, row in frame.iterrows():
            if pd.notna(row.get("target")):
                returns_by_date.setdefault(pd.Timestamp(dt), {})[symbol] = float(row["target"])

    label_rows = _oracle_portfolio_label_rows(returns_by_date, list(frames_by_symbol), TRADE_COST_RATE)
    frames: List[pd.DataFrame] = []
    for symbol, frame in frames_by_symbol.items():
        labels = pd.DataFrame.from_dict(label_rows.get(symbol, {}), orient="index")
        part = frame.drop(
            columns=[
                "oracle_selected_symbol",
                "oracle_action",
                "oracle_action_label",
                "oracle_is_selected",
                "oracle_gross_edge",
                "oracle_expected_edge",
                "oracle_position_size",
                "oracle_switching_cost",
            ],
            errors="ignore",
        ).join(labels, how="left")
        part["symbol"] = symbol
        frames.append(part)

    pooled = pd.concat(frames, axis=0).sort_index()
    return pooled


def _run_cross_sectional_momentum_for_config(
    prepared: Dict[str, pd.DataFrame],
    train_symbols: List[str],
    eval_symbols: List[str],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    ref_symbol = train_symbols[0]
    month_starts = _iter_month_starts(prepared[ref_symbol].index)
    top_k = max(1, int(config.get("top_k", 5)))
    threshold = float(config.get("threshold", 0.0))

    returns_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
    positions_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
    prev_weights = {symbol: 0.0 for symbol in eval_symbols}

    for month_idx, month_start in enumerate(month_starts):
        if month_idx % AUTORESEARCH_MONTH_STRIDE != 0:
            continue
        if len(_build_pooled_train_frame(prepared, train_symbols, month_start)) < MIN_TRAIN_SAMPLES:
            continue

        month_end = month_start + pd.offsets.MonthBegin(1)
        scores: Dict[str, float] = {}
        month_frames: Dict[str, pd.DataFrame] = {}
        for symbol in eval_symbols:
            coin_df = prepared[symbol]
            month_df = coin_df[(coin_df.index >= month_start) & (coin_df.index < month_end)]
            if len(month_df) < MIN_TEST_SAMPLES:
                continue
            scores[symbol] = float(month_df.iloc[0].get("mom_120", 0.0))
            month_frames[symbol] = month_df

        ranked = [
            symbol
            for symbol, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
            if score > threshold
        ][:top_k]
        weights = {symbol: 0.0 for symbol in eval_symbols}
        if ranked:
            weight = 1.0 / len(ranked)
            for symbol in ranked:
                weights[symbol] = weight

        all_dates = sorted({dt for frame in month_frames.values() for dt in frame.index})
        for day_idx, dt in enumerate(all_dates):
            returns_by_date.setdefault(dt, {})
            positions_by_date.setdefault(dt, {})
            for symbol, frame in month_frames.items():
                if dt not in frame.index:
                    continue
                returns_by_date[dt][symbol] = float(frame.loc[dt, "target"])
                positions_by_date[dt][symbol] = float(weights.get(symbol, 0.0))

        prev_weights = weights

    if not returns_by_date:
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

    dates = sorted(returns_by_date)
    daily_model: List[float] = []
    daily_buyhold: List[float] = []
    active_exposure: List[float] = []
    turnover: List[float] = []
    prev = {symbol: 0.0 for symbol in eval_symbols}
    for dt in dates:
        day_returns = returns_by_date[dt]
        pos = positions_by_date.get(dt, {})
        turn = sum(abs(float(pos.get(symbol, 0.0)) - prev.get(symbol, 0.0)) for symbol in eval_symbols)
        model_ret = sum(float(pos.get(symbol, 0.0)) * day_returns.get(symbol, 0.0) for symbol in eval_symbols)
        model_ret -= TRADE_COST_RATE * turn
        active_symbols = [symbol for symbol in eval_symbols if symbol in day_returns]
        buy_ret = float(np.mean([day_returns[symbol] for symbol in active_symbols])) if active_symbols else 0.0
        if turn > 0.0:
            prev = {symbol: float(pos.get(symbol, 0.0)) for symbol in eval_symbols}
        daily_model.append(float(model_ret))
        daily_buyhold.append(float(buy_ret))
        active_exposure.append(float(sum(abs(pos.get(symbol, 0.0)) for symbol in eval_symbols)))
        turnover.append(float(turn))

    index = pd.DatetimeIndex(dates)
    model_validation = _metrics_from_returns(
        np.asarray(daily_model, dtype=float),
        index,
        trade_count=int(sum(1 for x in turnover if x > 1e-12)),
        active_positions=np.asarray(active_exposure, dtype=float),
        underlying_returns=np.asarray(daily_buyhold, dtype=float),
        turnover=np.asarray(turnover, dtype=float),
    )
    buyhold_validation = _metrics_from_returns(
        np.asarray(daily_buyhold, dtype=float),
        index,
        trade_count=1,
        active_positions=np.ones(len(daily_buyhold), dtype=float),
        underlying_returns=np.asarray(daily_buyhold, dtype=float),
        turnover=np.zeros(len(daily_buyhold), dtype=float),
    )
    excess = float(model_validation["total_return"] - buyhold_validation["total_return"])
    outperform_rate = float(np.mean(np.asarray(daily_model) > np.asarray(daily_buyhold)))
    relative_capture = float(model_validation["total_return"] / max(abs(float(buyhold_validation["total_return"])), 1e-9))
    gap_validation = {
        "excess_vs_buyhold": excess,
        "relative_capture_vs_buyhold": relative_capture,
        "outperform_rate": outperform_rate,
    }
    score = (
        3.50 * excess
        + 0.15 * _bounded_metric(float(model_validation["sharpe"]))
        + 0.05 * _bounded_metric(float(model_validation["sortino"]))
        - 0.10 * float(model_validation["max_drawdown"])
        + 0.35 * outperform_rate
        - 0.05 * float(model_validation.get("trade_rate", 0.0))
        - 0.05 * float(model_validation.get("avg_turnover_per_day", 0.0))
    )
    if excess < 0.0:
        score -= 2.0 + 20.0 * abs(excess)

    return {
        "score": float(score),
        "model_validation": model_validation,
        "buyhold_validation": buyhold_validation,
        "oracle_validation": {},
        "gap_validation": gap_validation,
        "selection_penalties": {
            "negative_excess_penalty": float(2.0 + 20.0 * abs(excess)) if excess < 0.0 else 0.0,
            "weak_model_edge_penalty": 0.0,
        },
        "days_scored": int(len(dates)),
        "symbols_used": int(len(eval_symbols)),
    }


def _score_portfolio_candidates(
    scores: Dict[str, float],
    threshold: float,
    trade_mode: str,
    top_k: int,
    position_scale: float = 1.0,
) -> Dict[str, float]:
    if trade_mode == "flat" or position_scale <= 0.0:
        return {symbol: 0.0 for symbol in scores}

    candidates: List[Tuple[str, float, float]] = []
    for symbol, score in scores.items():
        score = float(score)
        if trade_mode == "long_only":
            if score > threshold:
                candidates.append((symbol, score, 1.0))
        else:
            if abs(score) > threshold:
                candidates.append((symbol, abs(score), 1.0 if score > 0.0 else -1.0))

    ranked = sorted(candidates, key=lambda item: item[1], reverse=True)[: max(1, int(top_k))]
    weights = {symbol: 0.0 for symbol in scores}
    if ranked:
        weight = float(position_scale) / float(len(ranked))
        for symbol, _, direction in ranked:
            weights[symbol] = weight * direction
    return weights


def _score_portfolio_series(
    returns_by_date: Dict[pd.Timestamp, Dict[str, float]],
    scores_by_date: Dict[pd.Timestamp, Dict[str, float]],
    config: Dict[str, Any],
    oracle_by_date: Dict[pd.Timestamp, Dict[str, Any]] | None = None,
    configs_by_date: Dict[pd.Timestamp, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    dates = sorted(returns_by_date)

    daily_model: List[float] = []
    daily_buyhold: List[float] = []
    active_exposure: List[float] = []
    turnover: List[float] = []
    action_matches: List[float] = []
    edge_captures: List[float] = []
    prev_weights: Dict[str, float] = {}

    for dt in dates:
        day_returns = returns_by_date[dt]
        day_scores = scores_by_date.get(dt, {})
        day_config = configs_by_date.get(dt, config) if configs_by_date else config
        top_k = max(1, int(day_config.get("top_k", config.get("top_k", 1)) or 1))
        threshold = float(day_config.get("threshold", config.get("threshold", 0.0)))
        trade_mode = str(day_config.get("trade_mode", config.get("trade_mode", "long_short")))
        position_scale = float(day_config.get("position_scale", config.get("position_scale", 1.0)))
        weights = _score_portfolio_candidates(
            scores=day_scores,
            threshold=threshold,
            trade_mode=trade_mode,
            top_k=top_k,
            position_scale=position_scale,
        )
        symbols = sorted(set(day_returns) | set(weights) | set(prev_weights))
        turn = sum(abs(float(weights.get(symbol, 0.0)) - float(prev_weights.get(symbol, 0.0))) for symbol in symbols)
        model_ret = sum(float(weights.get(symbol, 0.0)) * float(day_returns.get(symbol, 0.0)) for symbol in symbols)
        model_ret -= TRADE_COST_RATE * turn
        model_ret = max(float(model_ret), -0.999999)

        active_symbols = [symbol for symbol in day_returns if symbol in day_scores]
        buy_ret = float(np.mean([day_returns[symbol] for symbol in active_symbols])) if active_symbols else 0.0

        if oracle_by_date and dt in oracle_by_date:
            oracle = oracle_by_date[dt]
            oracle_symbol = str(oracle.get("symbol", "CASH"))
            oracle_action = float(oracle.get("action", 0.0))
            model_action = float(weights.get(oracle_symbol, 0.0)) if oracle_symbol != "CASH" else 0.0
            matched = (
                abs(oracle_action) < 1e-12 and sum(abs(v) for v in weights.values()) < 1e-12
            ) or (
                oracle_symbol != "CASH"
                and np.sign(model_action) == np.sign(oracle_action)
                and abs(model_action) > 1e-12
            )
            action_matches.append(1.0 if matched else 0.0)
            edge = max(float(oracle.get("edge", 0.0)), 0.0)
            if edge > 1e-12:
                edge_captures.append(1.0 if matched else 0.0)

        daily_model.append(model_ret)
        daily_buyhold.append(buy_ret)
        active_exposure.append(float(sum(abs(v) for v in weights.values())))
        turnover.append(float(turn))
        prev_weights = weights

    index = pd.DatetimeIndex(dates)
    model_validation = _metrics_from_returns(
        np.asarray(daily_model, dtype=float),
        index,
        trade_count=int(sum(1 for x in turnover if x > 1e-12)),
        active_positions=np.asarray(active_exposure, dtype=float),
        underlying_returns=np.asarray(daily_buyhold, dtype=float),
        turnover=np.asarray(turnover, dtype=float),
    )
    buyhold_validation = _metrics_from_returns(
        np.asarray(daily_buyhold, dtype=float),
        index,
        trade_count=1,
        active_positions=np.ones(len(daily_buyhold), dtype=float),
        underlying_returns=np.asarray(daily_buyhold, dtype=float),
        turnover=np.zeros(len(daily_buyhold), dtype=float),
    )
    excess = float(model_validation["total_return"] - buyhold_validation["total_return"])
    outperform_rate = float(np.mean(np.asarray(daily_model) > np.asarray(daily_buyhold))) if daily_model else 0.0
    relative_capture = float(model_validation["total_return"] / max(abs(float(buyhold_validation["total_return"])), 1e-9))
    oracle_action_match_rate = float(np.mean(action_matches)) if action_matches else 0.0
    oracle_edge_capture_rate = float(np.mean(edge_captures)) if edge_captures else 0.0
    score = (
        2.00 * excess
        + 0.35 * _bounded_metric(float(model_validation["sharpe"]))
        + 0.20 * _bounded_metric(float(model_validation["sortino"]))
        - 0.85 * float(model_validation["max_drawdown"])
        + 0.35 * outperform_rate
        + 0.85 * oracle_action_match_rate
        + 1.20 * oracle_edge_capture_rate
        - 0.10 * float(model_validation.get("trade_rate", 0.0))
        - 0.20 * float(model_validation.get("avg_turnover_per_day", 0.0))
    )
    if excess < 0.0:
        score -= 2.0 + 20.0 * abs(excess)

    return {
        "score": float(score),
        "model_validation": model_validation,
        "buyhold_validation": buyhold_validation,
        "oracle_validation": {},
        "gap_validation": {
            "excess_vs_buyhold": excess,
            "relative_capture_vs_buyhold": relative_capture,
            "outperform_rate": outperform_rate,
            "oracle_action_match_rate": oracle_action_match_rate,
            "oracle_edge_capture_rate": oracle_edge_capture_rate,
        },
        "selection_penalties": {
            "negative_excess_penalty": float(2.0 + 20.0 * abs(excess)) if excess < 0.0 else 0.0,
            "weak_model_edge_penalty": 0.0,
        },
        "days_scored": int(len(dates)),
        "symbols_used": int(len({s for row in returns_by_date.values() for s in row})),
    }


def _portfolio_oracle_by_date(
    returns_by_date: Dict[pd.Timestamp, Dict[str, float]],
    symbols: List[str],
) -> Dict[pd.Timestamp, Dict[str, Any]]:
    oracle_label_rows = _oracle_portfolio_label_rows(returns_by_date, symbols, TRADE_COST_RATE)
    oracle_by_date: Dict[pd.Timestamp, Dict[str, Any]] = {}
    for symbol, rows in oracle_label_rows.items():
        for dt, label in rows.items():
            selected = str(label.get("oracle_selected_symbol", "CASH"))
            if selected == symbol:
                oracle_by_date[dt] = {
                    "symbol": selected,
                    "action": float(label.get("oracle_action", 0.0)),
                    "edge": float(label.get("oracle_expected_edge", 0.0)),
                }
            elif selected == "CASH" and dt not in oracle_by_date:
                oracle_by_date[dt] = {"symbol": "CASH", "action": 0.0, "edge": 0.0}
    for dt in returns_by_date:
        oracle_by_date.setdefault(dt, {"symbol": "CASH", "action": 0.0, "edge": 0.0})
    return oracle_by_date


def _portfolio_selector_thresholds(
    scores_by_date: Dict[pd.Timestamp, Dict[str, float]],
    base_threshold: float,
) -> List[float]:
    abs_scores = [
        abs(float(score))
        for day_scores in scores_by_date.values()
        for score in day_scores.values()
        if np.isfinite(float(score)) and abs(float(score)) > 1e-12
    ]
    thresholds = {
        0.0,
        float(base_threshold),
        0.001,
        0.0025,
        0.005,
        0.01,
        0.02,
        0.04,
        0.08,
    }
    if abs_scores:
        values = np.asarray(abs_scores, dtype=float)
        for q in (0.55, 0.70, 0.82, 0.90, 0.95, 0.98):
            thresholds.add(float(np.quantile(values, q)))
    return sorted(t for t in thresholds if np.isfinite(t) and t >= 0.0)


def _calibrate_portfolio_selector(
    returns_by_date: Dict[pd.Timestamp, Dict[str, float]],
    scores_by_date: Dict[pd.Timestamp, Dict[str, float]],
    base_config: Dict[str, Any],
    oracle_by_date: Dict[pd.Timestamp, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    usable_dates = [
        dt
        for dt in sorted(returns_by_date)
        if returns_by_date.get(dt) and scores_by_date.get(dt)
    ]
    if len(usable_dates) < MIN_CALIBRATION_SAMPLES:
        return {
            "threshold": 1.0e9,
            "top_k": 1,
            "position_scale": 0.0,
            "trade_mode": "flat",
            "calibration_score": -999.0,
            "samples": int(len(usable_dates)),
            "used_default": True,
            "candidates_evaluated": 0,
            "calibration_model_total_return": 0.0,
            "calibration_buyhold_total_return": 0.0,
            "calibration_excess_vs_buyhold": 0.0,
            "calibration_active_rate": 0.0,
            "calibration_trade_rate": 0.0,
            "calibration_turnover_per_day": 0.0,
            "calibration_oracle_action_match_rate": 0.0,
            "calibration_oracle_edge_capture_rate": 0.0,
        }

    cal_returns = {dt: returns_by_date[dt] for dt in usable_dates}
    cal_scores = {dt: scores_by_date[dt] for dt in usable_dates}
    cal_oracle = {dt: oracle_by_date[dt] for dt in usable_dates if oracle_by_date and dt in oracle_by_date}
    base_top_k = max(1, int(base_config.get("top_k", 1) or 1))
    thresholds = _portfolio_selector_thresholds(cal_scores, float(base_config.get("threshold", 0.0)))
    top_ks = sorted({1, 2, 3, base_top_k})
    modes = [str(base_config.get("trade_mode", "long_short"))]
    if "long_only" not in modes:
        modes.append("long_only")
    scales = [0.35, 0.65, 1.0]

    best: Dict[str, Any] | None = None
    candidates_evaluated = 0
    for threshold in thresholds:
        for top_k in top_ks:
            for mode in modes:
                for scale in scales:
                    candidate = {
                        **base_config,
                        "threshold": float(threshold),
                        "top_k": int(top_k),
                        "trade_mode": mode,
                        "position_scale": float(scale),
                    }
                    sim = _score_portfolio_series(
                        returns_by_date=cal_returns,
                        scores_by_date=cal_scores,
                        config=candidate,
                        oracle_by_date=cal_oracle,
                    )
                    metrics = sim["model_validation"]
                    gap = sim["gap_validation"]
                    total_return = float(metrics.get("total_return", 0.0))
                    excess = float(gap.get("excess_vs_buyhold", 0.0))
                    active_rate = float(metrics.get("active_rate", 0.0))
                    trade_rate = float(metrics.get("trade_rate", 0.0))
                    turnover_per_day = float(metrics.get("avg_turnover_per_day", 0.0))
                    objective = (
                        float(sim["score"])
                        + 0.45 * max(excess, 0.0)
                        + 0.20 * _bounded_metric(total_return, limit=1.0)
                        - 0.95 * max(active_rate - 0.65, 0.0)
                        - 0.75 * max(turnover_per_day - 0.55, 0.0)
                        - 0.45 * max(trade_rate - 0.65, 0.0)
                    )
                    if total_return < -0.05:
                        objective -= 1.0 + 4.0 * abs(total_return)
                    if active_rate < 0.02 and excess <= 0.0:
                        objective -= 0.40
                    candidates_evaluated += 1
                    if best is None or objective > float(best["objective"]):
                        best = {
                            "objective": float(objective),
                            "threshold": float(threshold),
                            "top_k": int(top_k),
                            "position_scale": float(scale),
                            "trade_mode": mode,
                            "samples": int(len(usable_dates)),
                            "used_default": False,
                            "calibration_model_total_return": total_return,
                            "calibration_buyhold_total_return": float(sim["buyhold_validation"].get("total_return", 0.0)),
                            "calibration_excess_vs_buyhold": excess,
                            "calibration_active_rate": active_rate,
                            "calibration_trade_rate": trade_rate,
                            "calibration_turnover_per_day": turnover_per_day,
                            "calibration_oracle_action_match_rate": float(gap.get("oracle_action_match_rate", 0.0)),
                            "calibration_oracle_edge_capture_rate": float(gap.get("oracle_edge_capture_rate", 0.0)),
                        }

    flat_candidate = {
        **base_config,
        "threshold": 1.0e9,
        "top_k": 1,
        "trade_mode": "flat",
        "position_scale": 0.0,
    }
    flat_sim = _score_portfolio_series(
        returns_by_date=cal_returns,
        scores_by_date=cal_scores,
        config=flat_candidate,
        oracle_by_date=cal_oracle,
    )
    flat_objective = float(flat_sim["score"]) - 0.15
    candidates_evaluated += 1
    if best is None or flat_objective > float(best["objective"]):
        best = {
            "objective": float(flat_objective),
            "threshold": 1.0e9,
            "top_k": 1,
            "position_scale": 0.0,
            "trade_mode": "flat",
            "samples": int(len(usable_dates)),
            "used_default": False,
            "calibration_model_total_return": float(flat_sim["model_validation"].get("total_return", 0.0)),
            "calibration_buyhold_total_return": float(flat_sim["buyhold_validation"].get("total_return", 0.0)),
            "calibration_excess_vs_buyhold": float(flat_sim["gap_validation"].get("excess_vs_buyhold", 0.0)),
            "calibration_active_rate": float(flat_sim["model_validation"].get("active_rate", 0.0)),
            "calibration_trade_rate": float(flat_sim["model_validation"].get("trade_rate", 0.0)),
            "calibration_turnover_per_day": float(flat_sim["model_validation"].get("avg_turnover_per_day", 0.0)),
            "calibration_oracle_action_match_rate": float(flat_sim["gap_validation"].get("oracle_action_match_rate", 0.0)),
            "calibration_oracle_edge_capture_rate": float(flat_sim["gap_validation"].get("oracle_edge_capture_rate", 0.0)),
        }

    return {
        "threshold": float(best["threshold"]),
        "top_k": int(best["top_k"]),
        "position_scale": float(best["position_scale"]),
        "trade_mode": str(best["trade_mode"]),
        "calibration_score": float(best["objective"]),
        "samples": int(best["samples"]),
        "used_default": bool(best["used_default"]),
        "candidates_evaluated": int(candidates_evaluated),
        "calibration_model_total_return": float(best["calibration_model_total_return"]),
        "calibration_buyhold_total_return": float(best["calibration_buyhold_total_return"]),
        "calibration_excess_vs_buyhold": float(best["calibration_excess_vs_buyhold"]),
        "calibration_active_rate": float(best["calibration_active_rate"]),
        "calibration_trade_rate": float(best["calibration_trade_rate"]),
        "calibration_turnover_per_day": float(best["calibration_turnover_per_day"]),
        "calibration_oracle_action_match_rate": float(best["calibration_oracle_action_match_rate"]),
        "calibration_oracle_edge_capture_rate": float(best["calibration_oracle_edge_capture_rate"]),
    }


def _run_oracle_portfolio_for_config(
    prepared: Dict[str, pd.DataFrame],
    train_symbols: List[str],
    eval_symbols: List[str],
    feature_cols: List[str],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    ref_symbol = train_symbols[0]
    month_starts = _iter_month_starts(prepared[ref_symbol].index)
    returns_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
    scores_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
    configs_by_date: Dict[pd.Timestamp, Dict[str, Any]] = {}
    calibration_rows: List[Dict[str, Any]] = []

    for month_idx, month_start in enumerate(month_starts):
        if month_idx % AUTORESEARCH_MONTH_STRIDE != 0:
            continue
        month_end = month_start + pd.offsets.MonthBegin(1)
        pooled_train = _build_pooled_train_frame(prepared, train_symbols, month_start)
        if len(pooled_train) < MIN_TRAIN_SAMPLES:
            continue

        cal_start = month_start - pd.Timedelta(days=CALIBRATION_LOOKBACK_DAYS)
        cal_returns_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
        cal_scores_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
        calibration_train = _build_pooled_train_frame(prepared, train_symbols, cal_start)
        if len(calibration_train) >= MIN_TRAIN_SAMPLES:
            calibration_bundle = _fit_model(calibration_train, feature_cols, config)
            for symbol in eval_symbols:
                coin_df = prepared[symbol]
                cal_df = coin_df[(coin_df.index >= cal_start) & (coin_df.index < month_start)]
                if len(cal_df) < MIN_TEST_SAMPLES:
                    continue
                cal_scores = _predict_scores(calibration_bundle, cal_df, feature_cols)
                for i, dt in enumerate(cal_df.index):
                    target = cal_df.iloc[i].get("target")
                    if pd.notna(target):
                        cal_returns_by_date.setdefault(pd.Timestamp(dt), {})[symbol] = float(target)
                        cal_scores_by_date.setdefault(pd.Timestamp(dt), {})[symbol] = float(cal_scores[i])

        cal_oracle_by_date = _portfolio_oracle_by_date(cal_returns_by_date, eval_symbols) if cal_returns_by_date else {}
        calibration = _calibrate_portfolio_selector(
            returns_by_date=cal_returns_by_date,
            scores_by_date=cal_scores_by_date,
            base_config=config,
            oracle_by_date=cal_oracle_by_date,
        )
        calibration["month_start"] = month_start.strftime("%Y-%m-%d")
        calibration_rows.append(calibration)

        bundle = _fit_model(pooled_train, feature_cols, config)
        for symbol in eval_symbols:
            coin_df = prepared[symbol]
            month_df = coin_df[(coin_df.index >= month_start) & (coin_df.index < month_end)]
            if len(month_df) < MIN_TEST_SAMPLES:
                continue
            scores = _predict_scores(bundle, month_df, feature_cols)
            for i, dt in enumerate(month_df.index):
                target = month_df.iloc[i].get("target")
                if pd.notna(target):
                    dt = pd.Timestamp(dt)
                    returns_by_date.setdefault(dt, {})[symbol] = float(target)
                    scores_by_date.setdefault(dt, {})[symbol] = float(scores[i])
                    configs_by_date[dt] = calibration

    if not returns_by_date:
        return {
            "score": -999.0,
            "model_validation": _metrics_from_returns(np.array([]), pd.DatetimeIndex([])),
            "buyhold_validation": _metrics_from_returns(np.array([]), pd.DatetimeIndex([])),
            "oracle_validation": {},
            "gap_validation": {
                "excess_vs_buyhold": 0.0,
                "relative_capture_vs_buyhold": 0.0,
                "outperform_rate": 0.0,
                "oracle_action_match_rate": 0.0,
                "oracle_edge_capture_rate": 0.0,
            },
            "days_scored": 0,
            "symbols_used": 0,
        }

    oracle_by_date = _portfolio_oracle_by_date(returns_by_date, eval_symbols)
    result = _score_portfolio_series(
        returns_by_date=returns_by_date,
        scores_by_date=scores_by_date,
        config=config,
        oracle_by_date=oracle_by_date,
        configs_by_date=configs_by_date,
    )
    result["portfolio_calibration_summary"] = _summarize_calibration(calibration_rows)
    result["portfolio_calibration_rows"] = calibration_rows
    return result


def _merge_metric_dicts(metric_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not metric_rows:
        return _metrics_from_returns(np.array([]), pd.DatetimeIndex([]))

    keys = [
        "total_return",
        "cagr",
        "sharpe",
        "sortino",
        "max_drawdown",
        "trade_count",
        "trade_rate",
        "avg_turnover_per_day",
        "total_turnover",
        "active_rate",
        "win_rate",
        "daily_hit_rate",
    ]
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
    if str(config.get("model_kind")) == "xmom_topk":
        return _run_cross_sectional_momentum_for_config(
            prepared=prepared,
            train_symbols=train_symbols,
            eval_symbols=eval_symbols,
            config=config,
        )
    if str(config.get("model_kind")) in ORACLE_PORTFOLIO_MODEL_KINDS:
        return _run_oracle_portfolio_for_config(
            prepared=prepared,
            train_symbols=train_symbols,
            eval_symbols=eval_symbols,
            feature_cols=feature_cols,
            config=config,
        )

    ref_symbol = train_symbols[0]
    month_starts = _iter_month_starts(prepared[ref_symbol].index)

    model_metric_rows: List[Dict[str, Any]] = []
    buyhold_metric_rows: List[Dict[str, Any]] = []
    symbol_day_counts: Dict[str, int] = {s: 0 for s in eval_symbols}
    oracle_action_matches: List[float] = []
    oracle_edge_captures: List[float] = []

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

            positions = _positions_from_scores(
                scores=scores,
                feature_df=month_df,
                threshold=float(config["threshold"]),
                trade_mode=str(config["trade_mode"]),
                position_scale=1.0,
                config=config,
            )
            model_sim = _simulate_from_positions(returns, positions, TRADE_COST_RATE)
            model_metrics = _metrics_from_returns(
                daily_returns=model_sim["daily_returns"],
                index=index,
                trade_count=model_sim["trade_count"],
                active_positions=positions,
                underlying_returns=returns,
                turnover=model_sim["turnover"],
            )
            buyhold_metrics, _ = _build_buyhold_metrics(returns, index)

            model_metric_rows.append(model_metrics)
            buyhold_metric_rows.append(buyhold_metrics)
            symbol_day_counts[symbol] += int(len(month_df))
            if "oracle_action" in month_df.columns:
                oracle_positions = month_df["oracle_action"].to_numpy(dtype=float)
                oracle_edges = np.maximum(month_df["oracle_expected_edge"].to_numpy(dtype=float), 0.0)
                oracle_action_matches.append(float(np.mean(np.sign(positions) == np.sign(oracle_positions))))
                denom = float(np.sum(oracle_edges))
                if denom > 1e-12:
                    same_action = np.sign(positions) == np.sign(oracle_positions)
                    oracle_edge_captures.append(float(np.sum(oracle_edges[same_action]) / denom))

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
        "oracle_action_match_rate": float(np.mean(oracle_action_matches)) if oracle_action_matches else 0.0,
        "oracle_edge_capture_rate": float(np.mean(oracle_edge_captures)) if oracle_edge_captures else 0.0,
    }

    excess_vs_buyhold = float(gap_validation["excess_vs_buyhold"])
    negative_excess_penalty = 0.0
    if excess_vs_buyhold < 0.0:
        negative_excess_penalty = 2.0 + 20.0 * abs(excess_vs_buyhold)
    weak_model_edge_penalty = 0.0
    robust_baselines = {"buy_hold", "trend_120", "xmom_topk"}
    if str(config.get("trade_mode")) != "flat" and str(config.get("model_kind")) not in robust_baselines and excess_vs_buyhold < 0.05:
        weak_model_edge_penalty = 1.50
    score = (
        excess_vs_buyhold
        + 0.45 * _bounded_metric(float(model_validation["sharpe"]))
        + 0.25 * _bounded_metric(float(model_validation["sortino"]))
        - 1.15 * float(model_validation["max_drawdown"])
        + 0.50 * float(outperform_rate)
        - 0.25 * float(model_validation.get("trade_rate", 0.0))
        - 0.40 * float(model_validation.get("avg_turnover_per_day", 0.0))
        - 0.20 * max(float(model_validation.get("active_rate", 0.0)) - 0.82, 0.0)
        + 0.45 * float(gap_validation["oracle_action_match_rate"])
        + 0.65 * float(gap_validation["oracle_edge_capture_rate"])
        - negative_excess_penalty
        - weak_model_edge_penalty
    )

    return {
        "score": float(score),
        "model_validation": model_validation,
        "buyhold_validation": buyhold_validation,
        "oracle_validation": {},
        "gap_validation": gap_validation,
        "selection_penalties": {
            "negative_excess_penalty": float(negative_excess_penalty),
            "weak_model_edge_penalty": float(weak_model_edge_penalty),
        },
        "days_scored": int(sum(symbol_day_counts.values())),
        "symbols_used": int(sum(1 for _, c in symbol_day_counts.items() if c > 0)),
    }


def _run_autoresearch_trial_worker(args: Tuple[int, Dict[str, Any], Dict[str, pd.DataFrame], List[str], List[str], List[str]]) -> Dict[str, Any]:
    trial_idx, cfg, prepared, train_symbols, eval_symbols, feature_cols = args
    result = _run_multi_coin_walkforward_for_config(
        prepared=prepared,
        train_symbols=train_symbols,
        eval_symbols=eval_symbols,
        feature_cols=feature_cols,
        config=cfg,
    )
    return {
        "trial": int(trial_idx),
        "config": cfg,
        "model_validation": result["model_validation"],
        "buyhold_validation": result["buyhold_validation"],
        "oracle_validation": result["oracle_validation"],
        "gap_validation": result["gap_validation"],
        "days_scored": result["days_scored"],
        "symbols_used": result["symbols_used"],
        "score": result["score"],
    }


def _init_final_walkforward_worker(
    prepared: Dict[str, pd.DataFrame],
    train_symbols: List[str],
    available_eval: List[str],
    feature_cols: List[str],
    best_config: Dict[str, Any],
) -> None:
    _FINAL_WALKFORWARD_CONTEXT.clear()
    _FINAL_WALKFORWARD_CONTEXT.update(
        {
            "prepared": prepared,
            "train_symbols": train_symbols,
            "available_eval": available_eval,
            "feature_cols": feature_cols,
            "best_config": best_config,
        }
    )


def _run_final_walkforward_month_worker(month_start_value: Any) -> Dict[str, Any]:
    prepared: Dict[str, pd.DataFrame] = _FINAL_WALKFORWARD_CONTEXT["prepared"]
    train_symbols: List[str] = _FINAL_WALKFORWARD_CONTEXT["train_symbols"]
    available_eval: List[str] = _FINAL_WALKFORWARD_CONTEXT["available_eval"]
    feature_cols: List[str] = _FINAL_WALKFORWARD_CONTEXT["feature_cols"]
    best_config: Dict[str, Any] = _FINAL_WALKFORWARD_CONTEXT["best_config"]

    month_start = pd.Timestamp(month_start_value)
    month_end = month_start + pd.offsets.MonthBegin(1)
    pooled_train = _build_pooled_train_frame(prepared, train_symbols, month_start)
    if len(pooled_train) < MIN_TRAIN_SAMPLES:
        return {"month": month_start.strftime("%Y-%m"), "rows": {}, "calibrations": {}}

    is_flat_config = str(best_config.get("trade_mode")) == "flat"
    is_portfolio_config = str(best_config.get("model_kind")) in ORACLE_PORTFOLIO_MODEL_KINDS
    portfolio_calibration: Dict[str, Any] | None = None
    if is_portfolio_config and not is_flat_config:
        cal_start = month_start - pd.Timedelta(days=CALIBRATION_LOOKBACK_DAYS)
        cal_returns_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
        cal_scores_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
        calibration_train = _build_pooled_train_frame(prepared, train_symbols, cal_start)
        if len(calibration_train) >= MIN_TRAIN_SAMPLES:
            calibration_bundle = _fit_model(calibration_train, feature_cols, best_config)
            for symbol in available_eval:
                coin_df = prepared[symbol]
                cal_df = coin_df[(coin_df.index >= cal_start) & (coin_df.index < month_start)]
                if len(cal_df) < MIN_TEST_SAMPLES:
                    continue
                cal_scores = _predict_scores(calibration_bundle, cal_df, feature_cols)
                for i, dt in enumerate(cal_df.index):
                    target = cal_df.iloc[i].get("target")
                    if pd.notna(target):
                        cal_returns_by_date.setdefault(pd.Timestamp(dt), {})[symbol] = float(target)
                        cal_scores_by_date.setdefault(pd.Timestamp(dt), {})[symbol] = float(cal_scores[i])
        cal_oracle_by_date = _portfolio_oracle_by_date(cal_returns_by_date, available_eval) if cal_returns_by_date else {}
        portfolio_calibration = _calibrate_portfolio_selector(
            returns_by_date=cal_returns_by_date,
            scores_by_date=cal_scores_by_date,
            base_config=best_config,
            oracle_by_date=cal_oracle_by_date,
        )

    bundle = None if is_flat_config else _fit_model(pooled_train, feature_cols, best_config)
    rows_by_symbol: Dict[str, List[Dict[str, Any]]] = {sym: [] for sym in available_eval}
    calibrations_by_symbol: Dict[str, List[Dict[str, Any]]] = {sym: [] for sym in available_eval}

    for symbol in available_eval:
        coin_df = prepared[symbol]
        month_df = coin_df[(coin_df.index >= month_start) & (coin_df.index < month_end)]
        if len(month_df) < MIN_TEST_SAMPLES:
            continue

        if is_flat_config:
            all_scores = np.zeros(len(coin_df), dtype=float)
        else:
            all_scores = _predict_scores(bundle, coin_df, feature_cols)
        if is_portfolio_config:
            calibration = portfolio_calibration or _calibrate_portfolio_selector({}, {}, best_config, {})
        else:
            calibration = _calibrate_coin(
                coin_df=coin_df,
                month_start=month_start,
                scores_history=all_scores,
                base_config=best_config,
            )
        risk_guard_reason = ""
        if (
            str(best_config.get("model_kind")) not in {"buy_hold", "trend_120", "xmom_topk", "oracle_portfolio", "gbt_oracle_portfolio"}
            and
            not bool(calibration["used_default"])
            and str(calibration["trade_mode"]) != "flat"
            and float(calibration["calibration_score"]) <= 0.015
        ):
            risk_guard_reason = "weak_trailing_calibration"
            calibration = {
                **calibration,
                "threshold": 1.0e9,
                "position_scale": 0.0,
                "trade_mode": "flat",
            }

        calibrations_by_symbol[symbol].append(
            {
                "month": month_start.strftime("%Y-%m"),
                "threshold": calibration["threshold"],
                "top_k": calibration.get("top_k", best_config.get("top_k", 1)),
                "position_scale": calibration["position_scale"],
                "trade_mode": calibration["trade_mode"],
                "calibration_score": calibration["calibration_score"],
                "samples": calibration["samples"],
                "used_default": calibration["used_default"],
                "risk_guard_reason": risk_guard_reason,
                "live_excess_before_month": 0.0,
                "live_model_return_before_month": 0.0,
            }
        )

        test_scores = all_scores[(coin_df.index >= month_start) & (coin_df.index < month_end)]
        for i, dt in enumerate(month_df.index):
            rows_by_symbol[symbol].append(
                {
                    "date": dt,
                    "close": float(month_df.iloc[i]["close"]),
                    "target_return": float(month_df.iloc[i]["target"]),
                    "prediction_score": float(test_scores[i]),
                    "threshold": float(calibration["threshold"]),
                    "top_k": int(calibration.get("top_k", best_config.get("top_k", 1) or 1)),
                    "position_scale": float(calibration["position_scale"]),
                    "trade_mode": str(calibration["trade_mode"]),
                    "risk_guard_reason": risk_guard_reason,
                    "ema_spread": float(month_df.iloc[i].get("ema_spread", 0.0)),
                    "mom_20": float(month_df.iloc[i].get("mom_20", 0.0)),
                    "vol_20": float(month_df.iloc[i].get("vol_20", 0.0)),
                }
            )

    return {"month": month_start.strftime("%Y-%m"), "rows": rows_by_symbol, "calibrations": calibrations_by_symbol}


def _run_karpathy_autoresearch(
    prepared: Dict[str, pd.DataFrame],
    train_symbols: List[str],
    eval_symbols: List[str],
    feature_cols: List[str],
    configs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    experiments = []
    best_trial = None
    max_workers = int(os.environ.get("CRYPTO_AUTORESEARCH_WORKERS", "0") or "0")
    if max_workers <= 0:
        max_workers = min(len(configs), max(1, (os.cpu_count() or 2) - 1), 6)

    if max_workers <= 1 or len(configs) <= 1:
        trial_rows = []
        for trial_idx, cfg in enumerate(configs, start=1):
            print(
                "[autoresearch] "
                f"trial {trial_idx}/{len(configs)} "
                f"kind={cfg.get('model_kind')} "
                f"mode={cfg.get('trade_mode')} "
                f"threshold={cfg.get('threshold')}",
                flush=True,
            )
            trial_rows.append(
                _run_autoresearch_trial_worker(
                    (trial_idx, cfg, prepared, train_symbols, eval_symbols, feature_cols)
                )
            )
    else:
        print(
            "[autoresearch] "
            f"parallel trial evaluation workers={max_workers} "
            f"trials={len(configs)}",
            flush=True,
        )
        for trial_idx, cfg in enumerate(configs, start=1):
            print(
                "[autoresearch] "
                f"queued trial {trial_idx}/{len(configs)} "
                f"kind={cfg.get('model_kind')} "
                f"mode={cfg.get('trade_mode')} "
                f"threshold={cfg.get('threshold')}",
                flush=True,
            )
        trial_rows = []
        worker_args = [
            (trial_idx, cfg, prepared, train_symbols, eval_symbols, feature_cols)
            for trial_idx, cfg in enumerate(configs, start=1)
        ]
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_trial = {executor.submit(_run_autoresearch_trial_worker, arg): arg[0] for arg in worker_args}
            for future in as_completed(future_to_trial):
                trial_rows.append(future.result())

    for row in sorted(trial_rows, key=lambda r: int(r["trial"])):
        experiments.append(row)
        print(
            "[autoresearch] "
            f"trial {row['trial']} score={row['score']:.4f} "
            f"excess={row['gap_validation']['excess_vs_buyhold']:.4f} "
            f"outperform={row['gap_validation']['outperform_rate']:.4f}",
            flush=True,
        )
        if best_trial is None or row["score"] > best_trial["score"]:
            best_trial = row

    if best_trial is None:
        raise RuntimeError("AutoResearch produced no valid trial")

    return {
        "best_config": best_trial["config"],
        "best_score": float(best_trial["score"]),
        "month_stride_for_selection": int(AUTORESEARCH_MONTH_STRIDE),
        "experiments": experiments,
        "anti_cheat_note": (
            "Training uses oracle action labels built only from each historical training window. "
            "Final walk-forward oracle paths remain verification-only."
        ),
    }


def _coin_acceptance(model_metrics: Dict[str, Any], buyhold_metrics: Dict[str, Any]) -> Dict[str, Any]:
    beat_buyhold = float(model_metrics["total_return"]) > float(buyhold_metrics["total_return"])
    sharpe_ok = float(model_metrics["sharpe"]) >= float(ACCEPTANCE_THRESHOLDS["min_sharpe"])
    sortino_ok = float(model_metrics["sortino"]) >= float(ACCEPTANCE_THRESHOLDS["min_sortino"])
    drawdown_ok = float(model_metrics["max_drawdown"]) <= float(ACCEPTANCE_THRESHOLDS["max_drawdown"])
    trade_rate_ok = float(model_metrics.get("trade_rate", 0.0)) <= float(ACCEPTANCE_THRESHOLDS["max_trade_rate"])
    turnover_ok = float(model_metrics.get("avg_turnover_per_day", 0.0)) <= float(ACCEPTANCE_THRESHOLDS["max_turnover_per_day"])
    active_rate_ok = float(model_metrics.get("active_rate", 0.0)) <= float(ACCEPTANCE_THRESHOLDS["max_active_rate"])

    accepted = (
        (beat_buyhold if ACCEPTANCE_THRESHOLDS["must_beat_buyhold"] else True)
        and sharpe_ok
        and sortino_ok
        and drawdown_ok
        and trade_rate_ok
        and turnover_ok
        and active_rate_ok
    )

    return {
        "accepted": bool(accepted),
        "checks": {
            "beat_buyhold": bool(beat_buyhold),
            "sharpe_ok": bool(sharpe_ok),
            "sortino_ok": bool(sortino_ok),
            "drawdown_ok": bool(drawdown_ok),
            "trade_rate_ok": bool(trade_rate_ok),
            "turnover_ok": bool(turnover_ok),
            "active_rate_ok": bool(active_rate_ok),
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
            "flat_months": 0,
            "risk_guard_months": 0,
        }

    thresholds = [
        float(r["threshold"])
        for r in calibration_rows
        if r.get("trade_mode") != "flat" and math.isfinite(float(r["threshold"]))
    ]
    scales = [float(r["position_scale"]) for r in calibration_rows]
    default_months = sum(1 for r in calibration_rows if bool(r.get("used_default")))
    ls_months = sum(1 for r in calibration_rows if r.get("trade_mode") == "long_short")
    lo_months = sum(1 for r in calibration_rows if r.get("trade_mode") == "long_only")
    flat_months = sum(1 for r in calibration_rows if r.get("trade_mode") == "flat")
    risk_guard_months = sum(1 for r in calibration_rows if bool(r.get("risk_guard_reason")))

    return {
        "months_calibrated": int(len(calibration_rows)),
        "default_used_months": int(default_months),
        "avg_threshold": float(np.mean(thresholds)) if thresholds else 0.0,
        "avg_position_scale": float(np.mean(scales)),
        "long_short_months": int(ls_months),
        "long_only_months": int(lo_months),
        "flat_months": int(flat_months),
        "risk_guard_months": int(risk_guard_months),
    }


def run_crypto_7y_autoresearch() -> Dict[str, Any]:
    np.random.seed(42)

    today = date.today()
    end_date = (today + timedelta(days=1)).isoformat()
    start_date = (today - timedelta(days=YEARS * 365)).isoformat()

    loader = DataLoader(cache_dir="data/cache")
    configured_train_symbols = TRAIN_SYMBOLS if TRAIN_SYMBOLS is not None else [TRAIN_SYMBOL] + EVAL_SYMBOLS
    configured_selection_symbols = AUTORESEARCH_EVAL_SYMBOLS if AUTORESEARCH_EVAL_SYMBOLS is not None else EVAL_SYMBOLS
    symbols = list(dict.fromkeys([TRAIN_SYMBOL] + configured_train_symbols + EVAL_SYMBOLS + configured_selection_symbols))
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

    feature_cols = _add_cross_sectional_features(prepared, feature_cols)

    available_eval = [s for s in EVAL_SYMBOLS if s in prepared]
    if not available_eval:
        raise RuntimeError("No evaluation symbols have enough feature data")

    train_symbols = list(dict.fromkeys([s for s in configured_train_symbols if s in prepared]))
    if TRAIN_SYMBOL in prepared and TRAIN_SYMBOL not in train_symbols:
        train_symbols.insert(0, TRAIN_SYMBOL)
    _add_oracle_action_labels(prepared, train_symbols, TRADE_COST_RATE)

    selection_eval_symbols = [s for s in configured_selection_symbols if s in prepared]
    if not selection_eval_symbols:
        raise RuntimeError("No autoresearch selection symbols have enough feature data")
    holdout_symbols = [s for s in available_eval if s not in set(selection_eval_symbols)]
    btc_df = prepared[TRAIN_SYMBOL]
    auto = _run_karpathy_autoresearch(
        prepared=prepared,
        train_symbols=train_symbols,
        eval_symbols=selection_eval_symbols,
        feature_cols=feature_cols,
        configs=DEFAULT_CONFIGS,
    )
    best_config = auto["best_config"]
    is_portfolio_best = str(best_config.get("model_kind")) in ORACLE_PORTFOLIO_MODEL_KINDS

    month_starts = _iter_month_starts(btc_df.index)

    per_coin_rows: Dict[str, List[Dict[str, Any]]] = {sym: [] for sym in available_eval}
    per_coin_calibrations: Dict[str, List[Dict[str, Any]]] = {sym: [] for sym in available_eval}
    per_coin_live_state: Dict[str, Dict[str, float]] = {
        sym: {
            "model_equity": 1.0,
            "buyhold_equity": 1.0,
            "months_seen": 0.0,
            "forced_flat_months": 0.0,
        }
        for sym in available_eval
    }

    eligible_month_starts = [
        month_start
        for month_start in month_starts
        if len(_build_pooled_train_frame(prepared, train_symbols, month_start)) >= MIN_TRAIN_SAMPLES
    ]
    eligible_month_count = len(eligible_month_starts)
    completed_month_count = 0
    final_workers = int(os.environ.get("CRYPTO_FINAL_WALKFORWARD_WORKERS", "0") or "0")

    if final_workers > 1 and eligible_month_count > 1:
        final_workers = min(final_workers, eligible_month_count)
        print(
            "[autoresearch] "
            f"parallel final walk-forward workers={final_workers} "
            f"months={eligible_month_count}",
            flush=True,
        )
        month_results: List[Dict[str, Any]] = []
        with ProcessPoolExecutor(
            max_workers=final_workers,
            initializer=_init_final_walkforward_worker,
            initargs=(prepared, train_symbols, available_eval, feature_cols, best_config),
        ) as executor:
            future_to_month = {
                executor.submit(_run_final_walkforward_month_worker, month_start): month_start
                for month_start in eligible_month_starts
            }
            for future in as_completed(future_to_month):
                completed_month_count += 1
                month_start = future_to_month[future]
                print(
                    "[autoresearch] "
                    f"final walk-forward month {completed_month_count}/{eligible_month_count} "
                    f"{month_start.strftime('%Y-%m')}",
                    flush=True,
                )
                month_results.append(future.result())

        for month_result in sorted(month_results, key=lambda row: row["month"]):
            month_start = pd.Timestamp(f"{month_result['month']}-01")
            for symbol in available_eval:
                rows = month_result["rows"].get(symbol, [])
                calibration_rows = month_result["calibrations"].get(symbol, [])
                if not rows or not calibration_rows:
                    continue

                calibration = dict(calibration_rows[0])
                state = per_coin_live_state[symbol]
                risk_guard_reason = ""
                live_excess_before_month = float(state["model_equity"] - state["buyhold_equity"])
                live_model_return_before_month = float(state["model_equity"] - 1.0)
                if (
                    not is_portfolio_best
                    and
                    state["months_seen"] >= 2.0
                    and state["model_equity"] < state["buyhold_equity"] * 0.97
                ):
                    risk_guard_reason = "prior_oos_underperformed_buyhold"
                elif not is_portfolio_best and state["months_seen"] >= 2.0 and live_model_return_before_month < -0.08:
                    risk_guard_reason = "prior_oos_drawdown_guard"
                elif (
                    str(best_config.get("model_kind")) not in {"buy_hold", "trend_120", "xmom_topk", "oracle_portfolio", "gbt_oracle_portfolio"}
                    and
                    not bool(calibration["used_default"])
                    and str(calibration["trade_mode"]) != "flat"
                    and float(calibration["calibration_score"]) <= 0.015
                ):
                    risk_guard_reason = "weak_trailing_calibration"

                if risk_guard_reason:
                    calibration["threshold"] = 1.0e9
                    calibration["position_scale"] = 0.0
                    calibration["trade_mode"] = "flat"
                    state["forced_flat_months"] += 1.0

                calibration["risk_guard_reason"] = risk_guard_reason
                calibration["live_excess_before_month"] = live_excess_before_month
                calibration["live_model_return_before_month"] = live_model_return_before_month
                per_coin_calibrations[symbol].append(calibration)

                for row in rows:
                    row["threshold"] = float(calibration["threshold"])
                    row["top_k"] = int(calibration.get("top_k", best_config.get("top_k", 1) or 1))
                    row["position_scale"] = float(calibration["position_scale"])
                    row["trade_mode"] = str(calibration["trade_mode"])
                    row["risk_guard_reason"] = risk_guard_reason
                per_coin_rows[symbol].extend(rows)

                month_df = pd.DataFrame(rows).sort_values("date")
                month_df.index = pd.to_datetime(month_df["date"])
                month_positions = _positions_from_scores(
                    scores=month_df["prediction_score"].to_numpy(dtype=float),
                    feature_df=month_df,
                    threshold=float(calibration["threshold"]),
                    trade_mode=str(calibration["trade_mode"]),
                    position_scale=float(calibration["position_scale"]),
                    config=best_config,
                )
                month_returns = month_df["target_return"].to_numpy(dtype=float)
                month_model_sim = _simulate_from_positions(month_returns, month_positions, TRADE_COST_RATE)
                month_buyhold_sim = _simulate_from_positions(month_returns, np.ones(len(month_returns)), TRADE_COST_RATE)
                state["model_equity"] *= float(np.prod(1.0 + month_model_sim["daily_returns"]))
                state["buyhold_equity"] *= float(np.prod(1.0 + month_buyhold_sim["daily_returns"]))
                state["months_seen"] += 1.0
    else:
        for month_start in month_starts:
            month_end = month_start + pd.offsets.MonthBegin(1)
            pooled_train = _build_pooled_train_frame(prepared, train_symbols, month_start)
            if len(pooled_train) < MIN_TRAIN_SAMPLES:
                continue

            completed_month_count += 1
            print(
                "[autoresearch] "
                f"final walk-forward month {completed_month_count}/{eligible_month_count} "
                f"{month_start.strftime('%Y-%m')}",
                flush=True,
            )
            is_flat_config = str(best_config.get("trade_mode")) == "flat"
            portfolio_calibration: Dict[str, Any] | None = None
            if is_portfolio_best and not is_flat_config:
                cal_start = month_start - pd.Timedelta(days=CALIBRATION_LOOKBACK_DAYS)
                cal_returns_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
                cal_scores_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
                calibration_train = _build_pooled_train_frame(prepared, train_symbols, cal_start)
                if len(calibration_train) >= MIN_TRAIN_SAMPLES:
                    calibration_bundle = _fit_model(calibration_train, feature_cols, best_config)
                    for cal_symbol in available_eval:
                        cal_coin_df = prepared[cal_symbol]
                        cal_df = cal_coin_df[(cal_coin_df.index >= cal_start) & (cal_coin_df.index < month_start)]
                        if len(cal_df) < MIN_TEST_SAMPLES:
                            continue
                        cal_scores = _predict_scores(calibration_bundle, cal_df, feature_cols)
                        for i, dt in enumerate(cal_df.index):
                            target = cal_df.iloc[i].get("target")
                            if pd.notna(target):
                                cal_returns_by_date.setdefault(pd.Timestamp(dt), {})[cal_symbol] = float(target)
                                cal_scores_by_date.setdefault(pd.Timestamp(dt), {})[cal_symbol] = float(cal_scores[i])
                cal_oracle_by_date = _portfolio_oracle_by_date(cal_returns_by_date, available_eval) if cal_returns_by_date else {}
                portfolio_calibration = _calibrate_portfolio_selector(
                    returns_by_date=cal_returns_by_date,
                    scores_by_date=cal_scores_by_date,
                    base_config=best_config,
                    oracle_by_date=cal_oracle_by_date,
                )

            bundle = None if is_flat_config else _fit_model(pooled_train, feature_cols, best_config)

            for symbol in available_eval:
                coin_df = prepared[symbol]
                month_df = coin_df[(coin_df.index >= month_start) & (coin_df.index < month_end)]
                if len(month_df) < MIN_TEST_SAMPLES:
                    continue

                all_scores = np.zeros(len(coin_df), dtype=float) if is_flat_config else _predict_scores(bundle, coin_df, feature_cols)
                if is_portfolio_best:
                    calibration = portfolio_calibration or _calibrate_portfolio_selector({}, {}, best_config, {})
                else:
                    calibration = _calibrate_coin(coin_df=coin_df, month_start=month_start, scores_history=all_scores, base_config=best_config)
                state = per_coin_live_state[symbol]
                risk_guard_reason = ""
                live_excess_before_month = float(state["model_equity"] - state["buyhold_equity"])
                live_model_return_before_month = float(state["model_equity"] - 1.0)
                if (
                    not is_portfolio_best
                    and
                    state["months_seen"] >= 2.0
                    and state["model_equity"] < state["buyhold_equity"] * 0.97
                ):
                    risk_guard_reason = "prior_oos_underperformed_buyhold"
                elif not is_portfolio_best and state["months_seen"] >= 2.0 and live_model_return_before_month < -0.08:
                    risk_guard_reason = "prior_oos_drawdown_guard"
                elif (
                    str(best_config.get("model_kind")) not in {"buy_hold", "trend_120", "xmom_topk", "oracle_portfolio", "gbt_oracle_portfolio"}
                    and
                    not bool(calibration["used_default"])
                    and str(calibration["trade_mode"]) != "flat"
                    and float(calibration["calibration_score"]) <= 0.015
                ):
                    risk_guard_reason = "weak_trailing_calibration"

                if risk_guard_reason:
                    calibration = {
                        **calibration,
                        "threshold": 1.0e9,
                        "position_scale": 0.0,
                        "trade_mode": "flat",
                    }
                    state["forced_flat_months"] += 1.0

                per_coin_calibrations[symbol].append(
                    {
                        "month": month_start.strftime("%Y-%m"),
                        "threshold": calibration["threshold"],
                        "top_k": calibration.get("top_k", best_config.get("top_k", 1)),
                        "position_scale": calibration["position_scale"],
                        "trade_mode": calibration["trade_mode"],
                        "calibration_score": calibration["calibration_score"],
                        "samples": calibration["samples"],
                        "used_default": calibration["used_default"],
                        "risk_guard_reason": risk_guard_reason,
                        "live_excess_before_month": live_excess_before_month,
                        "live_model_return_before_month": live_model_return_before_month,
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
                            "top_k": int(calibration.get("top_k", best_config.get("top_k", 1) or 1)),
                            "position_scale": float(calibration["position_scale"]),
                            "trade_mode": str(calibration["trade_mode"]),
                            "risk_guard_reason": risk_guard_reason,
                            "ema_spread": float(month_df.iloc[i].get("ema_spread", 0.0)),
                            "mom_20": float(month_df.iloc[i].get("mom_20", 0.0)),
                            "vol_20": float(month_df.iloc[i].get("vol_20", 0.0)),
                        }
                    )

                month_positions = _positions_from_scores(
                    scores=test_scores,
                    feature_df=month_df,
                    threshold=float(calibration["threshold"]),
                    trade_mode=str(calibration["trade_mode"]),
                    position_scale=float(calibration["position_scale"]),
                    config=best_config,
                )
                month_returns = month_df["target"].to_numpy(dtype=float)
                month_model_sim = _simulate_from_positions(month_returns, month_positions, TRADE_COST_RATE)
                month_buyhold_sim = _simulate_from_positions(month_returns, np.ones(len(month_returns)), TRADE_COST_RATE)
                state["model_equity"] *= float(np.prod(1.0 + month_model_sim["daily_returns"]))
                state["buyhold_equity"] *= float(np.prod(1.0 + month_buyhold_sim["daily_returns"]))
                state["months_seen"] += 1.0

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

        model_positions = np.zeros(len(sdf), dtype=float)
        for i in range(len(sdf)):
            model_positions[i] = _score_to_position(
                score=float(scores[i]),
                threshold=float(sdf.iloc[i]["threshold"]),
                trade_mode=str(sdf.iloc[i]["trade_mode"]),
                position_scale=float(sdf.iloc[i]["position_scale"]),
                feature_row=sdf.iloc[i],
                config=best_config,
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
                "model_expected_next_day_edge": np.abs(scores),
                "threshold": sdf["threshold"].to_numpy(dtype=float),
                "position_scale": sdf["position_scale"].to_numpy(dtype=float),
                "trade_mode": sdf["trade_mode"].to_numpy(),
                "risk_guard_reason": sdf["risk_guard_reason"].to_numpy(),
                "ema_spread": sdf["ema_spread"].to_numpy(dtype=float),
                "mom_20": sdf["mom_20"].to_numpy(dtype=float),
                "vol_20": sdf["vol_20"].to_numpy(dtype=float),
                "model_action": np.where(model_positions > 0.0, "long", np.where(model_positions < 0.0, "short", "cash")),
                "model_position": model_positions,
                "model_position_size": np.abs(model_positions),
                "model_switching_cost": model_sim["turnover"] * TRADE_COST_RATE,
                "oracle_action": np.where(oracle["positions"] > 0.0, "long", np.where(oracle["positions"] < 0.0, "short", "cash")),
                "oracle_position": oracle["positions"],
                "oracle_position_size": np.abs(oracle["positions"]),
                "oracle_switching_cost": oracle["turnover"] * TRADE_COST_RATE,
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
                "model_trade_rate": model_metrics["trade_rate"],
                "model_turnover_per_day": model_metrics["avg_turnover_per_day"],
                "model_active_rate": model_metrics["active_rate"],
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
        "avg_model_trade_rate": float(np.mean([r["model_walkforward"]["trade_rate"] for r in results_by_symbol])),
        "avg_model_turnover_per_day": float(np.mean([r["model_walkforward"]["avg_turnover_per_day"] for r in results_by_symbol])),
        "avg_model_active_rate": float(np.mean([r["model_walkforward"]["active_rate"] for r in results_by_symbol])),
        "avg_buyhold_sharpe": float(np.mean([r["buy_and_hold"]["sharpe"] for r in results_by_symbol])),
        "trade_cost_bps": float(TRADE_COST_BPS),
    }

    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "train_symbol": TRAIN_SYMBOL,
        "train_symbols": train_symbols,
        "years": YEARS,
        "date_range": {"start": start_date, "end": end_date},
        "pipeline": {
            "global_model_policy": "Single pooled multi-coin model retrained monthly, reused across all coins",
            "walk_forward_mode": "Monthly strict out-of-sample",
            "per_coin_calibration": "Enabled (threshold, trade mode, position scale) using trailing historical window only",
            "autorresearch_objective": (
                "Train and select oracle-action objectives: coin/action match, expected next-day edge, "
                "position size, switching cost, and net walk-forward performance"
            ),
            "autoresearch_selection_symbols": selection_eval_symbols,
            "hidden_holdout_symbols": holdout_symbols,
            "acceptance_thresholds": ACCEPTANCE_THRESHOLDS,
        },
        "autorresearch": auto,
        "best_config": auto["best_config"],
        "best_score": float(auto["best_score"]),
        "evaluation_symbols": available_eval,
        "autoresearch_selection_symbols": selection_eval_symbols,
        "hidden_holdout_symbols": holdout_symbols,
        "results_by_symbol": results_by_symbol,
        "summary": summary,
        "calibration_rows": [
            {"symbol": symbol, **row}
            for symbol, rows in per_coin_calibrations.items()
            for row in rows
        ],
        "anti_cheat_note": (
            "Oracle action labels are computed only inside historical training windows. "
            "Final walk-forward oracle paths are computed after evaluation for verification and gap scoring."
        ),
    }

    summary_df = pd.DataFrame(summary_rows).sort_values("symbol")
    years_tag = f"{YEARS}y"
    report_path = reports_dir / f"crypto_autoresearch_{years_tag}_{timestamp_tag}.json"
    summary_csv_path = reports_dir / f"crypto_autoresearch_{years_tag}_{timestamp_tag}.csv"

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
