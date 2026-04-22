import pandas as pd
import numpy as np
from backend.strategies.base import Strategy, Signal

class TrendFollowerStrategy(Strategy):
    """
    Trend following strategy using Bollinger Bands.
    Buy when price breakouts above upper band, Sell when price breakdowns below lower band.
    """
    
    def __init__(self, window: int = 20, num_std: int = 2):
        super().__init__(
            name="TrendFollower",
            params={
                "window": window,
                "num_std": num_std
            }
        )
        self.window = window
        self.num_std = num_std

    def analyze(self, data: pd.DataFrame, current_symbol: str) -> Signal:
        # Legacy wrapper
        if len(data) < self.window:
            return Signal(current_symbol, "HOLD", 0.0, "Insufficient data")
            
        mas = data['Close'].rolling(window=self.window).mean()
        stds = data['Close'].rolling(window=self.window).std()
        
        upper_band = mas + (stds * self.num_std)
        lower_band = mas - (stds * self.num_std)
        
        price = data['Close'].iloc[-1]
        ub = upper_band.iloc[-1]
        lb = lower_band.iloc[-1]
        
        if price > ub:
            confidence = min(0.7 + (price - ub)/ub * 20, 0.95)
            return Signal(current_symbol, "BUY", confidence, f"Price Breakout > Upper Band ({ub:.2f})")
        elif price < lb:
            confidence = min(0.7 + (lb - price)/lb * 20, 0.95) 
            return Signal(current_symbol, "SELL", confidence, f"Price Breakdown < Lower Band ({lb:.2f})")
            
        return Signal(current_symbol, "HOLD", 0.0, "Inside Bands")

    def generate_signals(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Vectorized Trend Follower (Bollinger Bands)."""
        # Calculate Indicators
        mas = data['Close'].rolling(window=self.window).mean()
        stds = data['Close'].rolling(window=self.window).std()
        
        upper_band = mas + (stds * self.num_std)
        lower_band = mas - (stds * self.num_std)
        prices = data['Close']
        
        # Initialize DataFrame
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = "HOLD"
        signals['confidence'] = 0.0
        signals['reason'] = ""
        signals['symbol'] = symbol
        
        # Conditions
        buy_cond = prices > upper_band
        sell_cond = prices < lower_band
        
        # Vectorized Logic
        # Confidence scales with distance from band
        conf_buy = 0.7 + ((prices - upper_band) / upper_band * 20)
        conf_sell = 0.7 + ((lower_band - prices) / lower_band * 20)
        
        # Apply BUY
        if buy_cond.any():
            signals.loc[buy_cond, 'signal'] = "BUY"
            signals.loc[buy_cond, 'confidence'] = conf_buy[buy_cond].clip(upper=0.95)
            signals.loc[buy_cond, 'reason'] = "Price Breakout > Upper Band (" + upper_band[buy_cond].round(2).astype(str) + ")"
        
        # Apply SELL
        if sell_cond.any():
            signals.loc[sell_cond, 'signal'] = "SELL"
            signals.loc[sell_cond, 'confidence'] = conf_sell[sell_cond].clip(upper=0.95)
            signals.loc[sell_cond, 'reason'] = "Price Breakdown < Lower Band (" + lower_band[sell_cond].round(2).astype(str) + ")"
        
        return signals
