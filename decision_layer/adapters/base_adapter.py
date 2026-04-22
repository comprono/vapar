from abc import ABC, abstractmethod
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class OrderBook:
    symbol: str
    bid_price: float
    ask_price: float
    bid_volume: float
    ask_volume: float
    timestamp: datetime

@dataclass
class OrderFill:
    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    fill_price: float
    timestamp: datetime
    fee: float = 0.0
    slippage: float = 0.0

class BaseExchangeAdapter(ABC):
    """
    Abstract base class for exchange connections.
    Implementations provide read-only market data and paper trading simulation.
    """
    
    @abstractmethod
    async def connect(self):
        """Establish connection to exchange API."""
        pass
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Fetch latest market price for a symbol."""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str) -> Optional[OrderBook]:
        """Fetch current bid/ask and depth."""
        pass
    
    @abstractmethod
    async def simulate_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float
    ) -> Optional[OrderFill]:
        """
        Simulate order execution using current market data.
        Returns fill with realistic slippage.
        """
        pass
