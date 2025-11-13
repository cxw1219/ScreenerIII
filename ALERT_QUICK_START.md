# ScreenerIII Alert System - Quick Start

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

```bash
cp .env.example .env
# Edit .env with your alert settings
```

### Minimal Setup (Desktop Only)

```env
ALERT_ENABLE_DESKTOP=true
ALERT_ENABLE_EMAIL=false
ALERT_ENABLE_TELEGRAM=false
```

### Email Setup (Gmail)

1. Get app password: https://myaccount.google.com/apppasswords
2. Configure:

```env
ALERT_ENABLE_EMAIL=true
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

### Telegram Setup

1. Create bot via @BotFather
2. Get chat ID: Send message to bot, visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Configure:

```env
ALERT_ENABLE_TELEGRAM=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Basic Usage

```python
from src.interface.alerts import send_signal_alert

# Send trading signal alert
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

## All Alert Types

```python
from src.interface.alerts import (
    send_signal_alert,
    send_price_alert,
    send_risk_alert,
    send_system_alert
)

# 1. Signal Alert
send_signal_alert(
    instrument="EUR_USD",
    timeframe="H1",
    signal_type="BUY",
    confidence=0.85,
    entry_price=1.0850
)

# 2. Price Alert
send_price_alert(
    instrument="EUR_USD",
    current_price=1.0875,
    threshold=1.0850,
    direction="above"
)

# 3. Risk Alert
send_risk_alert(
    subject="Portfolio Drawdown",
    message="Drawdown exceeded 10%",
    severity="high"
)

# 4. System Alert
send_system_alert(
    subject="System Error",
    message="Database connection lost",
    severity="critical"
)
```

## Test

```bash
python examples/alert_system_demo.py
```

## Documentation

- Full docs: `/home/user/ScreenerIII/docs/ALERT_SYSTEM.md`
- Demo: `/home/user/ScreenerIII/examples/alert_system_demo.py`
- Code: `/home/user/ScreenerIII/src/interface/alerts.py`

## Key Features

- **3 Channels**: Email, Desktop, Telegram
- **4 Alert Types**: Signal, Price, Risk, System
- **4 Priority Levels**: LOW, MEDIUM, HIGH, CRITICAL
- **Rate Limiting**: Prevents spam
- **Deduplication**: Avoids duplicate alerts
- **History Tracking**: Database storage
- **Statistics**: Analytics and metrics

## Environment Variables

```env
# Channels
ALERT_ENABLE_EMAIL=false
ALERT_ENABLE_DESKTOP=true
ALERT_ENABLE_TELEGRAM=false

# Thresholds
ALERT_MIN_CONFIDENCE=0.7

# Email (Gmail example)
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Rate Limiting
ALERT_RATE_LIMIT_SECONDS=300
ALERT_MAX_PER_HOUR=20

# Desktop
ALERT_DESKTOP_SOUND=true
ALERT_DESKTOP_TIMEOUT=10
```

## Common Issues

**Desktop notifications not showing?**
- Linux: `sudo apt-get install libnotify-bin`
- macOS/Windows: Should work out of the box

**Email not sending?**
- Gmail: Use app password (not regular password)
- Check SMTP server and port
- Verify firewall allows port 587

**Telegram not working?**
- Verify bot token from @BotFather
- Ensure you've sent at least one message to bot
- Check chat ID is correct

## Advanced Usage

```python
from src.interface.alerts import get_alert_manager, AlertPriority, AlertType

# Get manager for advanced control
manager = get_alert_manager()

# Send custom alert
manager.send_alert(
    subject="Custom Alert",
    message="Custom message",
    priority=AlertPriority.HIGH,
    alert_type=AlertType.SYSTEM,
    force=True  # Bypass rate limiting
)

# Get statistics
stats = manager.get_alert_statistics(hours=24)
print(f"Total: {stats['total_alerts']}")
print(f"Success rate: {stats['success_rate']:.1%}")
```

## Integration Example

```python
# In your signal detection code:
from src.interface.alerts import send_signal_alert

def on_signal_detected(instrument, timeframe, signal):
    """Called when a trading signal is detected."""

    # Send alert
    send_signal_alert(
        instrument=instrument,
        timeframe=timeframe,
        signal_type=signal.type,
        confidence=signal.confidence,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
        strategy=signal.strategy_name
    )
```

## Files Created

1. **alerts.py** (1,237 lines) - Main implementation
2. **alert_system_demo.py** (370 lines) - Demo script
3. **ALERT_SYSTEM.md** (750+ lines) - Full documentation
4. **Updated requirements.txt** - Added dependencies
5. **Updated .env.example** - Added configuration

## Dependencies

- `plyer>=2.1.0` - Desktop notifications
- `python-telegram-bot>=20.0` - Telegram integration

## Next Steps

1. ✓ Install: `pip install -r requirements.txt`
2. ✓ Configure: Edit `.env` with your settings
3. ✓ Test: `python examples/alert_system_demo.py`
4. ✓ Initialize DB: `python -c "from src.core.database import init_db; init_db()"`
5. ✓ Integrate: Add alerts to your trading logic
6. ✓ Read docs: `cat docs/ALERT_SYSTEM.md`

---

**Ready to use!** Start with desktop notifications (no setup) and add email/Telegram later.
