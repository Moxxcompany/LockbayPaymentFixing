"""
Comprehensive Unit and E2E Tests for Menu System (handlers/menu.py)
Tests hamburger menu, state cleanup, session management, and navigation flows
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram import Update, CallbackQuery, User as TelegramUser, Chat, Message
from telegram.ext import ContextTypes

# Import the handlers we're testing
from handlers.menu import show_hamburger_menu
from models import User, Escrow

import logging
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestMenuSystemUnit:
    """Unit tests for menu system functionality"""
    
    async def test_show_hamburger_menu_state_cleanup(self):
        """Test that hamburger menu properly cleans up conversation states"""
        # Setup mock update and context
        mock_update = Mock(spec=Update)
        mock_query = Mock(spec=CallbackQuery)
        mock_update.callback_query = mock_query
        mock_update.effective_user = Mock(spec=TelegramUser)
        mock_update.effective_user.id = 12345
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.user_data = {
            "active_conversation": "some_conversation",
            "exchange_data": {"test": "data"},
            "exchange_session_id": "session_123",
            "escrow_data": {"escrow": "info"},
            "contact_data": {"contact": "data"},
            "wallet_data": {"wallet": "info"},
            "expecting_funding_amount": True,
            "expecting_custom_amount": True,
        }
        
        # Mock the callback query answer
        with patch('utils.callback_utils.safe_answer_callback_query') as mock_answer:
            mock_answer.return_value = None
            
            # Mock universal session manager
            with patch('utils.universal_session_manager.universal_session_manager') as mock_session_mgr:
                mock_session_mgr.get_user_session_ids.return_value = ["session1", "session2"]
                mock_session_mgr.terminate_session = Mock()
                
                # Mock database session
                with patch('handlers.menu.SessionLocal') as mock_session_class:
                    mock_session = Mock()
                    mock_session_class.return_value.__enter__.return_value = mock_session
                    mock_session.query.return_value.filter.return_value.first.return_value = None
                    
                    # Mock the message sending
                    with patch('utils.message_utils.send_unified_message') as mock_send_message:
                        mock_send_message.return_value = None
                        
                        # Mock keyboards 
                        with patch('utils.keyboards.hamburger_menu_keyboard') as mock_keyboard:
                            mock_keyboard.return_value = Mock()
                            
                            # Execute the function
                            result = await show_hamburger_menu(mock_update, mock_context)
                        
                        # Verify state cleanup
                        assert "active_conversation" not in mock_context.user_data
                        assert "exchange_data" not in mock_context.user_data
                        assert "exchange_session_id" not in mock_context.user_data
                        assert "escrow_data" not in mock_context.user_data
                        assert "contact_data" not in mock_context.user_data
                        assert "wallet_data" not in mock_context.user_data
                        assert "expecting_funding_amount" not in mock_context.user_data
                        assert "expecting_custom_amount" not in mock_context.user_data
                        
                        # Verify callback was answered
                        mock_answer.assert_called_once_with(mock_query, "🏠 Main menu")
                        
                        # Verify universal sessions were cleaned
                        mock_session_mgr.get_user_session_ids.assert_called_once_with(12345)
                        assert mock_session_mgr.terminate_session.call_count == 2

    async def test_hamburger_menu_without_callback_query(self):
        """Test hamburger menu when called without callback query (direct message)"""
        mock_update = Mock(spec=Update)
        mock_update.callback_query = None
        mock_update.effective_user = Mock(spec=TelegramUser)
        mock_update.effective_user.id = 12345
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.user_data = {}
        
        with patch('utils.universal_session_manager.universal_session_manager') as mock_session_mgr:
            mock_session_mgr.get_user_session_ids.return_value = []
            
            with patch('handlers.menu.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session.query.return_value.filter.return_value.first.return_value = None
                
                with patch('utils.message_utils.send_unified_message') as mock_send_message:
                    mock_send_message.return_value = None
                    
                    with patch('utils.keyboards.hamburger_menu_keyboard') as mock_keyboard:
                        mock_keyboard.return_value = Mock()
                        
                        result = await show_hamburger_menu(mock_update, mock_context)
                        
                        # Should still work without callback query
                        mock_send_message.assert_called_once()

    async def test_hamburger_menu_session_cleanup_error_handling(self):
        """Test that session cleanup errors don't break the menu"""
        mock_update = Mock(spec=Update)
        mock_update.callback_query = None
        mock_update.effective_user = Mock(spec=TelegramUser)
        mock_update.effective_user.id = 12345
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.user_data = {}
        
        # Mock session manager to raise exception
        with patch('utils.universal_session_manager.universal_session_manager') as mock_session_mgr:
            mock_session_mgr.get_user_session_ids.side_effect = Exception("Session manager error")
            
            with patch('handlers.menu.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session.query.return_value.filter.return_value.first.return_value = None
                
                with patch('utils.message_utils.send_unified_message') as mock_send_message:
                    mock_send_message.return_value = None
                    
                    with patch('utils.keyboards.hamburger_menu_keyboard') as mock_keyboard:
                        mock_keyboard.return_value = Mock()
                        
                        # Should not raise exception despite session manager error
                        result = await show_hamburger_menu(mock_update, mock_context)
                        mock_send_message.assert_called_once()

    async def test_hamburger_menu_database_integration(self):
        """Test hamburger menu with actual database integration"""
        mock_update = Mock(spec=Update)
        mock_update.callback_query = None
        mock_update.effective_user = Mock(spec=TelegramUser)
        mock_update.effective_user.id = 12345
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.user_data = {}
        
        # Mock user and escrow data
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.first_name = "Test User"
        
        mock_escrow = Mock(spec=Escrow)
        mock_escrow.id = 1
        
        with patch('handlers.menu.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Mock database queries
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            mock_session.query.return_value.filter.return_value.count.return_value = 2
            
            with patch('handlers.menu.show_main_menu') as mock_show_menu:
                mock_show_menu.return_value = 0
                
                result = await show_hamburger_menu(mock_update, mock_context)
                
                # Verify database queries were made
                assert mock_session.query.called
                assert result == 0


@pytest.mark.asyncio
class TestMenuSystemE2E:
    """End-to-end tests for complete menu navigation workflows"""
    
    async def test_e2e_main_menu_navigation_flow(self):
        """Test complete main menu navigation flow from start to finish"""
        # Create realistic update and context objects
        mock_user = Mock(spec=TelegramUser)
        mock_user.id = 12345
        mock_user.first_name = "John"
        mock_user.username = "johndoe"
        
        mock_chat = Mock(spec=Chat)
        mock_chat.id = 12345
        
        mock_message = Mock(spec=Message)
        mock_message.message_id = 1
        mock_message.chat = mock_chat
        
        mock_query = Mock(spec=CallbackQuery)
        mock_query.data = "main_menu"
        mock_query.message = mock_message
        
        mock_update = Mock(spec=Update)
        mock_update.callback_query = mock_query
        mock_update.effective_user = mock_user
        mock_update.effective_chat = mock_chat
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.user_data = {
            "active_conversation": "test_conversation",
            "some_session_data": "test_data"
        }
        mock_context.bot = AsyncMock()
        
        # Mock all external dependencies
        with patch('utils.callback_utils.safe_answer_callback_query') as mock_answer:
            with patch('utils.universal_session_manager.universal_session_manager') as mock_session_mgr:
                mock_session_mgr.get_user_session_ids.return_value = ["session1"]
                mock_session_mgr.terminate_session = Mock()
                
                with patch('handlers.menu.SessionLocal') as mock_session_class:
                    mock_session = Mock()
                    mock_session_class.return_value.__enter__.return_value = mock_session
                    
                    # Mock database user
                    mock_db_user = Mock(spec=User)
                    mock_db_user.first_name = "John"
                    mock_db_user.id = 1
                    mock_session.query.return_value.filter.return_value.first.return_value = mock_db_user
                    
                    with patch('handlers.menu.show_main_menu') as mock_show_menu:
                        mock_show_menu.return_value = 0
                        
                        # Execute the E2E flow
                        result = await show_hamburger_menu(mock_update, mock_context)
                        
                        # Verify the complete flow
                        mock_answer.assert_called_once()
                        mock_session_mgr.terminate_session.assert_called_once_with("session1", "hamburger_menu_navigation")
                        mock_show_menu.assert_called_once()
                        assert result == 0
                        assert "active_conversation" not in mock_context.user_data

    async def test_e2e_menu_state_persistence_across_sessions(self):
        """Test that menu properly handles state persistence across multiple sessions"""
        # Simulate multiple rapid menu calls (user clicking rapidly)
        mock_update = Mock(spec=Update)
        mock_update.callback_query = Mock(spec=CallbackQuery)
        mock_update.effective_user = Mock(spec=TelegramUser)
        mock_update.effective_user.id = 12345
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # First call with some state
        mock_context.user_data = {"session1": "data1", "session2": "data2"}
        
        with patch('utils.callback_utils.safe_answer_callback_query'):
            with patch('utils.universal_session_manager.universal_session_manager') as mock_session_mgr:
                mock_session_mgr.get_user_session_ids.return_value = ["session1", "session2"]
                mock_session_mgr.terminate_session = Mock()
                
                with patch('handlers.menu.SessionLocal') as mock_session_class:
                    mock_session = Mock()
                    mock_session_class.return_value.__enter__.return_value = mock_session
                    mock_session.query.return_value.filter.return_value.first.return_value = None
                    
                    with patch('handlers.menu.show_main_menu') as mock_show_menu:
                        mock_show_menu.return_value = 0
                        
                        # First call
                        result1 = await show_hamburger_menu(mock_update, mock_context)
                        
                        # Verify sessions were terminated
                        assert mock_session_mgr.terminate_session.call_count == 2
                        
                        # Second call with new state
                        mock_context.user_data = {"new_session": "new_data"}
                        mock_session_mgr.get_user_session_ids.return_value = ["new_session"]
                        mock_session_mgr.terminate_session.reset_mock()
                        
                        result2 = await show_hamburger_menu(mock_update, mock_context)
                        
                        # Verify second cleanup
                        mock_session_mgr.terminate_session.assert_called_once_with("new_session", "hamburger_menu_navigation")
                        assert result1 == result2 == 0

    async def test_e2e_menu_error_recovery_workflow(self):
        """Test complete menu error recovery workflow"""
        mock_update = Mock(spec=Update)
        mock_update.callback_query = Mock(spec=CallbackQuery)
        mock_update.effective_user = Mock(spec=TelegramUser)
        mock_update.effective_user.id = 12345
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.user_data = {"test": "data"}
        
        # Simulate database error
        with patch('utils.callback_utils.safe_answer_callback_query'):
            with patch('utils.universal_session_manager.universal_session_manager'):
                with patch('handlers.menu.SessionLocal') as mock_session_class:
                    # Database error simulation
                    mock_session_class.side_effect = Exception("Database connection failed")
                    
                    with patch('handlers.menu.show_main_menu') as mock_show_menu:
                        # Should still attempt to show menu despite database error
                        mock_show_menu.return_value = 0
                        
                        # Should not raise exception
                        result = await show_hamburger_menu(mock_update, mock_context)
                        
                        # Verify graceful degradation
                        assert result == 0  # Should still return successfully


@pytest.mark.integration
class TestMenuSystemIntegration:
    """Integration tests with real components"""
    
    async def test_menu_with_real_database_session(self, test_db_session):
        """Test menu system with real database session"""
        # Create a real user in test database
        from models import User
        
        test_user = User(
            telegram_id=12345,
            username="testuser",
            first_name="Test",
            email="test@example.com"
        )
        test_db_session.add(test_user)
        test_db_session.commit()
        
        mock_update = Mock(spec=Update)
        mock_update.callback_query = None
        mock_update.effective_user = Mock(spec=TelegramUser)
        mock_update.effective_user.id = 12345
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.user_data = {"test_data": "cleanup_me"}
        
        with patch('handlers.menu.SessionLocal', return_value=test_db_session):
            with patch('handlers.menu.show_main_menu') as mock_show_menu:
                mock_show_menu.return_value = 0
                
                result = await show_hamburger_menu(mock_update, mock_context)
                
                # Verify database integration worked
                assert result == 0
                assert "test_data" not in mock_context.user_data

    async def test_menu_performance_under_load(self):
        """Test menu system performance under concurrent load"""
        import time
        
        async def single_menu_call():
            mock_update = Mock(spec=Update)
            mock_update.callback_query = None
            mock_update.effective_user = Mock(spec=TelegramUser)
            mock_update.effective_user.id = 12345
            
            mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
            mock_context.user_data = {}
            
            with patch('handlers.menu.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session.query.return_value.filter.return_value.first.return_value = None
                
                with patch('handlers.menu.show_main_menu') as mock_show_menu:
                    mock_show_menu.return_value = 0
                    return await show_hamburger_menu(mock_update, mock_context)
        
        # Run 10 concurrent menu calls
        start_time = time.time()
        results = await asyncio.gather(*[single_menu_call() for _ in range(10)])
        end_time = time.time()
        
        # Verify all calls completed successfully
        assert all(result == 0 for result in results)
        
        # Verify reasonable performance (should complete in under 1 second)
        execution_time = end_time - start_time
        assert execution_time < 1.0, f"Menu calls took too long: {execution_time}s"