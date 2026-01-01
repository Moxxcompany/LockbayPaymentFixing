"""
Test suite for the simplified 5-state transaction system

Tests state mappings, transitions, validation, and integration with StateManager.
"""

import pytest
import asyncio
import logging
from decimal import Decimal
from datetime import datetime

# Import the simplified state system components
from services.core.payment_data_structures import (
    TransactionStatus, PaymentProvider, PaymentError,
    map_legacy_status, is_valid_transition, validate_state_transition,
    get_status_category, map_provider_status_to_unified,
    StateTransitionError, get_valid_transitions, is_terminal_state,
    is_error_state, is_waiting_state, is_active_processing_state,
    LEGACY_STATUS_MAPPING, VALID_STATE_TRANSITIONS
)

from services.core.state_manager import (
    StateManager, StateTransitionContext, state_manager,
    transition_to_processing, transition_to_success, 
    transition_to_failed, transition_to_awaiting
)

from services.core.payment_processor import PaymentProcessor

# Set up logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestSimplifiedStateSystem:
    """Test suite for the simplified 5-state system"""
    
    def test_basic_5_state_enum(self):
        """Test that TransactionStatus has exactly 5 states"""
        assert len(TransactionStatus) == 5
        assert TransactionStatus.PENDING in TransactionStatus
        assert TransactionStatus.PROCESSING in TransactionStatus
        assert TransactionStatus.AWAITING in TransactionStatus
        assert TransactionStatus.SUCCESS in TransactionStatus
        assert TransactionStatus.FAILED in TransactionStatus
        
        logger.info("✅ Basic 5-state enum test passed")
    
    def test_legacy_status_mappings(self):
        """Test that legacy statuses map correctly to 5-state system"""
        
        # Test UnifiedTransactionStatus mappings
        assert map_legacy_status("pending") == TransactionStatus.PENDING
        assert map_legacy_status("awaiting_payment") == TransactionStatus.AWAITING
        assert map_legacy_status("processing") == TransactionStatus.PROCESSING
        assert map_legacy_status("success") == TransactionStatus.SUCCESS
        assert map_legacy_status("failed") == TransactionStatus.FAILED
        
        # Test CashoutStatus mappings
        assert map_legacy_status("otp_pending") == TransactionStatus.AWAITING
        assert map_legacy_status("admin_pending") == TransactionStatus.AWAITING
        assert map_legacy_status("approved") == TransactionStatus.PROCESSING
        assert map_legacy_status("completed") == TransactionStatus.SUCCESS
        
        # Test EscrowStatus mappings
        assert map_legacy_status("created") == TransactionStatus.PENDING
        assert map_legacy_status("payment_pending") == TransactionStatus.AWAITING
        assert map_legacy_status("active") == TransactionStatus.PROCESSING
        
        # Test ExchangeStatus mappings
        assert map_legacy_status("awaiting_deposit") == TransactionStatus.AWAITING
        assert map_legacy_status("rate_locked") == TransactionStatus.PROCESSING
        assert map_legacy_status("address_generation_failed") == TransactionStatus.FAILED
        
        # Test unknown status defaults to PENDING
        assert map_legacy_status("unknown_status") == TransactionStatus.PENDING
        assert map_legacy_status(None) == TransactionStatus.PENDING
        assert map_legacy_status("") == TransactionStatus.PENDING
        
        logger.info("✅ Legacy status mappings test passed")
    
    def test_state_transition_validation(self):
        """Test that state transitions are validated correctly"""
        
        # Test valid transitions from PENDING
        assert is_valid_transition(TransactionStatus.PENDING, TransactionStatus.PROCESSING)
        assert is_valid_transition(TransactionStatus.PENDING, TransactionStatus.AWAITING)
        assert is_valid_transition(TransactionStatus.PENDING, TransactionStatus.SUCCESS)
        assert is_valid_transition(TransactionStatus.PENDING, TransactionStatus.FAILED)
        
        # Test valid transitions from PROCESSING
        assert is_valid_transition(TransactionStatus.PROCESSING, TransactionStatus.AWAITING)
        assert is_valid_transition(TransactionStatus.PROCESSING, TransactionStatus.SUCCESS)
        assert is_valid_transition(TransactionStatus.PROCESSING, TransactionStatus.FAILED)
        assert is_valid_transition(TransactionStatus.PROCESSING, TransactionStatus.PENDING)  # retry
        
        # Test invalid transitions from SUCCESS (terminal state)
        assert not is_valid_transition(TransactionStatus.SUCCESS, TransactionStatus.PENDING)
        assert not is_valid_transition(TransactionStatus.SUCCESS, TransactionStatus.PROCESSING)
        assert not is_valid_transition(TransactionStatus.SUCCESS, TransactionStatus.AWAITING)
        assert not is_valid_transition(TransactionStatus.SUCCESS, TransactionStatus.FAILED)
        
        # Test same state is always valid (idempotent)
        for status in TransactionStatus:
            assert is_valid_transition(status, status)
        
        logger.info("✅ State transition validation test passed")
    
    def test_state_transition_exceptions(self):
        """Test that invalid transitions raise appropriate exceptions"""
        
        with pytest.raises(StateTransitionError) as exc_info:
            validate_state_transition(TransactionStatus.SUCCESS, TransactionStatus.PENDING)
        
        assert "Invalid transition from success to pending" in str(exc_info.value)
        assert exc_info.value.from_status == TransactionStatus.SUCCESS
        assert exc_info.value.to_status == TransactionStatus.PENDING
        
        logger.info("✅ State transition exceptions test passed")
    
    def test_provider_status_mappings(self):
        """Test provider-specific status mappings"""
        
        # Test Fincra mappings
        assert map_provider_status_to_unified(PaymentProvider.FINCRA, "pending") == TransactionStatus.PENDING
        assert map_provider_status_to_unified(PaymentProvider.FINCRA, "successful") == TransactionStatus.SUCCESS
        assert map_provider_status_to_unified(PaymentProvider.FINCRA, "failed") == TransactionStatus.FAILED
        assert map_provider_status_to_unified(PaymentProvider.FINCRA, "processing") == TransactionStatus.PROCESSING
        
        # Test Kraken mappings
        assert map_provider_status_to_unified(PaymentProvider.KRAKEN, "success") == TransactionStatus.SUCCESS
        assert map_provider_status_to_unified(PaymentProvider.KRAKEN, "failure") == TransactionStatus.FAILED
        assert map_provider_status_to_unified(PaymentProvider.KRAKEN, "canceled") == TransactionStatus.FAILED
        
        # Test BlockBee mappings
        assert map_provider_status_to_unified(PaymentProvider.BLOCKBEE, "confirmed") == TransactionStatus.SUCCESS
        assert map_provider_status_to_unified(PaymentProvider.BLOCKBEE, "unconfirmed") == TransactionStatus.AWAITING
        assert map_provider_status_to_unified(PaymentProvider.BLOCKBEE, "expired") == TransactionStatus.FAILED
        
        logger.info("✅ Provider status mappings test passed")
    
    def test_state_helper_functions(self):
        """Test utility functions for state categorization"""
        
        # Test terminal state detection
        assert is_terminal_state(TransactionStatus.SUCCESS)
        assert not is_terminal_state(TransactionStatus.PENDING)
        assert not is_terminal_state(TransactionStatus.PROCESSING)
        
        # Test error state detection
        assert is_error_state(TransactionStatus.FAILED)
        assert not is_error_state(TransactionStatus.SUCCESS)
        
        # Test waiting state detection
        assert is_waiting_state(TransactionStatus.AWAITING)
        assert not is_waiting_state(TransactionStatus.PROCESSING)
        
        # Test active processing detection
        assert is_active_processing_state(TransactionStatus.PROCESSING)
        assert not is_active_processing_state(TransactionStatus.AWAITING)
        
        # Test status categories
        assert get_status_category(TransactionStatus.PENDING) == "Queued for Processing"
        assert get_status_category(TransactionStatus.PROCESSING) == "Processing"
        assert get_status_category(TransactionStatus.AWAITING) == "Waiting for Action"
        assert get_status_category(TransactionStatus.SUCCESS) == "Completed Successfully"
        assert get_status_category(TransactionStatus.FAILED) == "Failed"
        
        logger.info("✅ State helper functions test passed")
    
    def test_valid_transitions_mapping(self):
        """Test that VALID_STATE_TRANSITIONS covers all states properly"""
        
        # Ensure all states are covered
        for status in TransactionStatus:
            assert status in VALID_STATE_TRANSITIONS
        
        # Test specific transition rules
        pending_transitions = VALID_STATE_TRANSITIONS[TransactionStatus.PENDING]
        assert len(pending_transitions) == 4  # Can go to PROCESSING, AWAITING, SUCCESS, FAILED
        
        success_transitions = VALID_STATE_TRANSITIONS[TransactionStatus.SUCCESS]
        assert len(success_transitions) == 0  # Terminal state
        
        failed_transitions = VALID_STATE_TRANSITIONS[TransactionStatus.FAILED]
        assert TransactionStatus.PENDING in failed_transitions  # Can retry
        
        logger.info("✅ Valid transitions mapping test passed")
    
    def test_comprehensive_legacy_mapping_coverage(self):
        """Test that all important legacy statuses are covered"""
        
        # Key statuses that must be mapped correctly
        critical_mappings = [
            # UnifiedTransactionStatus
            ("pending", TransactionStatus.PENDING),
            ("processing", TransactionStatus.PROCESSING),
            ("success", TransactionStatus.SUCCESS),
            ("failed", TransactionStatus.FAILED),
            ("awaiting_response", TransactionStatus.AWAITING),
            
            # CashoutStatus  
            ("otp_pending", TransactionStatus.AWAITING),
            ("admin_pending", TransactionStatus.AWAITING),
            ("approved", TransactionStatus.PROCESSING),
            ("completed", TransactionStatus.SUCCESS),
            
            # EscrowStatus
            ("created", TransactionStatus.PENDING),
            ("payment_pending", TransactionStatus.AWAITING),
            ("active", TransactionStatus.PROCESSING),
            ("refunded", TransactionStatus.SUCCESS),
            
            # ExchangeStatus
            ("awaiting_deposit", TransactionStatus.AWAITING),
            ("rate_locked", TransactionStatus.PROCESSING),
            ("address_generation_failed", TransactionStatus.FAILED),
            
            # WalletHoldStatus
            ("held", TransactionStatus.PROCESSING),
            ("settled", TransactionStatus.SUCCESS),
            ("failed_held", TransactionStatus.FAILED),
        ]
        
        for legacy_status, expected_status in critical_mappings:
            assert map_legacy_status(legacy_status) == expected_status, \
                f"Legacy status '{legacy_status}' should map to {expected_status.value}"
        
        logger.info("✅ Comprehensive legacy mapping coverage test passed")


async def test_state_manager_integration():
    """Test StateManager integration (async test)"""
    
    # Test StateTransitionContext creation
    context = StateTransitionContext(
        transaction_id="UTX123456789",
        transaction_type="test_cashout",
        user_id=12345,
        reason="Testing state transition",
        metadata={"test": "data"},
        provider=PaymentProvider.FINCRA
    )
    
    assert context.transaction_id == "UTX123456789"
    assert context.transaction_type == "test_cashout"
    assert context.user_id == 12345
    assert context.provider == PaymentProvider.FINCRA
    assert isinstance(context.timestamp, datetime)
    
    logger.info("✅ StateTransitionContext creation test passed")
    
    # Note: Full StateManager testing would require database setup
    # This is a basic structure test
    sm = StateManager()
    assert sm is not None
    assert hasattr(sm, 'transition_state')
    assert hasattr(sm, 'get_transaction_status')
    
    logger.info("✅ StateManager integration test passed")


async def test_convenience_functions():
    """Test convenience functions for common state transitions"""
    
    # These functions should exist and be callable
    functions_to_test = [
        transition_to_processing,
        transition_to_success,
        transition_to_failed,
        transition_to_awaiting
    ]
    
    for func in functions_to_test:
        assert callable(func), f"Function {func.__name__} should be callable"
        
        # Test function signature (should not raise)
        import inspect
        sig = inspect.signature(func)
        required_params = ['transaction_id', 'transaction_type', 'user_id']
        for param in required_params:
            assert param in sig.parameters, f"Function {func.__name__} missing required parameter: {param}"
    
    logger.info("✅ Convenience functions test passed")


def run_all_tests():
    """Run all tests and report results"""
    logger.info("🧪 Starting Simplified State System Test Suite")
    logger.info("=" * 60)
    
    test_suite = TestSimplifiedStateSystem()
    
    # Run synchronous tests
    sync_tests = [
        test_suite.test_basic_5_state_enum,
        test_suite.test_legacy_status_mappings,
        test_suite.test_state_transition_validation,
        test_suite.test_state_transition_exceptions,
        test_suite.test_provider_status_mappings,
        test_suite.test_state_helper_functions,
        test_suite.test_valid_transitions_mapping,
        test_suite.test_comprehensive_legacy_mapping_coverage
    ]
    
    failed_tests = []
    
    for test in sync_tests:
        try:
            test()
        except Exception as e:
            logger.error(f"❌ Test {test.__name__} failed: {e}")
            failed_tests.append(test.__name__)
    
    # Run async tests
    async_tests = [
        test_state_manager_integration,
        test_convenience_functions
    ]
    
    for test in async_tests:
        try:
            asyncio.run(test())
        except Exception as e:
            logger.error(f"❌ Async test {test.__name__} failed: {e}")
            failed_tests.append(test.__name__)
    
    logger.info("=" * 60)
    if failed_tests:
        logger.error(f"❌ {len(failed_tests)} tests failed: {', '.join(failed_tests)}")
        return False
    else:
        logger.info("✅ All tests passed! Simplified 5-state system is working correctly.")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)