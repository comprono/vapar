from abc import ABC, abstractmethod
from typing import List, AsyncGenerator
from common.schemas.market_data import Instrument, Quote, Trade

class BaseIngestor(ABC):
    """
    Abstract base class for all data ingestors.
    Enforces normalization at the source.
    """
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def connect(self):
        """Establish connection to the data source."""
        pass
        
    @abstractmethod
    async def subscribe(self, instruments: List[Instrument]):
        """Subscribe to real-time updates for the given instruments."""
        pass
        
    @abstractmethod
    async def stream_quotes(self) -> AsyncGenerator[Quote, None]:
        """Yield normalized quotes."""
        pass

    @abstractmethod
    async def stream_trades(self) -> AsyncGenerator[Trade, None]:
        """Yield normalized confirmed trades."""
        pass
