import json
import os
from typing import List, Any
from .base import BaseStorage
from common.schemas.market_data import Quote, Trade

class FileStorage(BaseStorage):
    """
    Simple file-based storage for local development.
    Appends JSON lines to files.
    """
    def __init__(self, root_dir: str = "data_store"):
        self.root_dir = root_dir
        
    async def connect(self):
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)
            
    async def save_quotes(self, quotes: List[Quote]):
        with open(f"{self.root_dir}/quotes.jsonl", "a") as f:
            for q in quotes:
                f.write(q.model_dump_json() + "\n")

    async def save_trades(self, trades: List[Trade]):
        with open(f"{self.root_dir}/trades.jsonl", "a") as f:
            for t in trades:
                f.write(t.model_dump_json() + "\n")
                
    async def save_blob(self, key: str, data: Any):
        path = f"{self.root_dir}/blobs/{key}"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(str(data))
