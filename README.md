# ScreenerIII

Advanced financial market scanner with real-time data collection, pattern recognition, and machine learning analysis.

## Features

- Real-time market data collection at 10-second intervals
- Focus on commodity markets
- Pattern recognition and technical analysis
- Machine learning-based predictions
- SQLite database for data storage
- ASCII-based real-time dashboard

## Setup

1. Clone the repository
2. Install requirements: `pip install -r requirements.txt`
3. Create a `.env` file with your OANDA credentials:
```env
OANDA_API_KEY=your_api_key
OANDA_ACCOUNT_ID=your_account_id
OANDA_ENVIRONMENT=practice  # or live
```

## Usage

Run the main script:
```bash
python main.py
```

## Project Structure

```
src/
├── core/           # Core engine and event dispatcher
├── data/           # Data collection and storage
├── analysis/       # Pattern recognition and ML
├── interface/      # CLI and dashboard
└── utils/          # Utility functions
```

## License

MIT