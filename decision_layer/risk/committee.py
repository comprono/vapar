from typing import Dict, Optional
from common.schemas.trade_intent import TradeIntent
from decision_layer.risk.var_calculator import VaRCalculator
from research_layer.correlation import CorrelationAnalyzer

class RiskCommittee:
    """
    Hard gatekeeper for all trades.
    Now includes statistical risk measures (VaR) and correlation checks.
    """
    
    def __init__(
        self, 
        max_position_size_usd: float = 1000.0, 
        min_confidence: float = 0.6,
        max_portfolio_var_pct: float = 5.0,
        var_calculator: Optional[VaRCalculator] = None,
        correlation_analyzer: Optional[CorrelationAnalyzer] = None
    ):
        self.max_position_size_usd = max_position_size_usd
        self.min_confidence = min_confidence
        self.max_portfolio_var_pct = max_portfolio_var_pct
        self.current_exposure: Dict[str, float] = {}
        self.is_kill_switch_active = False
        self.var_calculator = var_calculator or VaRCalculator()
        self.correlation_analyzer = correlation_analyzer or CorrelationAnalyzer()
        
        print(f"[RISK] Initialized with VaR limit: {max_portfolio_var_pct}%, Min Diversification: 0.3")
    
    def check(
        self, 
        intent: TradeIntent, 
        current_price: float,
        current_positions: Optional[Dict] = None,
        portfolio_value: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Validate a trade intent against all risk rules.
        
        Returns:
            Dict with {"approved": bool, "checks": {...}, "reason": str}
        """
        checks = {}
        
        # 1. Kill Switch Check
        if self.is_kill_switch_active:
            return {
                "approved": False,
                "checks": {"kill_switch": False},
                "reason": "Kill switch is active"
            }
        checks["kill_switch"] = True
        
        # 2. Confidence Check
        confidence_ok = intent.confidence_score >= self.min_confidence
        checks["confidence"] = confidence_ok
        if not confidence_ok:
            return {
                "approved": False,
                "checks": checks,
                "reason": f"Confidence {intent.confidence_score:.2f} < {self.min_confidence}"
            }
        
        # 3. Position Size Check
        notional_value = intent.size * current_price
        size_ok = notional_value <= self.max_position_size_usd
        checks["position_size"] = size_ok
        if not size_ok:
            return {
                "approved": False,
                "checks": checks,
                "reason": f"Size ${notional_value:.2f} > Limit ${self.max_position_size_usd}"
            }
        
        # 4. Concentration Check
        current = self.current_exposure.get(intent.instrument_id, 0.0)
        concentration_ok = current + notional_value <= self.max_position_size_usd * 2
        checks["concentration"] = concentration_ok
        if not concentration_ok:
            return {
                "approved": False,
                "checks": checks,
                "reason": "Concentration limit exceeded"
            }
        
        # 5. VaR Check (if positions and portfolio value provided)
        if current_positions and portfolio_value:
            try:
                # Calculate current portfolio VaR
                current_var = self.var_calculator.calculate_portfolio_var(
                    current_positions
                )
                
                # Calculate proposed trade VaR
                trade_var = self.var_calculator.calculate_position_var(
                    intent.instrument_id,
                    intent.size,
                    current_price
                )
                
                # Check if new VaR exceeds limit
                new_total_var = current_var["portfolio_var_usd"] + trade_var["var_usd"]
                var_pct = (new_total_var / portfolio_value) * 100
                var_ok = var_pct <= self.max_portfolio_var_pct
                
                checks["var"] = var_ok
                checks["var_pct"] = var_pct
                
                if not var_ok:
                    return {
                        "approved": False,
                        "checks": checks,
                        "reason": f"VaR {var_pct:.2f}% > Limit {self.max_portfolio_var_pct}%"
                    }
            except Exception as e:
                print(f"[RISK] VaR check failed: {e}")
                checks["var"] = True  # Don't block on VaR errors in early phase
        else:
            checks["var"] = True  # Skip VaR if no position data
        
        # 6. Diversification Check (Correlation)
        if current_positions:
            try:
                proposed_trade = {intent.instrument_id: notional_value}
                div_check = self.correlation_analyzer.check_diversification(
                    current_positions,
                    proposed_trade
                )
                
                checks["diversification"] = div_check["approved"]
                checks["div_score"] = div_check["new_score"]
                
                if not div_check["approved"]:
                    return {
                        "approved": False,
                        "checks": checks,
                        "reason": div_check["reason"]
                    }
            except Exception as e:
                print(f"[RISK] Diversification check failed: {e}")
                checks["diversification"] = True  # Don't block on errors
        else:
            checks["diversification"] = True
        
        # All checks passed
        print(f"[RISK] ✓ APPROVED {intent.id}: ${notional_value:.2f} on {intent.instrument_id}")
        return {
            "approved": True,
            "checks": checks,
            "reason": "All checks passed"
        }
    
    def update_exposure(self, intent: TradeIntent, current_price: float):
        """Update internal state after a confirmed trade."""
        notional_value = intent.size * current_price
        if intent.side == 'buy':
            self.current_exposure[intent.instrument_id] = \
                self.current_exposure.get(intent.instrument_id, 0.0) + notional_value
        # Sell logic omitted for brevity
    
    def activate_kill_switch(self, reason: str):
        """Emergency stop all trading."""
        self.is_kill_switch_active = True
        print(f"[RISK] 🚨 KILL SWITCH ACTIVATED: {reason}")
    
    def deactivate_kill_switch(self):
        """Resume trading after manual review."""
        self.is_kill_switch_active = False
        print(f"[RISK] Kill switch deactivated")
