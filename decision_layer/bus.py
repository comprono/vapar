import asyncio
from typing import AsyncGenerator
from common.schemas.trade_intent import TradeIntent

class SignalBus:
    """
    Async message bus transporting TradeIntents from
    Research Layer -> Decision Layer.
    """
    def __init__(self):
        self._queue = asyncio.Queue()
        self._running = True

    async def publish(self, intent: TradeIntent):
        """Publish a trade intent to the bus."""
        await self._queue.put(intent)

    async def subscribe(self) -> AsyncGenerator[TradeIntent, None]:
        """Consume intents from the bus."""
        while self._running:
            # Wait for next intent
            intent = await self._queue.get()
            yield intent
            self._queue.task_done()
            
    def stop(self):
        self._running = False
