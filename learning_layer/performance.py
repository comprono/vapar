from typing import List, Dict, Any
from datetime import datetime

class TradeResult:
    def __init__(self, trade_id: str, pnl: float, accurate: bool):
        self.trade_id = trade_id
        self.pnl = pnl
        self.accurate = accurate

class PerformanceAnalytics:
    """
    Evaluates completed trades to determine model accuracy.
    """
    def __init__(self):
        self.history: List[TradeResult] = []

    def evaluate(self, trade_id: str, entry_price: float, exit_price: float, side: str, size: float) -> TradeResult:
        """
        Calculate PnL for a closed trade.
        """
        if side == 'buy':
            pnl = (exit_price - entry_price) * size
            accurate = pnl > 0
        else: # sell
            pnl = (entry_price - exit_price) * size
            accurate = pnl > 0
            
        result = TradeResult(trade_id, pnl, accurate)
        self.history.append(result)
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate stats."""
        if not self.history:
            return {"total_trades": 0, "win_rate": 0.0, "total_pnl": 0.0}
            
        wins = sum(1 for t in self.history if t.accurate)
        total_pnl = sum(t.pnl for t in self.history)
        
        return {
            "total_trades": len(self.history),
            "win_rate": round(wins / len(self.history), 2),
            "total_pnl": round(total_pnl, 2)
        }
