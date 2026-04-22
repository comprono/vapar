from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float
    last_updated: datetime
    unrealized_pnl: float = 0.0
    
    def update_pnl(self, current_price: float):
        """Calculate unrealized PnL based on current market price."""
        self.unrealized_pnl = (current_price - self.avg_price) * self.quantity

class PositionTracker:
    """
    Tracks all open positions and calculates portfolio metrics.
    """
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.total_capital: float = 0.0
        self.cash: float = 0.0
    
    def initialize(self, starting_capital: float):
        """Set initial capital."""
        self.total_capital = starting_capital
        self.cash = starting_capital
        print(f"[POSITION] Initialized with ${starting_capital:,.2f}")
    
    def update_position(
        self, 
        symbol: str, 
        quantity: float, 
        price: float,
        side: str
    ):
        """
        Update position after a trade.
        For buys: increase position, decrease cash
        For sells: decrease position, increase cash
        """
        if side.lower() == 'buy':
            cost = quantity * price
            
            if symbol in self.positions:
                # Average up
                pos = self.positions[symbol]
                total_qty = pos.quantity + quantity
                new_avg = ((pos.quantity * pos.avg_price) + cost) / total_qty
                pos.quantity = total_qty
                pos.avg_price = new_avg
                pos.last_updated = datetime.now()
            else:
                # New position
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=price,
                    last_updated=datetime.now()
                )
            
            self.cash -= cost
            print(f"[POSITION] BUY {quantity} {symbol} @ ${price:.2f} | Cash: ${self.cash:,.2f}")
        
        else:  # sell
            proceeds = quantity * price
            
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos.quantity -= quantity
                pos.last_updated = datetime.now()
                
                # Close position if quantity is zero
                if pos.quantity <= 0.0001:
                    del self.positions[symbol]
            
            self.cash += proceeds
            print(f"[POSITION] SELL {quantity} {symbol} @ ${price:.2f} | Cash: ${self.cash:,.2f}")
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Retrieve current position for a symbol."""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Return all open positions."""
        return self.positions.copy()
    
    def calculate_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate total portfolio value (cash + positions).
        """
        positions_value = 0.0
        
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                market_price = current_prices[symbol]
                pos.update_pnl(market_price)
                positions_value += pos.quantity * market_price
            else:
                # Use last known price if current unavailable
                positions_value += pos.quantity * pos.avg_price
        
        total_value = self.cash + positions_value
        return total_value
    
    def get_portfolio_summary(self, current_prices: Dict[str, float]) -> Dict:
        """Generate portfolio summary including PnL."""
        total_value = self.calculate_portfolio_value(current_prices)
        total_pnl = total_value - self.total_capital
        pnl_pct = (total_pnl / self.total_capital * 100) if self.total_capital > 0 else 0
        
        return {
            "cash": self.cash,
            "positions_value": total_value - self.cash,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "pnl_pct": pnl_pct,
            "num_positions": len(self.positions),
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_price": p.avg_price,
                    "current_price": current_prices.get(p.symbol, p.avg_price),
                    "unrealized_pnl": p.unrealized_pnl
                }
                for p in self.positions.values()
            ]
        }
