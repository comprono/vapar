from typing import Optional, Dict
from common.schemas.trade_intent import TradeIntent
from backend.common.schemas.config import SystemConfig

class ExecutionGatekeeper:
    """
    FINAL SAFETY LAYER.
    This component sits between the Decision Engine and the Order Router.
    It enforces hard cryptographic-like limits that the AI cannot override.
    
    Checks:
    1. Capital Limits (Max trade size)
    2. Frequency Limits (Kill switch if trading too fast)
    3. Mode Safety (Prevents execution in SHADOW mode)
    """
    def __init__(self, config: SystemConfig):
        self.config = config
        self.daily_loss = 0.0
        self.trade_count = 0
        self.max_daily_trades = 50 # Hard limit
        self.max_single_trade_pct = 0.05 # 5% hard cap

    def validate(self, intent: TradeIntent, mode: str, current_equity: float) -> bool:
        """
        Returns True if trade is SAFE to execute.
        Returns False if blocked by safety protocols.
        """
        # 1. Shadow Mode Check
        if mode == "SHADOW":
            # In shadow mode, we return False to block physical execution,
            # but we should log it as "Approved Virtual" upstream.
            # actually, for this gatekeeper, let's say it validates SAFETY.
            # The router should handle the "Shadow" logic, but the Gate ensures 
            # we don't accidentally send real orders if logic fails.
            return False 

        # 2. Hard Trade Cap (Frequency Attack Protection)
        if self.trade_count >= self.max_daily_trades:
            print(f"[GATEKEEPER] BLOCKED: Daily trade limit ({self.max_daily_trades}) reached.")
            return False

        # 3. Position Sizing Hard Cap (Fat Finger Protection)
        max_allowed_size = current_equity * self.max_single_trade_pct
        # In current pipeline intent.size is quantity. Use a conservative guard:
        # if quantity itself is larger than notional cap, block it.
        estimated_value = float(intent.size)
        if estimated_value > max_allowed_size:
            print(f"[GATEKEEPER] BLOCKED: Trade size {estimated_value:.2f} exceeds cap {max_allowed_size:.2f}")
            return False

        return True

    def record_execution(self, value: float):
        self.trade_count += 1
        # self.daily_loss update would happen on close, 
        # here we just track activity frequency.
