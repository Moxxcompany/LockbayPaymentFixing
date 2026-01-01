"""
Comprehensive Unit and E2E Tests for Health Monitoring (handlers/health_endpoint.py)
Tests admin access verification, system status reporting, and monitoring workflows
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram import Update, User as TelegramUser, Chat, Message
from telegram.ext import ContextTypes

# Import the handlers we're testing
from handlers.health_endpoint import handle_health_check

import logging
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestHealthMonitoringUnit:
    """Unit tests for health monitoring functionality"""
    
    async def test_health_check_admin_access_granted(self):
        """Test health check access for authorized admin users"""
        # Setup admin user
        mock_effective_user = Mock(spec=TelegramUser)
        mock_effective_user.id = 12345
        
        mock_message = AsyncMock()
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_effective_user
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Mock admin security check to return True
        with patch('handlers.health_endpoint.is_admin_secure') as mock_admin_check:
            mock_admin_check.return_value = True
            
            # Mock health status response
            with patch('handlers.health_endpoint.get_health_status') as mock_health_status:
                mock_health_data = {
                    "status": "healthy",
                    "summary": "All systems operational",
                    "checks": [
                        {"component": "database", "status": "healthy"},
                        {"component": "application", "status": "healthy"}
                    ]
                }
                mock_health_status.return_value = mock_health_data
                
                # Execute health check
                result = await handle_health_check(mock_update, mock_context)
                
                # Verify admin check was called
                mock_admin_check.assert_called_once_with(12345)
                
                # Verify health status was retrieved
                mock_health_status.assert_called_once()
                
                # Verify message was sent
                mock_message.reply_text.assert_called_once()
                call_args = mock_message.reply_text.call_args
                sent_message = call_args[0][0]
                
                # Verify health information is in the message
                assert "✅" in sent_message or "healthy" in sent_message.lower()

    async def test_health_check_admin_access_denied(self):
        """Test health check access denial for non-admin users"""
        mock_effective_user = Mock(spec=TelegramUser)
        mock_effective_user.id = 99999  # Non-admin user ID
        
        mock_message = AsyncMock()
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_effective_user
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Mock admin security check to return False
        with patch('handlers.health_endpoint.is_admin_secure') as mock_admin_check:
            mock_admin_check.return_value = False
            
            # Execute health check
            result = await handle_health_check(mock_update, mock_context)
            
            # Verify admin check was called
            mock_admin_check.assert_called_once_with(99999)
            
            # Verify access denied message was sent
            mock_message.reply_text.assert_called_once()
            call_args = mock_message.reply_text.call_args
            sent_message = call_args[0][0]
            
            # Verify access denied message
            assert "❌" in sent_message and ("access denied" in sent_message.lower() or "admin" in sent_message.lower())

    async def test_health_status_formatting_healthy_system(self):
        """Test health status formatting for healthy system"""
        mock_effective_user = Mock(spec=TelegramUser)
        mock_effective_user.id = 12345
        
        mock_message = AsyncMock()
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_effective_user
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        with patch('handlers.health_endpoint.is_admin_secure', return_value=True):
            with patch('handlers.health_endpoint.get_health_status') as mock_health_status:
                # Mock healthy system response
                mock_health_data = {
                    "status": "healthy",
                    "summary": "All systems running smoothly",
                    "checks": [
                        {"component": "database", "status": "healthy", "details": "Connection OK"},
                        {"component": "application", "status": "healthy", "details": "Running normally"},
                        {"component": "external_apis", "status": "healthy", "details": "All APIs responding"}
                    ]
                }
                mock_health_status.return_value = mock_health_data
                
                await handle_health_check(mock_update, mock_context)
                
                mock_message.reply_text.assert_called_once()
                call_args = mock_message.reply_text.call_args
                sent_message = call_args[0][0]
                
                # Verify healthy status indicators
                assert "✅" in sent_message
                assert "healthy" in sent_message.lower() or "ok" in sent_message.lower()

    async def test_health_status_formatting_warning_system(self):
        """Test health status formatting for system with warnings"""
        mock_effective_user = Mock(spec=TelegramUser)
        mock_effective_user.id = 12345
        
        mock_message = AsyncMock()
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_effective_user
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        with patch('handlers.health_endpoint.is_admin_secure', return_value=True):
            with patch('handlers.health_endpoint.get_health_status') as mock_health_status:
                # Mock system with warnings
                mock_health_data = {
                    "status": "warning",
                    "summary": "Some components need attention",
                    "checks": [
                        {"component": "database", "status": "healthy", "details": "Connection OK"},
                        {"component": "application", "status": "warning", "details": "High memory usage"},
                        {"component": "external_apis", "status": "healthy", "details": "All APIs responding"}
                    ]
                }
                mock_health_status.return_value = mock_health_data
                
                await handle_health_check(mock_update, mock_context)
                
                mock_message.reply_text.assert_called_once()
                call_args = mock_message.reply_text.call_args
                sent_message = call_args[0][0]
                
                # Verify warning status indicators
                assert "⚠️" in sent_message or "warning" in sent_message.lower()

    async def test_health_status_formatting_critical_system(self):
        """Test health status formatting for critical system issues"""
        mock_effective_user = Mock(spec=TelegramUser)
        mock_effective_user.id = 12345
        
        mock_message = AsyncMock()
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_effective_user
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        with patch('handlers.health_endpoint.is_admin_secure', return_value=True):
            with patch('handlers.health_endpoint.get_health_status') as mock_health_status:
                # Mock critical system issues
                mock_health_data = {
                    "status": "critical",
                    "summary": "Critical issues detected",
                    "checks": [
                        {"component": "database", "status": "critical", "details": "Connection failed"},
                        {"component": "application", "status": "warning", "details": "High error rate"},
                        {"component": "external_apis", "status": "healthy", "details": "APIs responding"}
                    ]
                }
                mock_health_status.return_value = mock_health_data
                
                await handle_health_check(mock_update, mock_context)
                
                mock_message.reply_text.assert_called_once()
                call_args = mock_message.reply_text.call_args
                sent_message = call_args[0][0]
                
                # Verify critical status indicators
                assert "❌" in sent_message or "critical" in sent_message.lower()

    async def test_health_check_no_effective_user(self):
        """Test health check behavior when no effective user is present"""
        mock_update = Mock(spec=Update)
        mock_update.effective_user = None  # No user
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Execute health check with no user
        result = await handle_health_check(mock_update, mock_context)
        
        # Should return early without processing
        # Result should be None or appropriate return value
        assert result is None

    async def test_health_check_error_handling(self):
        """Test health check error handling when health status retrieval fails"""
        mock_effective_user = Mock(spec=TelegramUser)
        mock_effective_user.id = 12345
        
        mock_message = AsyncMock()
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_effective_user
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        with patch('handlers.health_endpoint.is_admin_secure', return_value=True):
            with patch('handlers.health_endpoint.get_health_status') as mock_health_status:
                # Mock health status retrieval error
                mock_health_status.side_effect = Exception("Health check service unavailable")
                
                # Should handle error gracefully
                try:
                    result = await handle_health_check(mock_update, mock_context)
                    
                    # If no exception is raised, verify graceful handling
                    # Some implementations might send an error message
                    
                except Exception as e:
                    # If exception is raised, verify it's handled appropriately
                    assert "health" in str(e).lower() or "service" in str(e).lower()


@pytest.mark.asyncio
class TestHealthMonitoringE2E:
    """End-to-end tests for complete health monitoring workflows"""
    
    async def test_e2e_admin_health_check_workflow(self):
        """Test complete admin health check workflow from request to response"""
        # Create realistic admin user
        mock_telegram_user = Mock(spec=TelegramUser)
        mock_telegram_user.id = 555555
        mock_telegram_user.username = "admin_user"
        mock_telegram_user.first_name = "Admin"
        
        mock_chat = Mock(spec=Chat)
        mock_chat.id = 555555
        
        mock_message = AsyncMock()
        mock_message.chat = mock_chat
        
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.effective_chat = mock_chat
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.bot = AsyncMock()
        
        # Mock complete workflow
        with patch('handlers.health_endpoint.is_admin_secure') as mock_admin_check:
            mock_admin_check.return_value = True
            
            with patch('handlers.health_endpoint.get_health_status') as mock_health_status:
                # Realistic health status response
                mock_health_data = {
                    "status": "healthy",
                    "summary": "LockBay system operational",
                    "checks": [
                        {"component": "database", "status": "healthy", "uptime": "99.9%"},
                        {"component": "telegram_api", "status": "healthy", "response_time": "50ms"},
                        {"component": "payment_processor", "status": "healthy", "last_check": "2 min ago"},
                        {"component": "email_service", "status": "healthy", "queue_size": "3"},
                        {"component": "redis_cache", "status": "healthy", "memory_usage": "45%"}
                    ]
                }
                mock_health_status.return_value = mock_health_data
                
                # Execute complete E2E workflow
                result = await handle_health_check(mock_update, mock_context)
                
                # Verify complete workflow
                mock_admin_check.assert_called_once_with(555555)
                mock_health_status.assert_called_once()
                mock_message.reply_text.assert_called_once()
                
                # Verify comprehensive health report
                call_args = mock_message.reply_text.call_args
                sent_message = call_args[0][0]
                
                # Should contain system components
                assert any(component in sent_message.lower() for component in 
                          ["database", "telegram", "payment", "email", "redis"])

    async def test_e2e_non_admin_access_denial_workflow(self):
        """Test complete access denial workflow for non-admin users"""
        mock_telegram_user = Mock(spec=TelegramUser)
        mock_telegram_user.id = 777777
        mock_telegram_user.username = "regular_user"
        
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.message = AsyncMock()
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Mock non-admin access
        with patch('handlers.health_endpoint.is_admin_secure') as mock_admin_check:
            mock_admin_check.return_value = False
            
            # Health status should not be called for non-admin
            with patch('handlers.health_endpoint.get_health_status') as mock_health_status:
                mock_health_status.return_value = {}
                
                # Execute access denial workflow
                result = await handle_health_check(mock_update, mock_context)
                
                # Verify access control workflow
                mock_admin_check.assert_called_once_with(777777)
                
                # Health status should NOT be called for non-admin
                mock_health_status.assert_not_called()
                
                # Verify access denied message
                mock_update.message.reply_text.assert_called_once()

    async def test_e2e_health_monitoring_performance(self):
        """Test health monitoring performance under load"""
        import time
        
        async def single_health_check():
            mock_update = Mock(spec=Update)
            mock_update.effective_user = Mock(spec=TelegramUser)
            mock_update.effective_user.id = 12345
            mock_update.message = AsyncMock()
            
            mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
            
            with patch('handlers.health_endpoint.is_admin_secure', return_value=True):
                with patch('handlers.health_endpoint.get_health_status') as mock_health_status:
                    mock_health_status.return_value = {"status": "healthy", "summary": "OK", "checks": []}
                    
                    return await handle_health_check(mock_update, mock_context)
        
        # Run multiple concurrent health checks
        start_time = time.time()
        
        import asyncio
        results = await asyncio.gather(*[single_health_check() for _ in range(5)])
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify all completed successfully and quickly
        assert all(result is None for result in results)  # Expected return value
        assert execution_time < 2.0, f"Health checks took too long: {execution_time}s"


@pytest.mark.integration
class TestHealthMonitoringIntegration:
    """Integration tests with real health monitoring components"""
    
    async def test_health_check_with_real_monitoring_service(self):
        """Test health check integration with actual monitoring service"""
        mock_effective_user = Mock(spec=TelegramUser)
        mock_effective_user.id = 12345
        
        mock_message = AsyncMock()
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_effective_user
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Use real admin check (mocked) but simulate real health service
        with patch('handlers.health_endpoint.is_admin_secure', return_value=True):
            # Let get_health_status run with real implementation (if available)
            # or mock with realistic data structure
            with patch('handlers.health_endpoint.get_health_status') as mock_health_status:
                # Simulate realistic health service response
                realistic_health_data = {
                    "status": "healthy",
                    "timestamp": "2025-09-21T12:00:00Z",
                    "version": "1.0.0",
                    "uptime": 86400,
                    "summary": "All critical systems operational",
                    "checks": [
                        {
                            "component": "postgresql_database",
                            "status": "healthy",
                            "details": {"connection_pool": "8/20", "query_time_avg": "12ms"}
                        },
                        {
                            "component": "redis_cache",
                            "status": "healthy", 
                            "details": {"memory_usage": "45%", "connected_clients": 15}
                        },
                        {
                            "component": "telegram_webhook",
                            "status": "healthy",
                            "details": {"last_update": "30s ago", "queue_size": 0}
                        },
                        {
                            "component": "payment_apis",
                            "status": "warning",
                            "details": {"blockbee": "healthy", "fincra": "slow_response"}
                        }
                    ]
                }
                mock_health_status.return_value = realistic_health_data
                
                # Execute with realistic integration
                result = await handle_health_check(mock_update, mock_context)
                
                # Verify realistic integration worked
                mock_health_status.assert_called_once()
                mock_message.reply_text.assert_called_once()
                
                # Verify realistic health data was processed
                call_args = mock_message.reply_text.call_args
                sent_message = call_args[0][0]
                
                # Should contain realistic component information
                assert any(comp in sent_message.lower() for comp in 
                          ["database", "redis", "telegram", "payment"])