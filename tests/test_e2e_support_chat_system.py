"""
DEPRECATED - Test quarantined due to missing imports/deprecated modules
Reason: Missing test foundation module 'tests.e2e_test_foundation' (TelegramObjectFactory, CommunicationDatabaseHelper, NotificationVerifier, TimeController, provider_fakes)
Quarantined: 2025-10-16
Status: Needs rewrite against current architecture or permanent removal
"""

# """
# COMPREHENSIVE E2E TESTS FOR SUPPORT CHAT SYSTEM - PRODUCTION GRADE
# ====================================================================
#
# Complete End-to-End tests validating support chat workflows in LockBay.
# Tests prove users can access support and admins can manage tickets successfully
# without bugs across all user-to-admin communication operations.
#
# CRITICAL SUCCESS FACTORS:
# ✅ HERMETIC TESTING - All external services properly mocked at test scope
# ✅ NO LIVE API CALLS - Email service, admin notifications fully mocked
# ✅ DATABASE VALIDATION - Strong assertions on ticket states, message persistence
# ✅ SECURITY TESTING - Access control, admin privilege validation
# ✅ TICKET MANAGEMENT - Creation, assignment, escalation workflows tested
# ✅ MESSAGE ROUTING - User-admin communication and notification delivery
# ✅ ESCALATION WORKFLOWS - Priority handling, admin assignment validation
# ✅ SESSION CONSISTENCY - Proper session management throughout workflows
#
# SUPPORT CHAT WORKFLOWS TESTED:
# 1. User-to-Admin Support Chat Initiation (Ticket creation, initial contact)
# 2. Support Ticket Creation and Management (Assignment, status tracking, escalation)
# 3. Support Message Routing and Escalation (Admin notifications, priority handling)
# 4. Support Chat Resolution and Closure Workflows (Resolution tracking, follow-up)
#
# SUCCESS CRITERIA VALIDATION:
# - pytest tests/test_e2e_support_chat_system.py -v (ALL TESTS PASS)
# - Complete user support chat journeys validated end-to-end
# - Database state properly validated throughout support lifecycle
# - All support operations with proper security tested
# - Ticket management, escalation, and resolution workflows covered
# - Admin dashboard and support management comprehensively tested
# """
#
# import pytest
# import pytest_asyncio
# import asyncio
# import logging
# import json
# import uuid
# from decimal import Decimal
# from datetime import datetime, timedelta
# from typing import Dict, Any, Optional, List
# from unittest.mock import patch, AsyncMock, MagicMock, call
#
# # Core database and model imports
# import sys
# import os
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# from database import managed_session
# from models import (
#     User, SupportTicket, SupportMessage, UserStatus,
#     NotificationActivity, NotificationPreference, AdminAction
# )
# from sqlalchemy import select, text, update
#
# # Support services and handlers
# from handlers.support_chat import (
#     start_support_chat, show_support_chat_interface, handle_support_message_input,
#     notify_admins_new_ticket
# )
# # Note: admin_support handlers removed as they don't exist
# from services.consolidated_notification_service import (
#     ConsolidatedNotificationService, NotificationRequest, NotificationCategory, NotificationPriority
# )
#
# # Test foundation
# from tests.e2e_test_foundation import (
#     TelegramObjectFactory, 
#     CommunicationDatabaseHelper,
#     NotificationVerifier,
#     TimeController,
#     provider_fakes
# )
#
# # Utils
# from utils.helpers import generate_utid, get_user_display_name
# from utils.admin_security import is_admin_secure
# from utils.comprehensive_audit_logger import ComprehensiveAuditLogger
# from config import Config
#
# logger = logging.getLogger(__name__)
#
#
# @pytest.mark.e2e_support_chat
# class TestSupportChatE2E:
#     """Complete support chat E2E tests"""
#
#     @pytest.mark.asyncio
#     async def test_complete_user_support_chat_initiation_workflow(
#         self, 
#         test_db_session, 
#         patched_services,
#         mock_external_services
#     ):
#         """
#         Test complete user support chat initiation workflow
#
#         Journey:
#         1. User initiates support chat request
#         2. System creates new support ticket
#         3. User sends initial support message
#         4. Admin receives notification about new ticket
#         5. Ticket status and message tracking validation
#         """
#         logger.info("🧪 TESTING: Complete User Support Chat Initiation Workflow")
#
#         session = test_db_session
#         db_helper = CommunicationDatabaseHelper(session)
#         notification_verifier = NotificationVerifier()
#         time_controller = TimeController()
#
#         # === SETUP: Create test user ===
#         user_telegram = TelegramObjectFactory.create_user(
#             user_id=5590345001,
#             username="support_user",
#             first_name="Support",
#             last_name="User"
#         )
#
#         # Create database user using ORM (session already in transaction)
#         db_user = User(
#             telegram_id=str(user_telegram.id),
#             username=user_telegram.username,
#             first_name=user_telegram.first_name,
#             last_name=user_telegram.last_name,
#             email=f"support_user_{user_telegram.id}@example.com",
#             status=UserStatus.ACTIVE
#         )
#         session.add(db_user)
#         await session.flush()
#
#         # Create admin user for notifications
#         admin_telegram = TelegramObjectFactory.create_user(
#             user_id=5590345099,
#             username="support_admin",
#             first_name="Support",
#             last_name="Admin"
#         )
#
#         # Create admin user using ORM (session already in transaction)
#         admin_user = User(
#             telegram_id=str(admin_telegram.id),
#             username=admin_telegram.username,
#             first_name=admin_telegram.first_name,
#             last_name=admin_telegram.last_name,
#             email=f"support_admin_{admin_telegram.id}@example.com",
#             status=UserStatus.ACTIVE,
#             is_admin=True
#         )
#         session.add(admin_user)
#         await session.flush()
#
#         # Mock notification service responses
#         mock_external_services['notifications'].send_admin_notification.return_value = {
#             'success': True,
#             'notification_id': 'ADMIN_NOTIF_001',
#             'delivered_at': datetime.utcnow()
#         }
#
#         mock_external_services['email'].send_support_notification.return_value = {
#             'success': True,
#             'message_id': 'EMAIL_001',
#             'sent_at': datetime.utcnow()
#         }
#
#         # === TEST PHASE 1: User Initiates Support Chat ===
#         logger.info("🆘 PHASE 1: Testing user initiates support chat")
#
#         # Create Telegram update for support chat initiation
#         support_update = TelegramObjectFactory.create_update(
#             user=user_telegram,
#             callback_query=TelegramObjectFactory.create_callback_query(
#                 user_telegram, "start_support_chat"
#             )
#         )
#         support_context = TelegramObjectFactory.create_context()
#
#         # Mock support chat initiation with proper async session handling
#         with patch('handlers.support_chat.SyncSessionLocal') as mock_sync_session:
#             # Create async context manager that returns our test session
#             async def async_session_context():
#                 yield session
#
#             mock_sync_session.return_value = session
#
#             with patch('handlers.support_chat.safe_edit_message_text') as mock_edit:
#                 with patch('handlers.support_chat.notify_admins_new_ticket') as mock_notify_admins:
#                     # Simulate support chat start
#                     result = await start_support_chat(support_update, support_context)
#
#                     # Verify support chat interface was shown
#                     mock_edit.assert_called()
#                     mock_notify_admins.assert_called_once()
#
#                     # Result should indicate successful conversation start
#                     assert result is not None, "Support chat initiation should return conversation state"
#
#         # Create support ticket using ORM (session already in transaction)
#         ticket_id = "SUP-001"
#         ticket_created_at = datetime.utcnow()
#
#         support_ticket = SupportTicket(
#             ticket_id=ticket_id,
#             user_id=db_user.id,
#             subject="Live Chat Support",
#             status="open",
#             priority="normal",
#             created_at=ticket_created_at,
#             last_message_at=ticket_created_at
#         )
#         session.add(support_ticket)
#         await session.flush()
#         ticket_db_id = support_ticket.id
#
#         # === TEST PHASE 2: User Sends Initial Support Message ===
#         logger.info("💬 PHASE 2: Testing user sends initial support message")
#
#         initial_message_text = "Hi, I need help with my account. I'm having trouble accessing my wallet balance."
#
#         # Create user message update
#         message_update = TelegramObjectFactory.create_update(
#             user=user_telegram,
#             message=TelegramObjectFactory.create_message(user_telegram, initial_message_text)
#         )
#         message_context = TelegramObjectFactory.create_context({
#             'active_support_ticket': ticket_db_id,
#             'support_chat_mode': True
#         })
#
#         # Insert user's initial message using ORM (session already in transaction)
#         user_message_created_at = datetime.utcnow()
#         support_message = SupportMessage(
#             ticket_id=ticket_db_id,
#             sender_id=db_user.id,
#             message_text=initial_message_text,
#             is_admin_message=False,
#             message_type='text',
#             created_at=user_message_created_at
#         )
#         session.add(support_message)
#
#         # Update ticket last message time using ORM
#         from sqlalchemy import update
#         update_stmt = update(SupportTicket).where(
#             SupportTicket.id == ticket_db_id
#         ).values(last_message_at=user_message_created_at)
#         await session.execute(update_stmt)
#         await session.flush()
#
#         # === TEST PHASE 3: Admin Receives Notification ===
#         logger.info("🔔 PHASE 3: Testing admin receives notification about new ticket")
#
#         # Add admin notification activity using ORM (session already in transaction)
#         notification_activity = NotificationActivity(
#             activity_id=f"ADMIN_NOTIF_{uuid.uuid4().hex[:8]}",
#             user_id=admin_user.id,
#             notification_type="new_support_ticket",
#             channel_type="telegram",
#             channel_value=str(admin_telegram.id),
#             sent_at=ticket_created_at,
#             delivered_at=ticket_created_at + timedelta(seconds=5),
#             was_successful=True,
#             created_at=ticket_created_at
#         )
#         session.add(notification_activity)
#         await session.flush()
#
#         # Verify admin notification was created using ORM
#         from sqlalchemy import select
#         notifications_query = select(NotificationActivity).where(
#             NotificationActivity.notification_type == 'new_support_ticket'
#         )
#         admin_notifications_result = await session.execute(notifications_query)
#         notifications = list(admin_notifications_result.scalars())
#
#         assert len(notifications) >= 1, "Admin should receive notification about new ticket"
#         notification = notifications[0]
#         assert notification.user_id == admin_user.id
#         assert notification.was_successful is True
#
#         # === TEST PHASE 4: Ticket Status and Message Validation ===
#         logger.info("📋 PHASE 4: Testing ticket status and message tracking validation")
#
#         # Verify ticket creation and status using ORM
#         ticket_query = select(SupportTicket).where(
#             SupportTicket.ticket_id == ticket_id
#         )
#         ticket_result = await session.execute(ticket_query)
#         ticket = ticket_result.scalar_one_or_none()
#
#         assert ticket is not None, "Support ticket should be created"
#         assert ticket.user_id == db_user.id, "Ticket should belong to correct user"
#         assert ticket.status == "open", "New ticket should have 'open' status"
#         assert ticket.priority == "normal", "Default priority should be 'normal'"
#         assert ticket.subject == "Live Chat Support", "Subject should be set"
#         assert ticket.admin_id is None, "New ticket should not be assigned yet"
#
#         # Verify message persistence using ORM
#         messages_query = select(SupportMessage).where(
#             SupportMessage.ticket_id == ticket_db_id
#         )
#         messages_result = await session.execute(messages_query)
#         messages = list(messages_result.scalars())
#
#         assert len(messages) == 1, "Should have one initial message"
#         message = messages[0]
#         assert message.sender_id == db_user.id, "Message should be from user"
#         assert message.message_text == initial_message_text
#         assert message.is_admin_message is False, "User message should not be marked as admin"
#         assert message.message_type == "text"
#
#         # Verify ticket last message time was updated
#         assert ticket.last_message_at == user_message_created_at, "Last message time should be updated"
#
#         logger.info("✅ USER SUPPORT CHAT INITIATION: All workflows validated successfully")
#
#     @pytest.mark.asyncio
#     async def test_support_ticket_creation_and_management_workflow(
#         self,
#         test_db_session,
#         patched_services,
#         mock_external_services
#     ):
#         """
#         Test support ticket creation and comprehensive management workflow
#
#         Journey:
#         1. Create multiple support tickets with different priorities
#         2. Test admin assignment and ticket status transitions
#         3. Validate escalation and priority management
#         4. Test ticket analytics and reporting
#         """
#         logger.info("🧪 TESTING: Support Ticket Creation & Management Workflow")
#
#         session = test_db_session
#         db_helper = CommunicationDatabaseHelper(session)
#         time_controller = TimeController()
#
#         # === SETUP: Create test users and admins ===
#         users = []
#         for i in range(3):
#             user_telegram = TelegramObjectFactory.create_user(
#                 user_id=5590345010 + i,
#                 username=f"user_{i+1}",
#                 first_name=f"User{i+1}",
#                 last_name="Support"
#             )
#
#             db_user = await db_helper.create_user(
#                 telegram_id=str(user_telegram.id),
#                 username=user_telegram.username,
#                 first_name=user_telegram.first_name,
#                 last_name=user_telegram.last_name,
#                 status=UserStatus.ACTIVE
#             )
#
#             users.append((user_telegram, db_user))
#
#         # Create admin users
#         admins = []
#         for i in range(2):
#             admin_telegram = TelegramObjectFactory.create_user(
#                 user_id=5590345090 + i,
#                 username=f"admin_{i+1}",
#                 first_name=f"Admin{i+1}",
#                 last_name="Support"
#             )
#
#             admin_user = await db_helper.create_user(
#                 telegram_id=str(admin_telegram.id),
#                 username=admin_telegram.username,
#                 first_name=admin_telegram.first_name,
#                 last_name=admin_telegram.last_name,
#                 status=UserStatus.ACTIVE,
#                 is_admin=True
#             )
#
#             admins.append((admin_telegram, admin_user))
#
#         # === TEST PHASE 1: Create Multiple Support Tickets ===
#         logger.info("🎫 PHASE 1: Creating multiple support tickets with different priorities")
#
#         ticket_configs = [
#             {"user_idx": 0, "priority": "urgent", "subject": "Payment Issue - Money Missing"},
#             {"user_idx": 1, "priority": "high", "subject": "Account Locked - Cannot Login"},
#             {"user_idx": 2, "priority": "normal", "subject": "General Question About Features"},
#             {"user_idx": 0, "priority": "low", "subject": "Feature Request - UI Improvement"},
#         ]
#
#         created_tickets = []
#         base_time = datetime.utcnow() - timedelta(hours=2)
#
#         for i, config in enumerate(ticket_configs):
#             ticket_id = f"SUP-{(i+1):03d}"
#             ticket_time = base_time + timedelta(minutes=i*15)
#             user_telegram, user_db = users[config["user_idx"]]
#
#             await session.execute(
#                 """INSERT INTO support_tickets 
#                 (ticket_id, user_id, subject, status, priority, created_at, last_message_at)
#                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
#                 (
#                     ticket_id, user_db.id, config["subject"], "open", config["priority"], 
#                     ticket_time, ticket_time
#                 )
#             )
#
#             # Get ticket DB ID
#             ticket_query = await session.execute(
#                 "SELECT id FROM support_tickets WHERE ticket_id = ?",
#                 (ticket_id,)
#             )
#             ticket_record = ticket_query.fetchone()
#
#             created_tickets.append({
#                 "ticket_id": ticket_id,
#                 "db_id": ticket_record.id,
#                 "user": user_db,
#                 "priority": config["priority"],
#                 "subject": config["subject"],
#                 "created_at": ticket_time
#             })
#
#             # Add initial message for each ticket
#             initial_message = f"Initial support request for {config['subject']}"
#             await session.execute(
#                 """INSERT INTO support_messages 
#                 (ticket_id, sender_id, message_text, is_admin_message, message_type, created_at)
#                 VALUES (?, ?, ?, ?, ?, ?)""",
#                 (
#                     ticket_record.id, user_db.id, initial_message, False, 'text', ticket_time
#                 )
#             )
#
#         # === TEST PHASE 2: Admin Assignment and Status Transitions ===
#         logger.info("👨‍💼 PHASE 2: Testing admin assignment and ticket status transitions")
#
#         # Assign urgent and high priority tickets to Admin 1
#         admin1_telegram, admin1_db = admins[0]
#         urgent_ticket = created_tickets[0]  # urgent priority
#         high_ticket = created_tickets[1]    # high priority
#
#         # Assign urgent ticket
#         assignment_time = datetime.utcnow()
#         await session.execute(
#             "UPDATE support_tickets SET admin_id = ?, status = ? WHERE id = ?",
#             (admin1_db.id, "assigned", urgent_ticket["db_id"])
#         )
#
#         # Add admin action record
#         await session.execute(
#             """INSERT INTO admin_actions 
#             (admin_id, action_type, target_type, target_id, description, created_at)
#             VALUES (?, ?, ?, ?, ?, ?)""",
#             (
#                 admin1_db.id, "ticket_assignment", "support_ticket", urgent_ticket["ticket_id"],
#                 f"Assigned urgent ticket {urgent_ticket['ticket_id']} to admin", assignment_time
#             )
#         )
#
#         # Assign high priority ticket to Admin 2
#         admin2_telegram, admin2_db = admins[1]
#         await session.execute(
#             "UPDATE support_tickets SET admin_id = ?, status = ? WHERE id = ?",
#             (admin2_db.id, "assigned", high_ticket["db_id"])
#         )
#
#         # Verify assignments
#         assigned_tickets = await session.execute(
#             "SELECT * FROM support_tickets WHERE status = 'assigned'"
#         )
#         assigned = assigned_tickets.fetchall()
#
#         assert len(assigned) == 2, "Should have 2 assigned tickets"
#
#         # Find specific assigned tickets
#         admin1_assigned = next((t for t in assigned if t.admin_id == admin1_db.id), None)
#         admin2_assigned = next((t for t in assigned if t.admin_id == admin2_db.id), None)
#
#         assert admin1_assigned is not None, "Admin 1 should have assigned ticket"
#         assert admin1_assigned.priority == "urgent", "Admin 1 should have urgent ticket"
#         assert admin2_assigned is not None, "Admin 2 should have assigned ticket"
#         assert admin2_assigned.priority == "high", "Admin 2 should have high ticket"
#
#         # === TEST PHASE 3: Escalation and Priority Management ===
#         logger.info("⬆️ PHASE 3: Testing escalation and priority management")
#
#         # Escalate normal priority ticket to high
#         normal_ticket = created_tickets[2]  # normal priority
#         escalation_time = datetime.utcnow()
#
#         await session.execute(
#             "UPDATE support_tickets SET priority = ? WHERE id = ?",
#             ("high", normal_ticket["db_id"])
#         )
#
#         # Add escalation admin action
#         await session.execute(
#             """INSERT INTO admin_actions 
#             (admin_id, action_type, target_type, target_id, description, created_at)
#             VALUES (?, ?, ?, ?, ?, ?)""",
#             (
#                 admin1_db.id, "ticket_escalation", "support_ticket", normal_ticket["ticket_id"],
#                 f"Escalated ticket {normal_ticket['ticket_id']} from normal to high priority", escalation_time
#             )
#         )
#
#         # Test priority-based ticket sorting
#         priority_sorted = await session.execute(
#             """SELECT * FROM support_tickets 
#             ORDER BY 
#                 CASE priority 
#                     WHEN 'urgent' THEN 1 
#                     WHEN 'high' THEN 2 
#                     WHEN 'normal' THEN 3 
#                     WHEN 'low' THEN 4 
#                 END, 
#                 created_at ASC"""
#         )
#         sorted_tickets = priority_sorted.fetchall()
#
#         # Verify sorting (urgent first, then high, etc.)
#         priorities = [t.priority for t in sorted_tickets]
#         expected_order = ["urgent", "high", "high", "low"]  # One escalated from normal to high
#         assert priorities == expected_order, f"Priority sorting incorrect: {priorities}"
#
#         # === TEST PHASE 4: Ticket Analytics and Reporting ===
#         logger.info("📊 PHASE 4: Testing ticket analytics and reporting")
#
#         # Test analytics queries
#         analytics_query = await session.execute(
#             """SELECT 
#                 COUNT(*) as total_tickets,
#                 COUNT(CASE WHEN status = 'open' THEN 1 END) as open_tickets,
#                 COUNT(CASE WHEN status = 'assigned' THEN 1 END) as assigned_tickets,
#                 COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_tickets,
#                 COUNT(CASE WHEN priority = 'urgent' THEN 1 END) as urgent_tickets,
#                 COUNT(CASE WHEN priority = 'high' THEN 1 END) as high_tickets,
#                 COUNT(CASE WHEN priority = 'normal' THEN 1 END) as normal_tickets,
#                 COUNT(CASE WHEN priority = 'low' THEN 1 END) as low_tickets,
#                 COUNT(CASE WHEN admin_id IS NOT NULL THEN 1 END) as assigned_to_admin
#             FROM support_tickets"""
#         )
#         analytics = analytics_query.fetchone()
#
#         assert analytics.total_tickets == 4, "Should have 4 total tickets"
#         assert analytics.open_tickets == 2, "Should have 2 open tickets"  # normal escalated + low priority
#         assert analytics.assigned_tickets == 2, "Should have 2 assigned tickets"
#         assert analytics.urgent_tickets == 1, "Should have 1 urgent ticket"
#         assert analytics.high_tickets == 2, "Should have 2 high tickets (1 original + 1 escalated)"
#         assert analytics.normal_tickets == 0, "Should have 0 normal tickets (one escalated)"
#         assert analytics.low_tickets == 1, "Should have 1 low ticket"
#         assert analytics.assigned_to_admin == 2, "Should have 2 tickets assigned to admins"
#
#         # Test admin workload distribution
#         admin_workload = await session.execute(
#             """SELECT 
#                 u.first_name, u.last_name, 
#                 COUNT(st.id) as assigned_tickets,
#                 COUNT(CASE WHEN st.priority = 'urgent' THEN 1 END) as urgent_count,
#                 COUNT(CASE WHEN st.priority = 'high' THEN 1 END) as high_count
#             FROM users u
#             LEFT JOIN support_tickets st ON u.id = st.admin_id AND st.status = 'assigned'
#             WHERE u.is_admin = true
#             GROUP BY u.id, u.first_name, u.last_name"""
#         )
#         workload_results = admin_workload.fetchall()
#
#         assert len(workload_results) == 2, "Should have workload data for 2 admins"
#
#         # Find specific admin workloads
#         admin1_workload = next((w for w in workload_results if w.first_name == "Admin1"), None)
#         admin2_workload = next((w for w in workload_results if w.first_name == "Admin2"), None)
#
#         assert admin1_workload is not None, "Should have workload data for Admin1"
#         assert admin1_workload.assigned_tickets == 1, "Admin1 should have 1 assigned ticket"
#         assert admin1_workload.urgent_count == 1, "Admin1 should have 1 urgent ticket"
#
#         assert admin2_workload is not None, "Should have workload data for Admin2"
#         assert admin2_workload.assigned_tickets == 1, "Admin2 should have 1 assigned ticket"
#         assert admin2_workload.high_count == 1, "Admin2 should have 1 high ticket"
#
#         # === VERIFICATION: Database Integrity ===
#         logger.info("🔍 VERIFICATION: Checking database integrity")
#
#         # Verify ticket-message relationship integrity
#         message_count_check = await session.execute(
#             """SELECT st.ticket_id, COUNT(sm.id) as message_count
#             FROM support_tickets st
#             LEFT JOIN support_messages sm ON st.id = sm.ticket_id
#             GROUP BY st.id, st.ticket_id"""
#         )
#         message_counts = message_count_check.fetchall()
#
#         for count_result in message_counts:
#             assert count_result.message_count >= 1, f"Ticket {count_result.ticket_id} should have at least 1 message"
#
#         # Verify admin action audit trail
#         admin_actions = await session.execute(
#             "SELECT * FROM admin_actions ORDER BY created_at ASC"
#         )
#         actions = admin_actions.fetchall()
#
#         assert len(actions) >= 2, "Should have admin actions for assignment and escalation"
#         assignment_action = actions[0]
#         assert assignment_action.action_type == "ticket_assignment"
#         assert assignment_action.target_type == "support_ticket"
#
#         escalation_action = next((a for a in actions if a.action_type == "ticket_escalation"), None)
#         assert escalation_action is not None, "Should have escalation action"
#
#         logger.info("✅ SUPPORT TICKET MANAGEMENT: All workflows validated successfully")
#
#     async def test_support_message_routing_and_escalation_workflow(
#         self,
#         test_db_session,
#         patched_services,
#         mock_external_services
#     ):
#         """
#         Test support message routing and escalation workflows
#
#         Journey:
#         1. Test bidirectional messaging between users and admins
#         2. Validate message routing and notification patterns
#         3. Test escalation triggers and workflows
#         4. Verify message history and thread management
#         """
#         logger.info("🧪 TESTING: Support Message Routing & Escalation Workflow")
#
#         session = test_db_session
#         db_helper = CommunicationDatabaseHelper(session)
#         time_controller = TimeController()
#
#         # === SETUP: Create user, admin, and support ticket ===
#         user_telegram = TelegramObjectFactory.create_user(
#             user_id=5590345021,
#             username="routing_user",
#             first_name="Routing",
#             last_name="User"
#         )
#
#         admin_telegram = TelegramObjectFactory.create_user(
#             user_id=5590345091,
#             username="routing_admin",
#             first_name="Routing",
#             last_name="Admin"
#         )
#
#         user_db = await db_helper.create_user(
#             telegram_id=str(user_telegram.id),
#             username=user_telegram.username,
#             first_name=user_telegram.first_name,
#             last_name=user_telegram.last_name,
#             status=UserStatus.ACTIVE
#         )
#
#         admin_db = await db_helper.create_user(
#             telegram_id=str(admin_telegram.id),
#             username=admin_telegram.username,
#             first_name=admin_telegram.first_name,
#             last_name=admin_telegram.last_name,
#             status=UserStatus.ACTIVE,
#             is_admin=True
#         )
#
#         # Create support ticket
#         ticket_id = "SUP-ROUTE-001"
#         ticket_created_at = datetime.utcnow()
#
#         await session.execute(
#             """INSERT INTO support_tickets 
#             (ticket_id, user_id, admin_id, subject, status, priority, created_at, last_message_at)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
#             (
#                 ticket_id, user_db.id, admin_db.id, "Test Routing Issue", 
#                 "assigned", "normal", ticket_created_at, ticket_created_at
#             )
#         )
#
#         ticket_query = await session.execute(
#             "SELECT id FROM support_tickets WHERE ticket_id = ?",
#             (ticket_id,)
#         )
#         ticket_record = ticket_query.fetchone()
#         ticket_db_id = ticket_record.id
#
#         # === TEST PHASE 1: Bidirectional User-Admin Messaging ===
#         logger.info("💬 PHASE 1: Testing bidirectional user-admin messaging")
#
#         base_time = datetime.utcnow() - timedelta(hours=1)
#         conversation_messages = [
#             # User initiates
#             (user_db.id, "Hi, I'm having trouble with my account balance showing incorrectly.", False, "text"),
#
#             # Admin responds
#             (admin_db.id, "Hello! I can help you with that. Can you tell me when you first noticed this issue?", True, "text"),
#
#             # User provides details
#             (user_db.id, "It started yesterday after I made a deposit. The amount shows as pending but never confirmed.", False, "text"),
#
#             # Admin asks for evidence
#             (admin_db.id, "Thank you for the details. Can you please provide a screenshot of your transaction history?", True, "text"),
#
#             # User sends screenshot
#             (user_db.id, "Here's the screenshot you requested", False, "image"),
#
#             # Admin confirms and provides solution
#             (admin_db.id, "I can see the issue. Your deposit is being processed by our payment provider. It should confirm within 2 hours. I'll monitor this for you.", True, "text"),
#
#             # User thanks admin
#             (user_db.id, "Thank you so much for the quick help! I'll wait for the confirmation.", False, "text"),
#         ]
#
#         created_message_ids = []
#         for i, (sender_id, message_text, is_admin, msg_type) in enumerate(conversation_messages):
#             message_time = base_time + timedelta(minutes=i*5)
#
#             # Add file metadata for image message
#             file_id = "IMG_SUPPORT_001" if msg_type == "image" else None
#             file_name = "transaction_screenshot.jpg" if msg_type == "image" else None
#
#             await session.execute(
#                 """INSERT INTO support_messages 
#                 (ticket_id, sender_id, message_text, is_admin_message, message_type, 
#                  file_id, file_name, created_at)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
#                 (
#                     ticket_db_id, sender_id, message_text, is_admin, msg_type,
#                     file_id, file_name, message_time
#                 )
#             )
#
#             # Get message ID for tracking
#             message_query = await session.execute(
#                 "SELECT id FROM support_messages WHERE ticket_id = ? AND created_at = ?",
#                 (ticket_db_id, message_time)
#             )
#             message_record = message_query.fetchone()
#             created_message_ids.append(message_record.id)
#
#             # Update ticket last message time
#             await session.execute(
#                 "UPDATE support_tickets SET last_message_at = ? WHERE id = ?",
#                 (message_time, ticket_db_id)
#             )
#
#         # === TEST PHASE 2: Message Routing and Notification Patterns ===
#         logger.info("🔔 PHASE 2: Testing message routing and notification patterns")
#
#         # Add notification activities for each message
#         for i, (sender_id, message_text, is_admin, msg_type) in enumerate(conversation_messages):
#             message_time = base_time + timedelta(minutes=i*5)
#
#             # Determine notification recipient (opposite of sender)
#             if is_admin:
#                 # Admin sent message, notify user
#                 recipient_id = user_db.id
#                 recipient_telegram_id = str(user_telegram.id)
#                 notification_type = "support_admin_reply"
#             else:
#                 # User sent message, notify admin
#                 recipient_id = admin_db.id
#                 recipient_telegram_id = str(admin_telegram.id)
#                 notification_type = "support_user_message"
#
#             await session.execute(
#                 """INSERT INTO notification_activities 
#                 (activity_id, user_id, notification_type, channel_type, channel_value, 
#                  sent_at, delivered_at, was_successful, created_at)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
#                 (
#                     f"SUPPORT_MSG_{i}_{uuid.uuid4().hex[:8]}", recipient_id, notification_type,
#                     "telegram", recipient_telegram_id, message_time, 
#                     message_time + timedelta(seconds=10), True, message_time
#                 )
#             )
#
#         # Verify notification routing
#         user_notifications = await session.execute(
#             "SELECT * FROM notification_activities WHERE user_id = ? AND notification_type = 'support_admin_reply'",
#             (user_db.id,)
#         )
#         user_notifs = user_notifications.fetchall()
#
#         admin_notifications = await session.execute(
#             "SELECT * FROM notification_activities WHERE user_id = ? AND notification_type = 'support_user_message'",
#             (admin_db.id,)
#         )
#         admin_notifs = admin_notifications.fetchall()
#
#         # Should have notifications for admin messages to user
#         admin_message_count = len([m for m in conversation_messages if m[2]])  # is_admin = True
#         user_message_count = len([m for m in conversation_messages if not m[2]])  # is_admin = False
#
#         assert len(user_notifs) == admin_message_count, f"User should receive {admin_message_count} admin reply notifications"
#         assert len(admin_notifs) == user_message_count, f"Admin should receive {user_message_count} user message notifications"
#
#         # === TEST PHASE 3: Escalation Triggers and Workflows ===
#         logger.info("⬆️ PHASE 3: Testing escalation triggers and workflows")
#
#         # Simulate escalation scenario - user not satisfied with response
#         escalation_time = datetime.utcnow()
#
#         # User sends escalation message
#         escalation_message = "I'm still not seeing the deposit after 3 hours. This is urgent - I need this resolved immediately."
#
#         await session.execute(
#             """INSERT INTO support_messages 
#             (ticket_id, sender_id, message_text, is_admin_message, message_type, created_at)
#             VALUES (?, ?, ?, ?, ?, ?)""",
#             (
#                 ticket_db_id, user_db.id, escalation_message, False, 'text', escalation_time
#             )
#         )
#
#         # Trigger escalation - update ticket priority
#         await session.execute(
#             "UPDATE support_tickets SET priority = ?, status = ? WHERE id = ?",
#             ("urgent", "assigned", ticket_db_id)
#         )
#
#         # Add escalation admin action
#         await session.execute(
#             """INSERT INTO admin_actions 
#             (admin_id, action_type, target_type, target_id, description, created_at)
#             VALUES (?, ?, ?, ?, ?, ?)""",
#             (
#                 admin_db.id, "ticket_escalation", "support_ticket", ticket_id,
#                 "Auto-escalated to urgent due to user follow-up after 3 hours", escalation_time
#             )
#         )
#
#         # Add urgent escalation notification to senior admin (simulated)
#         await session.execute(
#             """INSERT INTO notification_activities 
#             (activity_id, user_id, notification_type, channel_type, channel_value, 
#              sent_at, delivered_at, was_successful, created_at)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
#             (
#                 f"ESCALATION_{uuid.uuid4().hex[:8]}", admin_db.id, "urgent_ticket_escalation",
#                 "telegram", str(admin_telegram.id), escalation_time, 
#                 escalation_time + timedelta(seconds=5), True, escalation_time
#             )
#         )
#
#         # Verify escalation
#         escalated_ticket = await session.execute(
#             "SELECT * FROM support_tickets WHERE id = ?",
#             (ticket_db_id,)
#         )
#         ticket_after_escalation = escalated_ticket.fetchone()
#
#         assert ticket_after_escalation.priority == "urgent", "Ticket should be escalated to urgent"
#         assert ticket_after_escalation.status == "assigned", "Ticket should remain assigned during escalation"
#
#         # === TEST PHASE 4: Message History and Thread Management ===
#         logger.info("📜 PHASE 4: Testing message history and thread management")
#
#         # Retrieve complete conversation history
#         conversation_history = await session.execute(
#             """SELECT sm.*, u.first_name, u.last_name, u.is_admin
#             FROM support_messages sm
#             JOIN users u ON sm.sender_id = u.id
#             WHERE sm.ticket_id = ?
#             ORDER BY sm.created_at ASC""",
#             (ticket_db_id,)
#         )
#         history = conversation_history.fetchall()
#
#         total_expected_messages = len(conversation_messages) + 1  # +1 for escalation message
#         assert len(history) == total_expected_messages, f"Should have {total_expected_messages} messages in history"
#
#         # Verify conversation flow and alternating participants
#         user_messages = [h for h in history if not h.is_admin_message]
#         admin_messages = [h for h in history if h.is_admin_message]
#
#         assert len(user_messages) >= 4, "Should have multiple user messages"
#         assert len(admin_messages) >= 3, "Should have multiple admin messages"
#
#         # Verify chronological ordering
#         for i in range(1, len(history)):
#             prev_msg = history[i-1]
#             curr_msg = history[i]
#             assert prev_msg.created_at <= curr_msg.created_at, f"Messages should be chronologically ordered (index {i})"
#
#         # Verify file attachment handling
#         image_messages = [h for h in history if h.message_type == "image"]
#         assert len(image_messages) == 1, "Should have one image message"
#         image_msg = image_messages[0]
#         assert image_msg.file_id == "IMG_SUPPORT_001"
#         assert image_msg.file_name == "transaction_screenshot.jpg"
#
#         # Test conversation threading and context
#         conversation_export = await session.execute(
#             """SELECT 
#                 sm.created_at,
#                 CASE WHEN sm.is_admin_message THEN 'Admin' ELSE 'User' END as sender_type,
#                 u.first_name as sender_name,
#                 sm.message_text,
#                 sm.message_type
#             FROM support_messages sm
#             JOIN users u ON sm.sender_id = u.id
#             WHERE sm.ticket_id = ?
#             ORDER BY sm.created_at ASC""",
#             (ticket_db_id,)
#         )
#         conversation_thread = conversation_export.fetchall()
#
#         # Verify conversation maintains context and flows naturally
#         for msg in conversation_thread:
#             assert msg.sender_type in ["Admin", "User"], "Sender type should be identified"
#             assert msg.sender_name is not None, "Sender name should be included"
#             assert len(msg.message_text.strip()) > 0, "Message should have content"
#
#         # === VERIFICATION: Support System Integrity ===
#         logger.info("🔍 VERIFICATION: Checking support system integrity")
#
#         # Verify ticket-message relationship consistency
#         ticket_validation = await session.execute(
#             """SELECT 
#                 st.ticket_id, st.last_message_at,
#                 MAX(sm.created_at) as latest_message_time,
#                 COUNT(sm.id) as total_messages
#             FROM support_tickets st
#             LEFT JOIN support_messages sm ON st.id = sm.ticket_id
#             WHERE st.id = ?
#             GROUP BY st.id, st.ticket_id, st.last_message_at""",
#             (ticket_db_id,)
#         )
#         validation_result = ticket_validation.fetchone()
#
#         assert validation_result.latest_message_time == validation_result.last_message_at, "Last message time should match latest message"
#         assert validation_result.total_messages == total_expected_messages, "Message count should be consistent"
#
#         # Verify notification coverage (every message should trigger notification)
#         notification_coverage = await session.execute(
#             "SELECT COUNT(*) as count FROM notification_activities WHERE notification_type LIKE 'support_%'",
#         )
#         notif_count = notification_coverage.fetchone()
#         expected_notifications = total_expected_messages  # Each message triggers a notification
#         assert notif_count.count >= expected_notifications, "Should have comprehensive notification coverage"
#
#         # Verify escalation audit trail
#         escalation_actions = await session.execute(
#             "SELECT * FROM admin_actions WHERE action_type = 'ticket_escalation' AND target_id = ?",
#             (ticket_id,)
#         )
#         escalation_audit = escalation_actions.fetchall()
#
#         assert len(escalation_audit) >= 1, "Should have escalation audit trail"
#         escalation_record = escalation_audit[0]
#         assert escalation_record.admin_id == admin_db.id
#         assert "urgent" in escalation_record.description.lower()
#
#         logger.info("✅ SUPPORT MESSAGE ROUTING & ESCALATION: All workflows validated successfully")
#
#
# @pytest.mark.e2e_support_resolution
# class TestSupportResolutionWorkflows:
#     """Support chat resolution and closure workflow tests"""
#
#     async def test_support_chat_resolution_and_closure_workflow(
#         self,
#         test_db_session,
#         patched_services,
#         mock_external_services
#     ):
#         """
#         Test support chat resolution and closure workflows
#
#         Journey:
#         1. Complete support ticket from assignment to resolution
#         2. Test resolution confirmation and user satisfaction
#         3. Validate closure procedures and follow-up
#         4. Test analytics and performance metrics
#         """
#         logger.info("🧪 TESTING: Support Chat Resolution & Closure Workflow")
#
#         session = test_db_session
#         db_helper = CommunicationDatabaseHelper(session)
#         time_controller = TimeController()
#
#         # === SETUP: Create complete support scenario ===
#         user_telegram = TelegramObjectFactory.create_user(
#             user_id=5590345031,
#             username="resolution_user",
#             first_name="Resolution",
#             last_name="User"
#         )
#
#         admin_telegram = TelegramObjectFactory.create_user(
#             user_id=5590345092,
#             username="resolution_admin",
#             first_name="Resolution",
#             last_name="Admin"
#         )
#
#         user_db = await db_helper.create_user(
#             telegram_id=str(user_telegram.id),
#             username=user_telegram.username,
#             first_name=user_telegram.first_name,
#             last_name=user_telegram.last_name,
#             status=UserStatus.ACTIVE
#         )
#
#         admin_db = await db_helper.create_user(
#             telegram_id=str(admin_telegram.id),
#             username=admin_telegram.username,
#             first_name=admin_telegram.first_name,
#             last_name=admin_telegram.last_name,
#             status=UserStatus.ACTIVE,
#             is_admin=True
#         )
#
#         # Create support ticket with complete lifecycle
#         ticket_id = "SUP-RESOLVE-001"
#         ticket_created_at = datetime.utcnow() - timedelta(hours=2)
#
#         await session.execute(
#             """INSERT INTO support_tickets 
#             (ticket_id, user_id, admin_id, subject, status, priority, created_at, last_message_at)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
#             (
#                 ticket_id, user_db.id, admin_db.id, "Account Balance Discrepancy", 
#                 "assigned", "high", ticket_created_at, ticket_created_at
#             )
#         )
#
#         ticket_query = await session.execute(
#             "SELECT id FROM support_tickets WHERE ticket_id = ?",
#             (ticket_id,)
#         )
#         ticket_record = ticket_query.fetchone()
#         ticket_db_id = ticket_record.id
#
#         # === TEST PHASE 1: Complete Resolution Process ===
#         logger.info("✅ PHASE 1: Testing complete support resolution process")
#
#         # Add conversation leading to resolution
#         resolution_conversation = [
#             (user_db.id, "My account balance is showing $50 less than it should be.", False),
#             (admin_db.id, "I'll investigate this right away. Can you provide your last transaction ID?", True),
#             (user_db.id, "The transaction ID is TXN-123456789. It was a deposit of $100.", False),
#             (admin_db.id, "I found the issue. There was a processing delay. I'm crediting the missing $50 to your account now.", True),
#             (admin_db.id, "Your account has been credited with $50. Please check your balance now.", True),
#             (user_db.id, "Perfect! I can see the correct balance now. Thank you so much for the quick resolution!", False),
#         ]
#
#         base_time = ticket_created_at + timedelta(minutes=10)
#         for i, (sender_id, message_text, is_admin) in enumerate(resolution_conversation):
#             message_time = base_time + timedelta(minutes=i*3)
#
#             await session.execute(
#                 """INSERT INTO support_messages 
#                 (ticket_id, sender_id, message_text, is_admin_message, message_type, created_at)
#                 VALUES (?, ?, ?, ?, ?, ?)""",
#                 (
#                     ticket_db_id, sender_id, message_text, is_admin, 'text', message_time
#                 )
#             )
#
#         # Admin resolves the ticket
#         resolution_time = base_time + timedelta(minutes=len(resolution_conversation)*3 + 5)
#
#         await session.execute(
#             "UPDATE support_tickets SET status = ?, resolved_at = ? WHERE id = ?",
#             ("resolved", resolution_time, ticket_db_id)
#         )
#
#         # Add resolution admin action
#         await session.execute(
#             """INSERT INTO admin_actions 
#             (admin_id, action_type, target_type, target_id, description, created_at)
#             VALUES (?, ?, ?, ?, ?, ?)""",
#             (
#                 admin_db.id, "ticket_resolution", "support_ticket", ticket_id,
#                 "Resolved account balance discrepancy by crediting missing funds", resolution_time
#             )
#         )
#
#         # === TEST PHASE 2: Resolution Confirmation and User Satisfaction ===
#         logger.info("😊 PHASE 2: Testing resolution confirmation and user satisfaction")
#
#         # Send resolution confirmation to user
#         await session.execute(
#             """INSERT INTO notification_activities 
#             (activity_id, user_id, notification_type, channel_type, channel_value, 
#              sent_at, delivered_at, was_successful, created_at)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
#             (
#                 f"RESOLUTION_{uuid.uuid4().hex[:8]}", user_db.id, "ticket_resolved",
#                 "telegram", str(user_telegram.id), resolution_time, 
#                 resolution_time + timedelta(seconds=10), True, resolution_time
#             )
#         )
#
#         # User provides satisfaction feedback (optional)
#         satisfaction_time = resolution_time + timedelta(minutes=10)
#         satisfaction_message = "⭐⭐⭐⭐⭐ Excellent support! Very quick and professional resolution."
#
#         await session.execute(
#             """INSERT INTO support_messages 
#             (ticket_id, sender_id, message_text, is_admin_message, message_type, created_at)
#             VALUES (?, ?, ?, ?, ?, ?)""",
#             (
#                 ticket_db_id, user_db.id, satisfaction_message, False, 'text', satisfaction_time
#             )
#         )
#
#         # Update ticket last message time
#         await session.execute(
#             "UPDATE support_tickets SET last_message_at = ? WHERE id = ?",
#             (satisfaction_time, ticket_db_id)
#         )
#
#         # === TEST PHASE 3: Closure Procedures and Follow-up ===
#         logger.info("🔒 PHASE 3: Testing closure procedures and follow-up")
#
#         # Admin closes ticket after confirmation
#         closure_time = satisfaction_time + timedelta(hours=1)
#
#         await session.execute(
#             "UPDATE support_tickets SET status = ?, closed_at = ? WHERE id = ?",
#             ("closed", closure_time, ticket_db_id)
#         )
#
#         # Add closure admin action
#         await session.execute(
#             """INSERT INTO admin_actions 
#             (admin_id, action_type, target_type, target_id, description, created_at)
#             VALUES (?, ?, ?, ?, ?, ?)""",
#             (
#                 admin_db.id, "ticket_closure", "support_ticket", ticket_id,
#                 "Closed ticket after user satisfaction confirmation", closure_time
#             )
#         )
#
#         # Send closure confirmation to user
#         await session.execute(
#             """INSERT INTO notification_activities 
#             (activity_id, user_id, notification_type, channel_type, channel_value, 
#              sent_at, delivered_at, was_successful, created_at)
#             VALUES (?, ?, ?, ?, ?, ?)""",
#             (
#                 f"CLOSURE_{uuid.uuid4().hex[:8]}", user_db.id, "ticket_closed",
#                 "telegram", str(user_telegram.id), closure_time, 
#                 closure_time + timedelta(seconds=5), True, closure_time
#             )
#         )
#
#         # === TEST PHASE 4: Analytics and Performance Metrics ===
#         logger.info("📊 PHASE 4: Testing analytics and performance metrics")
#
#         # Calculate resolution metrics
#         metrics_query = await session.execute(
#             """SELECT 
#                 st.ticket_id,
#                 st.created_at,
#                 st.resolved_at,
#                 st.closed_at,
#                 st.priority,
#                 ROUND(EXTRACT(EPOCH FROM (st.resolved_at - st.created_at)) / 60, 2) as resolution_time_minutes,
#                 ROUND(EXTRACT(EPOCH FROM (st.closed_at - st.created_at)) / 60, 2) as total_time_minutes,
#                 COUNT(sm.id) as total_messages,
#                 COUNT(CASE WHEN sm.is_admin_message THEN 1 END) as admin_messages,
#                 COUNT(CASE WHEN NOT sm.is_admin_message THEN 1 END) as user_messages
#             FROM support_tickets st
#             LEFT JOIN support_messages sm ON st.id = sm.ticket_id
#             WHERE st.id = ?
#             GROUP BY st.id, st.ticket_id, st.created_at, st.resolved_at, st.closed_at, st.priority""",
#             (ticket_db_id,)
#         )
#         metrics = metrics_query.fetchone()
#
#         # Verify resolution metrics
#         assert metrics.resolution_time_minutes is not None, "Resolution time should be calculated"
#         assert metrics.resolution_time_minutes > 0, "Resolution time should be positive"
#         assert metrics.total_time_minutes >= metrics.resolution_time_minutes, "Total time should be >= resolution time"
#         assert metrics.total_messages >= 6, "Should have multiple messages in conversation"
#         assert metrics.admin_messages >= 3, "Admin should have responded multiple times"
#         assert metrics.user_messages >= 3, "User should have sent multiple messages"
#
#         # Verify ticket status progression
#         final_ticket_state = await session.execute(
#             "SELECT * FROM support_tickets WHERE id = ?",
#             (ticket_db_id,)
#         )
#         final_ticket = final_ticket_state.fetchone()
#
#         assert final_ticket.status == "closed", "Ticket should be closed"
#         assert final_ticket.resolved_at is not None, "Ticket should have resolution timestamp"
#         assert final_ticket.closed_at is not None, "Ticket should have closure timestamp"
#         assert final_ticket.closed_at >= final_ticket.resolved_at, "Closure should be after resolution"
#
#         # Test performance benchmarks
#         expected_resolution_time = 30  # minutes for high priority
#         actual_resolution_time = metrics.resolution_time_minutes
#
#         # For high priority tickets, should be resolved within benchmark
#         if final_ticket.priority == "high":
#             performance_met = actual_resolution_time <= expected_resolution_time
#             logger.info(f"📊 Performance benchmark: {actual_resolution_time:.1f}m (target: {expected_resolution_time}m) - {'✅ MET' if performance_met else '❌ MISSED'}")
#
#         # Test admin workload metrics
#         admin_performance = await session.execute(
#             """SELECT 
#                 u.first_name, u.last_name,
#                 COUNT(st.id) as tickets_handled,
#                 AVG(EXTRACT(EPOCH FROM (st.resolved_at - st.created_at)) / 60) as avg_resolution_time,
#                 COUNT(CASE WHEN st.status = 'closed' THEN 1 END) as tickets_closed
#             FROM users u
#             LEFT JOIN support_tickets st ON u.id = st.admin_id
#             WHERE u.id = ? AND st.resolved_at IS NOT NULL
#             GROUP BY u.id, u.first_name, u.last_name""",
#             (admin_db.id,)
#         )
#         admin_metrics = admin_performance.fetchone()
#
#         assert admin_metrics is not None, "Should have admin performance metrics"
#         assert admin_metrics.tickets_handled >= 1, "Admin should have handled tickets"
#         assert admin_metrics.avg_resolution_time is not None, "Should have average resolution time"
#         assert admin_metrics.tickets_closed >= 1, "Admin should have closed tickets"
#
#         # === VERIFICATION: Complete Lifecycle Validation ===
#         logger.info("🔍 VERIFICATION: Checking complete support lifecycle")
#
#         # Verify complete audit trail
#         complete_audit = await session.execute(
#             """SELECT 
#                 aa.action_type, aa.description, aa.created_at,
#                 st.status, st.created_at as ticket_created, st.resolved_at, st.closed_at
#             FROM admin_actions aa
#             JOIN support_tickets st ON aa.target_id = st.ticket_id
#             WHERE aa.target_id = ?
#             ORDER BY aa.created_at ASC""",
#             (ticket_id,)
#         )
#         audit_trail = complete_audit.fetchall()
#
#         assert len(audit_trail) >= 2, "Should have complete audit trail (resolution + closure)"
#
#         # Verify audit trail progression
#         action_types = [a.action_type for a in audit_trail]
#         assert "ticket_resolution" in action_types, "Should have resolution action"
#         assert "ticket_closure" in action_types, "Should have closure action"
#
#         # Verify notification coverage for complete lifecycle
#         lifecycle_notifications = await session.execute(
#             """SELECT notification_type, COUNT(*) as count 
#             FROM notification_activities 
#             WHERE user_id = ? AND notification_type IN ('ticket_resolved', 'ticket_closed')
#             GROUP BY notification_type""",
#             (user_db.id,)
#         )
#         notif_coverage = lifecycle_notifications.fetchall()
#
#         notif_types = {n.notification_type: n.count for n in notif_coverage}
#         assert notif_types.get('ticket_resolved', 0) >= 1, "Should have resolution notification"
#         assert notif_types.get('ticket_closed', 0) >= 1, "Should have closure notification"
#
#         # Verify final ticket state integrity
#         assert final_ticket.created_at < final_ticket.resolved_at, "Creation should be before resolution"
#         assert final_ticket.resolved_at <= final_ticket.closed_at, "Resolution should be before or equal to closure"
#         assert final_ticket.admin_id == admin_db.id, "Admin assignment should be preserved"
#         assert final_ticket.user_id == user_db.id, "User association should be preserved"
#
#         logger.info("✅ SUPPORT RESOLUTION & CLOSURE: All workflows validated successfully")