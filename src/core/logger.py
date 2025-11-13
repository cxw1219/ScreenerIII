"""
Logging Module

This module provides centralized logging configuration with different log levels
for console and file output, structured logging format, and component-specific loggers.
"""

import logging
import sys
from typing import Optional, Dict
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Import colorama for colored console output
try:
    from colorama import Fore, Back, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to console output based on log level.
    """

    # Color mapping for different log levels
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT,
    }

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None,
                 use_colors: bool = True):
        """
        Initialize the colored formatter.

        Args:
            fmt: Log message format string
            datefmt: Date format string
            use_colors: Whether to use colors (disabled if colorama not available)
        """
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and COLORAMA_AVAILABLE

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors.

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        if self.use_colors:
            # Add color to level name
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"

            # Color the logger name
            record.name = f"{Fore.BLUE}{record.name}{Style.RESET_ALL}"

        return super().format(record)


class LoggerManager:
    """
    Manager for centralized logging configuration.

    Provides different log levels for console and file output,
    structured logging format, and component-specific loggers.
    """

    _instance: Optional['LoggerManager'] = None
    _initialized: bool = False
    _loggers: Dict[str, logging.Logger] = {}

    # Default format strings
    DETAILED_FORMAT = (
        '%(asctime)s | %(name)-30s | %(levelname)-8s | '
        '%(filename)s:%(lineno)d | %(funcName)s() | %(message)s'
    )

    SIMPLE_FORMAT = (
        '%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s'
    )

    CONSOLE_FORMAT = (
        '%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s'
    )

    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __new__(cls) -> 'LoggerManager':
        """Implement singleton pattern for logger manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the logger manager."""
        if not self._initialized:
            self._setup_logging()
            LoggerManager._initialized = True

    def _setup_logging(self) -> None:
        """Setup centralized logging configuration."""
        from .config_loader import get_config

        try:
            config = get_config()
            log_level = config.log_level
            log_file_path = config.log_file_path
            rotation_size_mb = config.log_rotation_size
            backup_count = config.log_backup_count
        except Exception:
            # Fallback to defaults if config not available
            log_level = 'INFO'
            log_file_path = 'logs/screener.log'
            rotation_size_mb = 10
            backup_count = 5

        # Create logs directory if it doesn't exist
        log_dir = Path(log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Convert string log level to logging constant
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Capture all levels

        # Remove existing handlers
        root_logger.handlers.clear()

        # Console handler with color formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_formatter = ColoredFormatter(
            fmt=self.CONSOLE_FORMAT,
            datefmt=self.DATE_FORMAT,
            use_colors=True
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=rotation_size_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_formatter = logging.Formatter(
            fmt=self.DETAILED_FORMAT,
            datefmt=self.DATE_FORMAT
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Log initialization message
        root_logger.info(f"Logging system initialized - Level: {log_level}")
        root_logger.info(f"Log file: {log_file_path}")

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get or create a logger for a specific component.

        Args:
            name: Logger name (typically __name__ of the module)

        Returns:
            logging.Logger: Configured logger instance
        """
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        self._loggers[name] = logger
        return logger

    def set_level(self, level: str, logger_name: Optional[str] = None) -> None:
        """
        Set log level for a specific logger or all loggers.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            logger_name: Specific logger name, or None for root logger
        """
        numeric_level = getattr(logging, level.upper(), logging.INFO)

        if logger_name:
            logger = logging.getLogger(logger_name)
            logger.setLevel(numeric_level)
        else:
            # Update console handler level only (keep file at DEBUG)
            root_logger = logging.getLogger()
            for handler in root_logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                    handler.setLevel(numeric_level)

    def add_file_handler(
        self,
        logger_name: str,
        file_path: str,
        level: str = 'DEBUG',
        rotation_size_mb: int = 10,
        backup_count: int = 5
    ) -> None:
        """
        Add an additional file handler to a specific logger.

        Args:
            logger_name: Name of the logger
            file_path: Path to log file
            level: Log level for this handler
            rotation_size_mb: Size in MB before rotation
            backup_count: Number of backup files to keep
        """
        logger = self.get_logger(logger_name)

        # Create directory if needed
        log_dir = Path(file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create file handler
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=rotation_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )

        numeric_level = getattr(logging, level.upper(), logging.DEBUG)
        file_handler.setLevel(numeric_level)

        formatter = logging.Formatter(
            fmt=self.DETAILED_FORMAT,
            datefmt=self.DATE_FORMAT
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    def get_component_logger(
        self,
        component: str,
        log_file: Optional[str] = None
    ) -> logging.Logger:
        """
        Get a logger for a specific component with optional separate log file.

        Args:
            component: Component name (e.g., 'oanda_api', 'strategy', 'screener')
            log_file: Optional separate log file for this component

        Returns:
            logging.Logger: Configured logger for the component
        """
        logger = self.get_logger(f'screener.{component}')

        if log_file:
            self.add_file_handler(
                logger_name=f'screener.{component}',
                file_path=log_file
            )

        return logger


# Global logger manager instance
_logger_manager: Optional[LoggerManager] = None


def get_logger_manager() -> LoggerManager:
    """
    Get or create the global logger manager instance.

    Returns:
        LoggerManager: The global logger manager instance
    """
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    return _logger_manager


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module or component.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        logging.Logger: Configured logger instance
    """
    manager = get_logger_manager()
    return manager.get_logger(name)


def get_component_logger(component: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Get a logger for a specific component with optional separate log file.

    Args:
        component: Component name (e.g., 'oanda_api', 'strategy', 'screener')
        log_file: Optional separate log file for this component

    Returns:
        logging.Logger: Configured logger for the component
    """
    manager = get_logger_manager()
    return manager.get_component_logger(component, log_file)


def set_log_level(level: str, logger_name: Optional[str] = None) -> None:
    """
    Set log level for a specific logger or all loggers.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        logger_name: Specific logger name, or None for root logger
    """
    manager = get_logger_manager()
    manager.set_level(level, logger_name)


if __name__ == '__main__':
    # Test logging system
    logger = get_logger(__name__)

    print("Testing logging system...")
    print()

    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")

    print()
    print("Testing component-specific logger...")

    api_logger = get_component_logger('oanda_api')
    api_logger.info("OANDA API logger initialized")

    strategy_logger = get_component_logger('strategy')
    strategy_logger.info("Strategy logger initialized")

    print()
    print("Logging test complete. Check logs/screener.log for file output.")
