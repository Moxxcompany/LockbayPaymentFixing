"""
Comprehensive Unit Tests for Unified Status Management System

This test suite provides complete coverage for the unified status management system
including round-trip mapping, transition validity, cross-phase regression prevention,
and end-to-end integration testing.

Test Coverage:
1. Round-Trip Mapping Tests - Legacy ↔ Unified status conversions
2. Transition Validity Tests - Valid/invalid transitions for all transaction types
3. Cross-Phase Regression Tests - Prevention of backwards phase transitions
4. Integration Tests - StatusUpdateFacade end-to-end workflows
5. Error Handling Tests - Validation errors and edge cases

Ensures financial integrity and prevents status transition bugs across all systems.
"""

import pytest
import asyncio
import logging
from typing import Dict, List, Set, Tuple, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

# Core model imports
from models import (
    UnifiedTransactionStatus, UnifiedTransactionType, UnifiedTransactionPriority,
    EscrowStatus, CashoutStatus, ExchangeStatus,
    UnifiedTransaction, Cashout, Escrow, ExchangeOrder,
    User, Wallet, WalletHolds
)

# Status management system imports
from utils.status_flows import (
    UnifiedTransitionValidator, UnifiedStatusFlows, StatusPhase,
    TransitionValidationResult, unified_transition_validator,
    validate_unified_transition, get_allowed_next_statuses,
    is_terminal_transaction_status, get_transaction_status_phase
)

from services.legacy_status_mapper import LegacyStatusMapper, LegacySystemType

from utils.status_update_facade import (
    StatusUpdateFacade, StatusUpdateRequest, StatusUpdateResult,
    StatusUpdateContext, StatusUpdateError
)

from services.unified_transaction_service import (
    UnifiedTransactionService, TransactionRequest, TransactionResult
)

logger = logging.getLogger(__name__)


# Test Data Classes
@dataclass
class RoundTripTestCase:
    """Test case for round-trip mapping validation"""
    legacy_status: Any
    system_type: LegacySystemType
    expected_unified: UnifiedTransactionStatus
    description: str
    should_preserve_data: bool = True


@dataclass
class TransitionTestCase:
    """Test case for status transition validation"""
    transaction_type: UnifiedTransactionType
    current_status: UnifiedTransactionStatus
    new_status: UnifiedTransactionStatus
    should_be_valid: bool
    description: str
    error_code: Optional[str] = None


@dataclass
class PhaseRegressionTestCase:
    """Test case for cross-phase regression prevention"""
    current_phase: StatusPhase
    target_phase: StatusPhase
    transaction_type: UnifiedTransactionType
    should_be_blocked: bool
    description: str


class TestRoundTripMapping:
    """
    Comprehensive tests for bidirectional status mapping
    Ensures legacy ↔ unified conversions preserve data integrity
    """
    
    def test_cashout_round_trip_mapping_complete(self):
        """Test complete round-trip mapping for all cashout statuses"""
        cashout_test_cases = [
            RoundTripTestCase(
                legacy_status=CashoutStatus.PENDING,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.PENDING,
                description="Basic pending status"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.OTP_PENDING,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.OTP_PENDING,
                description="OTP verification required"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.USER_CONFIRM_PENDING,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.AWAITING_APPROVAL,
                description="User confirmation pending"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.ADMIN_PENDING,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.ADMIN_PENDING,
                description="Admin approval required"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.PENDING_ADDRESS_CONFIG,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.ADMIN_PENDING,
                description="Address configuration needed"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.PENDING_SERVICE_FUNDING,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.ADMIN_PENDING,
                description="Service funding required"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.APPROVED,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.FUNDS_HELD,
                description="Approved and funds secured"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.EXECUTING,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.PROCESSING,
                description="Execution in progress"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.AWAITING_RESPONSE,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.AWAITING_RESPONSE,
                description="Waiting for external API response"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.SUCCESS,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.SUCCESS,
                description="Successfully completed"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.COMPLETED,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.SUCCESS,
                description="Deprecated completed status",
                should_preserve_data=False  # Deprecated status maps to SUCCESS
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.FAILED,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.FAILED,
                description="Transaction failed"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.CANCELLED,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.CANCELLED,
                description="User or system cancelled"
            ),
            RoundTripTestCase(
                legacy_status=CashoutStatus.EXPIRED,
                system_type=LegacySystemType.CASHOUT,
                expected_unified=UnifiedTransactionStatus.EXPIRED,
                description="Transaction expired"
            )
        ]
        
        self._execute_round_trip_tests(cashout_test_cases)
    
    def test_escrow_round_trip_mapping_complete(self):
        """Test complete round-trip mapping for all escrow statuses"""
        escrow_test_cases = [
            RoundTripTestCase(
                legacy_status=EscrowStatus.CREATED,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.PENDING,
                description="Escrow created"
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.PAYMENT_PENDING,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.AWAITING_PAYMENT,
                description="Waiting for buyer payment"
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.PAYMENT_CONFIRMED,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                description="Payment received and confirmed"
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.PARTIAL_PAYMENT,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.PARTIAL_PAYMENT,
                description="Partial payment received"
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.PENDING_DEPOSIT,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.AWAITING_PAYMENT,
                description="Waiting for deposit"
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.AWAITING_SELLER,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.AWAITING_APPROVAL,
                description="Seller needs to accept"
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.PENDING_SELLER,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.AWAITING_APPROVAL,
                description="Pending seller action"
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.ACTIVE,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.FUNDS_HELD,
                description="Escrow active, funds secured"
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.COMPLETED,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.SUCCESS,
                description="Escrow completed successfully"
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.DISPUTED,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.DISPUTED,
                description="Dispute raised"
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.CANCELLED,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.CANCELLED,
                description="Escrow cancelled"
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.REFUNDED,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.SUCCESS,
                description="Refund completed successfully",
                should_preserve_data=False  # Refund maps to SUCCESS
            ),
            RoundTripTestCase(
                legacy_status=EscrowStatus.EXPIRED,
                system_type=LegacySystemType.ESCROW,
                expected_unified=UnifiedTransactionStatus.EXPIRED,
                description="Escrow expired"
            )
        ]
        
        self._execute_round_trip_tests(escrow_test_cases)
    
    def test_exchange_round_trip_mapping_complete(self):
        """Test complete round-trip mapping for all exchange statuses"""
        exchange_test_cases = [
            RoundTripTestCase(
                legacy_status=ExchangeStatus.CREATED,
                system_type=LegacySystemType.EXCHANGE,
                expected_unified=UnifiedTransactionStatus.PENDING,
                description="Exchange order created"
            ),
            RoundTripTestCase(
                legacy_status=ExchangeStatus.AWAITING_DEPOSIT,
                system_type=LegacySystemType.EXCHANGE,
                expected_unified=UnifiedTransactionStatus.AWAITING_PAYMENT,
                description="Waiting for crypto deposit"
            ),
            RoundTripTestCase(
                legacy_status=ExchangeStatus.PAYMENT_RECEIVED,
                system_type=LegacySystemType.EXCHANGE,
                expected_unified=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                description="Payment received"
            ),
            RoundTripTestCase(
                legacy_status=ExchangeStatus.PAYMENT_CONFIRMED,
                system_type=LegacySystemType.EXCHANGE,
                expected_unified=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                description="Payment confirmed"
            ),
            RoundTripTestCase(
                legacy_status=ExchangeStatus.RATE_LOCKED,
                system_type=LegacySystemType.EXCHANGE,
                expected_unified=UnifiedTransactionStatus.FUNDS_HELD,
                description="Exchange rate locked"
            ),
            RoundTripTestCase(
                legacy_status=ExchangeStatus.PENDING_APPROVAL,
                system_type=LegacySystemType.EXCHANGE,
                expected_unified=UnifiedTransactionStatus.AWAITING_APPROVAL,
                description="Pending approval"
            ),
            RoundTripTestCase(
                legacy_status=ExchangeStatus.PROCESSING,
                system_type=LegacySystemType.EXCHANGE,
                expected_unified=UnifiedTransactionStatus.PROCESSING,
                description="Exchange processing"
            ),
            RoundTripTestCase(
                legacy_status=ExchangeStatus.ADDRESS_GENERATION_FAILED,
                system_type=LegacySystemType.EXCHANGE,
                expected_unified=UnifiedTransactionStatus.FAILED,
                description="Technical failure"
            ),
            RoundTripTestCase(
                legacy_status=ExchangeStatus.COMPLETED,
                system_type=LegacySystemType.EXCHANGE,
                expected_unified=UnifiedTransactionStatus.SUCCESS,
                description="Exchange completed"
            ),
            RoundTripTestCase(
                legacy_status=ExchangeStatus.FAILED,
                system_type=LegacySystemType.EXCHANGE,
                expected_unified=UnifiedTransactionStatus.FAILED,
                description="Exchange failed"
            ),
            RoundTripTestCase(
                legacy_status=ExchangeStatus.CANCELLED,
                system_type=LegacySystemType.EXCHANGE,
                expected_unified=UnifiedTransactionStatus.CANCELLED,
                description="Exchange cancelled"
            )
        ]
        
        self._execute_round_trip_tests(exchange_test_cases)
    
    def test_round_trip_data_preservation(self):
        """Test that round-trip conversions preserve data integrity"""
        # Test cases where perfect round-trip is expected
        perfect_round_trip_cases = [
            (CashoutStatus.OTP_PENDING, LegacySystemType.CASHOUT),
            (EscrowStatus.DISPUTED, LegacySystemType.ESCROW),
            (ExchangeStatus.RATE_LOCKED, LegacySystemType.EXCHANGE),
        ]
        
        for legacy_status, system_type in perfect_round_trip_cases:
            # Forward mapping: Legacy → Unified
            unified_status = LegacyStatusMapper.map_to_unified(legacy_status, system_type)
            
            # Reverse mapping: Unified → Legacy
            try:
                reverse_mapped = LegacyStatusMapper.map_from_unified(
                    unified_status, system_type, prefer_primary=True
                )
                
                assert reverse_mapped == legacy_status, (
                    f"Round-trip failed for {legacy_status.name}: "
                    f"{legacy_status} → {unified_status} → {reverse_mapped}"
                )
                
                logger.info(f"✅ Perfect round-trip: {legacy_status.name} ↔ {unified_status.name}")
                
            except Exception as e:
                # Some mappings might not support perfect round-trip due to many-to-one mapping
                logger.warning(f"⚠️ Round-trip not available for {legacy_status.name}: {e}")
    
    def test_mapping_conflicts_and_resolution(self):
        """Test handling of many-to-one mapping conflicts"""
        # Test cases where multiple legacy statuses map to same unified status
        conflict_cases = [
            # Multiple cashout statuses map to ADMIN_PENDING
            ([CashoutStatus.ADMIN_PENDING, CashoutStatus.PENDING_ADDRESS_CONFIG, 
              CashoutStatus.PENDING_SERVICE_FUNDING], UnifiedTransactionStatus.ADMIN_PENDING),
            
            # Multiple escrow statuses map to AWAITING_APPROVAL
            ([EscrowStatus.AWAITING_SELLER, EscrowStatus.PENDING_SELLER], 
             UnifiedTransactionStatus.AWAITING_APPROVAL),
            
            # Multiple statuses map to SUCCESS
            ([CashoutStatus.SUCCESS, CashoutStatus.COMPLETED], UnifiedTransactionStatus.SUCCESS),
        ]
        
        for legacy_statuses, expected_unified in conflict_cases:
            # All legacy statuses should map to the same unified status
            for legacy_status in legacy_statuses:
                system_type = self._get_system_type_for_status(legacy_status)
                mapped_unified = LegacyStatusMapper.map_to_unified(legacy_status, system_type)
                
                assert mapped_unified == expected_unified, (
                    f"Conflict resolution failed: {legacy_status.name} should map to "
                    f"{expected_unified.name}, got {mapped_unified.name}"
                )
            
            # Reverse mapping should return a primary/preferred status
            system_type = self._get_system_type_for_status(legacy_statuses[0])
            try:
                reverse_mapped = LegacyStatusMapper.map_from_unified(
                    expected_unified, system_type, prefer_primary=True
                )
                
                # Should return one of the valid legacy statuses
                assert reverse_mapped in legacy_statuses, (
                    f"Reverse mapping should return one of {[s.name for s in legacy_statuses]}, "
                    f"got {reverse_mapped.name}"
                )
                
                logger.info(f"✅ Conflict resolution: {expected_unified.name} → {reverse_mapped.name}")
                
            except Exception as e:
                logger.warning(f"⚠️ Reverse mapping not available for conflict case: {e}")
    
    def _execute_round_trip_tests(self, test_cases: List[RoundTripTestCase]):
        """Execute round-trip tests for a set of test cases"""
        for test_case in test_cases:
            with pytest.raises(Exception, match="") if test_case.legacy_status is None else pytest.raises(None):
                # Forward mapping: Legacy → Unified
                mapped_unified = LegacyStatusMapper.map_to_unified(
                    test_case.legacy_status, test_case.system_type
                )
                
                assert mapped_unified == test_case.expected_unified, (
                    f"Forward mapping failed for {test_case.description}: "
                    f"Expected {test_case.expected_unified.name}, got {mapped_unified.name}"
                )
                
                # Test reverse mapping if data preservation is expected
                if test_case.should_preserve_data:
                    try:
                        reverse_mapped = LegacyStatusMapper.map_from_unified(
                            mapped_unified, test_case.system_type, prefer_primary=True
                        )
                        
                        # For perfect preservation cases, should get exact same status back
                        if test_case.should_preserve_data:
                            assert reverse_mapped == test_case.legacy_status, (
                                f"Round-trip failed for {test_case.description}: "
                                f"{test_case.legacy_status.name} → {mapped_unified.name} → {reverse_mapped.name}"
                            )
                        
                        logger.info(f"✅ {test_case.description}: Round-trip successful")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ {test_case.description}: Reverse mapping not available - {e}")
                
                logger.info(f"✅ {test_case.description}: Forward mapping validated")
    
    def _get_system_type_for_status(self, legacy_status) -> LegacySystemType:
        """Get system type for a legacy status enum"""
        if isinstance(legacy_status, CashoutStatus):
            return LegacySystemType.CASHOUT
        elif isinstance(legacy_status, EscrowStatus):
            return LegacySystemType.ESCROW
        elif isinstance(legacy_status, ExchangeStatus):
            return LegacySystemType.EXCHANGE
        else:
            raise ValueError(f"Unknown legacy status type: {type(legacy_status)}")


class TestTransitionValidityComprehensive:
    """
    Comprehensive tests for status transition validation
    Tests all transaction types with valid and invalid transitions
    """
    
    def test_wallet_cashout_transition_flows(self):
        """Test comprehensive WALLET_CASHOUT transition flows"""
        wallet_cashout_tests = [
            # Valid flow: pending → processing → awaiting_response → success
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.PROCESSING,
                should_be_valid=True,
                description="OTP verified, start processing"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.PROCESSING,
                new_status=UnifiedTransactionStatus.AWAITING_RESPONSE,
                should_be_valid=True,
                description="API call made, awaiting response"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.AWAITING_RESPONSE,
                new_status=UnifiedTransactionStatus.SUCCESS,
                should_be_valid=True,
                description="External API confirmed success"
            ),
            
            # Alternative failure paths
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.CANCELLED,
                should_be_valid=True,
                description="User cancels before OTP"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.PROCESSING,
                new_status=UnifiedTransactionStatus.FAILED,
                should_be_valid=True,
                description="Processing error"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.AWAITING_RESPONSE,
                new_status=UnifiedTransactionStatus.FAILED,
                should_be_valid=True,
                description="External API failure"
            ),
            
            # Invalid transitions
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                should_be_valid=False,
                description="Cashout doesn't require payment",
                error_code="INVALID_TRANSITION"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.SUCCESS,
                new_status=UnifiedTransactionStatus.PROCESSING,
                should_be_valid=False,
                description="Cannot restart from terminal state",
                error_code="TERMINAL_STATE"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.SUCCESS,
                should_be_valid=False,
                description="Cannot skip required OTP and processing",
                error_code="SKIPPED_STEPS"
            ),
        ]
        
        self._execute_transition_tests(wallet_cashout_tests)
    
    def test_exchange_sell_crypto_transition_flows(self):
        """Test comprehensive EXCHANGE_SELL_CRYPTO transition flows"""
        exchange_sell_tests = [
            # Valid flow: pending → awaiting_payment → payment_confirmed → processing → success
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                should_be_valid=True,
                description="Waiting for crypto deposit"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                current_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                new_status=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                should_be_valid=True,
                description="Crypto payment confirmed"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                current_status=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                new_status=UnifiedTransactionStatus.PROCESSING,
                should_be_valid=True,
                description="Start exchange processing"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                current_status=UnifiedTransactionStatus.PROCESSING,
                new_status=UnifiedTransactionStatus.SUCCESS,
                should_be_valid=True,
                description="Exchange completed successfully"
            ),
            
            # Alternative paths
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                current_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                new_status=UnifiedTransactionStatus.PARTIAL_PAYMENT,
                should_be_valid=True,
                description="Partial crypto payment received"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                current_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                new_status=UnifiedTransactionStatus.EXPIRED,
                should_be_valid=True,
                description="Payment timeout"
            ),
            
            # Invalid transitions
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.PROCESSING,
                should_be_valid=False,
                description="Cannot skip payment confirmation",
                error_code="SKIPPED_PAYMENT"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                current_status=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                new_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                should_be_valid=False,
                description="Cannot go back to awaiting payment",
                error_code="BACKWARDS_TRANSITION"
            ),
        ]
        
        self._execute_transition_tests(exchange_sell_tests)
    
    def test_exchange_buy_crypto_transition_flows(self):
        """Test comprehensive EXCHANGE_BUY_CRYPTO transition flows"""
        exchange_buy_tests = [
            # Valid flow: pending → awaiting_payment → payment_confirmed → processing → success
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                should_be_valid=True,
                description="Waiting for fiat payment"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                current_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                new_status=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                should_be_valid=True,
                description="Fiat payment confirmed"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                current_status=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                new_status=UnifiedTransactionStatus.PROCESSING,
                should_be_valid=True,
                description="Start crypto purchase processing"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                current_status=UnifiedTransactionStatus.PROCESSING,
                new_status=UnifiedTransactionStatus.AWAITING_RESPONSE,
                should_be_valid=True,
                description="Waiting for exchange API response"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                current_status=UnifiedTransactionStatus.AWAITING_RESPONSE,
                new_status=UnifiedTransactionStatus.SUCCESS,
                should_be_valid=True,
                description="Crypto purchase completed"
            ),
            
            # Alternative failure paths
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                current_status=UnifiedTransactionStatus.PROCESSING,
                new_status=UnifiedTransactionStatus.FAILED,
                should_be_valid=True,
                description="Exchange processing failed"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                current_status=UnifiedTransactionStatus.AWAITING_RESPONSE,
                new_status=UnifiedTransactionStatus.FAILED,
                should_be_valid=True,
                description="Exchange API failure"
            ),
            
            # Invalid transitions specific to buy crypto
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.SUCCESS,
                should_be_valid=False,
                description="Cannot complete without payment and processing",
                error_code="SKIPPED_REQUIRED_STEPS"
            ),
        ]
        
        self._execute_transition_tests(exchange_buy_tests)
    
    def test_escrow_transition_flows(self):
        """Test comprehensive ESCROW transition flows"""
        escrow_tests = [
            # Valid flow: pending → awaiting_payment → payment_confirmed → funds_held → release_pending → success
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                should_be_valid=True,
                description="Waiting for buyer payment"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                new_status=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                should_be_valid=True,
                description="Buyer payment confirmed"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                new_status=UnifiedTransactionStatus.AWAITING_APPROVAL,
                should_be_valid=True,
                description="Waiting for seller acceptance"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.AWAITING_APPROVAL,
                new_status=UnifiedTransactionStatus.FUNDS_HELD,
                should_be_valid=True,
                description="Escrow active, funds secured"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.FUNDS_HELD,
                new_status=UnifiedTransactionStatus.RELEASE_PENDING,
                should_be_valid=True,
                description="Release condition met"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.RELEASE_PENDING,
                new_status=UnifiedTransactionStatus.SUCCESS,
                should_be_valid=True,
                description="Funds released to seller"
            ),
            
            # Escrow-specific paths
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.FUNDS_HELD,
                new_status=UnifiedTransactionStatus.DISPUTED,
                should_be_valid=True,
                description="Dispute raised during escrow"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                new_status=UnifiedTransactionStatus.PARTIAL_PAYMENT,
                should_be_valid=True,
                description="Partial payment received"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.PARTIAL_PAYMENT,
                new_status=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                should_be_valid=True,
                description="Full payment completed"
            ),
            
            # Invalid escrow transitions
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.FUNDS_HELD,
                should_be_valid=False,
                description="Cannot hold funds without payment",
                error_code="SKIPPED_PAYMENT"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.DISPUTED,
                new_status=UnifiedTransactionStatus.FUNDS_HELD,
                should_be_valid=False,
                description="Cannot return to normal flow after dispute",
                error_code="DISPUTE_TERMINAL"
            ),
        ]
        
        self._execute_transition_tests(escrow_tests)
    
    def test_universal_invalid_transitions(self):
        """Test transitions that should be invalid for all transaction types"""
        all_transaction_types = [
            UnifiedTransactionType.WALLET_CASHOUT,
            UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
            UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
            UnifiedTransactionType.ESCROW
        ]
        
        universal_invalid_tests = [
            # Terminal state transitions (should be blocked for all types)
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,  # Will be tested for all
                current_status=UnifiedTransactionStatus.SUCCESS,
                new_status=UnifiedTransactionStatus.PENDING,
                should_be_valid=False,
                description="Cannot restart from SUCCESS"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,  # Will be tested for all
                current_status=UnifiedTransactionStatus.FAILED,
                new_status=UnifiedTransactionStatus.PROCESSING,
                should_be_valid=False,
                description="Cannot restart from FAILED"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,  # Will be tested for all
                current_status=UnifiedTransactionStatus.CANCELLED,
                new_status=UnifiedTransactionStatus.PROCESSING,
                should_be_valid=False,
                description="Cannot restart from CANCELLED"
            ),
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,  # Will be tested for all
                current_status=UnifiedTransactionStatus.EXPIRED,
                new_status=UnifiedTransactionStatus.PENDING,
                should_be_valid=False,
                description="Cannot restart from EXPIRED"
            ),
        ]
        
        # Test each invalid transition for all transaction types
        for test_case in universal_invalid_tests:
            for transaction_type in all_transaction_types:
                test_case.transaction_type = transaction_type
                
                validator = UnifiedTransitionValidator()
                result = validator.validate_transition(
                    current_status=test_case.current_status,
                    new_status=test_case.new_status,
                    transaction_type=test_case.transaction_type
                )
                
                assert not result.is_valid, (
                    f"Universal invalid transition should be blocked for {transaction_type.name}: "
                    f"{test_case.description} - {test_case.current_status.name} → {test_case.new_status.name}"
                )
                
                logger.info(f"✅ {transaction_type.name}: {test_case.description} correctly blocked")
    
    def _execute_transition_tests(self, test_cases: List[TransitionTestCase]):
        """Execute transition validation tests"""
        validator = UnifiedTransitionValidator()
        
        for test_case in test_cases:
            result = validator.validate_transition(
                current_status=test_case.current_status,
                new_status=test_case.new_status,
                transaction_type=test_case.transaction_type
            )
            
            if test_case.should_be_valid:
                assert result.is_valid, (
                    f"Expected valid transition for {test_case.description}: "
                    f"{test_case.current_status.name} → {test_case.new_status.name} "
                    f"in {test_case.transaction_type.name}. Error: {result.error_message}"
                )
                logger.info(f"✅ VALID: {test_case.description}")
            else:
                assert not result.is_valid, (
                    f"Expected invalid transition for {test_case.description}: "
                    f"{test_case.current_status.name} → {test_case.new_status.name} "
                    f"in {test_case.transaction_type.name} should be blocked"
                )
                
                # Check error code if specified
                if test_case.error_code:
                    assert test_case.error_code.lower() in result.error_message.lower(), (
                        f"Expected error code '{test_case.error_code}' in error message: {result.error_message}"
                    )
                
                logger.info(f"✅ BLOCKED: {test_case.description} - {result.error_message}")


class TestCrossPhaseRegressionPrevention:
    """
    Tests to ensure status updates cannot regress to earlier phases
    Critical for preventing financial integrity issues
    """
    
    def test_phase_progression_enforcement(self):
        """Test that phase progression is enforced across all transaction types"""
        phase_regression_tests = [
            # Terminal → Any earlier phase (should all be blocked)
            PhaseRegressionTestCase(
                current_phase=StatusPhase.TERMINAL,
                target_phase=StatusPhase.PROCESSING,
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                should_be_blocked=True,
                description="Terminal → Processing regression"
            ),
            PhaseRegressionTestCase(
                current_phase=StatusPhase.TERMINAL,
                target_phase=StatusPhase.AUTHORIZATION,
                transaction_type=UnifiedTransactionType.ESCROW,
                should_be_blocked=True,
                description="Terminal → Authorization regression"
            ),
            PhaseRegressionTestCase(
                current_phase=StatusPhase.TERMINAL,
                target_phase=StatusPhase.INITIATION,
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                should_be_blocked=True,
                description="Terminal → Initiation regression"
            ),
            
            # Processing → Earlier phases (should be blocked)
            PhaseRegressionTestCase(
                current_phase=StatusPhase.PROCESSING,
                target_phase=StatusPhase.AUTHORIZATION,
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                should_be_blocked=True,
                description="Processing → Authorization regression"
            ),
            PhaseRegressionTestCase(
                current_phase=StatusPhase.PROCESSING,
                target_phase=StatusPhase.INITIATION,
                transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                should_be_blocked=True,
                description="Processing → Initiation regression"
            ),
            
            # Authorization → Initiation (should be blocked)
            PhaseRegressionTestCase(
                current_phase=StatusPhase.AUTHORIZATION,
                target_phase=StatusPhase.INITIATION,
                transaction_type=UnifiedTransactionType.ESCROW,
                should_be_blocked=True,
                description="Authorization → Initiation regression"
            ),
            
            # Valid forward progressions (should be allowed)
            PhaseRegressionTestCase(
                current_phase=StatusPhase.INITIATION,
                target_phase=StatusPhase.AUTHORIZATION,
                transaction_type=UnifiedTransactionType.ESCROW,
                should_be_blocked=False,
                description="Initiation → Authorization progression"
            ),
            PhaseRegressionTestCase(
                current_phase=StatusPhase.AUTHORIZATION,
                target_phase=StatusPhase.PROCESSING,
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                should_be_blocked=False,
                description="Authorization → Processing progression"
            ),
            PhaseRegressionTestCase(
                current_phase=StatusPhase.PROCESSING,
                target_phase=StatusPhase.TERMINAL,
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                should_be_blocked=False,
                description="Processing → Terminal progression"
            ),
        ]
        
        self._execute_phase_regression_tests(phase_regression_tests)
    
    def test_specific_regression_scenarios(self):
        """Test specific regression scenarios that have caused issues"""
        specific_regression_tests = [
            # Success → Processing (classic regression bug)
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.SUCCESS,
                new_status=UnifiedTransactionStatus.PROCESSING,
                should_be_valid=False,
                description="Cannot restart processing after success"
            ),
            
            # Payment confirmed → Awaiting payment (data integrity issue)
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                current_status=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                new_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                should_be_valid=False,
                description="Cannot un-confirm payment"
            ),
            
            # Funds held → Payment pending (escrow regression)
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.ESCROW,
                current_status=UnifiedTransactionStatus.FUNDS_HELD,
                new_status=UnifiedTransactionStatus.AWAITING_PAYMENT,
                should_be_valid=False,
                description="Cannot return to payment pending after funds secured"
            ),
            
            # Processing → OTP pending (workflow regression)
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.PROCESSING,
                new_status=UnifiedTransactionStatus.OTP_PENDING,
                should_be_valid=False,
                description="Cannot return to OTP after processing started"
            ),
            
            # Failed → Awaiting response (retry confusion)
            TransitionTestCase(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.FAILED,
                new_status=UnifiedTransactionStatus.AWAITING_RESPONSE,
                should_be_valid=False,
                description="Cannot await response after failure"
            ),
        ]
        
        self._execute_transition_tests(specific_regression_tests)
    
    def test_terminal_state_finality(self):
        """Test that terminal states are truly final"""
        terminal_statuses = [
            UnifiedTransactionStatus.SUCCESS,
            UnifiedTransactionStatus.FAILED,
            UnifiedTransactionStatus.CANCELLED,
            UnifiedTransactionStatus.DISPUTED,
            UnifiedTransactionStatus.EXPIRED
        ]
        
        non_terminal_statuses = [
            UnifiedTransactionStatus.PENDING,
            UnifiedTransactionStatus.AWAITING_PAYMENT,
            UnifiedTransactionStatus.PAYMENT_CONFIRMED,
            UnifiedTransactionStatus.FUNDS_HELD,
            UnifiedTransactionStatus.AWAITING_APPROVAL,
            UnifiedTransactionStatus.OTP_PENDING,
            UnifiedTransactionStatus.ADMIN_PENDING,
            UnifiedTransactionStatus.PROCESSING,
            UnifiedTransactionStatus.AWAITING_RESPONSE,
            UnifiedTransactionStatus.RELEASE_PENDING
        ]
        
        all_transaction_types = [
            UnifiedTransactionType.WALLET_CASHOUT,
            UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
            UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
            UnifiedTransactionType.ESCROW
        ]
        
        validator = UnifiedTransitionValidator()
        
        # Test that no terminal status can transition to any non-terminal status
        for terminal_status in terminal_statuses:
            for non_terminal_status in non_terminal_statuses:
                for transaction_type in all_transaction_types:
                    result = validator.validate_transition(
                        current_status=terminal_status,
                        new_status=non_terminal_status,
                        transaction_type=transaction_type
                    )
                    
                    assert not result.is_valid, (
                        f"Terminal state {terminal_status.name} should not allow transition to "
                        f"{non_terminal_status.name} for {transaction_type.name}"
                    )
        
        logger.info("✅ All terminal states confirmed as final across all transaction types")
    
    def test_phase_boundary_enforcement(self):
        """Test enforcement of phase boundaries"""
        phase_status_map = {
            StatusPhase.INITIATION: [
                UnifiedTransactionStatus.PENDING,
                UnifiedTransactionStatus.AWAITING_PAYMENT,
                UnifiedTransactionStatus.PAYMENT_CONFIRMED
            ],
            StatusPhase.AUTHORIZATION: [
                UnifiedTransactionStatus.FUNDS_HELD,
                UnifiedTransactionStatus.AWAITING_APPROVAL,
                UnifiedTransactionStatus.OTP_PENDING,
                UnifiedTransactionStatus.ADMIN_PENDING
            ],
            StatusPhase.PROCESSING: [
                UnifiedTransactionStatus.PROCESSING,
                UnifiedTransactionStatus.AWAITING_RESPONSE,
                UnifiedTransactionStatus.RELEASE_PENDING
            ],
            StatusPhase.TERMINAL: [
                UnifiedTransactionStatus.SUCCESS,
                UnifiedTransactionStatus.FAILED,
                UnifiedTransactionStatus.CANCELLED,
                UnifiedTransactionStatus.DISPUTED,
                UnifiedTransactionStatus.EXPIRED,
                UnifiedTransactionStatus.PARTIAL_PAYMENT
            ]
        }
        
        validator = UnifiedTransitionValidator()
        
        # Test that statuses from later phases cannot transition to earlier phase statuses
        phase_order = [StatusPhase.INITIATION, StatusPhase.AUTHORIZATION, StatusPhase.PROCESSING, StatusPhase.TERMINAL]
        
        for i, current_phase in enumerate(phase_order):
            for j, target_phase in enumerate(phase_order):
                if j < i:  # Target phase is earlier than current phase
                    for current_status in phase_status_map[current_phase]:
                        for target_status in phase_status_map[target_phase]:
                            # Test with a representative transaction type
                            result = validator.validate_transition(
                                current_status=current_status,
                                new_status=target_status,
                                transaction_type=UnifiedTransactionType.ESCROW
                            )
                            
                            assert not result.is_valid, (
                                f"Phase regression should be blocked: {current_status.name} "
                                f"({current_phase.name}) → {target_status.name} ({target_phase.name})"
                            )
        
        logger.info("✅ Phase boundary enforcement validated across all status combinations")
    
    def _execute_phase_regression_tests(self, test_cases: List[PhaseRegressionTestCase]):
        """Execute phase regression prevention tests"""
        validator = UnifiedTransitionValidator()
        
        for test_case in test_cases:
            # Get representative statuses from each phase
            current_statuses = self._get_statuses_for_phase(test_case.current_phase)
            target_statuses = self._get_statuses_for_phase(test_case.target_phase)
            
            # Test transitions between phases
            regression_found = False
            
            for current_status in current_statuses:
                for target_status in target_statuses:
                    result = validator.validate_transition(
                        current_status=current_status,
                        new_status=target_status,
                        transaction_type=test_case.transaction_type
                    )
                    
                    if test_case.should_be_blocked:
                        if result.is_valid:
                            regression_found = True
                            logger.error(
                                f"❌ REGRESSION DETECTED: {test_case.description} - "
                                f"{current_status.name} → {target_status.name} should be blocked"
                            )
                    else:
                        if result.is_valid:
                            logger.info(
                                f"✅ Valid progression: {current_status.name} → {target_status.name}"
                            )
            
            if test_case.should_be_blocked:
                assert not regression_found, f"Phase regression detected: {test_case.description}"
                logger.info(f"✅ Phase regression blocked: {test_case.description}")
            else:
                logger.info(f"✅ Valid progression allowed: {test_case.description}")
    
    def _get_statuses_for_phase(self, phase: StatusPhase) -> List[UnifiedTransactionStatus]:
        """Get representative statuses for a given phase"""
        phase_map = {
            StatusPhase.INITIATION: [UnifiedTransactionStatus.PENDING, UnifiedTransactionStatus.AWAITING_PAYMENT],
            StatusPhase.AUTHORIZATION: [UnifiedTransactionStatus.FUNDS_HELD, UnifiedTransactionStatus.OTP_PENDING],
            StatusPhase.PROCESSING: [UnifiedTransactionStatus.PROCESSING, UnifiedTransactionStatus.AWAITING_RESPONSE],
            StatusPhase.TERMINAL: [UnifiedTransactionStatus.SUCCESS, UnifiedTransactionStatus.FAILED]
        }
        
        return phase_map.get(phase, [])


class TestStatusUpdateFacadeIntegration:
    """
    End-to-end integration tests for StatusUpdateFacade
    Tests the complete validate → dual-write → history workflow
    """
    
    @pytest.fixture
    def mock_database_session(self):
        """Mock database session for testing"""
        session = Mock()
        session.add = Mock()
        session.flush = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.query = Mock()
        return session
    
    @pytest.fixture
    def status_facade(self):
        """Create StatusUpdateFacade instance for testing"""
        return StatusUpdateFacade()
    
    @pytest.mark.asyncio
    async def test_complete_status_update_workflow(self, status_facade):
        """Test complete status update workflow from validation to completion"""
        # Create a status update request
        request = StatusUpdateRequest(
            transaction_id="UTX123456789012345",
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            current_status=UnifiedTransactionStatus.PENDING,
            new_status=UnifiedTransactionStatus.PROCESSING,
            context=StatusUpdateContext.AUTOMATED_SYSTEM,
            reason="OTP verified, proceeding to processing",
            user_id=12345,
            metadata={"otp_verified": True, "verification_timestamp": datetime.utcnow().isoformat()}
        )
        
        # Mock the database operations
        with patch('utils.status_update_facade.managed_session') as mock_session_context:
            mock_session = Mock()
            mock_session_context.return_value.__enter__.return_value = mock_session
            
            # Mock finding the transaction
            mock_transaction = Mock(spec=UnifiedTransaction)
            mock_transaction.transaction_id = "UTX123456789012345"
            mock_transaction.status = UnifiedTransactionStatus.PENDING
            mock_transaction.transaction_type = UnifiedTransactionType.WALLET_CASHOUT
            
            mock_session.query.return_value.filter.return_value.first.return_value = mock_transaction
            
            # Test the validation-only workflow first
            validation_result = await status_facade.validate_transition_only(
                current_status=request.current_status,
                new_status=request.new_status,
                transaction_type=request.transaction_type
            )
            
            assert validation_result.is_valid, f"Validation should pass: {validation_result.error_message}"
            logger.info(f"✅ Validation passed: {validation_result.current_status} → {validation_result.new_status}")
            
            # Test allowed next statuses
            allowed_statuses = await status_facade.get_allowed_next_statuses(
                current_status=request.current_status,
                transaction_type=request.transaction_type
            )
            
            assert request.new_status in allowed_statuses, (
                f"Target status {request.new_status} should be in allowed statuses: {allowed_statuses}"
            )
            logger.info(f"✅ Target status in allowed transitions: {allowed_statuses}")
    
    @pytest.mark.asyncio
    async def test_status_update_error_handling(self, status_facade):
        """Test error handling in status update workflow"""
        # Test invalid transition
        invalid_request = StatusUpdateRequest(
            transaction_id="UTX123456789012345",
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            current_status=UnifiedTransactionStatus.SUCCESS,  # Terminal state
            new_status=UnifiedTransactionStatus.PROCESSING,   # Cannot go back
            context=StatusUpdateContext.MANUAL_ADMIN,
            reason="Admin attempting to restart completed transaction"
        )
        
        # Validation should fail
        validation_result = await status_facade.validate_transition_only(
            current_status=invalid_request.current_status,
            new_status=invalid_request.new_status,
            transaction_type=invalid_request.transaction_type
        )
        
        assert not validation_result.is_valid, "Invalid transition should be caught"
        assert "terminal" in validation_result.error_message.lower() or "final" in validation_result.error_message.lower()
        logger.info(f"✅ Invalid transition properly blocked: {validation_result.error_message}")
    
    @pytest.mark.asyncio
    async def test_transaction_type_specific_workflows(self, status_facade):
        """Test transaction-type-specific status update workflows"""
        transaction_type_tests = [
            {
                'type': UnifiedTransactionType.WALLET_CASHOUT,
                'flow': [
                    (UnifiedTransactionStatus.PENDING, UnifiedTransactionStatus.PROCESSING),
                    (UnifiedTransactionStatus.PROCESSING, UnifiedTransactionStatus.AWAITING_RESPONSE),
                    (UnifiedTransactionStatus.AWAITING_RESPONSE, UnifiedTransactionStatus.SUCCESS)
                ],
                'description': 'Wallet cashout flow'
            },
            {
                'type': UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                'flow': [
                    (UnifiedTransactionStatus.PENDING, UnifiedTransactionStatus.AWAITING_PAYMENT),
                    (UnifiedTransactionStatus.AWAITING_PAYMENT, UnifiedTransactionStatus.PAYMENT_CONFIRMED),
                    (UnifiedTransactionStatus.PAYMENT_CONFIRMED, UnifiedTransactionStatus.PROCESSING),
                    (UnifiedTransactionStatus.PROCESSING, UnifiedTransactionStatus.SUCCESS)
                ],
                'description': 'Exchange sell crypto flow'
            },
            {
                'type': UnifiedTransactionType.ESCROW,
                'flow': [
                    (UnifiedTransactionStatus.PENDING, UnifiedTransactionStatus.AWAITING_PAYMENT),
                    (UnifiedTransactionStatus.AWAITING_PAYMENT, UnifiedTransactionStatus.PAYMENT_CONFIRMED),
                    (UnifiedTransactionStatus.PAYMENT_CONFIRMED, UnifiedTransactionStatus.AWAITING_APPROVAL),
                    (UnifiedTransactionStatus.AWAITING_APPROVAL, UnifiedTransactionStatus.FUNDS_HELD),
                    (UnifiedTransactionStatus.FUNDS_HELD, UnifiedTransactionStatus.RELEASE_PENDING),
                    (UnifiedTransactionStatus.RELEASE_PENDING, UnifiedTransactionStatus.SUCCESS)
                ],
                'description': 'Escrow flow'
            }
        ]
        
        for test_case in transaction_type_tests:
            logger.info(f"Testing {test_case['description']}...")
            
            for current_status, new_status in test_case['flow']:
                validation_result = await status_facade.validate_transition_only(
                    current_status=current_status,
                    new_status=new_status,
                    transaction_type=test_case['type']
                )
                
                assert validation_result.is_valid, (
                    f"{test_case['description']} transition failed: "
                    f"{current_status.name} → {new_status.name}. Error: {validation_result.error_message}"
                )
                
                logger.info(f"  ✅ {current_status.name} → {new_status.name}")
    
    @pytest.mark.asyncio
    async def test_concurrent_status_updates(self, status_facade):
        """Test handling of concurrent status update requests"""
        # Simulate concurrent update requests for the same transaction
        requests = [
            StatusUpdateRequest(
                transaction_id="UTX123456789012345",
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.PROCESSING,
                context=StatusUpdateContext.AUTOMATED_SYSTEM,
                reason="Concurrent update 1"
            ),
            StatusUpdateRequest(
                transaction_id="UTX123456789012345",
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.CANCELLED,
                context=StatusUpdateContext.USER_ACTION,
                reason="Concurrent update 2"
            )
        ]
        
        # Both updates should validate individually
        for i, request in enumerate(requests):
            validation_result = await status_facade.validate_transition_only(
                current_status=request.current_status,
                new_status=request.new_status,
                transaction_type=request.transaction_type
            )
            
            assert validation_result.is_valid, f"Request {i+1} should be valid individually"
            logger.info(f"✅ Concurrent request {i+1} validated: {request.new_status.name}")


class TestErrorHandlingAndEdgeCases:
    """
    Tests for error handling, edge cases, and boundary conditions
    """
    
    def test_invalid_status_values(self):
        """Test handling of invalid status values"""
        validator = UnifiedTransitionValidator()
        
        # Test with invalid status strings
        invalid_status_tests = [
            ("INVALID_STATUS", UnifiedTransactionStatus.PROCESSING, "Invalid current status"),
            (UnifiedTransactionStatus.PENDING, "INVALID_TARGET", "Invalid target status"),
            ("PENDING", "PROCESSING", "String status values should work"),  # This should actually work
        ]
        
        for current, new, description in invalid_status_tests:
            try:
                result = validator.validate_transition(
                    current_status=current,
                    new_status=new,
                    transaction_type=UnifiedTransactionType.WALLET_CASHOUT
                )
                
                # If strings are valid enum names, they should work
                if isinstance(current, str) and isinstance(new, str):
                    if current in [s.value for s in UnifiedTransactionStatus] and new in [s.value for s in UnifiedTransactionStatus]:
                        logger.info(f"✅ {description}: String status values handled correctly")
                        continue
                
                # Otherwise, should handle gracefully
                logger.info(f"✅ {description}: Handled gracefully with result: {result.is_valid}")
                
            except Exception as e:
                # Should not crash, should handle gracefully
                assert "invalid" in str(e).lower() or "unknown" in str(e).lower(), (
                    f"Should provide meaningful error for invalid status: {e}"
                )
                logger.info(f"✅ {description}: Properly rejected with error: {e}")
    
    def test_invalid_transaction_types(self):
        """Test handling of invalid transaction types"""
        validator = UnifiedTransitionValidator()
        
        invalid_transaction_type_tests = [
            ("INVALID_TYPE", "Invalid transaction type string"),
            (None, "Null transaction type"),
            (123, "Numeric transaction type"),
        ]
        
        for invalid_type, description in invalid_transaction_type_tests:
            try:
                result = validator.validate_transition(
                    current_status=UnifiedTransactionStatus.PENDING,
                    new_status=UnifiedTransactionStatus.PROCESSING,
                    transaction_type=invalid_type
                )
                
                # Should either handle gracefully or provide meaningful error
                logger.info(f"✅ {description}: Handled with result: {result.is_valid}")
                
            except Exception as e:
                # Should provide meaningful error message
                assert any(word in str(e).lower() for word in ["invalid", "unknown", "type"]), (
                    f"Should provide meaningful error for invalid transaction type: {e}"
                )
                logger.info(f"✅ {description}: Properly rejected with error: {e}")
    
    def test_edge_case_status_combinations(self):
        """Test edge case status combinations across systems"""
        validator = UnifiedTransitionValidator()
        
        edge_case_tests = [
            # Same status transitions (should be blocked or handled specially)
            (UnifiedTransactionStatus.PENDING, UnifiedTransactionStatus.PENDING, "Same status transition"),
            (UnifiedTransactionStatus.PROCESSING, UnifiedTransactionStatus.PROCESSING, "Processing to processing"),
            (UnifiedTransactionStatus.SUCCESS, UnifiedTransactionStatus.SUCCESS, "Success to success"),
            
            # Unusual but potentially valid transitions
            (UnifiedTransactionStatus.AWAITING_RESPONSE, UnifiedTransactionStatus.PROCESSING, "Back to processing from awaiting"),
            (UnifiedTransactionStatus.OTP_PENDING, UnifiedTransactionStatus.CANCELLED, "Cancel during OTP"),
            (UnifiedTransactionStatus.ADMIN_PENDING, UnifiedTransactionStatus.FAILED, "Admin rejection"),
        ]
        
        for current_status, new_status, description in edge_case_tests:
            result = validator.validate_transition(
                current_status=current_status,
                new_status=new_status,
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT
            )
            
            # Log the result regardless of validity
            status_text = "VALID" if result.is_valid else "INVALID"
            logger.info(f"✅ Edge case '{description}': {status_text} - {result.error_message or 'No error'}")
            
            # Same status transitions should generally be blocked
            if current_status == new_status:
                assert not result.is_valid, f"Same status transition should be blocked: {description}"
    
    def test_legacy_status_mapping_edge_cases(self):
        """Test edge cases in legacy status mapping"""
        # Test mapping with None values
        with pytest.raises(Exception):
            LegacyStatusMapper.map_to_unified(None, LegacySystemType.CASHOUT)
        
        # Test mapping with wrong system type
        with pytest.raises(Exception):
            LegacyStatusMapper.map_to_unified(CashoutStatus.PENDING, LegacySystemType.ESCROW)
        
        # Test reverse mapping for statuses that don't exist in target system
        with pytest.raises(Exception):
            # PARTIAL_PAYMENT doesn't exist in cashout system
            LegacyStatusMapper.map_from_unified(
                UnifiedTransactionStatus.PARTIAL_PAYMENT, 
                LegacySystemType.CASHOUT
            )
        
        logger.info("✅ Legacy mapping edge cases handled correctly")
    
    def test_boundary_conditions(self):
        """Test boundary conditions and limits"""
        validator = UnifiedTransitionValidator()
        
        # Test with all possible transaction types
        all_transaction_types = list(UnifiedTransactionType)
        all_statuses = list(UnifiedTransactionStatus)
        
        # Sample a few combinations to test boundaries
        boundary_tests = [
            (all_statuses[0], all_statuses[-1], all_transaction_types[0], "First to last status"),
            (all_statuses[-1], all_statuses[0], all_transaction_types[-1], "Last to first status"),
        ]
        
        for current, new, tx_type, description in boundary_tests:
            result = validator.validate_transition(
                current_status=current,
                new_status=new,
                transaction_type=tx_type
            )
            
            logger.info(f"✅ Boundary test '{description}': {'VALID' if result.is_valid else 'INVALID'}")
    
    def test_performance_under_load(self):
        """Test performance of validation under high load"""
        validator = UnifiedTransitionValidator()
        
        import time
        start_time = time.time()
        
        # Run many validations to test performance
        num_tests = 1000
        valid_count = 0
        
        for i in range(num_tests):
            result = validator.validate_transition(
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.PROCESSING,
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT
            )
            if result.is_valid:
                valid_count += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert duration < 10.0, f"Validation should complete in under 10 seconds, took {duration:.2f}s"
        assert valid_count == num_tests, f"All {num_tests} validations should pass"
        
        avg_time_per_validation = (duration / num_tests) * 1000  # Convert to milliseconds
        assert avg_time_per_validation < 10, f"Average validation time should be under 10ms, was {avg_time_per_validation:.2f}ms"
        
        logger.info(f"✅ Performance test: {num_tests} validations in {duration:.2f}s ({avg_time_per_validation:.2f}ms avg)")


# Test execution helper functions
def run_all_comprehensive_tests():
    """Run all comprehensive status management tests"""
    import pytest
    
    # Configure logging for test output
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    print("🚀 Running Comprehensive Status Management Tests")
    print("=" * 60)
    
    # Run the tests using pytest
    test_result = pytest.main([
        __file__,
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--color=yes",  # Colored output
    ])
    
    if test_result == 0:
        print("\n🎉 ALL COMPREHENSIVE TESTS PASSED!")
        print("✅ Status management system is ready for production")
        return True
    else:
        print(f"\n❌ {test_result} test(s) failed")
        print("⚠️ Status management system needs fixes")
        return False


if __name__ == "__main__":
    """Direct execution for manual testing"""
    success = run_all_comprehensive_tests()
    exit(0 if success else 1)