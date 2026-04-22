import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class CorrelationAnalyzer:
    """
    Cross-asset correlation analyzer for portfolio risk management.
    Prevents over-concentration in correlated assets.
    """
    
    def __init__(self, min_diversification_score: float = 0.3):
        self.min_diversification = min_diversification_score
        self.correlation_cache: Dict[str, np.ndarray] = {}
    
    def compute_correlation(
        self, 
        returns_by_symbol: Dict[str, List[float]],
        window: int = 30
    ) -> np.ndarray:
        """
        Compute correlation matrix from returns.
        
        Args:
            returns_by_symbol: Dict of {symbol: [daily_returns]}
            window: Lookback window for correlation
        
        Returns:
            Correlation matrix (n_assets x n_assets)
        """
        symbols = list(returns_by_symbol.keys())
        n_assets = len(symbols)
        
        if n_assets == 0:
            return np.array([[]])
        
        # Build returns matrix
        returns_matrix = []
        min_length = min(len(returns_by_symbol[s]) for s in symbols)
        
        for symbol in symbols:
            recent_returns = returns_by_symbol[symbol][-min(window, min_length):]
            returns_matrix.append(recent_returns)
        
        # Handle case where we don't have enough data
        if min_length < 2:
            # Return identity matrix (no correlation)
            return np.eye(n_assets)
        
        # Compute correlation
        try:
            corr_matrix = np.corrcoef(returns_matrix)
            return corr_matrix
        except Exception as e:
            print(f"[CORRELATION] Calculation failed: {e}")
            return np.eye(n_assets)
    
    def diversification_score(
        self, 
        portfolio_weights: Dict[str, float],
        correlation_matrix: np.ndarray
    ) -> float:
        """
        Calculate portfolio diversification score.
        
        Score = 1 - (avg_correlation weighted by positions)
        Score of 1.0 = perfectly diversified
        Score of 0.0 = perfectly correlated
        
        Args:
            portfolio_weights: {symbol: weight (0-1)}
            correlation_matrix: Correlation matrix
        
        Returns:
            Diversification score (0-1)
        """
        symbols = list(portfolio_weights.keys())
        n_assets = len(symbols)
        
        if n_assets < 2:
            return 1.0  # Single asset is "diversified" by definition
        
        # Build weight vector
        weights = np.array([portfolio_weights[s] for s in symbols])
        
        # Portfolio variance = w^T * Corr * w
        portfolio_var = np.dot(weights, np.dot(correlation_matrix, weights))
        
        # Average variance (if uncorrelated)
        avg_var = np.sum(weights ** 2)
        
        # Diversification ratio
        if avg_var > 0:
            diversification = 1 - (portfolio_var - avg_var) / avg_var
            diversification = np.clip(diversification, 0, 1)
        else:
            diversification = 1.0
        
        return float(diversification)
    
    def find_correlated_clusters(
        self,
        symbols: List[str],
        correlation_matrix: np.ndarray,
        threshold: float = 0.7
    ) -> List[List[str]]:
        """
        Find clusters of highly correlated assets.
        
        Args:
            symbols: List of symbols
            correlation_matrix: Correlation matrix
            threshold: Correlation above this = same cluster
        
        Returns:
            List of clusters (each cluster is a list of symbols)
        """
        n_assets = len(symbols)
        visited = set()
        clusters = []
        
        for i in range(n_assets):
            if i in visited:
                continue
            
            cluster = [symbols[i]]
            visited.add(i)
            
            for j in range(i + 1, n_assets):
                if j in visited:
                    continue
                
                if abs(correlation_matrix[i, j]) > threshold:
                    cluster.append(symbols[j])
                    visited.add(j)
            
            if len(cluster) > 1:
                clusters.append(cluster)
        
        return clusters
    
    def check_diversification(
        self,
        current_portfolio: Dict[str, float],
        proposed_trade: Dict[str, float],
        returns_data: Optional[Dict[str, List[float]]] = None
    ) -> Dict:
        """
        Check if adding a trade maintains diversification.
        
        Args:
            current_portfolio: {symbol: position_value}
            proposed_trade: {symbol: trade_value}
            returns_data: Historical returns (optional)
        
        Returns:
            {
                "approved": bool,
                "current_score": float,
                "new_score": float,
                "reason": str
            }
        """
        # Normalize holdings to notional floats.
        normalized_current = {}
        for symbol, value in current_portfolio.items():
            if isinstance(value, dict):
                qty = float(value.get("quantity", 0.0))
                price = float(value.get("price", 0.0))
                normalized_current[symbol] = qty * price
            else:
                normalized_current[symbol] = float(value)

        # Combine current + proposed
        new_portfolio = normalized_current.copy()
        for symbol, value in proposed_trade.items():
            new_portfolio[symbol] = new_portfolio.get(symbol, 0) + value
        
        # Calculate weights
        total_value = sum(new_portfolio.values())
        if total_value == 0:
            return {"approved": True, "current_score": 1.0, "new_score": 1.0, "reason": "Empty portfolio"}
        
        new_weights = {s: v / total_value for s, v in new_portfolio.items()}
        
        # If no returns data, use heuristic correlation assumptions
        if not returns_data:
            corr_matrix = self._estimate_correlation(list(new_weights.keys()))
        else:
            corr_matrix = self.compute_correlation(returns_data)
        
        # Calculate diversification score
        new_score = self.diversification_score(new_weights, corr_matrix)
        
        # Check threshold
        approved = new_score >= self.min_diversification
        
        return {
            "approved": approved,
            "current_score": 1.0,  # Would need to calculate
            "new_score": new_score,
            "reason": f"Diversification score: {new_score:.2f}" if approved else f"Portfolio too concentrated ({new_score:.2f} < {self.min_diversification})"
        }
    
    def _estimate_correlation(self, symbols: List[str]) -> np.ndarray:
        """
        Estimate correlation based on asset type heuristics.
        """
        n = len(symbols)
        corr = np.eye(n)
        
        # Apply heuristic correlations
        for i in range(n):
            for j in range(i + 1, n):
                sym_i = symbols[i]
                sym_j = symbols[j]
                
                # Crypto assets are highly correlated
                if all(s in ["BTC", "ETH", "DOGE", "SOL"] for s in [sym_i, sym_j]):
                    corr[i, j] = corr[j, i] = 0.8
                # Sports bets are uncorrelated with each other
                elif sym_i.startswith("NBA_") and sym_j.startswith("NBA_"):
                    corr[i, j] = corr[j, i] = 0.1
                # Crypto and sports are uncorrelated
                elif (sym_i.startswith("NBA_") and sym_j in ["BTC", "ETH"]) or \
                     (sym_j.startswith("NBA_") and sym_i in ["BTC", "ETH"]):
                    corr[i, j] = corr[j, i] = 0.05
                # Default: moderate correlation
                else:
                    corr[i, j] = corr[j, i] = 0.3
        
        return corr
