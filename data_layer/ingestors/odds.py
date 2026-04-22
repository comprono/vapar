import asyncio
import os
from typing import List, Optional, AsyncGenerator
from datetime import datetime
import aiohttp
from data_layer.ingestors.base import BaseIngestor
from common.schemas.odds import OddsData

class OddsIngestor(BaseIngestor):
    """
    The Odds API ingestor for live sports betting data.
    Free tier: 500 requests/month
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ODDS_API_KEY", "")
        self.base_url = "https://api.the-odds-api.com/v4"
        self.sports = []
        self.running = False
        self.session = None
        
        if not self.api_key:
            print("[ODDS] WARNING: No API key set. Using demo mode.")
    
    async def connect(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession()
        print("[ODDS] Connected to The Odds API")
    
    def subscribe(self, sports: List[str]):
        """
        Set sports to track.
        
        Args:
            sports: List of sport keys (e.g., ['basketball_nba', 'americanfootball_nfl'])
        """
        self.sports = sports
        print(f"[ODDS] Subscribed to: {', '.join(sports)}")
    
    async def stream_odds(self) -> AsyncGenerator[OddsData, None]:
        """
        Stream live odds (polling-based).
        Polls every 30 seconds to respect rate limits.
        """
        if not self.session:
            await self.connect()
        
        self.running = True
        
        while self.running:
            for sport in self.sports:
                try:
                    odds_list = await self._fetch_odds(sport)
                    for odds in odds_list:
                        yield odds
                except Exception as e:
                    print(f"[ODDS] Error fetching {sport}: {e}")
            
            # Wait before next poll (30s to avoid rate limits)
            await asyncio.sleep(30)
    
    async def _fetch_odds(self, sport: str) -> List[OddsData]:
        """Fetch odds for a specific sport."""
        if not self.api_key:
            # Demo mode - return mock data
            return self._generate_demo_odds(sport)
        
        url = f"{self.base_url}/sports/{sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h",  # Head-to-head (moneyline)
            "oddsFormat": "american"
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_api_response(data, sport)
                else:
                    print(f"[ODDS] API error {response.status}: {await response.text()}")
                    return []
        except Exception as e:
            print(f"[ODDS] Request failed: {e}")
            return []
    
    def _parse_api_response(self, data: List[dict], sport: str) -> List[OddsData]:
        """Parse The Odds API response."""
        odds_list = []
        
        for event in data:
            try:
                for bookmaker in event.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        if market["key"] == "h2h":
                            outcomes = market["outcomes"]
                            
                            # Extract odds
                            home_odds = next((o["price"] for o in outcomes if o["name"] == event["home_team"]), 0)
                            away_odds = next((o["price"] for o in outcomes if o["name"] == event["away_team"]), 0)
                            
                            odds_data = OddsData(
                                event_id=event["id"],
                                sport=sport,
                                home_team=event["home_team"],
                                away_team=event["away_team"],
                                commence_time=datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00")),
                                bookmaker=bookmaker["key"],
                                market_type="h2h",
                                home_odds=home_odds,
                                away_odds=away_odds
                            )
                            odds_list.append(odds_data)
            except Exception as e:
                print(f"[ODDS] Parse error: {e}")
                continue
        
        return odds_list
    
    def _generate_demo_odds(self, sport: str) -> List[OddsData]:
        """Generate mock odds for demo purposes."""
        import random
        
        teams_by_sport = {
            "basketball_nba": [("Lakers", "Celtics"), ("Warriors", "Nets")],
            "americanfootball_nfl": [("Chiefs", "Bills"), ("49ers", "Cowboys")],
            "soccer_epl": [("Arsenal", "Chelsea"), ("Liverpool", "ManCity")]
        }
        
        teams = teams_by_sport.get(sport, [("TeamA", "TeamB")])
        odds_list = []
        
        for home, away in teams:
            odds_list.append(OddsData(
                event_id=f"demo_{sport}_{home}_vs_{away}",
                sport=sport,
                home_team=home,
                away_team=away,
                commence_time=datetime.now(),
                bookmaker="DRAFTKINGS",
                market_type="h2h",
                home_odds=random.choice([-150, -120, +110, +150]),
                away_odds=random.choice([-140, -110, +120, +160])
            ))
        
        return odds_list
    
    async def disconnect(self):
        """Close HTTP session."""
        self.running = False
        if self.session:
            await self.session.close()
        print("[ODDS] Disconnected")
