from learning_layer.performance import PerformanceAnalytics
from learning_layer.registry import ModelRegistry
from learning_layer.loop import OptimizationLoop

def main():
    print("Starting Learning Layer Integration Test...")
    
    # 1. Setup
    analytics = PerformanceAnalytics()
    registry = ModelRegistry()
    loop = OptimizationLoop(analytics, registry)
    
    model_name = "test_model_v1"
    registry.register_model(model_name, "1.0.0", {"type": "test"})
    
    # 2. Simulate Feedback (Wins)
    print("\n--- Simulating 3 Winning Trades ---")
    for i in range(3):
        loop.process_feedback(f"trade_{i}", model_name, pnl=100.0)
        
    status = registry.get_model_status(model_name)
    print(f"Score after wins: {status['score']} (Status: {status['status']})")
    
    # 3. Simulate Feedback (Losses - leading to Probation)
    print("\n--- Simulating 10 Losing Trades ---")
    for i in range(10):
        loop.process_feedback(f"trade_bad_{i}", model_name, pnl=-100.0)
        
    status = registry.get_model_status(model_name)
    print(f"Score after losses: {status['score']} (Status: {status['status']})")
    
    print("\nTest Complete.")

if __name__ == "__main__":
    main()
