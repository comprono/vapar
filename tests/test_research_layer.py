import asyncio
from common.schemas.market_data import Instrument, MarketType
from data_layer.ingestors.mock import MockIngestor
from research_layer.models.random_model import RandomModel
from research_layer.allocator import PortfolioAllocator
from research_layer.backtest import BacktestEngine

async def main():
    print("Starting Research Layer Integration Test...")
    
    # 1. Setup Data
    instruments = [
        Instrument(id="mock:btc", symbol="BTC", exchange="MOCK", market_type=MarketType.CRYPTO),
        Instrument(id="mock:eth", symbol="ETH", exchange="MOCK", market_type=MarketType.CRYPTO)
    ]
    ingestor = MockIngestor()
    await ingestor.connect()
    await ingestor.subscribe(instruments)
    
    # 2. Setup AI
    models = [RandomModel()]
    allocator = PortfolioAllocator(risk_aversion=1.5)
    
    # 3. Setup Backtest
    engine = BacktestEngine(ingestor, models, allocator)
    
    # 4. Run
    report = await engine.run(max_ticks=20)
    
    print("\n--- Backtest Report ---")
    print(f"Total Events with Action: {report['total_ticks']}")
    print(f"Total Allocations: {report['trades_generated']}")
    
    for i, res in enumerate(report['sample_decisions']):
        print(f"\nEvent {i+1} ({res['quote'].instrument_id}):")
        for d in res['decisions']:
            print(f"  -> Allocation: {d.instrument_id} = {d.target_weight:.2%} ({d.rationale})")

    # Clean shutdown
    ingestor.running = False

if __name__ == "__main__":
    asyncio.run(main())
