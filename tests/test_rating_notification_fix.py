"""
Unit test for rating notification fixes
Tests:
1. Telegram notification without Markdown parsing (prevents parsing errors)
2. Email notification without await (fixes boolean await error)
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from decimal import Decimal
from datetime import datetime

from models import User, Escrow, Rating
from handlers.user_rating import handle_rating_submit


@pytest.mark.asyncio
async def test_rating_notification_telegram_no_markdown():
    """Test that Telegram rating notification sends without Markdown parsing"""
    
    # Create mock objects
    mock_query = AsyncMock()
    mock_query.data = "rating_submit"
    mock_query.get_bot = Mock()
    mock_bot = AsyncMock()
    mock_query.get_bot.return_value = mock_bot
    
    mock_update = Mock()
    mock_update.callback_query = mock_query
    mock_update.effective_user = Mock(id=123456)
    
    mock_context = Mock()
    mock_context.user_data = {
        'rating_trade': Mock(
            id=1,
            escrow_id="ES123456TEST",
            buyer_id=1,
            seller_id=2,
            amount=Decimal("50.00")
        ),
        'rating_type': 'buyer',
        'rating_stars': 5,
        'rating_comment': 'Great buyer!',
        'rating_counterpart': Mock(
            id=1,
            telegram_id=111111,
            username="buyer_user",
            email="buyer@test.com"
        )
    }
    
    mock_session = MagicMock()
    mock_user = Mock(
        id=2,
        telegram_id=123456,
        username="seller_user"
    )
    mock_rated_user = Mock(
        id=1,
        telegram_id=111111,
        username="buyer_user",
        email="buyer@test.com"
    )
    
    mock_session.query.return_value.filter.return_value.first.side_effect = [
        mock_user,  # rater
        mock_rated_user,  # rated user
        None  # no existing trade rating
    ]
    
    with patch('handlers.user_rating.SessionLocal', return_value=mock_session), \
         patch('handlers.user_rating.EmailService') as MockEmailService:
        
        # Execute
        await handle_rating_submit(mock_update, mock_context)
        
        # Verify Telegram notification was sent WITHOUT parse_mode parameter
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        
        # Critical assertion: parse_mode should NOT be in kwargs
        assert 'parse_mode' not in call_kwargs, "Telegram notification should NOT use parse_mode"
        assert call_kwargs['chat_id'] == 111111
        assert "⭐⭐⭐⭐⭐" in call_kwargs['text']


@pytest.mark.asyncio 
async def test_rating_notification_email_no_await():
    """Test that email notification is called WITHOUT await (synchronous call)"""
    
    # Create mock objects
    mock_query = AsyncMock()
    mock_query.data = "rating_submit"
    mock_query.get_bot = Mock()
    mock_bot = AsyncMock()
    mock_query.get_bot.return_value = mock_bot
    
    mock_update = Mock()
    mock_update.callback_query = mock_query
    mock_update.effective_user = Mock(id=123456)
    
    mock_context = Mock()
    mock_context.user_data = {
        'rating_trade': Mock(
            id=1,
            escrow_id="ES123456TEST",
            buyer_id=1,
            seller_id=2,
            amount=Decimal("50.00")
        ),
        'rating_type': 'buyer',
        'rating_stars': 5,
        'rating_comment': 'Great buyer!',
        'rating_counterpart': Mock(
            id=1,
            telegram_id=111111,
            username="buyer_user",
            email="buyer@test.com",
            email_verified=True
        )
    }
    
    mock_session = MagicMock()
    mock_user = Mock(
        id=2,
        telegram_id=123456,
        username="seller_user"
    )
    mock_rated_user = Mock(
        id=1,
        telegram_id=111111,
        username="buyer_user",
        email="buyer@test.com",
        email_verified=True
    )
    
    mock_session.query.return_value.filter.return_value.first.side_effect = [
        mock_user,  # rater
        mock_rated_user,  # rated user
        None  # no existing trade rating
    ]
    
    # Create a mock email service that returns a boolean (synchronous behavior)
    mock_email_service = Mock()
    mock_email_service.send_email = Mock(return_value=True)  # Synchronous return
    
    with patch('handlers.user_rating.SessionLocal', return_value=mock_session), \
         patch('handlers.user_rating.EmailService', return_value=mock_email_service):
        
        # Execute - should NOT raise "object bool can't be used in 'await' expression"
        await handle_rating_submit(mock_update, mock_context)
        
        # Verify email service was called (synchronously, no await)
        assert mock_email_service.send_email.called
        assert mock_email_service.send_email.return_value == True  # Boolean return


@pytest.mark.asyncio
async def test_rating_notification_with_quote_in_comment():
    """Test that rating notification handles quotes in comments without parse errors"""
    
    mock_query = AsyncMock()
    mock_query.data = "rating_submit"
    mock_query.get_bot = Mock()
    mock_bot = AsyncMock()
    mock_query.get_bot.return_value = mock_bot
    
    mock_update = Mock()
    mock_update.callback_query = mock_query
    mock_update.effective_user = Mock(id=123456)
    
    # Comment with quotes that would break Markdown parsing
    mock_context = Mock()
    mock_context.user_data = {
        'rating_trade': Mock(
            id=1,
            escrow_id="ES123456TEST",
            buyer_id=1,
            seller_id=2,
            amount=Decimal("50.00")
        ),
        'rating_type': 'buyer',
        'rating_stars': 5,
        'rating_comment': 'Great buyer! He said "thanks" and paid quickly.',  # Quote in comment
        'rating_counterpart': Mock(
            id=1,
            telegram_id=111111,
            username="buyer_user",
            email="buyer@test.com"
        )
    }
    
    mock_session = MagicMock()
    mock_user = Mock(id=2, telegram_id=123456, username="seller_user")
    mock_rated_user = Mock(id=1, telegram_id=111111, username="buyer_user", email="buyer@test.com")
    
    mock_session.query.return_value.filter.return_value.first.side_effect = [
        mock_user,
        mock_rated_user,
        None
    ]
    
    with patch('handlers.user_rating.SessionLocal', return_value=mock_session), \
         patch('handlers.user_rating.EmailService'):
        
        # Should NOT raise "can't find end of entity" error
        await handle_rating_submit(mock_update, mock_context)
        
        # Verify notification was sent successfully
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]
        
        # Verify quote character is in the message
        assert '"thanks"' in call_kwargs['text']
        # Verify no parse_mode is used (which would cause the error)
        assert 'parse_mode' not in call_kwargs
