import numpy as np
import math
from typing import Optional, List
from datetime import datetime
from .base import BaseModel, Prediction

class NumpyTransformerLayer:
    """
    A lightweight, pure-numpy Single-Head Attention layer.
    Used as a fallback when heavy DL frameworks (Torch) fail in restricted envs.
    """
    def __init__(self, input_dim: int, d_model: int):
        self.d_model = d_model
        # Initialize weights (Xavier/Glorot)
        scale = np.sqrt(2.0 / (input_dim + d_model))
        self.W_q = np.random.randn(input_dim, d_model) * scale
        self.W_k = np.random.randn(input_dim, d_model) * scale
        self.W_v = np.random.randn(input_dim, d_model) * scale
        self.W_o = np.random.randn(d_model, d_model) * scale
        
        # Feed Forward weights
        self.W_ff1 = np.random.randn(d_model, d_model*4) * np.sqrt(2.0 / (d_model + d_model*4))
        self.W_ff2 = np.random.randn(d_model*4, d_model) * np.sqrt(2.0 / (d_model*4 + d_model))

    def forward(self, x: np.ndarray) -> np.ndarray:
        # x: (Seq_Len, Input_Dim)
        
        # 1. Project Q, K, V
        Q = np.dot(x, self.W_q) # (Seq, D)
        K = np.dot(x, self.W_k)
        V = np.dot(x, self.W_v)
        
        # 2. Scaled Dot-Product Attention
        # scores = Q . K^T / sqrt(d)
        scores = np.dot(Q, K.T) / np.sqrt(self.d_model)
        
        # Softmax
        # Stable softmax
        exp_scores = np.exp(scores - np.max(scores, axis=-1, keepdims=True))
        attn_weights = exp_scores / np.sum(exp_scores, axis=-1, keepdims=True)
        
        # Context = Weights . V
        context = np.dot(attn_weights, V) # (Seq, D)
        
        # Output Linear
        attn_out = np.dot(context, self.W_o)
        
        # Residual + Norm (Simplified: just Residual)
        # Assuming input_dim == d_model for residual, else skip or project. 
        # Here we just pass attn_out to FF.
        
        # 3. Feed Forward
        ff_hidden = np.maximum(0, np.dot(attn_out, self.W_ff1)) # ReLU
        ff_out = np.dot(ff_hidden, self.W_ff2)
        
        return ff_out # (Seq, D)

class TransformerModel(BaseModel):
    def __init__(self, name: str = "NumpyTransformer_v1", input_dim: int = 10):
        super().__init__(name, "1.0.0")
        self.d_model = 64
        # We assume input features are projected to d_model internally or we init layer with input_dim
        self.layer = NumpyTransformerLayer(input_dim, self.d_model)
        
        # Decoder Head
        self.head_mean = np.random.randn(self.d_model, 1) * 0.1
        self.head_logvar = np.random.randn(self.d_model, 1) * 0.1

    async def predict(self, features: np.ndarray) -> Optional[Prediction]:
        """
        Features: (Seq_Len, Input_Dim)
        """
        if features.shape[0] < 5:
            return None
            
        # Forward pass
        embeddings = self.layer.forward(features)
        
        # Pooling (Take last step)
        last_step = embeddings[-1] # (D_model,)
        
        # Decode
        expected_return = float(np.dot(last_step, self.head_mean).item())
        logvar = float(np.dot(last_step, self.head_logvar).item())
        
        uncertainty = math.sqrt(math.exp(logvar)) if logvar < 50 else 1.0 # Clip
        confidence = 1.0 / (1.0 + uncertainty * 10.0)

        return Prediction(
            instrument_id="TBD",
            timestamp=datetime.now(),
            expected_return=expected_return,
            uncertainty=uncertainty,
            confidence_score=confidence,
            horizon_seconds=60
        )

    async def train(self, data: List[np.ndarray], targets: List[float]):
        pass
