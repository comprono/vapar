from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional

class MarketType(str, Enum):
    CRYPTO = "CRYPTO"
    EQUITY = "EQUITY"
    FOREX = "FOREX"
    SPORTS = "SPORTS"

class Instrument(BaseModel):
    id: str
    symbol: str
    exchange: str
    market_type: MarketType

class Quote(BaseModel):
    instrument_id: str
    price: float
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None
    market_type: MarketType
    volatility: Optional[float] = None

class Trade(BaseModel):
    id: str
    instrument_id: str
    side: str
    price: float
    size: float
    timestamp: datetime
