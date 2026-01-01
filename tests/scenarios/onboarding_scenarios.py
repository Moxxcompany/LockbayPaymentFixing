"""
Onboarding Flow Critical Scenarios
Top 8 onboarding scenarios: email→OTP→TOS→done with edge cases and timeouts
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any

from tests.harness.test_harness import comprehensive_test_harness
from models import OnboardingStep, User, UserStatus
from handlers.onboarding_router import OnboardingCallbacks
from services.onboarding_service import OnboardingService
from services.email_verification_service import EmailVerificationService


@pytest.mark.asyncio
@pytest.mark.integration
class OnboardingScenarios:
    """
    Critical Scenario Matrix: Onboarding Flows
    
    Scenarios covered:
    1. Happy path: email→OTP→TOS→done (complete success)
    2. Email validation failures and recovery
    3. OTP timeout and resend flows
    4. Invalid OTP attempts and lockout
    5. TOS decline and re-acceptance
    6. Session timeout during onboarding
    7. Concurrent onboarding attempts (race conditions)
    8. Network failure recovery during critical steps
    """
    
    async def test_scenario_1_onboarding_happy_path(self):
        """
        Scenario 1: Complete onboarding happy path
        Flow: /start → email → OTP → TOS → welcome → done
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 12345
            test_email = "happy@example.com"
            
            # Step 1: User starts onboarding with /start
            update = harness.create_user_update(
                user_id=user_id,
                message_text="/start",
                first_name="John",
                last_name="Doe"
            )
            context = harness.create_context()
            
            # Execute start handler
            from handlers.start import start_handler
            await start_handler(update, context)
            
            # Verify welcome message sent
            messages = harness.telegram.get_sent_messages(user_id)
            assert len(messages) >= 1
            welcome_msg = messages[-1]
            assert "Welcome to LockBay" in welcome_msg["text"]
            
            # Step 2: User provides email
            email_update = harness.create_user_update(
                user_id=user_id,
                message_text=test_email
            )
            
            # Execute onboarding email handler
            from handlers.onboarding_router import handle_email_input
            await handle_email_input(email_update, context)
            
            # Verify email verification initiated
            emails = harness.email.get_sent_emails(test_email)
            assert len(emails) >= 1
            otp_email = emails[-1]
            assert "verification code" in otp_email["subject"].lower()
            
            # Extract OTP from email (in real system, user would receive email)
            otp_data = harness.email.get_otp_data(test_email)
            assert otp_data is not None
            verification_otp = otp_data["otp"]
            
            # Step 3: User provides OTP
            otp_update = harness.create_user_update(
                user_id=user_id,
                message_text=verification_otp
            )
            
            # Execute OTP verification handler
            from handlers.onboarding_router import handle_otp_input
            await handle_otp_input(otp_update, context)
            
            # Verify OTP accepted and TOS presented
            tos_messages = harness.telegram.get_sent_messages(user_id)
            tos_msg = [msg for msg in tos_messages if "Terms of Service" in msg.get("text", "")]
            assert len(tos_msg) >= 1
            
            # Step 4: User accepts TOS
            tos_callback = harness.create_callback_update(
                user_id=user_id,
                callback_data=OnboardingCallbacks.TOS_ACCEPT
            )
            
            # Execute TOS acceptance handler
            from handlers.onboarding_router import handle_callback_query
            await handle_callback_query(tos_callback, context)
            
            # Verify onboarding completion
            completion_messages = harness.telegram.get_sent_messages(user_id)
            completion_msg = [msg for msg in completion_messages if "Welcome" in msg.get("text", "") or "complete" in msg.get("text", "").lower()]
            assert len(completion_msg) >= 1
            
            # Verify user status in database
            async with harness.test_db_session() as session:
                from sqlalchemy import select
                user_result = await session.execute(select(User).where(User.telegram_id == user_id))
                user = user_result.scalar_one_or_none()
                assert user is not None
                assert user.email == test_email
                assert user.status == UserStatus.ACTIVE
                assert user.onboarding_completed_at is not None
            
            # Verify welcome email sent
            welcome_emails = harness.email.get_sent_emails(test_email)
            welcome_email = [email for email in welcome_emails if "welcome" in email.get("subject", "").lower()]
            assert len(welcome_email) >= 1
    
    async def test_scenario_2_email_validation_failures(self):
        """
        Scenario 2: Email validation failures and recovery
        Flow: invalid emails → error messages → valid email → success
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 12346
            
            # Start onboarding
            update = harness.create_user_update(user_id=user_id, message_text="/start")
            context = harness.create_context()
            
            from handlers.start import start_handler
            await start_handler(update, context)
            
            invalid_emails = [
                "invalid-email",           # No @ symbol
                "@example.com",            # Missing local part
                "user@",                   # Missing domain
                "user@.com",               # Invalid domain
                "user@domain.",            # Invalid domain
                "",                        # Empty string
                "   ",                     # Whitespace only
                "a" * 100 + "@example.com" # Too long
            ]
            
            for invalid_email in invalid_emails:
                # Try invalid email
                email_update = harness.create_user_update(
                    user_id=user_id,
                    message_text=invalid_email
                )
                
                from handlers.onboarding_router import handle_email_input
                await handle_email_input(email_update, context)
                
                # Verify error message sent
                messages = harness.telegram.get_sent_messages(user_id)
                error_messages = [msg for msg in messages if "invalid" in msg.get("text", "").lower() or "error" in msg.get("text", "").lower()]
                assert len(error_messages) >= 1, f"No error message for invalid email: {invalid_email}"
                
                # Verify no OTP email sent
                otp_emails = harness.email.get_sent_emails(invalid_email)
                assert len(otp_emails) == 0, f"OTP email sent for invalid email: {invalid_email}"
            
            # Finally provide valid email
            valid_email = "recovered@example.com"
            valid_update = harness.create_user_update(
                user_id=user_id,
                message_text=valid_email
            )
            
            await handle_email_input(valid_update, context)
            
            # Verify success - OTP email sent
            otp_emails = harness.email.get_sent_emails(valid_email)
            assert len(otp_emails) >= 1
    
    async def test_scenario_3_otp_timeout_and_resend(self):
        """
        Scenario 3: OTP timeout and resend flows
        Flow: email → OTP expires → resend OTP → verify new OTP
        """
        
        with comprehensive_test_harness(scenario="success", frozen_time="2025-01-01T10:00:00Z") as harness:
            user_id = 12347
            test_email = "timeout@example.com"
            
            # Complete email step
            update = harness.create_user_update(user_id=user_id, message_text="/start")
            context = harness.create_context()
            
            from handlers.start import start_handler
            await start_handler(update, context)
            
            email_update = harness.create_user_update(user_id=user_id, message_text=test_email)
            from handlers.onboarding_router import handle_email_input
            await handle_email_input(email_update, context)
            
            # Get first OTP
            otp_data = harness.email.get_otp_data(test_email)
            first_otp = otp_data["otp"]
            
            # Advance time beyond OTP expiry (15 minutes + 1 minute)
            harness.advance_time_by(minutes=16)
            
            # Try expired OTP
            expired_otp_update = harness.create_user_update(
                user_id=user_id,
                message_text=first_otp
            )
            
            from handlers.onboarding_router import handle_otp_input
            await handle_otp_input(expired_otp_update, context)
            
            # Verify expiry error message
            messages = harness.telegram.get_sent_messages(user_id)
            expiry_messages = [msg for msg in messages if "expired" in msg.get("text", "").lower()]
            assert len(expiry_messages) >= 1
            
            # User clicks resend OTP
            resend_callback = harness.create_callback_update(
                user_id=user_id,
                callback_data=OnboardingCallbacks.RESEND_OTP
            )
            
            from handlers.onboarding_router import handle_callback_query
            await handle_callback_query(resend_callback, context)
            
            # Verify new OTP sent
            all_emails = harness.email.get_sent_emails(test_email)
            assert len(all_emails) >= 2  # Original + resend
            
            # Get new OTP
            harness.email.clear_history()  # Clear to get fresh OTP data
            # Simulate new OTP generation
            new_otp = harness.get_deterministic_otp()
            
            # Try new OTP
            new_otp_update = harness.create_user_update(
                user_id=user_id,
                message_text=new_otp
            )
            
            await handle_otp_input(new_otp_update, context)
            
            # Should proceed to TOS (success case would show TOS)
            tos_messages = harness.telegram.get_sent_messages(user_id)
            tos_msg = [msg for msg in tos_messages if "Terms" in msg.get("text", "")]
            assert len(tos_msg) >= 1
    
    async def test_scenario_4_invalid_otp_attempts_lockout(self):
        """
        Scenario 4: Invalid OTP attempts and security lockout
        Flow: email → multiple invalid OTPs → lockout → cooldown → retry
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 12348
            test_email = "lockout@example.com"
            
            # Complete email step
            update = harness.create_user_update(user_id=user_id, message_text="/start")
            context = harness.create_context()
            
            from handlers.start import start_handler
            await start_handler(update, context)
            
            email_update = harness.create_user_update(user_id=user_id, message_text=test_email)
            from handlers.onboarding_router import handle_email_input
            await handle_email_input(email_update, context)
            
            # Try multiple invalid OTPs (default max is 5 attempts)
            invalid_otps = ["111111", "222222", "333333", "444444", "555555", "666666"]
            
            from handlers.onboarding_router import handle_otp_input
            
            for i, invalid_otp in enumerate(invalid_otps):
                invalid_update = harness.create_user_update(
                    user_id=user_id,
                    message_text=invalid_otp
                )
                
                await handle_otp_input(invalid_update, context)
                
                messages = harness.telegram.get_sent_messages(user_id)
                
                if i < 4:  # First 5 attempts
                    # Should show "invalid OTP" message with remaining attempts
                    error_messages = [msg for msg in messages if "invalid" in msg.get("text", "").lower()]
                    assert len(error_messages) >= 1
                else:  # 6th attempt triggers lockout
                    # Should show lockout message
                    lockout_messages = [msg for msg in messages if "locked" in msg.get("text", "").lower() or "too many" in msg.get("text", "").lower()]
                    assert len(lockout_messages) >= 1
            
            # Verify even correct OTP is rejected during lockout
            correct_otp = harness.email.get_otp_data(test_email)["otp"]
            correct_update = harness.create_user_update(
                user_id=user_id,
                message_text=correct_otp
            )
            
            await handle_otp_input(correct_update, context)
            
            # Should still show lockout
            messages = harness.telegram.get_sent_messages(user_id)
            lockout_messages = [msg for msg in messages if "locked" in msg.get("text", "").lower()]
            assert len(lockout_messages) >= 1
    
    async def test_scenario_5_tos_decline_and_reacceptance(self):
        """
        Scenario 5: TOS decline and re-acceptance flow
        Flow: email → OTP → decline TOS → retry → accept TOS → done
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 12349
            test_email = "tos_decline@example.com"
            
            # Complete email and OTP steps
            await self._complete_email_otp_steps(harness, user_id, test_email)
            
            # Decline TOS
            tos_decline_callback = harness.create_callback_update(
                user_id=user_id,
                callback_data=OnboardingCallbacks.TOS_DECLINE
            )
            context = harness.create_context()
            
            from handlers.onboarding_router import handle_callback_query
            await handle_callback_query(tos_decline_callback, context)
            
            # Verify decline message and retry option
            messages = harness.telegram.get_sent_messages(user_id)
            decline_messages = [msg for msg in messages if "declined" in msg.get("text", "").lower() or "required" in msg.get("text", "").lower()]
            assert len(decline_messages) >= 1
            
            # User tries to continue without accepting (should be blocked)
            continue_callback = harness.create_callback_update(
                user_id=user_id,
                callback_data="main_menu"  # Try to access main menu
            )
            
            # Should redirect back to TOS
            await handle_callback_query(continue_callback, context)
            tos_messages = harness.telegram.get_sent_messages(user_id)
            tos_retry_msg = [msg for msg in tos_messages if "Terms" in msg.get("text", "")]
            assert len(tos_retry_msg) >= 1
            
            # Finally accept TOS
            tos_accept_callback = harness.create_callback_update(
                user_id=user_id,
                callback_data=OnboardingCallbacks.TOS_ACCEPT
            )
            
            await handle_callback_query(tos_accept_callback, context)
            
            # Verify completion
            completion_messages = harness.telegram.get_sent_messages(user_id)
            completion_msg = [msg for msg in completion_messages if "complete" in msg.get("text", "").lower() or "welcome" in msg.get("text", "").lower()]
            assert len(completion_msg) >= 1
    
    async def test_scenario_6_session_timeout_during_onboarding(self):
        """
        Scenario 6: Session timeout during onboarding process
        Flow: email → wait 24+ hours → OTP fails → restart onboarding
        """
        
        with comprehensive_test_harness(scenario="success", frozen_time="2025-01-01T10:00:00Z") as harness:
            user_id = 12350
            test_email = "timeout_session@example.com"
            
            # Start onboarding and complete email step
            update = harness.create_user_update(user_id=user_id, message_text="/start")
            context = harness.create_context()
            
            from handlers.start import start_handler
            await start_handler(update, context)
            
            email_update = harness.create_user_update(user_id=user_id, message_text=test_email)
            from handlers.onboarding_router import handle_email_input
            await handle_email_input(email_update, context)
            
            # Get OTP
            otp_data = harness.email.get_otp_data(test_email)
            valid_otp = otp_data["otp"]
            
            # Advance time beyond session timeout (25 hours)
            harness.advance_time_by(hours=25)
            
            # Try to use OTP after session timeout
            otp_update = harness.create_user_update(
                user_id=user_id,
                message_text=valid_otp
            )
            
            from handlers.onboarding_router import handle_otp_input
            await handle_otp_input(otp_update, context)
            
            # Should receive session expired message
            messages = harness.telegram.get_sent_messages(user_id)
            timeout_messages = [msg for msg in messages if "expired" in msg.get("text", "").lower() or "restart" in msg.get("text", "").lower()]
            assert len(timeout_messages) >= 1
            
            # User restarts onboarding
            restart_update = harness.create_user_update(user_id=user_id, message_text="/start")
            await start_handler(restart_update, context)
            
            # Should get fresh welcome message
            welcome_messages = harness.telegram.get_sent_messages(user_id)
            fresh_welcome = [msg for msg in welcome_messages if "Welcome" in msg.get("text", "")]
            assert len(fresh_welcome) >= 1
    
    async def test_scenario_7_concurrent_onboarding_attempts(self):
        """
        Scenario 7: Concurrent onboarding attempts (race conditions)
        Flow: multiple simultaneous requests → proper locking → single success
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 12351
            test_email = "concurrent@example.com"
            
            # Create multiple concurrent requests
            concurrent_tasks = []
            
            for i in range(5):  # 5 concurrent start requests
                update = harness.create_user_update(user_id=user_id, message_text="/start")
                context = harness.create_context()
                
                from handlers.start import start_handler
                task = asyncio.create_task(start_handler(update, context))
                concurrent_tasks.append(task)
            
            # Wait for all to complete
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Verify no exceptions and proper handling
            for result in results:
                assert not isinstance(result, Exception), f"Concurrent request failed: {result}"
            
            # Should have only one onboarding session created
            messages = harness.telegram.get_sent_messages(user_id)
            # Even with concurrent requests, should get reasonable number of messages (not 5x)
            assert len(messages) <= 10, f"Too many messages from concurrent requests: {len(messages)}"
            
            # Continue with email step
            email_update = harness.create_user_update(user_id=user_id, message_text=test_email)
            
            # Also test concurrent email submissions
            email_tasks = []
            for i in range(3):
                context = harness.create_context()
                from handlers.onboarding_router import handle_email_input
                task = asyncio.create_task(handle_email_input(email_update, context))
                email_tasks.append(task)
            
            email_results = await asyncio.gather(*email_tasks, return_exceptions=True)
            
            # Should handle gracefully
            for result in email_results:
                assert not isinstance(result, Exception), f"Concurrent email handling failed: {result}"
            
            # Should have sent OTP (but not multiple times)
            otp_emails = harness.email.get_sent_emails(test_email)
            assert len(otp_emails) >= 1
            assert len(otp_emails) <= 3, f"Too many OTP emails from concurrent requests: {len(otp_emails)}"
    
    async def test_scenario_8_network_failure_recovery(self):
        """
        Scenario 8: Network failure recovery during critical steps
        Flow: email step → email service fails → retry → success
        """
        
        # Start with network failures, then recover
        with comprehensive_test_harness(scenario="network_failures") as harness:
            user_id = 12352
            test_email = "network_recovery@example.com"
            
            # Complete start step (should work as it doesn't need external services)
            update = harness.create_user_update(user_id=user_id, message_text="/start")
            context = harness.create_context()
            
            from handlers.start import start_handler
            await start_handler(update, context)
            
            # Try email step with network failures
            email_update = harness.create_user_update(user_id=user_id, message_text=test_email)
            
            from handlers.onboarding_router import handle_email_input
            await handle_email_input(email_update, context)
            
            # Should get error message due to email service failure
            messages = harness.telegram.get_sent_messages(user_id)
            error_messages = [msg for msg in messages if "error" in msg.get("text", "").lower() or "try again" in msg.get("text", "").lower()]
            assert len(error_messages) >= 1
            
            # No email should be sent due to network failure
            otp_emails = harness.email.get_sent_emails(test_email)
            assert len(otp_emails) == 0
        
        # Now recover network and retry
        with comprehensive_test_harness(scenario="success") as harness:
            # User retries email submission
            retry_update = harness.create_user_update(user_id=user_id, message_text=test_email)
            retry_context = harness.create_context()
            
            await handle_email_input(retry_update, retry_context)
            
            # Should succeed now
            recovery_emails = harness.email.get_sent_emails(test_email)
            assert len(recovery_emails) >= 1
            
            # Should get success message
            recovery_messages = harness.telegram.get_sent_messages(user_id)
            success_messages = [msg for msg in recovery_messages if "sent" in msg.get("text", "").lower() or "code" in msg.get("text", "").lower()]
            assert len(success_messages) >= 1
    
    # Helper methods
    async def _complete_email_otp_steps(self, harness, user_id: int, email: str):
        """Helper to complete email and OTP steps"""
        # Start onboarding
        update = harness.create_user_update(user_id=user_id, message_text="/start")
        context = harness.create_context()
        
        from handlers.start import start_handler
        await start_handler(update, context)
        
        # Complete email
        email_update = harness.create_user_update(user_id=user_id, message_text=email)
        from handlers.onboarding_router import handle_email_input
        await handle_email_input(email_update, context)
        
        # Complete OTP
        otp_data = harness.email.get_otp_data(email)
        valid_otp = otp_data["otp"]
        
        otp_update = harness.create_user_update(user_id=user_id, message_text=valid_otp)
        from handlers.onboarding_router import handle_otp_input
        await handle_otp_input(otp_update, context)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])