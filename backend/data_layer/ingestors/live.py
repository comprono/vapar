import yfinance as yf
import asyncio
import pandas as pd
from datetime import datetime
from typing import List, AsyncGenerator
from backend.common.schemas.market_data import Quote, MarketType

class YahooIngestor:
    def __init__(self):
        self.running = False
        self.tickers = ["BTC-USD", "ETH-USD", "SPY"] # Default, will be updated by config

    async def connect(self):
        print(f"[YaphooIngestor] Connected to Yahoo Finance API.")
        self.running = True

    def update_tickers(self, tickers: List[str]):
        # Map simple symbols to Yahoo format if needed
        self.tickers = []
        for t in tickers:
            if t in ["BTC", "ETH"]: self.tickers.append(f"{t}-USD")
            else: self.tickers.append(t)
        print(f"[YahooIngestor] Tickers updated: {self.tickers}")

    async def stream_quotes(self) -> AsyncGenerator[Quote, None]:
        print("[YahooIngestor] Starting poll loop...")
        while self.running:
            try:
                # Fetch data for all tickers at once
                data = yf.download(self.tickers, period="1d", interval="1m", progress=False)
                
                # Get latest row
                if not data.empty:
                    latest = data.iloc[-1]
                    timestamp = data.index[-1]
                    
                    # Handle MultiIndex columns if multiple tickers
                    is_multi = isinstance(data.columns, pd.MultiIndex)
                    
                    for ticker in self.tickers:
                        try:
                            if is_multi:
                                price = float(latest["Close"][ticker])
                                # volume = float(latest["Volume"][ticker])
                            else:
                                price = float(latest["Close"])
                            
                            # Determine market type
                            m_type = MarketType.CRYPTO if "-USD" in ticker else MarketType.EQUITY
                            
                            yield Quote(
                                instrument_id=ticker,
                                price=price,
                                timestamp=datetime.now(), # Use system time for real-time feel, or timestamp.to_pydatetime()
                                bid=price * 0.9995,
                                ask=price * 1.0005,
                                volume=0, # Simplified
                                market_type=m_type,
                                volatility=0.02 # Placeholder or calculate
                            )
                        except Exception as e:
                            # print(f"Error parsing ticker {ticker}: {e}")
                            pass
                            
                await asyncio.sleep(5) # Poll every 5 seconds (Yahoo limitation)
                
            except Exception as e:
                print(f"[YahooIngestor] Fetch Error: {e}")
                await asyncio.sleep(5)
