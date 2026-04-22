import asyncio
from typing import Optional
from common.types import TradeIntent

class SignalBus:
    """
    Async message bus for TradeIntents.
    Decouples Strategy (Producers) from Risk/Execution (Consumers).
    """
    def __init__(self):
        self._queue = asyncio.Queue()

    async def push(self, intent: TradeIntent):
        """Publish a new trade intent."""
        await self._queue.put(intent)

    async def pop(self) -> TradeIntent:
        """Wait for and retrieve the next intent."""
        return await self._queue.get()

    def empty(self) -> bool:
        return self._queue.empty()
