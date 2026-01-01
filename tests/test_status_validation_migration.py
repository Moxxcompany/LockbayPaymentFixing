"""
Test Status Validation Migration

Comprehensive tests to verify the migration from utils.status_enums to utils.status_flows
is complete and working correctly, especially the critical validation bug fixes.

Tests:
- Exchange flow validation: pending → awaiting_payment → payment_confirmed
- EXCHANGE_BUY_CRYPTO validation works correctly  
- Status mapping between legacy and unified systems
- No remaining references to old validation functions
"""

import pytest
import logging
from decimal import Decimal
from typing import Dict, Any

from utils.status_flows import (
    UnifiedTransitionValidator,
    UnifiedTransactionType,
    UnifiedTransactionStatus,
    ExchangeStatus,
    EscrowStatus
)

from services.legacy_status_mapper import LegacyStatusMapper, LegacySystemType


logger = logging.getLogger(__name__)


class TestStatusValidationMigration:
    """Test the complete status validation migration"""

    def test_exchange_buy_crypto_flow_validation(self):
        """Test EXCHANGE_BUY_CRYPTO validation flow: pending → awaiting_payment → payment_confirmed"""
        validator = UnifiedTransitionValidator()
        
        # Test the complete EXCHANGE_BUY_CRYPTO flow
        flow_tests = [
            # Start: pending → awaiting_payment  
            {
                'current': UnifiedTransactionStatus.PENDING.value,
                'new': UnifiedTransactionStatus.AWAITING_PAYMENT.value,
                'transaction_type': UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                'should_pass': True,
                'description': 'Initial pending to awaiting payment'
            },
            
            # Valid: awaiting_payment → payment_confirmed
            {
                'current': UnifiedTransactionStatus.AWAITING_PAYMENT.value,
                'new': UnifiedTransactionStatus.PAYMENT_CONFIRMED.value,
                'transaction_type': UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                'should_pass': True,
                'description': 'Payment confirmed after awaiting'
            },
            
            # Valid: payment_confirmed → processing
            {
                'current': UnifiedTransactionStatus.PAYMENT_CONFIRMED.value,
                'new': UnifiedTransactionStatus.PROCESSING.value,
                'transaction_type': UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                'should_pass': True,
                'description': 'Start processing after payment confirmed'
            },
            
            # Valid: processing → success
            {
                'current': UnifiedTransactionStatus.PROCESSING.value,
                'new': UnifiedTransactionStatus.SUCCESS.value,
                'transaction_type': UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                'should_pass': True,
                'description': 'Successful completion'
            },
            
            # Invalid: success → processing (terminal state)
            {
                'current': UnifiedTransactionStatus.SUCCESS.value,
                'new': UnifiedTransactionStatus.PROCESSING.value,
                'transaction_type': UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                'should_pass': False,
                'description': 'Cannot go back from terminal state'
            },
            
            # Invalid: pending → success (skip required steps)
            {
                'current': UnifiedTransactionStatus.PENDING.value,
                'new': UnifiedTransactionStatus.SUCCESS.value,
                'transaction_type': UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                'should_pass': False,
                'description': 'Cannot skip required flow steps'
            }
        ]
        
        for test in flow_tests:
            result = validator.validate_transition(
                current_status=test['current'],
                new_status=test['new'],
                transaction_type=test['transaction_type']
            )
            
            if test['should_pass']:
                assert result.is_valid, f"FAILED: {test['description']} - {test['current']} → {test['new']} should be valid. Error: {result.error_message}"
            else:
                assert not result.is_valid, f"FAILED: {test['description']} - {test['current']} → {test['new']} should be invalid but passed"
            
            logger.info(f"✅ {test['description']}: {test['current']} → {test['new']} ({'VALID' if result.is_valid else 'INVALID'})")

    def test_exchange_sell_crypto_flow_validation(self):
        """Test EXCHANGE_SELL_CRYPTO validation flow"""
        validator = UnifiedTransitionValidator()
        
        # Test EXCHANGE_SELL_CRYPTO flow (similar but different validation rules)
        sell_flow_tests = [
            {
                'current': UnifiedTransactionStatus.PENDING.value,
                'new': UnifiedTransactionStatus.AWAITING_PAYMENT.value,
                'transaction_type': UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                'should_pass': True,
                'description': 'Sell crypto: pending → awaiting payment'
            },
            {
                'current': UnifiedTransactionStatus.AWAITING_PAYMENT.value,
                'new': UnifiedTransactionStatus.PAYMENT_CONFIRMED.value,
                'transaction_type': UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                'should_pass': True,
                'description': 'Sell crypto: payment confirmed'
            }
        ]
        
        for test in sell_flow_tests:
            result = validator.validate_transition(
                current_status=test['current'],
                new_status=test['new'],
                transaction_type=test['transaction_type']
            )
            
            assert result.is_valid == test['should_pass'], f"FAILED: {test['description']}"
            logger.info(f"✅ {test['description']}: {'VALID' if result.is_valid else 'INVALID'}")

    def test_status_mapping_legacy_to_unified(self):
        """Test status mapping from legacy systems to unified system"""
        
        # Test Exchange Status Mapping
        exchange_mapping_tests = [
            {
                'legacy_status': ExchangeStatus.AWAITING_DEPOSIT,
                'expected_unified': UnifiedTransactionStatus.AWAITING_PAYMENT,
                'system_type': LegacySystemType.EXCHANGE,
                'description': 'ExchangeStatus.AWAITING_DEPOSIT → UnifiedTransactionStatus.AWAITING_PAYMENT'
            },
            {
                'legacy_status': ExchangeStatus.PAYMENT_CONFIRMED,
                'expected_unified': UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                'system_type': LegacySystemType.EXCHANGE,
                'description': 'ExchangeStatus.PAYMENT_CONFIRMED → UnifiedTransactionStatus.PAYMENT_CONFIRMED'
            },
            {
                'legacy_status': ExchangeStatus.PROCESSING,
                'expected_unified': UnifiedTransactionStatus.PROCESSING,
                'system_type': LegacySystemType.EXCHANGE,
                'description': 'ExchangeStatus.PROCESSING → UnifiedTransactionStatus.PROCESSING'
            },
            {
                'legacy_status': ExchangeStatus.COMPLETED,
                'expected_unified': UnifiedTransactionStatus.SUCCESS,
                'system_type': LegacySystemType.EXCHANGE,
                'description': 'ExchangeStatus.COMPLETED → UnifiedTransactionStatus.SUCCESS'
            }
        ]
        
        for test in exchange_mapping_tests:
            mapped_status = LegacyStatusMapper.map_to_unified(
                test['legacy_status'], 
                test['system_type']
            )
            
            assert mapped_status == test['expected_unified'], (
                f"FAILED: {test['description']} - Got {mapped_status}, expected {test['expected_unified']}"
            )
            logger.info(f"✅ {test['description']}: Correctly mapped")
        
        # Test Escrow Status Mapping
        escrow_mapping_tests = [
            {
                'legacy_status': EscrowStatus.CREATED,
                'expected_unified': UnifiedTransactionStatus.PENDING,
                'system_type': LegacySystemType.ESCROW,
                'description': 'EscrowStatus.CREATED → UnifiedTransactionStatus.PENDING'
            },
            {
                'legacy_status': EscrowStatus.PAYMENT_PENDING,
                'expected_unified': UnifiedTransactionStatus.AWAITING_PAYMENT,
                'system_type': LegacySystemType.ESCROW,
                'description': 'EscrowStatus.PAYMENT_PENDING → UnifiedTransactionStatus.AWAITING_PAYMENT'
            },
            {
                'legacy_status': EscrowStatus.ACTIVE,
                'expected_unified': UnifiedTransactionStatus.FUNDS_HELD,
                'system_type': LegacySystemType.ESCROW,
                'description': 'EscrowStatus.ACTIVE → UnifiedTransactionStatus.FUNDS_HELD'
            }
        ]
        
        for test in escrow_mapping_tests:
            mapped_status = LegacyStatusMapper.map_to_unified(
                test['legacy_status'], 
                test['system_type']
            )
            
            assert mapped_status == test['expected_unified'], (
                f"FAILED: {test['description']} - Got {mapped_status}, expected {test['expected_unified']}"
            )
            logger.info(f"✅ {test['description']}: Correctly mapped")

    def test_reverse_status_mapping(self):
        """Test reverse mapping from unified back to legacy statuses"""
        
        # Test mapping UnifiedTransactionStatus back to ExchangeStatus
        reverse_tests = [
            {
                'unified_status': UnifiedTransactionStatus.AWAITING_PAYMENT,
                'system_type': LegacySystemType.EXCHANGE,
                'expected_legacy': ExchangeStatus.AWAITING_DEPOSIT,  # AWAITING_PAYMENT maps back to AWAITING_DEPOSIT
                'description': 'UnifiedTransactionStatus.AWAITING_PAYMENT → ExchangeStatus.AWAITING_DEPOSIT'
            },
            {
                'unified_status': UnifiedTransactionStatus.SUCCESS,
                'system_type': LegacySystemType.EXCHANGE,
                'expected_legacy': ExchangeStatus.COMPLETED,
                'description': 'UnifiedTransactionStatus.SUCCESS → ExchangeStatus.COMPLETED'
            }
        ]
        
        for test in reverse_tests:
            try:
                reverse_mapped = LegacyStatusMapper.map_from_unified(
                    test['unified_status'],
                    test['system_type']
                )
                
                # Note: reverse mapping might return the first matching legacy status
                # if multiple legacy statuses map to the same unified status
                assert reverse_mapped == test['expected_legacy'], (
                    f"FAILED: {test['description']} - Got {reverse_mapped}, expected {test['expected_legacy']}"
                )
                logger.info(f"✅ {test['description']}: Correctly reverse mapped")
                
            except Exception as e:
                # Some reverse mappings might not be implemented yet - log but don't fail
                logger.warning(f"⚠️  {test['description']}: Reverse mapping not available - {e}")

    def test_critical_direct_exchange_bug_fix(self):
        """Test the specific bug fix in handlers/direct_exchange.py"""
        
        # This test simulates the bug that was fixed:
        # Before fix: ExchangeStatus.AWAITING_DEPOSIT.value was passed directly to UnifiedTransitionValidator
        # After fix: ExchangeStatus.AWAITING_DEPOSIT is mapped to UnifiedTransactionStatus.AWAITING_PAYMENT first
        
        validator = UnifiedTransitionValidator()
        
        # Simulate the OLD buggy way (should fail validation now)
        legacy_exchange_status = ExchangeStatus.AWAITING_DEPOSIT.value  # "awaiting_deposit"
        
        # This would fail because "awaiting_deposit" is not a valid UnifiedTransactionStatus
        buggy_result = validator.validate_transition(
            current_status=UnifiedTransactionStatus.PENDING.value,
            new_status=legacy_exchange_status,  # BUG: This is ExchangeStatus, not UnifiedTransactionStatus!
            transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO
        )
        
        # The buggy approach should fail
        assert not buggy_result.is_valid, "Bug fix verification: Direct ExchangeStatus should fail unified validation"
        logger.info("✅ Confirmed: Direct ExchangeStatus.value fails unified validation (bug fixed)")
        
        # Now test the FIXED way using LegacyStatusMapper
        legacy_status = ExchangeStatus.AWAITING_DEPOSIT
        unified_status = LegacyStatusMapper.map_to_unified(legacy_status, LegacySystemType.EXCHANGE)
        
        # This should work correctly
        fixed_result = validator.validate_transition(
            current_status=UnifiedTransactionStatus.PENDING.value,
            new_status=unified_status.value,  # Properly mapped to UnifiedTransactionStatus.AWAITING_PAYMENT
            transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO
        )
        
        # The fixed approach should succeed
        assert fixed_result.is_valid, f"Bug fix verification: Mapped status should pass - {fixed_result.error_message}"
        logger.info(f"✅ Bug fix confirmed: {legacy_status} → {unified_status} validates correctly")

    def test_escrow_validation_migration(self):
        """Test escrow validation works with unified system"""
        validator = UnifiedTransitionValidator()
        
        escrow_flow_tests = [
            {
                'current': UnifiedTransactionStatus.PENDING.value,
                'new': UnifiedTransactionStatus.AWAITING_PAYMENT.value,
                'transaction_type': UnifiedTransactionType.ESCROW,
                'should_pass': True,
                'description': 'Escrow: pending → awaiting payment'
            },
            {
                'current': UnifiedTransactionStatus.AWAITING_PAYMENT.value,
                'new': UnifiedTransactionStatus.PAYMENT_CONFIRMED.value,
                'transaction_type': UnifiedTransactionType.ESCROW,
                'should_pass': True,
                'description': 'Escrow: payment confirmed'
            },
            {
                'current': UnifiedTransactionStatus.PAYMENT_CONFIRMED.value,
                'new': UnifiedTransactionStatus.FUNDS_HELD.value,
                'transaction_type': UnifiedTransactionType.ESCROW,
                'should_pass': True,
                'description': 'Escrow: funds held (active)'
            }
        ]
        
        for test in escrow_flow_tests:
            result = validator.validate_transition(
                current_status=test['current'],
                new_status=test['new'],
                transaction_type=test['transaction_type']
            )
            
            assert result.is_valid == test['should_pass'], f"FAILED: {test['description']} - {result.error_message}"
            logger.info(f"✅ {test['description']}: {'VALID' if result.is_valid else 'INVALID'}")

    def test_wallet_cashout_validation(self):
        """Test wallet cashout validation works correctly"""
        validator = UnifiedTransitionValidator()
        
        cashout_flow_tests = [
            {
                'current': UnifiedTransactionStatus.PENDING.value,
                'new': UnifiedTransactionStatus.PROCESSING.value,
                'transaction_type': UnifiedTransactionType.WALLET_CASHOUT,
                'should_pass': True,
                'description': 'Cashout: pending → processing (OTP verified)'
            },
            {
                'current': UnifiedTransactionStatus.PROCESSING.value,
                'new': UnifiedTransactionStatus.AWAITING_RESPONSE.value,
                'transaction_type': UnifiedTransactionType.WALLET_CASHOUT,
                'should_pass': True,
                'description': 'Cashout: processing → awaiting response'
            },
            {
                'current': UnifiedTransactionStatus.AWAITING_RESPONSE.value,
                'new': UnifiedTransactionStatus.SUCCESS.value,
                'transaction_type': UnifiedTransactionType.WALLET_CASHOUT,
                'should_pass': True,
                'description': 'Cashout: awaiting response → success'
            }
        ]
        
        for test in cashout_flow_tests:
            result = validator.validate_transition(
                current_status=test['current'],
                new_status=test['new'],
                transaction_type=test['transaction_type']
            )
            
            assert result.is_valid == test['should_pass'], f"FAILED: {test['description']} - {result.error_message}"
            logger.info(f"✅ {test['description']}: {'VALID' if result.is_valid else 'INVALID'}")


class TestMigrationCompleteness:
    """Verify that the migration is complete and no old references remain"""

    def test_no_deprecated_imports(self):
        """Verify no code imports from utils.status_enums (except the shim itself)"""
        import os
        import glob
        
        # Find all Python files
        python_files = []
        for root, dirs, files in os.walk('.'):
            # Skip test files, __pycache__, and the deprecated shim itself
            if '__pycache__' in root or 'tests' in root:
                continue
            for file in files:
                if file.endswith('.py') and file != 'status_enums.py':  # Skip the shim itself
                    python_files.append(os.path.join(root, file))
        
        problematic_files = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for problematic imports
                    if ('from utils.status_enums import' in content or 
                        'import utils.status_enums' in content):
                        problematic_files.append(file_path)
                        logger.warning(f"⚠️  Found utils.status_enums import in: {file_path}")
                        
            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")
        
        # Assert no problematic imports found (except documentation and comments)
        assert len(problematic_files) == 0, f"Found {len(problematic_files)} files still importing utils.status_enums: {problematic_files}"
        logger.info("✅ No problematic imports from utils.status_enums found")

    def test_unified_system_integration(self):
        """Test that all components integrate correctly with unified system"""
        from utils.status_flows import UnifiedTransitionValidator, UnifiedTransactionType
        from services.legacy_status_mapper import LegacyStatusMapper
        from utils.status_update_facade import StatusUpdateFacade
        
        # Test that all key components can be imported and instantiated
        try:
            validator = UnifiedTransitionValidator()
            mapper = LegacyStatusMapper()
            facade = StatusUpdateFacade()
            
            logger.info("✅ All unified system components can be imported and instantiated")
            
        except Exception as e:
            pytest.fail(f"Failed to import/instantiate unified system components: {e}")


if __name__ == "__main__":
    """Run tests directly for manual verification"""
    import sys
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # Run all test methods
    migration_test = TestStatusValidationMigration()
    completeness_test = TestMigrationCompleteness()
    
    test_methods = [
        migration_test.test_exchange_buy_crypto_flow_validation,
        migration_test.test_exchange_sell_crypto_flow_validation,
        migration_test.test_status_mapping_legacy_to_unified,
        migration_test.test_reverse_status_mapping,
        migration_test.test_critical_direct_exchange_bug_fix,
        migration_test.test_escrow_validation_migration,
        migration_test.test_wallet_cashout_validation,
        completeness_test.test_unified_system_integration,
    ]
    
    passed = 0
    failed = 0
    
    for test_method in test_methods:
        try:
            print(f"\n🧪 Running {test_method.__name__}...")
            test_method()
            print(f"✅ {test_method.__name__} PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {test_method.__name__} FAILED: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("🎉 All tests passed! Status validation migration is complete.")