import logging
import sys
from typing import Any, Dict
import json
from datetime import datetime

# Standard enterprise-level logging configuration
LOG_FORMAT = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"

def setup_logger(name: str = "venueflow", level: int = logging.INFO):
    """
    Configures and returns a structured logger.
    In production, this could be extended to use JSON formatters for ELK/Splunk.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if re-initialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

# Global logger instance
logger = setup_logger()

def log_event(event_type: str, data: Dict[str, Any]):
    """Log a structured event (useful for audit trails)."""
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        "payload": data
    }
    logger.info(f"EVENT: {json.dumps(payload)}")
