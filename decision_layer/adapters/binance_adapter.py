import asyncio
import random
from typing import Optional
from datetime import datetime
from decision_layer.adapters.base_adapter import BaseExchangeAdapter, OrderBook, OrderFill

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_SDK_AVAILABLE = True
except Exception:
    Client = None

    class BinanceAPIException(Exception):
        pass

    BINANCE_SDK_AVAILABLE = False

class BinanceAdapter(BaseExchangeAdapter):
    """
    Binance exchange adapter for paper trading.
    Uses real market data but simulates execution.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        # For read-only operations, keys are optional
        self.client = Client(api_key or "", api_secret or "") if BINANCE_SDK_AVAILABLE else None
        self.connected = False
        self.available = BINANCE_SDK_AVAILABLE
    
    async def connect(self):
        """Test connection to Binance API."""
        if not self.available:
            print("[BINANCE] python-binance not installed. Adapter running in disabled mode.")
            self.connected = False
            return
        try:
            # Test connectivity (async wrapper for sync client)
            status = await asyncio.to_thread(self.client.get_system_status)
            self.connected = True
            print(f"[BINANCE] Connected. Status: {status}")
        except BinanceAPIException as e:
            print(f"[BINANCE] Connection failed: {e}")
            self.connected = False
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Fetch latest ticker price (async-safe)."""
        if not self.available:
            return None
        try:
            ticker = await asyncio.to_thread(
                self.client.get_symbol_ticker,
                symbol=symbol.upper()
            )
            return float(ticker['price'])
        except Exception as e:
            print(f"[BINANCE] Failed to get price for {symbol}: {e}")
            return None
    
    async def get_order_book(self, symbol: str) -> Optional[OrderBook]:
        """Fetch current order book (best bid/ask) (async-safe)."""
        if not self.available:
            return None
        try:
            depth = await asyncio.to_thread(
                self.client.get_order_book,
                symbol=symbol.upper(),
                limit=5
            )
            
            best_bid = float(depth['bids'][0][0]) if depth['bids'] else 0
            best_ask = float(depth['asks'][0][0]) if depth['asks'] else 0
            bid_vol = float(depth['bids'][0][1]) if depth['bids'] else 0
            ask_vol = float(depth['asks'][0][1]) if depth['asks'] else 0
            
            return OrderBook(
                symbol=symbol,
                bid_price=best_bid,
                ask_price=best_ask,
                bid_volume=bid_vol,
                ask_volume=ask_vol,
                timestamp=datetime.now()
            )
        except Exception as e:
            print(f"[BINANCE] Failed to get order book for {symbol}: {e}")
            return None
    
    async def simulate_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float
    ) -> Optional[OrderFill]:
        """
        Simulate order execution with realistic slippage.
        Uses current bid/ask to model market order fill.
        """
        try:
            book = await self.get_order_book(symbol)
            if not book:
                return None
            
            # Market order simulation
            if side.lower() == 'buy':
                # Buy at ask + slippage
                base_price = book.ask_price
                slippage_pct = random.uniform(0.0001, 0.002)  # 0.01% to 0.2% slippage
                fill_price = base_price * (1 + slippage_pct)
            else:  # sell
                # Sell at bid - slippage
                base_price = book.bid_price
                slippage_pct = random.uniform(0.0001, 0.002)
                fill_price = base_price * (1 - slippage_pct)
            
            # Binance fee: 0.1% (simplified)
            fee = quantity * fill_price * 0.001
            
            return OrderFill(
                order_id=f"paper_{int(datetime.now().timestamp())}",
                symbol=symbol,
                side=side,
                quantity=quantity,
                fill_price=fill_price,
                timestamp=datetime.now(),
                fee=fee,
                slippage=(fill_price - base_price) / base_price
            )
        except Exception as e:
            print(f"[BINANCE] Simulation failed for {symbol}: {e}")
            return None
