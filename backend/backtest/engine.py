import pandas as pd
from typing import Dict, List
from datetime import datetime
from backend.strategies.base import Strategy, Signal
from backend.backtest.metrics import PerformanceMetrics

class BacktestEngine:
    """Bar-by-bar backtesting engine."""
    
    def __init__(self, initial_capital: float = 10000, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission  # 0.1% per trade
        
    def run(self, strategy: Strategy, data: pd.DataFrame, symbol: str, 
            min_confidence: float = 0.65, risk_per_trade: float = 0.02) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            strategy: Trading strategy to test
            data: DataFrame with OHLCV data
            symbol: Symbol being traded
            min_confidence: Minimum confidence to execute (0-1)
            risk_per_trade: Fraction of capital to risk per trade
        
        Returns:
            Dictionary with backtest results
        """
        print(f"[Backtest] Running {strategy.name} on {symbol} ({len(data)} bars)")
        print(f"[Backtest] Min confidence: {min_confidence}, Risk per trade: {risk_per_trade}")
        
        # Initialize portfolio state
        cash = self.initial_capital
        position = 0  # Number of shares/units held
        entry_price = 0
        entry_time = None
        entry_reason = ""
        
        trades = []
        equity_curve = []
        decisions = []
        
        buy_signals = 0
        sell_signals = 0
        hold_signals = 0
        
        # Bar-by-bar replay
        for i in range(50, len(data)):  # Start at bar 50 to have enough history
            current_bar = data.iloc[:i+1]  # All data up to current point
            current_price = current_bar['Close'].iloc[-1]
            current_time = current_bar.index[-1]
            
            # Generate signal
            signal = strategy.analyze(current_bar, symbol)
            
            # Track signal counts
            if signal.action == "BUY":
                buy_signals += 1
            elif signal.action == "SELL":
                sell_signals += 1
            else:
                hold_signals += 1
            
            # Calculate current portfolio value
            portfolio_value = cash + (position * current_price)
            equity_curve.append({
                "timestamp": current_time,
                "value": portfolio_value
            })
            
            # Decision logic
            decision = {
                "timestamp": current_time,
                "signal": signal.action,
                "confidence": signal.confidence,
                "reason": signal.reason,
                "price": current_price
            }
            
            # Execute trades
            if signal.action == "BUY" and signal.confidence >= min_confidence and position == 0:
                # Calculate position size
                risk_amount = portfolio_value * risk_per_trade
                shares = risk_amount / current_price
                
                if shares > 0.000001:  # Small minimum threshold
                    cost = shares * current_price * (1 + self.commission)
                    if cost <= cash:
                        cash -= cost
                        position = shares
                        entry_price = current_price
                        entry_time = current_time
                        entry_reason = signal.reason
                        
                        decision["action"] = "EXECUTED_BUY"
                        decision["shares"] = shares
                        decision["cost"] = cost
                        
                        print(f"  [{current_time}] BUY {shares:.6f} units @ ${current_price:.2f} (Conf: {signal.confidence:.2f})")
                    else:
                        print(f"  [{current_time}] REJECTED: Insufficient cash (${cash:.2f} < cost ${cost:.2f})")
                else:
                    print(f"  [{current_time}] REJECTED: Position size too small ({shares:.8f})")
            
            elif signal.action == "SELL" and signal.confidence >= min_confidence and position > 0:
                # Close position
                proceeds = position * current_price * (1 - self.commission)
                pnl = proceeds - (position * entry_price * (1 + self.commission))
                
                cash += proceeds
                
                trades.append({
                    "symbol": symbol,
                    "entry_time": entry_time,
                    "exit_time": current_time,
                    "entry_price": entry_price,
                    "exit_price": current_price,
                    "shares": position,
                    "pnl": pnl,
                    "return_pct": (pnl / (position * entry_price)) * 100,
                    "reason": entry_reason
                })
                
                decision["action"] = "EXECUTED_SELL"
                decision["shares"] = position
                decision["pnl"] = pnl
                
                print(f"  [{current_time}] SELL {position:.6f} @ ${current_price:.2f} | P&L: ${pnl:.2f}")
                
                position = 0
                entry_price = 0
                entry_time = None
                entry_reason = ""
            
            else:
                decision["action"] = "HOLD"
            
            decisions.append(decision)
        
        # Final portfolio value
        final_price = data['Close'].iloc[-1]
        final_value = cash + (position * final_price)
        
        # Calculate metrics
        equity_df = pd.DataFrame(equity_curve).set_index('timestamp')['value']
        metrics = PerformanceMetrics.calculate_all(equity_df, trades, self.initial_capital)
        
        print(f"[Backtest] Signal Summary: {buy_signals} BUY, {sell_signals} SELL, {hold_signals} HOLD")
        print(f"[Backtest] Complete - Final Value: ${final_value:.2f} | Total P&L: ${metrics['total_pnl']:.2f}")
        print(f"           Trades executed: {len(trades)} | Sharpe: {metrics['sharpe_ratio']} | Win Rate: {metrics['win_rate_pct']}%")
        
        return {
            "strategy": strategy.name,
            "symbol": symbol,
            "initial_capital": self.initial_capital,
            "final_value": round(final_value, 2),
            "metrics": metrics,
            "trades": trades,
            "equity_curve": equity_curve,
            "decisions": decisions[-100:],  # Last 100 decisions for UI
            "debug_info": {
                "total_bars": len(data),
                "bars_analyzed": len(data) - 50,
                "buy_signals": buy_signals,
                "sell_signals": sell_signals,
                "hold_signals": hold_signals,
                "min_confidence_used": min_confidence
            }
        }
    def run_multi(self, strategy: Strategy, all_data: Dict[str, pd.DataFrame], 
                  min_confidence: float = 0.65, risk_per_trade: float = 0.02,
                  stop_loss_pct: float = 0.05, take_profit_pct: float = 0.10) -> Dict:
        """
        Run backtest on multiple symbols simultaneously with SHARED CASH.
        This resolves the frequency/limit issues by allowing any symbol to trade if cash is available.
        """
        n_symbols = len(all_data)
        if n_symbols == 0:
            return {"error": "No data provided"}
            
        print(f"[Backtest] Starting Portfolio Simulation (Shared Cash: ${self.initial_capital})")
        
        # Create unified timeline
        all_indices = []
        for df in all_data.values():
            all_indices.extend(df.index.tolist())
        global_timeline = sorted(list(set(all_indices)))
        
        # Initial bar buffer (ensure enough data for MA/RSI etc)
        start_idx = 50
        if len(global_timeline) <= start_idx:
            return {"error": "Insufficient data timeline for simulation buffer"}
            
        cash = self.initial_capital
        # 0. Pre-compute Signals
        print("[Backtest] Vectorizing signals for all symbols...")
        # ... (pre-computation code remains same) ...
        
        # Risk Management State
        stop_loss_pct = 0.05  # Default 5% stop loss
        take_profit_pct = 0.10 # Default 10% take profit
        
        # Adaptive Learning State
        loss_streak = {s: 0 for s in all_data}
        is_blacklisted = {s: False for s in all_data}
        
        print(f"[Backtest] Signal vectorization complete. Starting execution loop ({len(global_timeline)} bars)...")
        
        # Core Simulation Loop
        for i in range(start_idx, len(global_timeline)):
            current_time = global_timeline[i]
            total_equity = cash
            
            # 1. Update Equity & Check Exits (SL/TP)
            active_buys = []
            active_sells = []
            
            # Check existing positions for SL/TP
            # We iterate through active positions first
            active_position_symbols = [s for s, pos in positions.items() if pos > 0]
            
            for symbol in active_position_symbols:
                if current_time in all_data[symbol].index:
                    current_bar = all_data[symbol].loc[current_time]
                    current_price = current_bar['Close']
                    entry = entry_prices[symbol]
                    
                    # Check SL/TP (Using High/Low would be more accurate, using Close for speed/simplicity)
                    # Stop Loss
                    if current_price <= entry * (1 - stop_loss_pct):
                        active_sells.append((symbol, 1.0, "Triggered Stop-Loss", current_price))
                        # Learning: Penalize this asset
                        loss_streak[symbol] += 1
                        if loss_streak[symbol] >= 3:
                            is_blacklisted[symbol] = True
                            # print(f"  [Learning] {symbol} blacklisted due to 3 consecutive losses.")
                            
                    # Take Profit
                    elif current_price >= entry * (1 + take_profit_pct):
                        active_sells.append((symbol, 1.0, "Triggered Take-Profit", current_price))
                        # Learning: Reset streak on win
                        loss_streak[symbol] = 0
            
            # 2. Process New Signals (from pre-computed)
            for symbol, sig_df in precomputed_signals.items():
                if is_blacklisted[symbol]: continue # Skip blacklisted assets
                
                if current_time in sig_df.index:
                    sig_row = sig_df.loc[current_time]
                    price = all_data[symbol].loc[current_time, 'Close']
                    
                    # Update equity for tracking (approximate)
                    if positions[symbol] > 0:
                        total_equity += positions[symbol] * price
                    
                    action = sig_row['signal']
                    if action == "HOLD": continue
                    
                    # If we haven't already decided to sell via SL/TP...
                    if action == "SELL" and positions[symbol] > 0:
                        # Don't double sell
                        if not any(s == symbol for s, _, _, _ in active_sells):
                           active_sells.append((symbol, sig_row['confidence'], sig_row['reason'], price))
                           
                    elif action == "BUY" and positions[symbol] == 0:
                        active_buys.append((symbol, sig_row['confidence'], sig_row['reason'], price))
            
            # Record Equity Curve
            equity_curve.append({"timestamp": current_time, "value": total_equity})

            # Execute SELLS first to free up cash
            for symbol, conf, reason, price in active_sells:
                if conf >= min_confidence and positions[symbol] > 0:
                    proceeds = positions[symbol] * price * (1 - self.commission)
                    pnl = proceeds - (positions[symbol] * entry_prices[symbol] * (1 + self.commission))
                    
                    cash += proceeds
                    
                    trade_obj = {
                        "symbol": symbol,
                        "entry_time": entry_times[symbol],
                        "exit_time": current_time,
                        "entry_price": entry_prices[symbol],
                        "exit_price": price,
                        "shares": positions[symbol],
                        "pnl": pnl,
                        "return_pct": (pnl / (positions[symbol] * entry_prices[symbol])) * 100,
                        "reason": entry_reasons[symbol]
                    }
                    trades.append(trade_obj)
                    
                    symbol_stats[symbol]["pnl"] += pnl
                    symbol_stats[symbol]["trades"] += 1
                    if pnl > 0: symbol_stats[symbol]["wins"] += 1
                    
                    positions[symbol] = 0
                    entry_prices[symbol] = 0
                    entry_times[symbol] = None

            # Execute BUYS (sorted by confidence)
            active_buys.sort(key=lambda x: x[1], reverse=True)
            
            for symbol, conf, reason, price in active_buys:
                if conf >= min_confidence and positions[symbol] == 0:
                    # Risk management
                    risk_amount = total_equity * risk_per_trade
                    shares = risk_amount / price
                    
                    if shares > 0.000001:
                        cost = shares * price * (1 + self.commission)
                        if cost <= cash:
                            cash -= cost
                            positions[symbol] = shares
                            entry_prices[symbol] = price
                            entry_times[symbol] = current_time
                            entry_reasons[symbol] = reason
        
        # Calculate Final Metrics
        equity_df = pd.DataFrame(equity_curve).set_index('timestamp')['value']
        global_metrics = PerformanceMetrics.calculate_all(equity_df, trades, self.initial_capital)
        
        # Breakdown results by symbol
        symbol_results = {}
        for s in all_data:
            s_trades = [t for t in trades if t['symbol'] == s]
            s_win_rate = (symbol_stats[s]["wins"] / symbol_stats[s]["trades"] * 100) if symbol_stats[s]["trades"] > 0 else 0
            
            # Simple approximation for each symbol since they share cash
            symbol_results[s] = {
                "total_pnl": round(symbol_stats[s]["pnl"], 2),
                "total_return_pct": round(symbol_stats[s]["pnl"] / (self.initial_capital/n_symbols) * 100, 2), # Relative to initial split
                "win_rate_pct": round(s_win_rate, 2),
                "total_trades": symbol_stats[s]["trades"],
                "sharpe_ratio": 0.0 # Individual sharpe is complex in shared pool
            }
            
        print(f"[Backtest] Simulation Complete. Total P&L: ${global_metrics['total_pnl']:.2f}")
        
        return {
            "strategy": strategy.name,
            "symbols": list(all_data.keys()),
            "initial_capital": self.initial_capital,
            "final_value": round(equity_df.iloc[-1], 2),
            "metrics": global_metrics,
            "trades": sorted(trades, key=lambda x: x['entry_time']),
            "equity_curve": equity_curve,
            "symbol_results": symbol_results
        }
