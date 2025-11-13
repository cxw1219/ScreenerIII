"""
Example script demonstrating the terminal interface module.

This script shows how to use the TerminalDisplay class to display
commodity market data with color-coded output and formatted tables.
"""

from src.interface import TerminalDisplay

# Sample market data
sample_data = [
    # Precious Metals
    {
        "symbol": "XAU_USD",
        "price": 2045.50,
        "bid": 2045.25,
        "ask": 2045.75,
        "change_24h": 1.25,
        "signal": "BUY",
        "direction": "LONG",
        "target": 2065.00,
        "stop_loss": 2035.00,
        "risk_reward": 2.5,
        "atr": 12.50,
        "volume": 145000,
        "confidence": 75
    },
    {
        "symbol": "XAG_USD",
        "price": 24.85,
        "bid": 24.83,
        "ask": 24.87,
        "change_24h": -0.75,
        "signal": "SELL",
        "direction": "SHORT",
        "target": 24.20,
        "stop_loss": 25.10,
        "risk_reward": 1.8,
        "atr": 0.45,
        "volume": 98000,
        "confidence": 65
    },
    {
        "symbol": "XPT_USD",
        "price": 925.30,
        "bid": 925.10,
        "ask": 925.50,
        "change_24h": 0.15,
        "signal": "HOLD",
        "direction": "NEUTRAL",
        "target": 930.00,
        "stop_loss": 920.00,
        "risk_reward": 1.2,
        "atr": 8.75,
        "volume": 12500,
        "confidence": 45
    },
    {
        "symbol": "XPD_USD",
        "price": 1045.75,
        "bid": 1045.50,
        "ask": 1046.00,
        "change_24h": 2.10,
        "signal": "BUY",
        "direction": "LONG",
        "target": 1065.00,
        "stop_loss": 1035.00,
        "risk_reward": 2.8,
        "atr": 15.25,
        "volume": 8900,
        "confidence": 80
    },
    # Energy
    {
        "symbol": "BCO_USD",
        "price": 82.45,
        "bid": 82.40,
        "ask": 82.50,
        "change_24h": -1.20,
        "signal": "SELL",
        "direction": "SHORT",
        "target": 80.00,
        "stop_loss": 83.50,
        "risk_reward": 2.0,
        "atr": 1.85,
        "volume": 2500000,
        "confidence": 70
    },
    {
        "symbol": "WTICO_USD",
        "price": 78.90,
        "bid": 78.85,
        "ask": 78.95,
        "change_24h": -0.95,
        "signal": "SELL",
        "direction": "SHORT",
        "target": 76.50,
        "stop_loss": 80.00,
        "risk_reward": 1.9,
        "atr": 1.75,
        "volume": 3200000,
        "confidence": 68
    },
    {
        "symbol": "NATGAS_USD",
        "price": 2.85,
        "bid": 2.84,
        "ask": 2.86,
        "change_24h": 3.50,
        "signal": "BUY",
        "direction": "LONG",
        "target": 3.00,
        "stop_loss": 2.75,
        "risk_reward": 3.2,
        "atr": 0.12,
        "volume": 1850000,
        "confidence": 85
    },
    # Agriculture
    {
        "symbol": "CORN_USD",
        "price": 4.65,
        "bid": 4.64,
        "ask": 4.66,
        "change_24h": 0.50,
        "signal": "HOLD",
        "direction": "NEUTRAL",
        "target": 4.75,
        "stop_loss": 4.55,
        "risk_reward": 1.5,
        "atr": 0.08,
        "volume": 450000,
        "confidence": 50
    },
    {
        "symbol": "SOYBN_USD",
        "price": 12.35,
        "bid": 12.33,
        "ask": 12.37,
        "change_24h": 1.85,
        "signal": "BUY",
        "direction": "LONG",
        "target": 12.80,
        "stop_loss": 12.10,
        "risk_reward": 2.3,
        "atr": 0.18,
        "volume": 380000,
        "confidence": 72
    },
    {
        "symbol": "WHEAT_USD",
        "price": 6.25,
        "bid": 6.24,
        "ask": 6.26,
        "change_24h": -0.40,
        "signal": "HOLD",
        "direction": "NEUTRAL",
        "target": 6.35,
        "stop_loss": 6.15,
        "risk_reward": 1.3,
        "atr": 0.11,
        "volume": 320000,
        "confidence": 48
    },
    {
        "symbol": "SUGAR_USD",
        "price": 0.2145,
        "bid": 0.2143,
        "ask": 0.2147,
        "change_24h": -1.50,
        "signal": "SELL",
        "direction": "SHORT",
        "target": 0.2100,
        "stop_loss": 0.2180,
        "risk_reward": 2.1,
        "atr": 0.0025,
        "volume": 580000,
        "confidence": 62
    }
]

# Summary statistics
summary = {
    "total_markets": 11,
    "bullish_count": 4,
    "bearish_count": 4,
    "neutral_count": 3,
    "avg_change": 0.41
}


def main():
    """Main function to demonstrate the display."""
    # Create display instance
    display = TerminalDisplay(refresh_rate=10)

    # Show startup banner
    display.display_startup_banner()

    # Display market data
    display.display_markets(sample_data)

    # Display summary
    display.display_summary(summary)

    # Show example messages
    display.display_info("Data stream is active")
    display.display_success("All markets loaded successfully")


if __name__ == "__main__":
    main()
