"""
Centralized currency and financial constants
"""

# Supported currencies
SUPPORTED_FIAT = ["USD", "NGN"]
SUPPORTED_CRYPTO = ["BTC", "ETH", "LTC", "DOGE", "BCH", "TRX", "USDT-ERC20", "USDT-TRC20"]
ALL_CURRENCIES = SUPPORTED_FIAT + SUPPORTED_CRYPTO

# Currency display names
CURRENCY_NAMES = {
    "USD": "US Dollar",
    "NGN": "Nigerian Naira", 
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "LTC": "Litecoin",
    "DOGE": "Dogecoin",
    "BCH": "Bitcoin Cash",
    "TRX": "Tron",
    "USDT-ERC20": "Tether (ERC20)",
    "USDT-TRC20": "Tether (TRC20)"
}

# Currency symbols
CURRENCY_SYMBOLS = {
    "USD": "$",
    "NGN": "₦",
    "BTC": "₿",
    "ETH": "Ξ",
    "LTC": "Ł",
    "DOGE": "Ð",
    "BCH": "◊",
    "TRX": "🔴",
    "USDT-ERC20": "₮",
    "USDT-TRC20": "₮"
}
