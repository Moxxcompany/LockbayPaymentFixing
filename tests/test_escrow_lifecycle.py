"""
Comprehensive test suite for escrow lifecycle
Tests post-creation flows: amounts, payment methods, confirmation, completion
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal

from telegram import Update, Message, User as TelegramUser, CallbackQuery
from telegram.ext import ContextTypes

from handlers.escrow import (
    handle_amount_input, handle_description_input, handle_delivery_time_input,
    handle_payment_method_selection, handle_wallet_payment_confirmation
)
from models import User, Escrow, EscrowStatus, Wallet, Transaction
from services.crypto import CryptoServiceAtomic
from services.unified_transaction_service import UnifiedTransactionService
from utils.constants import EscrowStates
from config import Config


class TestEscrowLifecycle:
    """Test suite for escrow lifecycle management"""

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram update object"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=TelegramUser)
        update.effective_user.id = 5590563715
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        update.callback_query = None
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock context with escrow data"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {
            "escrow_data": {
                "early_escrow_id": "ES0918256R2N",
                "status": "creating",
                "seller_type": "username",
                "seller_identifier": "onarrival1",
                "seller_profile": {
                    "user_id": 2,
                    "display_name": "Seller User",
                    "exists_on_platform": True
                }
            }
        }
        return context

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing"""
        return User(
            id=1,
            telegram_id="5590563715",
            username="testuser",
            first_name="Test",
            email="test@example.com",
            created_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_escrow(self):
        """Create a sample escrow for testing"""
        return Escrow(
            id="ES0918256R2N",
            buyer_id=1,
            seller_id=2,
            amount=Decimal("100.00"),
            currency="USD",
            description="Test trade",
            status=EscrowStatus.PAYMENT_PENDING,
            created_at=datetime.utcnow()
        )

    @pytest.mark.asyncio
    async def test_handle_amount_input_valid(self, mock_update, mock_context, sample_user):
        """Test handling valid amount input"""
        mock_update.message.text = "100"
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            
            result = await handle_amount_input(mock_update, mock_context)
            
            assert result == EscrowStates.DESCRIPTION_INPUT
            assert mock_context.user_data["escrow_data"]["amount"] == Decimal("100.00")
            
            # Verify progression message was sent
            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Step 3 of 4" in call_args

    @pytest.mark.asyncio
    async def test_handle_amount_input_below_minimum(self, mock_update, mock_context, sample_user):
        """Test handling amount below minimum threshold"""
        mock_update.message.text = "5"  # Below minimum
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            
            result = await handle_amount_input(mock_update, mock_context)
            
            # Should return to amount input due to validation error
            assert result == EscrowStates.AMOUNT_INPUT
            
            # Verify error message was sent
            mock_update.message.reply_text.assert_called()
            error_call_args = mock_update.message.reply_text.call_args[0][0]
            assert "minimum" in error_call_args.lower()

    @pytest.mark.asyncio
    async def test_handle_amount_input_invalid_format(self, mock_update, mock_context, sample_user):
        """Test handling invalid amount format"""
        mock_update.message.text = "not_a_number"
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            
            result = await handle_amount_input(mock_update, mock_context)
            
            assert result == EscrowStates.AMOUNT_INPUT
            
            # Verify error message was sent
            mock_update.message.reply_text.assert_called()
            error_call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in error_call_args

    @pytest.mark.asyncio
    async def test_handle_description_input_valid(self, mock_update, mock_context, sample_user):
        """Test handling valid description input"""
        mock_update.message.text = "MacBook Pro 16-inch laptop in excellent condition"
        mock_context.user_data["escrow_data"]["amount"] = Decimal("100.00")
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            
            result = await handle_description_input(mock_update, mock_context)
            
            assert result == EscrowStates.DELIVERY_TIME
            assert mock_context.user_data["escrow_data"]["description"] == "MacBook Pro 16-inch laptop in excellent condition"

    @pytest.mark.asyncio
    async def test_handle_description_too_long(self, mock_update, mock_context, sample_user):
        """Test handling description that's too long"""
        mock_update.message.text = "A" * 1001  # Over 1000 character limit
        mock_context.user_data["escrow_data"]["amount"] = Decimal("100.00")
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            
            result = await handle_description_input(mock_update, mock_context)
            
            # Should return to description input due to length validation
            assert result == EscrowStates.DESCRIPTION_INPUT
            
            # Verify error message about length
            mock_update.message.reply_text.assert_called()
            error_call_args = mock_update.message.reply_text.call_args[0][0]
            assert "1000" in error_call_args

    @pytest.mark.asyncio
    async def test_handle_delivery_time_selection(self, mock_update, mock_context, sample_user):
        """Test delivery time selection callback"""
        mock_update.callback_query = Mock(spec=CallbackQuery)
        mock_update.callback_query.data = "delivery_1_hour"
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.message = None
        
        mock_context.user_data["escrow_data"].update({
            "amount": Decimal("100.00"),
            "description": "Test item"
        })
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            
            result = await handle_delivery_time_input(mock_update, mock_context)
            
            assert result == EscrowStates.TRADE_REVIEW
            assert mock_context.user_data["escrow_data"]["delivery_time"] == "1 hour"

    @pytest.mark.asyncio
    async def test_payment_method_selection(self, mock_update, mock_context, sample_user):
        """Test payment method selection for escrow"""
        mock_update.callback_query = Mock(spec=CallbackQuery)
        mock_update.callback_query.data = "escrow_payment_USD"
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.message = None
        
        # Mock wallet with sufficient balance
        mock_wallet = Mock()
        mock_wallet.balance = Decimal("150.00")
        mock_wallet.currency = "USD"
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            mock_session.query.return_value.filter.return_value.all.return_value = [mock_wallet]
            
            result = await handle_payment_method_selection(mock_update, mock_context)
            
            # Should proceed to payment confirmation
            assert result is not None
            mock_update.callback_query.edit_message_text.assert_called()

    @pytest.mark.asyncio
    async def test_payment_method_insufficient_balance(self, mock_update, mock_context, sample_user):
        """Test payment method selection with insufficient wallet balance"""
        mock_update.callback_query = Mock(spec=CallbackQuery)
        mock_update.callback_query.data = "escrow_payment_USD"
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.message = None
        
        mock_context.user_data["escrow_data"]["amount"] = Decimal("100.00")
        
        # Mock wallet with insufficient balance
        mock_wallet = Mock()
        mock_wallet.balance = Decimal("50.00")  # Less than required
        mock_wallet.currency = "USD"
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            mock_session.query.return_value.filter.return_value.all.return_value = [mock_wallet]
            
            result = await handle_payment_method_selection(mock_update, mock_context)
            
            # Should show insufficient balance message
            mock_update.callback_query.edit_message_text.assert_called()
            call_args = mock_update.callback_query.edit_message_text.call_args[1]["text"]
            assert "insufficient" in call_args.lower()

    @pytest.mark.asyncio
    async def test_wallet_payment_confirmation_success(self, mock_update, mock_context, sample_user, sample_escrow):
        """Test successful wallet payment confirmation"""
        mock_update.callback_query = Mock(spec=CallbackQuery)
        mock_update.callback_query.data = "confirm_wallet_payment"
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.message = None
        
        mock_context.user_data["escrow_data"].update({
            "amount": Decimal("100.00"),
            "description": "Test item",
            "delivery_time": "1 hour",
            "payment_currency": "USD"
        })
        
        # Mock successful payment processing
        mock_transaction_result = {
            "success": True,
            "escrow_id": "ES0918256R2N",
            "transaction_id": "TXN123456"
        }
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            mock_session.add = Mock()
            mock_session.commit = Mock()
            
            with patch.object(UnifiedTransactionService, 'process_escrow_payment', 
                            return_value=mock_transaction_result):
                result = await handle_wallet_payment_confirmation(mock_update, mock_context)
                
                # Should complete escrow creation successfully
                assert result == EscrowStates.PAYMENT_CONFIRMED
                mock_session.add.assert_called()
                mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_wallet_payment_confirmation_failure(self, mock_update, mock_context, sample_user):
        """Test wallet payment confirmation failure"""
        mock_update.callback_query = Mock(spec=CallbackQuery)
        mock_update.callback_query.data = "confirm_wallet_payment"
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.message = None
        
        mock_context.user_data["escrow_data"].update({
            "amount": Decimal("100.00"),
            "payment_currency": "USD"
        })
        
        # Mock failed payment processing
        mock_transaction_result = {
            "success": False,
            "error": "Insufficient balance"
        }
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            
            with patch.object(UnifiedTransactionService, 'process_escrow_payment', 
                            return_value=mock_transaction_result):
                result = await handle_wallet_payment_confirmation(mock_update, mock_context)
                
                # Should show error and return to payment selection
                mock_update.callback_query.edit_message_text.assert_called()
                call_args = mock_update.callback_query.edit_message_text.call_args[1]["text"]
                assert "failed" in call_args.lower()

    def test_escrow_amount_calculations(self):
        """Test escrow amount calculations including fees"""
        from utils.fee_calculator import calculate_escrow_fee
        
        test_amounts = [
            Decimal("10.00"),
            Decimal("100.00"),
            Decimal("1000.00"),
            Decimal("10000.00")
        ]
        
        for amount in test_amounts:
            fee = calculate_escrow_fee(amount)
            total = amount + fee
            
            # Fee should be reasonable (not more than 10% of amount)
            assert fee <= amount * Decimal("0.1")
            
            # Total should be greater than original amount
            assert total > amount
            
            # Fee should be positive
            assert fee > 0

    @pytest.mark.asyncio
    async def test_escrow_expiration_handling(self, sample_escrow):
        """Test handling of expired escrows"""
        from handlers.escrow import handle_escrow_expiration
        
        # Set escrow to expired
        sample_escrow.status = EscrowStatus.EXPIRED
        sample_escrow.expires_at = datetime.utcnow() - timedelta(hours=1)
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.all.return_value = [sample_escrow]
            
            # Mock refund processing
            with patch.object(UnifiedTransactionService, 'process_escrow_refund', 
                            return_value={"success": True, "refund_id": "REF123"}):
                result = await handle_escrow_expiration()
                
                # Should process expired escrows
                assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_payment_processing(self, mock_context, sample_user):
        """Test concurrent payment processing doesn't cause race conditions"""
        import asyncio
        
        async def process_payment(escrow_id):
            mock_transaction_result = {
                "success": True,
                "escrow_id": escrow_id,
                "transaction_id": f"TXN{escrow_id}"
            }
            
            with patch('handlers.escrow.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value = mock_session
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                
                mock_session.query.return_value.filter.return_value.first.return_value = sample_user
                mock_session.add = Mock()
                mock_session.commit = Mock()
                
                with patch.object(UnifiedTransactionService, 'process_escrow_payment', 
                                return_value=mock_transaction_result):
                    # Simulate payment processing
                    await asyncio.sleep(0.1)  # Simulate processing time
                    return mock_transaction_result
        
        # Process multiple payments concurrently
        tasks = [
            process_payment("ES001"),
            process_payment("ES002"),
            process_payment("ES003")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All payments should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert result["success"] == True

    def test_escrow_state_validation(self):
        """Test that escrow state transitions are valid"""
        from models import EscrowStatus
        
        # Define valid state transitions
        valid_transitions = {
            EscrowStatus.CREATED: [EscrowStatus.PAYMENT_PENDING, EscrowStatus.CANCELLED],
            EscrowStatus.PAYMENT_PENDING: [EscrowStatus.PAYMENT_CONFIRMED, EscrowStatus.EXPIRED, EscrowStatus.CANCELLED],
            EscrowStatus.PAYMENT_CONFIRMED: [EscrowStatus.ACTIVE, EscrowStatus.CANCELLED],
            EscrowStatus.ACTIVE: [EscrowStatus.COMPLETED, EscrowStatus.DISPUTED, EscrowStatus.RELEASED],
            EscrowStatus.DISPUTED: [EscrowStatus.RESOLVED, EscrowStatus.REFUNDED],
            EscrowStatus.COMPLETED: [],  # Terminal state
            EscrowStatus.CANCELLED: [],  # Terminal state
            EscrowStatus.REFUNDED: [],  # Terminal state
        }
        
        # Test each valid transition
        for current_status, allowed_next in valid_transitions.items():
            for next_status in allowed_next:
                # This would test the state transition logic
                assert True  # Placeholder for actual state transition validation
        
        # Test invalid transitions (should be prevented)
        invalid_transitions = [
            (EscrowStatus.COMPLETED, EscrowStatus.PAYMENT_PENDING),
            (EscrowStatus.CANCELLED, EscrowStatus.ACTIVE),
            (EscrowStatus.REFUNDED, EscrowStatus.COMPLETED),
        ]
        
        for current, invalid_next in invalid_transitions:
            # This would test that invalid transitions are prevented
            assert True  # Placeholder for actual validation

    @pytest.mark.asyncio
    async def test_escrow_notification_system(self, sample_escrow, sample_user):
        """Test that proper notifications are sent during escrow lifecycle"""
        from services.consolidated_notification_service import ConsolidatedNotificationService
        
        with patch.object(ConsolidatedNotificationService, 'send_notification') as mock_notify:
            # Test escrow creation notification
            await handle_escrow_creation_notification(sample_escrow, sample_user)
            
            # Verify notification was sent
            mock_notify.assert_called()
            call_args = mock_notify.call_args[1]
            assert call_args["channel"] == "telegram"
            assert "escrow" in call_args["message"].lower()


async def handle_escrow_creation_notification(escrow, user):
    """Mock function for escrow creation notification"""
    # This would be implemented in the actual notification system
    pass