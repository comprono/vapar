from pydantic import BaseModel, Field
from typing import List, Optional

class SystemConfig(BaseModel):
    capital_base: float = Field(..., description="Total capital available for trading (USD)")
    risk_tolerance_pct: float = Field(..., description="Maximum risk per trade as a decimal (0.01 = 1%)")
    min_confidence: float = Field(default=0.65, description="Minimum confidence threshold (0-1) for trade execution")
    active_markets: List[str] = Field(default=["BTC", "ETH", "SPY"], description="List of symbols to trade")
    
    class Config:
        json_schema_extra = {
            "example": {
                "capital_base": 10000.0,
                "risk_tolerance_pct": 0.02,
                "min_confidence": 0.70,
                "active_markets": ["BTC", "ETH"]
            }
        }
