# ScreenerIII - Real-time Commodity Market Scanner

A real-time market scanner for commodity trading with technical analysis and pattern recognition.

## Security Warning

**IMPORTANT: Please read before using this software**

- **Financial Risk**: Trading commodities and financial instruments involves substantial risk. This software is provided for educational and informational purposes. You may lose money. Never trade with money you cannot afford to lose.
- **API Credentials**: Your OANDA API credentials provide access to your trading account. Keep them secure and never share them.
- **Environment File Security**: Never commit your `.env` file to version control. It contains sensitive credentials that could compromise your account.
- **Practice First**: Always test with OANDA's practice environment before using live trading. Set `OANDA_ENVIRONMENT=practice` in your `.env` file.
- **No Guarantees**: Past performance does not guarantee future results. This tool provides technical analysis but cannot predict market movements.

## Features

- Real-time market data from OANDA
- 10-second interval updates
- Technical analysis with multiple indicators
- Pattern recognition
- Risk/reward calculation
- Grouped view by commodity type
- Color-coded signals and trends
- SQLite database for data storage
- Automated signal generation

## Supported Markets

### Precious Metals
- Gold (XAU_USD)
- Silver (XAG_USD)
- Platinum (XPT_USD)
- Palladium (XPD_USD)

### Energy
- Brent Crude (BCO_USD)
- WTI Crude (WTICO_USD)
- Natural Gas (NATGAS_USD)

### Agriculture
- Corn (CORN_USD)
- Soybeans (SOYBN_USD)
- Wheat (WHEAT_USD)
- Sugar (SUGAR_USD)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ScreenerIII.git
cd ScreenerIII
```

2. Create a virtual environment and activate it:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your OANDA credentials:

**IMPORTANT**: Use the practice environment first! Copy from `.env.example` template if available.

```bash
# Create your .env file
cp .env.example .env  # If .env.example exists, otherwise create manually
```

Edit your `.env` file:
```
OANDA_API_KEY=your_api_key_here
OANDA_ACCOUNT_ID=your_account_id_here
OANDA_ENVIRONMENT=practice  # Use 'practice' for testing, 'live' for real trading
```

**Security Notes**:
- Never commit your `.env` file to version control
- The `.env` file is already in `.gitignore` to prevent accidental commits
- Start with `practice` environment to test without financial risk
- Only switch to `live` when you're confident and understand the risks

## Quick Start with Docker

Docker makes it easy to run ScreenerIII with TimescaleDB without manual installation. TimescaleDB is a time-series database built on PostgreSQL that provides excellent performance for historical market data and technical analysis results.

### Prerequisites

- Docker and Docker Compose installed
- OANDA API credentials

### Setup with Docker

1. **Copy the environment template:**
```bash
cp .env.example .env
```

2. **Edit your `.env` file with your OANDA credentials:**
```bash
nano .env  # or your favorite editor
```

Update the following variables:
```
OANDA_API_KEY=your_api_key_here
OANDA_ACCOUNT_ID=your_account_id_here
OANDA_ENVIRONMENT=practice  # Use 'practice' for testing
```

3. **Start TimescaleDB and the application:**

Start just the database:
```bash
docker-compose up -d timescaledb
```

Start database with pgAdmin (for database management UI at http://localhost:5050):
```bash
docker-compose --profile with-pgadmin up -d
```

Start full stack (database + pgAdmin + application):
```bash
docker-compose --profile with-app --profile with-pgadmin up -d
```

4. **Check service status:**
```bash
docker-compose ps
docker-compose logs -f timescaledb
```

### Docker Commands Reference

**View logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f timescaledb
docker-compose logs -f pgadmin
docker-compose logs -f screeneriii
```

**Access database directly:**
```bash
# Connect to TimescaleDB via psql
docker-compose exec timescaledb psql -U screener_user -d screener_db

# Example queries:
# \dt                    # List all tables
# SELECT * FROM instruments;
# SELECT * FROM price_data LIMIT 10;
```

**Access pgAdmin:**
- Open http://localhost:5050 in your browser
- Login with credentials from `.env` (default: admin@screener.local / admin_password)
- Add server connection to TimescaleDB:
  - Hostname: `timescaledb`
  - Username: `screener_user` (from .env)
  - Password: `screener_password` (from .env)

**Stop services:**
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes database data!)
docker-compose down -v
```

**Restart services:**
```bash
docker-compose restart timescaledb
```

### Environment Variables for Docker

Create a `.env` file based on `.env.example` with these key variables:

```
# OANDA API
OANDA_API_KEY=your_key
OANDA_ACCOUNT_ID=your_account_id
OANDA_ENVIRONMENT=practice

# TimescaleDB
POSTGRES_DB=screener_db
POSTGRES_USER=screener_user
POSTGRES_PASSWORD=screener_password
TIMESCALEDB_PORT=5432

# pgAdmin (optional)
PGADMIN_EMAIL=admin@screener.local
PGADMIN_PASSWORD=admin_password
PGADMIN_PORT=5050

# Application
UPDATE_INTERVAL=10
LOG_LEVEL=INFO
```

### Database Schema

TimescaleDB is automatically initialized with the following tables:

- **price_data**: Raw market price data (OHLCV) - stores bid/ask, spreads, volume
- **analysis_results**: Technical indicators and analysis (RSI, MACD, Bollinger Bands, ATR, etc.)
- **trading_signals**: Generated trading signals with entry/target/stop levels
- **instruments**: Metadata for all supported commodities

All price and analysis tables are optimized as TimescaleDB hypertables for excellent performance with time-series data. Retention policies are configured to automatically manage data storage.

### Data Persistence

Data is persisted in Docker volumes:
- `timescaledb_data`: Database files (survives container restarts)
- `pgadmin_data`: pgAdmin configuration

To backup your database:
```bash
docker-compose exec timescaledb pg_dump -U screener_user screener_db > backup.sql
```

To restore:
```bash
docker-compose exec -T timescaledb psql -U screener_user screener_db < backup.sql
```

### Troubleshooting Docker Setup

**Port already in use:**
```bash
# Change ports in .env file
TIMESCALEDB_PORT=5433  # Use different port
PGADMIN_PORT=5051
```

**Database connection errors:**
```bash
# Check if TimescaleDB is healthy
docker-compose ps
# Status should show "healthy" for timescaledb

# View logs
docker-compose logs timescaledb
```

**Rebuild images after code changes:**
```bash
docker-compose build --no-cache
docker-compose up -d
```

## Development Setup

For developers who want to contribute or run tests:

1. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Development tools included:
   - **pytest**: Testing framework
   - **pytest-cov**: Code coverage reporting
   - **black**: Code formatter
   - **flake8**: Style guide enforcement
   - **mypy**: Static type checking
   - **bandit**: Security vulnerability scanner
   - **pre-commit**: Git hooks for code quality
   - **ipython**: Enhanced interactive shell
   - **pytest-mock**: Mocking framework for tests

3. Set up pre-commit hooks (optional but recommended):
```bash
pre-commit install
```

## Usage

Run the scanner:
```bash
python main.py
```

## Testing

The project includes a comprehensive test suite with unit and integration tests.

### Running Tests

Run all tests:
```bash
pytest
```

Run tests with coverage report:
```bash
pytest --cov=src --cov-report=html --cov-report=term
```

Run specific test categories:
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Run tests matching a pattern
pytest -k "test_data"
```

Run tests with verbose output:
```bash
pytest -v
```

### Test Structure

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for system workflows
└── __init__.py
```

### Coverage Reports

After running tests with coverage, view the HTML report:
```bash
# Coverage report is generated in htmlcov/
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Output

The scanner displays:
- Current prices and spreads
- 24-hour price changes
- Technical signals
- Trade direction
- Target and stop levels
- Risk/reward ratios
- Volatility measures (ATR)
- Volume information
- Signal confidence levels

## Architecture

ScreenerIII follows a modular architecture with clear separation of concerns:

### Core Components

#### 1. Data Layer (`src/data/`)
- **Market Data Collection**: Interfaces with OANDA API to fetch real-time price data
- **Database Management**: SQLite storage for historical data and analysis results
- **Data Validation**: Ensures data integrity and handles API errors
- **Rate Limiting**: Manages API call frequency to respect OANDA limits

#### 2. Analysis Layer (`src/analysis/`)
- **Technical Indicators**: Calculates RSI, MACD, Bollinger Bands, ATR, and more
- **Pattern Recognition**: Identifies chart patterns and trading setups
- **Signal Generation**: Produces buy/sell signals based on technical analysis
- **Risk Calculation**: Computes stop-loss, take-profit, and risk/reward ratios

#### 3. Core Engine (`src/core/`)
- **Scanner Engine**: Orchestrates data collection and analysis cycles
- **Market Manager**: Manages multiple commodity instruments
- **Update Scheduler**: Handles 10-second interval updates
- **State Management**: Tracks scanner state and configuration

#### 4. Interface Layer (`src/interface/`)
- **Dashboard Display**: Terminal-based UI with color-coded outputs
- **Data Formatting**: Presents analysis results in readable format
- **Grouping Logic**: Organizes commodities by category (metals, energy, agriculture)
- **Real-time Updates**: Refreshes display with latest market data

#### 5. Utilities (`src/utils/`)
- **Configuration Management**: Loads settings from config files
- **Logging**: Application logging and error tracking
- **Helper Functions**: Common utilities used across modules

### Data Flow

1. **Collection**: OANDA API → Data Layer → SQLite Database
2. **Analysis**: Database → Analysis Layer → Technical Indicators → Signals
3. **Display**: Signals → Interface Layer → Terminal Dashboard
4. **Loop**: Repeat every 10 seconds

### Design Principles

- **Modularity**: Each component has a single, well-defined responsibility
- **Extensibility**: Easy to add new indicators, patterns, or data sources
- **Testability**: Clear interfaces enable comprehensive unit testing
- **Error Handling**: Graceful degradation when API or data issues occur

## Project Structure

```
ScreenerIII/
├── config/          # Configuration files
├── src/
│   ├── core/        # Core engine components
│   ├── data/        # Data collection and storage
│   ├── analysis/    # Technical analysis and patterns
│   ├── interface/   # Dashboard and UI
│   └── utils/       # Utility functions
├── tests/
│   ├── unit/        # Unit tests
│   └── integration/ # Integration tests
├── data/           # Data storage
├── logs/           # Application logs
├── models/         # Saved analysis models
├── docs/           # Documentation
├── requirements.txt      # Production dependencies
└── requirements-dev.txt  # Development dependencies
```

## API Rate Limits

### OANDA API Limitations

When using OANDA's API, be aware of the following rate limits:

#### Practice Environment
- **Rate Limit**: 120 requests per second
- **Burst Limit**: Higher temporary bursts allowed
- **Best for**: Testing and development without financial risk

#### Live Environment
- **Rate Limit**: Varies by account type (typically 100-120 requests/second)
- **Stricter Limits**: May have additional constraints based on account tier
- **Best for**: Production use with real capital

### ScreenerIII Rate Management

The scanner is configured to update every 10 seconds for all instruments:

- **Update Interval**: 10 seconds
- **Instruments Tracked**: 11 commodities
- **Estimated API Calls**: ~6-12 calls per update cycle (depending on data requirements)
- **Calls Per Minute**: ~40-80 (well within OANDA limits)

### Best Practices

1. **Start Conservative**: Use longer update intervals during testing
2. **Monitor Usage**: Check OANDA dashboard for API usage statistics
3. **Handle Rate Limit Errors**: The scanner includes retry logic with exponential backoff
4. **Batch Requests**: Where possible, the scanner batches instrument requests
5. **Cache Data**: Historical data is cached in SQLite to minimize API calls

### Rate Limit Error Handling

If you encounter rate limit errors (HTTP 429):
- The scanner will automatically retry with exponential backoff
- Consider increasing the update interval in configuration
- Check for multiple instances running simultaneously
- Review OANDA account status and tier limits

## Troubleshooting

### Common Issues and Solutions

#### 1. Authentication Errors

**Problem**: `401 Unauthorized` or authentication failures

**Solutions**:
- Verify your `OANDA_API_KEY` is correct in `.env`
- Ensure `OANDA_ACCOUNT_ID` matches your OANDA account
- Check that API key is not expired (generate a new one in OANDA dashboard)
- Confirm you're using the correct environment (`practice` vs `live`)

#### 2. No Data Received

**Problem**: Scanner runs but shows no market data

**Solutions**:
- Check your internet connection
- Verify OANDA API status (https://status.oanda.com/)
- Ensure the markets are open (commodities have different trading hours)
- Check logs in `logs/` directory for detailed error messages
- Verify instrument names are correct in configuration

#### 3. Database Errors

**Problem**: SQLite database issues or corruption

**Solutions**:
```bash
# Backup and reset database
mv data/screener.db data/screener.db.backup
# The scanner will create a new database on next run
```

- Ensure `data/` directory exists and is writable
- Check disk space availability
- Review file permissions on database file

#### 4. Missing Dependencies

**Problem**: `ModuleNotFoundError` when running the scanner

**Solutions**:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### 5. Rate Limit Errors

**Problem**: HTTP 429 errors or "Too Many Requests"

**Solutions**:
- Reduce update frequency in configuration
- Check for multiple scanner instances running
- Wait a few minutes before retrying
- Upgrade OANDA account tier for higher limits

#### 6. Performance Issues

**Problem**: Scanner is slow or unresponsive

**Solutions**:
- Reduce number of tracked instruments
- Increase update interval
- Check system resources (CPU, memory)
- Review and optimize database queries
- Clear old data from database:
```bash
# Backup first
sqlite3 data/screener.db "DELETE FROM prices WHERE timestamp < date('now', '-30 days');"
```

#### 7. Environment Variable Not Loading

**Problem**: `.env` file variables not being read

**Solutions**:
- Ensure `.env` file is in the project root directory
- Check file name is exactly `.env` (not `.env.txt`)
- Verify no spaces around `=` in variable definitions
- Restart the scanner after modifying `.env`
- Check that `python-dotenv` is installed

#### 8. Display Issues

**Problem**: Colors or formatting look wrong in terminal

**Solutions**:
- Use a terminal that supports ANSI colors
- On Windows, use Windows Terminal or enable ANSI in Command Prompt
- Try running in different terminal emulator
- Check terminal encoding is set to UTF-8

### Getting Help

If you encounter issues not covered here:

1. **Check Logs**: Review files in `logs/` directory for detailed error traces
2. **Enable Debug Mode**: Set log level to DEBUG in configuration
3. **OANDA Documentation**: https://developer.oanda.com/rest-live-v20/introduction/
4. **GitHub Issues**: Report bugs or request features on the project repository
5. **Test in Practice Mode**: Always troubleshoot in practice environment first

### Diagnostic Commands

Run these commands to gather diagnostic information:

```bash
# Check Python version
python --version

# Verify dependencies
pip list | grep -E "(oanda|pandas|numpy|requests)"

# Test database connection
sqlite3 data/screener.db ".tables"

# Check environment variables (without exposing secrets)
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key loaded:', bool(os.getenv('OANDA_API_KEY')))"

# View recent logs
tail -n 50 logs/screener.log
```

## Requirements

- Python 3.9+
- OANDA API access
- Required Python packages listed in requirements.txt

## License

This project is licensed under the MIT License - see the LICENSE file for details.