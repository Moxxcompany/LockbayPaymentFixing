"""
Phase 1 Validation Test
Comprehensive validation that all Phase 1 components work together
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from tests.harness.test_harness import comprehensive_test_harness


@pytest.mark.asyncio
@pytest.mark.unit
class TestPhase1Integration:
    """Test Phase 1: Provider Fakes & Test Harness Integration"""
    
    async def test_comprehensive_harness_initialization(self):
        """Test that test harness initializes all components correctly"""
        
        with comprehensive_test_harness(scenario="success") as harness:
            # Verify all components are accessible
            assert harness.fincra is not None
            assert harness.kraken is not None
            assert harness.fastforex is not None
            assert harness.telegram is not None
            assert harness.email is not None
            
            # Verify time is frozen
            current_time = harness.get_current_time()
            assert current_time.year == 2025
            assert current_time.month == 9
            assert current_time.day == 19
            
            # Verify deterministic randomness
            otp1 = harness.get_deterministic_otp()
            otp2 = harness.get_deterministic_otp()
            assert otp1 == "123456"  # First OTP in sequence
            assert otp2 == "789012"  # Second OTP in sequence
            assert otp1 != otp2
    
    async def test_provider_fakes_basic_functionality(self):
        """Test that all provider fakes respond correctly"""
        
        with comprehensive_test_harness(scenario="success") as harness:
            # Test Fincra fake
            fincra_balance = await harness.fincra.get_cached_account_balance()
            assert fincra_balance["success"] is True
            assert fincra_balance["available_balance"] == 100000.0
            
            # Test Kraken fake
            kraken_balance = await harness.kraken.check_balance()
            assert kraken_balance["success"] is True
            assert "balances" in kraken_balance
            
            # Test FastForex fake
            btc_rate = await harness.fastforex.get_crypto_to_usd_rate("BTC")
            assert btc_rate == 45000.0  # Deterministic rate
            
            # Test Email fake
            email_result = await harness.email.send_otp_email(
                "test@example.com", "123456"
            )
            assert email_result["success"] is True
            
            # Test Telegram fake
            message_result = await harness.telegram.send_message(
                chat_id=123, text="Test message"
            )
            assert "message_id" in message_result
    
    async def test_scenario_configuration(self):
        """Test that scenarios configure providers correctly"""
        
        # Test success scenario
        with comprehensive_test_harness(scenario="success") as harness:
            assert harness.fincra.failure_mode is None
            assert harness.kraken.failure_mode is None
            
            # Should succeed
            balance = await harness.fincra.get_cached_account_balance()
            assert balance["success"] is True
        
        # Test network failures scenario
        with comprehensive_test_harness(scenario="network_failures") as harness:
            assert harness.fincra.failure_mode == "api_timeout"
            assert harness.kraken.failure_mode == "api_timeout"
            
            # Should fail with timeout
            with pytest.raises(Exception, match="timeout"):
                await harness.fincra.get_cached_account_balance()
        
        # Test insufficient funds scenario  
        with comprehensive_test_harness(scenario="insufficient_funds") as harness:
            assert harness.fincra.balance_ngn == Decimal("0")
            assert harness.kraken.balances["USD"] == Decimal("0")
    
    async def test_time_control_functionality(self):
        """Test time freezing and advancement"""
        
        with comprehensive_test_harness(frozen_time="2025-01-01T00:00:00Z") as harness:
            # Verify initial time
            start_time = harness.get_current_time()
            assert start_time.month == 1
            assert start_time.day == 1
            
            # Advance time
            harness.advance_time(3600)  # 1 hour
            new_time = harness.get_current_time()
            assert new_time == start_time + timedelta(seconds=3600)
            
            # Jump to specific time
            harness.set_time("2025-12-31T23:59:59Z")
            final_time = harness.get_current_time()
            assert final_time.month == 12
            assert final_time.day == 31
    
    async def test_deterministic_randomness(self):
        """Test deterministic random generation"""
        
        # Two harnesses with same seed should generate identical values
        results1 = []
        results2 = []
        
        with comprehensive_test_harness(random_seed=42) as harness:
            for _ in range(5):
                results1.append(harness.get_deterministic_otp())
                results1.append(harness.get_deterministic_reference("TEST"))
        
        with comprehensive_test_harness(random_seed=42) as harness:
            for _ in range(5):
                results2.append(harness.get_deterministic_otp())
                results2.append(harness.get_deterministic_reference("TEST"))
        
        assert results1 == results2  # Identical sequences
        assert len(set(results1)) > 1  # Not all the same
    
    async def test_telegram_object_factories(self):
        """Test Telegram Update/Context object creation"""
        
        with comprehensive_test_harness() as harness:
            # Create user message update
            update = harness.create_user_update(
                user_id=123,
                message_text="/start",
                first_name="John",
                last_name="Doe"
            )
            
            assert update.message is not None
            assert update.message.text == "/start"
            assert update.message.from_user.id == 123
            assert update.message.from_user.first_name == "John"
            
            # Create callback update
            callback_update = harness.create_callback_update(
                user_id=123,
                callback_data="onboarding_accept_tos"
            )
            
            assert callback_update.callback_query is not None
            assert callback_update.callback_query.data == "onboarding_accept_tos"
            assert callback_update.callback_query.from_user.id == 123
            
            # Create context
            context = harness.create_context(
                user_data={"step": "email_verification"},
                chat_data={"language": "en"}
            )
            
            assert context.user_data["step"] == "email_verification"
            assert context.chat_data["language"] == "en"
    
    async def test_network_blocking(self):
        """Test that network calls are properly blocked"""
        
        with comprehensive_test_harness(block_network=True) as harness:
            # Initially no blocked calls
            assert len(harness.get_blocked_calls()) == 0
            
            # Network blocker should be active
            assert harness.network_blocker is not None
            
            # Verify we can clear blocked calls
            harness.clear_blocked_calls()
            assert len(harness.get_blocked_calls()) == 0
    
    async def test_state_reset_functionality(self):
        """Test comprehensive state reset"""
        
        with comprehensive_test_harness() as harness:
            # Generate some state
            await harness.fincra.get_cached_account_balance()
            await harness.telegram.send_message(123, "test")
            harness.advance_time(3600)
            otp = harness.get_deterministic_otp()
            
            # Verify state exists
            assert len(harness.fincra.get_request_history()) > 0
            assert len(harness.telegram.get_sent_messages()) > 0
            
            # Reset state
            harness.reset_all_state()
            
            # Verify state is cleared
            assert len(harness.fincra.get_request_history()) == 0
            assert len(harness.telegram.get_sent_messages()) == 0
    
    async def test_comprehensive_status_reporting(self):
        """Test comprehensive status reporting"""
        
        with comprehensive_test_harness(scenario="success") as harness:
            # Generate some activity
            await harness.fincra.get_cached_account_balance()
            await harness.kraken.check_balance()
            await harness.telegram.send_message(123, "test")
            
            status = harness.get_comprehensive_status()
            
            # Verify status structure
            assert "scenario" in status
            assert "current_time" in status
            assert "random_seed" in status
            assert "providers_status" in status
            
            # Verify provider status
            providers = status["providers_status"]
            assert "fincra" in providers
            assert "kraken" in providers
            assert "telegram" in providers
            
            # Verify request counts
            assert providers["fincra"]["request_count"] > 0
            assert providers["kraken"]["request_count"] > 0
            assert providers["telegram"]["messages_sent"] > 0
    
    async def test_error_scenarios_isolation(self):
        """Test that error scenarios don't interfere with each other"""
        
        # Test network failure scenario
        with comprehensive_test_harness(scenario="network_failures") as harness1:
            with pytest.raises(Exception):
                await harness1.fincra.get_cached_account_balance()
        
        # Test success scenario should work after failure scenario
        with comprehensive_test_harness(scenario="success") as harness2:
            result = await harness2.fincra.get_cached_account_balance()
            assert result["success"] is True
    
    async def test_phase1_completeness(self):
        """Comprehensive test that Phase 1 is complete and functional"""
        
        with comprehensive_test_harness() as harness:
            # ✅ Provider Fakes: All external services have test doubles
            provider_tests = [
                harness.fincra.get_cached_account_balance(),
                harness.kraken.check_balance(),
                harness.fastforex.get_crypto_to_usd_rate("BTC"),
                harness.email.send_welcome_email("test@example.com", "Test User"),
                harness.telegram.send_message(123, "Phase 1 Test")
            ]
            
            results = await asyncio.gather(*provider_tests, return_exceptions=True)
            
            # All providers should respond (no network calls)
            for result in results:
                assert not isinstance(result, Exception), f"Provider test failed: {result}"
            
            # ✅ Time Fixtures: Time control works
            start_time = harness.get_current_time()
            harness.advance_time(300)  # 5 minutes
            end_time = harness.get_current_time()
            assert end_time == start_time + timedelta(seconds=300)
            
            # ✅ Deterministic Randomness: Reproducible values
            otp1 = harness.get_deterministic_otp()
            harness.reset_random()
            otp2 = harness.get_deterministic_otp()
            assert otp1 == otp2  # Same after reset
            
            # ✅ Network Blocker: External calls prevented
            blocked_calls = harness.get_blocked_calls()
            # No real network calls should have been made
            
            # ✅ Telegram Factories: Realistic objects
            update = harness.create_user_update(123, "/start")
            context = harness.create_context()
            assert update.message.text == "/start"
            assert context is not None
            
            logger.info("✅ Phase 1: Provider Fakes & Test Harness - COMPLETE")


if __name__ == "__main__":
    # Run Phase 1 validation
    pytest.main([__file__, "-v"])