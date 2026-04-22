from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class TradeIntent(BaseModel):
    """
    Formal request from the Research Layer to the Decision Layer.
    Must be fully specified to allow for independent risk validation.
    """
    id: str = Field(..., description="Unique ID for this intent")
    timestamp: datetime
    
    instrument_id: str
    strategy_id: str
    
    side: str = Field(..., description="'buy' or 'sell'")
    size: float = Field(..., description="Quantity to trade")
    
    # Justification fields (critical for auditing)
    expected_return: float
    confidence_score: float
    max_slippage: Optional[float] = None
    
    meta: Dict[str, Any] = Field(default_factory=dict)
