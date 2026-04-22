from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import sqrt
from typing import Dict, List, Optional

import pandas as pd

from backend.backtest.data_loader import DataLoader
from backend.strategies.base import Strategy
from backend.strategies.ensemble import EnsembleStrategy
from backend.strategies.mean_reversion import MeanReversionStrategy
from backend.strategies.momentum import MomentumStrategy
from backend.strategies.trend_follower import TrendFollowerStrategy


@dataclass
class CandidateResult:
    name: str
    strategy: Strategy
    score: float
    total_return: float
    sharpe: float
    max_drawdown: float
    trades: int
    symbols_used: int


class KarpathyAutoResearch:
    """
    Lightweight "auto-research loop" for live strategy selection.
    Picks the strategy with the best risk-adjusted score on recent history.
    """

    def __init__(self, lookback_days: int = 180, min_bars: int = 80, commission_bps: float = 8.0):
        self.lookback_days = lookback_days
        self.min_bars = min_bars
        self.commission_rate = commission_bps / 10000.0
        self.loader = DataLoader()
        self.selected_strategy: Strategy = EnsembleStrategy()
        self.last_report: Dict = {
            "status": "idle",
            "selected_strategy": self.selected_strategy.name,
            "message": "Research not run yet.",
        }

    def get_selected_strategy(self) -> Strategy:
        return self.selected_strategy

    def get_report(self) -> Dict:
        return self.last_report

    def run(self, symbols: List[str]) -> Dict:
        start_date = (date.today() - timedelta(days=self.lookback_days)).isoformat()
        end_date = date.today().isoformat()

        historical_data: Dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            yahoo_symbol = self._to_yahoo_symbol(symbol)
            try:
                df = self.loader.load(yahoo_symbol, start_date, end_date, interval="1d")
                if "Close" in df.columns:
                    close_df = df[["Close"]].copy().dropna()
                else:
                    continue
                if len(close_df) >= self.min_bars:
                    historical_data[symbol] = close_df
            except Exception:
                continue

        if not historical_data:
            self.last_report = {
                "status": "warning",
                "selected_strategy": self.selected_strategy.name,
                "message": "No usable historical data found. Keeping previous strategy.",
                "evaluated_symbols": 0,
            }
            return self.last_report

        candidates: List[CandidateResult] = []
        for name, strategy in self._candidate_strategies():
            combined_returns = []
            total_trades = 0
            symbols_used = 0

            for symbol, df in historical_data.items():
                sim = self._simulate(strategy, df, symbol, min_confidence=0.60)
                if sim is None:
                    continue
                combined_returns.append(sim["returns"])
                total_trades += sim["trades"]
                symbols_used += 1

            if not combined_returns:
                continue

            portfolio_returns = pd.concat(combined_returns, axis=1).mean(axis=1).fillna(0.0)
            metrics = self._compute_metrics(portfolio_returns)
            score = (
                metrics["total_return"]
                + (0.30 * metrics["sharpe"])
                - (1.20 * metrics["max_drawdown"])
                + min(total_trades / 120.0, 0.25)
            )
            if total_trades < 4:
                score -= 0.1

            candidates.append(
                CandidateResult(
                    name=name,
                    strategy=strategy,
                    score=float(score),
                    total_return=float(metrics["total_return"]),
                    sharpe=float(metrics["sharpe"]),
                    max_drawdown=float(metrics["max_drawdown"]),
                    trades=total_trades,
                    symbols_used=symbols_used,
                )
            )

        if not candidates:
            self.last_report = {
                "status": "warning",
                "selected_strategy": self.selected_strategy.name,
                "message": "Research ran but no candidate generated valid results.",
                "evaluated_symbols": len(historical_data),
            }
            return self.last_report

        candidates.sort(key=lambda x: x.score, reverse=True)
        winner = candidates[0]
        self.selected_strategy = winner.strategy

        candidate_rows = [
            {
                "name": c.name,
                "score": round(c.score, 4),
                "total_return": round(c.total_return, 4),
                "sharpe": round(c.sharpe, 4),
                "max_drawdown": round(c.max_drawdown, 4),
                "trades": c.trades,
                "symbols_used": c.symbols_used,
            }
            for c in candidates
        ]

        self.last_report = {
            "status": "ok",
            "selected_strategy": winner.strategy.name,
            "selected_candidate": winner.name,
            "evaluated_symbols": len(historical_data),
            "lookback_days": self.lookback_days,
            "top_candidates": candidate_rows[:5],
        }
        return self.last_report

    def _candidate_strategies(self) -> List[tuple[str, Strategy]]:
        return [
            ("Ensemble_Default", EnsembleStrategy()),
            ("Momentum_5_20", MomentumStrategy(short_window=5, long_window=20)),
            ("Momentum_3_12", MomentumStrategy(short_window=3, long_window=12)),
            ("MeanReversion_14", MeanReversionStrategy(rsi_period=14, oversold=35, overbought=65)),
            ("TrendFollower_20_2", TrendFollowerStrategy(window=20, num_std=2)),
        ]

    def _simulate(
        self,
        strategy: Strategy,
        df: pd.DataFrame,
        symbol: str,
        min_confidence: float,
    ) -> Optional[Dict]:
        try:
            signals = strategy.generate_signals(df.copy(), symbol)
        except Exception:
            return None

        returns = df["Close"].pct_change().fillna(0.0)
        if returns.empty:
            return None

        position = 0
        trades = 0
        strategy_returns: List[float] = []

        for idx in returns.index:
            bar_return = position * float(returns.loc[idx])

            signal = "HOLD"
            confidence = 0.0
            if idx in signals.index:
                signal = str(signals.at[idx, "signal"])
                try:
                    confidence = float(signals.at[idx, "confidence"])
                except Exception:
                    confidence = 0.0

            target_position = position
            if signal == "BUY" and confidence >= min_confidence:
                target_position = 1
            elif signal == "SELL" and confidence >= min_confidence:
                target_position = 0

            turnover = abs(target_position - position)
            if turnover > 0:
                trades += 1
            cost = turnover * self.commission_rate

            strategy_returns.append(bar_return - cost)
            position = target_position

        return {"returns": pd.Series(strategy_returns, index=returns.index), "trades": trades}

    def _compute_metrics(self, returns: pd.Series) -> Dict[str, float]:
        if returns.empty:
            return {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 1.0}

        equity = (1.0 + returns).cumprod()
        total_return = float(equity.iloc[-1] - 1.0)
        running_peak = equity.cummax()
        drawdown = (equity / running_peak) - 1.0
        max_drawdown = float(abs(drawdown.min()))

        vol = float(returns.std())
        sharpe = 0.0
        if vol > 1e-12:
            sharpe = float((returns.mean() / vol) * sqrt(252))

        return {
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
        }

    def _to_yahoo_symbol(self, symbol: str) -> str:
        upper = symbol.upper()
        crypto_roots = {"BTC", "ETH", "SOL", "XRP", "DOGE", "BNB"}
        if "/" in upper:
            return upper.replace("/", "-")
        if upper in crypto_roots:
            return f"{upper}-USD"
        return upper
