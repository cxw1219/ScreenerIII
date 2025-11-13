"""
Configuration Loader Module

This module handles loading and validating environment variables from .env files,
with special focus on OANDA API credentials and application settings.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass


class Config:
    """
    Configuration manager for the ScreenerIII application.

    Loads environment variables, validates required credentials,
    and provides centralized access to configuration throughout the app.
    """

    _instance: Optional['Config'] = None
    _initialized: bool = False

    def __new__(cls) -> 'Config':
        """Implement singleton pattern to ensure single configuration instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize configuration by loading and validating environment variables."""
        if not self._initialized:
            self._load_env()
            self._validate_config()
            Config._initialized = True

    def _load_env(self) -> None:
        """
        Load environment variables from .env file.

        Searches for .env file in current directory and parent directories.
        """
        # Find .env file starting from current directory
        current_dir = Path.cwd()
        env_file = current_dir / '.env'

        # Search up to 3 parent directories for .env file
        for _ in range(3):
            if env_file.exists():
                load_dotenv(env_file)
                break
            current_dir = current_dir.parent
            env_file = current_dir / '.env'
        else:
            # If no .env found, load from environment
            load_dotenv()

    def _validate_config(self) -> None:
        """
        Validate that all required configuration values are present.

        Raises:
            ConfigurationError: If required configuration is missing or invalid.
        """
        errors = []

        # Validate OANDA credentials
        if not self.oanda_account_id:
            errors.append("OANDA_ACCOUNT_ID is not set")

        if not self.oanda_api_token:
            errors.append("OANDA_API_TOKEN is not set")

        if not self.oanda_environment:
            errors.append("OANDA_ENVIRONMENT is not set (should be 'practice' or 'live')")
        elif self.oanda_environment not in ['practice', 'live']:
            errors.append(
                f"OANDA_ENVIRONMENT must be 'practice' or 'live', got: {self.oanda_environment}"
            )

        # Validate database configuration
        if not self.database_url:
            errors.append("DATABASE_URL is not set")

        if errors:
            raise ConfigurationError(
                "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            )

    # OANDA Configuration
    @property
    def oanda_account_id(self) -> str:
        """Get OANDA account ID."""
        return os.getenv('OANDA_ACCOUNT_ID', '')

    @property
    def oanda_api_token(self) -> str:
        """Get OANDA API token."""
        return os.getenv('OANDA_API_TOKEN', '')

    @property
    def oanda_environment(self) -> str:
        """Get OANDA environment (practice or live)."""
        return os.getenv('OANDA_ENVIRONMENT', 'practice').lower()

    @property
    def oanda_base_url(self) -> str:
        """Get OANDA API base URL based on environment."""
        if self.oanda_environment == 'live':
            return 'https://api-fxtrade.oanda.com'
        return 'https://api-fxpractice.oanda.com'

    # Database Configuration
    @property
    def database_url(self) -> str:
        """Get database connection URL."""
        return os.getenv('DATABASE_URL', 'sqlite:///screener.db')

    @property
    def database_echo(self) -> bool:
        """Get database echo setting (for SQL logging)."""
        return os.getenv('DATABASE_ECHO', 'false').lower() == 'true'

    @property
    def database_pool_size(self) -> int:
        """Get database connection pool size."""
        try:
            return int(os.getenv('DATABASE_POOL_SIZE', '5'))
        except ValueError:
            return 5

    @property
    def database_max_overflow(self) -> int:
        """Get database connection pool max overflow."""
        try:
            return int(os.getenv('DATABASE_MAX_OVERFLOW', '10'))
        except ValueError:
            return 10

    # Application Configuration
    @property
    def app_environment(self) -> str:
        """Get application environment (development, production, testing)."""
        return os.getenv('APP_ENVIRONMENT', 'development').lower()

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return os.getenv('LOG_LEVEL', 'INFO').upper()

    @property
    def log_file_path(self) -> str:
        """Get log file path."""
        return os.getenv('LOG_FILE_PATH', 'logs/screener.log')

    @property
    def log_rotation_size(self) -> int:
        """Get log file rotation size in MB."""
        try:
            return int(os.getenv('LOG_ROTATION_SIZE_MB', '10'))
        except ValueError:
            return 10

    @property
    def log_backup_count(self) -> int:
        """Get number of backup log files to keep."""
        try:
            return int(os.getenv('LOG_BACKUP_COUNT', '5'))
        except ValueError:
            return 5

    # Trading Configuration
    @property
    def max_concurrent_requests(self) -> int:
        """Get maximum concurrent API requests."""
        try:
            return int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))
        except ValueError:
            return 5

    @property
    def request_timeout(self) -> int:
        """Get API request timeout in seconds."""
        try:
            return int(os.getenv('REQUEST_TIMEOUT', '30'))
        except ValueError:
            return 30

    @property
    def rate_limit_delay(self) -> float:
        """Get delay between API requests in seconds."""
        try:
            return float(os.getenv('RATE_LIMIT_DELAY', '0.1'))
        except ValueError:
            return 0.1

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key (environment variable name)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return os.getenv(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary (excluding sensitive data).

        Returns:
            Dictionary of configuration values
        """
        return {
            'oanda_environment': self.oanda_environment,
            'oanda_base_url': self.oanda_base_url,
            'database_url': self._mask_sensitive(self.database_url),
            'database_echo': self.database_echo,
            'database_pool_size': self.database_pool_size,
            'database_max_overflow': self.database_max_overflow,
            'app_environment': self.app_environment,
            'log_level': self.log_level,
            'log_file_path': self.log_file_path,
            'max_concurrent_requests': self.max_concurrent_requests,
            'request_timeout': self.request_timeout,
            'rate_limit_delay': self.rate_limit_delay,
        }

    @staticmethod
    def _mask_sensitive(value: str) -> str:
        """
        Mask sensitive values for logging.

        Args:
            value: Value to mask

        Returns:
            Masked value
        """
        if not value or len(value) < 8:
            return '***'
        return f"{value[:4]}...{value[-4:]}"

    def __repr__(self) -> str:
        """String representation of Config object."""
        return f"<Config environment={self.app_environment}>"


# Global configuration instance
config: Optional[Config] = None


def get_config() -> Config:
    """
    Get or create the global configuration instance.

    Returns:
        Config: The global configuration instance

    Raises:
        ConfigurationError: If configuration validation fails
    """
    global config
    if config is None:
        config = Config()
    return config


def reload_config() -> Config:
    """
    Force reload of configuration from environment.

    Returns:
        Config: New configuration instance

    Raises:
        ConfigurationError: If configuration validation fails
    """
    global config
    Config._initialized = False
    Config._instance = None
    config = None
    return get_config()


if __name__ == '__main__':
    # Test configuration loading
    try:
        cfg = get_config()
        print("Configuration loaded successfully!")
        print("\nConfiguration summary:")
        for key, value in cfg.to_dict().items():
            print(f"  {key}: {value}")
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
