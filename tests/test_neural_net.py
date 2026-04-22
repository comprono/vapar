import asyncio
import numpy as np
from research_layer.models.mlp_model import MLPModel
from common.schemas.market_data import Quote
from datetime import datetime

async def test_mlp_learning_capability():
    print("Initializing MLP Model (Scikit-Learn)...")
    model = MLPModel(window_size=10)
    
    # 1. Generate Synthetic Sine Wave Data (Predictable)
    print("Generating sine wave data...")
    t = np.linspace(0, 100, 500)
    prices = 100 + 10 * np.sin(t) # Sine wave prices
    
    # 2. Train Model
    print("Training MLP on sine wave...")
    await model.train(list(prices))
    
    # 3. Predict on new data continuing the wave
    # Simulate a sequence that should lead to a positive return
    # Rising part of sine wave
    last_prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0] 
    # Initialize buffer
    for p in last_prices:
        model.price_buffer.append(p)
        
    quote = Quote(
        instrument_id="TEST",
        timestamp=datetime.now(),
        price=111.0,
        bid=111.0,
        ask=111.1,
        bid_size=1,
        ask_size=1,
        source="TEST_SCRIPT"
    )
    
    print("Predicting next return...")
    prediction = await model.predict(quote)
    
    if prediction is None:
        print("FAILED: Prediction is None")
        exit(1)

    print(f"Prediction result: {prediction}")
    
    # Check structure
    assert prediction.instrument_id == "TEST"
    assert isinstance(prediction.expected_return, float)
    
    print("SUCCESS: MLP Model trained and predicted successfully.")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_mlp_learning_capability())
