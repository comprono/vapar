from collections import defaultdict, deque
from datetime import datetime
from typing import Deque, Dict

import pandas as pd

from backend.strategies.base import Strategy
from backend.strategies.ensemble import EnsembleStrategy


class StrategyIntelligence:
    def __init__(self, strategy: Strategy | None = None, history_size: int = 300):
        self.strategy: Strategy = strategy or EnsembleStrategy()
        self.history_size = history_size
        self._prices: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=self.history_size))
        self._timestamps: Dict[str, Deque[datetime]] = defaultdict(lambda: deque(maxlen=self.history_size))
        self.min_bars = 60

    def set_strategy(self, strategy: Strategy):
        self.strategy = strategy
        # Keep price history and only switch strategy logic.
        print(f"[StrategyIntelligence] Active strategy set to: {strategy.name}")

    def get_strategy_name(self) -> str:
        return self.strategy.name

    async def analyze(self, market_snapshot: list):
        """
        Apply active strategy to rolling per-symbol history.
        Returns opportunities with confidence scores.
        """
        opportunities = []

        for item in market_snapshot:
            symbol = item.get("instrument_id") or item.get("symbol")
            price = item.get("price")
            if not symbol or price is None:
                continue

            timestamp = item.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            elif timestamp is None:
                timestamp = datetime.now()

            self._prices[symbol].append(float(price))
            self._timestamps[symbol].append(timestamp)

            if len(self._prices[symbol]) < self.min_bars:
                continue

            df = pd.DataFrame(
                {"Close": list(self._prices[symbol])},
                index=pd.to_datetime(list(self._timestamps[symbol])),
            )
            signal = self.strategy.analyze(df, symbol)
            if signal.action == "HOLD":
                continue

            expected_return = max(signal.confidence * 0.02, 0.001)
            opportunities.append(
                {
                    "symbol": symbol,
                    "direction": signal.action,
                    "confidence": round(float(signal.confidence), 4),
                    "expected_return": round(float(expected_return), 4),
                    "risk_score": round(float(max(0.0, 1.0 - signal.confidence)), 4),
                    "reason": signal.reason,
                    "strategy": self.strategy.name,
                }
            )

        return opportunities
