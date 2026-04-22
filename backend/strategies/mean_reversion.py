import pandas as pd
import numpy as np
from backend.strategies.base import Strategy, Signal

class MeanReversionStrategy(Strategy):
    """
    Mean reversion strategy using RSI.
    Buy when oversold (RSI < 40), sell when overbought (RSI > 60).
    """
    
    def __init__(self, rsi_period: int = 14, oversold: int = 40, overbought: int = 60):
        super().__init__(
            name="MeanReversion",
            params={
                "rsi_period": rsi_period,
                "oversold": oversold,
                "overbought": overbought
            }
        )
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
    
    def analyze(self, data: pd.DataFrame, current_symbol: str) -> Signal:
        # Backward compatibility wrapper
        rsi = self.calculate_rsi(data['Close'], self.rsi_period)
        if rsi.empty or pd.isna(rsi.iloc[-1]):
            return Signal(current_symbol, "HOLD", 0.0, "Insufficient data")
            
        current_rsi = rsi.iloc[-1]
        
        if current_rsi < self.oversold:
            confidence = min(0.6 + (self.oversold - current_rsi) / 100, 0.95)
            return Signal(current_symbol, "BUY", confidence, f"RSI Oversold ({current_rsi:.1f})")
        elif current_rsi > self.overbought:
            confidence = min(0.6 + (current_rsi - self.overbought) / 100, 0.95)
            return Signal(current_symbol, "SELL", confidence, f"RSI Overbought ({current_rsi:.1f})")
            
        return Signal(current_symbol, "HOLD", 0.0, f"RSI Neutral ({current_rsi:.1f})")

    def generate_signals(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Vectorized execution for 100x speedup."""
        # Calculate RSI for entire series at once
        rsi = self.calculate_rsi(data['Close'], self.rsi_period)
        
        # Initialize results frame
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = "HOLD"
        signals['confidence'] = 0.0
        signals['reason'] = ""
        signals['symbol'] = symbol
        
        # Vectorized conditions
        buy_cond = rsi < self.oversold
        sell_cond = rsi > self.overbought
        
        # Apply Signals
        # logic: 0.6 + distance / 100
        signals.loc[buy_cond, 'signal'] = "BUY"
        # Avoid SettingWithCopy by assigning directly or using proper index
        if buy_cond.any():
            signals.loc[buy_cond, 'confidence'] = (0.6 + (self.oversold - rsi[buy_cond]) / 100).clip(upper=0.95)
            signals.loc[buy_cond, 'reason'] = "RSI Oversold (" + rsi[buy_cond].round(1).astype(str) + ")"
        
        if sell_cond.any():
            signals.loc[sell_cond, 'signal'] = "SELL"
            signals.loc[sell_cond, 'confidence'] = (0.6 + (rsi[sell_cond] - self.overbought) / 100).clip(upper=0.95)
            signals.loc[sell_cond, 'reason'] = "RSI Overbought (" + rsi[sell_cond].round(1).astype(str) + ")"

        # Handle neutral signals
        neutral_cond = ~(buy_cond | sell_cond)
        if neutral_cond.any():
            signals.loc[neutral_cond, 'reason'] = "RSI Neutral (" + rsi[neutral_cond].round(1).astype(str) + ")"
        
        return signals

    def calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
