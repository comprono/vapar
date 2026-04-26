from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research_layer import crypto_autoresearch as ca
from research_layer.deep_policy_model import DeepCryptoPolicy, DeepPolicyConfig, predict_scores, pretrain_policy, save_checkpoint, train_policy
from research_layer.deep_sequence_dataset import (
    SequenceDatasetConfig,
    build_sequence_arrays,
    fit_feature_normalizer,
    load_crypto_feature_frames,
    make_dataset,
    month_starts,
)


warnings.filterwarnings(
    "ignore",
    message="enable_nested_tensor is True, but self.use_nested_tensor is False.*",
    category=UserWarning,
)

UTC = timezone.utc


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


def _records_to_maps(
    prepared: Dict[str, pd.DataFrame],
    meta: List[Dict[str, Any]],
    score_values: np.ndarray,
) -> Tuple[Dict[pd.Timestamp, Dict[str, float]], Dict[pd.Timestamp, Dict[str, float]]]:
    returns_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
    scores_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
    for record, score in zip(meta, score_values):
        symbol = str(record["symbol"])
        dt = pd.Timestamp(record["date"])
        if symbol not in prepared or dt not in prepared[symbol].index:
            continue
        target = prepared[symbol].loc[dt].get("target")
        if pd.isna(target):
            continue
        returns_by_date.setdefault(dt, {})[symbol] = float(target)
        scores_by_date.setdefault(dt, {})[symbol] = float(score)
    return returns_by_date, scores_by_date


def _score_window(
    model: DeepCryptoPolicy,
    prepared: Dict[str, pd.DataFrame],
    symbols: List[str],
    feature_cols: List[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
    seq_config: SequenceDatasetConfig,
    mean: np.ndarray,
    std: np.ndarray,
    device: torch.device,
) -> Tuple[Dict[pd.Timestamp, Dict[str, float]], Dict[pd.Timestamp, Dict[str, float]], int]:
    arrays, meta = build_sequence_arrays(
        prepared=prepared,
        symbols=symbols,
        feature_cols=feature_cols,
        start=start,
        end=end,
        config=seq_config,
        mean=mean,
        std=std,
    )
    if len(arrays["x"]) == 0:
        return {}, {}, 0
    out = predict_scores(
        model=model,
        x=torch.tensor(arrays["x"], dtype=torch.float32),
        device=device,
    )
    returns_by_date, scores_by_date = _records_to_maps(
        prepared=prepared,
        meta=meta,
        score_values=out["score"].numpy(),
    )
    return returns_by_date, scores_by_date, int(len(arrays["x"]))


def _train_one_model(
    prepared: Dict[str, pd.DataFrame],
    symbols: List[str],
    feature_cols: List[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
    seq_config: SequenceDatasetConfig,
    model_config: DeepPolicyConfig,
    device: torch.device,
    progress_prefix: str,
) -> Tuple[DeepCryptoPolicy | None, np.ndarray, np.ndarray, Dict[str, Any]]:
    mean, std = fit_feature_normalizer(
        prepared=prepared,
        symbols=symbols,
        feature_cols=feature_cols,
        start=start,
        end=end,
    )
    arrays, _ = build_sequence_arrays(
        prepared=prepared,
        symbols=symbols,
        feature_cols=feature_cols,
        start=start,
        end=end,
        config=seq_config,
        mean=mean,
        std=std,
    )
    if len(arrays["x"]) < seq_config.min_train_samples:
        return None, mean, std, {"skipped": True, "samples": int(len(arrays["x"]))}
    dataset = make_dataset(arrays)
    model = DeepCryptoPolicy(model_config)
    pretrain_info = {"history": [], "final_loss": 0.0}
    if int(model_config.pretrain_epochs) > 0:
        pretrain_info = pretrain_policy(
            model=model,
            dataset=dataset,
            config=model_config,
            device=device,
            progress_prefix=progress_prefix,
        )
    train_info = train_policy(
        model=model,
        dataset=dataset,
        config=model_config,
        device=device,
        progress_prefix=progress_prefix,
    )
    train_info["pretrain"] = pretrain_info
    train_info["samples"] = int(len(dataset))
    train_info["skipped"] = False
    return model, mean, std, train_info


def run_deep_walkforward(args: argparse.Namespace) -> Dict[str, Any]:
    np.random.seed(42)
    torch.manual_seed(42)
    os.chdir(REPO_ROOT)

    symbols = list(dict.fromkeys(args.symbols.split(","))) if args.symbols else TOP10_SYMBOLS
    prepared, feature_cols = load_crypto_feature_frames(symbols=symbols, years=int(args.years))
    available_symbols = [symbol for symbol in symbols if symbol in prepared]
    if len(available_symbols) < 2:
        raise RuntimeError("Need at least two prepared symbols for portfolio training")

    seq_config = SequenceDatasetConfig(
        window_size=int(args.window_size),
        train_lookback_days=int(args.train_lookback_days),
        calibration_lookback_days=int(args.calibration_lookback_days),
        min_train_samples=int(args.min_train_samples),
        max_samples=int(args.max_train_samples) if int(args.max_train_samples) > 0 else None,
    )
    model_config = DeepPolicyConfig(
        input_dim=len(feature_cols),
        window_size=int(args.window_size),
        d_model=int(args.d_model),
        n_heads=int(args.n_heads),
        n_layers=int(args.n_layers),
        dropout=float(args.dropout),
        lr=float(args.lr),
        batch_size=int(args.batch_size),
        pretrain_epochs=int(args.pretrain_epochs),
        epochs=int(args.epochs),
        ranking_weight=float(args.ranking_weight),
    )
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu_only else "cpu")
    months = month_starts(prepared, ref_symbol="BTC-USD")

    returns_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
    scores_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
    configs_by_date: Dict[pd.Timestamp, Dict[str, Any]] = {}
    month_reports: List[Dict[str, Any]] = []
    checkpoint_paths: List[str] = []

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_dir = Path("data/reports") / f"deep_crypto_policy_{timestamp}"
    checkpoint_dir = report_dir / "checkpoints"
    report_dir.mkdir(parents=True, exist_ok=True)
    partial_path = report_dir / "partial_progress.json"

    eligible = []
    for month_start in months:
        train_start = month_start - pd.Timedelta(days=int(args.train_lookback_days))
        cal_start = month_start - pd.Timedelta(days=int(args.calibration_lookback_days))
        if cal_start <= train_start:
            continue
        eligible.append(month_start)
    eligible = eligible[:: max(1, int(args.month_stride))]
    if int(args.max_months) > 0:
        eligible = eligible[-int(args.max_months) :]

    for idx, month_start in enumerate(eligible, start=1):
        month_end = month_start + pd.offsets.MonthBegin(1)
        train_start = month_start - pd.Timedelta(days=int(args.train_lookback_days))
        cal_start = month_start - pd.Timedelta(days=int(args.calibration_lookback_days))
        print(
            f"[deep-policy] month {idx}/{len(eligible)} {month_start.strftime('%Y-%m')} "
            f"train={train_start.date()}..{month_start.date()}",
            flush=True,
        )

        calibration_model, cal_mean, cal_std, cal_train_info = _train_one_model(
            prepared=prepared,
            symbols=available_symbols,
            feature_cols=feature_cols,
            start=train_start,
            end=cal_start,
            seq_config=seq_config,
            model_config=model_config,
            device=device,
            progress_prefix=f"{month_start.strftime('%Y-%m')} calibration",
        )
        cal_returns: Dict[pd.Timestamp, Dict[str, float]] = {}
        cal_scores: Dict[pd.Timestamp, Dict[str, float]] = {}
        if calibration_model is not None:
            cal_returns, cal_scores, _ = _score_window(
                model=calibration_model,
                prepared=prepared,
                symbols=available_symbols,
                feature_cols=feature_cols,
                start=cal_start,
                end=month_start,
                seq_config=seq_config,
                mean=cal_mean,
                std=cal_std,
                device=device,
            )

        base_config = {
            "model_kind": "deep_transformer_policy",
            "threshold": float(args.base_threshold),
            "top_k": int(args.top_k),
            "trade_mode": str(args.trade_mode),
            "position_scale": 1.0,
        }
        cal_oracle = ca._portfolio_oracle_by_date(cal_returns, available_symbols) if cal_returns else {}
        calibration = ca._calibrate_portfolio_selector(
            returns_by_date=cal_returns,
            scores_by_date=cal_scores,
            base_config=base_config,
            oracle_by_date=cal_oracle,
        )

        model, mean, std, train_info = _train_one_model(
            prepared=prepared,
            symbols=available_symbols,
            feature_cols=feature_cols,
            start=train_start,
            end=month_start,
            seq_config=seq_config,
            model_config=model_config,
            device=device,
            progress_prefix=f"{month_start.strftime('%Y-%m')} production",
        )
        if model is None:
            month_reports.append(
                {
                    "month": month_start.strftime("%Y-%m"),
                    "skipped": True,
                    "train_info": train_info,
                    "calibration": calibration,
                }
            )
            partial_path.write_text(
                json.dumps(
                    {
                        "timestamp_utc": datetime.now(UTC).isoformat(),
                        "status": "partial",
                        "device": str(device),
                        "months": month_reports,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            continue

        month_returns, month_scores, scored_samples = _score_window(
            model=model,
            prepared=prepared,
            symbols=available_symbols,
            feature_cols=feature_cols,
            start=month_start,
            end=month_end,
            seq_config=seq_config,
            mean=mean,
            std=std,
            device=device,
        )
        for dt, rows in month_returns.items():
            returns_by_date.setdefault(dt, {}).update(rows)
            if dt in month_scores:
                scores_by_date.setdefault(dt, {}).update(month_scores[dt])
                configs_by_date[dt] = calibration

        checkpoint_path = checkpoint_dir / f"deep_policy_{month_start.strftime('%Y_%m')}.pt"
        save_checkpoint(
            checkpoint_path,
            model=model,
            config=model_config,
            metadata={
                "month": month_start.strftime("%Y-%m"),
                "symbols": available_symbols,
                "feature_cols": feature_cols,
                "normalizer_mean": mean.tolist(),
                "normalizer_std": std.tolist(),
                "calibration": calibration,
            },
        )
        checkpoint_paths.append(str(checkpoint_path))
        month_reports.append(
            {
                "month": month_start.strftime("%Y-%m"),
                "skipped": False,
                "train_info": train_info,
                "calibration_train_info": cal_train_info,
                "calibration": calibration,
                "scored_samples": scored_samples,
                "checkpoint_path": str(checkpoint_path),
            }
        )
        partial_path.write_text(
            json.dumps(
                {
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "status": "partial",
                    "device": str(device),
                    "months": month_reports,
                    "latest_checkpoint": str(checkpoint_path),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            f"[deep-policy] month {month_start.strftime('%Y-%m')} complete "
            f"cal_threshold={float(calibration.get('threshold', 0.0)):.6f} "
            f"mode={calibration.get('trade_mode')} top_k={calibration.get('top_k')} "
            f"checkpoint={checkpoint_path}",
            flush=True,
        )

    oracle_by_date = ca._portfolio_oracle_by_date(returns_by_date, available_symbols) if returns_by_date else {}
    result = ca._score_portfolio_series(
        returns_by_date=returns_by_date,
        scores_by_date=scores_by_date,
        config={"threshold": float(args.base_threshold), "top_k": int(args.top_k), "trade_mode": str(args.trade_mode)},
        oracle_by_date=oracle_by_date,
        configs_by_date=configs_by_date,
    )

    daily_rows = []
    if returns_by_date:
        prev_weights: Dict[str, float] = {}
        equity = float(args.initial_capital)
        buyhold_equity = float(args.initial_capital)
        for dt in sorted(returns_by_date):
            config = configs_by_date.get(dt, {})
            weights = ca._score_portfolio_candidates(
                scores=scores_by_date.get(dt, {}),
                threshold=float(config.get("threshold", args.base_threshold)),
                trade_mode=str(config.get("trade_mode", args.trade_mode)),
                top_k=int(config.get("top_k", args.top_k)),
                position_scale=float(config.get("position_scale", 1.0)),
            )
            symbols_for_day = sorted(set(returns_by_date[dt]) | set(weights) | set(prev_weights))
            turn = sum(abs(float(weights.get(symbol, 0.0)) - float(prev_weights.get(symbol, 0.0))) for symbol in symbols_for_day)
            model_ret = sum(float(weights.get(symbol, 0.0)) * float(returns_by_date[dt].get(symbol, 0.0)) for symbol in symbols_for_day)
            model_ret -= ca.TRADE_COST_RATE * turn
            active = [returns_by_date[dt][symbol] for symbol in returns_by_date[dt] if symbol in scores_by_date.get(dt, {})]
            buyhold_ret = float(np.mean(active)) if active else 0.0
            equity *= 1.0 + max(float(model_ret), -0.999999)
            buyhold_equity *= 1.0 + buyhold_ret
            daily_rows.append(
                {
                    "date": dt.strftime("%Y-%m-%d"),
                    "model_return": float(model_ret),
                    "buyhold_return": buyhold_ret,
                    "model_total_balance": equity,
                    "buyhold_total_balance": buyhold_equity,
                    "turnover": float(turn),
                    "active_exposure": float(sum(abs(v) for v in weights.values())),
                    "threshold": float(config.get("threshold", args.base_threshold)),
                    "top_k": int(config.get("top_k", args.top_k)),
                    "position_scale": float(config.get("position_scale", 1.0)),
                    "trade_mode": str(config.get("trade_mode", args.trade_mode)),
                }
            )
            prev_weights = weights

    daily_path = report_dir / "portfolio_daily.csv"
    pd.DataFrame(daily_rows).to_csv(daily_path, index=False)
    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "mode": "deep_transformer_policy_walkforward",
        "device": str(device),
        "symbols": available_symbols,
        "feature_cols": feature_cols,
        "sequence_config": seq_config.__dict__,
        "model_config": model_config.__dict__,
        "months": month_reports,
        "result": result,
        "daily_path": str(daily_path),
        "checkpoint_paths": checkpoint_paths,
        "report_dir": str(report_dir),
        "anti_cheat_note": (
            "Each month trains only on data before that month. Calibration uses a model trained before "
            "the calibration window, then applies the selected portfolio gate to the next month."
        ),
    }
    report_path = report_dir / "deep_policy_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deep transformer crypto policy walk-forward runner.")
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--symbols", type=str, default=",".join(TOP10_SYMBOLS))
    parser.add_argument("--window-size", type=int, default=96)
    parser.add_argument("--train-lookback-days", type=int, default=730)
    parser.add_argument("--calibration-lookback-days", type=int, default=365)
    parser.add_argument("--min-train-samples", type=int, default=512)
    parser.add_argument("--max-train-samples", type=int, default=3000)
    parser.add_argument("--month-stride", type=int, default=1)
    parser.add_argument("--max-months", type=int, default=6)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--pretrain-epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--d-model", type=int, default=64)
    parser.add_argument("--n-heads", type=int, default=4)
    parser.add_argument("--n-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.10)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--ranking-weight", type=float, default=0.65)
    parser.add_argument("--base-threshold", type=float, default=0.001)
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument("--trade-mode", type=str, default="long_short", choices=["long_short", "long_only", "flat"])
    parser.add_argument("--initial-capital", type=float, default=10.0)
    parser.add_argument("--cpu-only", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    output = run_deep_walkforward(parse_args())
    result = output["result"]
    model_ret = float(result["model_validation"].get("total_return", 0.0))
    buy_ret = float(result["buyhold_validation"].get("total_return", 0.0))
    print("\n=== Deep Crypto Policy Complete ===")
    print(f"Report: {output['report_path']}")
    print(f"Daily CSV: {output['daily_path']}")
    print(f"Total return: model={model_ret:.4f}, buyhold={buy_ret:.4f}, excess={model_ret - buy_ret:.4f}")
    print(
        "Risk: "
        f"sharpe={float(result['model_validation'].get('sharpe', 0.0)):.4f}, "
        f"drawdown={float(result['model_validation'].get('max_drawdown', 0.0)):.4f}, "
        f"turnover/day={float(result['model_validation'].get('avg_turnover_per_day', 0.0)):.4f}"
    )
