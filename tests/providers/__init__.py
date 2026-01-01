"""
Provider Fakes Package
Reliable test doubles for external services
"""

from .fincra_fake import FincraFakeProvider
from .kraken_fake import KrakenFakeProvider  
from .fastforex_fake import FastForexFakeProvider
from .telegram_fake import TelegramFakeProvider
from .email_fake import EmailFakeProvider
from .provider_factory import ProviderFakeFactory

__all__ = [
    'FincraFakeProvider',
    'KrakenFakeProvider', 
    'FastForexFakeProvider',
    'TelegramFakeProvider',
    'EmailFakeProvider',
    'ProviderFakeFactory'
]