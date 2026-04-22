from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class AuditService:
    """
    Immutable audit logging service.
    Records all system events to database for compliance and debugging.
    """
    
    def __init__(self, storage_adapter):
        self.storage = storage_adapter
        self.session_id = str(uuid.uuid4())
        print(f"[AUDIT] Session: {self.session_id}")
    
    def log_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        actor: str = "system",
        model_version: Optional[str] = None
    ):
        """
        Write event to audit log.
        
        Args:
            event_type: Classification of event (e.g., 'trade_intent', 'risk_check')
            data: Event details (will be stored as JSONB)
            actor: Who triggered the event
            model_version: Model version if applicable
        """
        try:
            self.storage.save_audit_event(
                event_type=event_type,
                data=data,
                actor=actor,
                model_version=model_version,
                session_id=self.session_id
            )
        except Exception as e:
            # Audit failures should not crash the system
            print(f"[AUDIT] Failed to log {event_type}: {e}")
    
    def log_system_event(self, action: str, details: Optional[Dict] = None):
        """Log system lifecycle events (start, stop, config change)."""
        self.log_event(
            event_type="system_event",
            data={
                "action": action,
                "timestamp": datetime.now().isoformat(),
                **(details or {})
            }
        )
    
    def log_trade_intent(self, intent: Dict):
        """Log a trade intent before risk checks."""
        self.log_event(
            event_type="trade_intent",
            data={
                "intent_id": intent.get("id"),
                "symbol": intent.get("instrument_id"),
                "side": intent.get("side"),
                "quantity": intent.get("size"),
                "strategy": intent.get("strategy_id"),
                "confidence": intent.get("confidence_score"),
                "expected_return": intent.get("expected_return")
            }
        )
    
    def log_risk_decision(
        self,
        intent_id: str,
        approved: bool,
        checks: Dict[str, bool],
        reason: Optional[str] = None
    ):
        """Log risk committee decision."""
        self.log_event(
            event_type="risk_decision",
            data={
                "intent_id": intent_id,
                "approved": approved,
                "checks": checks,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def log_execution(self, order_fill: Dict):
        """Log order execution result."""
        self.log_event(
            event_type="execution",
            data={
                "order_id": order_fill.get("order_id"),
                "symbol": order_fill.get("symbol"),
                "side": order_fill.get("side"),
                "quantity": order_fill.get("quantity"),
                "fill_price": order_fill.get("fill_price"),
                "fee": order_fill.get("fee"),
                "slippage": order_fill.get("slippage"),
                "timestamp": order_fill.get("timestamp").isoformat() if hasattr(order_fill.get("timestamp"), 'isoformat') else str(order_fill.get("timestamp"))
            }
        )
    
    def log_config_change(self, old_config: Dict, new_config: Dict, changed_by: str = "user"):
        """Log configuration updates."""
        self.log_event(
            event_type="config_change",
            data={
                "old": old_config,
                "new": new_config,
                "diff": self._compute_diff(old_config, new_config)
            },
            actor=changed_by
        )
    
    def _compute_diff(self, old: Dict, new: Dict) -> Dict:
        """Compute difference between two configs."""
        diff = {}
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            
            if old_val != new_val:
                diff[key] = {"from": old_val, "to": new_val}
        
        return diff
    
    def query_session_events(self) -> list:
        """Retrieve all events for current session (if storage supports it)."""
        # This would require adding a query method to storage
        # For now, just return empty
        return []
