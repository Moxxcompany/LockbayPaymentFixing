"""
Comprehensive test suite for escrow error handling and edge cases
Tests database failures, network timeouts, validation errors, and system resilience
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from telegram import Update, Message, User as TelegramUser
from telegram.ext import ContextTypes
from telegram.error import NetworkError, TelegramError, BadRequest

from handlers.escrow import handle_seller_input, handle_amount_input
from handlers.escrow_direct import route_text_message_to_escrow_flow
from services.fast_seller_lookup_service import FastSellerLookupService
from models import User, Escrow
from database import SessionLocal
from utils.constants import EscrowStates
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError


class TestEscrowErrorHandling:
    """Test suite for escrow error handling and resilience"""

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram update object"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=TelegramUser)
        update.effective_user.id = 5590563715
        update.message = Mock(spec=Message)
        update.message.text = "@onarrival1"
        update.message.reply_text = AsyncMock()
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

    @pytest.mark.asyncio
    async def test_database_connection_failure(self, mock_update, mock_context):
        """Test handling of database connection failures"""
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            # Simulate database connection failure
            mock_session_class.side_effect = OperationalError("Connection failed", None, None)
            
            result = await handle_seller_input(mock_update, mock_context)
            
            # Should handle error gracefully
            assert result == EscrowStates.SELLER_INPUT
            
            # Verify error message was sent to user
            mock_update.message.reply_text.assert_called()
            error_message = mock_update.message.reply_text.call_args[0][0]
            assert "temporarily unavailable" in error_message.lower() or "try again" in error_message.lower()

    @pytest.mark.asyncio
    async def test_database_integrity_error(self, mock_update, mock_context):
        """Test handling of database integrity constraint violations"""
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            # Simulate integrity error during commit
            mock_session.commit.side_effect = IntegrityError("Duplicate key", None, None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_user.username = "testuser"
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=None):
                result = await handle_seller_input(mock_update, mock_context)
                
                # Should handle integrity error gracefully
                assert result is not None
                
                # Verify rollback was called
                mock_session.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_telegram_network_error(self, mock_update, mock_context):
        """Test handling of Telegram network errors"""
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Simulate Telegram network error
            mock_update.message.reply_text.side_effect = NetworkError("Network timeout")
            
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=None):
                # Should not raise exception despite network error
                result = await handle_seller_input(mock_update, mock_context)
                
                # Handler should complete despite messaging failure
                assert result is not None

    @pytest.mark.asyncio
    async def test_telegram_bad_request_error(self, mock_update, mock_context):
        """Test handling of Telegram bad request errors"""
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Simulate Telegram bad request (e.g., message too long)
            mock_update.message.reply_text.side_effect = BadRequest("Message too long")
            
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=None):
                result = await handle_seller_input(mock_update, mock_context)
                
                # Should handle bad request gracefully
                assert result is not None

    @pytest.mark.asyncio
    async def test_missing_user_data(self, mock_update):
        """Test handling when user_data is missing or corrupted"""
        # Create context with no user_data
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.user_data = None
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=None):
                result = await handle_seller_input(mock_update, mock_context)
                
                # Should initialize user_data and continue
                assert mock_context.user_data is not None
                assert "escrow_data" in mock_context.user_data
                assert result is not None

    @pytest.mark.asyncio
    async def test_corrupted_escrow_data(self, mock_update):
        """Test handling when escrow_data is corrupted"""
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.user_data = {
            "escrow_data": "invalid_data_type"  # Should be dict
        }
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=None):
                result = await handle_seller_input(mock_update, mock_context)
                
                # Should recover from corrupted data
                assert isinstance(mock_context.user_data["escrow_data"], dict)
                assert result is not None

    @pytest.mark.asyncio
    async def test_fast_seller_lookup_timeout(self, mock_update, mock_context):
        """Test handling of seller lookup service timeouts"""
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Simulate timeout in seller lookup
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', 
                            side_effect=asyncio.TimeoutError("Lookup timeout")):
                result = await handle_seller_input(mock_update, mock_context)
                
                # Should handle timeout gracefully
                assert result is not None
                
                # Should send appropriate message to user
                mock_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, mock_update, mock_context):
        """Test handling under memory pressure conditions"""
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Simulate memory error
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', 
                            side_effect=MemoryError("Out of memory")):
                result = await handle_seller_input(mock_update, mock_context)
                
                # Should handle memory pressure gracefully
                assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_state_modification(self, mock_update):
        """Test handling of concurrent state modifications"""
        # Create two contexts for the same user
        mock_context1 = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context1.user_data = {
            "escrow_data": {
                "early_escrow_id": "ES001",
                "status": "creating"
            }
        }
        
        mock_context2 = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context2.user_data = {
            "escrow_data": {
                "early_escrow_id": "ES002",
                "status": "creating"
            }
        }
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=None):
                # Process both contexts concurrently
                results = await asyncio.gather(
                    handle_seller_input(mock_update, mock_context1),
                    handle_seller_input(mock_update, mock_context2),
                    return_exceptions=True
                )
                
                # Both should complete without conflicts
                for result in results:
                    assert not isinstance(result, Exception)

    @pytest.mark.asyncio
    async def test_malicious_input_handling(self, mock_update, mock_context):
        """Test handling of malicious or unexpected input"""
        malicious_inputs = [
            "'; DROP TABLE users; --",  # SQL injection attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "A" * 10000,  # Extremely long input
            "\x00\x01\x02",  # Binary data
            "SELECT * FROM users",  # SQL-like input
            "../../../etc/passwd",  # Path traversal attempt
        ]
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            for malicious_input in malicious_inputs:
                mock_update.message.text = malicious_input
                
                with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=None):
                    result = await handle_seller_input(mock_update, mock_context)
                    
                    # Should handle malicious input safely
                    assert result is not None
                    
                    # Should not crash or execute malicious code
                    assert True  # If we reach here, no exception was raised

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, mock_update, mock_context):
        """Test handling of rate limit errors"""
        from telegram.error import RetryAfter
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Simulate rate limit error
            mock_update.message.reply_text.side_effect = RetryAfter(30)  # Retry after 30 seconds
            
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', return_value=None):
                result = await handle_seller_input(mock_update, mock_context)
                
                # Should handle rate limit gracefully
                assert result is not None

    @pytest.mark.asyncio
    async def test_invalid_state_recovery(self, mock_update, mock_context):
        """Test recovery from invalid conversation states"""
        # Set invalid state
        mock_context.user_data["escrow_data"]["status"] = "invalid_status"
        
        with patch('handlers.escrow_direct.get_user_state', return_value="invalid_state"):
            with patch('handlers.escrow_direct.set_user_state') as mock_set_state:
                result = await route_text_message_to_escrow_flow(mock_update, mock_context)
                
                # Should recover from invalid state
                assert result is not None
                
                # Should reset state
                mock_set_state.assert_called()

    @pytest.mark.asyncio
    async def test_session_cleanup_on_error(self, mock_update, mock_context):
        """Test that database sessions are properly cleaned up on errors"""
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            # Simulate error during processing
            mock_session.query.side_effect = Exception("Processing error")
            
            try:
                await handle_seller_input(mock_update, mock_context)
            except Exception as e:
                pass  # Error expected
            
            # Session cleanup should still occur
            mock_session.__exit__.assert_called()

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, mock_update, mock_context):
        """Test graceful degradation when optional services fail"""
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Simulate failure in seller lookup service
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', 
                            side_effect=Exception("Service unavailable")):
                result = await handle_seller_input(mock_update, mock_context)
                
                # Should continue processing despite service failure
                assert result is not None
                
                # Should provide fallback behavior
                mock_update.message.reply_text.assert_called()

    def test_input_sanitization(self):
        """Test input sanitization and validation"""
        from utils.input_validation import InputValidator
        
        # Test markdown sanitization
        dangerous_inputs = [
            "*bold* _italic_ `code`",  # Markdown injection
            "[link](javascript:alert('xss'))",  # Link injection
            "![image](http://evil.com/track.png)",  # Image injection
        ]
        
        for dangerous_input in dangerous_inputs:
            sanitized = InputValidator.sanitize_markdown(dangerous_input)
            
            # Should escape dangerous characters
            assert "*" not in sanitized or sanitized.count("\\*") > 0
            assert "_" not in sanitized or sanitized.count("\\_") > 0
            assert "[" not in sanitized or sanitized.count("\\[") > 0

    @pytest.mark.asyncio
    async def test_error_logging_and_monitoring(self, mock_update, mock_context):
        """Test that errors are properly logged for monitoring"""
        import logging
        
        with patch('handlers.escrow.logger') as mock_logger:
            with patch('handlers.escrow.SessionLocal') as mock_session_class:
                # Simulate error
                mock_session_class.side_effect = Exception("Test error for logging")
                
                try:
                    await handle_seller_input(mock_update, mock_context)
                except Exception as e:
                    pass
                
                # Should log the error
                mock_logger.error.assert_called()
                
                # Log message should contain relevant context
                error_call_args = mock_logger.error.call_args[0][0]
                assert "seller input" in error_call_args.lower() or "error" in error_call_args.lower()

    def test_configuration_validation(self):
        """Test that configuration values are validated"""
        from config import Config
        
        # Test minimum escrow amount
        assert hasattr(Config, 'MIN_ESCROW_AMOUNT_USD')
        assert Config.MIN_ESCROW_AMOUNT_USD > 0
        
        # Test maximum escrow amount
        if hasattr(Config, 'MAX_ESCROW_AMOUNT_USD'):
            assert Config.MAX_ESCROW_AMOUNT_USD > Config.MIN_ESCROW_AMOUNT_USD
        
        # Test timeout configurations
        if hasattr(Config, 'DATABASE_TIMEOUT'):
            assert Config.DATABASE_TIMEOUT > 0
            assert Config.DATABASE_TIMEOUT < 300  # Should be reasonable

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, mock_update, mock_context):
        """Test circuit breaker pattern for external service failures"""
        failure_count = 0
        
        def failing_service(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count < 5:
                raise Exception("Service temporarily unavailable")
            return None  # Service recovered
        
        with patch('handlers.escrow.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            
            mock_user = Mock()
            mock_user.id = 1
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Test multiple failures followed by recovery
            with patch.object(FastSellerLookupService, 'get_seller_profile_fast', 
                            side_effect=failing_service):
                
                # First few calls should fail
                for i in range(4):
                    result = await handle_seller_input(mock_update, mock_context)
                    assert result is not None  # Should handle failure gracefully
                
                # Service should recover on 5th call
                result = await handle_seller_input(mock_update, mock_context)
                assert result is not None