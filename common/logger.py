import logging
import sys
from datetime import datetime
from typing import Any, Dict

# Basic configuration for standard logging
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

class TradingLogger:
    """
    Wrapper for structured logging to ensure consistent log format
    across the entire system (Data -> Decision -> Execution).
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name

    def _format_log(self, event: str, level: str, **kwargs) -> str:
        """
        Create a standardized log string (JSON-like structure could be better for prod, 
        but keeping it readable for local dev).
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "component": self.name,
            "event": event,
            **kwargs
        }
        return str(log_data)

    def info(self, event: str, **kwargs):
        self.logger.info(self._format_log(event, "INFO", **kwargs))

    def warning(self, event: str, **kwargs):
        self.logger.warning(self._format_log(event, "WARNING", **kwargs))

    def error(self, event: str, **kwargs):
        self.logger.error(self._format_log(event, "ERROR", **kwargs))

    def critical(self, event: str, **kwargs):
        self.logger.critical(self._format_log(event, "CRITICAL", **kwargs))

def get_logger(name: str) -> TradingLogger:
    return TradingLogger(name)
