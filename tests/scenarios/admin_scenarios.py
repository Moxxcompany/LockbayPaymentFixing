"""
Admin Controls Critical Scenarios
Top 3 admin scenarios: statistics, broadcasts, cancellations with security authorization
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any

from tests.harness.test_harness import comprehensive_test_harness
from models import User, UserRole, Escrow, AdminAction, AdminActionType


@pytest.mark.asyncio
@pytest.mark.integration  
class AdminScenarios:
    """
    Critical Scenario Matrix: Admin Controls
    
    Scenarios covered:
    1. Admin statistics dashboard access and data accuracy
    2. Emergency broadcast to all users
    3. Admin escrow cancellation with proper authorization
    """
    
    async def test_scenario_1_admin_statistics_dashboard(self):
        """
        Scenario 1: Admin statistics dashboard access and real-time data
        Flow: admin login → dashboard access → real-time stats → drill-down data
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            admin_user_id = 99999999
            
            # Set up admin context
            admin_context = harness.create_context(
                user_data={
                    "is_admin": True,
                    "admin_level": "super",
                    "admin_permissions": ["view_stats", "user_management", "emergency_ops"]
                }
            )
            
            # Step 1: Admin accesses dashboard
            dashboard_update = harness.create_user_update(
                user_id=admin_user_id,
                message_text="/admin_dashboard"
            )
            
            from handlers.admin import admin_dashboard_handler
            await admin_dashboard_handler(dashboard_update, admin_context)
            
            # Verify dashboard message with key statistics
            messages = harness.telegram.get_sent_messages(admin_user_id)
            dashboard_msg = messages[-1]
            
            assert "📊 Admin Dashboard" in dashboard_msg["text"]
            assert "Total Users:" in dashboard_msg["text"]
            assert "Active Escrows:" in dashboard_msg["text"]
            assert "Daily Volume:" in dashboard_msg["text"]
            
            # Step 2: Admin requests detailed user stats
            user_stats_callback = harness.create_callback_update(
                user_id=admin_user_id,
                callback_data="admin_stats_users"
            )
            
            from handlers.admin import handle_admin_callback
            await handle_admin_callback(user_stats_callback, admin_context)
            
            # Verify detailed user statistics
            detailed_messages = harness.telegram.get_sent_messages(admin_user_id)
            user_stats_msg = [msg for msg in detailed_messages if "User Statistics" in msg.get("text", "")]
            assert len(user_stats_msg) >= 1
            
            stats_content = user_stats_msg[-1]["text"]
            assert "New Registrations:" in stats_content
            assert "Active Users:" in stats_content
            assert "Verified Users:" in stats_content
            
            # Step 3: Admin requests escrow analytics
            escrow_stats_callback = harness.create_callback_update(
                user_id=admin_user_id,
                callback_data="admin_stats_escrows"
            )
            
            await handle_admin_callback(escrow_stats_callback, admin_context)
            
            # Verify escrow analytics
            escrow_messages = harness.telegram.get_sent_messages(admin_user_id)
            escrow_stats_msg = [msg for msg in escrow_messages if "Escrow Analytics" in msg.get("text", "")]
            assert len(escrow_stats_msg) >= 1
            
            escrow_content = escrow_stats_msg[-1]["text"]
            assert "Total Volume:" in escrow_content
            assert "Success Rate:" in escrow_content
            assert "Average Amount:" in escrow_content
            
            # Step 4: Test unauthorized access
            regular_user_id = 12345
            regular_context = harness.create_context(
                user_data={"is_admin": False}
            )
            
            unauthorized_update = harness.create_user_update(
                user_id=regular_user_id,
                message_text="/admin_dashboard"
            )
            
            await admin_dashboard_handler(unauthorized_update, regular_context)
            
            # Should get access denied message
            unauthorized_messages = harness.telegram.get_sent_messages(regular_user_id)
            access_denied = [msg for msg in unauthorized_messages if "access denied" in msg.get("text", "").lower() or "unauthorized" in msg.get("text", "").lower()]
            assert len(access_denied) >= 1
    
    async def test_scenario_2_emergency_broadcast_system(self):
        """
        Scenario 2: Emergency broadcast to all platform users
        Flow: admin initiates → confirmation → delivery → tracking
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            admin_user_id = 99999999
            
            admin_context = harness.create_context(
                user_data={
                    "is_admin": True,
                    "admin_level": "super", 
                    "admin_permissions": ["emergency_broadcast"]
                }
            )
            
            # Step 1: Admin initiates emergency broadcast
            broadcast_update = harness.create_user_update(
                user_id=admin_user_id,
                message_text="/admin_broadcast"
            )
            
            from handlers.admin_broadcast import admin_broadcast_handler
            await admin_broadcast_handler(broadcast_update, admin_context)
            
            # Should request broadcast message
            messages = harness.telegram.get_sent_messages(admin_user_id)
            request_msg = [msg for msg in messages if "Enter broadcast message" in msg.get("text", "")]
            assert len(request_msg) >= 1
            
            # Step 2: Admin provides broadcast content
            broadcast_content = """
            🚨 URGENT MAINTENANCE NOTICE
            
            The platform will be under maintenance from 2:00-4:00 UTC today.
            All trading will be paused during this time.
            
            Thank you for your patience.
            - LockBay Team
            """
            
            content_update = harness.create_user_update(
                user_id=admin_user_id,
                message_text=broadcast_content
            )
            
            await admin_broadcast_handler(content_update, admin_context)
            
            # Should request confirmation with preview
            confirmation_messages = harness.telegram.get_sent_messages(admin_user_id)
            confirm_msg = [msg for msg in confirmation_messages if "Confirm broadcast" in msg.get("text", "")]
            assert len(confirm_msg) >= 1
            
            preview_text = confirm_msg[-1]["text"]
            assert "URGENT MAINTENANCE NOTICE" in preview_text
            assert "Recipient count:" in preview_text  # Should show how many users
            
            # Step 3: Admin confirms broadcast
            confirm_callback = harness.create_callback_update(
                user_id=admin_user_id,
                callback_data="admin_broadcast_confirm"
            )
            
            from handlers.admin import handle_admin_callback
            await handle_admin_callback(confirm_callback, admin_context)
            
            # Should start broadcast process
            broadcast_messages = harness.telegram.get_sent_messages(admin_user_id)
            start_msg = [msg for msg in broadcast_messages if "Broadcasting" in msg.get("text", "") or "started" in msg.get("text", "").lower()]
            assert len(start_msg) >= 1
            
            # Step 4: Verify broadcast delivery tracking
            # Simulate some users receiving the broadcast
            test_user_ids = [10001, 10002, 10003, 10004]
            
            for user_id in test_user_ids:
                # Verify each user got the broadcast message
                user_messages = harness.telegram.get_sent_messages(user_id)
                broadcast_received = [msg for msg in user_messages if "URGENT MAINTENANCE NOTICE" in msg.get("text", "")]
                assert len(broadcast_received) >= 1, f"User {user_id} did not receive broadcast"
            
            # Verify admin gets completion report
            completion_messages = harness.telegram.get_sent_messages(admin_user_id)
            completion_msg = [msg for msg in completion_messages if "Broadcast completed" in msg.get("text", "")]
            assert len(completion_msg) >= 1
            
            completion_report = completion_msg[-1]["text"]
            assert "sent to" in completion_report.lower()
            assert "users" in completion_report.lower()
    
    async def test_scenario_3_admin_escrow_cancellation_authorization(self):
        """
        Scenario 3: Admin escrow cancellation with proper authorization
        Flow: admin reviews → security check → multi-step confirmation → cancellation
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            admin_user_id = 99999999
            escrow_id = "admin_cancel_test_001"
            buyer_id = 10001
            seller_email = "admin_cancel_seller@example.com"
            
            # Set up admin with appropriate permissions
            admin_context = harness.create_context(
                user_data={
                    "is_admin": True,
                    "admin_level": "super",
                    "admin_permissions": ["escrow_management", "emergency_ops"],
                    "admin_id": "ADMIN_001"
                }
            )
            
            # Step 1: Admin reviews escrow for cancellation
            review_update = harness.create_user_update(
                user_id=admin_user_id,
                message_text=f"/admin_escrow {escrow_id}"
            )
            
            from handlers.admin import admin_escrow_handler
            await admin_escrow_handler(review_update, admin_context)
            
            # Should show escrow details and actions
            messages = harness.telegram.get_sent_messages(admin_user_id)
            details_msg = messages[-1]
            
            assert f"Escrow ID: {escrow_id}" in details_msg["text"]
            assert "Status:" in details_msg["text"]
            assert "Amount:" in details_msg["text"]
            assert "Emergency Cancel" in details_msg["text"]  # Action button available
            
            # Step 2: Admin initiates cancellation
            cancel_callback = harness.create_callback_update(
                user_id=admin_user_id,
                callback_data=f"admin_cancel_escrow_{escrow_id}"
            )
            
            from handlers.admin import handle_admin_callback
            await handle_admin_callback(cancel_callback, admin_context)
            
            # Should request cancellation reason
            reason_messages = harness.telegram.get_sent_messages(admin_user_id)
            reason_msg = [msg for msg in reason_messages if "cancellation reason" in msg.get("text", "").lower()]
            assert len(reason_msg) >= 1
            
            # Step 3: Admin provides reason
            reason_update = harness.create_user_update(
                user_id=admin_user_id,
                message_text="Security concern: Suspicious seller activity detected"
            )
            
            await admin_escrow_handler(reason_update, admin_context)
            
            # Should request security authorization
            auth_messages = harness.telegram.get_sent_messages(admin_user_id)
            auth_msg = [msg for msg in auth_messages if "Security Authorization" in msg.get("text", "")]
            assert len(auth_msg) >= 1
            
            auth_content = auth_msg[-1]["text"]
            assert "Enter admin PIN" in auth_content or "authorization code" in auth_content.lower()
            
            # Step 4: Admin provides security authorization
            admin_pin = harness.get_deterministic_otp()  # Use deterministic PIN
            pin_update = harness.create_user_update(
                user_id=admin_user_id,
                message_text=admin_pin
            )
            
            await admin_escrow_handler(pin_update, admin_context)
            
            # Should show final confirmation
            final_confirm_messages = harness.telegram.get_sent_messages(admin_user_id)
            final_msg = [msg for msg in final_confirm_messages if "FINAL CONFIRMATION" in msg.get("text", "")]
            assert len(final_msg) >= 1
            
            # Step 5: Final confirmation
            final_callback = harness.create_callback_update(
                user_id=admin_user_id,
                callback_data=f"admin_final_cancel_{escrow_id}_{admin_pin}"
            )
            
            await handle_admin_callback(final_callback, admin_context)
            
            # Verify cancellation executed
            success_messages = harness.telegram.get_sent_messages(admin_user_id)
            success_msg = [msg for msg in success_messages if "cancelled successfully" in msg.get("text", "").lower()]
            assert len(success_msg) >= 1
            
            # Step 6: Verify user notifications
            buyer_messages = harness.telegram.get_sent_messages(buyer_id)
            buyer_notification = [msg for msg in buyer_messages if "cancelled" in msg.get("text", "").lower() and "admin" in msg.get("text", "").lower()]
            assert len(buyer_notification) >= 1
            
            # Verify seller email notification
            seller_emails = harness.email.get_sent_emails(seller_email)
            seller_notification = [email for email in seller_emails if "cancelled" in email.get("subject", "").lower()]
            assert len(seller_notification) >= 1
            
            # Step 7: Verify audit trail
            async with harness.test_db_session() as session:
                from sqlalchemy import select
                from models import AdminAuditLog
                
                audit_result = await session.execute(
                    select(AdminAuditLog).where(
                        AdminAuditLog.action_type == AdminActionType.ESCROW_CANCELLATION
                    )
                )
                audit_logs = list(audit_result.scalars())
                
                cancellation_log = [log for log in audit_logs if escrow_id in str(log.details)]
                assert len(cancellation_log) >= 1
                
                log_entry = cancellation_log[-1]
                assert log_entry.admin_id == "ADMIN_001"
                assert "Security concern" in str(log_entry.details)
            
            # Step 8: Test insufficient permissions
            limited_admin_id = 88888888
            limited_context = harness.create_context(
                user_data={
                    "is_admin": True,
                    "admin_level": "basic",  # Lower level
                    "admin_permissions": ["view_stats"]  # No escrow management
                }
            )
            
            unauthorized_cancel = harness.create_callback_update(
                user_id=limited_admin_id,
                callback_data=f"admin_cancel_escrow_test_002"
            )
            
            await handle_admin_callback(unauthorized_cancel, limited_context)
            
            # Should get permission denied
            permission_messages = harness.telegram.get_sent_messages(limited_admin_id)
            denied_msg = [msg for msg in permission_messages if "permission" in msg.get("text", "").lower() or "unauthorized" in msg.get("text", "").lower()]
            assert len(denied_msg) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])