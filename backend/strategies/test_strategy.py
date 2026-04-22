from backend.strategies.base import Strategy, Signal

class AlwaysBuyStrategy(Strategy):
    """
    Test strategy that alternates between BUY and SELL every 10 bars.
    Used for debugging - will ALWAYS generate trades.
    """
    
    def __init__(self):
        super().__init__(name="AlwaysBuy", params={})
        self.bar_count = 0
    
    def analyze(self, bars, symbol: str) -> Signal:
        """Alternate between BUY and SELL signals."""
        self.bar_count += 1
        
        # Every 10 bars, generate a BUY signal
        if self.bar_count % 20 < 10:
            return Signal(symbol, "BUY", 0.80, "Test: Forced BUY")
        else:
            return Signal(symbol, "SELL", 0.80, "Test: Forced SELL")
