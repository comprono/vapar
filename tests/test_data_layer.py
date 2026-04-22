import asyncio
import os
from common.schemas.market_data import Instrument, MarketType
from data_layer.ingestors.mock import MockIngestor
from data_layer.storage.file import FileStorage

async def main():
    print("Starting Data Layer Integration Test...")
    
    # 1. Setup Storage
    storage = FileStorage(root_dir="test_data_store")
    await storage.connect()
    print("Storage connected.")
    
    # 2. Setup Ingestor
    ingestor = MockIngestor()
    await ingestor.connect()
    
    # 3. Define Instruments
    instruments = [
        Instrument(id="mock:btc", symbol="BTC", exchange="MOCK", market_type=MarketType.CRYPTO),
        Instrument(id="mock:aapl", symbol="AAPL", exchange="MOCK", market_type=MarketType.EQUITY)
    ]
    
    await ingestor.subscribe(instruments)
    
    # 4. Consume stream for a few seconds
    print("Listening for quotes (5 seconds)...")
    count = 0
    try:
        async for quote in ingestor.stream_quotes():
            await storage.save_quotes([quote])
            print(f"Saved quote for {quote.instrument_id} @ {quote.price}")
            count += 1
            if count >= 5:
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ingestor.running = False

    print(f"Test Complete. Saved {count} quotes to test_data_store/")

if __name__ == "__main__":
    asyncio.run(main())
