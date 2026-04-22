from abc import ABC, abstractmethod
from typing import List, Tuple
from .types import TradeIntent

class SafetyCheck(ABC):
    """
    Interface for individual safety rules (e.g., 'MaxDrawdownCheck', 'ExposureCheck').
    """
    
    @abstractmethod
    def check(self, trade: TradeIntent) -> Tuple[bool, str]:
        """
        Evaluates the trade against this specific rule.
        Returns:
            (passed: bool, reason: str)
        """
        pass

class RiskGatekeeper(ABC):
    """
    Interface for the authoritative Risk Committee.
    """
    
    @abstractmethod
    def validate_trade(self, trade: TradeIntent) -> Tuple[bool, List[str]]:
        """
        Runs all safety checks.
        Returns:
            (approved: bool, reasons: List[str])
        """
        pass
