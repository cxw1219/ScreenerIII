# ScreenerIII Alert System

Comprehensive alert system for ScreenerIII with support for multiple notification channels, priority levels, rate limiting, and alert history tracking.

## Features

- **Multiple Alert Channels**: Email, Desktop notifications, Telegram
- **Alert Types**: Signal, Price, Risk, System
- **Priority Levels**: LOW, MEDIUM, HIGH, CRITICAL
- **Rate Limiting**: Prevent alert spam with configurable limits
- **Deduplication**: Avoid duplicate alerts within time windows
- **Alert History**: Track all sent alerts in database
- **Template-based Messages**: HTML emails and Markdown Telegram messages
- **Statistics**: View alert metrics and success rates

## Quick Start

### 1. Installation

Install required dependencies:

```bash
pip install -r requirements.txt
```

Required packages:
- `plyer>=2.1.0` - Desktop notifications (cross-platform)
- `python-telegram-bot>=20.0` - Telegram bot integration

### 2. Configuration

Copy `.env.example` to `.env` and configure alert settings:

```bash
cp .env.example .env
```

Edit `.env` to configure your alert channels:

```env
# Enable/disable channels
ALERT_ENABLE_EMAIL=false
ALERT_ENABLE_DESKTOP=true
ALERT_ENABLE_TELEGRAM=false

# Alert thresholds
ALERT_MIN_CONFIDENCE=0.7

# Email settings (if enabled)
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Telegram settings (if enabled)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Rate limiting
ALERT_RATE_LIMIT_SECONDS=300
ALERT_MAX_PER_HOUR=20
```

### 3. Basic Usage

```python
from src.interface.alerts import get_alert_manager, send_signal_alert

# Get the global alert manager
manager = get_alert_manager()

# Send a trading signal alert
send_signal_alert(
    instrument="EUR_USD",
    timeframe="H1",
    signal_type="BUY",
    confidence=0.85,
    entry_price=1.0850,
    stop_loss=1.0820,
    take_profit=1.0920,
    strategy="MACD Crossover"
)
```

## Alert Types

### 1. Signal Alerts

Trading signal notifications with confidence levels:

```python
from src.interface.alerts import send_signal_alert

send_signal_alert(
    instrument="EUR_USD",
    timeframe="H1",
    signal_type="BUY",
    confidence=0.85,
    entry_price=1.0850,
    stop_loss=1.0820,
    take_profit=1.0920,
    strategy="MACD + RSI"
)
```

Features:
- Only sends if confidence >= `ALERT_MIN_CONFIDENCE`
- Priority based on confidence (>90% = HIGH, >80% = MEDIUM, else LOW)
- Includes entry price, stop loss, and take profit levels
- Shows strategy name

### 2. Price Alerts

Price threshold crossing notifications:

```python
from src.interface.alerts import send_price_alert

send_price_alert(
    instrument="EUR_USD",
    current_price=1.0875,
    threshold=1.0850,
    direction="above"  # or "below"
)
```

### 3. Risk Alerts

Risk management and portfolio warnings:

```python
from src.interface.alerts import send_risk_alert

send_risk_alert(
    subject="Portfolio Drawdown Warning",
    message="Portfolio drawdown has exceeded 10% threshold.",
    severity="high"  # low, medium, high, critical
)
```

### 4. System Alerts

System status and error notifications:

```python
from src.interface.alerts import send_system_alert

send_system_alert(
    subject="Database Connection Issue",
    message="Unable to connect to database. Retrying...",
    severity="critical"
)
```

## Advanced Usage

### Custom Alert Configuration

Create a custom alert configuration:

```python
from src.interface.alerts import AlertManager, AlertConfig

config = AlertConfig(
    enable_email=True,
    enable_desktop=True,
    enable_telegram=False,
    min_confidence=0.75,
    email_smtp_server="smtp.gmail.com",
    email_smtp_port=587,
    email_from="your_email@gmail.com",
    email_to=["recipient1@example.com", "recipient2@example.com"],
    rate_limit_seconds=300,
    max_alerts_per_hour=20
)

manager = AlertManager(config)
```

### Manual Alert Sending

Send alerts with full control:

```python
from src.interface.alerts import (
    AlertManager,
    AlertPriority,
    AlertType,
    AlertChannel
)

manager = get_alert_manager()

manager.send_alert(
    subject="Custom Alert",
    message="This is a custom alert message.",
    priority=AlertPriority.HIGH,
    alert_type=AlertType.SYSTEM,
    channels=[AlertChannel.EMAIL, AlertChannel.DESKTOP],
    instrument="EUR_USD",
    timeframe="H1",
    extra_data={
        "custom_field_1": "value1",
        "custom_field_2": "value2"
    },
    force=False  # Set True to bypass rate limiting
)
```

### Alert Statistics

Get alert statistics and metrics:

```python
manager = get_alert_manager()

# Get stats for last 24 hours
stats = manager.get_alert_statistics(hours=24)

print(f"Total alerts: {stats['total_alerts']}")
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"By type: {stats['by_type']}")
print(f"By priority: {stats['by_priority']}")
print(f"By channel: {stats['by_channel']}")
```

## Email Configuration

### Gmail Setup

1. Enable 2-Factor Authentication on your Google account
2. Go to: https://myaccount.google.com/apppasswords
3. Generate an app password for "Mail"
4. Use the generated password in `.env`:

```env
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USE_TLS=true
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_16_char_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

### Other Email Providers

**SendGrid:**
```env
EMAIL_SMTP_SERVER=smtp.sendgrid.net
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=apikey
EMAIL_PASSWORD=your_sendgrid_api_key
```

**Outlook:**
```env
EMAIL_SMTP_SERVER=smtp-mail.outlook.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@outlook.com
EMAIL_PASSWORD=your_password
```

**Custom SMTP:**
```env
EMAIL_SMTP_SERVER=mail.yourdomain.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_username
EMAIL_PASSWORD=your_password
```

## Telegram Configuration

### Setup Telegram Bot

1. **Create a Bot:**
   - Open Telegram and search for `@BotFather`
   - Send `/newbot` command
   - Follow instructions to name your bot
   - Save the bot token provided

2. **Get Your Chat ID:**
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find the `"chat":{"id":...}` value in the JSON response

3. **Configure in `.env`:**
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

### Multiple Chat IDs

Send alerts to multiple Telegram chats:

```env
TELEGRAM_CHAT_ID=123456789,987654321,456789123
```

## Desktop Notifications

Desktop notifications work out-of-the-box on all platforms:

- **Linux**: Uses notify-send or dbus
- **macOS**: Uses terminal-notifier or osascript
- **Windows**: Uses Windows notification system

No additional configuration required:

```env
ALERT_ENABLE_DESKTOP=true
ALERT_DESKTOP_SOUND=true
ALERT_DESKTOP_TIMEOUT=10
```

## Rate Limiting

The alert system includes rate limiting to prevent spam:

### Per-Alert Deduplication

Prevents sending identical alerts within a time window:

```env
ALERT_RATE_LIMIT_SECONDS=300  # 5 minutes
```

### Hourly Limits

Limits total alerts per type per hour:

```env
ALERT_MAX_PER_HOUR=20
```

### Bypass Rate Limiting

Use `force=True` to bypass rate limiting:

```python
send_signal_alert(
    instrument="EUR_USD",
    timeframe="H1",
    signal_type="BUY",
    confidence=0.85,
    force=True  # Bypass rate limiting and confidence check
)
```

## Alert History

All alerts are automatically saved to the database for tracking and analysis.

### Database Schema

The `alert_history` table tracks:
- Alert type and priority
- Subject and message content
- Channels used
- Instrument and timeframe
- Success/failure status
- Timestamp

### Query Alert History

```python
from src.core.database import get_db
from src.interface.alerts import AlertHistory

db = get_db()

with db.session_scope() as session:
    # Get recent alerts
    recent_alerts = session.query(AlertHistory)\
        .order_by(AlertHistory.sent_at.desc())\
        .limit(10)\
        .all()

    for alert in recent_alerts:
        print(f"{alert.sent_at}: {alert.subject} [{alert.priority}]")
```

## Integration Examples

### Integrate with Signal Detection

```python
from src.analysis.signals import SignalGenerator
from src.interface.alerts import send_signal_alert

def detect_and_alert_signals(instrument, timeframe, data):
    """Detect signals and send alerts."""

    # Generate signals
    generator = SignalGenerator()
    signal = generator.generate_signal(data)

    # Send alert if signal found
    if signal.signal_type in ['BUY', 'SELL']:
        send_signal_alert(
            instrument=instrument,
            timeframe=timeframe,
            signal_type=signal.signal_type,
            confidence=signal.confidence,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            strategy=signal.strategy_name
        )
```

### Integrate with Price Monitoring

```python
from src.data.market_data import MarketDataManager
from src.interface.alerts import send_price_alert

def monitor_price_levels(instrument, thresholds):
    """Monitor price levels and alert on crosses."""

    market_data = MarketDataManager()
    current_price = market_data.get_current_price(instrument)

    for threshold, last_position in thresholds.items():
        # Check if price crossed threshold
        if last_position == 'below' and current_price > threshold:
            send_price_alert(
                instrument=instrument,
                current_price=current_price,
                threshold=threshold,
                direction='above'
            )
            thresholds[threshold] = 'above'

        elif last_position == 'above' and current_price < threshold:
            send_price_alert(
                instrument=instrument,
                current_price=current_price,
                threshold=threshold,
                direction='below'
            )
            thresholds[threshold] = 'below'
```

### Integrate with Risk Management

```python
from src.interface.alerts import send_risk_alert

def monitor_portfolio_risk(portfolio):
    """Monitor portfolio risk and send alerts."""

    # Check drawdown
    if portfolio.drawdown > 0.10:
        send_risk_alert(
            subject="Portfolio Drawdown Alert",
            message=f"Portfolio drawdown: {portfolio.drawdown:.1%}",
            severity='high'
        )

    # Check position limits
    if portfolio.open_positions > 10:
        send_risk_alert(
            subject="Position Limit Exceeded",
            message=f"Open positions: {portfolio.open_positions}",
            severity='medium'
        )

    # Check margin
    if portfolio.margin_level < 0.30:
        send_risk_alert(
            subject="Low Margin Warning",
            message=f"Margin level: {portfolio.margin_level:.1%}",
            severity='critical'
        )
```

## Testing

Run the demo script to test all alert functionality:

```bash
python examples/alert_system_demo.py
```

This will demonstrate:
1. Basic alert functionality
2. Trading signal alerts
3. Price alerts
4. Risk alerts
5. System alerts
6. Rate limiting and deduplication
7. Alert statistics
8. Convenience functions

## Troubleshooting

### Email Alerts Not Sending

1. **Gmail**: Ensure you're using an app password, not your regular password
2. **Check SMTP settings**: Verify server address and port
3. **Firewall**: Ensure port 587 (or 465) is not blocked
4. **TLS/SSL**: Try toggling `EMAIL_USE_TLS` setting

### Desktop Notifications Not Showing

1. **Linux**: Install `libnotify-bin`: `sudo apt-get install libnotify-bin`
2. **macOS**: No setup required
3. **Windows**: Ensure notifications are enabled in Windows settings

### Telegram Alerts Not Sending

1. **Bot Token**: Verify token is correct from @BotFather
2. **Chat ID**: Ensure you've sent at least one message to the bot first
3. **Network**: Check internet connectivity
4. **Permissions**: Bot needs permission to send messages

### Rate Limiting Too Aggressive

Adjust rate limiting in `.env`:

```env
ALERT_RATE_LIMIT_SECONDS=60     # Reduce to 1 minute
ALERT_MAX_PER_HOUR=50           # Increase hourly limit
```

Or bypass for critical alerts:

```python
send_signal_alert(..., force=True)
```

## API Reference

See inline documentation in `/home/user/ScreenerIII/src/interface/alerts.py` for complete API reference.

### Key Classes

- `AlertManager`: Central alert orchestrator
- `AlertConfig`: Configuration dataclass
- `EmailAlerter`: Email notification handler
- `DesktopAlerter`: Desktop notification handler
- `TelegramAlerter`: Telegram notification handler
- `AlertHistory`: Database model for alert history

### Key Functions

- `get_alert_manager()`: Get global alert manager instance
- `send_signal_alert()`: Send trading signal alert
- `send_price_alert()`: Send price threshold alert
- `send_risk_alert()`: Send risk management alert
- `send_system_alert()`: Send system status alert

## License

Part of ScreenerIII Trading System.
