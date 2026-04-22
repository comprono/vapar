import asyncio
import os
from datetime import datetime
from typing import Dict, Any

# Core Layers
from backend.common.schemas.config import SystemConfig
from backend.data_layer.ingestors.live import YahooIngestor
from backend.layers.strategy_intelligence import StrategyIntelligence
from backend.layers.portfolio_engine import PortfolioEngine
from backend.services.karpathy_auto_research import KarpathyAutoResearch

# Phase 1: Infrastructure (using SQLite)
from data_layer.storage.sqlite import SQLiteStorage
from decision_layer.adapters.binance_adapter import BinanceAdapter
from decision_layer.adapters.sports_adapter import SportsAdapter
from decision_layer.adapters.registry import AdapterRegistry
from decision_layer.position_tracker import PositionTracker
from decision_layer.risk import RiskCommittee, VaRCalculator
from backend.services.audit_service import AuditService
from decision_layer.gatekeeper import ExecutionGatekeeper
from common.schemas.trade_intent import TradeIntent

# Phase 2: Intelligence
from research_layer.cached_regime_detector import CachedRegimeDetector
from research_layer.models import SimpleForecaster
from research_layer.optimizer import PortfolioOptimizer
from research_layer.correlation import CorrelationAnalyzer

class EngineService:
    """
    Production Engine Service (Phase 1 Complete).
    
    Features:
    - TimescaleDB persistence
    - Paper trading with Binance
    - VaR-based risk management
    - Position tracking
    - Immutable audit trail
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EngineService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def initialize(self):
        if self.initialized:
            return
            
        print("[ENGINE] Initializing Production Engine (Phase 1+2)...")
        
        # Config
        self.config = SystemConfig(
            capital_base=10000.0, 
            risk_tolerance_pct=0.01, 
            active_markets=["BTC", "ETH", "SPY"]
        )
        
        # Database (SQLite - no Docker required!)
        db_path = os.getenv("DB_PATH", "trading.db")
        self.storage = SQLiteStorage(db_path)
        
        # Data Ingestion
        self.market_layer = YahooIngestor()
        
        # Strategy & Portfolio
        self.auto_research = KarpathyAutoResearch()
        self.strategy_layer = StrategyIntelligence()
        self.portfolio_layer = PortfolioEngine()
        self.portfolio_layer.update_constraints(
            self.config.capital_base,
            self.config.risk_tolerance_pct,
            self.config.min_confidence,
        )
        
        # Phase 2: Intelligence Components
        self.regime_detector = CachedRegimeDetector(ttl_seconds=60)
        self.forecaster = SimpleForecaster()
        self.portfolio_optimizer = PortfolioOptimizer()
        self.correlation_analyzer = CorrelationAnalyzer()
        
        # Phase 3: Multi-Market Support
        self.adapter_registry = AdapterRegistry()
        self.exchange_adapter = BinanceAdapter()  # Crypto
        self.sports_adapter = SportsAdapter(mode="paper")
        
        # Register adapters
        self.adapter_registry.register("crypto", self.exchange_adapter, is_default=True)
        self.adapter_registry.register("sports", self.sports_adapter)
        
        self.position_tracker = PositionTracker()
        self.position_tracker.initialize(self.config.capital_base)
        
        # Risk Management
        self.var_calculator = VaRCalculator(self.storage)
        self.risk_committee = RiskCommittee(
            max_position_size_usd=self.config.capital_base * 0.1,
            min_confidence=0.1,
            max_portfolio_var_pct=5.0,
            var_calculator=self.var_calculator,
            correlation_analyzer=self.correlation_analyzer
        )
        self.gatekeeper = ExecutionGatekeeper(self.config)
        
        # Audit
        self.audit = None  # Will init on storage connect
        
        # State
        self.running = False
        self.mode = "SHADOW"
        self.task = None
        self.state = {
            "status": "STOPPED",
            "mode": "SHADOW",
            "regime": "UNKNOWN",
            "system_risk_score": 0,
            "active_markets": len(self.config.active_markets),
            "active_strategy": self.strategy_layer.get_strategy_name(),
            "opportunities": [],
            "decisions": [],
            "logs": [],
            "history": [],
            "positions": [],
            "research": self.auto_research.get_report(),
        }
        
        self.initialized = True
        print("[ENGINE] Initialized (SQLite, Paper Trading, VaR, ML Models)")

    async def configure(self, config: SystemConfig):
        """Update system configuration."""
        old_config = self.config.dict()
        self.config = config
        
        # Update sub-components
        self.state["active_markets"] = len(config.active_markets)
        self.portfolio_layer.update_constraints(
            config.capital_base, 
            config.risk_tolerance_pct, 
            getattr(config, 'min_confidence', 0.1)
        )
        self.position_tracker.initialize(config.capital_base)
        
        # Log config change
        if self.audit:
            self.audit.log_config_change(old_config, config.dict())
        
        self._log(f"Config Updated: ${config.capital_base:,.2f} Capital")
        self.state["history"] = []

    async def refresh_research(self) -> Dict[str, Any]:
        """
        Run strategy auto-research and swap active strategy if a better one is found.
        """
        try:
            report = await asyncio.to_thread(
                self.auto_research.run,
                self.config.active_markets,
            )
            strategy = self.auto_research.get_selected_strategy()
            self.strategy_layer.set_strategy(strategy)
            self.state["active_strategy"] = strategy.name
            self.state["research"] = report
            self._log(f"Research selected strategy: {strategy.name}")
            return report
        except Exception as e:
            msg = {"status": "error", "error": str(e)}
            self.state["research"] = msg
            self._log(f"Research refresh failed: {e}")
            return msg

    def get_research_status(self) -> Dict[str, Any]:
        report = self.auto_research.get_report()
        self.state["research"] = report
        self.state["active_strategy"] = self.strategy_layer.get_strategy_name()
        return report

    async def start(self, mode: str = "SHADOW"):
        if self.running:
            return

        # Connect database first.
        try:
            await self.storage.connect()
            self.audit = AuditService(self.storage)
            self.audit.log_system_event("engine_start", {"mode": mode})
        except Exception as e:
            self._log(f"ERROR: Database connection failed: {e}")
            self._log("WARNING: Running without persistence")

        # Run strategy auto-research before live decisions.
        await self.refresh_research()

        # Connect exchange.
        try:
            await self.exchange_adapter.connect()
        except Exception as e:
            self._log(f"WARNING: Exchange connection failed: {e}")

        self.mode = mode
        self.running = True
        self.state["status"] = "RUNNING"
        self.state["mode"] = mode

        icon = "[SHADOW]" if mode == "SHADOW" else "[LIVE]"
        self._log(f"{icon} Engine Started in {mode} MODE")

        # Initialize data feed.
        await self.market_layer.connect()
        self.market_layer.update_tickers(self.config.active_markets)

        # Start main loop.
        self.task = asyncio.create_task(self._run_loop())

    async def stop(self):
        self.running = False
        self.market_layer.running = False
        self.state["status"] = "STOPPED"
        
        if self.task:
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        if self.audit:
            self.audit.log_system_event("engine_stop")
        
        if self.storage:
            self.storage.close()
        
        self._log("Engine Stopped")

    async def _run_loop(self):
        """Main autonomous loop with full Phase 1 integration."""
        try:
            async for quote in self.market_layer.stream_quotes():
                if not self.running:
                    break
                
                # Save to database
                if self.storage:
                    try:
                        await self.storage.save_quote(quote)
                    except Exception as e:
                        print(f"[ENGINE] DB save failed: {e}")
                
                # Strategy analysis
                market_data = [quote.model_dump()]
                opportunities = await self.strategy_layer.analyze(market_data)
                self.state["opportunities"] = opportunities
                
                # Portfolio decisions
                decisions = await self.portfolio_layer.optimize(opportunities)
                
                # Execute decisions with full pipeline
                for dec in decisions:
                    if dec["action"] == "EXECUTE":
                        await self._execute_decision(dec, quote)
                
                # Update portfolio state
                await self._update_portfolio_state()
                
        except Exception as e:
            self._log(f"Engine error: {e}")
            if self.audit:
                self.audit.log_system_event("engine_error", {"error": str(e)})
            self.running = False
            self.state["status"] = "ERROR"

    async def _execute_decision(self, decision: Dict, quote):
        """Execute a single trade decision through the full pipeline."""
        # 1. Create TradeIntent
        intent = TradeIntent(
            id=f"trade_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            instrument_id=decision['symbol'],
            strategy_id="portfolio_engine",
            side=decision['direction'].lower(),
            size=decision['amount'] / quote.price if quote.price > 0 else 0,
            expected_return=0.01,
            confidence_score=decision.get('confidence', 0.5)
        )
        
        # 2. Audit: Log intent
        if self.audit:
            self.audit.log_trade_intent(intent.dict())
        
        # 3. Risk Check
        current_positions = {
            p.symbol: {"quantity": p.quantity, "price": p.avg_price}
            for p in self.position_tracker.get_all_positions().values()
        }
        portfolio_value = self.position_tracker.calculate_portfolio_value({
            quote.instrument_id: quote.price
        })
        
        risk_result = self.risk_committee.check(
            intent, 
            quote.price,
            current_positions,
            portfolio_value
        )
        
        # 4. Audit: Log risk decision
        if self.audit:
            self.audit.log_risk_decision(
                intent.id,
                risk_result["approved"],
                risk_result["checks"],
                risk_result.get("reason")
            )
        
        # 5. Gatekeeper check (mode + safety)
        if not risk_result["approved"]:
            self._log(f"BLOCKED: {decision['symbol']} - {risk_result['reason']}")
            return
        
        gate_safe = self.gatekeeper.validate(
            intent, 
            mode=self.mode, 
            current_equity=portfolio_value
        )
        
        # 6. Execute (Paper Trading)
        if self.mode == "SHADOW" or not gate_safe:
            # Shadow mode: log only
            self._log(f"SHADOW: {decision['direction']} {decision['symbol']} ${decision['amount']:.2f}")
            self._record_decision(decision, "SHADOW_LOGGED")
        else:
            # Paper trading execution
            try:
                fill = await self.exchange_adapter.simulate_order(
                    symbol=decision['symbol'],
                    side=decision['direction'].lower(),
                    quantity=intent.size
                )
                
                if fill:
                    self._log(f"FILLED: {fill.side.upper()} {fill.quantity:.4f} {fill.symbol} @ ${fill.fill_price:.2f}")
                    
                    # Update positions
                    self.position_tracker.update_position(
                        fill.symbol,
                        fill.quantity,
                        fill.fill_price,
                        fill.side
                    )
                    
                    # Save to DB
                    if self.storage and self.audit:
                        self.audit.log_execution(fill.__dict__)
                    
                    self._record_decision(decision, "EXECUTED")
                    
            except Exception as e:
                self._log(f"Execution failed: {e}")

    async def _update_portfolio_state(self):
        """Update state with current portfolio metrics."""
        try:
            # Get current prices (simplified - would fetch from exchange)
            current_prices = {}  # Mock
            
            portfolio_summary = self.position_tracker.get_portfolio_summary(current_prices)
            
            self.state["history"].append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "value": portfolio_summary["total_value"]
            })
            self.state["history"] = self.state["history"][-50:]
            
            self.state["positions"] = portfolio_summary["positions"]
            
        except Exception as e:
            print(f"[ENGINE] Portfolio update failed: {e}")

    def _record_decision(self, dec, status):
        decision_record = {**dec, "status": status, "time": datetime.now().strftime('%H:%M:%S')}
        self.state["decisions"].insert(0, decision_record)
        self.state["decisions"] = self.state["decisions"][:20]

    def _log(self, message: str):
        entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.state["logs"].insert(0, entry)
        self.state["logs"] = self.state["logs"][:50]
        print(entry)

    def get_status(self) -> Dict[str, Any]:
        self.state["active_strategy"] = self.strategy_layer.get_strategy_name()
        return self.state

# Global Instance
engine = EngineService()

