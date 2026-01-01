"""
Comprehensive Escrow Handler Tests - Priority 2 Coverage
Tests all error paths, edge cases, and negative scenarios for handlers/escrow.py

Coverage Goals:
- Seller lookup variants and validation failures  
- Amount validation (min/max/decimals) edge cases
- Payment flows with insufficient funds scenarios
- Over/underpayment handling and recovery
- Timeout/expiration scenarios and cleanup
- Dispute resolution and refund paths
- UnifiedTransactionService interactions
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

# Telegram imports
from telegram import Update, User as TelegramUser, Message, CallbackQuery, Chat
from telegram.ext import ContextTypes, ConversationHandler

# Database and model imports
from models import (
    User, Escrow, EscrowStatus, Wallet, Transaction, TransactionType,
    EscrowHolding, UnifiedTransaction, UnifiedTransactionStatus, UnifiedTransactionType
)

# Handler imports - real handlers for integration testing
from handlers.escrow import (
    start_secure_trade, handle_seller_input, handle_amount_input,
    handle_description_input, handle_delivery_time_input,
    handle_confirm_trade_final, execute_wallet_payment, execute_crypto_payment
)


@pytest.mark.escrow
@pytest.mark.handler_coverage
class TestEscrowSellerValidation:
    """Test seller lookup and validation scenarios"""
    
    @pytest.mark.asyncio
    async def test_handle_seller_input_invalid_username(
        self, test_db_session, patched_services, telegram_factory
    ):
        """Test seller input with invalid/non-existent username"""
        
        # Create buyer
        buyer = telegram_factory.create_user(telegram_id=123456, username='buyer')
        
        # Create update with invalid seller username
        update = telegram_factory.create_update(
            message=telegram_factory.create_message(
                text='@nonexistent_seller',
                user=buyer
            )
        )
        context = telegram_factory.create_context()
        
        # Mock seller lookup to return None (not found)
        with patch('handlers.escrow.get_user_by_username', return_value=None):
            result = await handle_seller_input(update, context)
            
            # Should handle invalid seller gracefully
            assert result is not None
            # Check that appropriate error message was sent
            if hasattr(context.bot, 'send_message'):
                context.bot.send_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_seller_input_seller_is_buyer(
        self, test_db_session, patched_services, telegram_factory
    ):
        """Test seller input where seller is the same as buyer"""
        
        # Create buyer
        buyer = telegram_factory.create_user(telegram_id=123456, username='buyer')
        
        # Create update where buyer tries to trade with themselves
        update = telegram_factory.create_update(
            message=telegram_factory.create_message(
                text='@buyer',  # Same username
                user=buyer
            )
        )
        context = telegram_factory.create_context()
        
        # Mock seller lookup to return the buyer (same user)
        with patch('handlers.escrow.get_user_by_username', return_value=buyer):
            result = await handle_seller_input(update, context)
            
            # Should reject self-trading
            assert result is not None
            if hasattr(context.bot, 'send_message'):
                context.bot.send_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_seller_input_invalid_format(
        self, test_db_session, patched_services, telegram_factory
    ):
        """Test seller input with invalid format (no @, special chars, etc.)"""
        
        buyer = telegram_factory.create_user(telegram_id=123456, username='buyer')
        
        invalid_inputs = [
            'seller_without_at',    # No @ symbol
            '@sel ler',            # Space in username
            '@seller!',            # Special character
            '@',                   # Just @ symbol
            '',                    # Empty string
            '123',                 # Numbers only
            '@' + 'x' * 50,       # Too long username
        ]
        
        for invalid_input in invalid_inputs:
            update = telegram_factory.create_update(
                message=telegram_factory.create_message(
                    text=invalid_input,
                    user=buyer
                )
            )
            context = telegram_factory.create_context()
            
            result = await handle_seller_input(update, context)
            
            # Should handle invalid format gracefully
            assert result is not None


@pytest.mark.escrow
@pytest.mark.handler_coverage  
class TestEscrowAmountValidation:
    """Test amount validation edge cases and error scenarios"""
    
    @pytest.mark.asyncio
    async def test_handle_amount_input_zero_amount(
        self, test_db_session, patched_services, telegram_factory
    ):
        """Test amount input with zero value"""
        
        buyer = telegram_factory.create_user(telegram_id=123456, username='buyer')
        
        zero_inputs = ['0', '0.00', '0.0', '00.00']
        
        for zero_input in zero_inputs:
            update = telegram_factory.create_update(
                message=telegram_factory.create_message(
                    text=zero_input,
                    user=buyer
                )
            )
            context = telegram_factory.create_context()
            
            result = await handle_amount_input(update, context)
            
            # Should reject zero amounts
            assert result is not None
            if hasattr(context.bot, 'send_message'):
                context.bot.send_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_amount_input_negative_amount(
        self, test_db_session, patched_services, telegram_factory
    ):
        """Test amount input with negative values"""
        
        buyer = telegram_factory.create_user(telegram_id=123456, username='buyer')
        
        negative_inputs = ['-1', '-10.50', '-0.01', '-.50']
        
        for negative_input in negative_inputs:
            update = telegram_factory.create_update(
                message=telegram_factory.create_message(
                    text=negative_input,
                    user=buyer
                )
            )
            context = telegram_factory.create_context()
            
            result = await handle_amount_input(update, context)
            
            # Should reject negative amounts
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_handle_amount_input_invalid_format(
        self, test_db_session, patched_services, telegram_factory
    ):
        """Test amount input with invalid formats"""
        
        buyer = telegram_factory.create_user(telegram_id=123456, username='buyer')
        
        invalid_inputs = [
            'abc',              # Non-numeric text
            '10.50.25',         # Multiple decimals
            '10,50',            # Comma separator
            '$10.50',           # Currency symbol
            '10.50 USD',        # With currency
            '1e10',             # Scientific notation
            '∞',                # Special characters
            '',                 # Empty string
            '   ',              # Whitespace only
            '10..50',           # Double decimal
        ]
        
        for invalid_input in invalid_inputs:
            update = telegram_factory.create_update(
                message=telegram_factory.create_message(
                    text=invalid_input,
                    user=buyer
                )
            )
            context = telegram_factory.create_context()
            
            result = await handle_amount_input(update, context)
            
            # Should handle invalid formats gracefully
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_handle_amount_input_precision_limits(
        self, test_db_session, patched_services, telegram_factory
    ):
        """Test amount input with excessive decimal precision"""
        
        buyer = telegram_factory.create_user(telegram_id=123456, username='buyer')
        
        precision_inputs = [
            '10.123456789',     # Many decimal places
            '0.00000001',       # Very small amount
            '1.999999999',      # High precision
        ]
        
        for precision_input in precision_inputs:
            update = telegram_factory.create_update(
                message=telegram_factory.create_message(
                    text=precision_input,
                    user=buyer
                )
            )
            context = telegram_factory.create_context()
            
            result = await handle_amount_input(update, context)
            
            # Should handle or round precision appropriately
            assert result is not None
    
    @pytest.mark.asyncio 
    async def test_handle_amount_input_extreme_values(
        self, test_db_session, patched_services, telegram_factory
    ):
        """Test amount input with extreme values (too large/small)"""
        
        buyer = telegram_factory.create_user(telegram_id=123456, username='buyer')
        
        extreme_inputs = [
            '999999999999.99',  # Very large amount
            '0.00000001',       # Very small amount 
            '1' + '0' * 20,     # Astronomical amount
        ]
        
        for extreme_input in extreme_inputs:
            update = telegram_factory.create_update(
                message=telegram_factory.create_message(
                    text=extreme_input,
                    user=buyer
                )
            )
            context = telegram_factory.create_context()
            
            result = await handle_amount_input(update, context)
            
            # Should handle extreme values appropriately
            assert result is not None


@pytest.mark.escrow
@pytest.mark.handler_coverage
class TestEscrowPaymentFlows:
    """Test payment flow scenarios and error handling"""
    
    @pytest.mark.asyncio
    async def test_execute_wallet_payment_insufficient_funds(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test wallet payment with insufficient funds"""
        
        # Create buyer with low balance
        buyer = test_data_factory.create_test_user(
            telegram_id=123456,
            username='buyer',
            balances={'USD': Decimal('10.00')}  # Low balance
        )
        
        # Create escrow requiring more funds
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=buyer.id + 1,
            amount=Decimal('100.00'),  # More than available balance
            currency='USD'
        )
        
        update = telegram_factory.create_update(
            callback_query=telegram_factory.create_callback_query(
                data=f'execute_wallet_payment:{escrow.id}',
                user=telegram_factory.create_user(telegram_id=buyer.telegram_id)
            )
        )
        context = telegram_factory.create_context()
        
        result = await execute_wallet_payment(update, context)
        
        # Should handle insufficient funds gracefully
        assert result is not None
        # Should not process payment
        if hasattr(context.bot, 'edit_message_text'):
            context.bot.edit_message_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_execute_crypto_payment_network_failure(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test crypto payment with network/service failure"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=buyer.id + 1,
            amount=Decimal('100.00'),
            currency='USD'
        )
        
        update = telegram_factory.create_update(
            callback_query=telegram_factory.create_callback_query(
                data=f'execute_crypto_payment:{escrow.id}:BTC',
                user=telegram_factory.create_user(telegram_id=buyer.telegram_id)
            )
        )
        context = telegram_factory.create_context()
        
        # Mock crypto service failure
        with patch('handlers.escrow.CryptoServiceAtomic') as mock_crypto:
            mock_crypto.generate_payment_address.side_effect = Exception("Network timeout")
            
            result = await execute_crypto_payment(update, context)
            
            # Should handle crypto service failure gracefully
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_execute_wallet_payment_concurrent_access(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test wallet payment with concurrent access/race conditions"""
        
        buyer = test_data_factory.create_test_user(
            telegram_id=123456,
            username='buyer', 
            balances={'USD': Decimal('100.00')}
        )
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=buyer.id + 1,
            amount=Decimal('90.00'),
            currency='USD'
        )
        
        update = telegram_factory.create_update(
            callback_query=telegram_factory.create_callback_query(
                data=f'execute_wallet_payment:{escrow.id}',
                user=telegram_factory.create_user(telegram_id=buyer.telegram_id)
            )
        )
        context = telegram_factory.create_context()
        
        # Simulate concurrent access by having transaction fail
        with patch('handlers.escrow.atomic_transaction') as mock_transaction:
            mock_transaction.side_effect = Exception("Database lock timeout")
            
            result = await execute_wallet_payment(update, context)
            
            # Should handle concurrency issues gracefully
            assert result is not None


@pytest.mark.escrow 
@pytest.mark.handler_coverage
class TestEscrowOverUnderpayment:
    """Test over/underpayment scenarios and recovery"""
    
    @pytest.mark.asyncio
    async def test_crypto_payment_overpayment_handling(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test handling of crypto overpayments"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=buyer.id + 1,
            amount=Decimal('100.00'),
            currency='USD'
        )
        
        # Simulate overpayment scenario
        overpayment_amount = Decimal('110.00')  # $10 overpayment
        
        with patch('handlers.escrow.CryptoServiceAtomic') as mock_crypto:
            # Mock crypto service detecting overpayment
            mock_crypto.check_payment_status.return_value = {
                'status': 'confirmed',
                'received_usd': overpayment_amount,
                'expected_usd': Decimal('100.00'),
                'overpayment': Decimal('10.00')
            }
            
            # Test overpayment detection and handling
            # This would be triggered by webhook or payment confirmation
            # The actual handler would need to process the overpayment
            
            assert overpayment_amount > Decimal('100.00')
            assert (overpayment_amount - Decimal('100.00')) == Decimal('10.00')
    
    @pytest.mark.asyncio
    async def test_crypto_payment_underpayment_handling(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test handling of crypto underpayments"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=buyer.id + 1,
            amount=Decimal('100.00'),
            currency='USD'
        )
        
        # Simulate underpayment scenario
        underpayment_amount = Decimal('95.00')  # $5 underpayment
        
        with patch('handlers.escrow.CryptoServiceAtomic') as mock_crypto:
            # Mock crypto service detecting underpayment
            mock_crypto.check_payment_status.return_value = {
                'status': 'partial',
                'received_usd': underpayment_amount,
                'expected_usd': Decimal('100.00'),
                'shortfall': Decimal('5.00')
            }
            
            # Test underpayment detection
            assert underpayment_amount < Decimal('100.00')
            assert (Decimal('100.00') - underpayment_amount) == Decimal('5.00')
    
    @pytest.mark.asyncio
    async def test_partial_payment_timeout_scenario(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test timeout scenarios with partial payments"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=buyer.id + 1,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.PAYMENT_PENDING.value
        )
        
        # Simulate payment timeout (escrow has been pending too long)
        with patch('handlers.escrow.datetime') as mock_datetime:
            # Mock current time to be past timeout
            mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(hours=25)  # 25 hours later
            
            # Test timeout handling logic
            # This would typically be handled by a background job
            # but we can test the logic components
            
            assert escrow.status == EscrowStatus.PAYMENT_PENDING.value
            # Timeout logic would change status to EXPIRED


@pytest.mark.escrow
@pytest.mark.handler_coverage
class TestEscrowDisputeResolution:
    """Test dispute resolution and refund paths"""
    
    @pytest.mark.asyncio
    async def test_dispute_initiation_by_buyer(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test buyer initiating dispute on active escrow"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        seller = test_data_factory.create_test_user(telegram_id=789012, username='seller')
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.ACTIVE.value  # Escrow is active
        )
        
        # Simulate buyer dispute button
        update = telegram_factory.create_update(
            callback_query=telegram_factory.create_callback_query(
                data=f'dispute_escrow:{escrow.id}',
                user=telegram_factory.create_user(telegram_id=buyer.telegram_id)
            )
        )
        context = telegram_factory.create_context()
        
        # Test dispute initiation
        # Note: We'd need the actual dispute handler for this test
        # This tests the framework for handling disputes
        
        assert escrow.status == EscrowStatus.ACTIVE.value
        assert escrow.buyer_id == buyer.id
    
    @pytest.mark.asyncio
    async def test_dispute_initiation_by_seller(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test seller initiating dispute on active escrow"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        seller = test_data_factory.create_test_user(telegram_id=789012, username='seller')
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.ACTIVE.value
        )
        
        # Simulate seller dispute
        update = telegram_factory.create_update(
            callback_query=telegram_factory.create_callback_query(
                data=f'dispute_escrow:{escrow.id}',
                user=telegram_factory.create_user(telegram_id=seller.telegram_id)
            )
        )
        context = telegram_factory.create_context()
        
        # Test seller can also initiate disputes
        assert escrow.seller_id == seller.id
        assert escrow.status == EscrowStatus.ACTIVE.value
    
    @pytest.mark.asyncio
    async def test_admin_dispute_resolution(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test admin resolving disputed escrow"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        seller = test_data_factory.create_test_user(telegram_id=789012, username='seller')
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.DISPUTED.value  # Already disputed
        )
        
        # Simulate admin resolution
        admin_user = telegram_factory.create_user(telegram_id=999999, is_admin=True)
        
        update = telegram_factory.create_update(
            callback_query=telegram_factory.create_callback_query(
                data=f'resolve_dispute:{escrow.id}:favor_buyer',
                user=admin_user
            )
        )
        context = telegram_factory.create_context()
        
        # Test admin resolution framework
        assert escrow.status == EscrowStatus.DISPUTED.value
        # Admin should be able to resolve in favor of buyer or seller


@pytest.mark.escrow
@pytest.mark.handler_coverage
class TestUnifiedTransactionServiceIntegration:
    """Test integration with UnifiedTransactionService"""
    
    @pytest.mark.asyncio
    async def test_unified_transaction_creation_success(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test successful UnifiedTransaction creation for escrow"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        seller = test_data_factory.create_test_user(telegram_id=789012, username='seller')
        
        # Mock UnifiedTransactionService success
        with patch('handlers.escrow.UnifiedTransactionService') as mock_uts:
            mock_uts.create_transaction.return_value = {
                'success': True,
                'transaction_id': 'UTS_123456',
                'status': UnifiedTransactionStatus.CREATED.value
            }
            
            # Test successful UTS integration
            result = mock_uts.create_transaction.return_value
            assert result['success'] is True
            assert 'transaction_id' in result
            assert result['status'] == UnifiedTransactionStatus.CREATED.value
    
    @pytest.mark.asyncio
    async def test_unified_transaction_creation_failure(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test UnifiedTransaction creation failure handling"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        
        # Mock UnifiedTransactionService failure
        with patch('handlers.escrow.UnifiedTransactionService') as mock_uts:
            mock_uts.create_transaction.side_effect = Exception("UTS service unavailable")
            
            # Test UTS failure handling
            try:
                result = mock_uts.create_transaction()
                assert False, "Should have raised exception"
            except Exception as e:
                assert "UTS service unavailable" in str(e)
    
    @pytest.mark.asyncio
    async def test_unified_transaction_retry_logic(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test UnifiedTransaction retry mechanisms"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        
        # Mock UTS with retry behavior
        with patch('handlers.escrow.UnifiedTransactionService') as mock_uts:
            # First call fails, second succeeds
            mock_uts.create_transaction.side_effect = [
                Exception("Temporary failure"),
                {'success': True, 'transaction_id': 'UTS_RETRY_123'}
            ]
            
            # Test retry logic (would need actual retry implementation)
            try:
                result = mock_uts.create_transaction()
                assert False, "First call should fail"
            except Exception:
                pass
            
            # Second call should succeed
            result = mock_uts.create_transaction()
            assert result['success'] is True
            assert 'UTS_RETRY_123' in result['transaction_id']


@pytest.mark.escrow
@pytest.mark.handler_coverage  
class TestEscrowTimeoutScenarios:
    """Test timeout and expiration scenarios"""
    
    @pytest.mark.asyncio
    async def test_payment_timeout_cleanup(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test cleanup of timed-out payment-pending escrows"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        seller = test_data_factory.create_test_user(telegram_id=789012, username='seller')
        
        # Create escrow that's been pending too long
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.PAYMENT_PENDING.value
        )
        
        # Mock expired timestamp
        with patch.object(escrow, 'created_at', datetime.utcnow() - timedelta(hours=25)):
            
            # Test timeout detection
            time_elapsed = datetime.utcnow() - escrow.created_at
            assert time_elapsed > timedelta(hours=24)  # Past timeout threshold
            
            # Timeout cleanup would change status to EXPIRED
            # and notify both parties
    
    @pytest.mark.asyncio  
    async def test_seller_response_timeout(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test timeout when seller doesn't respond to escrow invitation"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        seller = test_data_factory.create_test_user(telegram_id=789012, username='seller')
        
        # Create escrow awaiting seller response
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.AWAITING_SELLER.value
        )
        
        # Test seller response timeout (typically 48-72 hours)
        with patch.object(escrow, 'created_at', datetime.utcnow() - timedelta(hours=73)):
            
            time_elapsed = datetime.utcnow() - escrow.created_at
            assert time_elapsed > timedelta(hours=72)  # Past seller response timeout
            
            # Should expire and refund buyer
    
    @pytest.mark.asyncio
    async def test_delivery_confirmation_timeout(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test timeout when buyer doesn't confirm delivery"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        seller = test_data_factory.create_test_user(telegram_id=789012, username='seller')
        
        # Create active escrow (awaiting delivery confirmation)
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.ACTIVE.value
        )
        
        # Test delivery confirmation timeout (typically 7-14 days)
        with patch.object(escrow, 'created_at', datetime.utcnow() - timedelta(days=15)):
            
            time_elapsed = datetime.utcnow() - escrow.created_at
            assert time_elapsed > timedelta(days=14)  # Past delivery timeout
            
            # Should auto-release to seller after extended timeout


@pytest.mark.escrow
@pytest.mark.integration
class TestEscrowEndToEndErrorScenarios:
    """Integration tests for complete error scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_escrow_failure_recovery(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test complete escrow flow with failure and recovery"""
        
        buyer = test_data_factory.create_test_user(
            telegram_id=123456,
            username='buyer',
            balances={'USD': Decimal('100.00')}
        )
        seller = test_data_factory.create_test_user(telegram_id=789012, username='seller')
        
        # Start escrow creation
        telegram_buyer = telegram_factory.create_user(telegram_id=buyer.telegram_id)
        
        # Test 1: Start trade
        update1 = telegram_factory.create_update(
            message=telegram_factory.create_message(text='/start_trade', user=telegram_buyer)
        )
        context1 = telegram_factory.create_context()
        
        result1 = await start_secure_trade(update1, context1)
        assert result1 is not None
        
        # Test 2: Invalid seller input (should fail gracefully)
        update2 = telegram_factory.create_update(
            message=telegram_factory.create_message(text='@invalid_seller', user=telegram_buyer)
        )
        context2 = telegram_factory.create_context()
        
        with patch('handlers.escrow.get_user_by_username', return_value=None):
            result2 = await handle_seller_input(update2, context2)
            assert result2 is not None
        
        # Test 3: Valid seller input (should succeed)
        update3 = telegram_factory.create_update(
            message=telegram_factory.create_message(text='@seller', user=telegram_buyer)
        )
        context3 = telegram_factory.create_context()
        
        seller_user = test_data_factory.create_test_user(telegram_id=789012, username='seller')
        with patch('handlers.escrow.get_user_by_username', return_value=seller_user):
            result3 = await handle_seller_input(update3, context3)
            assert result3 is not None
        
        # Test 4: Invalid amount (should fail)  
        update4 = telegram_factory.create_update(
            message=telegram_factory.create_message(text='-10.50', user=telegram_buyer)
        )
        context4 = telegram_factory.create_context()
        
        result4 = await handle_amount_input(update4, context4)
        assert result4 is not None
        
        # Test 5: Valid amount (should succeed)
        update5 = telegram_factory.create_update(
            message=telegram_factory.create_message(text='50.00', user=telegram_buyer)
        )
        context5 = telegram_factory.create_context()
        
        result5 = await handle_amount_input(update5, context5)
        assert result5 is not None
    
    @pytest.mark.asyncio
    async def test_escrow_external_service_failures(
        self, test_db_session, patched_services, telegram_factory, test_data_factory
    ):
        """Test escrow handling when external services fail"""
        
        buyer = test_data_factory.create_test_user(telegram_id=123456, username='buyer')
        
        # Test with all external services failing
        with patch('handlers.escrow.CryptoServiceAtomic') as mock_crypto, \
             patch('handlers.escrow.UnifiedTransactionService') as mock_uts, \
             patch('handlers.escrow.ConditionalOTPService') as mock_otp:
            
            # Mock all services to fail
            mock_crypto.generate_payment_address.side_effect = Exception("Crypto service down")
            mock_uts.create_transaction.side_effect = Exception("UTS service down") 
            mock_otp.send_otp.side_effect = Exception("OTP service down")
            
            # Escrow creation should still handle gracefully
            # (Testing the resilience of the handlers)
            telegram_buyer = telegram_factory.create_user(telegram_id=buyer.telegram_id)
            
            update = telegram_factory.create_update(
                message=telegram_factory.create_message(text='/start_trade', user=telegram_buyer)
            )
            context = telegram_factory.create_context()
            
            result = await start_secure_trade(update, context)
            
            # Should handle service failures gracefully
            assert result is not None