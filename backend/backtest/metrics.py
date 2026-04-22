import numpy as np
import pandas as pd
from typing import List, Dict

class PerformanceMetrics:
    """Calculate professional trading performance metrics."""
    
    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """
        Calculate annualized Sharpe Ratio.
        
        Args:
            returns: Daily returns (as decimal, e.g., 0.01 for 1%)
            risk_free_rate: Annual risk-free rate (default 2%)
        
        Returns:
            Sharpe ratio (higher is better)
        """
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
        sharpe = np.sqrt(252) * (excess_returns.mean() / returns.std())
        return round(sharpe, 2)
    
    @staticmethod
    def max_drawdown(equity_curve: pd.Series) -> float:
        """
        Calculate maximum drawdown (peak-to-trough decline).
        
        Returns:
            Max drawdown as decimal (e.g., -0.15 for -15%)
        """
        if len(equity_curve) == 0:
            return 0.0
        
        cumulative = equity_curve
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        return round(max_dd, 4)
    
    @staticmethod
    def win_rate(trades: List[Dict]) -> float:
        """
        Calculate percentage of winning trades.
        
        Args:
            trades: List of trade dictionaries with 'pnl' field
        
        Returns:
            Win rate as decimal (e.g., 0.65 for 65%)
        """
        if len(trades) == 0:
            return 0.0
        
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        win_rate = len(winning_trades) / len(trades)
        return round(win_rate, 4)
    
    @staticmethod
    def profit_factor(trades: List[Dict]) -> float:
        """
        Calculate profit factor (gross profit / gross loss).
        
        Returns:
            Profit factor (>1 is profitable, higher is better)
        """
        if len(trades) == 0:
            return 0.0
        
        gross_profit = sum(t['pnl'] for t in trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t['pnl'] for t in trades if t.get('pnl', 0) < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        pf = gross_profit / gross_loss
        return round(pf, 2)
    
    @staticmethod
    def calculate_all(equity_curve: pd.Series, trades: List[Dict], initial_capital: float) -> Dict:
        """Calculate all metrics at once."""
        returns = equity_curve.pct_change().dropna()
        
        total_pnl = equity_curve.iloc[-1] - initial_capital if len(equity_curve) > 0 else 0
        total_return = (total_pnl / initial_capital) if initial_capital > 0 else 0
        
        return {
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_return * 100, 2),
            "sharpe_ratio": PerformanceMetrics.sharpe_ratio(returns),
            "max_drawdown_pct": round(PerformanceMetrics.max_drawdown(equity_curve) * 100, 2),
            "win_rate_pct": round(PerformanceMetrics.win_rate(trades) * 100, 2),
            "profit_factor": PerformanceMetrics.profit_factor(trades),
            "total_trades": len(trades),
            "winning_trades": len([t for t in trades if t.get('pnl', 0) > 0]),
            "losing_trades": len([t for t in trades if t.get('pnl', 0) < 0])
        }
