import logging
import sys
from pathlib import Path

def setup_logging(level: str = "INFO", log_file: str = None):
    """
    Configure application-wide logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for logs
    """
    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # File handler (if specified)
    handlers = [console_handler]
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers
    )
    
    # Silence noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('binance').setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized at {level} level")

def get_logger(name: str) -> logging.Logger:
    """Get logger for a module."""
    return logging.getLogger(name)
