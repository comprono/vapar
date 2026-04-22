from abc import ABC, abstractmethod
from typing import List, Optional, Deque
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from common.schemas.market_data import Quote, OrderBook

@dataclass
class Prediction:
    """
    Standardized probabilistic output from any model.
    """
    instrument_id: str
    timestamp: datetime
    expected_return: float        # E[R]
    uncertainty: float           # Variance/StdDev of prediction
    confidence_score: float      # Model's self-assessed calibration (0-1)
    horizon_seconds: int         # How far out is this prediction valid?
    meta_features: dict = None   # Debug info

class BaseModel(ABC):
    """
    Interface for all predictive models (Transformer, LSTM, etc.).
    """
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    @abstractmethod
    async def predict(self, features: np.ndarray) -> Optional[Prediction]:
        """
        Produce a prediction from a feature vector.
        Features shape: (Sequence_Len, Feature_Dim)
        """
        pass

    @abstractmethod
    async def train(self, data: List[np.ndarray], targets: List[float]):
        """
        Online or Offline training interface.
        """
        pass
