import numpy as np
import pandas as pd
from typing import List, Dict

class TechnicalFeatures:
    """
    Technical indicator calculations for feature engineering.
    All functions assume price data is sorted oldest to newest.
    """
    
    @staticmethod
    def calculate_returns(prices: np.ndarray) -> np.ndarray:
        """Simple returns."""
        return np.diff(prices) / prices[:-1]
    
    @staticmethod
    def calculate_log_returns(prices: np.ndarray) -> np.ndarray:
        """Log returns."""
        return np.diff(np.log(prices))
    
    @staticmethod
    def calculate_sma(prices: np.ndarray, window: int) -> float:
        """Simple Moving Average."""
        if len(prices) < window:
            return prices[-1] if len(prices) > 0 else 0
        return np.mean(prices[-window:])
    
    @staticmethod
    def calculate_ema(prices: np.ndarray, span: int) -> float:
        """Exponential Moving Average."""
        if len(prices) == 0:
            return 0
        if len(prices) < span:
            return np.mean(prices)
        
        # Simple EMA calculation
        alpha = 2 / (span + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema
    
    @staticmethod
    def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
        """Relative Strength Index."""
        if len(prices) < period + 1:
            return 50.0  # Neutral
        
        returns = np.diff(prices)
        gains = returns.copy()
        losses = returns.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, float]:
        """MACD indicator."""
        if len(prices) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0}
        
        ema_fast = TechnicalFeatures.calculate_ema(prices, fast)
        ema_slow = TechnicalFeatures.calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        
        # Simplified signal line (would need full history for proper EMA)
        signal_line = macd_line * 0.9  # Approximation
        histogram = macd_line - signal_line
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: np.ndarray, window: int = 20, num_std: float = 2.0) -> Dict[str, float]:
        """Bollinger Bands."""
        if len(prices) < window:
            mid = prices[-1] if len(prices) > 0 else 0
            return {"upper": mid, "middle": mid, "lower": mid, "width": 0}
        
        recent = prices[-window:]
        middle = np.mean(recent)
        std = np.std(recent)
        
        upper = middle + (num_std * std)
        lower = middle - (num_std * std)
        width = (upper - lower) / middle if middle > 0 else 0
        
        return {
            "upper": upper,
            "middle": middle,
            "lower": lower,
            "width": width,
            "percent_b": (prices[-1] - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
        }
    
    @staticmethod
    def calculate_volatility(prices: np.ndarray, window: int = 30) -> float:
        """Historical volatility (annualized)."""
        if len(prices) < 2:
            return 0.0
        
        returns = TechnicalFeatures.calculate_returns(prices)
        recent_returns = returns[-window:] if len(returns) >= window else returns
        
        daily_vol = np.std(recent_returns)
        annualized_vol = daily_vol * np.sqrt(252)  # Assuming daily data
        return annualized_vol
    
    @staticmethod
    def calculate_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Average True Range."""
        if len(closes) < 2:
            return 0.0
        
        # Simplified ATR using only closes if highs/lows not available
        true_ranges = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i] if len(highs) > i else closes[i] - closes[i-1],
                abs(highs[i] - closes[i-1]) if len(highs) > i else 0,
                abs(lows[i] - closes[i-1]) if len(lows) > i else 0
            )
            true_ranges.append(tr)
        
        if len(true_ranges) < period:
            return np.mean(true_ranges) if true_ranges else 0.0
        
        return np.mean(true_ranges[-period:])
    
    @staticmethod
    def calculate_momentum(prices: np.ndarray, period: int = 10) -> float:
        """Price momentum."""
        if len(prices) < period + 1:
            return 0.0
        
        return (prices[-1] - prices[-period-1]) / prices[-period-1] if prices[-period-1] > 0 else 0
    
    @staticmethod
    def calculate_all_features(prices: List[float], volumes: Optional[List[float]] = None) -> Dict[str, float]:
        """
        Calculate all technical features at once.
        """
        prices_array = np.array(prices)
        
        features = {
            # Price-based
            "current_price": prices_array[-1] if len(prices_array) > 0 else 0,
            "sma_20": TechnicalFeatures.calculate_sma(prices_array, 20),
            "sma_50": TechnicalFeatures.calculate_sma(prices_array, 50),
            "sma_200": TechnicalFeatures.calculate_sma(prices_array, 200),
            "ema_12": TechnicalFeatures.calculate_ema(prices_array, 12),
            "ema_26": TechnicalFeatures.calculate_ema(prices_array, 26),
            
            # Momentum
            "rsi": TechnicalFeatures.calculate_rsi(prices_array),
            "momentum_10": TechnicalFeatures.calculate_momentum(prices_array, 10),
            "momentum_20": TechnicalFeatures.calculate_momentum(prices_array, 20),
            
            # Volatility
            "volatility_30": TechnicalFeatures.calculate_volatility(prices_array, 30),
            
            # Derived
            "price_vs_sma20": (prices_array[-1] - TechnicalFeatures.calculate_sma(prices_array, 20)) / TechnicalFeatures.calculate_sma(prices_array, 20) if TechnicalFeatures.calculate_sma(prices_array, 20) > 0 else 0,
            "price_vs_sma50": (prices_array[-1] - TechnicalFeatures.calculate_sma(prices_array, 50)) / TechnicalFeatures.calculate_sma(prices_array, 50) if TechnicalFeatures.calculate_sma(prices_array, 50) > 0 else 0,
        }
        
        # MACD
        macd = TechnicalFeatures.calculate_macd(prices_array)
        features.update({
            "macd": macd["macd"],
            "macd_signal": macd["signal"],
            "macd_histogram": macd["histogram"]
        })
        
        # Bollinger Bands
        bb = TechnicalFeatures.calculate_bollinger_bands(prices_array)
        features.update({
            "bb_upper": bb["upper"],
            "bb_middle": bb["middle"],
            "bb_lower": bb["lower"],
            "bb_width": bb["width"],
            "bb_percent": bb["percent_b"]
        })
        
        return features
