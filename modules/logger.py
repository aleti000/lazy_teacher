#!/usr/bin/env python3
"""
Unified logging module for Lazy Teacher.
Provides centralized logging configuration and utilities.
"""

import logging
import sys
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

# Create console for rich output
console = Console()

class LazyTeacherLogger:
    """Centralized logger class with file and console output."""

    def __init__(self, name: str = "lazy_teacher", log_file: str = "lazy_teacher.log"):
        self.name = name
        self.log_file = Path(log_file)

        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )

        console_formatter = logging.Formatter(
            '%(levelname)s - %(funcName)s - %(message)s'
        )

        # Setup file handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)

        # Setup console handler with Rich
        console_handler = RichHandler(console=console, show_time=False, show_path=False)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)

        # Setup logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Prevent duplicate handlers
        self.logger.propagate = False

    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self.logger

# Global logger instance
logger_instance = LazyTeacherLogger()

def get_logger(module_name: str) -> logging.Logger:
    """
    Get a module-specific logger.

    Args:
        module_name: Name of the module requesting the logger

    Returns:
        Configured logger instance for the module
    """
    return logging.getLogger(f"{logger_instance.name}.{module_name}")

def log_operation(logger: logging.Logger, operation: str, success: bool = True, **context):
    """
    Standardized operation logging with context.

    Args:
        logger: Logger instance to use
        operation: Description of the operation
        success: Whether operation succeeded
        **context: Additional context to log
    """
    level = logging.INFO if success else logging.ERROR
    status = "SUCCESS" if success else "FAILED"

    message = f"{operation} - {status}"
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        message = f"{message} [{context_str}]"

    logger.log(level, message, extra=context)

def log_error(logger: logging.Logger, error: Exception, operation: str = "", **context):
    """
    Standardized error logging with traceback preservation.

    Args:
        logger: Logger instance to use
        error: Exception that occurred
        operation: Description of the operation that failed
        **context: Additional error context
    """
    error_msg = f"{operation} failed: {str(error)}" if operation else f"Error: {str(error)}"
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        error_msg = f"{error_msg} [{context_str}]"

    logger.error(error_msg, exc_info=True)

# Utility function to measure operation duration
class OperationTimer:
    """Context manager to log operation duration."""

    def __init__(self, logger: logging.Logger, operation_name: str):
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        self.start_time = logging.time.time()
        self.logger.debug(f"Started: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = logging.time.time() - self.start_time
        if exc_type:
            self.logger.error(f"Failed: {self.operation_name} (duration: {duration:.2f}s)", exc_info=True)
        else:
            self.logger.debug(f"Completed: {self.operation_name} (duration: {duration:.2f}s)")

# Initialize global logger
_logger = logger_instance.get_logger()
