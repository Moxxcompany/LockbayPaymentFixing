"""Auto-detect network from crypto address format"""

import re
import logging

logger = logging.getLogger(__name__)


def detect_network_from_address(address: str) -> tuple[str | None, bool]:
    """
    Detect cryptocurrency and network from address format

    Returns:
        tuple: (currency, is_valid) where currency is BTC, ETH, LTC, DOGE, BCH, BSC, TRX, USDT-ERC20, USDT-TRC20, or None
    """
    if not address:
        return None, False

    address = address.strip()

    # USDT TRC20 validation - starts with T and 34 characters
    if address.startswith("T") and len(address) == 34:
        if re.match(r"^T[1-9A-HJ-NP-Za-km-z]{33}$", address):
            return "USDT-TRC20", True
        return "USDT-TRC20", False

    # Ethereum-based tokens (ETH, USDT-ERC20, BSC) - starts with 0x and 42 characters
    elif address.startswith("0x") and len(address) == 42:
        if re.match(r"^0x[0-9a-fA-F]{40}$", address):
            # For Ethereum addresses, we'll default to ETH but allow user to specify
            # This could be ETH, USDT-ERC20, or BSC - context will determine
            return "ETH", True
        return "ETH", False

    # Bitcoin addresses (P2PKH) - starts with 1
    elif address.startswith("1") and 26 <= len(address) <= 35:
        if re.match(r"^1[1-9A-HJ-NP-Za-km-z]{25,34}$", address):
            return "BTC", True
        return "BTC", False

    # Bitcoin addresses (P2SH) - starts with 3
    elif address.startswith("3") and 26 <= len(address) <= 35:
        if re.match(r"^3[1-9A-HJ-NP-Za-km-z]{25,34}$", address):
            return "BTC", True
        return "BTC", False

    # Bitcoin addresses (Bech32) - starts with bc1
    elif address.startswith("bc1") and 39 <= len(address) <= 62:
        if re.match(r"^bc1[02-9ac-hj-np-z]{37,61}$", address):
            return "BTC", True
        return "BTC", False

    # Litecoin addresses - starts with L or M
    elif (address.startswith("L") or address.startswith("M")) and 26 <= len(
        address
    ) <= 35:
        if re.match(r"^[LM][1-9A-HJ-NP-Za-km-z]{25,34}$", address):
            return "LTC", True
        return "LTC", False

    # Litecoin Bech32 - starts with ltc1
    elif address.startswith("ltc1") and len(address) >= 39:
        if re.match(r"^ltc1[02-9ac-hj-np-z]+$", address):
            return "LTC", True
        return "LTC", False

    # Dogecoin addresses - starts with D
    elif address.startswith("D") and 26 <= len(address) <= 35:
        if re.match(r"^D[5-9A-HJ-NP-U][1-9A-HJ-NP-Za-km-z]{32}$", address):
            return "DOGE", True
        return "DOGE", False

    # Bitcoin Cash addresses - starts with 1, 3, or q/p (CashAddr)
    elif address.startswith(("bitcoincash:", "q", "p")) or (
        address.startswith(("1", "3")) and 26 <= len(address) <= 35
    ):
        # Basic validation for BCH CashAddr format
        if address.startswith("bitcoincash:"):
            clean_addr = address.replace("bitcoincash:", "")
            if re.match(r"^[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{42}$", clean_addr):
                return "BCH", True
            return "BCH", False
        elif address.startswith(("q", "p")) and len(address) == 42:
            if re.match(r"^[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{42}$", address):
                return "BCH", True
            return "BCH", False
        # Legacy BCH addresses (same as BTC format)
        elif address.startswith(("1", "3")):
            return "BCH", True
        return "BCH", False

    # Try to guess based on partial patterns
    elif address.startswith("T"):
        return "TRX", False  # Could be TRX or USDT-TRC20
    elif address.startswith("0x"):
        return "ETH", False  # Could be ETH, USDT-ERC20, or BSC
    elif address.startswith(("1", "3", "bc1")):
        return "BTC", False
    elif address.startswith(("L", "M", "ltc1")):
        return "LTC", False
    elif address.startswith("D"):
        return "DOGE", False
    elif address.startswith(("q", "p")) or "bitcoincash:" in address:
        return "BCH", False

    return None, False


def get_network_info(currency: str) -> dict:
    """Get currency/network information with fees and processing times"""
    currency_info = {
        "BTC": {
            "name": "Bitcoin",
            "fee": 25.0,
            "time": "30-60 minutes",
            "example": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "description": "Secure, widely accepted",
        },
        "ETH": {
            "name": "Ethereum",
            "fee": 10.0,
            "time": "5-15 minutes",
            "example": "0x742d35Cc6B6C4532CE58F8e3a5e7DEc6eE9AE100",
            "description": "Smart contracts, DeFi",
        },
        "LTC": {
            "name": "Litecoin",
            "fee": 1.0,
            "time": "5-15 minutes",
            "example": "LTC1QVV8R4U2DKZRFZ8DDQZ3NRRQZ...",
            "description": "Fast, low fees",
        },
        "DOGE": {
            "name": "Dogecoin",
            "fee": 0.5,
            "time": "5-10 minutes",
            "example": "DQVVr3c8t8pJ7Y8NCZK8Xc8K8...",
            "description": "Popular, community-driven",
        },
        "BCH": {
            "name": "Bitcoin Cash",
            "fee": 1.0,
            "time": "10-30 minutes",
            "example": "qzry9x8gf2tvdw0s3jn54khce6mua7l...",
            "description": "Fast, low-cost Bitcoin",
        },
        "BSC": {
            "name": "Binance Smart Chain",
            "fee": 1.0,
            "time": "3-5 minutes",
            "example": "0x742d35Cc6B6C4532CE58F8e3a5e7DEc6eE9AE100",
            "description": "Fast, low fees",
        },
        "TRX": {
            "name": "Tron",
            "fee": 1.0,
            "time": "3-5 minutes",
            "example": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            "description": "Ultra-fast, minimal fees",
        },
        "USDT-ERC20": {
            "name": "USDT (Ethereum)",
            "fee": 5.0,
            "time": "5-15 minutes",
            "example": "0x742d35Cc6B6C4532CE58F8e3a5e7DEc6eE9AE100",
            "description": "Stable, widely supported",
        },
        "USDT-TRC20": {
            "name": "USDT (Tron)",
            "fee": 1.0,
            "time": "3-5 minutes",
            "example": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            "description": "Stable, low fees",
        },
    }
    return currency_info.get(
        currency,
        {
            "name": currency,
            "fee": 5.0,
            "time": "10-30 minutes",
            "example": "Address format varies",
            "description": "Cryptocurrency",
        },
    )


def format_address_error(address: str, detected_currency: str | None = None) -> str:
    """Format helpful error message for invalid address"""
    currency_formats = {
        "BTC": {
            "name": "Bitcoin",
            "formats": [
                "Legacy: Starts with '1' (26-35 chars)",
                "SegWit: Starts with '3' (26-35 chars)",
                "Bech32: Starts with 'bc1' (39-62 chars)",
            ],
            "example": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        },
        "ETH": {
            "name": "Ethereum",
            "formats": ["Starts with '0x' (42 chars)", "Uses hexadecimal (0-9, a-f)"],
            "example": "0x742d35Cc6B6C4532CE58F8e3a5e7DEc6eE9AE100",
        },
        "LTC": {
            "name": "Litecoin",
            "formats": [
                "Legacy: Starts with 'L' or 'M' (26-35 chars)",
                "Bech32: Starts with 'ltc1'",
            ],
            "example": "LTC1QVV8R4U2DKZRFZ8DDQZ3NRRQZ...",
        },
        "DOGE": {
            "name": "Dogecoin",
            "formats": ["Starts with 'D' (34 chars)"],
            "example": "DQVVr3c8t8pJ7Y8NCZK8Xc8K8...",
        },
        "BCH": {
            "name": "Bitcoin Cash",
            "formats": [
                "CashAddr: Starts with 'q' or 'p' (42 chars)",
                "Legacy: Starts with '1' or '3'",
                "Full: 'bitcoincash:q...'",
            ],
            "example": "qzry9x8gf2tvdw0s3jn54khce6mua7l...",
        },
        "BSC": {
            "name": "Binance Smart Chain",
            "formats": ["Starts with '0x' (42 chars)", "Uses hexadecimal (0-9, a-f)"],
            "example": "0x742d35Cc6B6C4532CE58F8e3a5e7DEc6eE9AE100",
        },
        "TRX": {
            "name": "Tron",
            "formats": ["Starts with 'T' (34 chars)", "Uses Base58 encoding"],
            "example": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        },
        "USDT-TRC20": {
            "name": "USDT (Tron)",
            "formats": ["Starts with 'T' (34 chars)", "Uses Base58 encoding"],
            "example": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        },
        "USDT-ERC20": {
            "name": "USDT (Ethereum)",
            "formats": ["Starts with '0x' (42 chars)", "Uses hexadecimal (0-9, a-f)"],
            "example": "0x742d35Cc6B6C4532CE58F8e3a5e7DEc6eE9AE100",
        },
    }

    if detected_currency and detected_currency in currency_formats:
        info = currency_formats[detected_currency]
        formats_text = "\n".join([f"• {fmt}" for fmt in info["formats"]])

        return (
            f"❌ Invalid {info['name']} Address\n\n"
            f"Address format requirements:\n{formats_text}\n\n"
            f"Example: `{info['example']}`"
        )
    else:
        return (
            "❌ Unrecognized Address Format\n\n"
            "Supported cryptocurrencies:\n"
            "• Bitcoin (BTC): 1..., 3..., bc1...\n"
            "• Ethereum (ETH): 0x...\n"
            "• USDT-TRC20: T... (Tron)\n"
            "• USDT-ERC20: 0x... (Ethereum)\n"
            "• Litecoin (LTC): L..., M..., ltc1...\n"
            "• Dogecoin (DOGE): D...\n"
            "• Bitcoin Cash (BCH): q..., p...\n"
            "• BSC/TRX: Various formats\n\n"
            "💡 Copy address directly from your wallet"
        )
