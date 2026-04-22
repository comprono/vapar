import asyncio
from datetime import datetime
from common.schemas.trade_intent import TradeIntent
from decision_layer.bus import SignalBus
from decision_layer.risk import RiskCommittee
from decision_layer.execution import OrderRouter

async def main():
    print("Starting Decision Layer Integration Test...")
    
    # 1. Setup Components
    bus = SignalBus()
    risk = RiskCommittee(max_position_size_usd=5000, min_confidence=0.7)
    router = OrderRouter()
    
    # 2. Producer Task (Research Layer Simulation)
    async def producer():
        print("[Producer] Generating intents...")
        # Valid Intent
        intent_valid = TradeIntent(
            id="trade_001", timestamp=datetime.now(), instrument_id="mock:btc", strategy_id="strat_1",
            side="buy", size=0.05, expected_return=0.02, confidence_score=0.85
        )
        await bus.publish(intent_valid)
        
        # Risky Intent (Low Confidence)
        intent_risky = TradeIntent(
            id="trade_002", timestamp=datetime.now(), instrument_id="mock:eth", strategy_id="strat_1",
            side="buy", size=1.0, expected_return=0.05, confidence_score=0.50 
        )
        await bus.publish(intent_risky)
        
        # Too Large Intent
        intent_whale = TradeIntent(
            id="trade_003", timestamp=datetime.now(), instrument_id="mock:btc", strategy_id="strat_1",
            side="buy", size=100.0, expected_return=0.01, confidence_score=0.99
        )
        await bus.publish(intent_whale)
        
        print("[Producer] Done.")

    # 3. Consumer Task (Decision Engine)
    async def consumer():
        print("[Consumer] Listening...")
        count = 0
        async for intent in bus.subscribe():
            # In a real app, price comes from Data Layer. Mocking here.
            current_price = 1000.0 if "eth" in intent.instrument_id else 50000.0
            
            if risk.check(intent, current_price):
                await router.execute(intent)
                risk.update_exposure(intent, current_price)
            
            count += 1
            if count >= 3:
                bus.stop()

    # 4. Run
    await asyncio.gather(producer(), consumer())
    print("Test Complete.")

if __name__ == "__main__":
    asyncio.run(main())
