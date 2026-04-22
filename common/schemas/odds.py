from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class OddsData:
    """Sports betting odds data."""
    event_id: str
    sport: str
    home_team: str
    away_team: str
    commence_time: datetime
    bookmaker: str
    market_type: str  # h2h, spreads, totals
    home_odds: float
    away_odds: float
    draw_odds: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_quote_schema(self, team: str):
        """
        Convert odds to normalized Quote schema.
        
        For sports, "price" = implied probability
        """
        from common.schemas.market_data import Quote
        
        # Determine which odds to use
        if team == "home":
            odds = self.home_odds
            symbol = f"{self.sport}_{self.home_team}_WIN"
        elif team == "away":
            odds = self.away_odds
            symbol = f"{self.sport}_{self.away_team}_WIN"
        else:  # draw
            odds = self.draw_odds or 0
            symbol = f"{self.sport}_DRAW"
        
        # Convert American/Decimal odds to implied probability
        implied_prob = self._odds_to_probability(odds)
        
        return Quote(
            timestamp=self.timestamp,
            instrument_id=symbol,
            price=implied_prob,  # Use probability as "price"
            exchange=self.bookmaker
        )
    
    @staticmethod
    def _odds_to_probability(odds: float) -> float:
        """
        Convert odds to implied probability.
        Supports American odds (positive/negative) and Decimal odds.
        """
        if odds > 0 and odds < 100:  # Decimal odds (e.g., 2.5)
            return 1 / odds
        elif odds > 0:  # American positive (e.g., +150)
            return 100 / (odds + 100)
        else:  # American negative (e.g., -150)
            return abs(odds) / (abs(odds) + 100)
