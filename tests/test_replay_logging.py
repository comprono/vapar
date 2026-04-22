import unittest
from datetime import datetime
from learning_layer.replay import OrderBookReplay
from common.schemas.market_data import OrderBook
from common.types import TradeDirection

class TestOrderBookReplay(unittest.TestCase):
    def setUp(self):
        self.replay = OrderBookReplay()
        
        # Construct a fake book
        # Mid Price = 100.05
        # Asks: 100.10 (10), 100.20 (20), 100.50 (100)
        # Bids: 100.00 (10), 99.90 (20), 99.50 (100)
        
        self.fake_book = OrderBook(
            instrument_id="TEST/USDT",
            timestamp=datetime.now(),
            bids=[[100.00, 10.0], [99.90, 20.0], [99.50, 100.0]],
            asks=[[100.10, 10.0], [100.20, 20.0], [100.50, 100.0]],
            source="MOCK"
        )
        self.replay.update_book(self.fake_book)

    def test_small_buy_slippage(self):
        """Buying 5 units should fill at best ask (100.10)"""
        qty = 5.0
        avg_price, cost, slip_bps = self.replay.match_order(TradeDirection.LONG, qty)
        
        self.assertAlmostEqual(avg_price, 100.10)
        print(f"[Small Buy] Price: {avg_price:.2f}, Slippage: {slip_bps:.2f} bps")

    def test_large_buy_slippage(self):
        """Buying 20 units. 10 @ 100.10, 10 @ 100.20. Avg = 100.15"""
        qty = 20.0
        avg_price, cost, slip_bps = self.replay.match_order(TradeDirection.LONG, qty)
        
        expected_avg = (10 * 100.10 + 10 * 100.20) / 20.0
        self.assertAlmostEqual(avg_price, expected_avg)
        self.assertTrue(slip_bps > 0)
        print(f"[Large Buy] Price: {avg_price:.2f}, Slippage: {slip_bps:.2f} bps")

if __name__ == '__main__':
    unittest.main()
