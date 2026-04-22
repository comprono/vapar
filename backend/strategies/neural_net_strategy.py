import pandas as pd
import numpy as np
import asyncio
from backend.strategies.base import Strategy, Signal
from research_layer.models.mlp_model import MLPModel
from common.schemas.market_data import Quote
from datetime import datetime

class NeuralNetStrategy(Strategy):
    """
    Neural Network Scalper Strategy.
    """
    
    def __init__(self, window_size: int = 10, train_interval: int = 30):
        super().__init__(
            name="NeuralNet_Scalper",
            params={
                "window_size": window_size,
                "train_interval": train_interval
            }
        )
        self.window_size = window_size
        self.model = MLPModel(window_size=window_size)
        
    def analyze(self, data: pd.DataFrame, current_symbol: str) -> Signal:
        return Signal(current_symbol, "HOLD", 0.0, "Live mode pending")

    def generate_signals(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = "HOLD"
        signals['confidence'] = 0.0
        
        prices = data['Close'].values
        dates = data.index
        
        # Need enough data for indicators (e.g. 50)
        start_idx = 100 
        
        if len(prices) < start_idx:
            return signals

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 1. Train on first 50%
        split_idx = int(len(prices) * 0.5)
        train_df = data.iloc[:split_idx].copy()
        
        print(f"Training Scalper on {len(train_df)} candles...")
        loop.run_until_complete(self.model.train(train_df))
        
        # 2. Predict / Walk-Forward
        # We MUST prime the buffer with history before predicting
        # To match the split, we should fill buffer with recent history from training
        
        # Fill buffer with last 50 prices and volume of training set
        for i in range(split_idx-50, split_idx):
             self.model.price_buffer.append(float(prices[i]))
             vol = float(data.iloc[i]['Volume']) if 'Volume' in data.columns else 1.0
             self.model.vol_buffer.append(vol)
             
        # Calculate EMA 50 (Trend Filter)
        ema_50 = pd.Series(prices).ewm(span=50, adjust=False).mean().values
        
        print("Running prediction loop...")
        for i in range(split_idx, len(prices)):
            price = float(prices[i])
            ts = dates[i]
            trend = ema_50[i]
            
            # Create Quote (Simulating Live Feed)
            # Use Volume as proxy for size
            vol = float(data.iloc[i]['Volume']) if 'Volume' in data.columns else 1.0
            q = Quote(
                instrument_id=symbol,
                timestamp=ts,
                price=price, 
                bid_size=vol/2, # split for proxy
                ask_size=vol/2,
                source="sim"
            )
            
            # Predict
            pred = loop.run_until_complete(self.model.predict(q))
            
            if pred:
                # Logic: High Frequency Scalp
                # Filter: Only Long if Price > EMA 50 (Uptrend)
                if pred.expected_return > 0.004 and price > trend: 
                    signals.iloc[i, signals.columns.get_loc('signal')] = "BUY"
                    signals.iloc[i, signals.columns.get_loc('confidence')] = 0.9
                elif pred.expected_return < -0.004 and price < trend:
                    # Short logic enabled
                    signals.iloc[i, signals.columns.get_loc('signal')] = "SELL"
                    signals.iloc[i, signals.columns.get_loc('confidence')] = 0.9

        loop.close()
        return signals
