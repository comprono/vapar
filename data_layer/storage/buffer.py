import asyncio
from typing import List
from common.schemas.market_data import Quote
from data_layer.storage.base import BaseStorage

class QuoteBuffer:
    """
    Batch buffer for efficient quote storage.
    Accumulates quotes and flushes in batches to reduce DB writes.
    """
    
    def __init__(self, storage: BaseStorage, batch_size: int = 100, flush_interval: float = 5.0):
        self.storage = storage
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer: List[Quote] = []
        self._flush_task = None
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start auto-flush timer."""
        self._flush_task = asyncio.create_task(self._auto_flush())
    
    async def stop(self):
        """Stop buffer and flush remaining quotes."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
    
    async def add(self, quote: Quote):
        """Add quote to buffer, auto-flush if batch size reached."""
        async with self._lock:
            self.buffer.append(quote)
            
            if len(self.buffer) >= self.batch_size:
                await self._flush_now()
    
    async def flush(self):
        """Manually flush buffer."""
        async with self._lock:
            await self._flush_now()
    
    async def _flush_now(self):
        """Internal flush (no lock)."""
        if not self.buffer:
            return
        
        try:
            await self.storage.save_quotes_batch(self.buffer)
            count = len(self.buffer)
            self.buffer.clear()
            print(f"[BUFFER] Flushed {count} quotes")
        except Exception as e:
            print(f"[BUFFER] Flush failed: {e}")
    
    async def _auto_flush(self):
        """Periodic auto-flush."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[BUFFER] Auto-flush error: {e}")
