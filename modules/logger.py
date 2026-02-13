#!/usr/bin/env python3
"""
Logger module for Lazy Teacher.
Provides logging utilities without rich dependency.
"""

import logging
import time
from functools import wraps
from typing import Optional, Dict, Any
from datetime import datetime


# Setup basic logging
logging.basicConfig(
    filename='lazy_teacher.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def get_logger(name: str = __name__) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def log_operation(logger: logging.Logger, operation: str, success: bool = True, **kwargs) -> None:
    """Log an operation with optional context."""
    status = "SUCCESS" if success else "FAILED"
    context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    message = f"[{operation}] {status}"
    if context:
        message += f" | {context}"
    
    if success:
        logger.info(message)
    else:
        logger.warning(message)


def log_error(logger: logging.Logger, error: Exception, context: str = None) -> None:
    """Log an error with context."""
    message = f"ERROR: {type(error).__name__}: {error}"
    if context:
        message = f"[{context}] {message}"
    logger.error(message, exc_info=True)


class OperationTimer:
    """Context manager for timing operations."""
    
    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.kwargs = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        context = " | ".join(f"{k}={v}" for k, v in self.kwargs.items())
        
        if exc_type is None:
            message = f"[{self.operation}] completed in {elapsed:.2f}s"
            if context:
                message += f" | {context}"
            self.logger.debug(message)
        else:
            message = f"[{self.operation}] failed after {elapsed:.2f}s"
            if context:
                message += f" | {context}"
            self.logger.error(message)
        
        return False  # Don't suppress exceptions


def timed(logger: logging.Logger = None):
    """Decorator for timing functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.debug(f"[{func.__name__}] completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"[{func.__name__}] failed after {elapsed:.2f}s: {e}")
                raise
        return wrapper
    return decorator