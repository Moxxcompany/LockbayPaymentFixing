"""
Comprehensive test suite for escrow creation flow
Tests username validation, user lookup, database operations, and state transitions
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

# Telegram test imports
from telegram import Update, Message, User as TelegramUser, Chat
from telegram.ext import ContextTypes

# Local imports
from handlers.escrow import handle_seller_input, start_secure_trade
from handlers.escrow_direct import route_text_message_to_escrow_flow
from services.fast_seller_lookup_service import FastSellerLookupService, FastSellerProfile
from models import User, Escrow, EscrowStatus
from database import SessionLocal
from utils.constants import EscrowStates
from config import Config


class TestEscrowCreationFlow:
    """Test suite for escrow creation workflow"""

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram update object"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=TelegramUser)
        update.effective_user.id = 5590563715
        update.effective_user.username = "testuser"
        update.message = Mock(spec=Message)
        update.message.text = "@onarrival1"
        update.message.reply_text = AsyncMock()
        update.message.delete = AsyncMock()
        update.callback_query = None
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock context object"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {
            "escrow_data": {
                "early_escrow_id": "ES0918256R2N",
                "status": "creating"
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
            last_name="User",
            email="test@example.com",
            created_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_seller_user(self):
        """Create a sample seller user for testing"""
        return User(
            id=2,
            telegram_id="1234567890",
            username="onarrival1",
            first_name="Seller",
            last_name="User",
            email="seller@example.com",
            created_at=datetime.utcnow()
        )

    @pytest.mark.asyncio
    async def test_handle_seller_input_valid_username(self, mock_update, mock_context, sample_user, sample_seller_user):
        """Test handling valid Telegram username input"""
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            # Mock user queries
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                sample_user,  # First query for buyer user
                sample_seller_user  # Second query for seller lookup
            ]
            
            # Mock fast seller lookup
            mock_seller_profile = FastSellerProfile(
                user_id=2,
                username="onarrival1",
                display_name="Seller User",
                exists_on_platform=True,
                basic_rating=4.5,
                total_ratings=10,
                trust_level="silver",
                last_active="Recently",
                is_verified=True,
                warning_flags=[]
            )
            
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=mock_seller_profile):
                result = await handle_seller_input(mock_update, mock_context)
                
                # Assertions
                assert result == EscrowStates.AMOUNT_INPUT
                assert mock_context.user_data["escrow_data"]["seller_type"] == "username"
                assert mock_context.user_data["escrow_data"]["seller_identifier"] == "onarrival1"
                assert mock_context.user_data["escrow_data"]["seller_profile"]["user_id"] == 2
                
                # Verify immediate feedback was provided
                mock_update.message.reply_text.assert_called()
                feedback_text = mock_update.message.reply_text.call_args[0][0]
                assert "Processing seller details" in feedback_text

    @pytest.mark.asyncio
    async def test_handle_seller_input_invalid_username(self, mock_update, mock_context, sample_user):
        """Test handling invalid username format"""
        mock_update.message.text = "invalid_username"  # No @ symbol
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            
            result = await handle_seller_input(mock_update, mock_context)
            
            # Should return to seller input state due to validation error
            assert result == EscrowStates.SELLER_INPUT
            
            # Verify error message was sent
            mock_update.message.reply_text.assert_called()
            error_call = [call for call in mock_update.message.reply_text.call_args_list 
                         if "❌" in str(call)]
            assert len(error_call) > 0

    @pytest.mark.asyncio
    async def test_handle_seller_input_valid_email(self, mock_update, mock_context, sample_user):
        """Test handling valid email input"""
        mock_update.message.text = "seller@example.com"
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            
            # Mock seller not found on platform
            mock_seller_profile = FastSellerProfile(
                user_id=None,
                username="seller@example.com",
                display_name="seller@example.com",
                exists_on_platform=False,
                basic_rating=None,
                total_ratings=0,
                trust_level="new",
                last_active=None,
                is_verified=False,
                warning_flags=[]
            )
            
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=mock_seller_profile):
                result = await handle_seller_input(mock_update, mock_context)
                
                assert result == EscrowStates.AMOUNT_INPUT
                assert mock_context.user_data["escrow_data"]["seller_type"] == "email"
                assert mock_context.user_data["escrow_data"]["seller_identifier"] == "seller@example.com"

    @pytest.mark.asyncio
    async def test_handle_seller_input_self_trading_prevention(self, mock_update, mock_context, sample_user):
        """Test prevention of self-trading"""
        mock_update.message.text = "@testuser"  # Same as buyer username
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            
            # Mock seller profile for same user
            mock_seller_profile = FastSellerProfile(
                user_id=1,  # Same as buyer
                username="testuser",
                display_name="Test User",
                exists_on_platform=True,
                basic_rating=None,
                total_ratings=0,
                trust_level="new",
                last_active="Recently",
                is_verified=False,
                warning_flags=[]
            )
            
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=mock_seller_profile):
                result = await handle_seller_input(mock_update, mock_context)
                
                # Should return to seller input due to self-trading prevention
                assert result == EscrowStates.SELLER_INPUT
                
                # Verify self-trading error message
                mock_update.message.reply_text.assert_called()
                error_call_args = mock_update.message.reply_text.call_args[0][0]
                assert "Can't trade with yourself" in error_call_args

    @pytest.mark.asyncio
    async def test_handle_seller_input_phone_number(self, mock_update, mock_context, sample_user):
        """Test handling phone number input"""
        mock_update.message.text = "+1234567890"
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_session.query.return_value.filter.return_value.first.return_value = sample_user
            
            # Mock seller invitation service for phone
            mock_seller_info = {
                'type': 'phone',
                'seller_identifier': '+1234567890',
                'display_name': '+1234567890'
            }
            
            with patch('services.seller_invitation.SellerInvitationService._process_phone_seller', 
                      return_value=mock_seller_info):
                # Mock seller profile for phone
                mock_seller_profile = FastSellerProfile(
                    user_id=None,
                    username="+1234567890",
                    display_name="+1234567890",
                    exists_on_platform=False,
                    basic_rating=None,
                    total_ratings=0,
                    trust_level="new",
                    last_active=None,
                    is_verified=False,
                    warning_flags=[]
                )
                
                with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=mock_seller_profile):
                    result = await handle_seller_input(mock_update, mock_context)
                    
                    assert result == EscrowStates.AMOUNT_INPUT
                    assert mock_context.user_data["escrow_data"]["seller_type"] == "phone"
                    assert mock_context.user_data["escrow_data"]["seller_identifier"] == "+1234567890"

    @pytest.mark.asyncio
    async def test_fast_seller_lookup_performance(self):
        """Test that fast seller lookup performs within acceptable time limits"""
        import time
        
        with patch('services.fast_seller_lookup_service.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            # Mock optimized database queries
            mock_user = Mock()
            mock_user.id = 2
            mock_user.username = "onarrival1"
            mock_user.first_name = "Seller"
            mock_user.email = "seller@example.com"
            mock_user.phone_number = "+1234567890"
            
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock rating stats query
            mock_rating_stats = Mock()
            mock_rating_stats.avg_rating = 4.5
            mock_rating_stats.total_ratings = 10
            mock_session.query.return_value.filter.return_value.first.return_value = mock_rating_stats
            
            # Mock recent activity check
            mock_session.query.return_value.scalar.return_value = True
            
            start_time = time.time()
            result = FastSellerLookupService.get_seller_profile_fast("onarrival1", "username")
            end_time = time.time()
            
            # Performance assertion: should complete in under 100ms
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            assert execution_time < 100, f"Fast lookup took {execution_time}ms, should be under 100ms"
            
            # Verify result structure
            assert result is not None
            assert result.username == "onarrival1"
            assert result.exists_on_platform == True

    @pytest.mark.asyncio
    async def test_escrow_state_transitions(self, mock_update, mock_context, sample_user):
        """Test proper state transitions during escrow creation"""
        with patch('handlers.escrow_direct.set_user_state') as mock_set_state:
            with patch('handlers.escrow_direct.get_user_state', return_value="seller_input"):
                with patch('handlers.escrow.handle_seller_input', return_value=True) as mock_handler:
                    
                    # Test routing to seller input handler
                    result = await route_text_message_to_escrow_flow(mock_update, mock_context)
                    
                    assert result == True
                    mock_handler.assert_called_once()
                    
                    # Verify state transition to amount_input
                    mock_set_state.assert_called_with(mock_update.effective_user.id, "amount_input")

    @pytest.mark.asyncio
    async def test_database_error_handling(self, mock_update, mock_context):
        """Test graceful handling of database errors"""
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            # Simulate database connection error
            mock_session_class.side_effect = Exception("Database connection failed")
            
            result = await handle_seller_input(mock_update, mock_context)
            
            # Should handle error gracefully and return to seller input
            assert result == EscrowStates.SELLER_INPUT
            
            # Verify error message was sent to user
            mock_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_concurrent_escrow_creation(self, sample_user):
        """Test handling of concurrent escrow creation attempts"""
        # This test would verify that multiple users can create escrows simultaneously
        # without race conditions or data corruption
        
        async def create_escrow(user_id, seller_name):
            mock_update = Mock(spec=Update)
            mock_update.effective_user = Mock(spec=TelegramUser)
            mock_update.effective_user.id = user_id
            mock_update.message = Mock(spec=Message)
            mock_update.message.text = f"@{seller_name}"
            mock_update.message.reply_text = AsyncMock()
            
            mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
            mock_context.user_data = {
                "escrow_data": {
                    "early_escrow_id": f"ES091825{user_id}",
                    "status": "creating"
                }
            }
            
            with patch('handlers.escrow.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value = mock_session
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                
                mock_session.query.return_value.filter.return_value.first.return_value = sample_user
                
                with patch.object(FastSellerLookupService, 'get_seller_profile_fast', 
                                return_value=FastSellerProfile(
                                    user_id=None, username=seller_name, display_name=seller_name,
                                    exists_on_platform=False, basic_rating=None, total_ratings=0,
                                    trust_level="new", last_active=None, is_verified=False,
                                    warning_flags=[]
                                )):
                    return await handle_seller_input(mock_update, mock_context)
        
        # Run multiple escrow creations concurrently
        tasks = [
            create_escrow(111, "seller1"),
            create_escrow(222, "seller2"),
            create_escrow(333, "seller3")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert result == EscrowStates.AMOUNT_INPUT

    def test_username_validation_edge_cases(self):
        """Test edge cases in username validation"""
        from utils.input_validation import InputValidator, ValidationError
        
        # Test various invalid username formats
        invalid_usernames = [
            "@",  # Just @ symbol
            "@a",  # Too short
            "@" + "a" * 33,  # Too long
            "@123abc",  # Starts with number
            "@user-name",  # Contains hyphen
            "@user.name",  # Contains dot
            "@user name",  # Contains space
            "@@username",  # Double @
        ]
        
        for username in invalid_usernames:
            with pytest.raises(ValidationError):
                InputValidator.validate_username(username)
        
        # Test valid usernames
        valid_usernames = [
            "@username",
            "@user123",
            "@user_name",
            "@test_user_123",
            "@a" * 32,  # Max length
        ]
        
        for username in valid_usernames:
            result = InputValidator.validate_username(username)
            assert result == username  # Should return the same username

    def test_email_validation_edge_cases(self):
        """Test edge cases in email validation"""
        from utils.input_validation import InputValidator, ValidationError
        
        # Test various invalid email formats
        invalid_emails = [
            "notanemail",
            "@domain.com",
            "user@",
            "user@domain",
            "user..double@domain.com",
            "user@domain..com",
            "user name@domain.com",  # Space in email
            "a" * 255 + "@domain.com",  # Too long
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                InputValidator.validate_email(email)
        
        # Test valid emails
        valid_emails = [
            "user@domain.com",
            "test.user@example.org",
            "user+tag@domain.co.uk",
            "123@domain.com",
        ]
        
        for email in valid_emails:
            result = InputValidator.validate_email(email)
            assert result == email.lower()  # Should return lowercase

    @pytest.mark.asyncio
    async def test_memory_usage_during_escrow_creation(self, mock_update, mock_context, sample_user):
        """Test that escrow creation doesn't cause memory leaks"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Run escrow creation multiple times
        for i in range(10):
            mock_update.message.text = f"@seller{i}"
            
            with patch('handlers.escrow.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value = mock_session
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                
                mock_session.query.return_value.filter.return_value.first.return_value = sample_user
                
                with patch.object(FastSellerLookupService, 'get_seller_profile_fast', 
                                return_value=FastSellerProfile(
                                    user_id=None, username=f"seller{i}", display_name=f"seller{i}",
                                    exists_on_platform=False, basic_rating=None, total_ratings=0,
                                    trust_level="new", last_active=None, is_verified=False,
                                    warning_flags=[]
                                )):
                    await handle_seller_input(mock_update, mock_context)
        
        # Check final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (less than 10MB)
        assert memory_increase < 10 * 1024 * 1024, f"Memory increased by {memory_increase / 1024 / 1024}MB"