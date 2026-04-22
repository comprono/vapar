import random
import asyncio
from datetime import datetime

class MarketPerception:
    def __init__(self):
        # Simulator state
        self.tickers = ["BTC/USD", "ETH/USD", "SPY", "TSLA"]
        self.current_prices = {
            "BTC/USD": 65000.0,
            "ETH/USD": 3500.0,
            "SPY": 500.0,
            "TSLA": 200.0
        }

    async def get_market_state(self):
        """
        Simulate fetching live market state.
        In production, this would connect to exchanges.
        """
        snapshot = []
        for symbol in self.tickers:
            # Simulate random walk
            change_pct = random.uniform(-0.005, 0.005)
            self.current_prices[symbol] *= (1 + change_pct)
            
            snapshot.append({
                "symbol": symbol,
                "price": round(self.current_prices[symbol], 2),
                "volatility": round(random.uniform(10, 50), 2), # Implied Vol
                "timestamp": datetime.now().isoformat()
            })
        return snapshot
