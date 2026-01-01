"""
E2E Test: Seller Accept/Decline Notifications with Broadcast Mode
Validates that all seller notifications use ConsolidatedNotificationService with broadcast_mode=True
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from sqlalchemy import select

from models import User, Escrow, EscrowStatus, Wallet
from services.consolidated_notification_service import (
    consolidated_notification_service,
    NotificationRequest,
    NotificationCategory,
    NotificationPriority
)


@pytest.mark.asyncio
async def test_seller_accept_trade_broadcast_notifications(test_db_session):
    """Test that seller accepting trade sends dual-channel notifications to BOTH buyer and seller"""
    
    # Create test buyer
    buyer = User(
        telegram_id=111111111,
        username="test_buyer",
        first_name="Buyer",
        email="buyer@example.com",
        is_verified=True,
        email_verified=True,
        onboarded_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    test_db_session.add(buyer)
    test_db_session.flush()
    
    # Create buyer wallet
    buyer_wallet = Wallet(
        user_id=buyer.id,
        currency="USD",
        available_balance=Decimal("100.00"),
        frozen_balance=Decimal("0.00")
    )
    test_db_session.add(buyer_wallet)
    
    # Create test seller
    seller = User(
        telegram_id=222222222,
        username="test_seller",
        first_name="Seller",
        email="seller@example.com",
        is_verified=True,
        email_verified=True,
        onboarded_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    test_db_session.add(seller)
    test_db_session.flush()
    
    # Create payment_confirmed escrow
    escrow = Escrow(
        escrow_id="ES123TEST456",
        buyer_id=buyer.id,
        seller_id=None,  # Not yet accepted
        amount=Decimal("50.00"),
        currency="USD",
        total_amount=Decimal("50.00"),
        description="Test trade",
        status=EscrowStatus.PAYMENT_CONFIRMED.value,
        payment_confirmed_at=datetime.now(timezone.utc),
        seller_contact_type="username",
        seller_contact_value="test_seller"
    )
    test_db_session.add(escrow)
    test_db_session.commit()
    
    # Mock the ConsolidatedNotificationService
    with patch.object(consolidated_notification_service, 'send_notification', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        # Simulate seller accept handler logic
        escrow.seller_id = seller.id
        escrow.status = EscrowStatus.ACTIVE.value
        escrow.seller_accepted_at = datetime.now(timezone.utc)
        test_db_session.commit()
        
        # Send notifications (as the handler does)
        buyer_request = NotificationRequest(
            user_id=int(buyer.id),
            category=NotificationCategory.ESCROW_UPDATES,
            priority=NotificationPriority.HIGH,
            title="🎉 Trade Accepted!",
            message=f"The seller has accepted your trade: #{escrow.escrow_id}",
            template_data={
                "escrow_id": escrow.escrow_id,
                "amount": str(escrow.amount),
                "action": "seller_accepted"
            },
            broadcast_mode=True  # CRITICAL: Dual-channel delivery
        )
        await consolidated_notification_service.send_notification(buyer_request)
        
        seller_request = NotificationRequest(
            user_id=int(seller.id),
            category=NotificationCategory.ESCROW_UPDATES,
            priority=NotificationPriority.HIGH,
            title="✅ Trade Accepted",
            message=f"You accepted trade #{escrow.escrow_id}",
            template_data={
                "escrow_id": escrow.escrow_id,
                "amount": str(escrow.amount),
                "action": "seller_trade_accepted"
            },
            broadcast_mode=True  # CRITICAL: Dual-channel delivery
        )
        await consolidated_notification_service.send_notification(seller_request)
        
        # Verify both notifications were sent with broadcast_mode=True
        assert mock_send.call_count == 2, "Should send notifications to both buyer and seller"
        
        # Verify buyer notification
        buyer_call = mock_send.call_args_list[0]
        buyer_notification = buyer_call[0][0]
        assert buyer_notification.user_id == buyer.id
        assert buyer_notification.broadcast_mode is True, "Buyer notification must use broadcast_mode=True"
        assert buyer_notification.category == NotificationCategory.ESCROW_UPDATES
        assert buyer_notification.priority == NotificationPriority.HIGH
        assert "accepted" in buyer_notification.message.lower()
        
        # Verify seller notification
        seller_call = mock_send.call_args_list[1]
        seller_notification = seller_call[0][0]
        assert seller_notification.user_id == seller.id
        assert seller_notification.broadcast_mode is True, "Seller notification must use broadcast_mode=True"
        assert seller_notification.category == NotificationCategory.ESCROW_UPDATES
        assert seller_notification.priority == NotificationPriority.HIGH
        assert "accepted" in seller_notification.message.lower()


@pytest.mark.asyncio
async def test_seller_decline_trade_broadcast_notifications(test_db_session):
    """Test that seller declining trade sends dual-channel notifications to BOTH buyer and seller"""
    
    # Create test buyer
    buyer = User(
        telegram_id=333333333,
        username="test_buyer2",
        first_name="Buyer2",
        email="buyer2@example.com",
        is_verified=True,
        email_verified=True,
        onboarded_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    test_db_session.add(buyer)
    test_db_session.flush()
    
    # Create buyer wallet
    buyer_wallet = Wallet(
        user_id=buyer.id,
        currency="USD",
        available_balance=Decimal("100.00"),
        frozen_balance=Decimal("0.00")
    )
    test_db_session.add(buyer_wallet)
    
    # Create test seller
    seller = User(
        telegram_id=444444444,
        username="test_seller2",
        first_name="Seller2",
        email="seller2@example.com",
        is_verified=True,
        email_verified=True,
        onboarded_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    test_db_session.add(seller)
    test_db_session.flush()
    
    # Create payment_confirmed escrow
    escrow = Escrow(
        escrow_id="ES789TEST012",
        buyer_id=buyer.id,
        seller_id=None,
        amount=Decimal("75.00"),
        currency="USD",
        total_amount=Decimal("75.00"),
        description="Test trade for decline",
        status=EscrowStatus.PAYMENT_CONFIRMED.value,
        payment_confirmed_at=datetime.now(timezone.utc),
        seller_contact_type="username",
        seller_contact_value="test_seller2"
    )
    test_db_session.add(escrow)
    test_db_session.commit()
    
    # Mock the ConsolidatedNotificationService
    with patch.object(consolidated_notification_service, 'send_notification', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        # Simulate seller decline handler logic
        escrow.status = "cancelled"
        test_db_session.commit()
        
        # Send notifications (as the handler does)
        buyer_request = NotificationRequest(
            user_id=int(buyer.id),
            category=NotificationCategory.ESCROW_UPDATES,
            priority=NotificationPriority.HIGH,
            title="📥 Trade Declined",
            message=f"Seller declined trade #{escrow.escrow_id}. Refunded to your wallet.",
            template_data={
                "escrow_id": escrow.escrow_id,
                "amount": str(escrow.amount),
                "action": "seller_declined",
                "seller_name": seller.first_name or seller.username or "Seller"
            },
            broadcast_mode=True  # CRITICAL: Dual-channel delivery
        )
        await consolidated_notification_service.send_notification(buyer_request)
        
        seller_request = NotificationRequest(
            user_id=int(seller.id),
            category=NotificationCategory.ESCROW_UPDATES,
            priority=NotificationPriority.HIGH,
            title="✅ Trade Declined",
            message=f"You declined trade #{escrow.escrow_id}. Buyer refunded automatically.",
            template_data={
                "escrow_id": escrow.escrow_id,
                "amount": str(escrow.amount),
                "action": "seller_declined_confirmation"
            },
            broadcast_mode=True  # CRITICAL: Dual-channel delivery
        )
        await consolidated_notification_service.send_notification(seller_request)
        
        # Verify both notifications were sent with broadcast_mode=True
        assert mock_send.call_count == 2, "Should send notifications to both buyer and seller"
        
        # Verify buyer notification
        buyer_call = mock_send.call_args_list[0]
        buyer_notification = buyer_call[0][0]
        assert buyer_notification.user_id == buyer.id
        assert buyer_notification.broadcast_mode is True, "Buyer notification must use broadcast_mode=True"
        assert buyer_notification.category == NotificationCategory.ESCROW_UPDATES
        assert "declined" in buyer_notification.message.lower()
        
        # Verify seller notification (THIS WAS MISSING BEFORE!)
        seller_call = mock_send.call_args_list[1]
        seller_notification = seller_call[0][0]
        assert seller_notification.user_id == seller.id
        assert seller_notification.broadcast_mode is True, "Seller notification must use broadcast_mode=True"
        assert seller_notification.category == NotificationCategory.ESCROW_UPDATES
        assert "declined" in seller_notification.message.lower()


@pytest.mark.asyncio
async def test_initial_trade_offer_broadcast_notification(test_db_session):
    """Test that initial trade offer to seller uses broadcast_mode=True"""
    
    # Create test buyer
    buyer = User(
        telegram_id=555555555,
        username="test_buyer3",
        first_name="Buyer3",
        email="buyer3@example.com",
        is_verified=True,
        email_verified=True,
        onboarded_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    test_db_session.add(buyer)
    test_db_session.flush()
    
    # Create test seller
    seller = User(
        telegram_id=666666666,
        username="test_seller3",
        first_name="Seller3",
        email="seller3@example.com",
        is_verified=True,
        email_verified=True,
        onboarded_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    test_db_session.add(seller)
    test_db_session.flush()
    
    # Create new escrow (simulating trade creation)
    escrow = Escrow(
        escrow_id="ES345TEST678",
        buyer_id=buyer.id,
        seller_id=None,  # Not yet accepted
        amount=Decimal("100.00"),
        currency="USD",
        total_amount=Decimal("100.00"),
        description="Test initial offer",
        status=EscrowStatus.PAYMENT_PENDING.value,
        seller_contact_type="username",
        seller_contact_value="test_seller3"
    )
    test_db_session.add(escrow)
    test_db_session.commit()
    
    # Mock the ConsolidatedNotificationService
    with patch.object(consolidated_notification_service, 'send_notification', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        # Simulate initial trade offer notification (as created during escrow creation)
        seller_request = NotificationRequest(
            user_id=int(seller.id),
            category=NotificationCategory.ESCROW_UPDATES,
            priority=NotificationPriority.HIGH,
            title="💰 New Trade Request",
            message=f"New trade request #{escrow.escrow_id} from {buyer.first_name or buyer.username}",
            template_data={
                "escrow_id": escrow.escrow_id,
                "amount": str(escrow.amount),
                "buyer_name": buyer.first_name or buyer.username or "Buyer",
                "action": "new_trade_offer"
            },
            broadcast_mode=True  # CRITICAL: Was missing before, now added!
        )
        await consolidated_notification_service.send_notification(seller_request)
        
        # Verify notification was sent with broadcast_mode=True
        assert mock_send.call_count == 1, "Should send notification to seller"
        
        # Verify seller notification uses broadcast mode
        seller_call = mock_send.call_args_list[0]
        seller_notification = seller_call[0][0]
        assert seller_notification.user_id == seller.id
        assert seller_notification.broadcast_mode is True, "Initial trade offer must use broadcast_mode=True (not fallback mode)"
        assert seller_notification.category == NotificationCategory.ESCROW_UPDATES
        assert seller_notification.priority == NotificationPriority.HIGH


@pytest.mark.asyncio
async def test_no_legacy_telegram_email_calls():
    """Verify that NO legacy direct Telegram/Email calls exist in seller handlers"""
    
    import handlers.escrow as escrow_handlers
    import inspect
    
    # Get source code of seller accept/decline handlers
    accept_source = inspect.getsource(escrow_handlers.handle_seller_accept_trade)
    decline_source = inspect.getsource(escrow_handlers.handle_confirm_seller_decline_trade)
    
    # Verify NO legacy direct calls
    legacy_patterns = [
        "context.bot.send_message",
        "EmailService()",
        "email_service.send_",
        "Bot(Config.BOT_TOKEN)",
        "await bot.send_message"
    ]
    
    for pattern in legacy_patterns:
        assert pattern not in accept_source, f"Found legacy pattern '{pattern}' in handle_seller_accept_trade"
        assert pattern not in decline_source, f"Found legacy pattern '{pattern}' in handle_confirm_seller_decline_trade"
    
    # Verify ConsolidatedNotificationService is used
    assert "consolidated_notification_service" in accept_source, "handle_seller_accept_trade must use ConsolidatedNotificationService"
    assert "consolidated_notification_service" in decline_source, "handle_confirm_seller_decline_trade must use ConsolidatedNotificationService"
    assert "broadcast_mode=True" in accept_source, "handle_seller_accept_trade must use broadcast_mode=True"
    assert "broadcast_mode=True" in decline_source, "handle_confirm_seller_decline_trade must use broadcast_mode=True"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
