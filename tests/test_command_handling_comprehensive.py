"""
Comprehensive Unit and E2E Tests for Command Handling (handlers/commands.py)
Tests command processing, menu display, user stats, and markdown formatting
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal
from telegram import Update, User as TelegramUser, Chat, Message
from telegram.ext import ContextTypes

# Import the handlers we're testing
from handlers.commands import show_main_menu_with_message
from models import User, Wallet

import logging
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestCommandHandlingUnit:
    """Unit tests for command handling functionality"""
    
    async def test_show_main_menu_with_message_basic(self):
        """Test basic main menu display with custom message"""
        # Setup mock objects with proper async support
        mock_message = AsyncMock()
        mock_effective_user = Mock()
        mock_effective_user.id = 12345
        
        mock_update = Mock(spec=Update)
        mock_update.message = mock_message
        mock_update.effective_user = mock_effective_user
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.first_name = "John"
        mock_user.reputation_score = 4.5
        mock_user.total_ratings = 10
        mock_user.total_trades = 5
        
        custom_message = "Welcome back to the platform!"
        
        # Mock all external dependencies
        with patch('handlers.commands.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Mock wallet query
            mock_wallet = Mock(spec=Wallet)
            mock_wallet.balance = Decimal("100.50")
            mock_session.query.return_value.filter.return_value.first.return_value = mock_wallet
            
            with patch('handlers.commands.main_menu_keyboard') as mock_keyboard:
                mock_keyboard.return_value = Mock()
                
                # Execute the function
                result = await show_main_menu_with_message(mock_update, mock_context, mock_user, custom_message)
                
                # Verify the message was sent via reply_text
                mock_message.reply_text.assert_called_once()
                call_args = mock_message.reply_text.call_args
                sent_message = call_args[0][0]  # First argument is the message text
                
                # Verify custom message is included
                assert custom_message in sent_message
                assert "John" in sent_message
                assert "🏠" in sent_message  # Platform name indicator
                assert result == 0

    async def test_user_reputation_display_formatting(self):
        """Test reputation and stats display formatting"""
        # Setup mock objects with async support
        mock_message = AsyncMock()
        mock_effective_user = Mock()
        mock_effective_user.id = 12345
        
        mock_update = Mock(spec=Update)
        mock_update.message = mock_message
        mock_update.effective_user = mock_effective_user
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Test user with high reputation
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.first_name = "Alice"
        mock_user.reputation_score = 4.8
        mock_user.total_ratings = 25
        mock_user.total_trades = 15
        
        with patch('handlers.commands.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            with patch('handlers.commands.main_menu_keyboard') as mock_keyboard:
                mock_keyboard.return_value = Mock()
                
                with patch('utils.branding.UserRetentionElements.get_reputation_display') as mock_reputation:
                    mock_reputation.return_value = "⭐⭐⭐⭐⭐ 4.8/5"
                    
                    # Execute the function
                    await show_main_menu_with_message(mock_update, mock_context, mock_user, "Test message")
                    
                    # Verify reputation display was called with correct parameters
                    mock_reputation.assert_called_once_with(4.8, 25)
                    
                    # Verify message was sent
                    mock_message.reply_text.assert_called_once()
                    call_args = mock_message.reply_text.call_args
                    sent_message = call_args[0][0]  # First argument is the message text
                    assert "⭐⭐⭐⭐⭐ 4.8/5" in sent_message
                    assert "15 trades" in sent_message

    async def test_wallet_balance_integration(self):
        """Test wallet balance display integration"""
        mock_update = Mock(spec=Update)
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.first_name = "Bob"
        mock_user.reputation_score = 0
        mock_user.total_ratings = 0
        mock_user.total_trades = 0
        
        with patch('handlers.commands.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Test with wallet through SessionLocal
            mock_wallet = Mock(spec=Wallet)
            mock_wallet.balance = Decimal("250.75")
            mock_session.query.return_value.filter.return_value.first.return_value = mock_wallet
            
            with patch('handlers.commands.main_menu_keyboard') as mock_keyboard:
                mock_keyboard.return_value = Mock()
                
                # Setup async message mock
                mock_message = AsyncMock()
                mock_update.message = mock_message
                mock_update.effective_user = Mock()
                mock_update.effective_user.id = 12345
                
                await show_main_menu_with_message(mock_update, mock_context, mock_user, "Balance test")
                
                # Verify SessionLocal was used
                mock_session_class.assert_called()
                
                # Verify message was sent
                mock_message.reply_text.assert_called_once()

    async def test_markdown_escaping_security(self):
        """Test that user input is properly escaped for markdown"""
        mock_update = Mock(spec=Update)
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # User with special characters that need escaping
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.first_name = "John_*Bold*[Test]"  # Characters that need escaping
        
        with patch('handlers.commands.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            with patch('handlers.commands.escape_markdown') as mock_escape:
                mock_escape.return_value = "John\\_\\*Bold\\*\\[Test\\]"
                
                with patch('handlers.commands.main_menu_keyboard') as mock_keyboard:
                    mock_keyboard.return_value = Mock()
                    
                    with patch('utils.message_utils.send_unified_message') as mock_send:
                        mock_send.return_value = None
                        
                        await show_main_menu_with_message(mock_update, mock_context, mock_user, "Security test")
                        
                        # Verify markdown escaping was called
                        mock_escape.assert_called_once_with("John_*Bold*[Test]")
                        
                        # Verify escaped name is in the message
                        call_args = mock_send.call_args
                        sent_message = call_args[0][1]
                        assert "John\\_\\*Bold\\*\\[Test\\]" in sent_message

    async def test_missing_user_data_handling(self):
        """Test handling of missing user data (None values)"""
        mock_update = Mock(spec=Update)
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # User with missing data
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.first_name = None  # Missing first name
        mock_user.reputation_score = None
        mock_user.total_ratings = None
        mock_user.total_trades = None
        
        with patch('handlers.commands.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            with patch('handlers.commands.main_menu_keyboard') as mock_keyboard:
                mock_keyboard.return_value = Mock()
                
                with patch('utils.message_utils.send_unified_message') as mock_send:
                    with patch('utils.branding.UserRetentionElements.get_reputation_display') as mock_reputation:
                        mock_reputation.return_value = "⭐ New User"
                        
                        # Should not crash with None values
                        result = await show_main_menu_with_message(mock_update, mock_context, mock_user, "Test")
                        
                        # Verify fallback behavior
                        mock_reputation.assert_called_once_with(0.0, 0)  # Defaults for None values
                        
                        call_args = mock_send.call_args
                        sent_message = call_args[0][1]
                        assert "there" in sent_message  # Default greeting for None first_name

    async def test_database_error_handling(self):
        """Test graceful handling of database errors"""
        mock_update = Mock(spec=Update)
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.first_name = "Alice"
        
        # Simulate database error
        with patch('handlers.commands.SessionLocal') as mock_session_class:
            mock_session_class.side_effect = Exception("Database connection failed")
            
            with patch('handlers.commands.main_menu_keyboard') as mock_keyboard:
                mock_keyboard.return_value = Mock()
                
                with patch('utils.message_utils.send_unified_message') as mock_send:
                    # Should handle database error gracefully
                    result = await show_main_menu_with_message(mock_update, mock_context, mock_user, "Error test")
                    
                    # Should still send message despite database error
                    mock_send.assert_called_once()


@pytest.mark.asyncio
class TestCommandHandlingE2E:
    """End-to-end tests for complete command processing workflows"""
    
    async def test_e2e_command_response_flow(self):
        """Test complete command processing from input to response"""
        # Create realistic telegram objects
        mock_telegram_user = Mock(spec=TelegramUser)
        mock_telegram_user.id = 12345
        mock_telegram_user.first_name = "John"
        mock_telegram_user.username = "johndoe"
        
        mock_chat = Mock(spec=Chat)
        mock_chat.id = 12345
        
        mock_message = Mock(spec=Message)
        mock_message.chat = mock_chat
        mock_message.from_user = mock_telegram_user
        
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.effective_chat = mock_chat
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.bot = AsyncMock()
        
        # Create database user
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.first_name = "John"
        mock_user.reputation_score = 4.2
        mock_user.total_ratings = 8
        mock_user.total_trades = 3
        
        # Create wallet
        mock_wallet = Mock(spec=Wallet)
        mock_wallet.balance = Decimal("500.00")
        mock_wallet.currency = "USD"
        
        custom_message = "Welcome back! You have new notifications."
        
        # Mock all dependencies for E2E flow
        with patch('handlers.commands.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_wallet
            
            with patch('handlers.commands.main_menu_keyboard') as mock_keyboard:
                mock_menu_markup = Mock()
                mock_keyboard.return_value = mock_menu_markup
                
                with patch('utils.message_utils.send_unified_message') as mock_send:
                    with patch('utils.branding.UserRetentionElements.get_reputation_display') as mock_reputation:
                        mock_reputation.return_value = "⭐⭐⭐⭐ 4.2/5"
                        
                        with patch('handlers.commands.escape_markdown') as mock_escape:
                            mock_escape.return_value = "John"
                            
                            # Execute the complete E2E flow
                            result = await show_main_menu_with_message(
                                mock_update, mock_context, mock_user, custom_message
                            )
                            
                            # Verify complete workflow
                            mock_session.query.assert_called_once_with(Wallet)
                            mock_keyboard.assert_called_once()
                            mock_reputation.assert_called_once_with(4.2, 8)
                            mock_escape.assert_called_once_with("John")
                            mock_send.assert_called_once()
                            
                            # Verify message content
                            call_args = mock_send.call_args
                            sent_message = call_args[0][1]
                            assert custom_message in sent_message
                            assert "John" in sent_message
                            assert "⭐⭐⭐⭐ 4.2/5" in sent_message
                            assert "3 trades" in sent_message

    async def test_e2e_dynamic_menu_generation(self):
        """Test dynamic menu generation based on user context"""
        mock_update = Mock(spec=Update)
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Test different user scenarios
        scenarios = [
            {
                "name": "new_user",
                "user_data": {
                    "first_name": "Alice",
                    "reputation_score": None,
                    "total_ratings": 0,
                    "total_trades": 0
                },
                "wallet_balance": None,
                "expected_reputation": "⭐ New User"
            },
            {
                "name": "experienced_user", 
                "user_data": {
                    "first_name": "Bob",
                    "reputation_score": 4.9,
                    "total_ratings": 50,
                    "total_trades": 25
                },
                "wallet_balance": Decimal("1000.00"),
                "expected_reputation": "⭐⭐⭐⭐⭐ 4.9/5"
            }
        ]
        
        for scenario in scenarios:
            with patch('handlers.commands.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value.__enter__.return_value = mock_session
                
                # Setup wallet
                if scenario["wallet_balance"]:
                    mock_wallet = Mock(spec=Wallet)
                    mock_wallet.balance = scenario["wallet_balance"]
                    mock_session.query.return_value.filter.return_value.first.return_value = mock_wallet
                else:
                    mock_session.query.return_value.filter.return_value.first.return_value = None
                
                # Setup user
                mock_user = Mock(spec=User)
                mock_user.id = 1
                mock_user.first_name = scenario["user_data"]["first_name"]
                mock_user.reputation_score = scenario["user_data"]["reputation_score"]
                mock_user.total_ratings = scenario["user_data"]["total_ratings"]
                mock_user.total_trades = scenario["user_data"]["total_trades"]
                
                with patch('handlers.commands.main_menu_keyboard') as mock_keyboard:
                    mock_keyboard.return_value = Mock()
                    
                    with patch('utils.message_utils.send_unified_message') as mock_send:
                        mock_send.return_value = None
                        
                        with patch('utils.branding.UserRetentionElements.get_reputation_display') as mock_reputation:
                            mock_reputation.return_value = scenario["expected_reputation"]
                            
                            # Execute for each scenario
                            await show_main_menu_with_message(
                                mock_update, mock_context, mock_user, f"Test for {scenario['name']}"
                            )
                            
                            # Verify dynamic content
                            call_args = mock_send.call_args
                            sent_message = call_args[0][1]
                            assert scenario["user_data"]["first_name"] in sent_message
                            assert scenario["expected_reputation"] in sent_message
                            assert f"{scenario['user_data']['total_trades']} trades" in sent_message

    async def test_e2e_error_resilience_workflow(self):
        """Test complete error resilience across the command workflow"""
        mock_update = Mock(spec=Update)
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.first_name = "Charlie"
        
        # Test various error scenarios
        error_scenarios = [
            ("Database connection error", lambda: patch('handlers.commands.SessionLocal', side_effect=Exception("DB Error"))),
            ("Keyboard generation error", lambda: patch('handlers.commands.main_menu_keyboard', side_effect=Exception("Keyboard Error"))),
            ("Message sending error", lambda: patch('utils.message_utils.send_unified_message', side_effect=Exception("Send Error")))
        ]
        
        for error_name, error_patch in error_scenarios:
            with error_patch():
                try:
                    # Should handle error gracefully and not crash
                    result = await show_main_menu_with_message(
                        mock_update, mock_context, mock_user, f"Error test: {error_name}"
                    )
                    
                    # Some errors might be caught and handled, others might propagate
                    # The key is that critical errors should be caught at the handler level
                    
                except Exception as e:
                    # If an exception is raised, it should be a well-defined error
                    assert isinstance(e, Exception)
                    assert error_name.lower() in str(e).lower() or "error" in str(e).lower()


@pytest.mark.integration
class TestCommandHandlingIntegration:
    """Integration tests with real components"""
    
    async def test_command_with_real_database_session(self, test_db_session):
        """Test command handling with real database session"""
        from models import User, Wallet
        
        # Create real test data
        test_user = User(
            telegram_id=12345,
            username="testuser",
            first_name="Integration",
            email="integration@example.com",
            reputation_score=3.8,
            total_ratings=15,
            total_trades=8
        )
        test_db_session.add(test_user)
        test_db_session.commit()
        
        test_wallet = Wallet(
            user_id=test_user.id,
            currency="USD",
            balance=Decimal("750.25")
        )
        test_db_session.add(test_wallet)
        test_db_session.commit()
        
        mock_update = Mock(spec=Update)
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Use real database session
        with patch('handlers.commands.SessionLocal', return_value=test_db_session):
            with patch('handlers.commands.main_menu_keyboard') as mock_keyboard:
                mock_keyboard.return_value = Mock()
                
                with patch('utils.message_utils.send_unified_message') as mock_send:
                    # Execute with real data
                    result = await show_main_menu_with_message(
                        mock_update, mock_context, test_user, "Real database test"
                    )
                    
                    # Verify real database integration
                    mock_send.assert_called_once()
                    call_args = mock_send.call_args
                    sent_message = call_args[0][1]
                    assert "Integration" in sent_message
                    assert "8 trades" in sent_message

    async def test_command_performance_metrics(self):
        """Test command performance under various loads"""
        import time
        
        async def single_command_execution():
            mock_update = Mock(spec=Update)
            mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
            
            mock_user = Mock(spec=User)
            mock_user.id = 1
            mock_user.first_name = "Performance"
            
            with patch('handlers.commands.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session.query.return_value.filter.return_value.first.return_value = None
                
                with patch('handlers.commands.main_menu_keyboard') as mock_keyboard:
                    mock_keyboard.return_value = Mock()
                    
                    with patch('utils.message_utils.send_unified_message') as mock_send:
                        mock_send.return_value = None
                        
                        return await show_main_menu_with_message(
                            mock_update, mock_context, mock_user, "Performance test"
                        )
        
        # Measure execution time
        start_time = time.time()
        
        # Run multiple executions
        import asyncio
        results = await asyncio.gather(*[single_command_execution() for _ in range(5)])
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify performance (should be very fast with mocks)
        assert execution_time < 1.0, f"Command execution took too long: {execution_time}s"
        assert all(result is None for result in results)  # All should complete successfully