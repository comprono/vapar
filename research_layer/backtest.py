import asyncio
from typing import List, Dict
from data_layer.ingestors.base import BaseIngestor
from research_layer.models.base import BaseModel
from research_layer.allocator import PortfolioAllocator

class BacktestEngine:
    """
    Harness to run models against a data stream and
    evaluate the hypothetical portfolio performance.
    """
    def __init__(self, ingester: BaseIngestor, models: List[BaseModel], allocator: PortfolioAllocator):
        self.ingester = ingester
        self.models = models
        self.allocator = allocator
        self.results = []
        
    async def run(self, max_ticks: int = 100):
        print(f"Starting Backtest with {len(self.models)} models...")
        
        tick_count = 0
        async for quote in self.ingester.stream_quotes():
            if tick_count >= max_ticks:
                break
                
            # 1. Get predictions from all models
            predictions = []
            for model in self.models:
                p = await model.predict(quote)
                if p:
                    predictions.append(p)
            
            # 2. Run Allocator
            decisions = []
            if predictions:
                decisions = self.allocator.allocate(predictions)
                
            # 3. Log results (Mock fill assumption)
            if decisions:
                self.results.append({
                    "timestamp": quote.timestamp,
                    "quote": quote,
                    "predictions": len(predictions),
                    "decisions": decisions
                })
            
            tick_count += 1
            
        return self.generate_report()
        
    def generate_report(self):
        return {
            "total_ticks": len(self.results),
            "trades_generated": sum(len(r["decisions"]) for r in self.results),
            "sample_decisions": self.results[:5]
        }
