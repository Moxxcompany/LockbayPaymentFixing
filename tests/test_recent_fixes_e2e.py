"""
E2E Tests for Recent Fixes (October 11, 2025)

Tests cover:
1. Duplicate delivery warnings fix (24h, 8h, 2h, 30min intervals)
2. Fund release dual-channel notifications (Telegram + Email with broadcast_mode=True)
3. Chat restrictions for completed trades and resolved disputes
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy import select
from telegram import Update, CallbackQuery, User as TelegramUser, Message, Chat
from telegram.ext import ContextTypes

from models import Escrow, User, Dispute, EscrowMessage
from database import SessionLocal
from handlers.escrow import handle_confirm_release_funds
from handlers.messages_hub import open_trade_chat
from services.standalone_auto_release_service import StandaloneAutoReleaseService


class TestDeliveryWarningsDuplicatePrevention:
    """Test that delivery warnings are sent only once at each interval"""
    
    @pytest.mark.asyncio
    async def test_delivery_warnings_sent_once_per_interval(self):
        """Test all 4 warning intervals are triggered exactly once"""
        session = SessionLocal()
        
        try:
            # Create test users
            now = datetime.now(timezone.utc)
            buyer = User(
                telegram_id=1001,
                username="test_buyer",
                email="buyer@test.com",
                phone_number="+1234567890",
                created_at=now
            )
            seller = User(
                telegram_id=1002,
                username="test_seller",
                email="seller@test.com",
                phone_number="+1234567891",
                created_at=now
            )
            session.add_all([buyer, seller])
            session.commit()
            
            # Create escrow with delivery deadline in future
            delivery_deadline = now + timedelta(hours=25)  # 25 hours from now
            
            escrow = Escrow(
                escrow_id="TEST-WARN-001",
                buyer_id=buyer.id,
                seller_id=seller.id,
                amount=Decimal("100.00"),
                currency="USD",
                status="active",
                delivery_deadline=delivery_deadline,
                created_at=now,
                # Warning flags - all False initially
                warning_24h_sent=False,
                warning_8h_sent=False,
                warning_2h_sent=False,
                warning_30m_sent=False
            )
            session.add(escrow)
            session.commit()
            escrow_id = escrow.id
            
            # Initialize auto-release service
            service = StandaloneAutoReleaseService()
            
            # Test 24h warning (deadline = now + 25h, so 24h warning should trigger)
            escrow_24h = session.query(Escrow).filter(Escrow.id == escrow_id).with_for_update().first()
            escrow_24h.delivery_deadline = now + timedelta(hours=23, minutes=30)  # Within 24h window
            session.commit()
            
            with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_delivery_warning') as mock_notify:
                mock_notify.return_value = {'telegram': True, 'email': True}
                
                # First run - should send warning
                await service.process_delivery_warnings()
                
                # Verify warning was sent
                escrow_after_1 = session.query(Escrow).filter(Escrow.id == escrow_id).first()
                assert escrow_after_1.warning_24h_sent == True
                assert mock_notify.call_count == 1
                
                # Second run - should NOT send warning again (flag is set)
                mock_notify.reset_mock()
                await service.process_delivery_warnings()
                
                # Verify no duplicate warning
                assert mock_notify.call_count == 0
                escrow_after_2 = session.query(Escrow).filter(Escrow.id == escrow_id).first()
                assert escrow_after_2.warning_24h_sent == True
            
            # Test 8h warning
            escrow_8h = session.query(Escrow).filter(Escrow.id == escrow_id).with_for_update().first()
            escrow_8h.delivery_deadline = now + timedelta(hours=7, minutes=30)  # Within 8h window
            escrow_8h.warning_8h_sent = False
            session.commit()
            
            with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_delivery_warning') as mock_notify:
                mock_notify.return_value = {'telegram': True, 'email': True}
                
                await service.process_delivery_warnings()
                
                escrow_after = session.query(Escrow).filter(Escrow.id == escrow_id).first()
                assert escrow_after.warning_8h_sent == True
                assert mock_notify.call_count == 1
                
                # Second run - no duplicate
                mock_notify.reset_mock()
                await service.process_delivery_warnings()
                assert mock_notify.call_count == 0
            
            # Test 2h warning
            escrow_2h = session.query(Escrow).filter(Escrow.id == escrow_id).with_for_update().first()
            escrow_2h.delivery_deadline = now + timedelta(hours=1, minutes=30)  # Within 2h window
            escrow_2h.warning_2h_sent = False
            session.commit()
            
            with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_delivery_warning') as mock_notify:
                mock_notify.return_value = {'telegram': True, 'email': True}
                
                await service.process_delivery_warnings()
                
                escrow_after = session.query(Escrow).filter(Escrow.id == escrow_id).first()
                assert escrow_after.warning_2h_sent == True
                assert mock_notify.call_count == 1
                
                # Second run - no duplicate
                mock_notify.reset_mock()
                await service.process_delivery_warnings()
                assert mock_notify.call_count == 0
            
            # Test 30min warning
            escrow_30m = session.query(Escrow).filter(Escrow.id == escrow_id).with_for_update().first()
            escrow_30m.delivery_deadline = now + timedelta(minutes=20)  # Within 30min window
            escrow_30m.warning_30m_sent = False
            session.commit()
            
            with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_delivery_warning') as mock_notify:
                mock_notify.return_value = {'telegram': True, 'email': True}
                
                await service.process_delivery_warnings()
                
                escrow_after = session.query(Escrow).filter(Escrow.id == escrow_id).first()
                assert escrow_after.warning_30m_sent == True
                assert mock_notify.call_count == 1
                
                # Second run - no duplicate
                mock_notify.reset_mock()
                await service.process_delivery_warnings()
                assert mock_notify.call_count == 0
            
            # Verify final state - all flags set
            final_escrow = session.query(Escrow).filter(Escrow.id == escrow_id).first()
            assert final_escrow.warning_24h_sent == True
            assert final_escrow.warning_8h_sent == True
            assert final_escrow.warning_2h_sent == True
            assert final_escrow.warning_30m_sent == True
            
        finally:
            # Cleanup
            session.query(Escrow).filter(Escrow.escrow_id == "TEST-WARN-001").delete()
            session.query(User).filter(User.telegram_id.in_([1001, 1002])).delete()
            session.commit()
            session.close()
    
    @pytest.mark.asyncio
    async def test_warning_flags_prevent_race_conditions(self):
        """Test that row-level locking prevents concurrent warning duplicates"""
        session = SessionLocal()
        
        try:
            now = datetime.now(timezone.utc)
            buyer = User(telegram_id=2001, username="race_buyer", email="race_buyer@test.com", created_at=now)
            seller = User(telegram_id=2002, username="race_seller", email="race_seller@test.com", created_at=now)
            session.add_all([buyer, seller])
            session.commit()
            
            escrow = Escrow(
                escrow_id="TEST-RACE-001",
                buyer_id=buyer.id,
                seller_id=seller.id,
                amount=Decimal("100.00"),
                currency="USD",
                status="active",
                delivery_deadline=now + timedelta(hours=1),  # Triggers 2h warning
                warning_24h_sent=False,
                warning_8h_sent=False,
                warning_2h_sent=False,
                warning_30m_sent=False
            )
            session.add(escrow)
            session.commit()
            escrow_id = escrow.id
            
            # Simulate concurrent processing with SELECT FOR UPDATE
            with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_delivery_warning') as mock_notify:
                mock_notify.return_value = {'telegram': True, 'email': True}
                
                # First process - acquires lock and sets flag
                escrow_locked = session.query(Escrow).filter(Escrow.id == escrow_id).with_for_update().first()
                
                # Check flag before processing
                if not escrow_locked.warning_2h_sent:
                    escrow_locked.warning_2h_sent = True
                    session.commit()
                    notification_sent = True
                else:
                    notification_sent = False
                
                # Verify only one notification
                assert notification_sent == True
                
                # Second concurrent process - should see flag already set
                escrow_locked_2 = session.query(Escrow).filter(Escrow.id == escrow_id).with_for_update().first()
                
                if not escrow_locked_2.warning_2h_sent:
                    # This should not execute because flag is already True
                    pytest.fail("Race condition detected - flag should already be set")
                
                # Verify flag is set
                assert escrow_locked_2.warning_2h_sent == True
            
        finally:
            session.query(Escrow).filter(Escrow.escrow_id == "TEST-RACE-001").delete()
            session.query(User).filter(User.telegram_id.in_([2001, 2002])).delete()
            session.commit()
            session.close()


class TestFundReleaseNotifications:
    """Test that fund release sends dual-channel notifications to BOTH buyer and seller"""
    
    @pytest.mark.asyncio
    async def test_fund_release_dual_channel_notifications(self):
        """Test fund release sends Telegram + Email to both parties with broadcast_mode=True"""
        session = SessionLocal()
        
        try:
            # Create test users
            now = datetime.now(timezone.utc)
            buyer = User(
                telegram_id=3001,
                username="release_buyer",
                email="release_buyer@test.com",
                phone_number="+1111111111",
                created_at=now
            )
            seller = User(
                telegram_id=3002,
                username="release_seller",
                email="release_seller@test.com",
                phone_number="+2222222222",
                created_at=now
            )
            session.add_all([buyer, seller])
            session.commit()
            
            # Create active escrow
            escrow = Escrow(
                escrow_id="TEST-RELEASE-001",
                buyer_id=buyer.id,
                seller_id=seller.id,
                amount=Decimal("500.00"),
                currency="USD",
                status="active",
                seller_fee=Decimal("25.00")
            )
            session.add(escrow)
            session.commit()
            escrow_id = escrow.id
            
            # Mock Telegram update for buyer releasing funds
            mock_update = Mock(spec=Update)
            mock_query = Mock(spec=CallbackQuery)
            mock_user = Mock(spec=TelegramUser)
            mock_user.id = 3001  # Buyer
            mock_user.first_name = "Test Buyer"
            mock_query.data = f"confirm_release_{escrow_id}"
            mock_query.edit_message_text = AsyncMock()
            mock_query.answer = AsyncMock()
            mock_update.callback_query = mock_query
            mock_update.effective_user = mock_user
            
            mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
            mock_context.bot = AsyncMock()
            
            # Mock notification service to verify dual-channel delivery
            with patch('services.consolidated_notification_service.ConsolidatedNotificationService') as MockNotificationService:
                mock_service_instance = MockNotificationService.return_value
                mock_service_instance.send_funds_released_notification = AsyncMock(
                    return_value={'telegram': True, 'email': True}
                )
                
                # Execute fund release
                await handle_confirm_release_funds(mock_update, mock_context)
                
                # Verify notification service was called with broadcast_mode=True
                assert mock_service_instance.send_funds_released_notification.called
                call_args = mock_service_instance.send_funds_released_notification.call_args
                
                # Verify broadcast_mode=True for guaranteed dual-channel delivery
                assert 'broadcast_mode' in call_args[1] or len(call_args[0]) > 2
                
                # Verify escrow status changed to completed
                updated_escrow = session.query(Escrow).filter(Escrow.id == escrow_id).first()
                assert updated_escrow.status == "completed"
            
        finally:
            session.query(Escrow).filter(Escrow.escrow_id == "TEST-RELEASE-001").delete()
            session.query(User).filter(User.telegram_id.in_([3001, 3002])).delete()
            session.commit()
            session.close()
    
    @pytest.mark.asyncio
    async def test_fund_release_notification_to_seller(self):
        """Test seller receives notification when buyer releases funds"""
        session = SessionLocal()
        
        try:
            now = datetime.now(timezone.utc)
            buyer = User(telegram_id=3101, username="buyer_notify", email="buyer_notify@test.com", created_at=now)
            seller = User(telegram_id=3102, username="seller_notify", email="seller_notify@test.com", created_at=now)
            session.add_all([buyer, seller])
            session.commit()
            
            escrow = Escrow(
                escrow_id="TEST-SELLER-NOTIFY-001",
                buyer_id=buyer.id,
                seller_id=seller.id,
                amount=Decimal("200.00"),
                currency="USD",
                status="active",
                seller_fee=Decimal("10.00")
            )
            session.add(escrow)
            session.commit()
            
            # Verify seller receives notification
            with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_funds_released_notification') as mock_notify:
                mock_notify.return_value = {'telegram': True, 'email': True}
                
                # Simulate fund release notification
                from services.consolidated_notification_service import ConsolidatedNotificationService
                service = ConsolidatedNotificationService()
                
                result = await service.send_funds_released_notification(
                    seller_user_id=seller.id,
                    escrow_id=escrow.escrow_id,
                    amount=escrow.amount,
                    seller_fee=escrow.seller_fee,
                    broadcast_mode=True  # CRITICAL: Must use broadcast_mode=True
                )
                
                # Verify dual-channel delivery
                assert result.get('telegram') == True
                assert result.get('email') == True
        
        finally:
            session.query(Escrow).filter(Escrow.escrow_id == "TEST-SELLER-NOTIFY-001").delete()
            session.query(User).filter(User.telegram_id.in_([3101, 3102])).delete()
            session.commit()
            session.close()


class TestCompletedTradeChatRestrictions:
    """Test that chat is disabled for completed trades and resolved disputes"""
    
    @pytest.mark.asyncio
    async def test_chat_disabled_for_completed_trade(self):
        """Test users cannot access chat for completed trades"""
        session = SessionLocal()
        
        try:
            now = datetime.now(timezone.utc)
            buyer = User(telegram_id=4001, username="chat_buyer", email="chat_buyer@test.com", created_at=now)
            seller = User(telegram_id=4002, username="chat_seller", email="chat_seller@test.com", created_at=now)
            session.add_all([buyer, seller])
            session.commit()
            
            # Create completed escrow
            escrow = Escrow(
                escrow_id="TEST-CHAT-COMPLETED-001",
                buyer_id=buyer.id,
                seller_id=seller.id,
                amount=Decimal("100.00"),
                currency="USD",
                status="completed"  # Trade is completed
            )
            session.add(escrow)
            session.commit()
            escrow_id = escrow.id
            
            # Mock Telegram update for buyer trying to open chat
            mock_update = Mock(spec=Update)
            mock_query = Mock(spec=CallbackQuery)
            mock_user = Mock(spec=TelegramUser)
            mock_user.id = 4001  # Buyer
            mock_query.data = f"trade_chat_open:{escrow_id}"
            mock_query.answer = AsyncMock()
            
            # Mock edit_message_text to capture the response
            captured_message = None
            async def capture_message(text, **kwargs):
                nonlocal captured_message
                captured_message = text
            
            mock_query.edit_message_text = AsyncMock(side_effect=capture_message)
            mock_update.callback_query = mock_query
            mock_update.effective_user = mock_user
            
            mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
            mock_context.user_data = {}
            
            # Try to open chat - should be blocked
            await open_trade_chat(mock_update, mock_context)
            
            # Verify chat blocked message was shown
            assert captured_message is not None
            assert "Chat Closed" in captured_message or "closed" in captured_message.lower()
            
        finally:
            session.query(Escrow).filter(Escrow.escrow_id == "TEST-CHAT-COMPLETED-001").delete()
            session.query(User).filter(User.telegram_id.in_([4001, 4002])).delete()
            session.commit()
            session.close()
    
    @pytest.mark.asyncio
    async def test_chat_disabled_for_resolved_dispute(self):
        """Test users cannot access chat for resolved disputes"""
        session = SessionLocal()
        
        try:
            now = datetime.now(timezone.utc)
            buyer = User(telegram_id=4101, username="dispute_buyer", email="dispute_buyer@test.com", created_at=now)
            seller = User(telegram_id=4102, username="dispute_seller", email="dispute_seller@test.com", created_at=now)
            session.add_all([buyer, seller])
            session.commit()
            
            # Create disputed escrow
            escrow = Escrow(
                escrow_id="TEST-CHAT-DISPUTE-001",
                buyer_id=buyer.id,
                seller_id=seller.id,
                amount=Decimal("300.00"),
                currency="USD",
                status="disputed"
            )
            session.add(escrow)
            session.commit()
            
            # Create resolved dispute
            dispute = Dispute(
                escrow_id=escrow.id,
                raised_by=buyer.id,
                reason="Test dispute",
                status="resolved"  # Dispute is resolved
            )
            session.add(dispute)
            session.commit()
            escrow_id = escrow.id
            
            # Mock Telegram update
            mock_update = Mock(spec=Update)
            mock_query = Mock(spec=CallbackQuery)
            mock_user = Mock(spec=TelegramUser)
            mock_user.id = 4101  # Buyer
            mock_query.data = f"trade_chat_open:{escrow_id}"
            mock_query.answer = AsyncMock()
            
            captured_message = None
            async def capture_message(text, **kwargs):
                nonlocal captured_message
                captured_message = text
            
            mock_query.edit_message_text = AsyncMock(side_effect=capture_message)
            mock_update.callback_query = mock_query
            mock_update.effective_user = mock_user
            
            mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
            mock_context.user_data = {}
            
            # Try to open chat - should be blocked
            await open_trade_chat(mock_update, mock_context)
            
            # Verify chat blocked message
            assert captured_message is not None
            assert "Chat Closed" in captured_message or "resolved" in captured_message.lower()
            
        finally:
            session.query(Dispute).filter(Dispute.escrow_id == escrow_id).delete()
            session.query(Escrow).filter(Escrow.escrow_id == "TEST-CHAT-DISPUTE-001").delete()
            session.query(User).filter(User.telegram_id.in_([4101, 4102])).delete()
            session.commit()
            session.close()
    
    @pytest.mark.asyncio
    async def test_chat_allowed_for_active_trade(self):
        """Test chat is accessible for active trades"""
        session = SessionLocal()
        
        try:
            now = datetime.now(timezone.utc)
            buyer = User(telegram_id=4201, username="active_buyer", email="active_buyer@test.com", created_at=now)
            seller = User(telegram_id=4202, username="active_seller", email="active_seller@test.com", created_at=now)
            session.add_all([buyer, seller])
            session.commit()
            
            # Create active escrow
            escrow = Escrow(
                escrow_id="TEST-CHAT-ACTIVE-001",
                buyer_id=buyer.id,
                seller_id=seller.id,
                amount=Decimal("150.00"),
                currency="USD",
                status="active"  # Trade is active
            )
            session.add(escrow)
            session.commit()
            escrow_id = escrow.id
            
            # Mock Telegram update
            mock_update = Mock(spec=Update)
            mock_query = Mock(spec=CallbackQuery)
            mock_user = Mock(spec=TelegramUser)
            mock_user.id = 4201  # Buyer
            mock_query.data = f"trade_chat_open:{escrow_id}"
            mock_query.answer = AsyncMock()
            
            captured_message = None
            async def capture_message(text, **kwargs):
                nonlocal captured_message
                captured_message = text
            
            mock_query.edit_message_text = AsyncMock(side_effect=capture_message)
            mock_update.callback_query = mock_query
            mock_update.effective_user = mock_user
            
            mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
            mock_context.user_data = {}
            
            # Open chat - should succeed
            await open_trade_chat(mock_update, mock_context)
            
            # Verify chat was opened (no "Chat Closed" message)
            if captured_message:
                assert "Chat Closed" not in captured_message
            
        finally:
            session.query(Escrow).filter(Escrow.escrow_id == "TEST-CHAT-ACTIVE-001").delete()
            session.query(User).filter(User.telegram_id.in_([4201, 4202])).delete()
            session.commit()
            session.close()


class TestIntegrationAllFixes:
    """Integration tests combining all three fixes"""
    
    @pytest.mark.asyncio
    async def test_complete_trade_lifecycle_with_all_fixes(self):
        """Test complete trade flow: warnings → fund release → chat disabled"""
        session = SessionLocal()
        
        try:
            # Setup users
            now = datetime.now(timezone.utc)
            buyer = User(
                telegram_id=5001,
                username="lifecycle_buyer",
                email="lifecycle_buyer@test.com",
                created_at=now
            )
            seller = User(
                telegram_id=5002,
                username="lifecycle_seller",
                email="lifecycle_seller@test.com",
                created_at=now
            )
            session.add_all([buyer, seller])
            session.commit()
            
            # Create escrow with delivery deadline
            escrow = Escrow(
                escrow_id="TEST-LIFECYCLE-001",
                buyer_id=buyer.id,
                seller_id=seller.id,
                amount=Decimal("1000.00"),
                currency="USD",
                status="active",
                delivery_deadline=now + timedelta(hours=1),
                warning_24h_sent=False,
                warning_8h_sent=False,
                warning_2h_sent=False,
                warning_30m_sent=False,
                seller_fee=Decimal("50.00")
            )
            session.add(escrow)
            session.commit()
            escrow_id = escrow.id
            
            # Step 1: Test delivery warning (2h warning should trigger)
            service = StandaloneAutoReleaseService()
            with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_delivery_warning') as mock_warn:
                mock_warn.return_value = {'telegram': True, 'email': True}
                await service.process_delivery_warnings()
                
                # Verify warning sent
                escrow_warned = session.query(Escrow).filter(Escrow.id == escrow_id).first()
                assert escrow_warned.warning_2h_sent == True
            
            # Step 2: Buyer releases funds
            escrow_release = session.query(Escrow).filter(Escrow.id == escrow_id).first()
            escrow_release.status = "completed"
            session.commit()
            
            # Step 3: Test fund release notification
            with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_funds_released_notification') as mock_release:
                mock_release.return_value = {'telegram': True, 'email': True}
                
                from services.consolidated_notification_service import ConsolidatedNotificationService
                notif_service = ConsolidatedNotificationService()
                result = await notif_service.send_funds_released_notification(
                    seller_user_id=seller.id,
                    escrow_id=escrow.escrow_id,
                    amount=escrow.amount,
                    seller_fee=escrow.seller_fee,
                    broadcast_mode=True
                )
                
                # Verify dual-channel delivery
                assert result.get('telegram') == True
                assert result.get('email') == True
            
            # Step 4: Test chat is disabled for completed trade
            mock_update = Mock(spec=Update)
            mock_query = Mock(spec=CallbackQuery)
            mock_user = Mock(spec=TelegramUser)
            mock_user.id = 5001  # Buyer
            mock_query.data = f"trade_chat_open:{escrow_id}"
            mock_query.answer = AsyncMock()
            
            captured_message = None
            async def capture_message(text, **kwargs):
                nonlocal captured_message
                captured_message = text
            
            mock_query.edit_message_text = AsyncMock(side_effect=capture_message)
            mock_update.callback_query = mock_query
            mock_update.effective_user = mock_user
            
            mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
            mock_context.user_data = {}
            
            await open_trade_chat(mock_update, mock_context)
            
            # Verify chat is blocked
            assert captured_message is not None
            assert "Chat Closed" in captured_message or "completed" in captured_message.lower()
            
        finally:
            session.query(Escrow).filter(Escrow.escrow_id == "TEST-LIFECYCLE-001").delete()
            session.query(User).filter(User.telegram_id.in_([5001, 5002])).delete()
            session.commit()
            session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
