"""
Application Settings and Configuration
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Application Settings
APP_NAME = "ScreenerIII"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Update Interval (in seconds)
UPDATE_INTERVAL = 10  # 10 seconds for real-time updates
DATA_FETCH_TIMEOUT = 5  # Timeout for API calls

# OANDA API Settings
OANDA_API_KEY = os.getenv("OANDA_API_KEY", "")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "live")  # 'live' or 'practice'

# OANDA API Endpoints
OANDA_API_URLS = {
    "live": "https://api-fxtrade.oanda.com",
    "practice": "https://api-fxpractice.oanda.com"
}

# Database Configuration
DATABASE_DIR = BASE_DIR / "data"
DATABASE_NAME = "screener.db"
DATABASE_PATH = DATABASE_DIR / DATABASE_NAME

# Create database directory if it doesn't exist
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# Database Type Selection: 'sqlite', 'postgresql', or 'timescaledb'
# Auto-detect from DATABASE_URL if not explicitly set
DATABASE_URL = os.getenv("DATABASE_URL", "")

def _detect_database_type(url: str) -> str:
    """Auto-detect database type from DATABASE_URL."""
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return "timescaledb" if "timescaledb" in url else "postgresql"
    elif url.startswith("sqlite://"):
        return "sqlite"
    return "sqlite"  # Default to sqlite

DATABASE_TYPE = os.getenv("DATABASE_TYPE", _detect_database_type(DATABASE_URL))

# SQLite Configuration (default)
DATABASE_CONFIG = {
    "path": str(DATABASE_PATH),
    "timeout": 20,
    "check_same_thread": False,
    "isolation_level": None  # Autocommit mode
}

# PostgreSQL/TimescaleDB Configuration
POSTGRES_CONFIG = {
    "url": DATABASE_URL or "postgresql://user:password@localhost:5432/screener",
    "min_pool_size": 5,
    "max_pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 3600,  # Recycle connections after 1 hour
    "echo": DEBUG,  # Echo SQL statements in debug mode
}

# TimescaleDB-Specific Settings
TIMESCALEDB_CONFIG = {
    # Chunk configuration for time-series data
    "chunk_time_interval": os.getenv("TIMESCALEDB_CHUNK_INTERVAL", "1 day"),

    # Compression settings for historical data
    "compression_enabled": os.getenv("TIMESCALEDB_COMPRESSION", "true").lower() == "true",
    "compression_segment_by": "symbol,timeframe",  # Group data by symbol and timeframe
    "compression_order_by": "time DESC",  # Order by time descending

    # Retention policy (default 90 days for market data)
    "retention_days": int(os.getenv("TIMESCALEDB_RETENTION_DAYS", "90")),

    # Compression starts after data is this old (in days)
    "compression_after_days": int(os.getenv("TIMESCALEDB_COMPRESSION_AFTER", "7")),

    # Hypertable settings
    "if_not_exists": True,
    "time_column_name": "time",
}

# Select configuration based on database type
if DATABASE_TYPE == "timescaledb":
    ACTIVE_DATABASE_CONFIG = POSTGRES_CONFIG
elif DATABASE_TYPE == "postgresql":
    ACTIVE_DATABASE_CONFIG = POSTGRES_CONFIG
else:  # sqlite
    ACTIVE_DATABASE_CONFIG = DATABASE_CONFIG

# Logging Configuration
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "screener.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": LOG_FORMAT,
            "datefmt": LOG_DATE_FORMAT
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            "datefmt": LOG_DATE_FORMAT
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": LOG_LEVEL,
            "formatter": "default",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": LOG_LEVEL,
            "formatter": "detailed",
            "filename": str(LOG_FILE),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console", "file"]
    }
}

# Data Storage Settings
DATA_RETENTION_DAYS = 30  # Keep data for 30 days
DATA_CLEANUP_INTERVAL = 86400  # Clean up old data once per day (in seconds)

# Price Data Settings
CANDLE_GRANULARITY = "M1"  # 1-minute candles
CANDLE_COUNT = 200  # Number of candles to fetch for analysis

# Signal Generation Settings
SIGNAL_CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for signal generation
MIN_RISK_REWARD_RATIO = 1.5  # Minimum acceptable risk/reward ratio

# Display Settings
REFRESH_RATE = UPDATE_INTERVAL  # Display refresh rate matches update interval
DECIMAL_PLACES = 5  # Precision for price display
PERCENTAGE_DECIMAL_PLACES = 2  # Precision for percentage display

# Performance Settings
MAX_WORKERS = 4  # Maximum number of concurrent threads for data fetching
CACHE_TIMEOUT = 60  # Cache timeout in seconds

# Models Directory
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Color Schemes (for terminal output)
COLORS = {
    "BUY": "\033[92m",  # Green
    "SELL": "\033[91m",  # Red
    "NEUTRAL": "\033[93m",  # Yellow
    "HEADER": "\033[94m",  # Blue
    "RESET": "\033[0m",  # Reset
    "BOLD": "\033[1m"
}

# Alert Settings
ENABLE_ALERTS = True
ALERT_COOLDOWN = 300  # Minimum time between alerts for same market (in seconds)
