"""
Unit tests for logging module.

Tests logging configuration, colored formatters, log levels,
file handlers, and component-specific loggers.
"""

import pytest
import logging
import sys
from pathlib import Path as PathlibPath
from unittest.mock import Mock, MagicMock, patch, mock_open
import tempfile
import os

# Add src directory to path
sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent / "src"))


class TestColoredFormatter:
    """Test suite for ColoredFormatter."""

    def test_colored_formatter_initialization(self):
        """Test ColoredFormatter initialization."""
        from src.core.logger import ColoredFormatter

        formatter = ColoredFormatter()
        assert formatter is not None

    def test_colored_formatter_with_colors(self):
        """Test ColoredFormatter with colors enabled."""
        from src.core.logger import ColoredFormatter

        formatter = ColoredFormatter(use_colors=True)
        assert formatter.use_colors is True or not __import__('src.core.logger').COLORAMA_AVAILABLE

    def test_colored_formatter_without_colors(self):
        """Test ColoredFormatter with colors disabled."""
        from src.core.logger import ColoredFormatter

        formatter = ColoredFormatter(use_colors=False)
        assert formatter.use_colors is False

    def test_colored_formatter_format_record(self):
        """Test ColoredFormatter formatting a log record."""
        from src.core.logger import ColoredFormatter

        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        assert 'Test message' in formatted

    def test_colored_formatter_all_log_levels(self):
        """Test ColoredFormatter with all log levels."""
        from src.core.logger import ColoredFormatter

        formatter = ColoredFormatter()
        levels = [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL
        ]

        for level in levels:
            record = logging.LogRecord(
                name='test',
                level=level,
                pathname='test.py',
                lineno=1,
                msg=f'Test {logging.getLevelName(level)}',
                args=(),
                exc_info=None
            )
            formatted = formatter.format(record)
            assert formatted is not None


class TestLoggerManager:
    """Test suite for LoggerManager."""

    @patch('src.core.logger.get_config')
    def test_logger_manager_singleton(self, mock_config):
        """Test LoggerManager implements singleton pattern."""
        from src.core.logger import LoggerManager

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        manager1 = LoggerManager()
        manager2 = LoggerManager()

        assert manager1 is manager2

    @patch('src.core.logger.get_config')
    def test_logger_manager_initialization(self, mock_config):
        """Test LoggerManager initialization."""
        from src.core.logger import LoggerManager

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        manager = LoggerManager()
        assert manager is not None

    @patch('src.core.logger.get_config')
    def test_get_logger(self, mock_config):
        """Test getting a logger instance."""
        from src.core.logger import LoggerManager

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        manager = LoggerManager()
        logger = manager.get_logger('test_module')

        assert logger is not None
        assert isinstance(logger, logging.Logger)

    @patch('src.core.logger.get_config')
    def test_get_logger_caching(self, mock_config):
        """Test that get_logger caches logger instances."""
        from src.core.logger import LoggerManager

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        manager = LoggerManager()
        logger1 = manager.get_logger('test_module')
        logger2 = manager.get_logger('test_module')

        assert logger1 is logger2

    @patch('src.core.logger.get_config')
    def test_set_level(self, mock_config):
        """Test setting log level."""
        from src.core.logger import LoggerManager

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        manager = LoggerManager()
        manager.set_level('DEBUG')

        # Should not raise exception

    @patch('src.core.logger.get_config')
    def test_set_level_for_specific_logger(self, mock_config):
        """Test setting log level for specific logger."""
        from src.core.logger import LoggerManager

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        manager = LoggerManager()
        logger = manager.get_logger('test_module')
        manager.set_level('DEBUG', 'test_module')

        assert logger.level == logging.DEBUG

    @patch('src.core.logger.get_config')
    def test_get_component_logger(self, mock_config):
        """Test getting component-specific logger."""
        from src.core.logger import LoggerManager

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        manager = LoggerManager()
        logger = manager.get_component_logger('oanda_api')

        assert logger is not None
        assert 'oanda_api' in logger.name

    @patch('src.core.logger.get_config')
    def test_add_file_handler(self, mock_config):
        """Test adding file handler to logger."""
        from src.core.logger import LoggerManager

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        manager = LoggerManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, 'component.log')
            manager.add_file_handler(
                'test_logger',
                log_path,
                level='DEBUG'
            )

            logger = manager.get_logger('test_logger')
            assert len(logger.handlers) > 0


class TestLoggerFormats:
    """Test suite for logger format strings."""

    def test_detailed_format_exists(self):
        """Test that DETAILED_FORMAT exists."""
        from src.core.logger import LoggerManager

        assert hasattr(LoggerManager, 'DETAILED_FORMAT')
        assert isinstance(LoggerManager.DETAILED_FORMAT, str)

    def test_simple_format_exists(self):
        """Test that SIMPLE_FORMAT exists."""
        from src.core.logger import LoggerManager

        assert hasattr(LoggerManager, 'SIMPLE_FORMAT')
        assert isinstance(LoggerManager.SIMPLE_FORMAT, str)

    def test_console_format_exists(self):
        """Test that CONSOLE_FORMAT exists."""
        from src.core.logger import LoggerManager

        assert hasattr(LoggerManager, 'CONSOLE_FORMAT')
        assert isinstance(LoggerManager.CONSOLE_FORMAT, str)

    def test_date_format_exists(self):
        """Test that DATE_FORMAT exists."""
        from src.core.logger import LoggerManager

        assert hasattr(LoggerManager, 'DATE_FORMAT')
        assert isinstance(LoggerManager.DATE_FORMAT, str)


class TestLoggerHelperFunctions:
    """Test suite for logger helper functions."""

    @patch('src.core.logger.get_config')
    def test_get_logger_manager(self, mock_config):
        """Test get_logger_manager helper function."""
        from src.core.logger import get_logger_manager

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        manager = get_logger_manager()
        assert manager is not None

    @patch('src.core.logger.get_config')
    def test_get_logger_helper(self, mock_config):
        """Test get_logger helper function."""
        from src.core.logger import get_logger

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        logger = get_logger('test_module')
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    @patch('src.core.logger.get_config')
    def test_get_component_logger_helper(self, mock_config):
        """Test get_component_logger helper function."""
        from src.core.logger import get_component_logger

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        logger = get_component_logger('strategy')
        assert logger is not None

    @patch('src.core.logger.get_config')
    def test_set_log_level_helper(self, mock_config):
        """Test set_log_level helper function."""
        from src.core.logger import set_log_level

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        # Should not raise exception
        set_log_level('DEBUG')


class TestLoggingBehavior:
    """Test suite for actual logging behavior."""

    @patch('src.core.logger.get_config')
    def test_logger_logs_info_message(self, mock_config, caplog):
        """Test that logger logs INFO messages."""
        from src.core.logger import get_logger

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        logger = get_logger('test')

        with caplog.at_level(logging.INFO):
            logger.info('Test info message')

        assert 'Test info message' in caplog.text

    @patch('src.core.logger.get_config')
    def test_logger_logs_error_message(self, mock_config, caplog):
        """Test that logger logs ERROR messages."""
        from src.core.logger import get_logger

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        logger = get_logger('test')

        with caplog.at_level(logging.ERROR):
            logger.error('Test error message')

        assert 'Test error message' in caplog.text

    @patch('src.core.logger.get_config')
    def test_logger_logs_warning_message(self, mock_config, caplog):
        """Test that logger logs WARNING messages."""
        from src.core.logger import get_logger

        mock_config.return_value = Mock(
            log_level='INFO',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        logger = get_logger('test')

        with caplog.at_level(logging.WARNING):
            logger.warning('Test warning message')

        assert 'Test warning message' in caplog.text

    @patch('src.core.logger.get_config')
    def test_logger_logs_debug_message(self, mock_config, caplog):
        """Test that logger logs DEBUG messages."""
        from src.core.logger import get_logger

        mock_config.return_value = Mock(
            log_level='DEBUG',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        logger = get_logger('test')

        with caplog.at_level(logging.DEBUG):
            logger.debug('Test debug message')

        assert 'Test debug message' in caplog.text


class TestLoggerConfiguration:
    """Test suite for logger configuration."""

    @patch('src.core.logger.get_config')
    def test_logger_with_config_error_fallback(self, mock_config):
        """Test logger initialization with config error falls back to defaults."""
        from src.core.logger import LoggerManager

        # Make config raise exception
        mock_config.side_effect = Exception("Config error")

        # Should not raise exception, should use defaults
        manager = LoggerManager()
        assert manager is not None

    @patch('src.core.logger.get_config')
    def test_logger_level_configuration(self, mock_config):
        """Test logger level configuration from config."""
        from src.core.logger import LoggerManager

        mock_config.return_value = Mock(
            log_level='DEBUG',
            log_file_path='logs/test.log',
            log_rotation_size=10,
            log_backup_count=5
        )

        manager = LoggerManager()
        logger = manager.get_logger('test')

        # Root logger should be set to DEBUG
        assert logging.getLogger().level == logging.DEBUG


class TestColoramaAvailability:
    """Test suite for colorama availability handling."""

    def test_colorama_available_flag_exists(self):
        """Test that COLORAMA_AVAILABLE flag exists."""
        import src.core.logger as logger_module

        assert hasattr(logger_module, 'COLORAMA_AVAILABLE')
        assert isinstance(logger_module.COLORAMA_AVAILABLE, bool)
