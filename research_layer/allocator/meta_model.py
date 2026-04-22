from typing import List, Dict
import random
from common.schemas.market_data import MarketType
from research_layer.models.base import Prediction
from research_layer.regime.hmm import RegimePrediction

class PortfolioAllocator:
    """
    Layer 2.5: The 'Meta-Model'.
    Aggregates signals from various models and regimes to propose target weights.
    Does NOT execute trades (Layer 3 does that).
    """
    
    def __init__(self):
        self.min_confidence = 0.0 # Lowered for testing purposes (Prod: 0.6)
        
    def allocate(self, predictions: List[Prediction], regime: RegimePrediction) -> Dict[str, float]:
        """
        Input: List of model predictions + Market Regime
        Output: Target portfolio weights { 'BTC/USDT': 0.1, 'ETH/USDT': 0.2, 'CASH': 0.7 }
        """
        targets = {}
        total_risk_budget = 0.0
        
        # 1. Regime-based Risk Adjustment
        # In 'High_Vol_Crisis', slash all position sizes
        regime_scalar = 1.0
        if "Crisis" in regime.regime_name or "Bear" in regime.regime_name:
            regime_scalar = 0.5
        elif "High_Vol" in regime.regime_name:
            regime_scalar = 0.7
            
        # 2. Optimization (Naive implementation for stub)
        # In prod, this would be Mean-Variance or Black-Litterman optimization
        valid_predictions = [p for p in predictions if p.confidence_score >= self.min_confidence]
        
        if not valid_predictions:
            return {"CASH": 1.0}
            
        count = len(valid_predictions)
        # Naive equal weight adjusted by confidence and regime
        base_weight = (0.9 / count) * regime_scalar # Reserve 10% cash minimum
        
        current_alloc = 0.0
        for p in valid_predictions:
            # Simple heuristic: Higher return + Lower uncertainty = Higher weight
            score = (p.expected_return / (p.uncertainty + 1e-6)) * p.confidence_score
            weight = base_weight * (1.0 + score) # Slight tilt
            weight = min(weight, 0.2) # Hard Cap stub
            
            targets[p.instrument_id] = weight
            current_alloc += weight
            
        targets["CASH"] = max(0.0, 1.0 - current_alloc)
        
        return targets
