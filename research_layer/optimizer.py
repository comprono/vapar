import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass  
class PortfolioAllocation:
    """Optimized portfolio weights."""
    weights: Dict[str, float]  # {symbol: weight}
    expected_return: float
    expected_risk: float
    sharpe_ratio: float

class PortfolioOptimizer:
    """
    Mean-Variance Portfolio Optimizer (Markowitz).
    Finds optimal asset weights given expected returns and risks.
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self.max_weight = 0.4  # No single asset > 40%
        self.min_weight = 0.0
    
    def optimize(
        self,
        opportunities: List[Dict],
        covariance_matrix: Optional[np.ndarray] = None
    ) -> PortfolioAllocation:
        """
        Optimize portfolio weights.
        
        Args:
            opportunities: List of {symbol, expected_return, confidence}
            covariance_matrix: Asset covariance matrix (optional, will estimate if not provided)
        
        Returns:
            PortfolioAllocation with optimal weights
        """
        if not opportunities:
            return PortfolioAllocation(
                weights={},
                expected_return=0,
                expected_risk=0,
                sharpe_ratio=0
            )
        
        symbols = [opp['symbol'] for opp in opportunities]
        expected_returns = np.array([opp.get('expected_return', 0) for opp in opportunities])
        confidences = np.array([opp.get('confidence', 0.5) for opp in opportunities])
        
        # Adjust returns by confidence
        adjusted_returns = expected_returns * confidences
        
        # Estimate covariance if not provided
        if covariance_matrix is None:
            # Use simplified approach: assume constant correlation
            n_assets = len(symbols)
            volatilities = np.array([0.02] * n_assets)  # 2% daily vol
            correlation = 0.3  # Assume 30% correlation
            
            cov_matrix = np.outer(volatilities, volatilities) * correlation
            np.fill_diagonal(cov_matrix, volatilities ** 2)
        else:
            cov_matrix = covariance_matrix
        
        # Optimize using simplified approach (no scipy.optimize to avoid dependency)
        weights = self._simple_optimization(adjusted_returns, cov_matrix)
        
        # Calculate portfolio metrics
        portfolio_return = np.dot(weights, expected_returns)
        portfolio_risk = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
        
        weight_dict = {symbols[i]: float(weights[i]) for i in range(len(symbols))}
        
        return PortfolioAllocation(
            weights=weight_dict,
            expected_return=float(portfolio_return),
            expected_risk=float(portfolio_risk),
            sharpe_ratio=float(sharpe)
        )
    
    def _simple_optimization(self, returns: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray:
        """
        Simplified optimization (replaces quadratic programming).
        Uses risk-adjusted returns for weighting.
        """
        n_assets = len(returns)
        
        # Calculate Sharpe ratio for each asset
        variances = np.diag(cov_matrix)
        asset_sharpes = (returns - self.risk_free_rate) / np.sqrt(variances)
        asset_sharpes = np.maximum(asset_sharpes, 0)  # Only positive Sharpe
        
        # Weight by Sharpe ratio
        if asset_sharpes.sum() == 0:
            # Equal weight if all negative Sharpe
            weights = np.ones(n_assets) / n_assets
        else:
            weights = asset_sharpes / asset_sharpes.sum()
        
        # Apply constraints
        weights = np.minimum(weights, self.max_weight)
        weights = weights / weights.sum()  # Renormalize
        
        return weights
    
    def rebalance_needed(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        threshold: float = 0.05
    ) -> bool:
        """
        Check if portfolio needs rebalancing.
        
        Args:
            current_weights: Current allocation
            target_weights: Optimal allocation
            threshold: Rebalance if any weight differs by more than this
        
        Returns:
            True if rebalancing needed
        """
        for symbol in target_weights:
            current = current_weights.get(symbol, 0)
            target = target_weights[symbol]
            
            if abs(current - target) > threshold:
                return True
        
        return False
