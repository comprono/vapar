import asyncio
from typing import List
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.core.config import settings
from backend.services.engine_service import engine

# NEW: Backtest imports
from backend.backtest.data_loader import DataLoader
from backend.backtest.engine import BacktestEngine
from backend.strategies.mean_reversion import MeanReversionStrategy

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Unified Multi-Market Autonomous Trading System API"
)

# Enable CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    engine.initialize()

@app.get("/")
async def root():
    return {"status": "System Online", "engine_status": engine.get_status()["status"]}

from backend.common.schemas.config import SystemConfig

@app.post("/api/config")
async def configure_engine(config: SystemConfig):
    """Configure the trading engine parameters."""
    engine.configure(config)
    return {"message": "Configuration updated successfully", "config": config}

@app.post("/api/engine/start")
async def start_engine(request: Request, background_tasks: BackgroundTasks):
    """Start the autonomous trading loop. Accepts optional JSON body { mode: 'SHADOW' | 'LIVE' }"""
    try:
        body = await request.json()
    except Exception:
        body = {}
    mode = str(body.get("mode", "SHADOW")).upper()
    if mode not in {"SHADOW", "LIVE"}:
        mode = "SHADOW"
    background_tasks.add_task(engine.start, mode=mode)
    return {"message": f"Engine starting in {mode} mode..."}

@app.post("/api/engine/stop")
async def stop_engine():
    """Stop the autonomous trading loop."""
    await engine.stop()
    return {"message": "Engine stopped."}

@app.get("/api/engine/status")
async def get_status():
    """Get real-time system state (quotes, trades, logs)."""
    return engine.get_status()

@app.post("/api/research/refresh")
async def refresh_research():
    """Force a new auto-research run and strategy selection."""
    return await engine.refresh_research()

@app.get("/api/research/status")
async def research_status():
    """Get last auto-research output and current active strategy."""
    return engine.get_research_status()

@app.get("/api/backtest/universes")
async def get_universes():
    """Get list of preset asset universes."""
    from backend.common.universes import UNIVERSES
    return UNIVERSES

@app.get("/api/backtest/reports")
async def list_reports():
    """List all saved backtest reports."""
    from backend.services.report_manager import report_manager
    return report_manager.list_reports()

@app.get("/api/backtest/reports/{report_id}")
async def get_report(report_id: str):
    """Get details of a specific report."""
    from backend.services.report_manager import report_manager
    try:
        return report_manager.get_report(report_id)
    except FileNotFoundError:
        return {"error": "Report not found"}

class BacktestRequest(BaseModel):
    symbols: List[str]
    start_date: str
    end_date: str
    strategy: str = "MeanReversion"
    initial_capital: float = 10000.0
    min_confidence: float = 0.65
    risk_per_trade: float = 0.02

@app.post("/api/backtest/optimize")
async def optimize_backtest(request: BacktestRequest):
    """
    Run hyper-parameter optimization to find the best strategy config.
    """
    try:
        from backend.backtest.data_loader import DataLoader
        from backend.backtest.optimizer import optimizer
        from backend.services.report_manager import report_manager
        
        # Load data
        loader = DataLoader()
        all_data = {}
        for symbol in request.symbols:
            try:
                all_data[symbol] = loader.load(symbol, request.start_date, request.end_date, interval="1d")
            except Exception:
                continue
                
        if not all_data:
            return {"error": "No data found for optimization."}
            
        # Run optimization
        results = optimizer.find_moonshot(all_data)
        
        if "error" in results:
            return results
            
        # Save report
        results["report_id"] = report_manager.save_report(results)
        
        return results
        
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.post("/api/backtest/run")
async def run_backtest(request: BacktestRequest):
    """
    Run a backtest on historical data for multiple symbols.
    """
    try:
        # Load data for all symbols
        loader = DataLoader()
        all_data = {}
        for symbol in request.symbols:
            try:
                all_data[symbol] = loader.load(symbol, request.start_date, request.end_date, interval="1d")
            except Exception as e:
                print(f"Failed to load data for {symbol}: {e}")
        
        if not all_data:
            return {"error": "No data found for any symbols requested."}
        
        # Create strategy
        if request.strategy == "MeanReversion":
            from backend.strategies.mean_reversion import MeanReversionStrategy
            strategy = MeanReversionStrategy()
        elif request.strategy == "Momentum":
            from backend.strategies.momentum import MomentumStrategy
            strategy = MomentumStrategy()
        elif request.strategy == "TrendFollower":
            from backend.strategies.trend_follower import TrendFollowerStrategy
            strategy = TrendFollowerStrategy()
        elif request.strategy == "Ensemble":
            from backend.strategies.ensemble import EnsembleStrategy
            strategy = EnsembleStrategy()
        elif request.strategy == "Test":
            from backend.strategies.test_strategy import AlwaysBuyStrategy
            strategy = AlwaysBuyStrategy()
        elif request.strategy == "NeuralNet":
            from backend.strategies.neural_net_strategy import NeuralNetStrategy
            strategy = NeuralNetStrategy()
        else:
            return {"error": f"Unknown strategy: {request.strategy}"}
        
        # Run backtest engine
        backtest_engine = BacktestEngine(initial_capital=request.initial_capital)
        results = backtest_engine.run_multi(
            strategy=strategy,
            all_data=all_data,
            min_confidence=request.min_confidence,
            risk_per_trade=request.risk_per_trade
        )
        
        # Save report
        from backend.services.report_manager import report_manager
        results["report_id"] = report_manager.save_report(results)
        
        return results
    
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}
