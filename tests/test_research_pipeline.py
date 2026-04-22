import asyncio
import numpy as np
from datetime import datetime
from research_layer.models.transformer import TransformerModel
from research_layer.regime.hmm import ProbabilisticRegimeDetector
from research_layer.allocator.meta_model import PortfolioAllocator
from common.logger import get_logger

logger = get_logger("TestResearchLayer")

async def main():
    logger.info("Starting Research Layer Integration Test...")
    
    # 1. Initialize Models
    transformer = TransformerModel(input_dim=10) # 10 features
    regime_detector = ProbabilisticRegimeDetector(n_components=2)
    allocator = PortfolioAllocator()
    
    # 2. Fake Data Generation (Batch of 50 timestamps)
    # Features: [Price, Returns, Vol, OBI, Spread, ...]
    X = np.random.randn(50, 10).astype(np.float32)
    
    # Train Regime Detector (Unsupervised)
    returns = X[:, 1]
    vol = np.abs(X[:, 2])
    regime_detector.fit(returns, vol)
    logger.info("Regime Detector trained.")
    
    # 3. Inference Loop
    logger.info("Running Inference...")
    
    # A. Get current market state
    current_ret = 0.01
    current_vol = 0.02
    current_regime = regime_detector.predict(current_ret, current_vol)
    
    logger.info(f"Detected Regime: {current_regime.regime_name} (Conf: {current_regime.confidence:.2f})")
    
    # B. Get Signal from Transformer
    # Input shape (Seq_Len, Features)
    features_seq = X[-20:] # Last 20 steps
    prediction = await transformer.predict(features_seq)
    
    if prediction:
        prediction.instrument_id = "BTC/USDT" # Manually attach ID for test
        logger.info(f"Signal: E[R]={prediction.expected_return:.4f}, Uncert={prediction.uncertainty:.4f}")
        
    # C. Allocate
    if prediction:
        allocations = allocator.allocate([prediction], current_regime)
        logger.info(f"Proposed Allocations: {allocations}")
    
    logger.info("Test Complete.")

if __name__ == "__main__":
    asyncio.run(main())
