import asyncio
import random
from datetime import datetime
from typing import List
from common.schemas.market_data import MarketType, OrderBook, Quote
from .ingestor import DataIngestor

class MockIngestor(DataIngestor):
    """
    Simulates a high-frequency WebSocket stream for testing.
    Generates realistic-looking L2 updates and trades.
    """

    def __init__(self, market_type: MarketType = MarketType.CRYPTO, symbols: List[str] = None, interval_sec: float = 0.1):
        super().__init__(market_type, symbols or ["BTC/USDT", "ETH/USDT"])
        self._delay = interval_sec
        self._prices = {s: 50000.0 if "BTC" in s else 3000.0 for s in self.symbols}

    async def connect(self):
        """
        Simulate persistent connection and streamed updates.
        Yields events for async iteration.
        """
        self.running = True
        print(f"[MOCK] Connected. Stream interval: {self._delay}s")
        
    async def disconnect(self):
        self.running = False
        print("[MOCK] Disconnected.")

    async def subscribe(self, symbols: List[str]):
        print(f"[MOCK] Subscribed to {symbols}")
        self.symbols = symbols

    async def connect(self):
        """
        Simulate persistent connection and streamed updates.
        Yields events for async iteration.
        """
        self.running = True
        
        while self.running:
            await asyncio.sleep(self._delay)
            
            for symbol in self.symbols:
                # 1. Simulate Price Movement (Random Walk)
                change_pct = random.uniform(-0.0005, 0.0005) # +/- 0.05%
                self._prices[symbol] *= (1.0 + change_pct)
                current_price = self._prices[symbol]

                # 2. Generate L2 Order Book (Synthetic)
                book = self._generate_order_book(symbol, current_price)

                # 3. Yield to system
                yield book

    def _generate_order_book(self, symbol: str, mid_price: float) -> OrderBook:
        """Constructs a synthetic L2 book around the mid price."""
        spread_bps = 0.0005 # 5 bps spread
        half_spread = mid_price * spread_bps / 2
        
        best_bid = mid_price - half_spread
        best_ask = mid_price + half_spread
        
        # Generate 5 levels deep
        bids = []
        asks = []
        
        for i in range(5):
            # Bids decrease
            bid_p = best_bid * (1.0 - (i * 0.0002))
            bids.append([bid_p, random.uniform(0.1, 2.0)])
            
            # Asks increase
            ask_p = best_ask * (1.0 + (i * 0.0002))
            asks.append([ask_p, random.uniform(0.1, 2.0)])

        return OrderBook(
            symbol=symbol, # Note: Schema uses 'instrument_id', but let's assume mapping for now or fix schema usage
            instrument_id=symbol,
            timestamp=datetime.now(),
            bids=bids,
            asks=asks,
            source="MOCK"
        )
