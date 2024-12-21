# ScreenerIII - Real-time Commodity Market Scanner

A real-time market scanner for commodity trading with technical analysis and pattern recognition.

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

4. Create a .env file with your OANDA credentials:
```
OANDA_API_KEY=your_api_key_here
OANDA_ACCOUNT_ID=your_account_id_here
OANDA_ENVIRONMENT=live
```

## Usage

Run the scanner:
```bash
python main.py
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
├── data/           # Data storage
├── logs/           # Application logs
└── models/         # Saved analysis models
```

## Requirements

- Python 3.9+
- OANDA API access
- Required Python packages listed in requirements.txt

## License

This project is licensed under the MIT License - see the LICENSE file for details.