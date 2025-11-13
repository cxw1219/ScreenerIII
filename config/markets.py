"""
Market Definitions and Configurations
"""

# Market Categories
PRECIOUS_METALS = "Precious Metals"
ENERGY = "Energy"
AGRICULTURE = "Agriculture"
FOREX = "Forex"

# All Supported Markets
MARKETS = {
    # Precious Metals
    "XAU_USD": {
        "symbol": "XAU_USD",
        "display_name": "Gold",
        "category": PRECIOUS_METALS,
        "description": "Gold vs US Dollar",
        "pip_location": -2,
        "min_trade_size": 1,
        "max_trade_size": 10000,
        "typical_spread": 0.5
    },
    "XAG_USD": {
        "symbol": "XAG_USD",
        "display_name": "Silver",
        "category": PRECIOUS_METALS,
        "description": "Silver vs US Dollar",
        "pip_location": -3,
        "min_trade_size": 1,
        "max_trade_size": 50000,
        "typical_spread": 0.005
    },
    "XPT_USD": {
        "symbol": "XPT_USD",
        "display_name": "Platinum",
        "category": PRECIOUS_METALS,
        "description": "Platinum vs US Dollar",
        "pip_location": -2,
        "min_trade_size": 1,
        "max_trade_size": 10000,
        "typical_spread": 3.0
    },
    "XPD_USD": {
        "symbol": "XPD_USD",
        "display_name": "Palladium",
        "category": PRECIOUS_METALS,
        "description": "Palladium vs US Dollar",
        "pip_location": -2,
        "min_trade_size": 1,
        "max_trade_size": 10000,
        "typical_spread": 5.0
    },

    # Energy
    "BCO_USD": {
        "symbol": "BCO_USD",
        "display_name": "Brent Crude",
        "category": ENERGY,
        "description": "Brent Crude Oil vs US Dollar",
        "pip_location": -2,
        "min_trade_size": 1,
        "max_trade_size": 10000,
        "typical_spread": 0.03
    },
    "WTICO_USD": {
        "symbol": "WTICO_USD",
        "display_name": "WTI Crude",
        "category": ENERGY,
        "description": "West Texas Intermediate Crude Oil vs US Dollar",
        "pip_location": -2,
        "min_trade_size": 1,
        "max_trade_size": 10000,
        "typical_spread": 0.03
    },
    "NATGAS_USD": {
        "symbol": "NATGAS_USD",
        "display_name": "Natural Gas",
        "category": ENERGY,
        "description": "Natural Gas vs US Dollar",
        "pip_location": -3,
        "min_trade_size": 1,
        "max_trade_size": 10000,
        "typical_spread": 0.005
    },

    # Agriculture
    "CORN_USD": {
        "symbol": "CORN_USD",
        "display_name": "Corn",
        "category": AGRICULTURE,
        "description": "Corn vs US Dollar",
        "pip_location": -2,
        "min_trade_size": 1,
        "max_trade_size": 10000,
        "typical_spread": 0.25
    },
    "SOYBN_USD": {
        "symbol": "SOYBN_USD",
        "display_name": "Soybeans",
        "category": AGRICULTURE,
        "description": "Soybeans vs US Dollar",
        "pip_location": -2,
        "min_trade_size": 1,
        "max_trade_size": 10000,
        "typical_spread": 0.50
    },
    "WHEAT_USD": {
        "symbol": "WHEAT_USD",
        "display_name": "Wheat",
        "category": AGRICULTURE,
        "description": "Wheat vs US Dollar",
        "pip_location": -2,
        "min_trade_size": 1,
        "max_trade_size": 10000,
        "typical_spread": 0.25
    },
    "SUGAR_USD": {
        "symbol": "SUGAR_USD",
        "display_name": "Sugar",
        "category": AGRICULTURE,
        "description": "Sugar vs US Dollar",
        "pip_location": -4,
        "min_trade_size": 1,
        "max_trade_size": 10000,
        "typical_spread": 0.0005
    },

    # Forex - Major Pairs
    "EUR_USD": {
        "symbol": "EUR_USD",
        "display_name": "Euro/US Dollar",
        "category": FOREX,
        "subcategory": "Major",
        "description": "Euro vs US Dollar",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 1.5,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "Medium"
    },
    "GBP_USD": {
        "symbol": "GBP_USD",
        "display_name": "British Pound/US Dollar",
        "category": FOREX,
        "subcategory": "Major",
        "description": "British Pound vs US Dollar",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 2.0,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "High"
    },
    "USD_JPY": {
        "symbol": "USD_JPY",
        "display_name": "US Dollar/Japanese Yen",
        "category": FOREX,
        "subcategory": "Major",
        "description": "US Dollar vs Japanese Yen",
        "pip_value": 0.01,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 1.5,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "High"
    },
    "USD_CHF": {
        "symbol": "USD_CHF",
        "display_name": "US Dollar/Swiss Franc",
        "category": FOREX,
        "subcategory": "Major",
        "description": "US Dollar vs Swiss Franc",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 1.5,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "Medium"
    },
    "AUD_USD": {
        "symbol": "AUD_USD",
        "display_name": "Australian Dollar/US Dollar",
        "category": FOREX,
        "subcategory": "Major",
        "description": "Australian Dollar vs US Dollar",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 1.8,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "Medium"
    },
    "USD_CAD": {
        "symbol": "USD_CAD",
        "display_name": "US Dollar/Canadian Dollar",
        "category": FOREX,
        "subcategory": "Major",
        "description": "US Dollar vs Canadian Dollar",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 1.5,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "Medium"
    },
    "NZD_USD": {
        "symbol": "NZD_USD",
        "display_name": "New Zealand Dollar/US Dollar",
        "category": FOREX,
        "subcategory": "Major",
        "description": "New Zealand Dollar vs US Dollar",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 2.0,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "Medium"
    },

    # Forex - Minor Pairs (Cross Pairs)
    "EUR_GBP": {
        "symbol": "EUR_GBP",
        "display_name": "Euro/British Pound",
        "category": FOREX,
        "subcategory": "Minor",
        "description": "Euro vs British Pound",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 2.0,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "Medium"
    },
    "EUR_JPY": {
        "symbol": "EUR_JPY",
        "display_name": "Euro/Japanese Yen",
        "category": FOREX,
        "subcategory": "Minor",
        "description": "Euro vs Japanese Yen",
        "pip_value": 0.01,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 2.5,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "High"
    },
    "EUR_CHF": {
        "symbol": "EUR_CHF",
        "display_name": "Euro/Swiss Franc",
        "category": FOREX,
        "subcategory": "Minor",
        "description": "Euro vs Swiss Franc",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 2.0,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "Medium"
    },
    "EUR_AUD": {
        "symbol": "EUR_AUD",
        "display_name": "Euro/Australian Dollar",
        "category": FOREX,
        "subcategory": "Minor",
        "description": "Euro vs Australian Dollar",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 2.5,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "Medium"
    },
    "GBP_JPY": {
        "symbol": "GBP_JPY",
        "display_name": "British Pound/Japanese Yen",
        "category": FOREX,
        "subcategory": "Minor",
        "description": "British Pound vs Japanese Yen",
        "pip_value": 0.01,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 3.0,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "High"
    },
    "GBP_CHF": {
        "symbol": "GBP_CHF",
        "display_name": "British Pound/Swiss Franc",
        "category": FOREX,
        "subcategory": "Minor",
        "description": "British Pound vs Swiss Franc",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 2.5,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "High"
    },
    "AUD_JPY": {
        "symbol": "AUD_JPY",
        "display_name": "Australian Dollar/Japanese Yen",
        "category": FOREX,
        "subcategory": "Minor",
        "description": "Australian Dollar vs Japanese Yen",
        "pip_value": 0.01,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 2.5,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "Medium"
    },
    "NZD_JPY": {
        "symbol": "NZD_JPY",
        "display_name": "New Zealand Dollar/Japanese Yen",
        "category": FOREX,
        "subcategory": "Minor",
        "description": "New Zealand Dollar vs Japanese Yen",
        "pip_value": 0.01,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 3.0,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "Medium"
    },

    # Forex - Exotic Pairs
    "USD_TRY": {
        "symbol": "USD_TRY",
        "display_name": "US Dollar/Turkish Lira",
        "category": FOREX,
        "subcategory": "Exotic",
        "description": "US Dollar vs Turkish Lira",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 5.0,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "High"
    },
    "EUR_TRY": {
        "symbol": "EUR_TRY",
        "display_name": "Euro/Turkish Lira",
        "category": FOREX,
        "subcategory": "Exotic",
        "description": "Euro vs Turkish Lira",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 6.0,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "High"
    },
    "USD_ZAR": {
        "symbol": "USD_ZAR",
        "display_name": "US Dollar/South African Rand",
        "category": FOREX,
        "subcategory": "Exotic",
        "description": "US Dollar vs South African Rand",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 4.0,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "High"
    },
    "USD_MXN": {
        "symbol": "USD_MXN",
        "display_name": "US Dollar/Mexican Peso",
        "category": FOREX,
        "subcategory": "Exotic",
        "description": "US Dollar vs Mexican Peso",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 3.5,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "High"
    },
    "USD_SGD": {
        "symbol": "USD_SGD",
        "display_name": "US Dollar/Singapore Dollar",
        "category": FOREX,
        "subcategory": "Exotic",
        "description": "US Dollar vs Singapore Dollar",
        "pip_value": 0.0001,
        "min_trade_size": 0.01,
        "max_trade_size": 10000,
        "typical_spread": 2.5,
        "trading_hours": "24/5 (Sunday 17:00 - Friday 17:00 EST)",
        "volatility_rating": "Low"
    }
}

# Markets grouped by category
MARKETS_BY_CATEGORY = {
    PRECIOUS_METALS: [
        "XAU_USD",
        "XAG_USD",
        "XPT_USD",
        "XPD_USD"
    ],
    ENERGY: [
        "BCO_USD",
        "WTICO_USD",
        "NATGAS_USD"
    ],
    AGRICULTURE: [
        "CORN_USD",
        "SOYBN_USD",
        "WHEAT_USD",
        "SUGAR_USD"
    ],
    FOREX: [
        # Major Pairs
        "EUR_USD",
        "GBP_USD",
        "USD_JPY",
        "USD_CHF",
        "AUD_USD",
        "USD_CAD",
        "NZD_USD",
        # Minor Pairs
        "EUR_GBP",
        "EUR_JPY",
        "EUR_CHF",
        "EUR_AUD",
        "GBP_JPY",
        "GBP_CHF",
        "AUD_JPY",
        "NZD_JPY",
        # Exotic Pairs
        "USD_TRY",
        "EUR_TRY",
        "USD_ZAR",
        "USD_MXN",
        "USD_SGD"
    ]
}

# List of all market symbols
ALL_MARKET_SYMBOLS = list(MARKETS.keys())

# Category order for display
CATEGORY_ORDER = [PRECIOUS_METALS, ENERGY, AGRICULTURE, FOREX]


def get_market_info(symbol: str) -> dict:
    """
    Get market information for a given symbol.

    Args:
        symbol: Market symbol (e.g., 'XAU_USD')

    Returns:
        Dictionary containing market information
    """
    return MARKETS.get(symbol, {})


def get_markets_by_category(category: str) -> list:
    """
    Get list of market symbols for a given category.

    Args:
        category: Category name

    Returns:
        List of market symbols
    """
    return MARKETS_BY_CATEGORY.get(category, [])


def get_display_name(symbol: str) -> str:
    """
    Get display name for a market symbol.

    Args:
        symbol: Market symbol

    Returns:
        Display name
    """
    return MARKETS.get(symbol, {}).get("display_name", symbol)


def get_category(symbol: str) -> str:
    """
    Get category for a market symbol.

    Args:
        symbol: Market symbol

    Returns:
        Category name
    """
    return MARKETS.get(symbol, {}).get("category", "Unknown")


def get_forex_majors() -> list:
    """
    Get list of major Forex pairs.

    Returns:
        List of major Forex pair symbols
    """
    return [
        symbol for symbol in MARKETS_BY_CATEGORY.get(FOREX, [])
        if MARKETS.get(symbol, {}).get("subcategory") == "Major"
    ]


def get_forex_minors() -> list:
    """
    Get list of minor Forex pairs (cross pairs without USD).

    Returns:
        List of minor Forex pair symbols
    """
    return [
        symbol for symbol in MARKETS_BY_CATEGORY.get(FOREX, [])
        if MARKETS.get(symbol, {}).get("subcategory") == "Minor"
    ]


def get_forex_exotics() -> list:
    """
    Get list of exotic Forex pairs.

    Returns:
        List of exotic Forex pair symbols
    """
    return [
        symbol for symbol in MARKETS_BY_CATEGORY.get(FOREX, [])
        if MARKETS.get(symbol, {}).get("subcategory") == "Exotic"
    ]
