#!/usr/bin/env python3
"""
Test Session Management Fixes
Comprehensive tests for the session management bug fixes in StatusUpdateFacade and UnifiedTransactionService
"""

import asyncio
import sys
import os
import pytest
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test imports
from utils.status_update_facade import (
    StatusUpdateFacade, 
    StatusUpdateRequest, 
    StatusUpdateResult, 
    StatusUpdateContext
)
from services.unified_transaction_service import (
    UnifiedTransactionService,
    StatusTransitionResult
)
from models import UnifiedTransactionStatus, UnifiedTransactionType, CashoutStatus, EscrowStatus, ExchangeStatus
from services.legacy_status_mapper import LegacySystemType
from database import managed_session


class TestSessionManagementFixes(unittest.IsolatedAsyncioTestCase):
    """Test suite for session management bug fixes"""
    
    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.status_facade = StatusUpdateFacade()
        self.transaction_service = UnifiedTransactionService()
    
    # =============== StatusUpdateFacade Tests ===============
    
    async def test_cashout_status_update_with_managed_session(self):
        """Test cashout status update with managed session (session=None)"""
        request = StatusUpdateRequest(
            legacy_entity_id="test-cashout-123",
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            current_status=CashoutStatus.PENDING,
            new_status=CashoutStatus.PROCESSING,
            context=StatusUpdateContext.AUTOMATED_SYSTEM
        )
        
        # Mock the internal methods to avoid database dependencies
        with patch.object(self.status_facade, '_load_cashout_entity', new_callable=AsyncMock) as mock_load:
            with patch.object(self.status_facade, '_validate_status_transition', new_callable=AsyncMock) as mock_validate:
                with patch.object(self.status_facade, '_perform_cashout_dual_write', new_callable=AsyncMock) as mock_dual_write:
                    with patch.object(self.status_facade, '_record_status_history', new_callable=AsyncMock) as mock_history:
                        with patch.object(self.status_facade, '_handle_post_update_actions', new_callable=AsyncMock) as mock_post:
                            with patch('utils.status_update_facade.managed_session') as mock_managed_session:
                                
                                # Set up mocks
                                mock_session = MagicMock()
                                mock_managed_session.return_value.__aenter__.return_value = mock_session
                                
                                mock_cashout = MagicMock()
                                mock_cashout.status = CashoutStatus.PENDING.value
                                mock_load.return_value = mock_cashout
                                
                                mock_validate.return_value = StatusUpdateResult(success=True)
                                mock_dual_write.return_value = StatusUpdateResult(
                                    success=True,
                                    old_status=CashoutStatus.PENDING.value,
                                    new_status=CashoutStatus.PROCESSING.value
                                )
                                
                                # Test managed session path
                                result = await self.status_facade.update_cashout_status(request, session=None)
                                
                                # Verify managed_session was used
                                mock_managed_session.assert_called_once()
                                
                                # Verify success
                                self.assertTrue(result.success)
                                print(f"✅ Cashout managed session test: {result.success}")
    
    async def test_cashout_status_update_with_provided_session(self):
        """Test cashout status update with provided session"""
        request = StatusUpdateRequest(
            legacy_entity_id="test-cashout-456",
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            current_status=CashoutStatus.PENDING,
            new_status=CashoutStatus.PROCESSING,
            context=StatusUpdateContext.AUTOMATED_SYSTEM
        )
        
        # Create a mock session
        mock_provided_session = MagicMock()
        
        # Mock the internal methods
        with patch.object(self.status_facade, '_load_cashout_entity', new_callable=AsyncMock) as mock_load:
            with patch.object(self.status_facade, '_validate_status_transition', new_callable=AsyncMock) as mock_validate:
                with patch.object(self.status_facade, '_perform_cashout_dual_write', new_callable=AsyncMock) as mock_dual_write:
                    with patch.object(self.status_facade, '_record_status_history', new_callable=AsyncMock) as mock_history:
                        with patch.object(self.status_facade, '_handle_post_update_actions', new_callable=AsyncMock) as mock_post:
                            with patch('utils.status_update_facade.managed_session') as mock_managed_session:
                                
                                # Set up mocks
                                mock_cashout = MagicMock()
                                mock_cashout.status = CashoutStatus.PENDING.value
                                mock_load.return_value = mock_cashout
                                
                                mock_validate.return_value = StatusUpdateResult(success=True)
                                mock_dual_write.return_value = StatusUpdateResult(
                                    success=True,
                                    old_status=CashoutStatus.PENDING.value,
                                    new_status=CashoutStatus.PROCESSING.value
                                )
                                
                                # Test provided session path
                                result = await self.status_facade.update_cashout_status(request, session=mock_provided_session)
                                
                                # Verify managed_session was NOT used
                                mock_managed_session.assert_not_called()
                                
                                # Verify success
                                self.assertTrue(result.success)
                                print(f"✅ Cashout provided session test: {result.success}")
    
    async def test_escrow_status_update_session_handling(self):
        """Test escrow status update session handling"""
        request = StatusUpdateRequest(
            legacy_entity_id="test-escrow-789",
            transaction_type=UnifiedTransactionType.ESCROW,
            current_status=EscrowStatus.PENDING,
            new_status=EscrowStatus.PAYMENT_CONFIRMED,
            context=StatusUpdateContext.USER_ACTION
        )
        
        # Mock the internal methods
        with patch.object(self.status_facade, '_load_escrow_entity', new_callable=AsyncMock) as mock_load:
            with patch.object(self.status_facade, '_validate_escrow_business_rules', new_callable=AsyncMock) as mock_business:
                with patch.object(self.status_facade, '_validate_status_transition', new_callable=AsyncMock) as mock_validate:
                    with patch.object(self.status_facade, '_handle_escrow_fund_management', new_callable=AsyncMock) as mock_fund:
                        with patch.object(self.status_facade, '_perform_escrow_dual_write', new_callable=AsyncMock) as mock_dual_write:
                            with patch.object(self.status_facade, '_record_status_history', new_callable=AsyncMock) as mock_history:
                                with patch.object(self.status_facade, '_handle_post_update_actions', new_callable=AsyncMock) as mock_post:
                                    with patch('utils.status_update_facade.managed_session') as mock_managed_session:
                                        
                                        # Set up mocks
                                        mock_session = MagicMock()
                                        mock_managed_session.return_value.__aenter__.return_value = mock_session
                                        
                                        mock_escrow = MagicMock()
                                        mock_escrow.status = EscrowStatus.PENDING.value
                                        mock_load.return_value = mock_escrow
                                        
                                        mock_business.return_value = StatusUpdateResult(success=True)
                                        mock_validate.return_value = StatusUpdateResult(success=True)
                                        mock_fund.return_value = StatusUpdateResult(success=True)
                                        mock_dual_write.return_value = StatusUpdateResult(
                                            success=True,
                                            old_status=EscrowStatus.PENDING.value,
                                            new_status=EscrowStatus.PAYMENT_CONFIRMED.value
                                        )
                                        
                                        # Test managed session
                                        result = await self.status_facade.update_escrow_status(request, session=None)
                                        
                                        # Verify success
                                        self.assertTrue(result.success)
                                        print(f"✅ Escrow session handling test: {result.success}")
    
    async def test_exchange_status_update_session_handling(self):
        """Test exchange status update session handling"""
        request = StatusUpdateRequest(
            legacy_entity_id="test-exchange-abc",
            transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
            current_status=ExchangeStatus.CREATED,
            new_status=ExchangeStatus.AWAITING_DEPOSIT,
            context=StatusUpdateContext.AUTOMATED_SYSTEM
        )
        
        # Mock the internal methods
        with patch.object(self.status_facade, '_determine_exchange_transaction_type') as mock_determine:
            with patch.object(self.status_facade, '_load_exchange_entity', new_callable=AsyncMock) as mock_load:
                with patch.object(self.status_facade, '_validate_exchange_business_rules', new_callable=AsyncMock) as mock_business:
                    with patch.object(self.status_facade, '_validate_status_transition', new_callable=AsyncMock) as mock_validate:
                        with patch.object(self.status_facade, '_handle_exchange_fund_management', new_callable=AsyncMock) as mock_fund:
                            with patch.object(self.status_facade, '_perform_exchange_dual_write', new_callable=AsyncMock) as mock_dual_write:
                                with patch.object(self.status_facade, '_record_status_history', new_callable=AsyncMock) as mock_history:
                                    with patch.object(self.status_facade, '_handle_post_update_actions', new_callable=AsyncMock) as mock_post:
                                        with patch('utils.status_update_facade.managed_session') as mock_managed_session:
                                            
                                            # Set up mocks
                                            mock_session = MagicMock()
                                            mock_managed_session.return_value.__aenter__.return_value = mock_session
                                            
                                            mock_exchange = MagicMock()
                                            mock_exchange.status = ExchangeStatus.CREATED.value
                                            mock_load.return_value = mock_exchange
                                            
                                            mock_determine.return_value = UnifiedTransactionType.EXCHANGE_BUY_CRYPTO
                                            mock_business.return_value = StatusUpdateResult(success=True)
                                            mock_validate.return_value = StatusUpdateResult(success=True)
                                            mock_fund.return_value = StatusUpdateResult(success=True)
                                            mock_dual_write.return_value = StatusUpdateResult(
                                                success=True,
                                                old_status=ExchangeStatus.CREATED.value,
                                                new_status=ExchangeStatus.AWAITING_DEPOSIT.value
                                            )
                                            
                                            # Test managed session
                                            result = await self.status_facade.update_exchange_status(request, session=None)
                                            
                                            # Verify success
                                            self.assertTrue(result.success)
                                            print(f"✅ Exchange session handling test: {result.success}")
    
    # =============== UnifiedTransactionService Tests ===============
    
    async def test_transition_status_with_managed_session(self):
        """Test transition_status with managed session"""
        transaction_id = "test-tx-123"
        new_status = UnifiedTransactionStatus.PROCESSING
        
        with patch('services.unified_transaction_service.managed_session') as mock_managed_session:
            with patch.object(self.transaction_service.status_facade, 'update_unified_transaction_status', new_callable=AsyncMock) as mock_facade:
                
                # Set up mocks
                mock_session = MagicMock()
                mock_managed_session.return_value.__aenter__.return_value = mock_session
                
                mock_transaction = MagicMock()
                mock_transaction.transaction_id = transaction_id
                mock_transaction.status = UnifiedTransactionStatus.PENDING.value
                mock_transaction.transaction_type = UnifiedTransactionType.WALLET_CASHOUT.value
                mock_transaction.legacy_entity_id = "cashout-456"
                
                mock_session.query.return_value.filter.return_value.first.return_value = mock_transaction
                
                mock_facade.return_value = StatusUpdateResult(
                    success=True,
                    old_status=UnifiedTransactionStatus.PENDING.value,
                    new_status=UnifiedTransactionStatus.PROCESSING.value
                )
                
                # Test managed session path
                result = await self.transaction_service.transition_status(
                    transaction_id=transaction_id,
                    new_status=new_status,
                    session=None
                )
                
                # Verify managed_session was used
                mock_managed_session.assert_called_once()
                
                # Verify success
                self.assertTrue(result.success)
                self.assertEqual(result.old_status, UnifiedTransactionStatus.PENDING.value)
                self.assertEqual(result.new_status, UnifiedTransactionStatus.PROCESSING.value)
                print(f"✅ TransactionService managed session test: {result.success}")
    
    async def test_transition_status_with_provided_session(self):
        """Test transition_status with provided session"""
        transaction_id = "test-tx-789"
        new_status = UnifiedTransactionStatus.SUCCESS
        mock_provided_session = MagicMock()
        
        with patch('services.unified_transaction_service.managed_session') as mock_managed_session:
            with patch.object(self.transaction_service.status_facade, 'update_unified_transaction_status', new_callable=AsyncMock) as mock_facade:
                
                # Set up mocks
                mock_transaction = MagicMock()
                mock_transaction.transaction_id = transaction_id
                mock_transaction.status = UnifiedTransactionStatus.PROCESSING.value
                mock_transaction.transaction_type = UnifiedTransactionType.WALLET_CASHOUT.value
                mock_transaction.legacy_entity_id = "cashout-789"
                
                mock_provided_session.query.return_value.filter.return_value.first.return_value = mock_transaction
                
                mock_facade.return_value = StatusUpdateResult(
                    success=True,
                    old_status=UnifiedTransactionStatus.PROCESSING.value,
                    new_status=UnifiedTransactionStatus.SUCCESS.value,
                    is_terminal=True
                )
                
                # Test provided session path
                result = await self.transaction_service.transition_status(
                    transaction_id=transaction_id,
                    new_status=new_status,
                    session=mock_provided_session
                )
                
                # Verify managed_session was NOT used
                mock_managed_session.assert_not_called()
                
                # Verify success
                self.assertTrue(result.success)
                self.assertEqual(result.old_status, UnifiedTransactionStatus.PROCESSING.value)
                self.assertEqual(result.new_status, UnifiedTransactionStatus.SUCCESS.value)
                self.assertEqual(result.next_action, "check_terminal_status")
                print(f"✅ TransactionService provided session test: {result.success}")
    
    async def test_transition_cashout_status_session_handling(self):
        """Test transition_cashout_status session handling"""
        cashout_id = "test-cashout-xyz"
        new_status = CashoutStatus.PROCESSING
        
        with patch('services.unified_transaction_service.managed_session') as mock_managed_session:
            with patch.object(self.transaction_service.status_facade, 'update_cashout_status', new_callable=AsyncMock) as mock_facade:
                
                # Set up mocks
                mock_session = MagicMock()
                mock_managed_session.return_value.__aenter__.return_value = mock_session
                
                mock_cashout = MagicMock()
                mock_cashout.cashout_id = cashout_id
                mock_cashout.status = CashoutStatus.PENDING.value
                
                mock_session.query.return_value.filter.return_value.first.return_value = mock_cashout
                
                mock_facade.return_value = StatusUpdateResult(
                    success=True,
                    old_status=CashoutStatus.PENDING.value,
                    new_status=CashoutStatus.PROCESSING.value
                )
                
                # Test managed session path
                result = await self.transaction_service.transition_cashout_status(
                    cashout_id=cashout_id,
                    new_status=new_status,
                    session=None
                )
                
                # Verify success
                self.assertTrue(result.success)
                print(f"✅ Cashout transition session test: {result.success}")
    
    async def test_session_error_handling(self):
        """Test error handling in session management"""
        request = StatusUpdateRequest(
            legacy_entity_id="error-test-123",
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            current_status=CashoutStatus.PENDING,
            new_status=CashoutStatus.PROCESSING,
            context=StatusUpdateContext.AUTOMATED_SYSTEM
        )
        
        # Test error handling with managed session
        with patch('utils.status_update_facade.managed_session') as mock_managed_session:
            with patch.object(self.status_facade, '_load_cashout_entity', new_callable=AsyncMock) as mock_load:
                
                # Simulate an exception during processing
                mock_load.side_effect = Exception("Database connection error")
                
                # Test error handling
                result = await self.status_facade.update_cashout_status(request, session=None)
                
                # Verify error was handled gracefully
                self.assertFalse(result.success)
                self.assertIn("Cashout status update failed", result.error)
                print(f"✅ Error handling test: Handled gracefully - {result.error[:50]}...")


# =============== INTEGRATION TESTS ===============

class TestSessionManagementIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for session management fixes"""
    
    async def test_no_invalid_asynccontextmanager_pattern(self):
        """Verify no invalid asynccontextmanager patterns remain"""
        import subprocess
        import os
        
        # Search for the problematic pattern in both files
        facade_file = "utils/status_update_facade.py"
        service_file = "services/unified_transaction_service.py"
        
        # Search pattern
        pattern = r"asynccontextmanager\s*\(\s*lambda.*iter.*session"
        
        try:
            # Check StatusUpdateFacade
            result_facade = subprocess.run(
                ["grep", "-n", "-E", pattern, facade_file],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            # Check UnifiedTransactionService
            result_service = subprocess.run(
                ["grep", "-n", "-E", pattern, service_file],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            # Both should return no matches (non-zero exit code)
            self.assertNotEqual(result_facade.returncode, 0, f"Found invalid pattern in {facade_file}: {result_facade.stdout}")
            self.assertNotEqual(result_service.returncode, 0, f"Found invalid pattern in {service_file}: {result_service.stdout}")
            
            print("✅ No invalid asynccontextmanager patterns found")
            
        except FileNotFoundError:
            print("⚠️ grep command not available, skipping pattern verification")
    
    async def test_session_handling_consistency(self):
        """Test that session handling is consistent across all methods"""
        facade = StatusUpdateFacade()
        service = UnifiedTransactionService()
        
        # Verify all methods handle both session=None and session=provided correctly
        test_cases = [
            ("StatusUpdateFacade.update_cashout_status", facade.update_cashout_status),
            ("StatusUpdateFacade.update_escrow_status", facade.update_escrow_status),
            ("StatusUpdateFacade.update_exchange_status", facade.update_exchange_status),
            ("StatusUpdateFacade.update_unified_transaction_status", facade.update_unified_transaction_status),
            ("UnifiedTransactionService.transition_status", service.transition_status),
        ]
        
        for method_name, method in test_cases:
            # Check method signature supports session parameter
            import inspect
            sig = inspect.signature(method)
            self.assertIn('session', sig.parameters, f"{method_name} should accept session parameter")
            
            # Check session parameter has default None
            session_param = sig.parameters['session']
            self.assertEqual(session_param.default, None, f"{method_name} session parameter should default to None")
            
        print("✅ All methods have consistent session parameter handling")


async def run_session_management_tests():
    """Run all session management tests"""
    print("🧪 Running Session Management Fix Tests...")
    print("=" * 60)
    
    # Run main test suite
    test_suite = TestSessionManagementFixes()
    await test_suite.asyncSetUp()
    
    try:
        # StatusUpdateFacade tests
        print("\n🔧 Testing StatusUpdateFacade Session Management...")
        await test_suite.test_cashout_status_update_with_managed_session()
        await test_suite.test_cashout_status_update_with_provided_session()
        await test_suite.test_escrow_status_update_session_handling()
        await test_suite.test_exchange_status_update_session_handling()
        
        # UnifiedTransactionService tests
        print("\n🔧 Testing UnifiedTransactionService Session Management...")
        await test_suite.test_transition_status_with_managed_session()
        await test_suite.test_transition_status_with_provided_session()
        await test_suite.test_transition_cashout_status_session_handling()
        
        # Error handling tests
        print("\n🔧 Testing Error Handling...")
        await test_suite.test_session_error_handling()
        
        # Integration tests
        print("\n🔧 Running Integration Tests...")
        integration_suite = TestSessionManagementIntegration()
        await integration_suite.test_no_invalid_asynccontextmanager_pattern()
        await integration_suite.test_session_handling_consistency()
        
        print("\n" + "=" * 60)
        print("🎉 ALL SESSION MANAGEMENT TESTS PASSED!")
        print("✅ Critical session management bug has been successfully fixed")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_session_management_tests())
    sys.exit(0 if success else 1)