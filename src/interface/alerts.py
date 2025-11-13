"""
Alert System Module

This module provides a comprehensive alert system for ScreenerIII with support for
multiple alert channels (Email, Desktop, Telegram), alert priority levels, rate limiting,
and alert history tracking.

Features:
- Multiple alert channels (Email, Desktop, Telegram)
- Alert priority levels (LOW, MEDIUM, HIGH, CRITICAL)
- Rate limiting to prevent spam
- Alert history tracking and deduplication
- Template-based messages
- Configurable per-user preferences
"""

import os
import time
import smtplib
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, Index
from sqlalchemy.exc import SQLAlchemyError

# Import project modules
from ..core.logger import get_logger
from ..core.database import Base, get_db

# Optional dependencies with graceful fallback
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    notification = None

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Bot = None
    TelegramError = Exception

logger = get_logger(__name__)


class AlertPriority(Enum):
    """Alert priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AlertType(Enum):
    """Types of alerts that can be sent."""
    SIGNAL = "signal"
    PRICE = "price"
    RISK = "risk"
    SYSTEM = "system"


class AlertChannel(Enum):
    """Available alert channels."""
    EMAIL = "email"
    DESKTOP = "desktop"
    TELEGRAM = "telegram"


@dataclass
class AlertConfig:
    """
    Configuration for the alert system.

    Attributes:
        enable_email: Enable email notifications
        enable_desktop: Enable desktop notifications
        enable_telegram: Enable Telegram notifications
        min_confidence: Minimum confidence for signal alerts (0.0 to 1.0)
        email_smtp_server: SMTP server address
        email_smtp_port: SMTP server port
        email_use_tls: Use TLS for SMTP connection
        email_username: SMTP username
        email_password: SMTP password
        email_from: Sender email address
        email_to: List of recipient email addresses
        telegram_bot_token: Telegram bot token
        telegram_chat_ids: List of Telegram chat IDs
        rate_limit_seconds: Minimum seconds between similar alerts
        max_alerts_per_hour: Maximum alerts per hour per type
        desktop_sound: Enable sound for desktop notifications
    """
    enable_email: bool = False
    enable_desktop: bool = True
    enable_telegram: bool = False

    # Signal alert thresholds
    min_confidence: float = 0.7

    # Email settings
    email_smtp_server: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_use_tls: bool = True
    email_username: str = ""
    email_password: str = ""
    email_from: str = ""
    email_to: List[str] = field(default_factory=list)

    # Telegram settings
    telegram_bot_token: str = ""
    telegram_chat_ids: List[str] = field(default_factory=list)

    # Rate limiting
    rate_limit_seconds: int = 300  # 5 minutes
    max_alerts_per_hour: int = 20

    # Desktop notification settings
    desktop_sound: bool = True
    desktop_timeout: int = 10  # seconds

    @classmethod
    def from_env(cls) -> 'AlertConfig':
        """
        Create AlertConfig from environment variables.

        Returns:
            AlertConfig: Configuration object populated from environment
        """
        # Parse email recipients
        email_to = os.getenv('EMAIL_TO', '').strip()
        email_to_list = [e.strip() for e in email_to.split(',') if e.strip()]

        # Parse Telegram chat IDs
        telegram_chat_ids = os.getenv('TELEGRAM_CHAT_ID', '').strip()
        telegram_chat_ids_list = [c.strip() for c in telegram_chat_ids.split(',') if c.strip()]

        return cls(
            enable_email=os.getenv('ALERT_ENABLE_EMAIL', 'false').lower() == 'true',
            enable_desktop=os.getenv('ALERT_ENABLE_DESKTOP', 'true').lower() == 'true',
            enable_telegram=os.getenv('ALERT_ENABLE_TELEGRAM', 'false').lower() == 'true',
            min_confidence=float(os.getenv('ALERT_MIN_CONFIDENCE', '0.7')),
            email_smtp_server=os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'),
            email_smtp_port=int(os.getenv('EMAIL_SMTP_PORT', '587')),
            email_use_tls=os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true',
            email_username=os.getenv('EMAIL_USERNAME', ''),
            email_password=os.getenv('EMAIL_PASSWORD', ''),
            email_from=os.getenv('EMAIL_FROM', ''),
            email_to=email_to_list,
            telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            telegram_chat_ids=telegram_chat_ids_list,
            rate_limit_seconds=int(os.getenv('ALERT_RATE_LIMIT_SECONDS', '300')),
            max_alerts_per_hour=int(os.getenv('ALERT_MAX_PER_HOUR', '20')),
            desktop_sound=os.getenv('ALERT_DESKTOP_SOUND', 'true').lower() == 'true',
            desktop_timeout=int(os.getenv('ALERT_DESKTOP_TIMEOUT', '10')),
        )


class AlertHistory(Base):
    """
    Model for tracking sent alerts in the database.

    Used for deduplication and statistics.
    """
    __tablename__ = 'alert_history'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Alert identification
    alert_type = Column(String(20), nullable=False, index=True)
    alert_hash = Column(String(64), nullable=False, index=True)  # MD5 hash for deduplication

    # Alert details
    priority = Column(String(20), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Channels used
    channels = Column(JSON, nullable=False)  # List of channels alert was sent to

    # Metadata
    instrument = Column(String(20), nullable=True, index=True)
    timeframe = Column(String(10), nullable=True)
    extra_data = Column(JSON, nullable=True)

    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)

    # Timestamps
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Optimized indexes
    __table_args__ = (
        Index('idx_alert_history_type_sent_at', 'alert_type', 'sent_at'),
        Index('idx_alert_history_hash_sent_at', 'alert_hash', 'sent_at'),
        Index('idx_alert_history_instrument_sent_at', 'instrument', 'sent_at'),
    )

    def __repr__(self) -> str:
        return (
            f"<AlertHistory(type={self.alert_type}, priority={self.priority}, "
            f"sent_at={self.sent_at})>"
        )


class EmailAlerter:
    """
    Email notification handler using SMTP.

    Supports HTML formatted emails with template-based messages.
    """

    def __init__(self, config: AlertConfig):
        """
        Initialize email alerter.

        Args:
            config: Alert configuration
        """
        self.config = config
        self.enabled = config.enable_email and config.email_from and config.email_to

        if self.enabled:
            logger.info(f"Email alerter initialized: {config.email_smtp_server}:{config.email_smtp_port}")
        else:
            logger.info("Email alerter disabled")

    def send_alert(
        self,
        subject: str,
        message: str,
        priority: AlertPriority,
        alert_type: AlertType,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send email alert.

        Args:
            subject: Email subject
            message: Alert message
            priority: Alert priority level
            alert_type: Type of alert
            extra_data: Additional data for template

        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            logger.debug("Email alerter is disabled, skipping")
            return False

        try:
            # Create HTML email
            html_body = self._create_html_message(subject, message, priority, alert_type, extra_data)

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{priority.name}] {subject}"
            msg['From'] = self.config.email_from
            msg['To'] = ', '.join(self.config.email_to)

            # Add plain text and HTML parts
            text_part = MIMEText(message, 'plain')
            html_part = MIMEText(html_body, 'html')

            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port) as server:
                if self.config.email_use_tls:
                    server.starttls()

                if self.config.email_username and self.config.email_password:
                    server.login(self.config.email_username, self.config.email_password)

                server.send_message(msg)

            logger.info(f"Email alert sent: {subject}")
            return True

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False

    def _create_html_message(
        self,
        subject: str,
        message: str,
        priority: AlertPriority,
        alert_type: AlertType,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create HTML formatted email message.

        Args:
            subject: Email subject
            message: Alert message
            priority: Alert priority level
            alert_type: Type of alert
            extra_data: Additional data for template

        Returns:
            str: HTML formatted message
        """
        # Priority color mapping
        priority_colors = {
            AlertPriority.LOW: '#5cb85c',
            AlertPriority.MEDIUM: '#5bc0de',
            AlertPriority.HIGH: '#f0ad4e',
            AlertPriority.CRITICAL: '#d9534f',
        }

        color = priority_colors.get(priority, '#5cb85c')

        # Build extra data table if provided
        extra_html = ""
        if extra_data:
            rows = ""
            for key, value in extra_data.items():
                rows += f"<tr><td style='padding: 5px; border: 1px solid #ddd;'><strong>{key}</strong></td><td style='padding: 5px; border: 1px solid #ddd;'>{value}</td></tr>"
            extra_html = f"""
            <h3>Details</h3>
            <table style='border-collapse: collapse; width: 100%;'>
                {rows}
            </table>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;'>
            <div style='background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;'>
                <h1 style='margin: 0; font-size: 24px;'>{priority.name} ALERT</h1>
            </div>
            <div style='border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 5px 5px;'>
                <h2 style='color: {color}; margin-top: 0;'>{subject}</h2>
                <p style='font-size: 16px; white-space: pre-wrap;'>{message}</p>
                {extra_html}
                <hr style='border: none; border-top: 1px solid #ddd; margin: 20px 0;'>
                <p style='font-size: 12px; color: #666;'>
                    Alert Type: {alert_type.value.upper()}<br>
                    Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
                    Source: ScreenerIII Trading System
                </p>
            </div>
        </body>
        </html>
        """

        return html


class DesktopAlerter:
    """
    Desktop notification handler using plyer library.

    Supports cross-platform desktop notifications with icons and sounds.
    """

    def __init__(self, config: AlertConfig):
        """
        Initialize desktop alerter.

        Args:
            config: Alert configuration
        """
        self.config = config
        self.enabled = config.enable_desktop and PLYER_AVAILABLE

        if self.enabled:
            logger.info("Desktop alerter initialized")
        elif config.enable_desktop and not PLYER_AVAILABLE:
            logger.warning("Desktop alerter requested but plyer library not available")
        else:
            logger.info("Desktop alerter disabled")

    def send_alert(
        self,
        subject: str,
        message: str,
        priority: AlertPriority,
        alert_type: AlertType,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send desktop notification.

        Args:
            subject: Notification title
            message: Alert message
            priority: Alert priority level
            alert_type: Type of alert
            extra_data: Additional data (not used for desktop)

        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            logger.debug("Desktop alerter is disabled, skipping")
            return False

        try:
            # Truncate message for notification
            max_length = 200
            display_message = message[:max_length] + "..." if len(message) > max_length else message

            # Send notification
            notification.notify(
                title=f"[{priority.name}] {subject}",
                message=display_message,
                app_name="ScreenerIII",
                timeout=self.config.desktop_timeout,
            )

            logger.info(f"Desktop alert sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error sending desktop alert: {e}")
            return False


class TelegramAlerter:
    """
    Telegram notification handler using python-telegram-bot.

    Supports rich formatting (Markdown) and multiple chat IDs.
    """

    def __init__(self, config: AlertConfig):
        """
        Initialize Telegram alerter.

        Args:
            config: Alert configuration
        """
        self.config = config
        self.enabled = (
            config.enable_telegram
            and TELEGRAM_AVAILABLE
            and config.telegram_bot_token
            and config.telegram_chat_ids
        )

        self.bot = None
        if self.enabled:
            try:
                self.bot = Bot(token=config.telegram_bot_token)
                logger.info(f"Telegram alerter initialized: {len(config.telegram_chat_ids)} chat(s)")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                self.enabled = False
        elif config.enable_telegram and not TELEGRAM_AVAILABLE:
            logger.warning("Telegram alerter requested but python-telegram-bot library not available")
        else:
            logger.info("Telegram alerter disabled")

    def send_alert(
        self,
        subject: str,
        message: str,
        priority: AlertPriority,
        alert_type: AlertType,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send Telegram message.

        Args:
            subject: Message subject
            message: Alert message
            priority: Alert priority level
            alert_type: Type of alert
            extra_data: Additional data for message

        Returns:
            bool: True if sent successfully to at least one chat
        """
        if not self.enabled or not self.bot:
            logger.debug("Telegram alerter is disabled, skipping")
            return False

        try:
            # Format message with Markdown
            telegram_message = self._format_telegram_message(
                subject, message, priority, alert_type, extra_data
            )

            # Send to all configured chat IDs
            success_count = 0
            for chat_id in self.config.telegram_chat_ids:
                try:
                    self.bot.send_message(
                        chat_id=chat_id,
                        text=telegram_message,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                    success_count += 1
                except TelegramError as e:
                    logger.error(f"Error sending Telegram message to {chat_id}: {e}")

            if success_count > 0:
                logger.info(f"Telegram alert sent to {success_count}/{len(self.config.telegram_chat_ids)} chats: {subject}")
                return True
            else:
                logger.error("Failed to send Telegram alert to any chat")
                return False

        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False

    def _format_telegram_message(
        self,
        subject: str,
        message: str,
        priority: AlertPriority,
        alert_type: AlertType,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format message for Telegram with Markdown.

        Args:
            subject: Message subject
            message: Alert message
            priority: Alert priority level
            alert_type: Type of alert
            extra_data: Additional data for message

        Returns:
            str: Formatted Telegram message
        """
        # Priority emoji mapping
        priority_emojis = {
            AlertPriority.LOW: '🔵',
            AlertPriority.MEDIUM: '🟡',
            AlertPriority.HIGH: '🟠',
            AlertPriority.CRITICAL: '🔴',
        }

        emoji = priority_emojis.get(priority, '🔵')

        # Build message
        telegram_msg = f"{emoji} *{priority.name} ALERT*\n\n"
        telegram_msg += f"*{subject}*\n\n"
        telegram_msg += f"{message}\n\n"

        # Add extra data if provided
        if extra_data:
            telegram_msg += "*Details:*\n"
            for key, value in extra_data.items():
                telegram_msg += f"• {key}: `{value}`\n"
            telegram_msg += "\n"

        # Add footer
        telegram_msg += f"_Type: {alert_type.value.upper()}_\n"
        telegram_msg += f"_Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC_"

        return telegram_msg


class AlertManager:
    """
    Central alert orchestrator managing multiple alert channels.

    Features:
    - Multiple alert channels (Email, Desktop, Telegram)
    - Alert priority levels
    - Rate limiting to prevent spam
    - Alert history tracking and deduplication
    - Configurable preferences
    """

    def __init__(self, config: Optional[AlertConfig] = None):
        """
        Initialize alert manager.

        Args:
            config: Alert configuration (uses environment if not provided)
        """
        self.config = config or AlertConfig.from_env()

        # Initialize alert channels
        self.email_alerter = EmailAlerter(self.config)
        self.desktop_alerter = DesktopAlerter(self.config)
        self.telegram_alerter = TelegramAlerter(self.config)

        # Rate limiting tracking
        self._alert_timestamps: Dict[str, List[datetime]] = {}
        self._last_alert_hashes: Dict[str, datetime] = {}

        logger.info("Alert manager initialized")

    def send_alert(
        self,
        subject: str,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        alert_type: AlertType = AlertType.SYSTEM,
        channels: Optional[List[AlertChannel]] = None,
        instrument: Optional[str] = None,
        timeframe: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> bool:
        """
        Send alert through specified channels.

        Args:
            subject: Alert subject/title
            message: Alert message body
            priority: Alert priority level
            alert_type: Type of alert
            channels: List of channels to use (None = all enabled)
            instrument: Trading instrument (for deduplication)
            timeframe: Chart timeframe (for deduplication)
            extra_data: Additional data to include
            force: Skip rate limiting and deduplication

        Returns:
            bool: True if alert sent successfully through at least one channel
        """
        try:
            # Check rate limiting unless forced
            if not force:
                if not self._check_rate_limit(alert_type):
                    logger.warning(f"Rate limit exceeded for {alert_type.value} alerts")
                    return False

                # Check for duplicate alerts
                alert_hash = self._compute_alert_hash(subject, message, instrument, timeframe)
                if not self._check_duplicate(alert_hash):
                    logger.debug(f"Duplicate alert detected, skipping: {subject}")
                    return False

            # Determine which channels to use
            if channels is None:
                channels = []
                if self.config.enable_email:
                    channels.append(AlertChannel.EMAIL)
                if self.config.enable_desktop:
                    channels.append(AlertChannel.DESKTOP)
                if self.config.enable_telegram:
                    channels.append(AlertChannel.TELEGRAM)

            # Send through each channel
            success_channels = []
            for channel in channels:
                success = False

                if channel == AlertChannel.EMAIL:
                    success = self.email_alerter.send_alert(
                        subject, message, priority, alert_type, extra_data
                    )
                elif channel == AlertChannel.DESKTOP:
                    success = self.desktop_alerter.send_alert(
                        subject, message, priority, alert_type, extra_data
                    )
                elif channel == AlertChannel.TELEGRAM:
                    success = self.telegram_alerter.send_alert(
                        subject, message, priority, alert_type, extra_data
                    )

                if success:
                    success_channels.append(channel.value)

            # Record in alert history
            if success_channels:
                self._record_alert_history(
                    alert_type=alert_type,
                    alert_hash=self._compute_alert_hash(subject, message, instrument, timeframe),
                    priority=priority,
                    subject=subject,
                    message=message,
                    channels=success_channels,
                    instrument=instrument,
                    timeframe=timeframe,
                    extra_data=extra_data,
                    success=True
                )

                logger.info(
                    f"Alert sent successfully through {len(success_channels)} channel(s): {subject}"
                )
                return True
            else:
                logger.warning(f"Alert failed to send through any channel: {subject}")
                return False

        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False

    def send_signal_alert(
        self,
        instrument: str,
        timeframe: str,
        signal_type: str,
        confidence: float,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """
        Send trading signal alert.

        Args:
            instrument: Trading instrument
            timeframe: Chart timeframe
            signal_type: Signal type (BUY/SELL)
            confidence: Signal confidence (0.0 to 1.0)
            entry_price: Entry price level
            stop_loss: Stop loss level
            take_profit: Take profit level
            strategy: Strategy that generated signal
            force: Skip confidence check and rate limiting

        Returns:
            bool: True if alert sent successfully
        """
        # Check confidence threshold unless forced
        if not force and confidence < self.config.min_confidence:
            logger.debug(
                f"Signal confidence {confidence:.2f} below threshold "
                f"{self.config.min_confidence:.2f}, skipping alert"
            )
            return False

        # Determine priority based on confidence
        if confidence >= 0.9:
            priority = AlertPriority.HIGH
        elif confidence >= 0.8:
            priority = AlertPriority.MEDIUM
        else:
            priority = AlertPriority.LOW

        # Build message
        subject = f"{signal_type} Signal: {instrument} ({timeframe})"
        message = f"New {signal_type} signal detected for {instrument} on {timeframe} timeframe.\n\n"
        message += f"Confidence: {confidence:.1%}\n"

        if strategy:
            message += f"Strategy: {strategy}\n"

        if entry_price:
            message += f"\nEntry Price: {entry_price}\n"
        if stop_loss:
            message += f"Stop Loss: {stop_loss}\n"
        if take_profit:
            message += f"Take Profit: {take_profit}\n"

        # Extra data for templates
        extra_data = {
            'Instrument': instrument,
            'Timeframe': timeframe,
            'Signal': signal_type,
            'Confidence': f"{confidence:.1%}",
        }

        if strategy:
            extra_data['Strategy'] = strategy
        if entry_price:
            extra_data['Entry Price'] = entry_price
        if stop_loss:
            extra_data['Stop Loss'] = stop_loss
        if take_profit:
            extra_data['Take Profit'] = take_profit

        return self.send_alert(
            subject=subject,
            message=message,
            priority=priority,
            alert_type=AlertType.SIGNAL,
            instrument=instrument,
            timeframe=timeframe,
            extra_data=extra_data,
            force=force
        )

    def send_price_alert(
        self,
        instrument: str,
        current_price: float,
        threshold: float,
        direction: str,
        force: bool = False
    ) -> bool:
        """
        Send price threshold alert.

        Args:
            instrument: Trading instrument
            current_price: Current price
            threshold: Threshold price
            direction: Direction crossed ('above' or 'below')
            force: Skip rate limiting

        Returns:
            bool: True if alert sent successfully
        """
        subject = f"Price Alert: {instrument}"
        message = (
            f"{instrument} has crossed {direction} {threshold}\n\n"
            f"Current Price: {current_price}\n"
            f"Threshold: {threshold}\n"
            f"Direction: {direction.upper()}"
        )

        extra_data = {
            'Instrument': instrument,
            'Current Price': current_price,
            'Threshold': threshold,
            'Direction': direction.upper(),
        }

        return self.send_alert(
            subject=subject,
            message=message,
            priority=AlertPriority.MEDIUM,
            alert_type=AlertType.PRICE,
            instrument=instrument,
            extra_data=extra_data,
            force=force
        )

    def send_risk_alert(
        self,
        subject: str,
        message: str,
        severity: str = 'medium',
        force: bool = False
    ) -> bool:
        """
        Send risk management alert.

        Args:
            subject: Alert subject
            message: Alert message
            severity: Severity level ('low', 'medium', 'high', 'critical')
            force: Skip rate limiting

        Returns:
            bool: True if alert sent successfully
        """
        priority_map = {
            'low': AlertPriority.LOW,
            'medium': AlertPriority.MEDIUM,
            'high': AlertPriority.HIGH,
            'critical': AlertPriority.CRITICAL,
        }

        priority = priority_map.get(severity.lower(), AlertPriority.MEDIUM)

        return self.send_alert(
            subject=subject,
            message=message,
            priority=priority,
            alert_type=AlertType.RISK,
            force=force
        )

    def send_system_alert(
        self,
        subject: str,
        message: str,
        severity: str = 'medium',
        force: bool = False
    ) -> bool:
        """
        Send system status alert.

        Args:
            subject: Alert subject
            message: Alert message
            severity: Severity level ('low', 'medium', 'high', 'critical')
            force: Skip rate limiting

        Returns:
            bool: True if alert sent successfully
        """
        priority_map = {
            'low': AlertPriority.LOW,
            'medium': AlertPriority.MEDIUM,
            'high': AlertPriority.HIGH,
            'critical': AlertPriority.CRITICAL,
        }

        priority = priority_map.get(severity.lower(), AlertPriority.MEDIUM)

        return self.send_alert(
            subject=subject,
            message=message,
            priority=priority,
            alert_type=AlertType.SYSTEM,
            force=force
        )

    def _check_rate_limit(self, alert_type: AlertType) -> bool:
        """
        Check if rate limit allows sending alert.

        Args:
            alert_type: Type of alert

        Returns:
            bool: True if rate limit allows sending
        """
        now = datetime.utcnow()
        type_key = alert_type.value

        # Initialize tracking for this type if needed
        if type_key not in self._alert_timestamps:
            self._alert_timestamps[type_key] = []

        # Remove timestamps older than 1 hour
        one_hour_ago = now - timedelta(hours=1)
        self._alert_timestamps[type_key] = [
            ts for ts in self._alert_timestamps[type_key]
            if ts > one_hour_ago
        ]

        # Check hourly limit
        if len(self._alert_timestamps[type_key]) >= self.config.max_alerts_per_hour:
            return False

        # Add current timestamp
        self._alert_timestamps[type_key].append(now)
        return True

    def _check_duplicate(self, alert_hash: str) -> bool:
        """
        Check if alert is a duplicate within the rate limit window.

        Args:
            alert_hash: Hash of alert content

        Returns:
            bool: True if not a duplicate
        """
        now = datetime.utcnow()

        if alert_hash in self._last_alert_hashes:
            last_sent = self._last_alert_hashes[alert_hash]
            time_diff = (now - last_sent).total_seconds()

            if time_diff < self.config.rate_limit_seconds:
                return False

        # Update last sent time
        self._last_alert_hashes[alert_hash] = now

        # Clean old hashes
        cutoff = now - timedelta(seconds=self.config.rate_limit_seconds)
        self._last_alert_hashes = {
            h: ts for h, ts in self._last_alert_hashes.items()
            if ts > cutoff
        }

        return True

    def _compute_alert_hash(
        self,
        subject: str,
        message: str,
        instrument: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> str:
        """
        Compute hash for alert deduplication.

        Args:
            subject: Alert subject
            message: Alert message
            instrument: Trading instrument
            timeframe: Chart timeframe

        Returns:
            str: MD5 hash of alert content
        """
        content = f"{subject}|{message}|{instrument or ''}|{timeframe or ''}"
        return hashlib.md5(content.encode()).hexdigest()

    def _record_alert_history(
        self,
        alert_type: AlertType,
        alert_hash: str,
        priority: AlertPriority,
        subject: str,
        message: str,
        channels: List[str],
        instrument: Optional[str] = None,
        timeframe: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Record alert in database history.

        Args:
            alert_type: Type of alert
            alert_hash: Alert hash for deduplication
            priority: Alert priority
            subject: Alert subject
            message: Alert message
            channels: Channels used
            instrument: Trading instrument
            timeframe: Chart timeframe
            extra_data: Additional data
            success: Whether alert was sent successfully
            error_message: Error message if failed
        """
        try:
            db = get_db()

            with db.session_scope() as session:
                alert_record = AlertHistory(
                    alert_type=alert_type.value,
                    alert_hash=alert_hash,
                    priority=priority.name,
                    subject=subject,
                    message=message,
                    channels=channels,
                    instrument=instrument,
                    timeframe=timeframe,
                    extra_data=extra_data,
                    success=success,
                    error_message=error_message,
                    sent_at=datetime.utcnow()
                )

                session.add(alert_record)

            logger.debug(f"Alert recorded in history: {subject}")

        except SQLAlchemyError as e:
            logger.error(f"Failed to record alert history: {e}")
        except Exception as e:
            logger.error(f"Unexpected error recording alert history: {e}")

    def get_alert_statistics(
        self,
        hours: int = 24,
        alert_type: Optional[AlertType] = None
    ) -> Dict[str, Any]:
        """
        Get alert statistics for the specified time period.

        Args:
            hours: Number of hours to look back
            alert_type: Filter by alert type (None for all)

        Returns:
            dict: Alert statistics
        """
        try:
            db = get_db()
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            with db.session_scope() as session:
                query = session.query(AlertHistory).filter(
                    AlertHistory.sent_at >= cutoff
                )

                if alert_type:
                    query = query.filter(AlertHistory.alert_type == alert_type.value)

                alerts = query.all()

                # Calculate statistics
                total = len(alerts)
                successful = sum(1 for a in alerts if a.success)
                failed = total - successful

                by_type = {}
                by_priority = {}
                by_channel = {}

                for alert in alerts:
                    # Count by type
                    by_type[alert.alert_type] = by_type.get(alert.alert_type, 0) + 1

                    # Count by priority
                    by_priority[alert.priority] = by_priority.get(alert.priority, 0) + 1

                    # Count by channel
                    for channel in alert.channels:
                        by_channel[channel] = by_channel.get(channel, 0) + 1

                return {
                    'total_alerts': total,
                    'successful': successful,
                    'failed': failed,
                    'success_rate': successful / total if total > 0 else 0.0,
                    'by_type': by_type,
                    'by_priority': by_priority,
                    'by_channel': by_channel,
                    'time_period_hours': hours,
                }

        except Exception as e:
            logger.error(f"Error getting alert statistics: {e}")
            return {
                'error': str(e),
                'total_alerts': 0,
                'successful': 0,
                'failed': 0,
            }


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """
    Get or create the global alert manager instance.

    Returns:
        AlertManager: Global alert manager
    """
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


# Convenience functions for quick alerts
def send_signal_alert(*args, **kwargs) -> bool:
    """Send trading signal alert using global manager."""
    return get_alert_manager().send_signal_alert(*args, **kwargs)


def send_price_alert(*args, **kwargs) -> bool:
    """Send price alert using global manager."""
    return get_alert_manager().send_price_alert(*args, **kwargs)


def send_risk_alert(*args, **kwargs) -> bool:
    """Send risk alert using global manager."""
    return get_alert_manager().send_risk_alert(*args, **kwargs)


def send_system_alert(*args, **kwargs) -> bool:
    """Send system alert using global manager."""
    return get_alert_manager().send_system_alert(*args, **kwargs)


if __name__ == '__main__':
    """Test alert system."""
    print("Testing ScreenerIII Alert System")
    print("=" * 50)

    # Create test configuration
    config = AlertConfig(
        enable_desktop=True,
        enable_email=False,
        enable_telegram=False,
    )

    # Create alert manager
    manager = AlertManager(config)

    # Test signal alert
    print("\n1. Testing signal alert...")
    success = manager.send_signal_alert(
        instrument="EUR_USD",
        timeframe="H1",
        signal_type="BUY",
        confidence=0.85,
        entry_price=1.0850,
        stop_loss=1.0820,
        take_profit=1.0920,
        strategy="MACD Crossover"
    )
    print(f"   Signal alert: {'✓ Sent' if success else '✗ Failed'}")

    # Test price alert
    print("\n2. Testing price alert...")
    success = manager.send_price_alert(
        instrument="GBP_USD",
        current_price=1.2650,
        threshold=1.2600,
        direction="above"
    )
    print(f"   Price alert: {'✓ Sent' if success else '✗ Failed'}")

    # Test risk alert
    print("\n3. Testing risk alert...")
    success = manager.send_risk_alert(
        subject="Portfolio Drawdown Warning",
        message="Portfolio drawdown has exceeded 10% threshold.",
        severity="high"
    )
    print(f"   Risk alert: {'✓ Sent' if success else '✗ Failed'}")

    # Test system alert
    print("\n4. Testing system alert...")
    success = manager.send_system_alert(
        subject="Database Connection Issue",
        message="Unable to connect to database. Retrying...",
        severity="critical"
    )
    print(f"   System alert: {'✓ Sent' if success else '✗ Failed'}")

    # Get statistics
    print("\n5. Alert statistics:")
    stats = manager.get_alert_statistics(hours=1)
    print(f"   Total alerts: {stats.get('total_alerts', 0)}")
    print(f"   Successful: {stats.get('successful', 0)}")
    print(f"   Failed: {stats.get('failed', 0)}")

    print("\n" + "=" * 50)
    print("Alert system test complete!")
