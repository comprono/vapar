from typing import List
from .performance import PerformanceAnalytics
from .registry import ModelRegistry

class OptimizationLoop:
    """
    Closes the loop between Execution (PnL) and Research (Model Registry).
    """
    def __init__(self, analytics: PerformanceAnalytics, registry: ModelRegistry):
        self.analytics = analytics
        self.registry = registry

    def process_feedback(self, trade_id: str, model_name: str, pnl: float):
        """
        Feedback mechanism:
        Positive PnL -> Boost Model Score
        Negative PnL -> Penalize Model Score
        """
        # 1. Update Stats (Simplified, using passed PnL directly for loop validation)
        # In real system, analytics.evaluate would compute PnL first.
        
        # 2. Update Registry
        if pnl > 0:
            self.registry.update_score(model_name, +5.0)
            print(f"[LOOP] Positive feedback for {model_name}: +5.0")
        else:
            self.registry.update_score(model_name, -10.0) # Penalize losses harder
            print(f"[LOOP] Negative feedback for {model_name}: -10.0")
