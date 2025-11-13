# ScreenerIII Troubleshooting Guide

## Quick Diagnostics

### Check System Status

```bash
# Verify Python version (3.9+ required)
python --version

# Check if virtual environment is active
which python

# Verify dependencies are installed
pip list | grep -E "pandas|numpy|oandapyV20|sqlalchemy"

# Check if .env file exists
ls -la .env

# Test database connection
sqlite3 data/screener.db ".tables"

# Check log files
tail -f logs/screener_*.log
```

---

## Common Issues and Solutions

### 1. Configuration and Setup Issues

#### Issue: ".env file not found"

**Error Message**:
```
ERROR: .env file not found!
Please create a .env file with the following variables:
  OANDA_API_KEY=your_api_key_here
  OANDA_ACCOUNT_ID=your_account_id_here
  OANDA_ENVIRONMENT=live
```

**Causes**:
- .env file does not exist in project root
- File name is incorrect (case-sensitive on Linux/macOS)
- File was deleted or moved

**Solutions**:
1. Create .env file in project root:
   ```bash
   cd /home/user/ScreenerIII
   touch .env
   ```

2. Add required variables:
   ```bash
   cat > .env << EOF
   OANDA_API_KEY=your_actual_api_key
   OANDA_ACCOUNT_ID=your_actual_account_id
   OANDA_ENVIRONMENT=practice
   EOF
   ```

3. Verify file was created:
   ```bash
   ls -la .env
   cat .env
   ```

**Prevention**:
- Never delete or rename .env file
- Keep .env in .gitignore to prevent accidental commits
- Use .env.example as template for documentation

---

#### Issue: "Missing required environment variables"

**Error Message**:
```
ERROR: Missing required environment variables!
The following variables are missing or empty in .env:
  - OANDA_API_KEY
  - OANDA_ACCOUNT_ID
```

**Causes**:
- Variables not set in .env file
- Empty values (just the key without value)
- Syntax error in .env file

**Solutions**:
1. Check .env file contents:
   ```bash
   cat .env
   ```

2. Verify format is correct (no spaces around =):
   ```
   OANDA_API_KEY=abc123xyz   ✓ Correct
   OANDA_API_KEY = abc123xyz ✗ Wrong (spaces around =)
   OANDA_API_KEY=            ✗ Wrong (empty value)
   ```

3. Re-create .env with proper format:
   ```bash
   cat > .env << 'EOF'
   OANDA_API_KEY=your_api_token_here
   OANDA_ACCOUNT_ID=123-456-7890-123
   OANDA_ENVIRONMENT=practice
   UPDATE_INTERVAL=10
   LOG_LEVEL=INFO
   EOF
   ```

4. Verify values are set:
   ```bash
   grep -v "^#" .env | grep "=" | wc -l
   ```

---

#### Issue: "Invalid OANDA_ENVIRONMENT"

**Error Message**:
```
ERROR: Invalid OANDA_ENVIRONMENT!
OANDA_ENVIRONMENT must be either 'live' or 'practice'
```

**Causes**:
- Typo in environment value (e.g., 'Practice' instead of 'practice')
- Case sensitivity (Python is case-sensitive)
- Invalid value

**Solutions**:
1. Check current value:
   ```bash
   grep OANDA_ENVIRONMENT .env
   ```

2. Fix to lowercase 'practice' or 'live':
   ```bash
   sed -i 's/OANDA_ENVIRONMENT=.*/OANDA_ENVIRONMENT=practice/' .env
   ```

3. Verify change:
   ```bash
   grep OANDA_ENVIRONMENT .env
   ```

**Warning**: Always use 'practice' environment first for testing!

---

### 2. API Connection Issues

#### Issue: "Connection test failed"

**Error Message**:
```
ERROR: Connection test failed: [error details]
Connection status: ERROR
Last error: [specific API error]
```

**Causes**:
- Invalid API credentials
- API key revoked or expired
- Wrong environment (live vs practice)
- Network connectivity issues
- OANDA API server down

**Solutions**:

1. **Verify API credentials**:
   ```bash
   # Check if credentials exist
   grep -E "OANDA_API_KEY|OANDA_ACCOUNT_ID" .env

   # Count characters (typical API key length)
   grep OANDA_API_KEY .env | cut -d= -f2 | wc -c
   ```

2. **Check network connectivity**:
   ```bash
   # Test internet connection
   ping google.com

   # Test API endpoint (depending on environment)
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://api-fxpractice.oanda.com/v3/accounts
   ```

3. **Verify environment matches credentials**:
   - If using practice API credentials, set `OANDA_ENVIRONMENT=practice`
   - If using live API credentials, set `OANDA_ENVIRONMENT=live`

4. **Check OANDA account status**:
   - Log in to OANDA website
   - Verify account is active
   - Check if API access is enabled
   - Verify API token hasn't expired

5. **Review OANDA API status**:
   ```bash
   # Visit OANDA status page
   # https://status.oanda.com/
   ```

6. **Enable debug logging**:
   ```bash
   # Add to .env
   LOG_LEVEL=DEBUG

   # Restart application and check logs
   tail -f logs/screener_*.log
   ```

---

#### Issue: "Rate limit exceeded"

**Error Message**:
```
WARNING: Rate limit exceeded, waiting before retry
ConnectionStatus: RATE_LIMITED
Connection status: RATE_LIMITED
```

**Causes**:
- Making too many API requests per minute (OANDA limit: 120 req/min)
- Multiple instances running simultaneously
- Rapid requests in tight loop

**Solutions**:

1. **Increase UPDATE_INTERVAL**:
   ```bash
   # Reduce request frequency
   sed -i 's/UPDATE_INTERVAL=.*/UPDATE_INTERVAL=30/' .env  # 30 seconds
   ```

2. **Stop other instances**:
   ```bash
   # Find running Python processes
   ps aux | grep "python main.py"

   # Kill other instances
   kill -9 <pid>
   ```

3. **Check for rapid loops**:
   - Review application code for tight loops
   - Verify wait times between requests

4. **Monitor request rates**:
   ```bash
   # Count requests in logs
   tail -f logs/screener_*.log | grep -i "request\|fetch"
   ```

**Prevention**:
- Keep UPDATE_INTERVAL >= 10 seconds
- Run only one instance
- Implement proper rate limiter (already done in client)

---

#### Issue: "Server error (5xx)"

**Error Message**:
```
Server error 502, attempt 1 of 3
Connection failed after retries: Bad Gateway
```

**Causes**:
- OANDA API server temporarily down
- Network connectivity issue
- Request timeout

**Solutions**:

1. **Wait and retry**:
   ```bash
   # Application has automatic retry (up to 3 times)
   # Wait 30-60 seconds and it should recover
   ```

2. **Check OANDA status**:
   - https://status.oanda.com/
   - Wait for service to be restored

3. **Increase max retries**:
   ```python
   # In code: increase max_retries parameter
   client = OANDAClient(
       api_token=token,
       account_id=account_id,
       environment="practice",
       max_retries=5  # Increase from 3
   )
   ```

4. **Check network**:
   ```bash
   # Test connectivity to OANDA
   curl -I https://api-fxpractice.oanda.com/v3/accounts

   # Check DNS resolution
   nslookup api-fxpractice.oanda.com
   ```

---

### 3. Database Issues

#### Issue: "Database initialization failed"

**Error Message**:
```
ERROR: Database initialization failed: [error details]
Database error: [SQLAlchemy error]
```

**Causes**:
- Database file corrupted
- Disk space full
- File permissions issue
- SQLite locked by another process

**Solutions**:

1. **Check database file**:
   ```bash
   # Verify database exists and is readable
   ls -lh data/screener.db

   # Check file integrity
   sqlite3 data/screener.db ".schema"
   ```

2. **Check disk space**:
   ```bash
   # Verify sufficient disk space
   df -h

   # Check data directory size
   du -sh data/
   ```

3. **Fix file permissions**:
   ```bash
   # Make database world-readable/writable
   chmod 666 data/screener.db
   chmod 755 data/
   ```

4. **Unlock database**:
   ```bash
   # Check for locked database
   lsof data/screener.db

   # Kill process holding lock
   kill -9 <pid>
   ```

5. **Backup and recreate**:
   ```bash
   # Backup current database
   cp data/screener.db data/screener.db.backup

   # Remove corrupted database
   rm data/screener.db

   # Application will create new database on restart
   ```

---

#### Issue: "Database timeout"

**Error Message**:
```
sqlite3.OperationalError: database is locked
```

**Causes**:
- Another process accessing database
- Transaction not committed
- Timeout too short

**Solutions**:

1. **Check database access**:
   ```bash
   # Find processes using database
   lsof data/screener.db
   ```

2. **Increase timeout**:
   ```python
   # In config/settings.py
   DATABASE_CONFIG = {
       "timeout": 30,  # Increase from 20
       "check_same_thread": False,
       "isolation_level": None
   }
   ```

3. **Close other connections**:
   ```bash
   # Stop other application instances
   pkill -f "python main.py"
   ```

4. **Reset database**:
   ```bash
   # Remove database and let app recreate it
   rm data/screener.db
   ```

---

### 4. Logging and Monitoring Issues

#### Issue: "Log file not created"

**Error Message**:
```
Failed to initialize logging: [error details]
```

**Causes**:
- logs/ directory doesn't exist
- No write permissions
- Disk space full

**Solutions**:

1. **Create logs directory**:
   ```bash
   mkdir -p logs
   chmod 755 logs
   ```

2. **Check permissions**:
   ```bash
   ls -ld logs
   # Should show rwx for owner
   ```

3. **Check disk space**:
   ```bash
   df -h
   ```

4. **Verify logs directory exists before running**:
   ```bash
   # Create directory in main.py if missing (already done)
   ```

---

#### Issue: "No log output"

**Causes**:
- Log level set too high (ERROR only, INFO messages hidden)
- Logger not initialized
- Logs written to file only, not console

**Solutions**:

1. **Check log level**:
   ```bash
   grep LOG_LEVEL .env
   ```

2. **Lower log level for debugging**:
   ```bash
   echo "LOG_LEVEL=DEBUG" >> .env
   ```

3. **Check log files**:
   ```bash
   ls -la logs/
   tail -f logs/screener_*.log
   ```

4. **Enable console output**:
   - Logs are written to both console and file
   - If no console output, check terminal settings

---

### 5. Performance Issues

#### Issue: "Application running slowly"

**Symptoms**:
- Slow market data updates
- Delayed indicator calculation
- High CPU usage

**Causes**:
- Too many markets being monitored
- Indicator calculation inefficiency
- Database queries too complex
- Hardware limitations

**Solutions**:

1. **Monitor system resources**:
   ```bash
   # Check CPU usage
   top -p $(pgrep -f "python main.py")

   # Check memory usage
   ps aux | grep "python main.py"

   # Check disk I/O
   iostat -x 1
   ```

2. **Reduce market count**:
   ```python
   # In config/markets.py, comment out unused markets
   # Focus on 3-4 markets instead of all 12
   ```

3. **Increase update interval**:
   ```bash
   # Reduce frequency of updates
   echo "UPDATE_INTERVAL=30" >> .env  # 30 seconds instead of 10
   ```

4. **Optimize queries**:
   - Review database queries
   - Add indexes to frequently queried columns
   - Use connection pooling

5. **Check resource availability**:
   ```bash
   # Free up memory
   free -h

   # Check available CPU cores
   nproc

   # Check temperature (if available)
   sensors
   ```

---

#### Issue: "High CPU usage"

**Causes**:
- Tight loops without sleep
- Inefficient indicator calculations
- Database locking

**Solutions**:

1. **Check for busy loops**:
   ```bash
   # Review application code for loops
   grep -n "while True" src/

   # Verify sleep/wait exists
   grep -n "sleep\|time.sleep\|wait" src/
   ```

2. **Profile application**:
   ```python
   import cProfile
   import pstats

   profiler = cProfile.Profile()
   profiler.enable()

   # ... your code ...

   profiler.disable()
   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative')
   stats.print_stats(20)
   ```

3. **Reduce parallelization**:
   ```bash
   # Lower MAX_WORKERS in config/settings.py
   MAX_WORKERS=2  # Instead of 4
   ```

---

### 6. Data Quality Issues

#### Issue: "Missing or invalid market data"

**Error Message**:
```
Failed to fetch prices for [symbol]
Unexpected error: Invalid response format
```

**Causes**:
- API returning incomplete data
- Network packet loss
- Data parsing error

**Solutions**:

1. **Check API response**:
   ```bash
   # Enable debug logging
   echo "LOG_LEVEL=DEBUG" >> .env

   # Check logs for response details
   tail logs/screener_*.log | grep -i "response\|data"
   ```

2. **Verify market symbols**:
   ```python
   from config.markets import ALL_MARKET_SYMBOLS
   print(ALL_MARKET_SYMBOLS)
   ```

3. **Test API directly**:
   ```bash
   # Test with curl
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        "https://api-fxpractice.oanda.com/v3/accounts/YOUR_ACCOUNT/pricing?instruments=XAU_USD"
   ```

4. **Check data format**:
   - Verify JSON parsing
   - Check for required fields
   - Validate data types

---

#### Issue: "Outdated or stale data"

**Symptoms**:
- Prices not updating
- Old timestamp in data
- Delays between updates

**Causes**:
- API not responding
- Network latency
- Application paused

**Solutions**:

1. **Check update timestamp**:
   ```bash
   # Monitor logs for update times
   tail -f logs/screener_*.log | grep "time\|update"
   ```

2. **Verify network connectivity**:
   ```bash
   ping -c 5 api-fxpractice.oanda.com
   ```

3. **Check market hours**:
   - Some commodities have trading hours
   - Verify market is open
   - Check for weekend gaps

4. **Review update loop**:
   ```python
   # In main.py, verify loop timing
   # Should see update every UPDATE_INTERVAL seconds
   ```

---

### 7. Platform-Specific Issues

#### Linux Issues

##### Permission Denied Errors

```bash
# Make script executable
chmod +x main.py

# Fix directory permissions
chmod 755 logs/ data/

# Fix file permissions
chmod 644 config/*.py src/**/*.py
```

##### Path Issues

```bash
# Use absolute paths
cd /home/user/ScreenerIII

# Don't use relative paths
# Wrong: python main.py
# Right: python /home/user/ScreenerIII/main.py
```

#### macOS Issues

##### SSL Certificate Errors

```bash
# Install certificates
/Applications/Python\ 3.x/Install\ Certificates.command

# Or use certifi
pip install --upgrade certifi
```

##### M1/M2 Chip Compatibility

```bash
# Install ARM-compatible packages
pip install --upgrade pandas numpy

# Use native Python, not x86 emulation
file $(which python)
```

#### Windows Issues

##### Path Separators

```python
# Use pathlib for cross-platform paths
from pathlib import Path
db_path = Path("data") / "screener.db"

# Or use forward slashes
db_path = "data/screener.db"  # Works on all platforms
```

##### Virtual Environment Issues

```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Or use PowerShell
.venv\Scripts\Activate.ps1
```

---

### 8. Development and Testing Issues

#### Issue: "Tests failing"

**Solutions**:
```bash
# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_oanda_client.py -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run with specific markers
pytest -m "not integration" -v
```

#### Issue: "Import errors"

**Solutions**:
```bash
# Verify package is installed
pip list | grep oandapyV20

# Install missing dependencies
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"

# Verify module can be imported
python -c "from src.data.oanda_client import OANDAClient"
```

---

## Diagnostic Commands Reference

```bash
# Overall system health
python --version
pip list
df -h
free -h

# Application status
ps aux | grep "python main.py"
lsof -i :8000  # If using web server

# Database health
sqlite3 data/screener.db "PRAGMA integrity_check;"
sqlite3 data/screener.db ".tables"

# Network connectivity
ping api-fxpractice.oanda.com
curl -I https://api-fxpractice.oanda.com

# Log analysis
tail -n 100 logs/screener_*.log
grep -i "error\|warning" logs/screener_*.log

# Environment variables
env | grep OANDA
grep -v "^#" .env | grep "="

# Process management
pgrep -f "python main.py"
ps aux | grep "python main.py"
kill -9 <pid>
```

---

## Getting Help

### Information to Provide

When reporting issues, include:

1. **Error message** (exact text)
2. **Log file excerpt** (last 50 lines)
3. **System info**:
   ```bash
   python --version
   pip list | grep -E "pandas|numpy|oandapyV20|SQLAlchemy"
   uname -a
   ```

4. **Steps to reproduce**
5. **Environment settings** (without credentials)
6. **Terminal output** (full error trace)

### Resources

- OANDA API Documentation: https://developer.oanda.com/
- Python Documentation: https://docs.python.org/3/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- GitHub Issues: Create issue with diagnostic info

---

## Prevention Tips

1. **Regular backups**:
   ```bash
   cp -r data/ data.backup.$(date +%Y%m%d)
   ```

2. **Monitor logs regularly**:
   ```bash
   watch -n 5 'tail logs/screener_*.log'
   ```

3. **Test after configuration changes**:
   ```bash
   python -c "from main import ScreenerApp; app = ScreenerApp(); app.test_connection()"
   ```

4. **Keep dependencies updated**:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

5. **Document your setup**:
   - Save .env.example with template
   - Document any custom configurations
   - Keep change log

6. **Use version control**:
   ```bash
   git status
   git add .
   git commit -m "Configuration update"
   ```
