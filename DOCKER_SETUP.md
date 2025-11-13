# ScreenerIII Docker Setup Guide

This document provides a quick reference for the Docker configuration files created for ScreenerIII.

## Files Created

### 1. docker-compose.yml (111 lines)
**Location:** `/home/user/ScreenerIII/docker-compose.yml`

Main orchestration file that defines all services:
- **timescaledb**: TimescaleDB (PostgreSQL 15) with persistent volume
- **pgadmin**: Database management UI (optional, via `--profile with-pgadmin`)
- **screeneriii**: Python application container (optional, via `--profile with-app`)

Features:
- Health checks for database availability
- Environment variable configuration
- Persistent volumes for data
- Logging configuration with rotation
- Network isolation

### 2. Dockerfile (49 lines)
**Location:** `/home/user/ScreenerIII/Dockerfile`

Container definition for the ScreenerIII Python application:
- Base: Python 3.11-slim for minimal size
- Installs system dependencies (build tools, PostgreSQL client)
- Installs Python requirements
- Creates non-root user for security
- Includes health check
- Default command: `python main.py`

### 3. .dockerignore (108 lines)
**Location:** `/home/user/ScreenerIII/.dockerignore`

Excludes unnecessary files from Docker build context:
- Virtual environments, caches, logs
- Git history, IDE configs
- Database files, test artifacts
- OS-specific files
- Reduces image size significantly

### 4. docker/init.sql (174 lines)
**Location:** `/home/user/ScreenerIII/docker/init.sql`

Automatic database initialization script executed on container startup:

**Tables Created:**
- `price_data`: Raw market prices (bid, ask, volume)
- `analysis_results`: Technical indicators (RSI, MACD, Bollinger Bands, ATR, etc.)
- `trading_signals`: Generated trading signals with entry/target/stop levels
- `instruments`: Metadata for all 11 supported commodities

**Features:**
- TimescaleDB hypertables for optimal time-series performance
- Automatic index creation
- Retention policies (90 days for price data, 1 year for signals)
- Continuous aggregate for daily OHLC data
- Supports 11 commodities (4 metals, 3 energy, 4 agriculture)

**Retention Policies:**
- Raw price data: 90 days
- Analysis results: 90 days
- Trading signals: 365 days

### 5. .env.example (25 lines)
**Location:** `/home/user/ScreenerIII/.env.example`

Template for environment variables:
- OANDA API credentials
- TimescaleDB configuration
- pgAdmin settings
- Application parameters
- Docker project name

## Quick Start Commands

### 1. Setup
```bash
# Copy and configure environment
cp .env.example .env
nano .env  # Edit with your OANDA credentials
```

### 2. Start Services

Database only:
```bash
docker-compose up -d timescaledb
```

Database + pgAdmin (UI at http://localhost:5050):
```bash
docker-compose --profile with-pgadmin up -d
```

Full stack (database + pgAdmin + app):
```bash
docker-compose --profile with-app --profile with-pgadmin up -d
```

### 3. Monitor
```bash
docker-compose ps
docker-compose logs -f timescaledb
```

### 4. Access Database
```bash
docker-compose exec timescaledb psql -U screener_user -d screener_db
```

### 5. Stop Services
```bash
docker-compose down
docker-compose down -v  # Also remove volumes (WARNING: deletes data!)
```

## Key Configuration

### Environment Variables (.env file)

```
# OANDA API
OANDA_API_KEY=your_key_here
OANDA_ACCOUNT_ID=your_account_here
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

## Database Schema

### price_data (TimescaleDB hypertable)
- time (TIMESTAMPTZ) - Time of price
- instrument_id, symbol - Commodity identifier
- bid, ask, spread - Price data
- volume - Trading volume
- Indexed for fast queries by instrument and time

### analysis_results (TimescaleDB hypertable)
- time, instrument_id, symbol
- Technical indicators: RSI, MACD, Bollinger Bands, ATR, SMA
- Signal type and confidence level
- Indexed by instrument and signal type

### trading_signals
- Entry price, target, stop loss
- Risk/reward ratio
- Status tracking (active/closed)
- Historical record for backtesting

### instruments
- Metadata for all 11 commodities
- Category: Precious Metals, Energy, Agriculture
- Descriptions and exchange info

## Data Persistence

Data survives container restarts:
- `timescaledb_data`: Database files
- `pgadmin_data`: pgAdmin configuration

### Backup Database
```bash
docker-compose exec timescaledb pg_dump -U screener_user screener_db > backup.sql
```

### Restore Database
```bash
docker-compose exec -T timescaledb psql -U screener_user screener_db < backup.sql
```

## Troubleshooting

### Port Already in Use
Edit .env to use different ports:
```
TIMESCALEDB_PORT=5433
PGADMIN_PORT=5051
```

### Database Connection Errors
```bash
docker-compose logs timescaledb
docker-compose ps  # Check if healthy
```

### Rebuild After Code Changes
```bash
docker-compose build --no-cache
docker-compose up -d
```

## Related Documentation

- Full setup instructions: See `README.md` "Quick Start with Docker" section
- OANDA API: https://developer.oanda.com/
- TimescaleDB: https://docs.timescale.com/
- PostgreSQL: https://www.postgresql.org/docs/

## File Locations

```
ScreenerIII/
├── docker-compose.yml        # Main orchestration
├── Dockerfile                # App container definition
├── .dockerignore             # Docker build exclusions
├── .env.example              # Configuration template
├── docker/
│   └── init.sql              # Database initialization
└── README.md                 # Updated with Docker section
```

---
Created: 2025-11-13
