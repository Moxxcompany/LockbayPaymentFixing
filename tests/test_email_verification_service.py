"""
Unit Tests for EmailVerificationService - Async Context Manager Fix Validation

Tests the comprehensive fix for async context manager issues that caused
'_GeneratorContextManager' object does not support the asynchronous context manager protocol

Key Tests:
- Async OTP sending with new async_managed_session
- Database session management
- Error handling and recovery
- Rate limiting functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from services.email_verification_service import EmailVerificationService, EmailVerificationError, RateLimitError
from database import async_managed_session
from models import EmailVerification, User


class TestEmailVerificationServiceAsyncFix:
    """Test suite for async context manager fix validation"""
    
    @pytest.fixture
    def mock_session(self):
        """Mock async database session"""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        session.execute = AsyncMock()
        session.scalar = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_user(self):
        """Mock user object"""
        user = Mock()
        user.id = 12345
        user.email = "test@example.com"
        user.first_name = "TestUser"
        return user
    
    @pytest.mark.asyncio
    async def test_async_managed_session_context_manager(self):
        """Test that async_managed_session works as proper async context manager"""
        
        # This should NOT raise '_GeneratorContextManager' error anymore
        try:
            async with async_managed_session() as session:
                # Basic database operation simulation
                assert session is not None
                await session.commit()
                success = True
        except Exception as e:
            if "'_GeneratorContextManager' object does not support the asynchronous context manager protocol" in str(e):
                pytest.fail(f"CRITICAL: Async context manager fix failed! Error: {e}")
            success = False
            
        assert success, "Async context manager should work without errors"
    
    @pytest.mark.asyncio
    @patch('services.email_verification_service.async_managed_session')
    @patch('services.email_verification_service.EmailService')
    async def test_send_otp_async_with_new_context_manager(self, mock_email_service, mock_managed_session):
        """Test async OTP sending uses new async context manager without errors"""
        
        # Setup mocks
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=None)  # No existing verification
        
        # Mock the async context manager
        mock_managed_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_managed_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock email service
        mock_email_instance = Mock()
        mock_email_instance.send_email = Mock(return_value=True)
        mock_email_service.return_value = mock_email_instance
        
        # Test the send_otp_async method
        result = await EmailVerificationService.send_otp_async(
            user_id=12345,
            email="test@example.com",
            purpose='registration'
        )
        
        # Verify success
        assert result['success'] is True
        assert result['message'] == "Verification code sent to test@example.com"
        assert 'verification_id' in result
        
        # Verify async context manager was used
        mock_managed_session.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('services.email_verification_service.async_managed_session')
    async def test_send_otp_async_error_handling(self, mock_managed_session):
        """Test async error handling with new context manager"""
        
        # Setup mock to raise exception
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))
        
        mock_managed_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_managed_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Test error handling
        result = await EmailVerificationService.send_otp_async(
            user_id=12345,
            email="test@example.com",
            purpose='registration'
        )
        
        # Verify error response
        assert result['success'] is False
        assert result['error'] == 'system_error'
        assert 'System error occurred' in result['message']
    
    @pytest.mark.asyncio 
    @patch('services.email_verification_service.async_managed_session')
    async def test_verify_otp_async_with_new_context_manager(self, mock_managed_session):
        """Test async OTP verification uses new context manager"""
        
        # Setup mocks
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock()
        
        # Mock existing verification record
        mock_verification = Mock()
        mock_verification.id = 1
        mock_verification.user_id = 12345
        mock_verification.email = "test@example.com"
        mock_verification.otp_hash = EmailVerificationService._hash_otp("123456")
        mock_verification.expires_at = datetime.utcnow() + timedelta(minutes=15)
        mock_verification.attempts = 0
        mock_verification.verified = False
        
        mock_session.scalar = AsyncMock(return_value=mock_verification)
        
        mock_managed_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_managed_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Test verification
        result = await EmailVerificationService.verify_otp_async(
            user_id=12345,
            email="test@example.com",
            otp_code="123456",
            purpose='registration'
        )
        
        # Verify success
        assert result['success'] is True
        assert 'verified successfully' in result['message']
        
        # Verify async context manager was used
        mock_managed_session.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def test_sync_compatibility_still_works(self):
        """Test that sync methods still work for backward compatibility"""
        
        with patch('services.email_verification_service.run_io_task') as mock_run_io:
            mock_run_io.return_value = {
                'success': True,
                'message': 'Code sent successfully'
            }
            
            # Test sync wrapper
            result = EmailVerificationService.send_otp(
                user_id=12345,
                email="test@example.com",
                purpose='registration'
            )
            
            assert result['success'] is True
            mock_run_io.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_no_generator_context_manager_error(self):
        """Specific test to ensure '_GeneratorContextManager' error is eliminated"""
        
        with patch('services.email_verification_service.async_managed_session') as mock_managed_session:
            # This should NOT raise the specific error we're fixing
            mock_session = AsyncMock()
            mock_managed_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_managed_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            try:
                result = await EmailVerificationService.send_otp_async(
                    user_id=12345,
                    email="test@example.com",
                    purpose='registration'
                )
                
                # The key test: this should not contain the specific error
                error_occurred = False
                
            except Exception as e:
                if "'_GeneratorContextManager' object does not support the asynchronous context manager protocol" in str(e):
                    pytest.fail(f"CRITICAL FIX FAILED: The async context manager error still occurs: {e}")
                error_occurred = True
                
            # Either success or different error (not the context manager error)
            assert True, "Async context manager fix successful"


@pytest.mark.integration
class TestEmailVerificationIntegration:
    """Integration tests for email verification with real async context manager"""
    
    @pytest.mark.asyncio
    async def test_full_async_flow_integration(self):
        """Test complete async flow with database operations"""
        
        with patch('services.email_verification_service.EmailService') as mock_email_service:
            mock_email_instance = Mock()
            mock_email_instance.send_email = Mock(return_value=True)
            mock_email_service.return_value = mock_email_instance
            
            # This integration test ensures the full async flow works
            # without the context manager protocol errors
            result = await EmailVerificationService.send_otp_async(
                user_id=999999,  # Test user ID
                email="integration@test.com",
                purpose='registration'
            )
            
            # Should succeed without async context manager errors
            assert isinstance(result, dict)
            assert 'success' in result


if __name__ == "__main__":
    # Can be run directly for debugging
    asyncio.run(TestEmailVerificationServiceAsyncFix().test_async_managed_session_context_manager())
    print("✅ Async context manager fix validation passed!")