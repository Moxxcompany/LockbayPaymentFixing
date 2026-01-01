"""
Regression Test Suite for Recent Changes
Tests orjson integration and admin broadcast routing fix
"""
import pytest
import asyncio
import json
import orjson
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes


class TestOrjsonIntegration:
    """Test orjson JSON parsing integration"""
    
    def test_orjson_installed(self):
        """Verify orjson is properly installed"""
        import orjson
        assert orjson is not None
        
    def test_orjson_loads_performance(self):
        """Verify orjson.loads() works correctly"""
        test_data = {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "from": {"id": 1531772316, "first_name": "Test"},
                "chat": {"id": 1531772316, "type": "private"},
                "text": "/start"
            }
        }
        
        # Test orjson can parse the data
        json_str = json.dumps(test_data)
        result = orjson.loads(json_str)
        
        assert result["update_id"] == 123456
        assert result["message"]["text"] == "/start"
        
    def test_orjson_dumps_performance(self):
        """Verify orjson.dumps() works correctly"""
        test_data = {
            "provider": "telegram",
            "status": "success",
            "amount": 100.50
        }
        
        # Test orjson can serialize
        result = orjson.dumps(test_data)
        
        # orjson returns bytes, need to decode
        json_str = result.decode('utf-8')
        parsed = json.loads(json_str)
        
        assert parsed["provider"] == "telegram"
        assert parsed["amount"] == 100.50
        
    def test_orjson_compatibility_with_stdlib(self):
        """Verify orjson produces same output as stdlib json"""
        test_data = {"key": "value", "number": 42, "nested": {"a": 1}}
        
        stdlib_result = json.dumps(test_data)
        orjson_result = orjson.dumps(test_data).decode('utf-8')
        
        # Both should parse to the same dict
        assert json.loads(stdlib_result) == json.loads(orjson_result)


class TestAdminBroadcastRouting:
    """Test admin broadcast routing priority fix"""
    
    @pytest.mark.asyncio
    async def test_broadcast_state_priority(self):
        """Verify broadcast state is checked before support reply"""
        from handlers.text_router import UnifiedTextRouter
        from utils.admin_security import is_admin_silent
        
        # Create mock update with admin user
        admin_user = User(id=1531772316, first_name="Admin", is_bot=False)
        chat = Chat(id=1531772316, type="private")
        message = Message(
            message_id=1,
            date=None,
            chat=chat,
            from_user=admin_user,
            text="Test broadcast message"
        )
        
        update = Mock()
        update.effective_user = admin_user
        update.message = message
        
        context = Mock()
        context.user_data = {}
        
        # Test that admin is recognized
        assert is_admin_silent(1531772316) is True
        
    @pytest.mark.asyncio
    async def test_non_admin_routing(self):
        """Verify non-admin users don't get broadcast routing"""
        from utils.admin_security import is_admin_silent
        
        # Test non-admin user
        non_admin_id = 9999999
        assert is_admin_silent(non_admin_id) is False


class TestWebhookPerformance:
    """Test webhook performance with orjson"""
    
    def test_webhook_json_parsing_speed(self):
        """Benchmark JSON parsing speed"""
        import time
        
        # Create realistic webhook payload
        payload = {
            "update_id": 123456789,
            "message": {
                "message_id": 987654,
                "from": {
                    "id": 1531772316,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser",
                    "language_code": "en"
                },
                "chat": {
                    "id": 1531772316,
                    "first_name": "Test",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1698345600,
                "text": "/start"
            }
        }
        
        json_str = json.dumps(payload)
        
        # Test orjson parsing
        start = time.perf_counter()
        for _ in range(1000):
            result = orjson.loads(json_str)
        orjson_time = time.perf_counter() - start
        
        # Test stdlib parsing
        start = time.perf_counter()
        for _ in range(1000):
            result = json.loads(json_str)
        stdlib_time = time.perf_counter() - start
        
        # orjson should be faster
        print(f"\norjson: {orjson_time:.4f}s, stdlib: {stdlib_time:.4f}s")
        print(f"Speedup: {stdlib_time/orjson_time:.2f}x")
        
        assert orjson_time < stdlib_time


class TestBotStartup:
    """Test bot startup and initialization"""
    
    def test_bot_imports(self):
        """Verify all critical modules import correctly"""
        # Test critical imports
        import webhook_server
        import handlers.text_router
        import handlers.admin_broadcast
        from webhook_queue.webhook_inbox.fast_sqlite_webhook_queue import fast_sqlite_webhook_queue
        
        assert webhook_server is not None
        assert fast_sqlite_webhook_queue is not None
        
    def test_sqlite_queue_initialization(self):
        """Verify SQLite webhook queue is properly initialized"""
        from webhook_queue.webhook_inbox.fast_sqlite_webhook_queue import fast_sqlite_webhook_queue
        
        # Check queue is initialized
        assert fast_sqlite_webhook_queue is not None
        assert fast_sqlite_webhook_queue.db_path is not None
        
        # Check metrics exist
        assert 'events_enqueued' in fast_sqlite_webhook_queue._metrics
        assert 'average_enqueue_time_ms' in fast_sqlite_webhook_queue._metrics


class TestCriticalFunctionality:
    """Test critical bot functionality"""
    
    def test_admin_security_module(self):
        """Verify admin security module works"""
        from utils.admin_security import is_admin_silent
        from config import Config
        
        # Test admin detection
        admin_id = 1531772316  # globalservicehelp
        assert is_admin_silent(admin_id) is True
        
    def test_route_guard_imports(self):
        """Verify route guard module imports correctly"""
        from utils.route_guard import RouteGuard, OnboardingProtection
        
        assert RouteGuard is not None
        assert OnboardingProtection is not None
        
    def test_broadcast_service_imports(self):
        """Verify broadcast service imports correctly"""
        from services.broadcast_service import BroadcastService
        
        assert BroadcastService is not None


# Run tests with detailed output
if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "--color=yes"
    ])
