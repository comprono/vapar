import asyncio
from decimal import Decimal
from common.types import TradeIntent, MarketType, TradeDirection, TradeStatus
from decision_layer.signal_bus import SignalBus
from decision_layer.risk_committee import RiskCommittee
from decision_layer.execution import ExecutionEngine
from common.logger import get_logger

logger = get_logger("TestDecisionLayer")

async def main():
    logger.info("Starting Decision Layer Integration Test...")
    
    # 1. Setup Components
    bus = SignalBus()
    risk = RiskCommittee(current_equity=100000.0)
    execution = ExecutionEngine()
    
    # Update mock volatilities
    risk.update_market_stats("BTC/USDT", 0.80) # High Vol
    
    # 2. Simulate Research Layer pushing signals
    # Trade 1: Safe Trade
    safe_trade = TradeIntent(
        strategy_id="Strat_1",
        symbol="BTC/USDT",
        market_type=MarketType.CRYPTO,
        direction=TradeDirection.LONG,
        size=Decimal("1000.0"), # $1000 Notional
        price_limit=None,
        rationale="Test Safe",
        confidence=0.9,
        expected_return=0.05,
        time_horizon="1h"
    )
    
    # Trade 2: Dangerous Trade (Too big for High Vol asset)
    # With 20% Target Vol and 80% Inst Vol, Max Size should be 0.2/0.8 * 100k = $25k
    # Let's request $50k
    dangerous_trade = TradeIntent(
        strategy_id="Strat_1",
        symbol="BTC/USDT",
        market_type=MarketType.CRYPTO,
        direction=TradeDirection.SHORT,
        size=Decimal("50000.0"), 
        price_limit=None,
        rationale="Test Danger",
        confidence=0.9,
        expected_return=0.10,
        time_horizon="1h"
    )

    await bus.push(safe_trade)
    await bus.push(dangerous_trade)
    
    # 3. Decision Loop (Consumer)
    while not bus.empty():
        intent = await bus.pop()
        logger.info(f"Processing {intent.id} ({intent.rationale})...")
        
        # A. Risk Check
        approved = risk.review(intent)
        
        if approved:
            # B. Execute
            await execution.execute(intent)
            risk.on_fill(intent.symbol, float(intent.size))
        else:
            logger.warning(f"Trade Rejected: {intent.risk_check_log[-1]}")

    logger.info("Test Complete.")

if __name__ == "__main__":
    asyncio.run(main())
