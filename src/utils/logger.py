"""Structured JSON logging for auditability and compliance traceability."""

from datetime import datetime
import json
import logging
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Formatter that outputs structured JSON log records."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Create or retrieve a logger configured with JSON stream handler.

    Args:
        name: Logger name (usually __name__ or module path).
        level: Optional log level string (DEBUG, INFO, etc.).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if logger already has one
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    log_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
    logger.setLevel(log_level)
    return logger
