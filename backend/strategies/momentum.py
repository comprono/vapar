import pandas as pd
from backend.strategies.base import Strategy, Signal

class MomentumStrategy(Strategy):
    """
    Simple momentum strategy: Buy on uptrends, sell on downtrends.
    Uses moving average crossover logic with vectorized execution.
    """
    
    def __init__(self, short_window: int = 3, long_window: int = 12): 
        super().__init__(
            name="Momentum",
            params={
                "short_window": short_window,
                "long_window": long_window
            }
        )
        self.short_window = short_window
        self.long_window = long_window

    def analyze(self, data: pd.DataFrame, current_symbol: str) -> Signal:
        # Legacy wrapper
        if len(data) < self.long_window:
            return Signal(current_symbol, "HOLD", 0.0, "Insufficient data")
            
        short_ma = data['Close'].rolling(window=self.short_window).mean()
        long_ma = data['Close'].rolling(window=self.long_window).mean()
        
        s_ma = short_ma.iloc[-1]
        l_ma = long_ma.iloc[-1]
        
        # Golden Cross (Short > Long)
        if s_ma > l_ma:
            trend_strength = (s_ma - l_ma) / l_ma * 100 
            confidence = min(0.6 + trend_strength, 0.95)
            return Signal(current_symbol, "BUY", confidence, f"Golden Cross (Gap: {trend_strength:.2f}%)")
            
        # Death Cross (Short < Long)
        elif s_ma < l_ma:
            trend_strength = (l_ma - s_ma) / l_ma * 100
            confidence = min(0.6 + trend_strength, 0.95)
            return Signal(current_symbol, "SELL", confidence, f"Death Cross (Gap: {trend_strength:.2f}%)")
            
        return Signal(current_symbol, "HOLD", 0.0, "No clear trend")

    def generate_signals(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Vectorized Momentum Strategy."""
        # Calculate Indicators
        short_ma = data['Close'].rolling(window=self.short_window).mean()
        long_ma = data['Close'].rolling(window=self.long_window).mean()
        
        # Initialize DataFrame
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = "HOLD"
        signals['confidence'] = 0.0
        signals['reason'] = ""
        signals['symbol'] = symbol
        
        # Conditions
        buy_cond = short_ma > long_ma
        sell_cond = short_ma < long_ma
        
        # Vectorized Logic
        # Calculate Trend Strength for all rows
        trend_gap_buy = ((short_ma - long_ma) / long_ma * 100)
        trend_gap_sell = ((long_ma - short_ma) / long_ma * 100)
        
        # Apply BUY
        if buy_cond.any():
            signals.loc[buy_cond, 'signal'] = "BUY"
            signals.loc[buy_cond, 'confidence'] = (0.6 + trend_gap_buy[buy_cond]).clip(upper=0.95)
            signals.loc[buy_cond, 'reason'] = "Golden Cross (Gap: " + trend_gap_buy[buy_cond].round(2).astype(str) + "%)"
        
        # Apply SELL
        if sell_cond.any():
            signals.loc[sell_cond, 'signal'] = "SELL"
            signals.loc[sell_cond, 'confidence'] = (0.6 + trend_gap_sell[sell_cond]).clip(upper=0.95)
            signals.loc[sell_cond, 'reason'] = "Death Cross (Gap: " + trend_gap_sell[sell_cond].round(2).astype(str) + "%)"
        
        return signals
