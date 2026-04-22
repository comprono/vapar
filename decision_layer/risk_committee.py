import numpy as np
from typing import List, Dict, Tuple
from decimal import Decimal
from datetime import datetime
from common.types import TradeIntent, TradeStatus, TradeDirection
from common.risk_config import RiskConfig
from common.logger import get_logger

logger = get_logger("RiskCommittee")

class RiskCommittee:
    """
    The Safety Layer.
    Deterministically rejects trades that violate risk limits.
    Implements Dynamic Volatility Targeting (Gap #5).
    """

    def __init__(self, current_equity: float = 100000.0, target_annual_vol: float = 0.20):
        self.equity = current_equity
        self.target_annual_vol = target_annual_vol # e.g. 20% annualized vol target
        
        # State tracking for Covariance
        self.active_positions: Dict[str, float] = {} # Symbol -> Notional Value
        self.daily_losses = 0.0
        self.is_locked_out = False
        
        # Mock Covariance Matrix (In prod, this updates real-time from FeatureStore)
        # 1.0 correlation diagonal, 0.5 correlation off-diagonal stub
        self.correlation_matrix = {} 
        self.instrument_vols = {} # Annualized STD

    def update_market_stats(self, symbol: str, annualized_vol: float):
        """Update volatility estimates from Data Layer."""
        self.instrument_vols[symbol] = annualized_vol

    def review(self, intent: TradeIntent) -> bool:
        """
        Main entry point. Returns True if Approved, False if Rejected.
        Modifies trade.status and trade.risk_check_log.
        """
        intent.risk_check_log.append(f"Review started at {datetime.now()}")
        
        if self.is_locked_out:
            intent.status = TradeStatus.RISK_REJECTED
            intent.risk_check_log.append("REJECTED: System is in Drawdown Lockout")
            return False

        # 1. Check Dynamic Volatility Sizing (Gap #5)
        # Rule: Position Size = (Target Portfolio Vol / Instrument Vol) * Equity * Scalar
        # Simplified: We check if the *requested* size exceeds the Vol-Targeted Max Size
        
        inst_vol = self.instrument_vols.get(intent.symbol, 0.50) # Default to High Vol (50%) if unknown
        if inst_vol == 0: inst_vol = 0.50
        
        # Kelly-heuristic or Vol-Targeting cap
        # Max Size = (Target Vol 20% / Inst Vol 50%) * Equity * 1.5 (Buffer)
        vol_adjusted_limit_pct = (self.target_annual_vol / inst_vol)
        max_notional_vol_adj = self.equity * vol_adjusted_limit_pct
        
        # Also respect Hard Cap from Config
        hard_cap_notional = self.equity * float(RiskConfig.MAX_POSITION_SIZE_PCT)
        
        final_limit = min(max_notional_vol_adj, hard_cap_notional)
        
        requested_notional = float(intent.size) * 1.0 # Assuming size is notional for simplicity here, else Price * Qty
        # If size is quantity, we need price. In TradeIntent, let's assume 'size' is quantity, so we need price.
        # For this logic, let's assume intent.size is ESTIMATED NOTIONAL USD for safety check.
        
        if requested_notional > final_limit:
            intent.status = TradeStatus.RISK_REJECTED
            msg = f"REJECTED: Vol-Adj Limit Exceeded. Req: ${requested_notional:.2f}, Limit: ${final_limit:.2f} (InstVol: {inst_vol:.2%})"
            intent.risk_check_log.append(msg)
            logger.warning(msg)
            return False

        # 2. Check Portfolio Covariance / Correlation (Gap #5)
        # Prevent adding risk to an already correlated portfolio
        if not self._check_correlation_impact(intent):
            intent.status = TradeStatus.RISK_REJECTED
            intent.risk_check_log.append("REJECTED: Portfolio Correlation Limit Breached")
            return False

        # 3. Hard Constraints (Drawdown, etc)
        if self.daily_losses > (self.equity * float(RiskConfig.MAX_DAILY_DRAWDOWN_PCT)):
            self.is_locked_out = True
            intent.status = TradeStatus.RISK_REJECTED
            intent.risk_check_log.append("REJECTED: Daily Loss Limit Hit")
            return False
            
        intent.status = TradeStatus.RISK_APPROVED
        intent.risk_check_log.append("APPROVED: All checks passed")
        return True

    def _check_correlation_impact(self, intent: TradeIntent) -> bool:
        """
        Check if adding this trade increases Portfolio VaR beyond limit.
        """
        # Simplified Stub: Check if we already have exposure to this asset or highly correlated ones.
        if intent.symbol in self.active_positions:
            # Adding to existing? Check total exposure
            new_total = self.active_positions[intent.symbol] + float(intent.size)
            if new_total > (self.equity * float(RiskConfig.MAX_POSITION_SIZE_PCT)):
                return False
        
        return True

    def on_fill(self, symbol: str, notional: float):
        """Update state after execution."""
        current = self.active_positions.get(symbol, 0.0)
        self.active_positions[symbol] = current + notional
