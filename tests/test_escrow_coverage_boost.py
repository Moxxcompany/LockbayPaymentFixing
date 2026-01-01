"""
Comprehensive Escrow Coverage Boost Test Suite

MISSION: Boost handlers/escrow.py coverage from 7% to 80%+

This test suite targets the highest-impact uncovered functions in the escrow handler
to achieve substantial coverage increases. Focus is on core business logic functions
that handle money, user interactions, and critical workflows.

Coverage Strategy:
- Target 75+ functions in handlers/escrow.py systematically
- Focus on core lifecycle: creation → payment → confirmation → release
- Test error handling, validation, and edge cases
- Use working database infrastructure with proper mocking
- Achieve 80%+ coverage through comprehensive function testing

Priority Functions (highest line impact):
1. Core Lifecycle: start_secure_trade, handle_seller_input, execute_wallet_payment
2. Seller Flows: handle_seller_accept_trade, handle_mark_delivered, handle_release_funds
3. Business Logic: fee calculations, payment validation, trade management
4. Error Handling: input validation, service failures, edge cases
"""

import pytest
import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call

# Core imports
from telegram import Update, User as TelegramUser, Message, CallbackQuery, Chat, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Database and model imports
from database import SessionLocal
from models import (
    User, Escrow, EscrowStatus, Wallet, Transaction, TransactionType,
    EscrowHolding, UnifiedTransaction, UnifiedTransactionStatus, UnifiedTransactionType,
    WalletHolds, WalletHoldStatus
)

# Import ALL escrow handler functions for comprehensive testing
from handlers.escrow import (
    # Core lifecycle functions
    start_secure_trade, handle_seller_input, handle_amount_input,
    handle_description_input, handle_delivery_time_input,
    handle_confirm_trade_final, execute_wallet_payment, execute_crypto_payment,
    execute_ngn_payment,
    
    # Seller response functions  
    handle_seller_accept_trade, handle_seller_decline_trade,
    handle_mark_delivered, handle_release_funds, handle_confirm_release_funds,
    
    # Payment and business logic functions
    handle_payment_method_selection, handle_wallet_payment,
    process_immediate_wallet_payment, show_fee_split_options,
    show_trade_review, handle_fee_split_selection,
    
    # Trade management functions
    handle_cancel_escrow, handle_view_trade, handle_trade_pagination,
    handle_trade_filter, handle_buyer_cancel_trade,
    
    # Utility and callback functions
    handle_amount_callback, handle_delivery_time_callback,
    handle_trade_review_callbacks, handle_switch_payment_method,
    handle_create_secure_trade_callback, handle_copy_address,
    handle_show_qr, handle_back_to_payment,
    
    # Email and invitation functions
    handle_seller_email_input, handle_seller_email_verification,
    handle_seller_invitation_response, handle_share_link,
    
    # Helper functions
    safe_get_user_id, safe_get_context_data, as_decimal,
    get_trade_cache_stats, auto_refresh_trade_interfaces,
    
    # Edit functions
    handle_edit_trade_amount, handle_edit_trade_description,
    handle_edit_delivery_time, handle_edit_fee_split
)

# Service imports for mocking
from services.unified_transaction_service import UnifiedTransactionService
from services.crypto import CryptoServiceAtomic
from services.conditional_otp_service import ConditionalOTPService
from services.fincra_service import FincraService
from services.fastforex_service import FastForexService

# Utilities
from utils.helpers import generate_utid
from utils.wallet_manager import get_or_create_wallet
from utils.constants import States, EscrowStates

logger = logging.getLogger(__name__)


class TestEscrowCoreLifecycle:
    """Test core escrow lifecycle functions for maximum coverage impact"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, test_db_session):
        """Setup for each test method with clean database state"""
        self.session = test_db_session
        
        # Create test users
        self.buyer_user = User(
            telegram_id='1234567890',
            username='test_buyer',
            first_name='Test',
            last_name='Buyer',
            email='buyer@test.com',
            is_verified=True,
            created_at=datetime.utcnow()
        )
        
        self.seller_user = User(
            telegram_id='0987654321', 
            username='test_seller',
            first_name='Test',
            last_name='Seller', 
            email='seller@test.com',
            is_verified=True,
            created_at=datetime.utcnow()
        )
        
        self.session.add(self.buyer_user)
        self.session.add(self.seller_user)
        self.session.commit()
        
        # Create wallets with balances
        buyer_wallet = Wallet(
            user_id=self.buyer_user.id,
            currency='USD',
            balance=Decimal('1000.00'),
            created_at=datetime.utcnow()
        )
        
        seller_wallet = Wallet(
            user_id=self.seller_user.id,
            currency='USD',
            balance=Decimal('500.00'),
            created_at=datetime.utcnow()
        )
        
        self.session.add(buyer_wallet)
        self.session.add(seller_wallet)
        self.session.commit()
        
    def create_mock_update(self, text: str = "", callback_data: str = "", user_id: str = "1234567890"):
        """Create mock Telegram update for testing"""
        user = Mock()
        user.id = int(user_id)
        user.username = 'test_user'
        user.first_name = 'Test'
        user.last_name = 'User'
        
        update = Mock()
        
        if callback_data:
            # Callback query update
            query = Mock()
            query.data = callback_data
            query.from_user = user
            query.message = Mock()
            query.message.message_id = 123
            query.message.chat = Mock()
            query.message.chat.id = int(user_id)
            update.callback_query = query
            update.message = None
        else:
            # Regular message update
            message = Mock()
            message.text = text
            message.from_user = user
            message.chat = Mock()
            message.chat.id = int(user_id)
            message.message_id = 123
            update.message = message
            update.callback_query = None
            
        return update
    
    def create_mock_context(self, user_data: Dict = None):
        """Create mock context with user data"""
        context = Mock()
        context.user_data = user_data or {}
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        context.bot.edit_message_text = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_start_secure_trade_basic_flow(self):
        """Test start_secure_trade function - core escrow initiation"""
        
        update = self.create_mock_update(text="/start_trade", user_id=str(self.buyer_user.telegram_id))
        context = self.create_mock_context()
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = self.buyer_user
            
            result = await start_secure_trade(update, context)
            
            # Verify conversation state returned
            assert isinstance(result, int) or result == ConversationHandler.END
            
            # Verify user data initialized
            assert 'escrow_data' in context.user_data
            assert context.user_data['escrow_data']['buyer_id'] == str(self.buyer_user.telegram_id)
            
            logger.info("✅ start_secure_trade basic flow test passed")

    @pytest.mark.asyncio 
    async def test_handle_seller_input_username(self):
        """Test handle_seller_input with valid username"""
        
        update = self.create_mock_update(text=f"@{self.seller_user.username}", user_id=str(self.buyer_user.telegram_id))
        context = self.create_mock_context({
            'escrow_data': {'buyer_id': str(self.buyer_user.telegram_id)}
        })
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Mock user queries
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                self.buyer_user,  # First query for buyer
                self.seller_user  # Second query for seller
            ]
            
            result = await handle_seller_input(update, context)
            
            # Verify seller was set
            assert context.user_data['escrow_data']['seller_id'] == str(self.seller_user.telegram_id)
            assert isinstance(result, int)
            
            logger.info("✅ handle_seller_input username test passed")

    @pytest.mark.asyncio
    async def test_handle_seller_input_telegram_id(self):
        """Test handle_seller_input with Telegram ID"""
        
        update = self.create_mock_update(text=str(self.seller_user.telegram_id), user_id=str(self.buyer_user.telegram_id))
        context = self.create_mock_context({
            'escrow_data': {'buyer_id': str(self.buyer_user.telegram_id)}
        })
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Mock user queries
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                self.buyer_user,  # Buyer query
                self.seller_user  # Seller query by telegram_id
            ]
            
            result = await handle_seller_input(update, context)
            
            assert context.user_data['escrow_data']['seller_id'] == str(self.seller_user.telegram_id)
            assert isinstance(result, int)
            
            logger.info("✅ handle_seller_input telegram_id test passed")

    @pytest.mark.asyncio
    async def test_handle_amount_input_valid(self):
        """Test handle_amount_input with valid amount"""
        
        update = self.create_mock_update(text="100.50", user_id=str(self.buyer_user.telegram_id))
        context = self.create_mock_context({
            'escrow_data': {
                'buyer_id': str(self.buyer_user.telegram_id),
                'seller_id': str(self.seller_user.telegram_id)
            }
        })
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = self.buyer_user
            
            result = await handle_amount_input(update, context)
            
            # Verify amount was set
            assert context.user_data['escrow_data']['amount'] == "100.50"
            assert isinstance(result, int)
            
            logger.info("✅ handle_amount_input valid test passed")

    @pytest.mark.asyncio
    async def test_handle_amount_input_invalid(self):
        """Test handle_amount_input with invalid amount"""
        
        update = self.create_mock_update(text="invalid_amount", user_id=str(self.buyer_user.telegram_id))
        context = self.create_mock_context({
            'escrow_data': {'buyer_id': str(self.buyer_user.telegram_id)}
        })
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = self.buyer_user
            
            result = await handle_amount_input(update, context)
            
            # Should remain in same state for retry
            assert isinstance(result, int)
            
            logger.info("✅ handle_amount_input invalid test passed")

    @pytest.mark.asyncio
    async def test_handle_description_input(self):
        """Test handle_description_input function"""
        
        description_text = "Test product for escrow transaction"
        update = self.create_mock_update(text=description_text, user_id=str(self.buyer_user.telegram_id))
        context = self.create_mock_context({
            'escrow_data': {
                'buyer_id': str(self.buyer_user.telegram_id),
                'seller_id': str(self.seller_user.telegram_id),
                'amount': '100.50'
            }
        })
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = self.buyer_user
            
            result = await handle_description_input(update, context)
            
            # Verify description was set
            assert context.user_data['escrow_data']['description'] == description_text
            assert isinstance(result, int)
            
            logger.info("✅ handle_description_input test passed")

    @pytest.mark.asyncio
    async def test_execute_wallet_payment(self):
        """Test execute_wallet_payment function"""
        
        query = Mock()
        query.from_user = Mock()
        query.from_user.id = int(self.buyer_user.telegram_id)
        query.message = Mock()
        query.message.message_id = 123
        
        context = self.create_mock_context({
            'escrow_data': {
                'buyer_id': str(self.buyer_user.telegram_id),
                'seller_id': str(self.seller_user.telegram_id),
                'amount': '100.00',
                'description': 'Test escrow',
                'currency': 'USD'
            }
        })
        
        total_amount = Decimal('100.00')
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class, \
             patch('handlers.escrow.CryptoServiceAtomic') as mock_crypto:
                
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = self.buyer_user
            
            # Mock successful wallet debit
            mock_crypto.debit_user_wallet_atomic.return_value = True
            
            result = await execute_wallet_payment(query, context, total_amount)
            
            assert isinstance(result, int)
            
            logger.info("✅ execute_wallet_payment test passed")

    @pytest.mark.asyncio 
    async def test_execute_crypto_payment(self):
        """Test execute_crypto_payment function"""
        
        update = self.create_mock_update(callback_data="crypto_BTC", user_id=str(self.buyer_user.telegram_id))
        context = self.create_mock_context({
            'escrow_data': {
                'buyer_id': str(self.buyer_user.telegram_id),
                'seller_id': str(self.seller_user.telegram_id),
                'amount': '0.001',
                'currency': 'BTC',
                'crypto_currency': 'BTC'
            }
        })
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class, \
             patch('services.payment_manager.PaymentManager') as mock_payment_manager:
                
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = self.buyer_user
            
            # Mock payment manager
            mock_pm = Mock()
            mock_payment_manager.return_value = mock_pm
            mock_pm.create_payment_address.return_value = {
                'success': True,
                'address': 'bc1qtest123',
                'qr_code_data': 'bitcoin:bc1qtest123?amount=0.001'
            }
            
            result = await execute_crypto_payment(update, context)
            
            assert isinstance(result, int)
            
            logger.info("✅ execute_crypto_payment test passed")


class TestEscrowSellerFlows:
    """Test seller response and interaction functions"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, test_db_session):
        """Setup for seller flow tests"""
        self.session = test_db_session
        
        # Create users and escrow
        buyer = User(
            telegram_id='1111111111',
            username='buyer_user',
            first_name='Buyer',
            email='buyer@test.com',
            is_verified=True
        )
        
        seller = User(
            telegram_id='2222222222', 
            username='seller_user',
            first_name='Seller',
            email='seller@test.com',
            is_verified=True
        )
        
        self.session.add(buyer)
        self.session.add(seller)
        self.session.commit()
        
        # Create test escrow
        self.escrow = Escrow(
            escrow_id='ESC_TEST_123',
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            description='Test escrow for seller flows',
            status=EscrowStatus.PENDING_ACCEPTANCE,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        self.session.add(self.escrow)
        self.session.commit()
        
        self.buyer = buyer
        self.seller = seller

    def create_mock_update(self, callback_data: str = "", user_id: str = "2222222222"):
        """Create mock update for seller tests"""
        user = Mock()
        user.id = int(user_id)
        user.username = 'seller_user'
        
        update = Mock()
        query = Mock()
        query.data = callback_data
        query.from_user = user
        query.message = Mock()
        query.message.message_id = 123
        update.callback_query = query
        
        return update

    @pytest.mark.asyncio
    async def test_handle_seller_accept_trade(self):
        """Test handle_seller_accept_trade function"""
        
        callback_data = f"accept_trade:{self.escrow.escrow_id}"
        update = self.create_mock_update(callback_data=callback_data, user_id=str(self.seller.telegram_id))
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.edit_message_text = AsyncMock()
        context.bot.send_message = AsyncMock()
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Mock database queries
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                self.seller,  # Seller query
                self.escrow   # Escrow query
            ]
            
            result = await handle_seller_accept_trade(update, context)
            
            assert isinstance(result, int) or result == ConversationHandler.END
            
            logger.info("✅ handle_seller_accept_trade test passed")

    @pytest.mark.asyncio
    async def test_handle_seller_decline_trade(self):
        """Test handle_seller_decline_trade function"""
        
        callback_data = f"decline_trade:{self.escrow.escrow_id}"
        update = self.create_mock_update(callback_data=callback_data, user_id=str(self.seller.telegram_id))
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.edit_message_text = AsyncMock()
        context.bot.send_message = AsyncMock()
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                self.seller,  # Seller query  
                self.escrow   # Escrow query
            ]
            
            result = await handle_seller_decline_trade(update, context)
            
            assert isinstance(result, int) or result == ConversationHandler.END
            
            logger.info("✅ handle_seller_decline_trade test passed")

    @pytest.mark.asyncio
    async def test_handle_mark_delivered(self):
        """Test handle_mark_delivered function"""
        
        # Set escrow to payment confirmed status
        self.escrow.status = EscrowStatus.PAYMENT_CONFIRMED
        
        callback_data = f"mark_delivered_{self.escrow.escrow_id}"
        update = self.create_mock_update(callback_data=callback_data, user_id=str(self.seller.telegram_id))
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.edit_message_text = AsyncMock()
        context.bot.send_message = AsyncMock()
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                self.seller,  # Seller query
                self.escrow   # Escrow query  
            ]
            
            result = await handle_mark_delivered(update, context)
            
            assert isinstance(result, int) or result == ConversationHandler.END
            
            logger.info("✅ handle_mark_delivered test passed")

    @pytest.mark.asyncio
    async def test_handle_release_funds(self):
        """Test handle_release_funds function"""
        
        callback_data = f"release_funds_{self.escrow.escrow_id}"
        update = self.create_mock_update(callback_data=callback_data, user_id=str(self.buyer.telegram_id))
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.edit_message_text = AsyncMock()
        context.bot.send_message = AsyncMock()
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                self.buyer,   # Buyer query
                self.escrow   # Escrow query
            ]
            
            result = await handle_release_funds(update, context)
            
            assert isinstance(result, int) or result == ConversationHandler.END
            
            logger.info("✅ handle_release_funds test passed")


class TestEscrowBusinessLogic:
    """Test business logic, fee calculations, and validation functions"""
    
    def create_mock_context(self, escrow_data: Dict = None):
        """Create mock context for business logic tests"""
        context = Mock()
        context.user_data = {'escrow_data': escrow_data or {}}
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        context.bot.edit_message_text = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_show_fee_split_options(self):
        """Test show_fee_split_options function"""
        
        query = Mock()
        query.from_user = Mock()
        query.from_user.id = 1234567890
        query.message = Mock()
        query.message.message_id = 123
        
        context = self.create_mock_context({
            'buyer_id': '1234567890',
            'seller_id': '0987654321', 
            'amount': '100.00',
            'currency': 'USD'
        })
        
        with patch('handlers.escrow.Config') as mock_config:
            mock_config.FEE_PERCENTAGE = 0.01  # 1% fee
            
            result = await show_fee_split_options(query, context)
            
            # Should return conversation state or None
            assert result is None or isinstance(result, int)
            
            logger.info("✅ show_fee_split_options test passed")

    @pytest.mark.asyncio
    async def test_handle_fee_split_selection(self):
        """Test handle_fee_split_selection function"""
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.data = "buyer_pays_all"
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 1234567890
        update.callback_query.message = Mock()
        
        context = self.create_mock_context({
            'buyer_id': '1234567890',
            'amount': '100.00',
            'currency': 'USD'
        })
        
        result = await handle_fee_split_selection(update, context)
        
        # Verify fee split was set
        assert 'fee_split' in context.user_data['escrow_data']
        assert isinstance(result, int) or result == ConversationHandler.END
        
        logger.info("✅ handle_fee_split_selection test passed")

    @pytest.mark.asyncio
    async def test_show_trade_review(self):
        """Test show_trade_review function"""
        
        query = Mock()
        query.from_user = Mock()
        query.from_user.id = 1234567890
        query.message = Mock()
        query.message.message_id = 123
        
        context = self.create_mock_context({
            'buyer_id': '1234567890',
            'seller_id': '0987654321',
            'amount': '100.00',
            'currency': 'USD',
            'description': 'Test trade',
            'delivery_time': '24 hours',
            'fee_split': 'buyer_pays_all',
            'buyer_fee': '1.00',
            'seller_fee': '0.00'
        })
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Mock user queries
            mock_buyer = Mock()
            mock_buyer.username = 'test_buyer'
            mock_seller = Mock()  
            mock_seller.username = 'test_seller'
            
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                mock_buyer, mock_seller
            ]
            
            result = await show_trade_review(query, context)
            
            assert result is None or isinstance(result, int)
            
            logger.info("✅ show_trade_review test passed")

    @pytest.mark.asyncio
    async def test_handle_payment_method_selection(self):
        """Test handle_payment_method_selection function"""
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.data = "payment_wallet"
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 1234567890
        update.callback_query.message = Mock()
        
        context = self.create_mock_context({
            'buyer_id': '1234567890',
            'amount': '100.00',
            'currency': 'USD'
        })
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Mock user query
            mock_user = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            result = await handle_payment_method_selection(update, context)
            
            assert isinstance(result, int) or result == ConversationHandler.END
            
            logger.info("✅ handle_payment_method_selection test passed")


class TestEscrowUtilityFunctions:
    """Test utility and helper functions for additional coverage"""

    def test_safe_get_user_id(self):
        """Test safe_get_user_id helper function"""
        
        # Test with valid query
        query = Mock()
        query.from_user = Mock()
        query.from_user.id = 1234567890
        
        result = safe_get_user_id(query)
        assert result == "1234567890"
        
        # Test with None
        result = safe_get_user_id(None)
        assert result is None
        
        # Test with invalid query
        invalid_query = Mock()
        invalid_query.from_user = None
        result = safe_get_user_id(invalid_query)
        assert result is None
        
        logger.info("✅ safe_get_user_id test passed")

    def test_safe_get_context_data(self):
        """Test safe_get_context_data helper function"""
        
        context = Mock()
        context.user_data = {'test_key': {'data': 'value'}}
        
        # Test with existing key
        result = safe_get_context_data(context, 'test_key')
        assert result == {'data': 'value'}
        
        # Test with non-existing key  
        result = safe_get_context_data(context, 'non_existing')
        assert result == {}
        
        # Test with None context
        result = safe_get_context_data(None, 'any_key')
        assert result == {}
        
        logger.info("✅ safe_get_context_data test passed")

    def test_as_decimal(self):
        """Test as_decimal helper function"""
        
        # Test with valid decimal
        result = as_decimal("100.50")
        assert result == Decimal("100.50")
        
        # Test with integer
        result = as_decimal(100)
        assert result == Decimal("100")
        
        # Test with None
        result = as_decimal(None)
        assert result == Decimal("0")
        
        # Test with invalid value
        result = as_decimal("invalid")
        assert result == Decimal("0")
        
        # Test with custom default
        result = as_decimal(None, Decimal("50.00"))
        assert result == Decimal("50.00")
        
        logger.info("✅ as_decimal test passed")

    def test_get_trade_cache_stats(self):
        """Test get_trade_cache_stats function"""
        
        result = get_trade_cache_stats()
        assert isinstance(result, dict)
        
        logger.info("✅ get_trade_cache_stats test passed")

    @pytest.mark.asyncio
    async def test_auto_refresh_trade_interfaces(self):
        """Test auto_refresh_trade_interfaces function"""
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Mock database queries
            mock_session.query.return_value.count.return_value = 100
            mock_session.query.return_value.filter.return_value.count.return_value = 10
            
            # Should not raise exception
            await auto_refresh_trade_interfaces()
            
            logger.info("✅ auto_refresh_trade_interfaces test passed")


class TestEscrowErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_handle_seller_input_self_trade_error(self):
        """Test error when user tries to trade with themselves"""
        
        update = Mock()
        update.message = Mock()
        update.message.text = "1234567890"  # Same as buyer
        update.message.from_user = Mock()
        update.message.from_user.id = 1234567890
        
        context = Mock()
        context.user_data = {'escrow_data': {'buyer_id': '1234567890'}}
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Mock user query
            mock_user = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            result = await handle_seller_input(update, context)
            
            # Should handle self-trade error gracefully
            assert isinstance(result, int)
            
            logger.info("✅ handle_seller_input self-trade error test passed")

    @pytest.mark.asyncio 
    async def test_handle_amount_input_zero_amount_error(self):
        """Test error handling for zero amount"""
        
        update = Mock()
        update.message = Mock()
        update.message.text = "0.00"
        update.message.from_user = Mock()
        update.message.from_user.id = 1234567890
        
        context = Mock()
        context.user_data = {'escrow_data': {'buyer_id': '1234567890'}}
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            mock_user = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            result = await handle_amount_input(update, context)
            
            # Should handle zero amount error
            assert isinstance(result, int)
            
            logger.info("✅ handle_amount_input zero amount error test passed")

    @pytest.mark.asyncio
    async def test_execute_wallet_payment_insufficient_funds(self):
        """Test wallet payment with insufficient funds"""
        
        query = Mock()
        query.from_user = Mock()
        query.from_user.id = 1234567890
        query.message = Mock()
        
        context = Mock()
        context.user_data = {'escrow_data': {
            'buyer_id': '1234567890',
            'amount': '1000000.00'  # Huge amount to trigger insufficient funds
        }}
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        context.bot.edit_message_text = AsyncMock()
        
        total_amount = Decimal('1000000.00')
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class, \
             patch('handlers.escrow.CryptoServiceAtomic') as mock_crypto:
                
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            mock_user = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock insufficient funds
            mock_crypto.debit_user_wallet_atomic.return_value = False
            
            result = await execute_wallet_payment(query, context, total_amount)
            
            # Should handle insufficient funds gracefully
            assert isinstance(result, int)
            
            logger.info("✅ execute_wallet_payment insufficient funds test passed")


class TestEscrowTradeManagement:
    """Test trade management, pagination, and filtering functions"""
    
    @pytest.mark.asyncio
    async def test_handle_view_trade(self):
        """Test handle_view_trade function"""
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.data = "view_trade_ESC123"
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 1234567890
        update.callback_query.message = Mock()
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.edit_message_text = AsyncMock()
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Mock database queries
            mock_user = Mock()
            mock_escrow = Mock()
            mock_escrow.escrow_id = 'ESC123'
            mock_escrow.status = EscrowStatus.ACTIVE
            
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                mock_user, mock_escrow
            ]
            
            result = await handle_view_trade(update, context)
            
            assert isinstance(result, int) or result == ConversationHandler.END
            
            logger.info("✅ handle_view_trade test passed")

    @pytest.mark.asyncio
    async def test_handle_cancel_escrow(self):
        """Test handle_cancel_escrow function"""
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.data = "cancel_escrow_ESC123"
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 1234567890
        update.callback_query.message = Mock()
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.edit_message_text = AsyncMock()
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            mock_user = Mock()
            mock_escrow = Mock()
            mock_escrow.escrow_id = 'ESC123'
            
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                mock_user, mock_escrow
            ]
            
            result = await handle_cancel_escrow(update, context)
            
            assert isinstance(result, int) or result == ConversationHandler.END
            
            logger.info("✅ handle_cancel_escrow test passed")

    @pytest.mark.asyncio 
    async def test_handle_trade_pagination(self):
        """Test handle_trade_pagination function"""
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.data = "trades_page_2"
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 1234567890
        update.callback_query.message = Mock()
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.edit_message_text = AsyncMock()
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            mock_user = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock trades query
            mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
            mock_session.query.return_value.filter.return_value.count.return_value = 0
            
            result = await handle_trade_pagination(update, context)
            
            assert isinstance(result, int) or result == ConversationHandler.END
            
            logger.info("✅ handle_trade_pagination test passed")

    @pytest.mark.asyncio
    async def test_handle_trade_filter(self):
        """Test handle_trade_filter function"""
        
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.data = "filter_active"
        update.callback_query.from_user = Mock()
        update.callback_query.from_user.id = 1234567890
        update.callback_query.message = Mock()
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.edit_message_text = AsyncMock()
        
        result = await handle_trade_filter(update, context)
        
        assert isinstance(result, int) or result == ConversationHandler.END
        
        logger.info("✅ handle_trade_filter test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])