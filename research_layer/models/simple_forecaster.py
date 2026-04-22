import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from research_layer.features.technical import TechnicalFeatures

@dataclass
class Prediction:
    """Model prediction with uncertainty."""
    expected_return: float
    uncertainty: float  # Standard deviation
    confidence: float  # 0-1 score
    features_used: Dict[str, float]

class SimpleForecaster:
    """
    Simplified probabilistic forecaster (replaces LSTM for now).
    Uses technical features + momentum for predictions.
    
    Note: This is a placeholder. A real LSTM would require:
    - PyTorch/TensorFlow installation
    - Training data preparation
    - Model training pipeline
    - Saved model weights
    
    This version uses heuristics to demonstrate the prediction interface.
    """
    
    def __init__(self):
        self.lookback = 50
        self.model_version = "simple_v1"
    
    def predict(self, prices: List[float], volumes: Optional[List[float]] = None) -> Prediction:
        """
        Generate probabilistic forecast.
        
        Args:
            prices: Historical prices
            volumes: Optional volume data
        
        Returns:
            Prediction with expected return, uncertainty, and confidence
        """
        if len(prices) < self.lookback:
            return Prediction(
                expected_return=0.0,
                uncertainty=0.05,
                confidence=0.1,
                features_used={}
            )
        
        # Calculate features
        features = TechnicalFeatures.calculate_all_features(prices, volumes)
        
        # Heuristic-based prediction (mimics ML model output)
        expected_return = self._predict_return(features)
        uncertainty = self._estimate_uncertainty(features)
        confidence = self._calculate_confidence(features, uncertainty)
        
        return Prediction(
            expected_return=expected_return,
            uncertainty=uncertainty,
            confidence=confidence,
            features_used=features
        )
    
    def _predict_return(self, features: Dict[str, float]) -> float:
        """
        Predict expected return using feature-based heuristics.
        """
        # Momentum-based prediction
        momentum_signal = (
            features.get('momentum_10', 0) * 0.4 +
            features.get('momentum_20', 0) * 0.3 +
            features.get('macd_histogram', 0) * 0.3
        )
        
        # Trend confirmation
        trend_multiplier = 1.0
        if features.get('price_vs_sma50', 0) > 0 and features.get('rsi', 50) > 50:
            trend_multiplier = 1.2  # Bullish
        elif features.get('price_vs_sma50', 0) < 0 and features.get('rsi', 50) < 50:
            trend_multiplier = 0.8  # Bearish
        
        # Base prediction (capped)
        raw_prediction = momentum_signal * trend_multiplier
        expected_return = np.clip(raw_prediction, -0.05, 0.05)  # Cap at ±5%
        
        return float(expected_return)
    
    def _estimate_uncertainty(self, features: Dict[str, float]) -> float:
        """
        Estimate prediction uncertainty based on volatility.
        """
        volatility = features.get('volatility_30', 0.02)
        bb_width = features.get('bb_width', 0.1)
        
        # Higher volatility = higher uncertainty
        uncertainty = volatility * 0.5 + bb_width * 0.5
        uncertainty = np.clip(uncertainty, 0.01, 0.10)  # 1-10%
        
        return float(uncertainty)
    
    def _calculate_confidence(self, features: Dict[str, float], uncertainty: float) -> float:
        """
        Calculate prediction confidence based on signal strength.
        """
        # Strong RSI signals increase confidence
        rsi = features.get('rsi', 50)
        rsi_strength = 0.0
        if rsi > 70 or rsi < 30:  # Overbought/oversold
            rsi_strength = 0.3
        
        # MACD confirmation
        macd_hist = abs(features.get('macd_histogram', 0))
        macd_strength = min(macd_hist * 10, 0.3)
        
        # Trend strength
        price_vs_sma = abs(features.get('price_vs_sma50', 0))
        trend_strength = min(price_vs_sma * 2, 0.2)
        
        # Lower uncertainty = higher confidence
        uncertainty_penalty = (0.1 - uncertainty) / 0.1 * 0.2
        
        # Combine signals
        confidence = (
            0.3 +  # Base confidence
            rsi_strength +
            macd_strength +
            trend_strength +
            uncertainty_penalty
        )
        
        confidence = np.clip(confidence, 0.1, 0.95)
        return float(confidence)
    
    def get_model_info(self) -> Dict:
        """Return model metadata."""
        return {
            "model_type": "SimpleForecaster",
            "version": self.model_version,
            "features_count": 20,
            "lookback_period": self.lookback,
            "note": "Heuristic-based placeholder for LSTM"
        }
