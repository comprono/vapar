import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import os

class DataLoader:
    """Load and cache historical OHLCV data for backtesting."""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def load(self, symbol: str, start_date: str, end_date: str, interval: str = "1d") -> pd.DataFrame:
        """
        Load historical data, using cache if available.
        
        Args:
            symbol: Ticker symbol (e.g., "BTC-USD", "AAPL")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval (1m, 5m, 15m, 1h, 1d)
        
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        cache_file = f"{self.cache_dir}/{symbol}_{start_date}_{end_date}_{interval}.csv"
        
        # Check cache
        if os.path.exists(cache_file):
            print(f"[DataLoader] Loading {symbol} from cache")
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df
        
        # Fetch from Yahoo Finance
        print(f"[DataLoader] Fetching {symbol} from Yahoo Finance")
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval=interval)
        
        if df.empty:
            raise ValueError(f"No data found for {symbol} between {start_date} and {end_date}")
        
        # Save to cache
        df.to_csv(cache_file)
        print(f"[DataLoader] Cached {len(df)} bars for {symbol}")
        
        return df
    
    def load_multiple(self, symbols: list[str], start_date: str, end_date: str, interval: str = "1d") -> dict:
        """Load data for multiple symbols concurrently."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        start_time = time.time()
        data = {}
        
        # Determine optimal thread count (max 20 to avoid rate limits)
        max_workers = min(len(symbols), 20)
        print(f"[DataLoader] Fetching {len(symbols)} symbols with {max_workers} threads...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(self.load, symbol, start_date, end_date, interval): symbol 
                for symbol in symbols
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    df = future.result()
                    if not df.empty:
                        data[symbol] = df
                except Exception as e:
                    print(f"[DataLoader] Failed to load {symbol}: {e}")
                    
        elapsed = time.time() - start_time
        print(f"[DataLoader] Completed in {elapsed:.2f}s. Loaded {len(data)}/{len(symbols)} symbols.")
        return data
