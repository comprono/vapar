import yfinance as yf
import pandas as pd
import numpy as np
import time
from backend.strategies.neural_net_strategy import NeuralNetStrategy

def run_simulation():
    symbol = "ETH-USD" # High volatility, 24/7
    print(f"--- High Frequency Scalper Simulation: $10 -> $20K ---")
    print(f"Target: ~1000 trades @ ~0.8%")
    
    # 1. Fetch 15m Data (requires recent data for yfinance 15m)
    # yfinance max 60 days for 15m
    print("Downloading 15m data (Last 14 days)...")
    data = yf.download(symbol, period="14d", interval="15m", progress=False)
    
    if data.empty:
        print("No data.")
        return
        
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    print(f"Loaded {len(data)} candles.")

    # 2. Run Strategy
    print("Initializing NeuralNet_Scalper...")
    strategy = NeuralNetStrategy(window_size=10)
    signals = strategy.generate_signals(data, symbol)
    
    # 3. Simulate High Frequency Compounding
    balance = 10.0
    position = 0
    trades = 0
    wins = 0
    
    fee = 0.0004 # 0.04% Futures Taker Fee
    leverage = 20.0 # 20x Leverage
    
    print(f"Leverage: {leverage}x | Fee: {fee*100}%")
    
    for i in range(len(data)):
        if i >= len(signals): break
        
        sig = signals.iloc[i]['signal']
        price = float(data['Close'].iloc[i])
        
        if position != 0:
            # Check SL/TP
            entry_val = entry_price
            current_val = price
            
            # Pct Change depends on direction
            if position > 0: # Long
                pct_change = (current_val - entry_val) / entry_val
            else: # Short
                pct_change = (entry_val - current_val) / entry_val
            
            # SL: -0.5% | TP: +1.0%
            if pct_change <= -0.005 or pct_change >= 0.01:
                # Close
                exit_val = abs(position) * price
                exit_fee = exit_val * fee
                
                if position > 0:
                     pnl = (price - entry_price) * position
                else:
                     pnl = (entry_price - price) * abs(position)
                     
                balance += pnl - exit_fee
                position = 0
                trades += 1
                reason = "TP" if pct_change > 0 else "SL"
                # print(f"{reason} @ {price:.2f} | Bal: {balance:.2f}")

        # BUY signal
        if sig == "BUY":
            if position == 0:
                # Open Long
                position = (balance * leverage) / price
                entry_fee = (balance * leverage) * fee
                balance -= entry_fee 
                entry_price = price
            elif position < 0:
                # Close Short (and Flip? No, just close for now)
                # Close Short
                exit_val = abs(position) * price
                exit_fee = exit_val * fee
                pnl = (entry_price - price) * abs(position)
                balance += pnl - exit_fee
                position = 0
                trades += 1
                
                # Flip to Long? Optional. Let's just close to be safe.
                # If we want to flip, we re-check balance and open.
                # But simplify: Signal closes opposite position.
            
        # SELL signal
        elif sig == "SELL":
            if position == 0:
                 # Open Short
                 # Size = (Balance * Leverage) / Price
                 # Stored as negative
                 size = (balance * leverage) / price
                 position = -size
                 entry_fee = (size * price) * fee
                 balance -= entry_fee
                 entry_price = price
                 
            elif position > 0:
                # Close Long
                exit_val = position * price
                exit_fee = exit_val * fee
                pnl = (price - entry_price) * position
                balance += pnl - exit_fee
                position = 0
                trades += 1
                
        if balance <= 0:
            print("LIQUIDATED!")
            break
            
    # Close final
    if position > 0:
        balance = position * data['Close'].iloc[-1]
        
    print("-" * 30)
    print(f"Final Balance: ${balance:.2f} (Start: $10)")
    print(f"Total Trades: {trades}")
    print("-" * 30)
    
    if balance > 100:
        print("Promising! 10x in 2 months (extrapolated).")
    else:
        print("Needs tuning. Scalping is hard.")

if __name__ == "__main__":
    run_simulation()
