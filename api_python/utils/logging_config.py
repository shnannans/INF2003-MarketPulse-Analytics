"""
Logging Configuration (Task 50: Logging and Monitoring)
Provides centralized logging configuration and utilities
"""
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup centralized logging configuration (Task 50: Logging and Monitoring).
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path (default: logs/marketpulse.log)
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup log files to keep
    
    Returns:
        Configured logger instance
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler (rotating)
    if log_file is None:
        log_file = LOG_DIR / "marketpulse.log"
    else:
        log_file = Path(log_file)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler (separate file for errors)
    error_log_file = LOG_DIR / "marketpulse_errors.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module (Task 50: Logging and Monitoring).
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class RequestLogger:
    """
    Request logging utility (Task 50: Logging and Monitoring).
    Logs API requests and responses for monitoring and debugging.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or get_logger(__name__)
    
    def log_request(self, method: str, path: str, client_ip: str, **kwargs):
        """Log incoming API request."""
        self.logger.info(
            f"REQUEST: {method} {path} | IP: {client_ip} | "
            f"Params: {kwargs.get('params', {})} | "
            f"Query: {kwargs.get('query', {})}"
        )
    
    def log_response(self, method: str, path: str, status_code: int, duration_ms: float, **kwargs):
        """Log API response."""
        self.logger.info(
            f"RESPONSE: {method} {path} | Status: {status_code} | "
            f"Duration: {duration_ms:.2f}ms"
        )
    
    def log_error(self, method: str, path: str, error: Exception, **kwargs):
        """Log API error."""
        self.logger.error(
            f"ERROR: {method} {path} | Error: {type(error).__name__} | "
            f"Message: {str(error)}",
            exc_info=True
        )


class PerformanceLogger:
    """
    Performance logging utility (Task 50: Logging and Monitoring).
    Logs performance metrics for monitoring.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or get_logger(__name__)
    
    def log_slow_query(self, query: str, duration_ms: float, threshold_ms: float = 1000):
        """Log slow database queries."""
        if duration_ms > threshold_ms:
            self.logger.warning(
                f"SLOW QUERY: Duration: {duration_ms:.2f}ms | "
                f"Threshold: {threshold_ms}ms | Query: {query[:200]}..."
            )
    
    def log_cache_hit(self, key: str, cache_type: str = "memory"):
        """Log cache hit."""
        self.logger.debug(f"CACHE HIT: {cache_type} | Key: {key}")
    
    def log_cache_miss(self, key: str, cache_type: str = "memory"):
        """Log cache miss."""
        self.logger.debug(f"CACHE MISS: {cache_type} | Key: {key}")
    
    def log_database_operation(self, operation: str, table: str, duration_ms: float):
        """Log database operation performance."""
        self.logger.debug(
            f"DB OPERATION: {operation} | Table: {table} | "
            f"Duration: {duration_ms:.2f}ms"
        )

