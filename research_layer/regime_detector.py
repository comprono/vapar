import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class RegimeState:
    regime: str  # BULL, BEAR, CRASH, HIGH_VOL, RANGING
    confidence: float
    features: Dict[str, float]

class RegimeDetector:
    """
    Market regime classifier using heuristic rules.
    Classifies current market state for regime-aware strategy selection.
    """
    
    def __init__(self):
        self.lookback_short = 50  # 50-day SMA
        self.lookback_long = 200  # 200-day SMA
        self.vol_window = 30
    
    def detect(self, prices: List[float]) -> RegimeState:
        """
        Detect current market regime from price history.
        
        Args:
            prices: List of recent prices (oldest to newest)
        
        Returns:
            RegimeState with classification and confidence
        """
        if len(prices) < self.lookback_long:
            return RegimeState(
                regime="UNKNOWN",
                confidence=0.0,
                features={}
            )
        
        prices_array = np.array(prices)
        
        # Calculate features
        sma_50 = np.mean(prices_array[-self.lookback_short:])
        sma_200 = np.mean(prices_array[-self.lookback_long:])
        current_price = prices_array[-1]
        
        # Volatility
        returns = np.diff(prices_array) / prices_array[:-1]
        recent_vol = np.std(returns[-self.vol_window:])
        long_vol = np.std(returns)
        vol_ratio = recent_vol / long_vol if long_vol > 0 else 1.0
        
        # Trend strength
        trend_strength = (sma_50 - sma_200) / sma_200 if sma_200 > 0 else 0
        
        # Price vs SMA
        price_vs_sma50 = (current_price - sma_50) / sma_50 if sma_50 > 0 else 0
        price_vs_sma200 = (current_price - sma_200) / sma_200 if sma_200 > 0 else 0
        
        # Recent drawdown
        recent_high = np.max(prices_array[-30:])
        drawdown = (current_price - recent_high) / recent_high if recent_high > 0 else 0
        
        features = {
            "sma_50": sma_50,
            "sma_200": sma_200,
            "current_price": current_price,
            "volatility_ratio": vol_ratio,
            "trend_strength": trend_strength,
            "price_vs_sma50": price_vs_sma50,
            "price_vs_sma200": price_vs_sma200,
            "drawdown": drawdown
        }
        
        # Regime classification logic
        regime, confidence = self._classify_regime(features)
        
        return RegimeState(
            regime=regime,
            confidence=confidence,
            features=features
        )
    
    def _classify_regime(self, features: Dict[str, float]) -> tuple:
        """Apply heuristic rules to classify regime."""
        trend = features["trend_strength"]
        vol_ratio = features["volatility_ratio"]
        drawdown = features["drawdown"]
        price_vs_sma50 = features["price_vs_sma50"]
        
        # CRASH: Severe drawdown + elevated volatility
        if drawdown < -0.15 and vol_ratio > 2.0:
            return "CRASH", 0.9
        
        # HIGH_VOL: Elevated volatility without clear trend
        if vol_ratio > 1.5 and abs(trend) < 0.05:
            return "HIGH_VOL", 0.8
        
        # BULL: Strong uptrend + price above MAs
        if trend > 0.10 and price_vs_sma50 > 0:
            confidence = min(0.95, 0.6 + abs(trend) * 2)
            return "BULL", confidence
        
        # BEAR: Strong downtrend + price below MAs
        if trend < -0.10 and price_vs_sma50 < 0:
            confidence = min(0.95, 0.6 + abs(trend) * 2)
            return "BEAR", confidence
        
        # RANGING: Low volatility, no clear trend
        if vol_ratio < 0.8 and abs(trend) < 0.05:
            return "RANGING", 0.7
        
        # Default: Weak trend, normal vol
        if trend > 0:
            return "BULL", 0.5
        else:
            return "BEAR", 0.5
    
    def get_regime_strategy_hint(self, regime: str) -> str:
        """
        Get strategy recommendation based on regime.
        """
        strategies = {
            "BULL": "momentum_long",
            "BEAR": "defensive_short",
            "CRASH": "risk_off",
            "HIGH_VOL": "volatility_trading",
            "RANGING": "mean_reversion"
        }
        return strategies.get(regime, "neutral")
