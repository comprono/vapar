from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from datetime import datetime
import uuid
from common.schemas.market_data import MarketType

# TradeDirection and TradeStatus are specific to execution/intent, so they stay here.
class TradeDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"  # Close position

class TradeStatus(Enum):
    CREATED = "CREATED"
    PENDING_RISK = "PENDING_RISK"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

@dataclass
class TradeIntent:
    """
    The core signal object passed from Strategy (Layer 2) to Decision Engine (Layer 3).
    """
    strategy_id: str
    symbol: str
    market_type: MarketType
    direction: TradeDirection
    size: Decimal  # Could be quantity or notional value depending on convention
    price_limit: Optional[Decimal]
    
    # Justification
    rationale: str
    confidence: float # 0.0 to 1.0
    expected_return: float
    time_horizon: str # e.g., "1h", "1d"
    
    # Metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    status: TradeStatus = TradeStatus.CREATED
    risk_check_log: List[str] = field(default_factory=list)
