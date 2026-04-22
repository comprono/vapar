import asyncio
from data_layer.mock_ingestor import MockIngestor
from data_layer.feature_store import FeatureStore
from data_layer.storage.csv_storage import CSVStorage
from common.schemas.market_data import OrderBook, Quote
from common.logger import get_logger

logger = get_logger("TestPipeline")

async def main():
    logger.info("Starting Data Layer Integration Test...")
    
    # 1. Init Components
    ingestor = MockIngestor(symbols=["BTC/USDT", "ETH/USDT"])
    feature_store = FeatureStore(window_size=10)
    storage = CSVStorage(root_dir="test_data_output")
    await storage.connect()
    
    # 2. Define Callback
    async def on_market_data(data):
        # A. Store raw (Only if it's a Quote, because Storage expects Quote/Trade)
        if isinstance(data, Quote):
             await storage.save_quote(data)
        elif isinstance(data, OrderBook):
            # In a real system we'd save OrderBook snapshots to S3, here we skip or mock
            pass
        
        # B. Calculate Features
        feature_store.push(data)
        
        # C. Log
        symbol = data.instrument_id
        features = feature_store.get_features(symbol, n=1)
        if features is not None and len(features) > 0:
            last_feats = feature_store._history[symbol][-1]
            print(f"[{symbol}] OBI: {last_feats.get('obi', 0):.4f} | Spread: {last_feats.get('spread', 0):.4f}")

    ingestor.add_callback(on_market_data)
    
    # 3. Run
    ingestor_task = asyncio.create_task(ingestor.start())
    
    logger.info("Running for 5 seconds...")
    await asyncio.sleep(5)
    
    logger.info("Stopping...")
    await ingestor.stop()
    storage.close()
    logger.info("Test Complete.")

if __name__ == "__main__":
    asyncio.run(main())
