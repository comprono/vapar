from decimal import Decimal

class RiskConfig:
    """
    Immutable risk configuration.
    These are the "Seatbelts" that cannot be overridden by AI.
    """
    
    # Capital Limits
    MAX_POSITION_SIZE_PCT = Decimal("0.05") # Max 5% of equity per trade
    MAX_TOTAL_EXPOSURE_PCT = Decimal("0.80") # Max 80% deployed at any time
    MAX_LEVERAGE = Decimal("1.0") # No leverage initially
    
    # Loss Limits
    MAX_DAILY_DRAWDOWN_PCT = Decimal("0.02") # Stop trading if down 2% in a day
    MAX_PORTFOLIO_DRAWDOWN_PCT = Decimal("0.10") # Hard stop if down 10% total
    
    # Strategy Limits
    MIN_CONFIDENCE_THRESHOLD = 0.60 # Reject trades with low AI confidence
    MAX_CORRELATION_ALLOWED = 0.7 # Reject trades highly correlated with existing positions
    
    # Operational Limits
    MAX_SLIPPAGE_TOLERANCE_PCT = Decimal("0.005") # 0.5% slippage max
    KILL_SWITCH_ON_API_ERRORS = True
    MAX_CONSECUTIVE_FAILURES = 3
