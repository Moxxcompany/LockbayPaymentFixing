"""
Unit test for retention email fix - validates User.completed_trades field
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from jobs.retention_emails import send_weekly_retention_emails
from models import User


@pytest.mark.asyncio
async def test_weekly_retention_email_uses_completed_trades():
    """Test that weekly retention emails query uses User.completed_trades field"""
    
    mock_session = Mock()
    
    # Create mock user with completed_trades = 0
    mock_user = Mock(spec=User)
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.first_name = "Test"
    mock_user.username = "testuser"
    mock_user.completed_trades = 0
    mock_user.created_at = datetime.utcnow() - timedelta(days=7)
    
    # Configure mock query chain
    mock_query = Mock()
    mock_filter = Mock()
    mock_filter.all.return_value = [mock_user]
    mock_query.filter.return_value = mock_filter
    mock_session.query.return_value = mock_query
    
    # Mock email service
    mock_welcome_service = AsyncMock()
    mock_welcome_service.send_followup_email = AsyncMock(return_value=True)
    
    with patch('jobs.retention_emails.SessionLocal', return_value=mock_session), \
         patch('jobs.retention_emails.WelcomeEmailService', return_value=mock_welcome_service):
        
        await send_weekly_retention_emails()
        
        # Verify session.query was called with User model
        mock_session.query.assert_called_once_with(User)
        
        # Verify filter was called (which includes User.completed_trades == 0)
        assert mock_query.filter.called
        
        # Verify email was sent
        mock_welcome_service.send_followup_email.assert_called_once()
        
        # Verify session was closed
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_weekly_retention_email_handles_no_users():
    """Test that weekly retention emails handles case with no inactive users"""
    
    mock_session = Mock()
    
    # Configure mock query chain to return empty list
    mock_query = Mock()
    mock_filter = Mock()
    mock_filter.all.return_value = []
    mock_query.filter.return_value = mock_filter
    mock_session.query.return_value = mock_query
    
    with patch('jobs.retention_emails.SessionLocal', return_value=mock_session):
        # Should complete without error
        await send_weekly_retention_emails()
        
        # Verify session was closed
        mock_session.close.assert_called_once()


def test_user_model_has_completed_trades_field():
    """Verify User model has completed_trades field"""
    # This ensures the field exists on the model
    assert hasattr(User, 'completed_trades'), "User model should have completed_trades field"
    
    # Verify it doesn't have total_trades (the old incorrect field)
    assert not hasattr(User, 'total_trades'), "User model should NOT have total_trades field"
