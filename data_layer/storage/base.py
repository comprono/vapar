from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from common.schemas.market_data import Quote, Trade

class BaseStorage(ABC):
    """
    Abstract base class for all storage implementations.
    Ensures consistent interface across SQLite, TimescaleDB, etc.
    """
    
    @abstractmethod
    async def connect(self):
        """Establish connection to storage backend."""
        pass
    
    @abstractmethod
    async def save_quote(self, quote: Quote):
        """Save a single market quote."""
        pass
    
    @abstractmethod
    async def save_quotes_batch(self, quotes: List[Quote]):
        """Save multiple quotes in batch (for performance)."""
        pass
    
    @abstractmethod
    async def save_trade(self, trade: Trade):
        """Save an executed trade."""
        pass
    
    @abstractmethod
    def query_quotes(
        self, 
        instrument_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict]:
        """Query historical quotes for analysis."""
        pass
    
    @abstractmethod
    def save_audit_event(
        self, 
        event_type: str, 
        data: Dict[str, Any], 
        actor: str = "system",
        model_version: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Write to immutable audit log."""
        pass
    
    @abstractmethod
    def close(self):
        """Close connections and cleanup resources."""
        pass
