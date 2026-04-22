from abc import ABC, abstractmethod
from typing import List, Callable, Awaitable, Union
import asyncio
from common.schemas.market_data import Quote, OrderBook, MarketType

MarketEvent = Union[Quote, OrderBook]

class DataIngestor(ABC):
    """
    Abstract base class for all data ingestors (Crypto, Equities, Sports).
    Enforces Async/WebSocket-first architecture.
    """
    
    def __init__(self, market_type: MarketType, symbol_subscriptions: List[str]):
        self.market_type = market_type
        self.symbols = symbol_subscriptions
        self._callbacks: List[Callable[[MarketEvent], Awaitable[None]]] = []
        self.running = False

    def add_callback(self, callback: Callable[[MarketEvent], Awaitable[None]]):
        """Register a callback function to receive MarketData updates."""
        self._callbacks.append(callback)

    async def _emit(self, data: MarketEvent):
        """Distribute data to all registered callbacks."""
        tasks = [cb(data) for cb in self._callbacks]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @abstractmethod
    async def connect(self):
        """Establish connection (WebSocket or API session)."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Close connection gracefully."""
        pass

    @abstractmethod
    async def subscribe(self, symbols: List[str]):
        """Subscribe to specific tickers/streams."""
        pass

    async def start(self):
        """Main loop wrapper."""
        self.running = True
        await self.connect()
        await self.subscribe(self.symbols)

    async def stop(self):
        self.running = False
        await self.disconnect()
