import numpy as np
import pandas as pd
from typing import List, Deque, Optional, Any, Union
from collections import deque
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from research_layer.models.base import BaseModel, Prediction
from common.schemas.market_data import Quote
from research_layer.features.indicators import calculate_rsi, calculate_bollinger_bands

class MLPModel(BaseModel):
    def __init__(self, name: str = "MLP_Scalper", version: str = "2.1", window_size: int = 10):
        super().__init__(name, version)
        self.window_size = window_size
        
        # Features:
        # 1. Past 5 returns
        # 2. RSI
        # 3. BB %B
        # 4. Volume Change (New)
        # Total = 5 + 1 + 1 + 1 = 8
        self.input_dim = 8
        
        self.model = MLPRegressor(
            hidden_layer_sizes=(64, 32),
            activation='tanh', # Tanh often better for returns
            solver='adam',
            max_iter=500, 
            random_state=42,
            learning_rate_init=0.001
        )
        self.scaler = StandardScaler()
        
        self.price_buffer: Deque[float] = deque(maxlen=50) 
        self.vol_buffer: Deque[float] = deque(maxlen=50) # New buffer
        self.is_fitted = False

    async def train(self, data: Union[List[float], pd.DataFrame], targets: Optional[List[float]] = None):
        if isinstance(data, list):
            df = pd.DataFrame({'Close': data, 'Volume': [1.0]*len(data)}) # Mock volume
        else:
            df = data.copy()
            if 'Close' not in df.columns:
                 col = df.columns[0]
                 df['Close'] = df[col]
            if 'Volume' not in df.columns:
                 df['Volume'] = 1.0

        # Indicators
        df['Returns'] = df['Close'].pct_change()
        df['Vol_Chg'] = df['Volume'].pct_change().fillna(0)
        df['RSI'] = calculate_rsi(df['Close'], 14)
        _, _, df['BB_Pct'] = calculate_bollinger_bands(df['Close'], 20, 2)
        
        df.replace([np.inf, -np.inf], 0, inplace=True)
        df.dropna(inplace=True)
        
        if len(df) < self.window_size + 50:
            return

        X = []
        y = []
        
        lookback = 5
        
        # Vectorized-ish loop
        # Features: [Ret_t...Ret_t-4, RSI, BB, VolChg]
        
        for i in range(lookback, len(df) - 1):
            past_returns = df.iloc[i-lookback+1 : i+1]['Returns'].values
            curr_rsi = df.iloc[i]['RSI']
            curr_bb = df.iloc[i]['BB_Pct']
            curr_vol = df.iloc[i]['Vol_Chg']
            
            features = np.concatenate([past_returns, [curr_rsi, curr_bb, curr_vol]])
            target = df.iloc[i+1]['Returns']
            
            X.append(features)
            y.append(target)
            
        X = np.array(X)
        y = np.array(y)
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        print(f"[{self.name}] Trained on {len(X)} samples. Loss: {self.model.loss_:.6f}")

    async def predict(self, features: Any) -> Optional[Prediction]:
        if isinstance(features, Quote):
            quote = features
            self.price_buffer.append(float(quote.price))
            # Mock volume if not in quote, ideally Quote has volume? 
            # Review Quote schema... it has bid_size/ask_size but not volume of trade.
            # We'll use bid_size + ask_size as proxy or just 0 if missing.
            vol = (quote.bid_size or 0) + (quote.ask_size or 0)
            self.vol_buffer.append(vol)
            
            min_buffer = max(12, self.window_size + 2)
            if not self.is_fitted or len(self.price_buffer) < min_buffer:
                return None

            prices = list(self.price_buffer)
            vols = list(self.vol_buffer)
            if len(vols) < len(prices):
                vols = ([1.0] * (len(prices) - len(vols))) + vols
            
            df = pd.DataFrame({'Close': prices, 'Volume': vols})
            df['Returns'] = df['Close'].pct_change()
            df['Vol_Chg'] = df['Volume'].pct_change().fillna(0)
            rsi_window = min(14, max(5, len(df) - 1))
            bb_window = min(20, max(5, len(df)))
            df['RSI'] = calculate_rsi(df['Close'], rsi_window)
            _, _, df['BB_Pct'] = calculate_bollinger_bands(df['Close'], bb_window, 2)
            df.replace([np.inf, -np.inf], 0, inplace=True)
            
            last_idx = len(df) - 1
            if pd.isna(df.iloc[last_idx]['RSI']): return None

            lookback = 5
            past_returns = df.iloc[last_idx-lookback+1 : last_idx+1]['Returns'].values
            if len(past_returns) < lookback: return None
                
            curr_rsi = df.iloc[last_idx]['RSI']
            curr_bb = df.iloc[last_idx]['BB_Pct']
            curr_vol = df.iloc[last_idx]['Vol_Chg']
            
            feat_vec = np.concatenate([past_returns, [curr_rsi, curr_bb, curr_vol]]).reshape(1, -1)
            feat_scaled = self.scaler.transform(feat_vec)
            
            pred_return = self.model.predict(feat_scaled)[0]
            
            return Prediction(
                instrument_id=quote.instrument_id,
                timestamp=quote.timestamp,
                expected_return=pred_return,
                uncertainty=0.01,
                confidence_score=0.8,
                horizon_seconds=900, 
                meta_features={}
            )
        return None
