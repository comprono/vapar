import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BaseStorage
from common.schemas.market_data import Quote, Trade

class CSVStorage(BaseStorage):
    """
    Simpler CSV storage implementation for testing.
    Keeps separate files for Quotes and Trades.
    """
    def __init__(self, root_dir: str = "data_store"):
        self.root_dir = root_dir
        self._files = {}
        self._writers = {}

    async def connect(self):
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)

    async def save_quote(self, quote: Quote):
        await self.save_quotes_batch([quote])

    async def save_quotes_batch(self, quotes: List[Quote]):
        if not quotes:
            return
        
        # Partition by day to mimic standard data engineering practices
        date_str = quotes[0].timestamp.strftime("%Y%m%d")
        filename = os.path.join(self.root_dir, f"quotes_{date_str}.csv")
        
        if filename not in self._writers:
            is_new = not os.path.exists(filename)
            f = open(filename, "a", newline="")
            self._files[filename] = f
            writer = csv.writer(f)
            self._writers[filename] = writer
            if is_new:
                # Write header based on Quote fields
                writer.writerow(list(quotes[0].model_dump().keys()))
        
        writer = self._writers[filename]
        for q in quotes:
            writer.writerow(list(q.model_dump().values()))

    async def save_trade(self, trade: Trade):
        # Similar logic for trades
        date_str = trade.timestamp.strftime("%Y%m%d")
        filename = os.path.join(self.root_dir, f"trades_{date_str}.csv")
        
        if filename not in self._writers:
            is_new = not os.path.exists(filename)
            f = open(filename, "a", newline="")
            self._files[filename] = f
            writer = csv.writer(f)
            self._writers[filename] = writer
            if is_new:
                writer.writerow(list(trade.model_dump().keys()))
        
        self._writers[filename].writerow(list(trade.model_dump().values()))

    def query_quotes(self, instrument_id: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        return [] # Not implemented for CSV

    def save_audit_event(self, event_type: str, data: Dict[str, Any], actor: str = "system", model_version: Optional[str] = None, session_id: Optional[str] = None):
        pass # Skip for now

    def close(self):
        for f in self._files.values():
            f.close()
