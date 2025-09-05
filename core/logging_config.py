"""
Logging configuration for DOI2BibTex application.

This module provides centralized logging configuration with different
levels and formatters for development and production environments.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_colors: bool = True
) -> logging.Logger:
    """
    Set up logging configuration for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        enable_console: Whether to enable console logging
        enable_colors: Whether to use colored output (console only)
        
    Returns:
        Configured logger instance
    """
    # Create main logger
    logger = logging.getLogger("doi2bibtex")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        
        if enable_colors and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            console_format = ColoredFormatter(
                '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
                datefmt='%H:%M:%S'
            )
        else:
            console_format = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
                datefmt='%H:%M:%S'
            )
        
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler to prevent huge log files
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)  # File gets all messages
        
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return logging.getLogger(f"doi2bibtex.{name}")


# Performance monitoring decorator
def log_performance(func):
    """Decorator to log function execution time."""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger("performance")
        start_time = time.perf_counter()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.perf_counter() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper


# Context manager for operation logging
class LoggedOperation:
    """Context manager for logging operation start/end with timing."""
    
    def __init__(self, operation_name: str, logger_name: str = "operations"):
        self.operation_name = operation_name
        self.logger = get_logger(logger_name)
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        self.logger.info(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.perf_counter() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Completed {self.operation_name} in {execution_time:.3f}s")
        else:
            self.logger.error(
                f"Failed {self.operation_name} after {execution_time:.3f}s: "
                f"{exc_type.__name__}: {exc_val}"
            )
        
        return False  # Don't suppress exceptions


# Streamlit logging integration
def setup_streamlit_logging(level: str = "INFO") -> logging.Logger:
    """Set up logging specifically for Streamlit applications."""
    import streamlit as st
    
    # Check if running in Streamlit
    if hasattr(st, '_is_running_with_streamlit'):
        # Streamlit environment - simpler logging
        return setup_logging(
            level=level,
            log_file="logs/doi2bibtex.log",
            enable_console=False,  # Streamlit handles console
            enable_colors=False
        )
    else:
        # Development environment - full logging
        return setup_logging(
            level=level,
            log_file="logs/doi2bibtex.log",
            enable_console=True,
            enable_colors=True
        )


# Usage examples and configuration presets
LOGGING_PRESETS = {
    "development": {
        "level": "DEBUG",
        "log_file": "logs/doi2bibtex_dev.log",
        "enable_console": True,
        "enable_colors": True,
    },
    "production": {
        "level": "INFO", 
        "log_file": "logs/doi2bibtex.log",
        "enable_console": False,
        "enable_colors": False,
    },
    "testing": {
        "level": "WARNING",
        "log_file": None,
        "enable_console": True,
        "enable_colors": False,
    }
}


def setup_preset_logging(preset: str = "development") -> logging.Logger:
    """Set up logging using a predefined preset."""
    if preset not in LOGGING_PRESETS:
        raise ValueError(f"Unknown preset '{preset}'. Available: {list(LOGGING_PRESETS.keys())}")
    
    config = LOGGING_PRESETS[preset]
    return setup_logging(**config)


# Initialize default logger (can be overridden)
_default_logger = None

def init_default_logger(preset: str = "development") -> logging.Logger:
    """Initialize the default application logger."""
    global _default_logger
    _default_logger = setup_preset_logging(preset)
    return _default_logger


def get_default_logger() -> logging.Logger:
    """Get the default application logger, initializing if needed."""
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_preset_logging("development")
    return _default_logger
