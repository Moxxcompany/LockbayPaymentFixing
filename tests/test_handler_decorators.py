"""
Tests for Handler Decorators Audit Logging System
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from telegram import Update, User, Chat, Message, CallbackQuery
from telegram.ext import ContextTypes

from utils.handler_decorators import (
    audit_handler,
    audit_admin_handler,
    audit_escrow_handler,
    audit_callback_handler,
    extract_telegram_context,
    setup_trace_context,
    HandlerContext,
    AuditEventType
)
from utils.comprehensive_audit_logger import TraceContext


class TestHandlerDecorators:
    """Test suite for handler decorators"""
    
    def setup_method(self):
        """Setup for each test"""
        # Clear trace context
        TraceContext.clear_context()
        
        # Create mock update and context
        self.user = User(id=12345, first_name="Test", is_bot=False)
        self.chat = Chat(id=67890, type="private")
        self.message = Message(
            message_id=123,
            date=datetime.now(),
            chat=self.chat,
            from_user=self.user,
            text="/start"
        )
        
        self.update = Update(
            update_id=1,
            message=self.message
        )
        
        self.context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        self.context.user_data = {}
    
    def test_extract_telegram_context(self):
        """Test extraction of Telegram context information"""
        # Test with message update
        context = extract_telegram_context(self.update, self.context)
        
        assert context['user_id'] == 12345
        assert context['chat_id'] == 67890
        assert context['message_id'] == 123
        assert context['command'] == "/start"
        assert context['message_text_length'] == 6
        assert context['has_attachments'] is False
        
    def test_extract_telegram_context_callback_query(self):
        """Test extraction with callback query"""
        # Create callback query update
        callback_query = CallbackQuery(
            id="callback123",
            from_user=self.user,
            chat_instance="chat123",
            data="test_callback_data"
        )
        
        update_with_callback = Update(
            update_id=2,
            callback_query=callback_query
        )
        
        context = extract_telegram_context(update_with_callback, self.context)
        
        assert context['user_id'] == 12345
        assert context['callback_data'] == "test_callback_data"
    
    def test_handler_context_timing(self):
        """Test handler context timing functionality"""
        handler_ctx = HandlerContext("test_handler", AuditEventType.USER_INTERACTION)
        
        # Test timing
        handler_ctx.start_timing()
        assert handler_ctx.start_time is not None
        
        # Simulate some delay
        import time
        time.sleep(0.01)
        
        handler_ctx.end_timing()
        assert handler_ctx.end_time is not None
        assert handler_ctx.latency_ms > 0
    
    @patch('utils.handler_decorators.audit_logger')
    @pytest.mark.asyncio
    async def test_audit_handler_async_success(self, mock_audit_logger):
        """Test audit handler decorator with async function - success case"""
        
        @audit_handler(event_type=AuditEventType.USER_INTERACTION, action="test_action")
        async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            return "success"
        
        # Execute handler
        result = await test_handler(self.update, self.context)
        
        # Verify result
        assert result == "success"
        
        # Verify audit logging was called
        assert mock_audit_logger.log.call_count == 2  # Entry and exit
        
        # Check entry log call
        entry_call = mock_audit_logger.log.call_args_list[0]
        entry_kwargs = entry_call[1]
        assert entry_kwargs['action'] == "test_action_start"
        assert entry_kwargs['user_id'] == 12345
        assert entry_kwargs['chat_id'] == 67890
        assert entry_kwargs['result'] == "handler_entry"
        
        # Check exit log call
        exit_call = mock_audit_logger.log.call_args_list[1]
        exit_kwargs = exit_call[1]
        assert exit_kwargs['action'] == "test_action_end"
        assert exit_kwargs['result'] == "success"
        assert exit_kwargs['latency_ms'] is not None
    
    @patch('utils.handler_decorators.audit_logger')
    @pytest.mark.asyncio
    async def test_audit_handler_async_error(self, mock_audit_logger):
        """Test audit handler decorator with async function - error case"""
        
        @audit_handler(event_type=AuditEventType.USER_INTERACTION, action="test_error_action")
        async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            raise ValueError("Test error")
        
        # Execute handler and expect error
        with pytest.raises(ValueError, match="Test error"):
            await test_handler(self.update, self.context)
        
        # Verify audit logging was called
        assert mock_audit_logger.log.call_count == 2  # Entry and exit
        
        # Check exit log call for error
        exit_call = mock_audit_logger.log.call_args_list[1]
        exit_kwargs = exit_call[1]
        assert exit_kwargs['action'] == "test_error_action_end"
        assert exit_kwargs['result'] == "error"
        assert 'error_type' in exit_kwargs['payload_metadata']
        assert exit_kwargs['payload_metadata']['error_type'] == "ValueError"
    
    @patch('utils.handler_decorators.audit_logger')
    def test_audit_handler_sync(self, mock_audit_logger):
        """Test audit handler decorator with sync function"""
        
        @audit_handler(event_type=AuditEventType.ADMIN, action="sync_test")
        def test_sync_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            return "sync_success"
        
        # Execute handler
        result = test_sync_handler(self.update, self.context)
        
        # Verify result
        assert result == "sync_success"
        
        # Verify audit logging was called
        assert mock_audit_logger.log.call_count == 2  # Entry and exit
    
    @patch('utils.handler_decorators.audit_logger')
    @pytest.mark.asyncio
    async def test_audit_admin_handler(self, mock_audit_logger):
        """Test admin-specific decorator"""
        
        @audit_admin_handler(action="admin_test")
        async def test_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            return "admin_success"
        
        result = await test_admin_handler(self.update, self.context)
        
        assert result == "admin_success"
        
        # Check that admin event type was used
        entry_call = mock_audit_logger.log.call_args_list[0]
        entry_kwargs = entry_call[1]
        assert entry_kwargs['event_type'] == AuditEventType.ADMIN
    
    @patch('utils.handler_decorators.audit_logger')
    @pytest.mark.asyncio
    async def test_audit_escrow_handler(self, mock_audit_logger):
        """Test escrow-specific decorator"""
        
        @audit_escrow_handler(action="escrow_test")
        async def test_escrow_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Set escrow ID in context
            context.user_data['escrow_id'] = "ESC123"
            return "escrow_success"
        
        result = await test_escrow_handler(self.update, self.context)
        
        assert result == "escrow_success"
        
        # Check that transaction event type was used
        entry_call = mock_audit_logger.log.call_args_list[0]
        entry_kwargs = entry_call[1]
        assert entry_kwargs['event_type'] == AuditEventType.TRANSACTION
    
    @patch('utils.handler_decorators.audit_logger')
    @pytest.mark.asyncio
    async def test_callback_handler_logging(self, mock_audit_logger):
        """Test callback-specific handler logging"""
        
        @audit_callback_handler(action="callback_test")
        async def test_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            return "callback_success"
        
        # Create update with callback query
        callback_query = CallbackQuery(
            id="callback123",
            from_user=self.user,
            chat_instance="chat123",
            data="test_button_click"
        )
        
        update_with_callback = Update(
            update_id=2,
            callback_query=callback_query
        )
        
        result = await test_callback_handler(update_with_callback, self.context)
        
        assert result == "callback_success"
        
        # Should have additional callback-specific logging
        assert mock_audit_logger.log.call_count >= 2
    
    def test_setup_trace_context(self):
        """Test trace context setup"""
        handler_ctx = HandlerContext("test", AuditEventType.USER_INTERACTION)
        telegram_ctx = {
            'user_id': 12345,
            'chat_id': 67890,
            'message_id': 123,
            'is_admin': False
        }
        
        setup_trace_context(handler_ctx, telegram_ctx)
        
        assert handler_ctx.trace_id is not None
        assert handler_ctx.user_id == 12345
        assert handler_ctx.chat_id == 67890
        assert handler_ctx.message_id == 123
        assert handler_ctx.is_admin is False
        
        # Check that trace context was set
        assert TraceContext.get_trace_id() == handler_ctx.trace_id
        assert TraceContext.get_user_id() == 12345
    
    @patch('utils.handler_decorators.pii_extractor')
    @patch('utils.handler_decorators.audit_logger')
    @pytest.mark.asyncio
    async def test_pii_safe_metadata_extraction(self, mock_audit_logger, mock_pii_extractor):
        """Test that PII-safe metadata extraction is used"""
        
        # Mock PII extractor
        mock_metadata = MagicMock()
        mock_metadata.to_dict.return_value = {
            'message_length': 6,
            'command': '/start',
            'has_email': False
        }
        mock_pii_extractor.extract_safe_payload_metadata.return_value = mock_metadata
        
        @audit_handler()
        async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            return "success"
        
        await test_handler(self.update, self.context)
        
        # Verify PII extractor was called
        mock_pii_extractor.extract_safe_payload_metadata.assert_called_once_with(self.update)
        
        # Verify safe metadata was included in audit log
        exit_call = mock_audit_logger.log.call_args_list[1]
        exit_kwargs = exit_call[1]
        payload_metadata = exit_kwargs['payload_metadata']
        assert 'message_length' in payload_metadata
        assert 'command' in payload_metadata
    
    @patch('utils.handler_decorators.audit_logger')
    @pytest.mark.asyncio
    async def test_related_ids_extraction(self, mock_audit_logger):
        """Test extraction of related entity IDs from context"""
        
        @audit_handler()
        async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            return "success"
        
        # Set related IDs in context
        self.context.user_data = {
            'escrow_id': 'ESC123',
            'exchange_order_id': 'EXC456',
            'dispute_id': 'DIS789'
        }
        
        await test_handler(self.update, self.context)
        
        # Check that related IDs were captured
        exit_call = mock_audit_logger.log.call_args_list[1]
        exit_kwargs = exit_call[1]
        related_ids = exit_kwargs['related_ids']
        
        assert related_ids.escrow_id == 'ESC123'
        assert related_ids.exchange_order_id == 'EXC456'
        assert related_ids.dispute_id == 'DIS789'
    
    @patch('utils.handler_decorators.logger')
    @patch('utils.handler_decorators.audit_logger')
    @pytest.mark.asyncio
    async def test_decorator_error_handling(self, mock_audit_logger, mock_logger):
        """Test that decorator errors don't break handler execution"""
        
        # Make audit logger throw an error
        mock_audit_logger.log.side_effect = Exception("Audit logging failed")
        
        @audit_handler()
        async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            return "handler_success"
        
        # Handler should still execute successfully
        result = await test_handler(self.update, self.context)
        assert result == "handler_success"
        
        # Error should be logged
        assert mock_logger.error.called


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])