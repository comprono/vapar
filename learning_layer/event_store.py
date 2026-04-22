import json
from datetime import datetime
from common.types import TradeIntent
from common.logger import get_logger

class TradeEventLogger:
    """
    Immutable Event Store for the trading system.
    Records the lifecycle of every TradeIntent.
    """
    
    def __init__(self, log_path: str = "trade_events.jsonl"):
        self.log_path = log_path
        self.logger = get_logger("EventStore")

    def log_event(self, intent: TradeIntent, event_type: str, details: dict = None):
        """
        Append an event to the ledger.
        """
        payload = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "trade_id": intent.id,
            "symbol": intent.symbol,
            "status": str(intent.status),
            "details": details or {},
            "risk_log": intent.risk_check_log
        }
        
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write to event store: {e}")

    def replay_events(self):
        """Yields events generator for analysis."""
        try:
            with open(self.log_path, "r") as f:
                for line in f:
                    yield json.loads(line)
        except FileNotFoundError:
            return
