import asyncio
import random
from datetime import datetime
from typing import List

# Data Layer
from common.schemas.market_data import Instrument, MarketType, Quote
from data_layer.ingestors.mock import MockIngestor
from data_layer.storage.file import FileStorage

# Research Layer
from research_layer.models.random_model import RandomModel
from research_layer.allocator import PortfolioAllocator
from common.schemas.trade_intent import TradeIntent

# Decision Layer
from decision_layer.bus import SignalBus
from decision_layer.risk import RiskCommittee
from decision_layer.execution import OrderRouter

# Learning Layer
from learning_layer.performance import PerformanceAnalytics
from learning_layer.registry import ModelRegistry
from learning_layer.loop import OptimizationLoop

async def main():
    print("===================================================")
    print("   UNIFIED AUTONOMOUS SYSTEM - FULL SIMULATION")
    print("===================================================\n")

    # --- 1. INITIALIZATION ---
    print("[INIT] Setting up layers...")
    
    # Data
    ingestor = MockIngestor()
    storage = FileStorage(root_dir="sim_data")
    await ingestor.connect()
    await storage.connect()
    
    instruments = [
        Instrument(id="mock:btc", symbol="BTC", exchange="MOCK", market_type=MarketType.CRYPTO),
        Instrument(id="mock:eth", symbol="ETH", exchange="MOCK", market_type=MarketType.CRYPTO)
    ]
    await ingestor.subscribe(instruments)

    # Research
    model = RandomModel()
    allocator = PortfolioAllocator()
    
    # Decision
    bus = SignalBus()
    risk = RiskCommittee(max_position_size_usd=50000, min_confidence=0.1)
    router = OrderRouter()
    
    # Learning
    registry = ModelRegistry()
    analytics = PerformanceAnalytics()
    loop = OptimizationLoop(analytics, registry)
    
    registry.register_model(model.name, "1.0", {"type": "random"})
    
    print("[INIT] System ready.\n")

    # --- 2. THE LOOP ---
    # We will simulate the loop manually for clarity rather than independent async tasks,
    # so we can see the step-by-step flow of a single event.

    max_events = 5
    print(f"[RUN] Starting simulation for {max_events} events...\n")
    
    tick_count = 0
    async for quote in ingestor.stream_quotes():
        tick_count += 1
        print(f"--- Event {tick_count} ---")
        print(f"[DATA] Quote: {quote.instrument_id} @ {quote.price:.2f}")
        
        # A. Research (Predict & Allocate)
        # --------------------------------
        prediction = await model.predict(quote)
        intents: List[TradeIntent] = []
        
        if prediction:
            print(f"  [AI] Prediction: ExpRet={prediction.expected_return:.2%}, Conf={prediction.confidence_score:.2f}")
            allocations = allocator.allocate([prediction])
            
            for alloc in allocations:
                # Convert allocation to Trade Intent
                # Mocking logic: Allocation % -> Notional -> Size
                target_notional = 100000 * alloc.target_weight # Mock 100k capital
                size = target_notional / quote.price
                
                intent = TradeIntent(
                    id=f"trade_{tick_count}_{alloc.instrument_id}",
                    timestamp=datetime.now(),
                    instrument_id=alloc.instrument_id,
                    strategy_id=model.name,
                    side="buy", # Mock side
                    size=round(size, 4),
                    expected_return=prediction.expected_return,
                    confidence_score=prediction.confidence_score,
                    meta={"allocation_rationale": alloc.rationale}
                )
                intents.append(intent)
        else:
            print("  [AI] No signal.")

        # B. Decision (Risk & Exec)
        # -------------------------
        for intent in intents:
            print(f"  [BUS] Processing Intent: Buy {intent.size} {intent.instrument_id}")
            
            is_approved = risk.check(intent, quote.price)
            if is_approved:
                await router.execute(intent)
                risk.update_exposure(intent, quote.price)
                
                # C. Learning (Feedback Simulation)
                # ---------------------------------
                # Cheat: Simulate immediate outcome
                market_move = random.uniform(-0.02, 0.03) # Random move after trade
                pnl = (market_move) * (intent.size * quote.price)
                
                print(f"  [SIM] Market moved {market_move:.2%}. PnL: ${pnl:.2f}")
                
                loop.process_feedback(intent.id, intent.strategy_id, pnl)
                
                status = registry.get_model_status(intent.strategy_id)
                print(f"  [LEARN] Updated {intent.strategy_id} Score: {status['score']:.1f}")

        print("")
        if tick_count >= max_events:
            break

    print("===================================================")
    print("   SIMULATION COMPLETE")
    print("===================================================")

if __name__ == "__main__":
    asyncio.run(main())
