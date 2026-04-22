from enum import Enum
from typing import Optional, Dict, List, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class MarketType(str, Enum):
    EQUITY = "equity"
    CRYPTO = "crypto"
    SPORTS = "sports"

class Instrument(BaseModel):
    """
    Universal instrument definition.
    - Equity: 'AAPL' (symbol), 'NASDAQ' (exchange)
    - Crypto: 'BTC-USDT' (symbol), 'BINANCE' (exchange)
    - Sports: 'Kansas City Chiefs vs 49ers' (symbol/event), 'DRAFTKINGS' (exchange/book)
    """
    id: str = Field(..., description="Unique internal ID (e.g. eq:aapl:nasdaq)")
    symbol: str
    exchange: str
    market_type: MarketType
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Market-specific details (contract size, team IDs, etc)")

    model_config = ConfigDict(from_attributes=True)

class Quote(BaseModel):
    """
    Normalized market state.
    For financial markets: bid/ask/last
    For sports markets: home_odds/away_odds/draw_odds (mapped to generic fields where possible or in metadata)
    """
    timestamp: datetime
    instrument_id: str
    
    # Primary price (Last trade price for finance, or main line generic probability/odds for sports)
    price: float = Field(..., description="Current price or primary odds (decimal)")
    
    # Liquidity / Depth
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    
    # Sports specifics (can be partially mapped to bid/ask if it fits representing 'back'/'lay')
    # but often easier to keep separate or put in metadata for complex multi-outcome events
    probability: Optional[float] = Field(None, description="Implied probability if derived")
    
    source: str = Field(..., description="Source of this quote (API name)")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Trade(BaseModel):
    """
    Publicly executed trade (tick).
    """
    id: str = Field(..., description="Unique trade ID from exchange")
    timestamp: datetime
    instrument_id: str
    price: float
    size: float
    side: Optional[str] = None # 'buy', 'sell', 'unknown'
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OrderBook(BaseModel):
    """
    Snapshot of order book level 2 data.
    """
    timestamp: datetime
    instrument_id: str
    bids: List[List[float]] # [[price, size], ...]
    asks: List[List[float]] # [[price, size], ...]
    source: str
