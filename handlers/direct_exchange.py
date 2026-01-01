"""
Direct Exchange Handler - Compatibility Layer
Re-exports from exchange_handler.py for backward compatibility with test imports
"""

from handlers.exchange_handler import ExchangeHandler

__all__ = [
    'DirectExchangeHandler',
]

# Create alias for tests that expect DirectExchangeHandler
DirectExchangeHandler = ExchangeHandler
