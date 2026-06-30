"""Logging utilities."""

import logging
import sys
from datetime import datetime

# Configure logging format
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with consistent formatting."""
    logger = logging.getLogger(name)
    
    # Skip if already configured
    if logger.handlers:
        return logger
    
    # Configure level
    logger.setLevel(logging.INFO)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # Create formatter and add to handler
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    logger.propagate = False  # prevent double logging from root handler
    
    return logger


def log_error(logger: logging.Logger, error: Exception, context: str = ""):
    """Log error with context."""
    msg = f"Error in {context}: {type(error).__name__}: {str(error)}"
    logger.error(msg, exc_info=True)


def log_user_action(logger: logging.Logger, user_id: int, action: str, details: str = ""):
    """Log user action for audit trail."""
    msg = f"User {user_id} - {action}"
    if details:
        msg += f" ({details})"
    logger.info(msg)
