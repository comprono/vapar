from typing import Dict, Deque, Optional, Union
from collections import deque
import numpy as np
from common.schemas.market_data import Quote, OrderBook

class FeatureStore:
    """
    Real-time Feature Server.
    Calculates and stores Technical & Microstructure features from the stream.
    Used by Research Layer (Layer 2) to feed models.
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        # Dictionary mapping symbol -> Deque of feature vectors
        self._history: Dict[str, Deque[Dict[str, float]]] = {}
        # Dictionary mapping symbol -> last MidPrice (for diffs)
        self._last_price: Dict[str, float] = {}

    def push(self, data: Union[Quote, OrderBook]):
        """
        Ingest new MarketData, calculate features, and update history.
        """
        symbol = data.instrument_id
        if symbol not in self._history:
            self._history[symbol] = deque(maxlen=self.window_size)
        
        # Calculate Microstructure Features (Gap #1)
        features = self._calculate_features(data)
        
        self._history[symbol].append(features)
        self._last_price[symbol] = features.get("mid_price", 0.0)

    def get_features(self, symbol: str, n: int = 1) -> Optional[np.ndarray]:
        """
        Get last N feature vectors for a symbol as a Numpy array.
        Returns: Shape (N, num_features)
        """
        if symbol not in self._history or len(self._history[symbol]) < n:
            return None
        
        # Convert list of dicts to numpy array
        recent = list(self._history[symbol])[-n:]
        
        # Ensure consistent key order
        keys = sorted(recent[0].keys())
        matrix = [[item[k] for k in keys] for item in recent]
        
        return np.array(matrix, dtype=np.float32)

    def _calculate_features(self, data: Union[Quote, OrderBook]) -> Dict[str, float]:
        """
        Compute features from raw Level 2 data.
        """
        feats = {}
        
        if isinstance(data, OrderBook):
            # L2 Features
            best_bid = data.bids[0][0] if data.bids else 0.0
            best_ask = data.asks[0][0] if data.asks else 0.0
            best_bid_vol = data.bids[0][1] if data.bids else 0.0
            best_ask_vol = data.asks[0][1] if data.asks else 0.0
            
            mid_price = (best_bid + best_ask) / 2 if (best_bid and best_ask) else 0.0
            feats["mid_price"] = mid_price
            
            # Order Book Imbalance (OBI)
            total_vol = best_bid_vol + best_ask_vol
            feats["obi"] = (best_bid_vol - best_ask_vol) / total_vol if total_vol > 0 else 0.0
            
            # Spread
            feats["spread"] = best_ask - best_bid
            
            # Market Depth (Top 5 levels simple sum)
            bid_depth = sum(b[1] for b in data.bids[:5])
            ask_depth = sum(a[1] for a in data.asks[:5])
            feats["depth_imbalance"] = (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0.0
            
        elif isinstance(data, Quote):
            # L1 Features
            mid_price = data.price
            feats["mid_price"] = mid_price
            feats["obi"] = 0.0 # Cannot calc from simple quote
            feats["spread"] = (data.ask - data.bid) if (data.ask and data.bid) else 0.0
            feats["depth_imbalance"] = 0.0

        else:
            mid_price = 0.0
            feats["mid_price"] = 0.0

        # Returns
        prev_price = self._last_price.get(data.instrument_id, mid_price)
        if prev_price > 0:
            feats["log_return"] = np.log(mid_price / prev_price) if mid_price > 0 else 0.0
        else:
            feats["log_return"] = 0.0

        return feats
