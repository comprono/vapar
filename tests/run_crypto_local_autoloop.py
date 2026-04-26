from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import research_layer.crypto_autoresearch as ca


warnings.filterwarnings("ignore", category=ConvergenceWarning)


TOP10_SYMBOLS = [
    "BTC-USD",
    "ETH-USD",
    "BNB-USD",
    "SOL-USD",
    "XRP-USD",
    "ADA-USD",
    "DOGE-USD",
    "TRX-USD",
    "AVAX-USD",
    "DOT-USD",
]

NEW_HOLDOUT10_SYMBOLS = [
    "LINK-USD",
    "LTC-USD",
    "BCH-USD",
    "XLM-USD",
    "NEAR-USD",
    "HBAR-USD",
    "ICP-USD",
    "ETC-USD",
    "FIL-USD",
    "ATOM-USD",
]

TOP20_SYMBOLS = TOP10_SYMBOLS + NEW_HOLDOUT10_SYMBOLS


def _clamp(value: float, low: float, high: float) -> float:
    return float(max(low, min(high, value)))


def _bounded_metric(value: float, limit: float = 3.0) -> float:
    value = float(value)
    if not np.isfinite(value):
        return 0.0
    return _clamp(value, -limit, limit)


def _score_report(report: Dict[str, Any]) -> float:
    summary = report.get("summary", {})
    rows = report.get("results_by_symbol", [])
    if not rows:
        return -999.0

    best_config = report.get("autorresearch", {}).get("best_config", {})
    portfolio = report.get("portfolio", {})
    model_kind = str(best_config.get("model_kind"))
    is_portfolio_selector = model_kind == "xmom_topk" or model_kind in getattr(ca, "ORACLE_PORTFOLIO_MODEL_KINDS", set())
    initial_capital = float(portfolio.get("initial_capital", 0.0) or 0.0)
    portfolio_return = 0.0
    if initial_capital > 0.0:
        portfolio_return = float(portfolio.get("final_model_balance", initial_capital)) / initial_capital - 1.0
    if is_portfolio_selector and isinstance(portfolio.get("model_metrics"), dict):
        model_metrics = portfolio["model_metrics"]
        buyhold_return = float(portfolio.get("buyhold_return", 0.0))
        portfolio_excess = float(portfolio_return - buyhold_return)
        negative_excess_penalty = 2.0 + 20.0 * abs(portfolio_excess) if portfolio_excess < 0.0 else 0.0
        weak_model_edge_penalty = 0.75 if model_kind not in {"xmom_topk"} and portfolio_excess < 0.0 else 0.0
        return (
            portfolio_excess
            + 1.25 * portfolio_return
            + 0.45 * _bounded_metric(float(model_metrics.get("sharpe", 0.0)))
            - 1.15 * float(model_metrics.get("max_drawdown", 0.0))
            - 0.25 * float(model_metrics.get("trade_rate", 0.0))
            - 0.40 * float(model_metrics.get("avg_turnover_per_day", 0.0))
            - negative_excess_penalty
            - weak_model_edge_penalty
        )

    avg_drawdown = float(np.mean([float(r["model_walkforward"]["max_drawdown"]) for r in rows]))
    avg_trade_rate = float(summary.get("avg_model_trade_rate", 0.0))
    avg_turnover = float(summary.get("avg_model_turnover_per_day", 0.0))
    avg_active_rate = float(summary.get("avg_model_active_rate", 0.0))
    avg_excess = float(summary.get("avg_excess_vs_buyhold", 0.0))
    negative_excess_penalty = 0.0
    if avg_excess < 0.0:
        negative_excess_penalty = 2.0 + 20.0 * abs(avg_excess)
    weak_model_edge_penalty = 0.0
    robust_baselines = {"buy_hold", "trend_120", "xmom_topk"}
    if str(best_config.get("trade_mode")) != "flat" and str(best_config.get("model_kind")) not in robust_baselines and avg_excess < 0.05:
        weak_model_edge_penalty = 1.50
    return (
        avg_excess
        + 1.25 * portfolio_return
        + 0.45 * _bounded_metric(float(summary.get("avg_model_sharpe", 0.0)))
        - 1.15 * avg_drawdown
        + 0.60 * float(summary.get("acceptance_rate", 0.0))
        - 0.25 * avg_trade_rate
        - 0.40 * avg_turnover
        - 0.20 * max(avg_active_rate - 0.82, 0.0)
        - negative_excess_penalty
        - weak_model_edge_penalty
    )


def _mutate_configs(best_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    base = copy.deepcopy(best_config)
    hidden_layers = list(base.get("hidden_layers", [64, 32]))
    h0 = int(hidden_layers[0]) if hidden_layers else 64
    h1 = int(hidden_layers[1]) if len(hidden_layers) > 1 else max(16, h0 // 2)

    alpha = float(base.get("alpha", 0.001))
    lr = float(base.get("learning_rate_init", 0.001))
    threshold = float(base.get("threshold", 0.002))
    max_iter = int(base.get("max_iter", 180))
    trade_mode = str(base.get("trade_mode", "long_short"))
    model_kind = str(base.get("model_kind", "regression"))
    trend_filter = bool(base.get("trend_filter", model_kind.startswith("gbt")))
    trend_min = float(base.get("trend_min", 0.0))
    momentum_min = float(base.get("momentum_min", 0.0))
    max_vol_raw = base.get("max_vol_20", 0.06)
    max_vol_20 = 0.06 if max_vol_raw is None else float(max_vol_raw)

    if trade_mode == "flat":
        return [
            {
                "hidden_layers": [64, 32],
                "alpha": 0.0001,
                "learning_rate_init": 0.045,
                "threshold": 0.001,
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
                **base,
                "threshold": 1.0e9,
                "position_scale": 0.0,
                "trade_mode": "flat",
                "max_vol_20": None,
            },
            {
                "hidden_layers": [64, 32],
                "alpha": 0.0001,
                "learning_rate_init": 0.05,
                "threshold": 0.008,
                "max_iter": 220,
                "trade_mode": "long_only",
                "model_kind": "gbt_regression",
                "trend_filter": True,
                "trend_min": 0.003,
                "momentum_min": 0.010,
                "max_vol_20": 0.045,
            },
            {
                "hidden_layers": [64, 32],
                "alpha": 0.0001,
                "learning_rate_init": 0.04,
                "threshold": 0.10,
                "max_iter": 240,
                "trade_mode": "long_only",
                "model_kind": "gbt_classification",
                "trend_filter": True,
                "trend_min": 0.003,
                "momentum_min": 0.010,
                "max_vol_20": 0.045,
            },
            {
                "hidden_layers": [64, 32],
                "alpha": 0.0001,
                "learning_rate_init": 0.01,
                "threshold": 0.035,
                "max_iter": 80,
                "trade_mode": "long_only",
                "model_kind": "trend_following",
                "trend_filter": True,
                "trend_min": 0.0,
                "momentum_min": 0.0,
                "max_vol_20": 0.09,
            },
            {
                "hidden_layers": [64, 32],
                "alpha": 0.0001,
                "learning_rate_init": 0.01,
                "threshold": 0.075,
                "max_iter": 80,
                "trade_mode": "long_only",
                "model_kind": "trend_following",
                "trend_filter": True,
                "trend_min": 0.002,
                "momentum_min": 0.005,
                "max_vol_20": 0.075,
            },
            {
                "hidden_layers": [64, 32],
                "alpha": 0.0001,
                "learning_rate_init": 0.01,
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
                "learning_rate_init": 0.01,
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
                "learning_rate_init": 0.01,
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
                "learning_rate_init": 0.01,
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
                "learning_rate_init": 0.01,
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
                "learning_rate_init": 0.01,
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

    candidates = [
        {
            "hidden_layers": [64, 32],
            "alpha": 0.0001,
            "learning_rate_init": 0.045,
            "threshold": 0.001,
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
            "hidden_layers": [64, 32],
            "alpha": 0.0001,
            "learning_rate_init": 0.045,
            "threshold": 0.0025,
            "max_iter": 260,
            "trade_mode": "long_short",
            "model_kind": "gbt_oracle_portfolio",
            "top_k": 2,
            "trend_filter": False,
            "trend_min": 0.0,
            "momentum_min": 0.0,
            "max_vol_20": None,
            "objective": "oracle_portfolio_selector",
        },
        {
            "hidden_layers": [h0, h1],
            "alpha": alpha,
            "learning_rate_init": lr,
            "threshold": threshold,
            "max_iter": max_iter,
            "trade_mode": trade_mode,
            "model_kind": model_kind,
            "trend_filter": trend_filter,
            "trend_min": trend_min,
            "momentum_min": momentum_min,
            "max_vol_20": max_vol_20,
        },
        {
            "hidden_layers": [max(32, int(h0 * 1.25)), max(16, int(h1 * 1.25))],
            "alpha": _clamp(alpha * 0.7, 1e-5, 0.02),
            "learning_rate_init": _clamp(lr * 0.85, 1e-4, 0.01),
            "threshold": _clamp(max(threshold * 1.35, 0.004), 0.0005, 0.20),
            "max_iter": min(max_iter + 20, 320),
            "trade_mode": "long_only",
            "model_kind": model_kind,
            "trend_filter": True,
            "trend_min": _clamp(trend_min, 0.0, 0.02),
            "momentum_min": _clamp(momentum_min, 0.0, 0.06),
            "max_vol_20": _clamp(max_vol_20 * 0.85, 0.02, 0.10),
        },
        {
            "hidden_layers": [max(32, int(h0 * 0.9)), max(16, int(h1 * 0.9))],
            "alpha": _clamp(alpha * 1.25, 1e-5, 0.02),
            "learning_rate_init": _clamp(lr * 1.10, 1e-4, 0.01),
            "threshold": _clamp(max(threshold * 1.75, 0.006), 0.0005, 0.20),
            "max_iter": min(max_iter + 10, 320),
            "trade_mode": "long_only",
            "model_kind": model_kind,
            "trend_filter": True,
            "trend_min": _clamp(max(trend_min, 0.002), 0.0, 0.03),
            "momentum_min": _clamp(max(momentum_min, 0.005), 0.0, 0.08),
            "max_vol_20": _clamp(max_vol_20, 0.02, 0.10),
        },
        {
            "hidden_layers": [h0, h1],
            "alpha": _clamp(alpha * 1.4, 1e-5, 0.02),
            "learning_rate_init": _clamp(lr * 0.75, 1e-4, 0.01),
            "threshold": _clamp(max(threshold, 0.05), 0.01, 0.30),
            "max_iter": min(max_iter + 30, 340),
            "trade_mode": "long_only",
            "model_kind": "classification",
            "trend_filter": True,
            "trend_min": _clamp(trend_min, 0.0, 0.03),
            "momentum_min": _clamp(momentum_min, 0.0, 0.08),
            "max_vol_20": _clamp(max_vol_20 * 0.90, 0.02, 0.10),
        },
        {
            "hidden_layers": [max(48, int(h0 * 1.5)), max(24, int(h1 * 1.5))],
            "alpha": _clamp(alpha * 0.9, 1e-5, 0.02),
            "learning_rate_init": _clamp(lr * 0.9, 1e-4, 0.01),
            "threshold": _clamp(threshold * 0.9, 0.0005, 0.20),
            "max_iter": min(max_iter + 40, 360),
            "trade_mode": "long_short",
            "model_kind": "regression",
            "trend_filter": True,
            "trend_min": _clamp(max(trend_min, 0.001), 0.0, 0.03),
            "momentum_min": _clamp(max(momentum_min, 0.0025), 0.0, 0.08),
            "max_vol_20": _clamp(max_vol_20, 0.02, 0.10),
        },
        {
            "hidden_layers": [max(32, h0), max(16, h1)],
            "alpha": _clamp(alpha, 1e-5, 0.02),
            "learning_rate_init": _clamp(lr, 1e-4, 0.01),
            "threshold": _clamp(threshold, 0.0005, 0.20),
            "max_iter": min(max_iter, 320),
            "trade_mode": "long_short",
            "model_kind": "classification" if model_kind == "regression" else "regression",
            "trend_filter": False,
            "trend_min": 0.0,
            "momentum_min": 0.0,
            "max_vol_20": _clamp(max_vol_20, 0.02, 0.10),
        },
        {
            "hidden_layers": [max(48, h0), max(24, h1)],
            "alpha": _clamp(alpha, 1e-5, 0.02),
            "learning_rate_init": _clamp(lr, 1e-4, 0.08),
            "threshold": _clamp(max(threshold * 2.2, 0.008), 0.001, 0.25),
            "max_iter": min(max_iter + 30, 360),
            "trade_mode": "long_only",
            "model_kind": "gbt_regression",
            "trend_filter": True,
            "trend_min": _clamp(max(trend_min, 0.003), 0.0, 0.03),
            "momentum_min": _clamp(max(momentum_min, 0.010), 0.0, 0.08),
            "max_vol_20": _clamp(max_vol_20 * 0.75, 0.02, 0.10),
        },
        {
            "hidden_layers": [64, 32],
            "alpha": 0.0001,
            "learning_rate_init": 0.0100,
            "threshold": _clamp(max(threshold, 0.035), 0.015, 0.18),
            "max_iter": 80,
            "trade_mode": "long_only",
            "model_kind": "trend_following",
            "trend_filter": True,
            "trend_min": _clamp(trend_min, 0.0, 0.025),
            "momentum_min": _clamp(momentum_min, 0.0, 0.08),
            "max_vol_20": _clamp(max_vol_20, 0.04, 0.12),
        },
        {
            "hidden_layers": [64, 32],
            "alpha": 0.0001,
            "learning_rate_init": 0.0100,
            "threshold": _clamp(max(threshold * 1.6, 0.075), 0.035, 0.25),
            "max_iter": 80,
            "trade_mode": "long_only",
            "model_kind": "trend_following",
            "trend_filter": True,
            "trend_min": _clamp(max(trend_min, 0.002), 0.0, 0.03),
            "momentum_min": _clamp(max(momentum_min, 0.005), 0.0, 0.10),
            "max_vol_20": _clamp(max_vol_20 * 0.9, 0.035, 0.10),
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
            "threshold": _clamp(threshold, 0.0, 0.20),
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
            "threshold": _clamp(max(threshold, 0.08), 0.0, 0.25),
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
            "threshold": _clamp(threshold, 0.0, 0.15),
            "max_iter": 80,
            "trade_mode": "long_only",
            "model_kind": "xmom_topk",
            "top_k": max(1, int(base.get("top_k", 5)) - 1),
            "trend_filter": False,
            "trend_min": 0.0,
            "momentum_min": 0.0,
            "max_vol_20": None,
        },
        {
            "hidden_layers": [64, 32],
            "alpha": 0.0001,
            "learning_rate_init": 0.0100,
            "threshold": _clamp(threshold, 0.0, 0.15),
            "max_iter": 80,
            "trade_mode": "long_only",
            "model_kind": "xmom_topk",
            "top_k": min(10, max(1, int(base.get("top_k", 5)) + 1)),
            "trend_filter": False,
            "trend_min": 0.0,
            "momentum_min": 0.0,
            "max_vol_20": None,
        },
    ]

    # Deduplicate while preserving order.
    out: List[Dict[str, Any]] = []
    seen = set()
    for cfg in candidates:
        key = json.dumps(cfg, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(cfg)
    return out


def _canonical_config(config: Dict[str, Any]) -> str:
    return json.dumps(config, sort_keys=True, separators=(",", ":"))


def _config_set_signature(configs: List[Dict[str, Any]]) -> str:
    return "|".join(_canonical_config(cfg) for cfg in configs)


def _exploration_configs(anchor_config: Dict[str, Any], round_idx: int) -> List[Dict[str, Any]]:
    """Build deterministic extra candidates when normal mutation has plateaued."""
    anchor = copy.deepcopy(anchor_config) if isinstance(anchor_config, dict) else {}
    configs: List[Dict[str, Any]] = []

    for threshold in (0.0005, 0.0010, 0.0025, 0.0050):
        for top_k in (1, 2, 3):
            configs.append(
                {
                    "hidden_layers": [64, 32],
                    "alpha": 0.0001,
                    "learning_rate_init": 0.0450,
                    "threshold": float(threshold),
                    "max_iter": 260,
                    "trade_mode": "long_short",
                    "model_kind": "gbt_oracle_portfolio",
                    "top_k": int(top_k),
                    "trend_filter": False,
                    "trend_min": 0.0,
                    "momentum_min": 0.0,
                    "max_vol_20": None,
                    "objective": "oracle_portfolio_selector",
                }
            )

    for threshold in (0.0, 0.01, 0.02, 0.04, 0.08):
        for top_k in range(1, 11):
            configs.append(
                {
                    "hidden_layers": [64, 32],
                    "alpha": 0.0001,
                    "learning_rate_init": 0.0100,
                    "threshold": float(threshold),
                    "max_iter": 80,
                    "trade_mode": "long_only",
                    "model_kind": "xmom_topk",
                    "top_k": int(top_k),
                    "trend_filter": False,
                    "trend_min": 0.0,
                    "momentum_min": 0.0,
                    "max_vol_20": None,
                }
            )

    for threshold in (0.0, 0.02, 0.05, 0.10, 0.15):
        configs.append(
            {
                "hidden_layers": [64, 32],
                "alpha": 0.0001,
                "learning_rate_init": 0.0100,
                "threshold": float(threshold),
                "max_iter": 80,
                "trade_mode": "long_only",
                "model_kind": "trend_120",
                "trend_filter": False,
                "trend_min": 0.0,
                "momentum_min": 0.0,
                "max_vol_20": None,
            }
        )

    configs.extend(_mutate_configs(anchor) if anchor else copy.deepcopy(ca.DEFAULT_CONFIGS))

    # Rotate deterministically so repeated plateau rounds do not resubmit the same first batch.
    if configs:
        offset = (round_idx * 7) % len(configs)
        configs = configs[offset:] + configs[:offset]

    out: List[Dict[str, Any]] = []
    seen = set()
    for cfg in configs:
        key = _canonical_config(cfg)
        if key in seen:
            continue
        seen.add(key)
        out.append(cfg)
        if len(out) >= 24:
            break
    return out


def _augment_verification_files(report: Dict[str, Any], initial_capital: float) -> Dict[str, Any]:
    updated_paths: List[str] = []
    equity_frames: List[pd.DataFrame] = []
    result_rows = report.get("results_by_symbol", [])
    per_symbol_capital = float(initial_capital) / max(len(result_rows), 1)
    best_config = report.get("autorresearch", {}).get("best_config", {})
    is_xmom = str(best_config.get("model_kind")) == "xmom_topk"
    is_oracle_portfolio = str(best_config.get("model_kind")) in getattr(ca, "ORACLE_PORTFOLIO_MODEL_KINDS", set())
    is_portfolio_selector = is_xmom or is_oracle_portfolio
    loaded_frames: Dict[str, pd.DataFrame] = {}
    portfolio_model_override: pd.Series | None = None
    portfolio_oracle_override: pd.Series | None = None

    for row in result_rows:
        p = Path(str(row.get("daily_verification_path", "")))
        if not p.exists():
            continue

        df = pd.read_csv(p)
        if "model_return" not in df.columns or "buyhold_return" not in df.columns or "oracle_return" not in df.columns:
            continue
        symbol = str(row.get("symbol", p.stem.replace("_daily_verification", "")))
        loaded_frames[symbol] = df

    if loaded_frames:
        returns_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
        for symbol, df in loaded_frames.items():
            for _, row in df.iterrows():
                dt = pd.Timestamp(str(row["date"]))
                returns_by_date.setdefault(dt, {})[symbol] = float(row["target_return"])
        oracle_rows = ca._oracle_portfolio_label_rows(
            returns_by_date=returns_by_date,
            symbols=list(loaded_frames),
            trade_cost_rate=ca.TRADE_COST_RATE,
        )
        oracle_daily: List[float] = []
        oracle_dates: List[pd.Timestamp] = []
        for dt in sorted(returns_by_date):
            selected_label = None
            fallback_label = None
            for symbol, rows in oracle_rows.items():
                label = rows.get(dt)
                if label is None:
                    continue
                fallback_label = label
                if str(label.get("oracle_selected_symbol", "CASH")) == symbol:
                    selected_label = label
                    break
            label = selected_label or fallback_label
            oracle_daily.append(max(float(label.get("oracle_expected_edge", 0.0)) if label else 0.0, -0.999999))
            oracle_dates.append(dt)
        portfolio_oracle_override = pd.Series(oracle_daily, index=pd.to_datetime(oracle_dates), dtype=float)

    if is_portfolio_selector and loaded_frames:
        all_dates = sorted({d for df in loaded_frames.values() for d in df["date"].astype(str).tolist()})
        previous_positions = {symbol: 0.0 for symbol in loaded_frames}
        updated: Dict[str, pd.DataFrame] = {}
        portfolio_daily_returns: List[float] = []
        portfolio_daily_turnover: List[float] = []
        portfolio_daily_exposure: List[float] = []
        portfolio_dates: List[str] = []
        for symbol, df in loaded_frames.items():
            df = df.copy()
            df["model_position"] = 0.0
            df["model_return"] = 0.0
            updated[symbol] = df

        for dt in all_dates:
            day_scores: Dict[str, float] = {}
            day_controls: List[pd.Series] = []
            for symbol, df in loaded_frames.items():
                rows_for_day = df.index[df["date"].astype(str) == dt].tolist()
                if not rows_for_day:
                    continue
                row = df.loc[rows_for_day[0]]
                day_scores[symbol] = float(row["prediction_score"])
                day_controls.append(row)
            control = day_controls[0] if day_controls else pd.Series(dtype=float)
            top_k = max(1, int(control.get("top_k", best_config.get("top_k", 5)) or 1))
            threshold = float(control.get("threshold", best_config.get("threshold", 0.0)))
            trade_mode = str(control.get("trade_mode", best_config.get("trade_mode", "long_only" if is_xmom else "long_short")))
            position_scale = float(control.get("position_scale", best_config.get("position_scale", 1.0)))
            target_weight = {symbol: 0.0 for symbol in loaded_frames}
            if trade_mode == "flat" or position_scale <= 0.0:
                ranked = []
            elif is_oracle_portfolio:
                candidates = [
                    (symbol, abs(score), 1.0 if score > 0.0 else -1.0)
                    for symbol, score in day_scores.items()
                    if abs(score) > threshold and (trade_mode != "long_only" or score > threshold)
                ]
                ranked = sorted(candidates, key=lambda item: item[1], reverse=True)[:top_k]
            else:
                ranked = [
                    (symbol, score, 1.0)
                    for symbol, score in sorted(day_scores.items(), key=lambda item: item[1], reverse=True)
                    if score > threshold
                ][:top_k]
            if ranked:
                sleeve_exposure = position_scale / float(len(ranked))
                for symbol, _, direction in ranked:
                    target_weight[symbol] = sleeve_exposure * direction

            turn = sum(
                abs(float(target_weight.get(symbol, 0.0)) - float(previous_positions.get(symbol, 0.0)))
                for symbol in loaded_frames
            )
            portfolio_ret = 0.0
            for symbol, df in updated.items():
                rows_for_day = df.index[df["date"].astype(str) == dt].tolist()
                if not rows_for_day:
                    continue
                idx = rows_for_day[0]
                pos = float(target_weight.get(symbol, 0.0))
                df.loc[idx, "model_position"] = pos
                portfolio_ret += pos * float(df.loc[idx, "target_return"])
            portfolio_ret -= ca.TRADE_COST_RATE * turn
            portfolio_ret = max(float(portfolio_ret), -0.999999)

            # Store the portfolio-level return on every symbol row for this date so
            # equal starting sleeves sum back to the same no-leverage portfolio.
            for _, df in updated.items():
                rows_for_day = df.index[df["date"].astype(str) == dt].tolist()
                if rows_for_day:
                    df.loc[rows_for_day[0], "model_return"] = portfolio_ret
            portfolio_dates.append(dt)
            portfolio_daily_returns.append(portfolio_ret)
            portfolio_daily_turnover.append(float(turn))
            portfolio_daily_exposure.append(float(sum(abs(v) for v in target_weight.values())))
            previous_positions = target_weight

        portfolio_model_override = pd.Series(
            portfolio_daily_returns,
            index=pd.to_datetime(portfolio_dates),
            dtype=float,
        )
        loaded_frames = updated

    for row in result_rows:
        p = Path(str(row.get("daily_verification_path", "")))
        if not p.exists():
            continue

        symbol = str(row.get("symbol", p.stem.replace("_daily_verification", "")))
        df = loaded_frames.get(symbol)
        if df is None:
            df = pd.read_csv(p)
        if "model_return" not in df.columns or "buyhold_return" not in df.columns or "oracle_return" not in df.columns:
            continue

        model_ret = df["model_return"].astype(float).to_numpy()
        buy_ret = df["buyhold_return"].astype(float).to_numpy()
        oracle_ret = df["oracle_return"].astype(float).to_numpy()

        df["initial_capital"] = float(per_symbol_capital)
        df["model_equity"] = float(per_symbol_capital) * np.cumprod(1.0 + model_ret)
        df["buyhold_equity"] = float(per_symbol_capital) * np.cumprod(1.0 + buy_ret)
        df["oracle_equity"] = float(per_symbol_capital) * np.cumprod(1.0 + oracle_ret)
        df["model_daily_pnl"] = np.concatenate(([0.0], np.diff(df["model_equity"].to_numpy(dtype=float))))
        df["buyhold_daily_pnl"] = np.concatenate(([0.0], np.diff(df["buyhold_equity"].to_numpy(dtype=float))))
        df["oracle_daily_pnl"] = np.concatenate(([0.0], np.diff(df["oracle_equity"].to_numpy(dtype=float))))

        df.to_csv(p, index=False)
        updated_paths.append(str(p))
        equity_frames.append(
            pd.DataFrame(
                {
                    "date": pd.to_datetime(df["date"]),
                    f"{symbol}_model_equity": df["model_equity"].to_numpy(dtype=float),
                    f"{symbol}_buyhold_equity": df["buyhold_equity"].to_numpy(dtype=float),
                    f"{symbol}_oracle_equity": df["oracle_equity"].to_numpy(dtype=float),
                }
            ).set_index("date")
        )

    portfolio_summary: Dict[str, Any] = {
        "initial_capital": float(initial_capital),
        "per_symbol_initial_capital": float(per_symbol_capital),
        "symbols_included": int(len(equity_frames)),
        "daily_verification_path": "",
        "final_model_balance": float(initial_capital),
        "final_buyhold_balance": float(initial_capital),
        "final_oracle_balance": float(initial_capital),
        "model_profit": 0.0,
        "buyhold_profit": 0.0,
        "oracle_profit": 0.0,
    }

    if equity_frames:
        combined = pd.concat(equity_frames, axis=1).sort_index().ffill().dropna(how="all")
        model_cols = [c for c in combined.columns if c.endswith("_model_equity")]
        buyhold_cols = [c for c in combined.columns if c.endswith("_buyhold_equity")]
        oracle_cols = [c for c in combined.columns if c.endswith("_oracle_equity")]
        portfolio_df = pd.DataFrame(
            {
                "date": combined.index.strftime("%Y-%m-%d"),
                "initial_capital": float(initial_capital),
                "model_total_balance": combined[model_cols].sum(axis=1).to_numpy(dtype=float),
                "buyhold_total_balance": combined[buyhold_cols].sum(axis=1).to_numpy(dtype=float),
                "oracle_total_balance": combined[oracle_cols].sum(axis=1).to_numpy(dtype=float),
            }
        )
        if portfolio_model_override is not None and len(portfolio_model_override) > 0:
            model_curve = float(initial_capital) * np.cumprod(
                1.0 + portfolio_model_override.reindex(combined.index).fillna(0.0).to_numpy(dtype=float)
            )
            portfolio_df["model_total_balance"] = model_curve
        if portfolio_oracle_override is not None and len(portfolio_oracle_override) > 0:
            oracle_curve = float(initial_capital) * np.cumprod(
                1.0 + portfolio_oracle_override.reindex(combined.index).fillna(0.0).to_numpy(dtype=float)
            )
            portfolio_df["oracle_total_balance"] = oracle_curve
        for balance_col, return_col in (
            ("model_total_balance", "model_return"),
            ("buyhold_total_balance", "buyhold_return"),
            ("oracle_total_balance", "oracle_return"),
        ):
            balances = portfolio_df[balance_col].to_numpy(dtype=float)
            returns = np.zeros(len(balances), dtype=float)
            if len(balances) > 0:
                returns[0] = balances[0] / float(initial_capital) - 1.0
            if len(balances) > 1:
                prev = np.maximum(balances[:-1], 1e-12)
                returns[1:] = balances[1:] / prev - 1.0
            portfolio_df[return_col] = returns
        portfolio_df["model_total_pnl"] = np.concatenate(
            ([0.0], np.diff(portfolio_df["model_total_balance"].to_numpy(dtype=float)))
        )
        portfolio_df["buyhold_total_pnl"] = np.concatenate(
            ([0.0], np.diff(portfolio_df["buyhold_total_balance"].to_numpy(dtype=float)))
        )
        portfolio_df["oracle_total_pnl"] = np.concatenate(
            ([0.0], np.diff(portfolio_df["oracle_total_balance"].to_numpy(dtype=float)))
        )

        verification_dir = Path(str(report.get("verification_dir", "")))
        if not verification_dir.exists() and updated_paths:
            verification_dir = Path(updated_paths[0]).parent
        portfolio_path = verification_dir / "portfolio_daily_verification.csv"
        portfolio_df.to_csv(portfolio_path, index=False)
        updated_paths.append(str(portfolio_path))

        final_model = float(portfolio_df["model_total_balance"].iloc[-1])
        final_buyhold = float(portfolio_df["buyhold_total_balance"].iloc[-1])
        final_oracle = float(portfolio_df["oracle_total_balance"].iloc[-1])
        model_returns = portfolio_df["model_return"].to_numpy(dtype=float)
        buyhold_returns = portfolio_df["buyhold_return"].to_numpy(dtype=float)
        portfolio_index = pd.to_datetime(portfolio_df["date"])
        turnover = np.asarray(portfolio_daily_turnover, dtype=float)
        exposure = np.asarray(portfolio_daily_exposure, dtype=float)
        if len(turnover) != len(model_returns):
            turnover = np.zeros(len(model_returns), dtype=float)
        if len(exposure) != len(model_returns):
            exposure = np.ones(len(model_returns), dtype=float)
        model_metrics = ca._metrics_from_returns(
            daily_returns=model_returns,
            index=pd.DatetimeIndex(portfolio_index),
            trade_count=int(np.sum(turnover > 1e-12)),
            active_positions=exposure,
            underlying_returns=np.ones(len(model_returns), dtype=float),
            turnover=turnover,
        )
        buyhold_metrics = ca._metrics_from_returns(
            daily_returns=buyhold_returns,
            index=pd.DatetimeIndex(portfolio_index),
            trade_count=1,
            active_positions=np.ones(len(buyhold_returns), dtype=float),
            underlying_returns=buyhold_returns,
            turnover=np.zeros(len(buyhold_returns), dtype=float),
        )
        portfolio_summary.update(
            {
                "daily_verification_path": str(portfolio_path),
                "final_model_balance": final_model,
                "final_buyhold_balance": final_buyhold,
                "final_oracle_balance": final_oracle,
                "model_profit": final_model - float(initial_capital),
                "buyhold_profit": final_buyhold - float(initial_capital),
                "oracle_profit": final_oracle - float(initial_capital),
                "model_return": final_model / float(initial_capital) - 1.0,
                "buyhold_return": final_buyhold / float(initial_capital) - 1.0,
                "oracle_return": final_oracle / float(initial_capital) - 1.0,
                "excess_vs_buyhold": final_model / float(initial_capital) - final_buyhold / float(initial_capital),
                "model_metrics": model_metrics,
                "buyhold_metrics": buyhold_metrics,
            }
        )

    report["portfolio"] = portfolio_summary
    report["verification_files_updated"] = updated_paths
    report_path = Path(str(report.get("report_path", "")))
    if report_path.exists():
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return {"updated_paths": updated_paths, "portfolio": portfolio_summary}


def _apply_runtime_settings(
    years: int,
    month_stride: int,
    configs: List[Dict[str, Any]],
    universe_symbols: List[str],
    train_symbols: List[str],
    selection_symbols: List[str],
) -> None:
    days = int(years * 365)
    ca.YEARS = int(years)
    ca.TRAIN_SYMBOL = "BTC-USD"
    ca.TRAIN_SYMBOLS = train_symbols[:]
    ca.AUTORESEARCH_EVAL_SYMBOLS = selection_symbols[:]
    ca.EVAL_SYMBOLS = universe_symbols[:]
    ca.AUTORESEARCH_MONTH_STRIDE = int(month_stride)
    # Relax defaults for short-horizon local runs.
    ca.MIN_TRAIN_SAMPLES = int(max(120, min(365, days - 40)))
    ca.TRAIN_LOOKBACK_DAYS = int(max(180, days))
    ca.CALIBRATION_LOOKBACK_DAYS = int(max(90, min(365, days)))
    ca.MIN_CALIBRATION_SAMPLES = int(max(30, min(60, ca.CALIBRATION_LOOKBACK_DAYS // 2)))
    ca.ACCEPTANCE_THRESHOLDS = {
        "must_beat_buyhold": True,
        "min_sharpe": 0.20,
        "min_sortino": 0.30,
        "max_drawdown": 0.55,
        "max_trade_rate": 0.60,
        "max_turnover_per_day": 0.70,
        "max_active_rate": 0.88,
    }
    ca.DEFAULT_CONFIGS = copy.deepcopy(configs)


def _write_loop_progress(
    loop_dir: Path,
    rounds: List[Dict[str, Any]],
    best_round: Dict[str, Any] | None,
    years: int,
    month_stride: int,
    iterations: int,
    initial_capital: float,
    time_budget_minutes: float,
    args: argparse.Namespace,
    universe_symbols: List[str],
    train_symbols: List[str],
    selection_symbols: List[str],
    holdout_symbols: List[str],
) -> Dict[str, Any]:
    rounds_csv_path = loop_dir / "local_autoloop_rounds.csv"
    rounds_json_path = loop_dir / "local_autoloop_rounds.json"
    pd.DataFrame(rounds).to_csv(rounds_csv_path, index=False)

    progress = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "mode": "local_short_horizon_autoloop",
        "years": years,
        "month_stride": month_stride,
        "iterations_requested": iterations,
        "iterations_completed": int(len(rounds)),
        "initial_capital": float(initial_capital),
        "time_budget_minutes": float(time_budget_minutes),
        "targets": {
            "target_sharpe": float(args.target_sharpe),
            "target_excess": float(args.target_excess),
            "target_acceptance": float(args.target_acceptance),
            "max_turnover": float(args.max_turnover),
        },
        "universe": universe_symbols,
        "train_symbols": train_symbols,
        "autoresearch_selection_symbols": selection_symbols,
        "hidden_holdout_symbols": holdout_symbols,
        "best_round": best_round,
        "rounds": rounds,
        "note": (
            "Oracle action labels are generated only from historical training windows; final oracle remains verification-only."
        ),
    }
    rounds_json_path.write_text(json.dumps(progress, indent=2), encoding="utf-8")
    return {
        "progress": progress,
        "rounds_csv_path": rounds_csv_path,
        "rounds_json_path": rounds_json_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local-only short-horizon crypto autoloop (top-10, daily compounding verification)."
    )
    parser.add_argument("--years", type=int, default=2, help="Lookback years (2 to 5 supported locally).")
    parser.add_argument("--iterations", type=int, default=4, help="Number of local retrain/tune rounds.")
    parser.add_argument("--month-stride", type=int, default=1, help="Walk-forward month stride for selection.")
    parser.add_argument("--initial-capital", type=float, default=1000.0, help="Initial capital X for equity columns.")
    parser.add_argument("--target-sharpe", type=float, default=0.20, help="Stop when avg model sharpe reaches this.")
    parser.add_argument("--target-excess", type=float, default=0.00, help="Stop when avg excess vs buy-hold reaches this.")
    parser.add_argument("--target-acceptance", type=float, default=0.40, help="Stop when acceptance rate reaches this.")
    parser.add_argument("--max-turnover", type=float, default=0.70, help="Stop only if avg turnover/day is below this.")
    parser.add_argument("--output-dir", type=str, default="data/reports", help="Directory for loop summary artifacts.")
    parser.add_argument(
        "--time-budget-minutes",
        type=float,
        default=0.0,
        help="If > 0, keep improving until this wall-clock budget is reached instead of stopping on target thresholds.",
    )
    parser.add_argument(
        "--holdout-new-coins",
        action="store_true",
        help="Train/autoresearch on the original 10 coins, then verify on 20 coins including 10 hidden new holdout coins.",
    )
    return parser.parse_args()


def main() -> None:
    os.chdir(REPO_ROOT)
    args = parse_args()
    years = max(2, min(int(args.years), 5))
    if years != int(args.years):
        print(f"[local-autoloop] Clamped years from {args.years} to {years}")

    month_stride = max(1, int(args.month_stride))
    iterations = max(1, int(args.iterations))
    initial_capital = float(args.initial_capital)
    time_budget_minutes = max(0.0, float(args.time_budget_minutes))
    loop_started_at = datetime.now(UTC)
    universe_symbols = TOP20_SYMBOLS[:] if args.holdout_new_coins else TOP10_SYMBOLS[:]
    train_symbols = TOP10_SYMBOLS[:]
    selection_symbols = TOP10_SYMBOLS[:]
    holdout_symbols = [s for s in universe_symbols if s not in set(selection_symbols)]

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    loop_dir = Path(args.output_dir) / f"local_crypto_autoloop_{timestamp}"
    loop_dir.mkdir(parents=True, exist_ok=True)

    print("[local-autoloop] Starting local loop", flush=True)
    print(f"[local-autoloop] years={years}, iterations={iterations}, month_stride={month_stride}", flush=True)
    if time_budget_minutes > 0.0:
        print(f"[local-autoloop] time_budget_minutes={time_budget_minutes}", flush=True)
    print(f"[local-autoloop] universe={universe_symbols}", flush=True)
    if holdout_symbols:
        print(f"[local-autoloop] hidden_holdout={holdout_symbols}", flush=True)

    current_configs = copy.deepcopy(ca.DEFAULT_CONFIGS)
    rounds: List[Dict[str, Any]] = []
    best_round: Dict[str, Any] | None = None
    seen_config_sets: set[str] = set()
    stale_rounds = 0
    plateau_patience = 3

    for round_idx in range(1, iterations + 1):
        elapsed_minutes = (datetime.now(UTC) - loop_started_at).total_seconds() / 60.0
        if time_budget_minutes > 0.0 and elapsed_minutes >= time_budget_minutes:
            print(f"[local-autoloop] Time budget reached before round {round_idx}.", flush=True)
            break

        started_at = datetime.now(UTC)
        config_set_key = _config_set_signature(current_configs)
        if config_set_key in seen_config_sets:
            anchor_config = best_round.get("best_config", {}) if best_round else {}
            current_configs = _exploration_configs(anchor_config, round_idx)
            config_set_key = _config_set_signature(current_configs)
            print(
                f"[local-autoloop] Repeated candidate set detected; using broader exploration ({len(current_configs)} configs).",
                flush=True,
            )
        seen_config_sets.add(config_set_key)

        print(f"[local-autoloop] Round {round_idx}/{iterations} -> training/evaluating...", flush=True)
        _apply_runtime_settings(
            years=years,
            month_stride=month_stride,
            configs=current_configs,
            universe_symbols=universe_symbols,
            train_symbols=train_symbols,
            selection_symbols=selection_symbols,
        )
        report = ca.run_crypto_7y_autoresearch()
        verification_aug = _augment_verification_files(report, initial_capital=initial_capital)

        summary = report.get("summary", {})
        portfolio = verification_aug.get("portfolio", {}) if isinstance(verification_aug, dict) else {}
        score = _score_report(report)

        row = {
            "round": round_idx,
            "score": float(score),
            "report_path": report.get("report_path"),
            "summary_csv_path": report.get("summary_csv_path"),
            "verification_dir": report.get("verification_dir"),
            "best_config": report.get("autorresearch", {}).get("best_config", {}),
            "avg_excess_vs_buyhold": float(summary.get("avg_excess_vs_buyhold", 0.0)),
            "acceptance_rate": float(summary.get("acceptance_rate", 0.0)),
            "avg_model_sharpe": float(summary.get("avg_model_sharpe", 0.0)),
            "avg_model_trade_rate": float(summary.get("avg_model_trade_rate", 0.0)),
            "avg_model_turnover_per_day": float(summary.get("avg_model_turnover_per_day", 0.0)),
            "avg_model_active_rate": float(summary.get("avg_model_active_rate", 0.0)),
            "symbols_evaluated": int(summary.get("symbols_evaluated", 0)),
            "symbols_accepted": int(summary.get("symbols_accepted", 0)),
            "avg_model_total_return": float(summary.get("avg_model_total_return", 0.0)),
            "avg_buyhold_total_return": float(summary.get("avg_buyhold_total_return", 0.0)),
            "portfolio_initial_capital": float(portfolio.get("initial_capital", initial_capital)),
            "portfolio_final_model_balance": float(portfolio.get("final_model_balance", initial_capital)),
            "portfolio_final_buyhold_balance": float(portfolio.get("final_buyhold_balance", initial_capital)),
            "portfolio_final_oracle_balance": float(portfolio.get("final_oracle_balance", initial_capital)),
            "portfolio_model_return": float(portfolio.get("model_return", 0.0)),
            "portfolio_buyhold_return": float(portfolio.get("buyhold_return", 0.0)),
            "portfolio_excess_vs_buyhold": float(portfolio.get("excess_vs_buyhold", 0.0)),
            "portfolio_model_sharpe": float(portfolio.get("model_metrics", {}).get("sharpe", 0.0)) if isinstance(portfolio.get("model_metrics"), dict) else 0.0,
            "portfolio_model_turnover_per_day": float(portfolio.get("model_metrics", {}).get("avg_turnover_per_day", 0.0)) if isinstance(portfolio.get("model_metrics"), dict) else 0.0,
            "portfolio_model_active_rate": float(portfolio.get("model_metrics", {}).get("active_rate", 0.0)) if isinstance(portfolio.get("model_metrics"), dict) else 0.0,
            "portfolio_daily_verification_path": str(portfolio.get("daily_verification_path", "")),
        }
        rounds.append(row)

        display_excess = row["portfolio_excess_vs_buyhold"] if row["portfolio_daily_verification_path"] else row["avg_excess_vs_buyhold"]
        display_sharpe = row["portfolio_model_sharpe"] if row["portfolio_daily_verification_path"] else row["avg_model_sharpe"]
        display_turnover = row["portfolio_model_turnover_per_day"] if row["portfolio_daily_verification_path"] else row["avg_model_turnover_per_day"]
        display_active = row["portfolio_model_active_rate"] if row["portfolio_daily_verification_path"] else row["avg_model_active_rate"]
        print(
            "[local-autoloop] "
            f"score={row['score']:.4f}, "
            f"portfolio_excess={display_excess:.4f}, "
            f"portfolio_sharpe={display_sharpe:.4f}, "
            f"portfolio_turnover/day={display_turnover:.4f}, "
            f"portfolio_active={display_active:.4f}, "
            f"acceptance={row['acceptance_rate']:.4f}, "
            f"final_balance=${row['portfolio_final_model_balance']:.2f}, "
            f"elapsed={(datetime.now(UTC) - started_at).total_seconds():.1f}s",
            flush=True,
        )

        improved = best_round is None or row["score"] > float(best_round["score"]) + 1e-9
        if improved:
            best_round = row
            stale_rounds = 0
        else:
            stale_rounds += 1

        progress_paths = _write_loop_progress(
            loop_dir=loop_dir,
            rounds=rounds,
            best_round=best_round,
            years=years,
            month_stride=month_stride,
            iterations=iterations,
            initial_capital=initial_capital,
            time_budget_minutes=time_budget_minutes,
            args=args,
            universe_symbols=universe_symbols,
            train_symbols=train_symbols,
            selection_symbols=selection_symbols,
            holdout_symbols=holdout_symbols,
        )
        print(
            f"[local-autoloop] Progress saved: {progress_paths['rounds_json_path']}",
            flush=True,
        )

        elapsed_minutes = (datetime.now(UTC) - loop_started_at).total_seconds() / 60.0
        if time_budget_minutes > 0.0 and elapsed_minutes >= time_budget_minutes:
            print("[local-autoloop] Time budget reached.", flush=True)
            break
        if time_budget_minutes > 0.0 and stale_rounds >= plateau_patience:
            print(
                f"[local-autoloop] Plateau stop: no best-score improvement for {stale_rounds} rounds.",
                flush=True,
            )
            break

        if (
            time_budget_minutes <= 0.0
            and
            row["avg_model_sharpe"] >= float(args.target_sharpe)
            and row["avg_excess_vs_buyhold"] >= float(args.target_excess)
            and row["acceptance_rate"] >= float(args.target_acceptance)
            and row["avg_model_turnover_per_day"] <= float(args.max_turnover)
        ):
            print("[local-autoloop] Stop condition met.", flush=True)
            break

        best_source = best_round if best_round is not None else row
        best_config = best_source["best_config"] if isinstance(best_source.get("best_config"), dict) else {}
        current_configs = _mutate_configs(best_config) if best_config else copy.deepcopy(ca.DEFAULT_CONFIGS)

    progress_paths = _write_loop_progress(
        loop_dir=loop_dir,
        rounds=rounds,
        best_round=best_round,
        years=years,
        month_stride=month_stride,
        iterations=iterations,
        initial_capital=initial_capital,
        time_budget_minutes=time_budget_minutes,
        args=args,
        universe_symbols=universe_symbols,
        train_symbols=train_symbols,
        selection_symbols=selection_symbols,
        holdout_symbols=holdout_symbols,
    )
    rounds_csv_path = progress_paths["rounds_csv_path"]
    rounds_json_path = progress_paths["rounds_json_path"]

    print("\n=== Local Crypto AutoLoop Complete ===", flush=True)
    print(f"Rounds CSV: {rounds_csv_path}", flush=True)
    print(f"Rounds JSON: {rounds_json_path}", flush=True)
    if best_round:
        print(f"Best report: {best_round.get('report_path')}", flush=True)
        print(f"Best config: {best_round.get('best_config')}", flush=True)
        print(
            "Best final balance: "
            f"${float(best_round.get('portfolio_final_model_balance', initial_capital)):.2f} "
            f"from ${initial_capital:.2f}",
            flush=True,
        )
        if best_round.get("portfolio_daily_verification_path"):
            print(f"Portfolio verification: {best_round.get('portfolio_daily_verification_path')}", flush=True)


if __name__ == "__main__":
    main()
