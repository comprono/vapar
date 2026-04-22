import yfinance as yf
import pandas as pd
import numpy as np
import random
import asyncio
from typing import Dict, List
from backend.strategies.neural_net_strategy import NeuralNetStrategy

# Mock Sports Adapter for Simulation Speed
class SimSportsAdapter:
    def __init__(self):
        self.win_rate = 0.55 # 55% Win Rate (Professional Level)
        self.avg_odds = 1.91 # -110 American Odds
    
    def get_opportunities(self):
        """Returns list of available bets: (id, odds, ev)"""
        # Simulate 5 bets available per day approximately
        # In 15m intervals, that's rare.
        # Let's say 2% chance per 15m interval to find a value bet.
        if random.random() < 0.05: 
            return [{
                "id": f"BET_{random.randint(1000,9999)}",
                "odds": self.avg_odds,
                "confidence": 0.6 # High confidence
            }]
        return []

    def resolve_bet(self, bet) -> float:
        """Returns PnL multiplier (e.g. 1.91 or 0)"""
        # Sim outcome based on win rate
        if random.random() < self.win_rate:
            return bet['odds']
        return 0.0

async def train_models(strategies: Dict[str, NeuralNetStrategy], data_map: Dict[str, pd.DataFrame]):
    print("Training models...")
    loop = asyncio.get_event_loop()
    for symbol, strat in strategies.items():
        data = data_map[symbol]
        # Train on first 30% of data
        split_idx = int(len(data) * 0.3)
        train_df = data.iloc[:split_idx].copy()
        print(f"[{symbol}] Training on {len(train_df)} candles...")
        await strat.model.train(train_df)
        
        # Prime buffer
        prices = data['Close'].values
        # Fill buffer with last 50 prices and vol
        for i in range(split_idx-50, split_idx):
             strat.model.price_buffer.append(float(prices[i]))
             vol = float(data.iloc[i]['Volume']) if 'Volume' in data.columns else 1.0
             strat.model.vol_buffer.append(vol)

def run_simulation():
    print("--- Multi-Asset & Sports Portfolio: $10 -> $20K ---")
    
    # 1. Setup Assets
    crypto_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"]
    # Adjust symbols for yfinance if needed
    
    # 2. Fetch Data
    print("Downloading 15m data (Last 14 days)...")
    data_map = {}
    min_len = 999999
    
    for sym in crypto_symbols:
        try:
            df = yf.download(sym, period="14d", interval="15m", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if len(df) > 100:
                data_map[sym] = df
                min_len = min(min_len, len(df))
                print(f"Loaded {sym}: {len(df)} candles")
            else:
                print(f"Skipping {sym}: Not enough data")
        except Exception as e:
            print(f"Error loading {sym}: {e}")

    if not data_map:
        print("No data.")
        return

    # Align data lengths (simple truncation)
    for sym in data_map:
        data_map[sym] = data_map[sym].iloc[-min_len:]
    
    # 3. Initialize Strategies
    strategies = {}
    for sym in data_map:
        strategies[sym] = NeuralNetStrategy(window_size=10)
        
    sports = SimSportsAdapter()
    
    # 4. Train Models
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(train_models(strategies, data_map))
    
    # 5. Simulation Loop
    balance = 10.0
    positions = {sym: 0.0 for sym in data_map} # Size in units
    entry_prices = {sym: 0.0 for sym in data_map}
    active_bets = [] # List of pending sports bets
    
    crypto_leverage = 20.0
    crypto_fee = 0.0004
    
    split_idx = int(min_len * 0.3)
    common_index = data_map[list(data_map.keys())[0]].index
    
    trades = 0
    
    print(f"Starting Simulation from {common_index[split_idx]}...")
    
    for i in range(split_idx, min_len):
        # A. Resolve Sports Bets (assume they resolve in 2 hours / 8 steps, or random)
        # Simplify: Resolve immediately next step for simulation speed (or 4 steps)
        resolved_bets = []
        for bet in active_bets:
            bet['timer'] -= 1
            if bet['timer'] <= 0:
                payout_mult = sports.resolve_bet(bet)
                payout = bet['amount'] * payout_mult
                balance += payout
                # print(f"[SPORTS] Bet {bet['id']} Result: {payout:.2f} (Wager: {bet['amount']:.2f})")
                resolved_bets.append(bet)
                trades += 1
                
        for bet in resolved_bets:
            active_bets.remove(bet)
            
        # B. Crypto Logic
        for sym, strategy in strategies.items():
            df = data_map[sym]
            price = float(df['Close'].iloc[i])
            ts = df.index[i]
            
            # Trend
            # Calculate EMA online? Or pre-calc
            # Use pre-calc for speed
            # ema = df['Close'].ewm(span=50).mean() # this is full series
            # We need the value at i
            # Doing full ewm every step is slow. Let's approx or pre-calc.
            # Pre-calc:
            pass # See pre-calc below loop
            
        # Wait, optim: Pre-calc trend for all assets
        # Doing it inside loop is bad. 
        
    # RESTART LOOP Structure for efficiency
    # Pre-calc EMAs
    ema_map = {}
    for sym, df in data_map.items():
        ema_map[sym] = df['Close'].ewm(span=50, adjust=False).mean().values

    for i in range(split_idx, min_len):
        # 1. Sports Resolution
        resolved_bets = []
        for bet in active_bets:
            bet['timer'] -= 1
            if bet['timer'] <= 0:
                payout = bet['amount'] * sports.resolve_bet(bet)
                balance += payout
                resolved_bets.append(bet)
                trades += 1
        for bet in resolved_bets: active_bets.remove(bet)

        # 2. Crypto Updates
        for sym, strategy in strategies.items():
            df = data_map[sym]
            price = float(df['Close'].iloc[i])
            vol = float(df['Volume'].iloc[i]) if 'Volume' in df.columns else 1.0
            ts = df.index[i]
            trend = ema_map[sym][i]
            
            # Predict
            # Create Quote
            from common.schemas.market_data import Quote
            q = Quote(id=sym, instrument_id=sym, timestamp=ts, price=price, bid_size=vol/2, ask_size=vol/2, source="sim")
            
            pred = loop.run_until_complete(strategy.model.predict(q))
            
            # Logic
            pos = positions[sym]
            
            # Manage Open Position
            if pos != 0:
                 entry = entry_prices[sym]
                 pct = (entry - price) / entry if pos < 0 else (price - entry) / entry
                 
                 # Tight SL/TP
                 if pct <= -0.005 or pct >= 0.015:
                     # Close
                     val = abs(pos) * price
                     fee = val * crypto_fee
                     pnl = (entry - price) * abs(pos) if pos < 0 else (price - entry) * pos
                     balance += pnl - fee
                     positions[sym] = 0
                     trades += 1
            
            # Open New?
            if pred and positions[sym] == 0:
                # Allocation: Aggressive for small accounts
                # If balance < 50, use 25% or min $2
                if balance < 50:
                    alloc = max(2.5, balance * 0.25)
                    if alloc > balance: alloc = balance * 0.95 # Safety
                else:
                    alloc = balance * 0.20
                
                if alloc > 0.5: # Min bet $0.50
                    if pred.expected_return > 0.004 and price > trend:
                         # Long
                         size = (alloc * crypto_leverage) / price
                         fee = (alloc * crypto_leverage) * crypto_fee
                         balance -= fee
                         positions[sym] = size
                         entry_prices[sym] = price
                         # print(f"OPEN LONG {sym}")
                    elif pred.expected_return < -0.004 and price < trend:
                         # Short
                         size = (alloc * crypto_leverage) / price
                         fee = (alloc * crypto_leverage) * crypto_fee
                         balance -= fee
                         positions[sym] = -size
                         entry_prices[sym] = price
                         # print(f"OPEN SHORT {sym}")

        # 3. Sports Opportunities
        bets = sports.get_opportunities()
        if bets:
             for bet in bets:
                 # Alloc 10% for sports on small account
                 wager = balance * 0.10
                 if wager < 1.0: wager = 1.0 # Min $1 sports bet
                 
                 if balance > wager:
                     balance -= wager
                     bet['amount'] = wager
                     bet['timer'] = 8 # 2 hours approx
                     active_bets.append(bet)
                     # print(f"Placed Sports Bet: ${wager:.2f}")

        # Liquidation Check
        if balance < 1.0 and all(p == 0 for p in positions.values()) and not active_bets:
            print("BUSTED!")
            break

    # Final tally
    equity = balance
    for sym, pos in positions.items():
        if pos != 0:
            price = float(data_map[sym]['Close'].iloc[-1])
            entry = entry_prices[sym]
            pnl = (entry - price) * abs(pos) if pos < 0 else (price - entry) * pos
            equity += pnl

    # Add active bets (at cost)
    for bet in active_bets:
         equity += bet['amount']

    print("-" * 30)
    print(f"Final Equity: ${equity:.2f}")
    print(f"Total Trades: {trades}")
    print("-" * 30)

if __name__ == "__main__":
    run_simulation()
