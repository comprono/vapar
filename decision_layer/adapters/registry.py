from typing import Dict, Optional
from decision_layer.adapters.base_adapter import BaseExchangeAdapter
from decision_layer.adapters.binance_adapter import BinanceAdapter

class AdapterRegistry:
    """
    Registry for routing trades to appropriate exchange adapters.
    Determines which adapter to use based on instrument symbol.
    """
    
    def __init__(self):
        self.adapters: Dict[str, BaseExchangeAdapter] = {}
        self.default_adapter: Optional[BaseExchangeAdapter] = None
    
    def register(self, name: str, adapter: BaseExchangeAdapter, is_default: bool = False):
        """Register an adapter."""
        self.adapters[name] = adapter
        if is_default:
            self.default_adapter = adapter
        print(f"[REGISTRY] Registered adapter: {name}")
    
    def get_adapter(self, symbol: str) -> Optional[BaseExchangeAdapter]:
        """
        Select adapter based on symbol pattern.
        
        Routing logic:
        - NBA_*, NFL_*, etc. → SportsAdapter
        - BTC, ETH, DOGE → CryptoAdapter (Binance)
        - SPY, AAPL, TSLA → StockAdapter (IBKR/Alpaca)
        - Default → First registered or Binance
        """
        symbol_upper = symbol.upper()
        
        # Sports markets
        if any(symbol_upper.startswith(prefix) for prefix in ["NBA_", "NFL_", "MLB_", "SOCCER_"]):
            return self.adapters.get("sports")
        
        # Crypto markets
        if symbol_upper in ["BTC", "ETH", "DOGE", "SOL", "ADA"]:
            return self.adapters.get("crypto")
        
        # Stock markets (default)
        if "stocks" in self.adapters:
            return self.adapters["stocks"]
        
        # Fallback
        return self.default_adapter or self.adapters.get("crypto")
    
    def get_all_adapters(self) -> Dict[str, BaseExchangeAdapter]:
        """Get all registered adapters."""
        return self.adapters.copy()
