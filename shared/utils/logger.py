"""
Logger Utility
Simple file-based logging with rotation
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


class FundLogger:
    """Simple file-based logger with rotation."""

    @staticmethod
    def setup_logger(fund_name: str, date: str, log_dir: str = 'logs') -> logging.Logger:
        """
        Create a logger with file rotation.

        Args:
            fund_name: Name of the fund/component
            date: Date string for log file naming
            log_dir: Directory for log files

        Returns:
            Configured logger instance
        """
        # Create logs directory
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Create logger
        logger = logging.getLogger(fund_name)
        logger.setLevel(logging.INFO)

        # Remove existing handlers
        logger.handlers = []

        # File handler with rotation
        log_file = log_path / f"{fund_name}_{date}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )

        # Console handler
        console_handler = logging.StreamHandler()

        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger
