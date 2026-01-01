"""
Test suite to verify the critical financial bug fix in release_cashout_hold() method.

This test ensures that when cashouts fail, funds are properly returned to the user's 
available balance instead of vanishing permanently.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime
from services.crypto import CashoutHoldService


@pytest.mark.unit
class TestReleaseCashoutHoldFix:
    """Test the critical release_cashout_hold() financial bug fix"""

    def test_release_cashout_hold_restores_balance(self):
        """
        CRITICAL TEST: Verify that release_cashout_hold() properly moves funds 
        from frozen_balance back to available balance
        """
        # Mock scenario: User has $60.33 available + $2.00 frozen = $62.33 total
        user_id = 123
        frozen_amount = Decimal("2.00")
        available_balance = Decimal("60.33")
        total_before = available_balance + frozen_amount  # $62.33

        # Mock wallet with both available and frozen funds
        mock_wallet = MagicMock()
        mock_wallet.available_balance = available_balance
        mock_wallet.frozen_balance = frozen_amount
        mock_wallet.user_id = user_id

        # Mock database session
        mock_session = MagicMock()
        
        # Mock idempotency check - no existing release transaction
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock admin security check to allow test admin
        with patch('utils.admin_security.is_admin_secure', return_value=True):
            # Mock the locked wallet operation context manager
            with patch('utils.atomic_transactions.locked_wallet_operation') as mock_locked_wallet:
                mock_locked_wallet.return_value.__enter__.return_value = mock_wallet
                
                # Mock Transaction model
                with patch('services.crypto.Transaction') as mock_transaction_class:
                    mock_transaction_instance = MagicMock()
                    mock_transaction_class.return_value = mock_transaction_instance
                    
                    # Mock transaction ID generation
                    with patch('services.crypto.UniversalIDGenerator.generate_transaction_id', return_value="TEST_TX_123"):
                        
                        # Mock financial audit logger
                        with patch('services.crypto.financial_audit_logger.log_financial_event'):
                            
                            # Mock audit logger (imported inside the function)
                            with patch('services.audit_logger.AuditLogger') as mock_audit_logger_class:
                                mock_audit_logger = MagicMock()
                                mock_audit_logger_class.return_value = mock_audit_logger
                                
                                # Mock asyncio.create_task for async audit logging
                                with patch('asyncio.create_task'):
                                    
                                    # Call the fixed release_cashout_hold method with test admin
                                    TEST_ADMIN_ID = 999999  # Test admin for unit tests
                                    result = CashoutHoldService.release_cashout_hold(
                                        user_id=user_id,
                                        amount=float(frozen_amount),
                                        admin_id=TEST_ADMIN_ID,
                                        currency="USD",
                                        cashout_id="CASHOUT_FAIL_123",
                                        hold_transaction_id="HOLD_TX_456",
                                        session=mock_session
                                    )

        # CRITICAL ASSERTIONS: Verify the fix works correctly
        
        # 1. Method should succeed
        assert result["success"] is True, f"Method failed: {result.get('error', 'Unknown error')}"
        
        # 2. CRITICAL: Verify available balance was INCREASED by the released amount
        expected_new_balance = Decimal("62.33")  # $60.33 + $2.00
        assert mock_wallet.available_balance == expected_new_balance, (
            f"CRITICAL BUG: Available balance not restored! "
            f"Expected: ${expected_new_balance:.2f}, Got: ${mock_wallet.available_balance:.2f}"
        )
        
        # 3. CRITICAL: Verify frozen balance was DECREASED by the released amount  
        expected_new_frozen = Decimal("0.00")  # All frozen funds should be released
        assert mock_wallet.frozen_balance == expected_new_frozen, (
            f"CRITICAL BUG: Frozen balance not reduced! "
            f"Expected: ${expected_new_frozen:.2f}, Got: ${mock_wallet.frozen_balance:.2f}"
        )
        
        # 4. Verify total funds are conserved (no money vanishes)
        total_after = mock_wallet.available_balance + mock_wallet.frozen_balance
        assert total_after == total_before, (
            f"CRITICAL BUG: Funds vanished! "
            f"Total before: ${total_before:.2f}, Total after: ${total_after:.2f}"
        )
        
        # 5. Verify transaction was created with correct data
        mock_session.add.assert_called_once()
        added_transaction = mock_session.add.call_args[0][0]
        
        # Check transaction fields (no metadata field in Transaction model)
        assert added_transaction.transaction_type == "cashout_hold_release"
        assert added_transaction.amount == frozen_amount
        assert added_transaction.currency == "USD"
        assert added_transaction.status == "completed"
        assert "hold_tx:HOLD_TX_456" in added_transaction.description
        assert added_transaction.user_id == user_id
        
        # 6. Verify session was flushed to persist transaction
        mock_session.flush.assert_called_once()
        
        # 7. Verify result indicates funds were restored
        assert result["funds_restored"] is True
        assert result["admin_validated"] is True
        assert result["released_amount"] == frozen_amount

    def test_release_cashout_hold_insufficient_frozen_balance(self):
        """Test that method properly handles insufficient frozen balance"""
        user_id = 123
        frozen_amount = Decimal("1.00")  # User only has $1 frozen
        requested_release = 5.00  # But trying to release $5

        mock_wallet = MagicMock()
        mock_wallet.available_balance = Decimal("50.00")
        mock_wallet.frozen_balance = frozen_amount
        mock_wallet.user_id = user_id

        mock_session = MagicMock()
        
        # Mock idempotency check - no existing release
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch('utils.admin_security.is_admin_secure', return_value=True):
            with patch('utils.atomic_transactions.locked_wallet_operation') as mock_locked_wallet:
                mock_locked_wallet.return_value.__enter__.return_value = mock_wallet
                
                TEST_ADMIN_ID = 999999
                result = CashoutHoldService.release_cashout_hold(
                    user_id=user_id,
                    amount=requested_release,
                    admin_id=TEST_ADMIN_ID,
                    currency="USD",
                    session=mock_session
                )

        # Should fail gracefully with clear error message
        assert result["success"] is False
        assert "Insufficient frozen balance" in result["error"]
        assert result["frozen_balance"] == float(frozen_amount)
        assert result["requested_amount"] == Decimal("5.00")
        
        # Verify wallet was NOT modified
        assert mock_wallet.available_balance == Decimal("50.00")
        assert mock_wallet.frozen_balance == frozen_amount
        
        # Verify no transaction was added
        mock_session.add.assert_not_called()

    def test_release_cashout_hold_idempotency_protection(self):
        """Test that method prevents duplicate processing of the same hold release"""
        user_id = 123
        hold_transaction_id = "HOLD_TX_789"
        
        # Mock existing release transaction (already processed)
        mock_existing_tx = MagicMock()
        mock_existing_tx.transaction_id = "EXISTING_RELEASE_TX"
        mock_existing_tx.amount = Decimal("2.00")
        mock_existing_tx.created_at = datetime(2025, 1, 15, 10, 30, 0)
        
        mock_session = MagicMock()
        # Mock the query chain to return existing transaction
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_existing_tx
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        with patch('utils.admin_security.is_admin_secure', return_value=True):
            TEST_ADMIN_ID = 999999
            result = CashoutHoldService.release_cashout_hold(
                user_id=user_id,
                amount=2.00,
                admin_id=TEST_ADMIN_ID,
                currency="USD",
                hold_transaction_id=hold_transaction_id,
                session=mock_session
            )

        # Should succeed but indicate it's idempotent (duplicate prevented)
        assert result["success"] is True
        assert result["idempotent"] is True
        assert "duplicate prevention" in result.get("warning", "").lower()
        assert result["release_transaction_id"] == "EXISTING_RELEASE_TX"
        assert result["released_amount"] == 2.00
        
        # Verify NO new transaction was added (idempotent behavior)
        mock_session.add.assert_not_called()

    def test_precision_handling_micro_amounts(self):
        """Test that method handles very small amounts with correct precision"""
        user_id = 123
        # Use 0.006 which rounds UP to 0.01 with ROUND_HALF_UP for USD precision
        micro_amount = 0.006
        
        mock_wallet = MagicMock()
        mock_wallet.available_balance = Decimal("10.00")
        mock_wallet.frozen_balance = Decimal("0.02")  # Enough to cover 0.01 after rounding
        mock_wallet.user_id = user_id

        mock_session = MagicMock()
        
        # Mock idempotency check - no existing release
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch('utils.admin_security.is_admin_secure', return_value=True):
            with patch('utils.atomic_transactions.locked_wallet_operation') as mock_locked_wallet:
                mock_locked_wallet.return_value.__enter__.return_value = mock_wallet
                
                with patch('services.crypto.Transaction'):
                    with patch('services.crypto.UniversalIDGenerator.generate_transaction_id', return_value="MICRO_TX"):
                        with patch('services.crypto.financial_audit_logger.log_financial_event'):
                            with patch('services.audit_logger.AuditLogger'):
                                with patch('asyncio.create_task'):
                                    
                                    TEST_ADMIN_ID = 999999
                                    result = CashoutHoldService.release_cashout_hold(
                                        user_id=user_id,
                                        amount=micro_amount,
                                        admin_id=TEST_ADMIN_ID,
                                        currency="USD",  # USD uses 0.01 precision
                                        session=mock_session
                                    )

        # Should handle micro amounts with proper USD precision (0.01)
        assert result["success"] is True
        # 0.006 rounds UP to 0.01 with ROUND_HALF_UP
        assert result["released_amount"] == Decimal("0.01")
        
        # Verify wallet balances are properly quantized
        # Available: 10.00 + 0.01 = 10.01
        # Frozen: 0.02 - 0.01 = 0.01
        assert mock_wallet.available_balance == Decimal("10.01")
        assert mock_wallet.frozen_balance == Decimal("0.01")

    def test_admin_security_validation(self):
        """Test that non-admin users are rejected"""
        user_id = 123
        non_admin_id = 456  # Not an admin
        
        mock_session = MagicMock()
        
        # Mock admin security check to reject non-admin
        with patch('utils.admin_security.is_admin_secure', return_value=False):
            result = CashoutHoldService.release_cashout_hold(
                user_id=user_id,
                amount=2.00,
                admin_id=non_admin_id,
                currency="USD",
                session=mock_session
            )
        
        # Should fail with security error
        assert result["success"] is False
        assert "SECURITY" in result["error"]
        assert "Administrative privileges required" in result["error"]
        assert result["admin_validated"] is False
        assert result.get("security_violation") is True
        
        # Verify no database operations were performed
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
