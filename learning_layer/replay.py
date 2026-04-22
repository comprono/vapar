import numpy as np
from typing import List, Tuple, Optional
from common.schemas.market_data import OrderBook
from common.types import TradeDirection

class OrderBookReplay:
    """
    Simulates execution against a historical Order Book.
    Addresses Gap #3: Realistic Slippage vs Random Walk.
    """
    
    def __init__(self, fee_pct: float = 0.001):
        self.fee_pct = fee_pct
        self.current_book: Optional[OrderBook] = None

    def update_book(self, book: OrderBook):
        self.current_book = book

    def match_order(self, direction: TradeDirection, size_qty: float) -> Tuple[float, float, float]:
        """
        Walks the book to fill the order.
        Returns: (Avg_Fill_Price, Total_Cost, Slippage_BasisPoints)
        """
        if not self.current_book:
            raise ValueError("No Order Book loaded for replay")

        # Select Correct Side
        # Buying -> Eat Asks from Lowest Up
        # Selling -> Eat Bids from Highest Down
        
        # Bids/Asks are typically [[price, size], [price, size]]
        # Assumed sorted: Bids Descending, Asks Ascending
        
        if direction == TradeDirection.LONG:
            liquidity_pool = self.current_book.asks
            side_mult = 1
        else:
            liquidity_pool = self.current_book.bids
            side_mult = -1
            
        remaining_qty = size_qty
        total_cost = 0.0
        weighted_price_sum = 0.0
        
        # Walk the book
        for price, depth_qty in liquidity_pool:
            if remaining_qty <= 0:
                break
                
            fill_qty = min(remaining_qty, depth_qty)
            cost = fill_qty * price
            
            total_cost += cost
            remaining_qty -= fill_qty
            weighted_price_sum += (fill_qty * price)
            
        # Check if fully filled
        if remaining_qty > 1e-9:
            # In a real replay, this might be a partial fill or reject.
            # For simplicity, we fill the rest at the last price + penalty or fail.
            # Let's assume infinite depth at last price for now + 10bps penalty
            last_price = liquidity_pool[-1][0]
            penalty = last_price * (1.001 if direction == TradeDirection.LONG else 0.999)
            
            fill_qty = remaining_qty
            cost = fill_qty * penalty
            
            total_cost += cost
            weighted_price_sum += (fill_qty * penalty)
            remaining_qty = 0

        avg_price = weighted_price_sum / size_qty
        
        # Calculate Slippage
        # Mid Price reference
        best_bid = self.current_book.bids[0][0]
        best_ask = self.current_book.asks[0][0]
        mid_price = (best_bid + best_ask) / 2.0
        
        if direction == TradeDirection.LONG:
             slippage_pct = (avg_price - mid_price) / mid_price
        else:
             slippage_pct = (mid_price - avg_price) / mid_price
             
        return avg_price, total_cost, slippage_pct * 10000 # returns Basis Points
