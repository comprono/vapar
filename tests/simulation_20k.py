import yfinance as yf
import pandas as pd
import numpy as np

from backend.strategies.neural_net_strategy import NeuralNetStrategy

def run_simulation(symbol="BTC-USD", start_date="2024-01-01", end_date="2025-01-01", initial_capital=10.0):
    print(f"--- Starting Simulation: $10 -> $20K Challenge ---")
    print(f"Symbol: {symbol}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial Capital: ${initial_capital}")

    # 1. Fetch Data
    print("Downloading data...")
    data = yf.download(symbol, start=start_date, end=end_date, progress=False)

    if data.empty:
        print("Error: No data downloaded.")
        return

    # yfinance sometimes returns MultiIndex columns, flatten them if needed
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # 2. Run Strategy
    print("Running NeuralNet Strategy (this may take a moment)...")
    strategy = NeuralNetStrategy(window_size=10)
    signals = strategy.generate_signals(data, symbol)
    
    # 3. Simulate Account Growth
    balance = initial_capital
    position = 0 # 0 = cash, 1 = invested
    entry_price = 0.0
    equity_curve = []
    
    # Align signals with data
    # signals index should match data index
    
    # Fee assumption: 0.1% per trade
    fee_pct = 0.001 
    
    for i in range(len(data)):
        date = data.index[i]
        price = float(data['Close'].iloc[i])
        
        # Check signal
        if i < len(signals):
            sig = signals.iloc[i]['signal']
        else:
            sig = "HOLD"
            
        # Execute
        if sig == "BUY" and position == 0:
            # Buy All
            position = balance / price * (1 - fee_pct)
            balance = 0
            entry_price = price
            # print(f"[{date.date()}] BUY @ {price:.2f}")
            
        elif sig == "SELL" and position > 0:
            # Sell All
            balance = position * price * (1 - fee_pct)
            position = 0
            # print(f"[{date.date()}] SELL @ {price:.2f} -> Balance: ${balance:.2f}")
            
        # Calculate current equity
        current_equity = balance + (position * price)
        equity_curve.append(current_equity)

    final_equity = balance + (position * data['Close'].iloc[-1])
    roi = (final_equity - initial_capital) / initial_capital * 100
    
    print("-" * 30)
    print(f"Final Balance: ${final_equity:.2f}")
    print(f"Return: {roi:.2f}%")
    print("-" * 30)
    
    if final_equity > 20000:
        print("SUCCESS: REACHED $20K GOAL!")
    else:
        print("[WARN] Goal not reached. Need more volatility or better predictions.")

if __name__ == "__main__":
    # Using specific dates to ensure known volatility if possible
    run_simulation(symbol="BTC-USD", start_date="2023-01-01", end_date="2024-01-01", initial_capital=10.0)
