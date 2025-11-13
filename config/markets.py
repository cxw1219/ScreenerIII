"""
Market Definitions and Configurations
"""

# Market Categories
PRECIOUS_METALS = "Precious Metals"
ENERGY = "Energy"
AGRICULTURE = "Agriculture"

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
    ]
}

# List of all market symbols
ALL_MARKET_SYMBOLS = list(MARKETS.keys())

# Category order for display
CATEGORY_ORDER = [PRECIOUS_METALS, ENERGY, AGRICULTURE]


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
