import pandas as pd
from typing import Dict, List, Any, Optional
from backend.backtest.engine import BacktestEngine
from backend.strategies.ensemble import EnsembleStrategy
from backend.strategies.mean_reversion import MeanReversionStrategy
from backend.strategies.momentum import MomentumStrategy
from backend.strategies.trend_follower import TrendFollowerStrategy

class HyperOptimizer:
    """Explores parameter space to find high-return strategy configurations."""
    
    def __init__(self, initial_capital: float = 10.0):
        self.initial_capital = initial_capital
        
    def find_moonshot(self, all_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Iterates through multiple strategy configurations to find the best performer.
        Target: Maximize terminal profit.
        """
        best_results = None
        highest_pnl = -float('inf')
        
        # Define search space
        # We try different strategy types and different risk/confidence combos
        strategies = [
            ("Ensemble", EnsembleStrategy()),
            ("TrendFollower_Aggr", TrendFollowerStrategy(window=10, num_std=1.5)),
            ("Momentum_Fast", MomentumStrategy(short_window=3, long_window=10)),
            ("MeanReversion_Sens", MeanReversionStrategy(rsi_period=7, overbought=65, oversold=35))
        ]
        
        confidence_thresholds = [0.55, 0.65]
        risk_levels = [0.05, 0.10]
        stop_loss_settings = [0.02, 0.05, 0.08] # 2%, 5%, 8%
        take_profit_settings = [0.05, 0.10, 0.15] # 5%, 10%, 15%
        
        print(f"[Optimizer] Starting Hyper-Search on {len(all_data)} symbols...")
        
        total_runs = len(strategies) * len(confidence_thresholds) * len(risk_levels) * len(stop_loss_settings) * len(take_profit_settings)
        current_run = 0
        
        for strat_name, strategy in strategies:
            for conf in confidence_thresholds:
                for risk in risk_levels:
                    for sl in stop_loss_settings:
                        for tp in take_profit_settings:
                            current_run += 1
                            # Optimization: Skip invalid R:R ratios (e.g. risking 5% to make 2%)
                            if tp <= sl: continue
                            
                            print(f"[Optimizer] Run {current_run}/{total_runs}: {strat_name} | Conf={conf} | Risk={risk} | SL={sl} | TP={tp}")
                            
                            try:
                                engine = BacktestEngine(initial_capital=self.initial_capital)
                                results = engine.run_multi(
                                    strategy=strategy,
                                    all_data=all_data,
                                    min_confidence=conf,
                                    risk_per_trade=risk,
                                    stop_loss_pct=sl,
                                    take_profit_pct=tp
                                )
                                
                                pnl = results['metrics']['total_pnl']
                                # Selection Criteria: High PnL but MUST be profitable
                                if pnl > highest_pnl:
                                    highest_pnl = pnl
                                    best_results = results
                                    best_results["optimized_params"] = {
                                        "strategy_type": strat_name,
                                        "confidence_threshold": conf,
                                        "risk_per_trade": risk,
                                        "stop_loss_pct": sl,
                                        "take_profit_pct": tp
                                    }
                            except Exception as e:
                                print(f"[Optimizer] Run failed: {e}")
                                continue
                        
        print(f"[Optimizer] Optimization Complete. Best P&L: ${highest_pnl:.2f}")
        return best_results or {"error": "No profitable configuration found."}

optimizer = HyperOptimizer()
