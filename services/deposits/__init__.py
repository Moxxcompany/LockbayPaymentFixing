"""
Deposit processing services

This package contains the new atomic deposit processing architecture
designed to solve unconfirmed -> confirmed transaction state issues.
"""

from .crypto_deposit_processor import CryptoDepositProcessor, crypto_deposit_processor

__all__ = ["CryptoDepositProcessor", "crypto_deposit_processor"]