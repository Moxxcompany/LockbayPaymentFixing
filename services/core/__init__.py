"""
Core Payment Processing Module

Unified payment architecture that replaces the current 100+ service complex architecture
with clean, simple interfaces for all payment operations.

Key Components:
- PaymentProcessor: Main entry point for all payment operations
- PayinRequest/PayoutRequest: Standardized request formats
- PaymentResult: Standardized response format
- Provider adapters: Clean interfaces to Fincra, Kraken, BlockBee
"""

from .payment_processor import (
    PaymentProcessor, 
    payment_processor,
    process_payin,
    process_payout, 
    check_balances
)

from .payment_data_structures import (
    PayinRequest,
    PayoutRequest,
    PaymentResult,
    PaymentDestination,
    BalanceCheckResult,
    BalanceSnapshot,
    TransactionStatus,
    PaymentError,
    PaymentProvider,
    create_success_result,
    create_error_result
)

from .payment_provider_interface import (
    PaymentProviderInterface,
    FincraProviderAdapter,
    KrakenProviderAdapter,
    BlockBeeProviderAdapter
)

__all__ = [
    # Main processor
    'PaymentProcessor',
    'payment_processor',
    'process_payin',
    'process_payout',
    'check_balances',
    
    # Data structures
    'PayinRequest',
    'PayoutRequest', 
    'PaymentResult',
    'PaymentDestination',
    'BalanceCheckResult',
    'BalanceSnapshot',
    'TransactionStatus',
    'PaymentError',
    'PaymentProvider',
    'create_success_result',
    'create_error_result',
    
    # Provider interfaces
    'PaymentProviderInterface',
    'FincraProviderAdapter',
    'KrakenProviderAdapter',
    'BlockBeeProviderAdapter'
]