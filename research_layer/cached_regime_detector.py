import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from research_layer.regime_detector import RegimeDetector, RegimeState

@dataclass
class CachedRegime:
    """Cached regime result with TTL."""
    regime: RegimeState
    timestamp: float
    price_snapshot: float

class CachedRegimeDetector:
    """
    Regime detector with caching to reduce CPU usage.
    Only recalculates if price changed significantly or TTL expired.
    """
    
    def __init__(self, ttl_seconds: float = 60.0, price_change_threshold: float = 0.02):
        self.detector = RegimeDetector()
        self.cache: Dict[str, CachedRegime] = {}
        self.ttl = ttl_seconds
        self.threshold = price_change_threshold
        self.cache_hits = 0
        self.cache_misses = 0
    
    def detect(self, symbol: str, prices: List[float]) -> RegimeState:
        """
        Detect regime with caching.
        
        Args:
            symbol: Asset symbol
            prices: Historical prices
        
        Returns:
            RegimeState (cached or fresh)
        """
        current_time = time.time()
        current_price = prices[-1] if prices else 0
        
        # Check cache
        if symbol in self.cache:
            cached = self.cache[symbol]
            age = current_time - cached.timestamp
            price_change = abs(current_price - cached.price_snapshot) / cached.price_snapshot if cached.price_snapshot > 0 else 1.0
            
            # Return cached if still valid
            if age < self.ttl and price_change < self.threshold:
                self.cache_hits += 1
                return cached.regime
        
        # Cache miss - recalculate
        self.cache_misses += 1
        regime = self.detector.detect(prices)
        
        # Update cache
        self.cache[symbol] = CachedRegime(
            regime=regime,
            timestamp=current_time,
            price_snapshot=current_price
        )
        
        return regime
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Clear cache for one symbol or all."""
        if symbol:
            self.cache.pop(symbol, None)
        else:
            self.cache.clear()
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total > 0 else 0
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_pct": hit_rate,
            "cached_symbols": len(self.cache)
        }
