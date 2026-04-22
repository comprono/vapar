from typing import List, Dict
from pydantic import BaseModel, Field
from .models.base import Prediction

class AllocationDecision(BaseModel):
    instrument_id: str
    target_weight: float = Field(..., description="Target portfolio weight (0.0 to 1.0)")
    rationale: str

class PortfolioAllocator:
    """
    Meta-model that takes predictions from various models
    and constructs an optimal portfolio.
    """
    def __init__(self, risk_aversion: float = 1.0):
        self.risk_aversion = risk_aversion

    def allocate(self, predictions: List[Prediction]) -> List[AllocationDecision]:
        """
        Simple mean-variance style allocation (Mock version).
        
        Logic:
        1. Filter for positive expected returns.
        2. Verify confidence is above threshold.
        3. Weight by (Expected Return / Uncertainty).
        4. Normalize weights to sum to max 1.0 (or less if few opportunities).
        """
        decisions = []
        scores = {}
        total_score = 0.0
        
        # 1. Score opportunities
        for p in predictions:
            if p.expected_return <= 0:
                continue
                
            if p.confidence_score < 0.5:
                continue
            
            # Simple Sharpe-like score
            score = (p.expected_return / p.uncertainty) * p.confidence_score
            scores[p.instrument_id] = score
            total_score += score
            
        # 2. Allocate weights
        if total_score > 0:
            for instrument_id, score in scores.items():
                weight = score / total_score
                # Cap max weight per asset (e.g. 20%)
                weight = min(weight, 0.20) 
                
                decisions.append(AllocationDecision(
                    instrument_id=instrument_id,
                    target_weight=round(weight, 4),
                    rationale=f"Score: {score:.2f} (Ret/Risk)"
                ))
        
        return decisions
