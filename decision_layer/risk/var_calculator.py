import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from scipy import stats

class VaRCalculator:
    """
    Value-at-Risk calculator for portfolio risk management.
    Uses historical simulation and parametric methods.
    """
    
    def __init__(self, storage_adapter=None):
        self.storage = storage_adapter
        self.confidence_level = 0.95  # 95% confidence
        self.lookback_days = 30
    
    def calculate_position_var(
        self, 
        symbol: str, 
        quantity: float,
        current_price: float,
        historical_returns: Optional[List[float]] = None
    ) -> Dict:
        """
        Calculate VaR for a single position.
        Returns VaR in USD and as % of position value.
        """
        if historical_returns is None:
            # Use mock volatility if no historical data
            daily_volatility = 0.02  # 2% daily vol assumption
            historical_returns = np.random.normal(0, daily_volatility, 100)
        
        position_value = quantity * current_price
        
        # Historical simulation method
        returns_array = np.array(historical_returns)
        var_percentile = stats.scoreatpercentile(returns_array, (1 - self.confidence_level) * 100)
        
        # VaR = position value * VaR percentile
        var_usd = abs(position_value * var_percentile)
        var_pct = abs(var_percentile) * 100
        
        return {
            "symbol": symbol,
            "position_value": position_value,
            "var_usd": var_usd,
            "var_pct": var_pct,
            "confidence": self.confidence_level,
            "method": "historical_simulation"
        }
    
    def calculate_portfolio_var(
        self,
        positions: Dict[str, Dict],  # {symbol: {qty, price}}
        historical_data: Optional[Dict[str, List[float]]] = None
    ) -> Dict:
        """
        Calculate portfolio-level VaR accounting for correlations.
        
        Args:
            positions: Dict of {symbol: {"quantity": float, "price": float}}
            historical_data: Dict of {symbol: [returns]}
        
        Returns:
            Dict with portfolio VaR metrics
        """
        if not positions:
            return {
                "portfolio_var_usd": 0,
                "portfolio_var_pct": 0,
                "confidence": self.confidence_level
            }
        
        # Extract symbols
        symbols = list(positions.keys())
        
        # Build returns matrix
        if historical_data:
            returns_matrix = self._build_returns_matrix(symbols, historical_data)
        else:
            # Mock returns for demo
            returns_matrix = self._generate_mock_returns(symbols)
        
        # Calculate portfolio value
        portfolio_value = sum(
            pos["quantity"] * pos["price"] 
            for pos in positions.values()
        )
        
        # Calculate weights
        weights = np.array([
            (positions[sym]["quantity"] * positions[sym]["price"]) / portfolio_value
            for sym in symbols
        ])
        
        # Covariance matrix
        cov_matrix = np.cov(returns_matrix.T)
        
        # Portfolio variance
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
        portfolio_std = np.sqrt(portfolio_variance)
        
        # VaR using normal approximation
        z_score = stats.norm.ppf(1 - self.confidence_level)
        var_pct = abs(z_score * portfolio_std)
        var_usd = portfolio_value * var_pct
        
        # Also calculate diversification benefit
        individual_vars = []
        for sym in symbols:
            pos = positions[sym]
            pos_var = self.calculate_position_var(
                sym, 
                pos["quantity"], 
                pos["price"],
                historical_data.get(sym) if historical_data else None
            )
            individual_vars.append(pos_var["var_usd"])
        
        undiversified_var = sum(individual_vars)
        diversification_benefit = (undiversified_var - var_usd) / undiversified_var * 100
        
        return {
            "portfolio_value": portfolio_value,
            "portfolio_var_usd": var_usd,
            "portfolio_var_pct": var_pct * 100,
            "confidence": self.confidence_level,
            "method": "parametric_covariance",
            "diversification_benefit_pct": diversification_benefit,
            "num_positions": len(positions)
        }
    
    def _build_returns_matrix(
        self, 
        symbols: List[str], 
        historical_data: Dict[str, List[float]]
    ) -> np.ndarray:
        """Build returns matrix from historical data."""
        min_length = min(len(historical_data[sym]) for sym in symbols)
        
        return np.array([
            historical_data[sym][-min_length:] 
            for sym in symbols
        ])
    
    def _generate_mock_returns(self, symbols: List[str], n_samples: int = 100) -> np.ndarray:
        """Generate mock correlated returns for demo."""
        n_assets = len(symbols)
        
        # Create correlation matrix (0.3 correlation between assets)
        corr = np.full((n_assets, n_assets), 0.3)
        np.fill_diagonal(corr, 1.0)
        
        # Volatilities (2% daily for simplicity)
        vols = np.full(n_assets, 0.02)
        
        # Covariance matrix
        cov = np.outer(vols, vols) * corr
        
        # Generate multivariate normal returns
        returns = np.random.multivariate_normal(
            mean=np.zeros(n_assets),
            cov=cov,
            size=n_samples
        )
        
        return returns
    
    def check_var_limit(
        self,
        current_var_usd: float,
        proposed_trade_var: float,
        max_var_pct: float,
        portfolio_value: float
    ) -> bool:
        """
        Check if a proposed trade would exceed VaR limits.
        
        Returns:
            True if trade is safe, False if it exceeds limit
        """
        new_total_var = current_var_usd + proposed_trade_var
        var_pct = (new_total_var / portfolio_value) * 100
        
        is_safe = var_pct <= max_var_pct
        
        print(f"[VAR] Current: ${current_var_usd:.2f}, Proposed: +${proposed_trade_var:.2f}")
        print(f"[VAR] New Total: ${new_total_var:.2f} ({var_pct:.2f}%) | Limit: {max_var_pct}%")
        print(f"[VAR] {'✓ APPROVED' if is_safe else '✗ REJECTED'}")
        
        return is_safe
