import asyncio
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal

# Layer 1: Data
from data_layer.mock_ingestor import MockIngestor
from data_layer.feature_store import FeatureStore
from common.schemas.market_data import Quote, OrderBook

# Layer 2: Research
from research_layer.models.transformer import TransformerModel
from research_layer.regime.hmm import ProbabilisticRegimeDetector
from research_layer.allocator.meta_model import PortfolioAllocator
from research_layer.models.base import Prediction

# Layer 3: Decision
from decision_layer.signal_bus import SignalBus
from decision_layer.risk_committee import RiskCommittee
from decision_layer.execution import ExecutionEngine
from common.types import TradeIntent, MarketType, TradeDirection

# Layer 5: Learning
from learning_layer.replay import OrderBookReplay
from learning_layer.event_store import TradeEventLogger
from common.logger import get_logger

logger = get_logger("TestFullSystem")

async def main():
    logger.info("Initializing Unified Multi-Market System (Test Mode)...")
    
    # --- 1. Infrastructure Setup ---
    bus = SignalBus()
    event_store = TradeEventLogger("test_audit_log.jsonl")
    
    # --- 2. Component Initialization ---
    # Layer 1
    ingestor = MockIngestor(symbols=["BTC/USDT"], interval_sec=0.1)
    feature_store = FeatureStore()
    
    # Layer 2
    transformer = TransformerModel(input_dim=10)
    regime_detector = ProbabilisticRegimeDetector()
    allocator = PortfolioAllocator()
    
    # Layer 3
    risk_committee = RiskCommittee(current_equity=100000.0)
    execution = ExecutionEngine()
    
    # Layer 5
    replay = OrderBookReplay() # For simulated fills
    
    # Mock Training of Models (so they work during inference)
    # Train Regime on fake history
    fake_ret = np.random.randn(100) * 0.01
    fake_vol = np.abs(np.random.randn(100) * 0.02)
    regime_detector.fit(fake_ret, fake_vol)
    
    logger.info("System Initialized.")
    
    # --- 3. The Main Loop (Simulating 1 minute of trading) ---
    logger.info("Starting Simulation Loop...")
    
    # State tracking
    simulation_steps = 20 # Run for 20 ticks
    
    # Hook for Data Ingestion
    # In prod, this is event-driven. Here we iterate the mock generator.
    
    async for event in ingestor.connect():
        simulation_steps -= 1
        if simulation_steps <= 0:
            break
            
        # A. Data Layer Processing
        if isinstance(event, OrderBook):
            # Update Feature Store
            feature_store.push(event)
            # Update Replay Environment with latest liquidity
            replay.update_book(event)
            
            # Calculate Features
            features = feature_store.get_features(event.instrument_id)
            # returns, vol, obi, spread... (Mocking generic feature vector for Transformer)
            # Create a fake feature vector for the Transformer (Sequence=10, Dim=10)
            model_input = np.random.randn(10, 10).astype(np.float32) 
            
            # B. Research Layer (Intelligence)
            # 1. Regime
            curr_regime = regime_detector.predict(0.001, 0.02) # Fake updated return/vol
            
            # 2. Signal
            signal = await transformer.predict(model_input)
            
            if signal:
                signal.instrument_id = event.instrument_id
                
                # 3. Allocation (Meta-Model)
                targets = allocator.allocate([signal], curr_regime)
                target_weight = targets.get(event.instrument_id, 0.0)
                
                print(f"[DEBUG] Signal: {signal.expected_return:.4f}, Weight: {target_weight:.4f}")

                # If allocator wants exposure > 0, generate Intent
                # Simplified logic: If target > 0 and we have no position (mock), BUY
                if target_weight > 0.02: # Threshold
                    # Generate Trade Intent
                    intent = TradeIntent(
                        strategy_id="Transformer_Alpha",
                        symbol=event.instrument_id,
                        market_type=MarketType.CRYPTO,
                        direction=TradeDirection.LONG,
                        size=Decimal(str(target_weight * 100000.0)), # Notional
                        confidence=signal.confidence_score,
                        rationale=f"Transformer Signal {signal.expected_return:.4f} | Regime {curr_regime.regime_name}",
                        expected_return=signal.expected_return,
                        price_limit=None,
                        time_horizon="1m"
                    )
                    
                    # Push to Decision Layer
                    await bus.push(intent)
                    event_store.log_event(intent, "SIGNAL_GENERATED")
        
        # C. Decision Layer (Risk & Execution)
        while not bus.empty():
            intent = await bus.pop()
            
            # 1. Risk Check (The "Seatbelt")
            risk_committee.update_market_stats(intent.symbol, 0.50) # Update vol stub
            approved = risk_committee.review(intent)
            event_store.log_event(intent, "RISK_CHECK_COMPLETED", {"approved": approved})
            
            if approved:
                # 2. Execution (Async)
                # In simulation, we use Replay to estimate fill
                price, cost, slippage = replay.match_order(intent.direction, float(intent.size)) # Size as Qty approximation for Replay
                
                # In real execution, we'd call: await execution.execute(intent)
                # Here we simulate the result directly to verify Replay
                intent.status = "FILLED"
                
                logger.info(f"*** TRADE EXECUTED *** {intent.direction.value} {intent.symbol} | Price: {price:.2f} | Slippage: {slippage:.2f}bps")
                event_store.log_event(intent, "TRADE_FILLED", {"price": price, "slippage_bps": slippage})
            else:
                logger.warning(f"Trade Blocked: {intent.risk_check_log[-1]}")
                
    logger.info("Simulation Complete. Checking Audit Log...")
    
    # --- 4. Post-Mortem ---
    count = 0
    for event in event_store.replay_events():
        count += 1
    logger.info(f"Audit Log contains {count} events.")

if __name__ == "__main__":
    asyncio.run(main())
