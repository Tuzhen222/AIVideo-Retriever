import logging
import os
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from app.core.config import settings


def setup_logging():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(exist_ok=True)
    
    # Log file path
    log_file = log_dir / "app.log"
    search_log_file = log_dir / "search_queries.log"
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for general logs
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Search query logger (separate file)
    search_logger = logging.getLogger("search_queries")
    search_logger.setLevel(logging.INFO)
    search_logger.propagate = False  # Don't propagate to root logger
    
    search_file_handler = RotatingFileHandler(
        search_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,  # Keep more backups for search queries
        encoding="utf-8"
    )
    search_file_handler.setLevel(logging.INFO)
    search_formatter = logging.Formatter(
        "%(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    search_file_handler.setFormatter(search_formatter)
    search_logger.addHandler(search_file_handler)
    
    return root_logger, search_logger


# Initialize loggers
app_logger, search_logger = setup_logging()


def log_search_query(query: str, method: str, top_k: int, filters: dict = None, 
                     results_count: int = 0, duration_ms: float = None):
    """
    Log search query to search_queries.log
    
    Args:
        query: Search query string
        method: Search method used
        top_k: Number of results requested
        filters: Additional filters
        results_count: Number of results returned
        duration_ms: Search duration in milliseconds
    """
    log_parts = [
        f"QUERY: {query}",
        f"METHOD: {method}",
        f"TOP_K: {top_k}",
    ]
    
    if filters:
        log_parts.append(f"FILTERS: {filters}")
    
    log_parts.append(f"RESULTS: {results_count}")
    
    if duration_ms is not None:
        log_parts.append(f"DURATION: {duration_ms:.2f}ms")
    
    search_logger.info(" | ".join(log_parts))

