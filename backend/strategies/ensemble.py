import pandas as pd
from typing import List, Dict
from backend.strategies.base import Strategy, Signal
from backend.strategies.mean_reversion import MeanReversionStrategy
from backend.strategies.momentum import MomentumStrategy
from backend.strategies.trend_follower import TrendFollowerStrategy

class EnsembleStrategy(Strategy):
    """
    Meta-Strategy that aggregates multiple strategies.
    It runs RSI, MA Cross, and Bollinger Band strategies and 
    combines them using a weighted voting system.
    """
    
    def __init__(self, strategies: List[Strategy] = None):
        if not strategies:
            strategies = [
                MeanReversionStrategy(),
                MomentumStrategy(),
                TrendFollowerStrategy()
            ]
            
        super().__init__(
            name="EnsembleIntelligence",
            params={"n_strategies": len(strategies)}
        )
        self.strategies = strategies
        
    def analyze(self, data: pd.DataFrame, current_symbol: str) -> Signal:
        # Backward compatibility: Iterate
        signals = []
        for strat in self.strategies:
            try:
                sig = strat.analyze(data, current_symbol)
                signals.append(sig)
            except:
                pass
        
        # Simple Vote
        buy_votes = 0
        sell_votes = 0
        total_conf = 0
        reasons = []
        
        for sig in signals:
            if sig.action == "BUY" and sig.confidence > 0.6:
                buy_votes += 1
                total_conf += sig.confidence
                reasons.append(f"{sig.reason}")
            elif sig.action == "SELL" and sig.confidence > 0.6:
                sell_votes += 1
                total_conf += sig.confidence
                reasons.append(f"{sig.reason}")
                
        if buy_votes > sell_votes and buy_votes >= 2:
            avg_conf = total_conf / (buy_votes + sell_votes)
            return Signal(current_symbol, "BUY", min(avg_conf + 0.1, 0.95), " | ".join(reasons))
        elif sell_votes > buy_votes and sell_votes >= 2:
            avg_conf = total_conf / (buy_votes + sell_votes)
            return Signal(current_symbol, "SELL", min(avg_conf + 0.1, 0.95), " | ".join(reasons))
            
        return Signal(current_symbol, "HOLD", 0.0, "Consensus not reached")

    def generate_signals(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Vectorized Ensemble Execution."""
        # 1. Get raw signals from all sub-strategies
        all_signals = []
        for strat in self.strategies:
            strat_signals = strat.generate_signals(data, symbol)
            all_signals.append(strat_signals)
            
        # 2. Aggregate votes
        # We need to sum votes row-by-row
        buy_votes = pd.Series(0, index=data.index)
        sell_votes = pd.Series(0, index=data.index)
        total_conf = pd.Series(0.0, index=data.index)
        reasons = pd.Series("", index=data.index)
        
        for s_df in all_signals:
            # BUY Votes
            is_buy = (s_df['signal'] == "BUY") & (s_df['confidence'] > 0.6)
            buy_votes[is_buy] += 1
            if is_buy.any():
                total_conf[is_buy] += s_df.loc[is_buy, 'confidence']
            
            # SELL Votes
            is_sell = (s_df['signal'] == "SELL") & (s_df['confidence'] > 0.6)
            sell_votes[is_sell] += 1
            if is_sell.any():
                total_conf[is_sell] += s_df.loc[is_sell, 'confidence']
            
            # Accumulate Reasons
            mask = is_buy | is_sell
            if mask.any():
                new_reasons = s_df.loc[mask, 'reason']
                reasons[mask] = reasons[mask] + " | " + new_reasons

        # 3. Determine Final Signal
        final_signals = pd.DataFrame(index=data.index)
        final_signals['signal'] = "HOLD"
        final_signals['confidence'] = 0.0
        final_signals['reason'] = ""
        final_signals['symbol'] = symbol
        
        # Clean Reasons
        reasons = reasons.str.strip(" | ")
        
        # BUY Consensus
        buy_consensus = (buy_votes > sell_votes) & (buy_votes >= 2)
        total_votes = buy_votes + sell_votes
        
        if buy_consensus.any():
            final_signals.loc[buy_consensus, 'signal'] = "BUY"
            final_signals.loc[buy_consensus, 'confidence'] = (total_conf[buy_consensus] / total_votes[buy_consensus]).clip(upper=0.95)
            # Avoid setting with copy warning? Should be fine here
            final_signals.loc[buy_consensus, 'reason'] = reasons[buy_consensus]
        
        # SELL Consensus
        sell_consensus = (sell_votes > buy_votes) & (sell_votes >= 2)
        if sell_consensus.any():
            final_signals.loc[sell_consensus, 'signal'] = "SELL"
            final_signals.loc[sell_consensus, 'confidence'] = (total_conf[sell_consensus] / total_votes[sell_consensus]).clip(upper=0.95)
            final_signals.loc[sell_consensus, 'reason'] = reasons[sell_consensus]
        
        return final_signals
