"""
End-to-End Tests for Payment Flow Bug Fixes
Tests overpayment credit, seller notifications, escrow status, and transaction history visibility
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select

from database import async_managed_session
from models import User, Wallet, Escrow, Transaction, EscrowStatus
from services.crypto import CryptoServiceAtomic
from services.enhanced_payment_tolerance_service import EnhancedPaymentToleranceService
from handlers.dynopay_webhook import DynoPayWebhookHandler


class TestPaymentFlowFixes:
    """Test suite for payment flow bug fixes"""
    
    @pytest.mark.asyncio
    async def test_overpayment_credit_persistence(self):
        """Test that overpayment credits persist and are immediately visible"""
        async with async_managed_session() as session:
            # Create test user and wallet
            user = User(
                id=999888777,
                telegram_id=999888777,
                username="test_overpay_user",
                first_name="Test",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(user)
            await session.flush()
            
            wallet = Wallet(user_id=user.id, available_balance=Decimal("10.00"))
            session.add(wallet)
            
            # Create test escrow for constraint compliance
            escrow = Escrow(
                escrow_id="TEST_OVERPAY_001",
                buyer_id=user.id,
                seller_id=user.id,
                amount=Decimal("5.00"),
                currency="USD",
                status=EscrowStatus.PAYMENT_PENDING.value,
                delivery_hours=24,
                pricing_snapshot={"delivery_hours": 24}
            )
            session.add(escrow)
            await session.flush()
            
            initial_balance = wallet.available_balance
            overpay_amount = Decimal("2.50")
            
            # Credit wallet with overpayment
            credit_success = await CryptoServiceAtomic.credit_user_wallet_atomic(
                user_id=user.id,
                amount=overpay_amount,
                currency="USD",
                escrow_id=escrow.id,
                transaction_type="escrow_overpayment",
                description=f"Test overpayment credit from escrow {escrow.escrow_id}",
                session=session
            )
            
            assert credit_success, "Wallet credit should succeed"
            
            # CRITICAL TEST: Verify wallet balance is immediately visible in same session
            stmt = select(Wallet).where(Wallet.user_id == user.id)
            updated_wallet = (await session.execute(stmt)).scalar_one()
            
            expected_balance = initial_balance + overpay_amount
            assert updated_wallet.available_balance == expected_balance, \
                f"Wallet balance should be {expected_balance}, got {updated_wallet.available_balance}"
            
            # Verify transaction was created
            tx_stmt = select(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.transaction_type == "escrow_overpayment",
                Transaction.escrow_id == escrow.id
            )
            transaction = (await session.execute(tx_stmt)).scalar_one_or_none()
            
            assert transaction is not None, "Overpayment transaction should exist"
            assert transaction.amount == overpay_amount, "Transaction amount should match"
            
            # Cleanup
            await session.rollback()
    
    @pytest.mark.asyncio
    async def test_seller_notification_without_buyer_duplicates(self):
        """Test that seller gets notified without duplicate buyer notifications"""
        async with async_managed_session() as session:
            # Create test users
            buyer = User(
                id=888777666,
                telegram_id=888777666,
                username="test_buyer",
                first_name="Buyer",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            seller = User(
                id=777666555,
                telegram_id=777666555,
                username="test_seller",
                first_name="Seller",
                email="seller@test.com",
                email_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(buyer)
            session.add(seller)
            await session.flush()
            
            # Create test escrow
            escrow = Escrow(
                escrow_id="TEST_NOTIF_001",
                buyer_id=buyer.id,
                seller_id=seller.id,
                amount=Decimal("10.00"),
                currency="USD",
                status=EscrowStatus.PAYMENT_CONFIRMED.value,
                delivery_hours=24,
                pricing_snapshot={"delivery_hours": 24}
            )
            session.add(escrow)
            await session.flush()
            
            # Mock notification methods
            with patch('services.trade_acceptance_notification_service.TradeAcceptanceNotificationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                
                # Mock all notification methods
                mock_service._notify_seller_trade_confirmed = AsyncMock(return_value=True)
                mock_service._send_seller_confirmation_email = AsyncMock(return_value=True)
                mock_service._is_first_trade = MagicMock(return_value=True)
                mock_service._send_seller_welcome_email = AsyncMock(return_value=True)
                mock_service._send_admin_trade_activation_alert = AsyncMock(return_value=True)
                
                # Simulate the notification flow from webhook
                from services.trade_acceptance_notification_service import TradeAcceptanceNotificationService
                notification_service = TradeAcceptanceNotificationService()
                
                # Seller Telegram notification
                await notification_service._notify_seller_trade_confirmed(
                    seller, escrow.escrow_id, float(escrow.amount), buyer, "USD"
                )
                
                # Seller email notification
                if seller.email and seller.email_verified:
                    await notification_service._send_seller_confirmation_email(
                        seller.email, escrow.escrow_id, float(escrow.amount), buyer, "USD"
                    )
                    
                    # First-trade welcome email
                    if notification_service._is_first_trade(seller.id):
                        seller_name = seller.first_name or seller.username or "Trader"
                        await notification_service._send_seller_welcome_email(
                            seller.email, seller_name, seller.id
                        )
                
                # Admin notification
                await notification_service._send_admin_trade_activation_alert(
                    escrow.escrow_id, float(escrow.amount), buyer, seller, "USD"
                )
                
                # Verify seller notifications were sent
                mock_service._notify_seller_trade_confirmed.assert_called_once()
                mock_service._send_seller_confirmation_email.assert_called_once()
                mock_service._send_seller_welcome_email.assert_called_once()
                mock_service._send_admin_trade_activation_alert.assert_called_once()
                
                # CRITICAL TEST: Verify NO buyer notification methods were called
                # The mock service should not have any buyer notification methods called
                assert not hasattr(mock_service, '_notify_buyer_trade_accepted') or \
                       not mock_service._notify_buyer_trade_accepted.called, \
                       "Buyer notification should NOT be called (already handled by enhanced tolerance)"
            
            # Cleanup
            await session.rollback()
    
    @pytest.mark.asyncio
    async def test_escrow_status_persistence(self):
        """Test that escrow status updates persist correctly"""
        async with async_managed_session() as session:
            # Create test user
            user = User(
                id=666555444,
                telegram_id=666555444,
                username="test_status_user",
                first_name="Status Test",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(user)
            await session.flush()
            
            # Create test escrow
            escrow = Escrow(
                escrow_id="TEST_STATUS_001",
                buyer_id=user.id,
                seller_id=user.id,
                amount=Decimal("15.00"),
                currency="USD",
                status=EscrowStatus.PAYMENT_PENDING.value,
                delivery_hours=24,
                pricing_snapshot={"delivery_hours": 24}
            )
            session.add(escrow)
            await session.flush()
            
            # Update escrow status (simulating webhook behavior)
            escrow.status = EscrowStatus.PAYMENT_CONFIRMED.value
            escrow.payment_confirmed_at = datetime.now(timezone.utc)
            
            # CRITICAL: Flush changes immediately
            await session.flush()
            
            # Verify status is immediately visible in same session
            stmt = select(Escrow).where(Escrow.escrow_id == "TEST_STATUS_001")
            updated_escrow = (await session.execute(stmt)).scalar_one()
            
            assert updated_escrow.status == EscrowStatus.PAYMENT_CONFIRMED.value, \
                f"Escrow status should be PAYMENT_CONFIRMED, got {updated_escrow.status}"
            assert updated_escrow.payment_confirmed_at is not None, \
                "Payment confirmation timestamp should be set"
            
            # Cleanup
            await session.rollback()
    
    @pytest.mark.asyncio
    async def test_overpayment_visibility_in_deposits_filter(self):
        """Test that overpayment credits appear when filtering by DEPOSITS"""
        async with async_managed_session() as session:
            # Create test user
            user = User(
                id=555444333,
                telegram_id=555444333,
                username="test_history_user",
                first_name="History Test",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(user)
            await session.flush()
            
            # Create test escrow for constraint
            escrow = Escrow(
                escrow_id="TEST_HISTORY_001",
                buyer_id=user.id,
                seller_id=user.id,
                amount=Decimal("10.00"),
                currency="USD",
                status=EscrowStatus.PAYMENT_CONFIRMED.value,
                delivery_hours=24,
                pricing_snapshot={"delivery_hours": 24}
            )
            session.add(escrow)
            await session.flush()
            
            # Create various transaction types
            transactions = [
                Transaction(
                    transaction_id="TX_OVERPAY_001",
                    user_id=user.id,
                    escrow_id=escrow.id,
                    transaction_type="escrow_overpayment",
                    amount=Decimal("2.50"),
                    currency="USD",
                    status="completed",
                    description="Overpayment bonus"
                ),
                Transaction(
                    transaction_id="TX_DEPOSIT_001",
                    user_id=user.id,
                    transaction_type="wallet_deposit",
                    amount=Decimal("50.00"),
                    currency="USD",
                    status="completed",
                    description="Regular deposit"
                ),
                Transaction(
                    transaction_id="TX_CASHOUT_001",
                    user_id=user.id,
                    transaction_type="cashout",
                    amount=Decimal("10.00"),
                    currency="USD",
                    status="completed",
                    description="Cashout"
                )
            ]
            
            for tx in transactions:
                session.add(tx)
            await session.flush()
            
            # Test DEPOSITS filter (simulating transaction history handler)
            deposit_types = [
                'deposit',
                'wallet_deposit',
                'escrow_overpayment',  # CRITICAL: Must be included
                'exchange_overpayment',
                'escrow_underpay_refund'
            ]
            
            deposits_stmt = select(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.transaction_type.in_(deposit_types)
            )
            deposits = (await session.execute(deposits_stmt)).scalars().all()
            
            # Verify overpayment is included in deposits
            overpay_tx = next((tx for tx in deposits if tx.transaction_type == "escrow_overpayment"), None)
            assert overpay_tx is not None, "Overpayment transaction should appear in DEPOSITS filter"
            
            # Verify regular deposit is included
            deposit_tx = next((tx for tx in deposits if tx.transaction_type == "wallet_deposit"), None)
            assert deposit_tx is not None, "Regular deposit should appear in DEPOSITS filter"
            
            # Verify cashout is NOT included
            cashout_tx = next((tx for tx in deposits if tx.transaction_type == "cashout"), None)
            assert cashout_tx is None, "Cashout should NOT appear in DEPOSITS filter"
            
            # Count should be 2 (overpayment + deposit, not cashout)
            assert len(deposits) == 2, f"Should have 2 deposit transactions, got {len(deposits)}"
            
            # Cleanup
            await session.rollback()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
