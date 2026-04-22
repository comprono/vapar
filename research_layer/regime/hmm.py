import numpy as np
from typing import Tuple, Dict, Optional
from sklearn.mixture import GaussianMixture
from dataclasses import dataclass

@dataclass
class RegimePrediction:
    regime_id: int
    regime_name: str
    probabilities: Dict[str, float]
    confidence: float

class ProbabilisticRegimeDetector:
    """
    Unsupervised Regime Detection using Gaussian Mixture Models (GMM).
    Replaces brittle if/else thresholds.
    
    Clusters market features (Volatility, Returns) into 'k' latent states.
    Example: 
      State 0: Low Vol, Positive Return (Bull)
      State 1: High Vol, Negative Return (Crash/Bear)
    """
    
    def __init__(self, n_components: int = 3, lookback_window: int = 252):
        self.n_components = n_components
        self.lookback_window = lookback_window
        self.model = GaussianMixture(n_components=n_components, covariance_type="full", random_state=42)
        self.is_fitted = False
        self.regime_map = {} # Map cluster ID to human name (e.g. 0 -> "LowVol")

    def fit(self, returns: np.ndarray, volatility: np.ndarray):
        """
        Train the GMM on historical data.
        Features: [Returns, Volatility]
        """
        X = np.column_stack([returns, volatility])
        self.model.fit(X)
        self.is_fitted = True
        self._name_regimes(X)

    def predict(self, current_return: float, current_vol: float) -> Optional[RegimePrediction]:
        """
        Predict the current regime probabilistically.
        """
        if not self.is_fitted:
            return None
        
        X_new = np.array([[current_return, current_vol]])
        
        # Get raw cluster probabilities
        probs = self.model.predict_proba(X_new)[0]
        state = np.argmax(probs)
        confidence = probs[state]
        
        # Map to human readable output
        regime_name = self.regime_map.get(state, f"Regime_{state}")
        
        probs_dict = {self.regime_map.get(i, f"Regime_{i}"): float(p) for i, p in enumerate(probs)}
        
        return RegimePrediction(
            regime_id=int(state),
            regime_name=regime_name,
            probabilities=probs_dict,
            confidence=confidence
        )

    def _name_regimes(self, X: np.ndarray):
        """
        Heuristic to label clusters based on their centroids.
        e.g., The cluster with highest Volatility is "HighVol".
        """
        means = self.model.means_
        # means shape: (n_components, n_features) -> [Ret, Vol]
        
        # 1. Identifiy High Volatility Regime
        vol_col_idx = 1
        sorted_by_vol = np.argsort(means[:, vol_col_idx])
        
        # Lowest Vol -> Calm/Bull usually
        # Highest Vol -> Crash/Crisis
        
        low_vol_idx = sorted_by_vol[0]
        high_vol_idx = sorted_by_vol[-1]
        
        self.regime_map[low_vol_idx] = "Low_Vol_Bull"
        self.regime_map[high_vol_idx] = "High_Vol_Crisis"
        
        # Middle ones
        for i in range(self.n_components):
            if i not in self.regime_map:
                self.regime_map[i] = "Neutral/Transition"
