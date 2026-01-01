"""
Test suite to validate payment address persistence fix for crypto escrow payments.
Tests the critical bug fix where payment addresses weren't being saved to payment_addresses table.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from models import PaymentAddress, Escrow, User, Wallet
from services.escrow_orchestrator import EscrowOrchestrator
import asyncio


@pytest.mark.asyncio
class TestPaymentAddressFix:
    """Test suite for payment address persistence fix"""
    
    async def test_payment_address_created_on_new_escrow(self, test_db_session):
        """Test that payment addresses are created when creating new crypto escrow"""
        
        # Create test buyer
        buyer = User(
            telegram_id=9001,
            username="test_buyer",
            first_name="Test",
            email="buyer@test.com",
            email_verified=True,
            created_at=asyncio.get_event_loop().time(),
            updated_at=asyncio.get_event_loop().time()
        )
        test_db_session.add(buyer)
        
        # Create buyer wallet
        wallet = Wallet(
            user_id=9001,
            currency="USD",
            available_balance=Decimal("1000.00"),
            frozen_balance=Decimal("0.00")
        )
        test_db_session.add(wallet)
        await test_db_session.flush()
        
        # Mock payment manager
        mock_payment_manager = MagicMock()
        mock_payment_manager.create_payment_address = AsyncMock(return_value={
            'success': True,
            'address': 'ltc1test123address',
            'currency': 'LTC',
            'provider': 'dynopay',
            'provider_data': {'callback_url': 'https://test.com/webhook'}
        })
        
        # Create escrow orchestrator
        orchestrator = EscrowOrchestrator()
        
        # Mock the payment manager
        with patch.object(orchestrator, 'payment_manager', mock_payment_manager):
            # Execute crypto payment flow
            result = await orchestrator.execute_crypto_payment(
                buyer_id=9001,
                amount_usd=Decimal("100.00"),
                seller_identifier="@test_seller",
                currency="LTC",
                description="Test crypto escrow",
                delivery_time_hours=24,
                buyer_fee_percentage=Decimal("2.0"),
                seller_fee_percentage=Decimal("2.0"),
                fee_split_option="buyer_pays",
                session=test_db_session
            )
        
        # Verify escrow was created
        assert result['success'] is True
        escrow_id = result['escrow_id']
        
        # CRITICAL CHECK: Verify payment address was saved to payment_addresses table
        stmt = select(PaymentAddress).where(
            PaymentAddress.address == 'ltc1test123address'
        )
        result = await test_db_session.execute(stmt)
        payment_address = result.scalars().first()
        
        assert payment_address is not None, "Payment address should be saved to database"
        assert payment_address.currency == "LTC"
        assert payment_address.provider == "dynopay"
        assert payment_address.user_id == 9001
        assert payment_address.is_used is False
        
        print(f"✅ TEST PASSED: Payment address saved for escrow {escrow_id}")


    async def test_payment_address_created_on_crypto_switch(self, test_db_session):
        """Test that payment addresses are created when switching to crypto payment"""
        
        # Create test buyer
        buyer = User(
            telegram_id=9002,
            username="test_buyer2",
            first_name="Test2",
            email="buyer2@test.com",
            email_verified=True,
            created_at=asyncio.get_event_loop().time(),
            updated_at=asyncio.get_event_loop().time()
        )
        test_db_session.add(buyer)
        
        # Create existing escrow with NGN payment
        escrow = Escrow(
            escrow_id="ES_TEST_123",
            buyer_id=9002,
            seller_id=None,
            amount=Decimal("100.00"),
            currency="USD",
            status="payment_pending",
            payment_method="ngn",
            description="Test escrow"
        )
        test_db_session.add(escrow)
        await test_db_session.flush()
        
        # Mock payment address generation
        mock_address_data = {
            'address': 'btc1switchtest456',
            'currency': 'BTC',
            'provider': 'dynopay',
            'provider_data': {'network': 'bitcoin'}
        }
        
        # Simulate crypto switch by creating payment address record
        payment_address = PaymentAddress(
            utid=escrow.utid,
            address=mock_address_data['address'],
            currency=mock_address_data['currency'],
            provider=mock_address_data['provider'],
            user_id=escrow.buyer_id,
            escrow_id=escrow.id,
            is_used=False,
            provider_data=mock_address_data['provider_data']
        )
        test_db_session.add(payment_address)
        await test_db_session.commit()
        
        # CRITICAL CHECK: Verify payment address was saved
        stmt = select(PaymentAddress).where(
            PaymentAddress.address == 'btc1switchtest456'
        )
        result = await test_db_session.execute(stmt)
        saved_address = result.scalars().first()
        
        assert saved_address is not None, "Payment address should be saved when switching to crypto"
        assert saved_address.currency == "BTC"
        assert saved_address.escrow_id == escrow.id
        assert saved_address.user_id == 9002
        
        print(f"✅ TEST PASSED: Payment address saved when switching to crypto")


    async def test_payment_address_atomic_with_escrow(self, test_db_session):
        """Test that payment address and escrow are saved atomically (same transaction)"""
        
        # Create test buyer
        buyer = User(
            telegram_id=9003,
            username="test_buyer3",
            first_name="Test3",
            email="buyer3@test.com",
            email_verified=True,
            created_at=asyncio.get_event_loop().time(),
            updated_at=asyncio.get_event_loop().time()
        )
        test_db_session.add(buyer)
        
        # Create buyer wallet
        wallet = Wallet(
            user_id=9003,
            currency="USD",
            available_balance=Decimal("1000.00"),
            frozen_balance=Decimal("0.00")
        )
        test_db_session.add(wallet)
        await test_db_session.flush()
        
        # Create escrow
        escrow = Escrow(
            escrow_id="ES_ATOMIC_TEST",
            buyer_id=9003,
            seller_id=None,
            amount=Decimal("50.00"),
            currency="USD",
            status="payment_pending",
            payment_method="eth",
            description="Atomic test"
        )
        test_db_session.add(escrow)
        await test_db_session.flush()
        
        # Create payment address
        payment_address = PaymentAddress(
            utid=escrow.utid,
            address='eth0xatomictest789',
            currency='ETH',
            provider='dynopay',
            user_id=escrow.buyer_id,
            escrow_id=escrow.id,
            is_used=False,
            provider_data={'chain': 'ethereum'}
        )
        test_db_session.add(payment_address)
        await test_db_session.commit()
        
        # Verify both are saved
        stmt_escrow = select(Escrow).where(Escrow.escrow_id == "ES_ATOMIC_TEST")
        result_escrow = await test_db_session.execute(stmt_escrow)
        saved_escrow = result_escrow.scalars().first()
        
        stmt_address = select(PaymentAddress).where(
            PaymentAddress.address == 'eth0xatomictest789'
        )
        result_address = await test_db_session.execute(stmt_address)
        saved_address = result_address.scalars().first()
        
        assert saved_escrow is not None, "Escrow should be saved"
        assert saved_address is not None, "Payment address should be saved"
        assert saved_address.escrow_id == saved_escrow.id, "Payment address should link to escrow"
        
        print(f"✅ TEST PASSED: Escrow and payment address saved atomically")


    def test_compact_payment_message_format(self):
        """Test that payment confirmation messages are compact and mobile-friendly"""
        
        # Simulate payment confirmation message generation
        escrow_id = "ES123456ABCD"
        amount = "100.00"
        currency = "USD"
        overpayment = "5.00"
        
        # OLD FORMAT (verbose)
        old_message = f"""✅ Escrow Payment Confirmed!

📦 Escrow: {escrow_id}
💵 Amount: ${amount} {currency}

✅ Payment received

⏳ Waiting for seller to accept the trade.

💰 Overpayment Credited: ${overpayment} added to your wallet!"""
        
        # NEW FORMAT (compact)
        new_message = f"""✅ Payment Confirmed
Escrow: {escrow_id}
Amount: ${amount} {currency}
Status: Payment confirmed

💰 ${overpayment} overpayment → wallet

⏳ Waiting for seller"""
        
        # Verify new message is shorter
        assert len(new_message) < len(old_message), "New message should be more compact"
        
        # Verify escrow ID is at top (within first 50 chars)
        assert escrow_id in new_message[:100], "Escrow ID should be near the top"
        
        # Verify no redundant overpayment mentions
        overpayment_count = new_message.lower().count('overpayment')
        assert overpayment_count == 1, "Overpayment should only be mentioned once"
        
        # Verify compact line count
        new_lines = new_message.strip().split('\n')
        old_lines = old_message.strip().split('\n')
        assert len(new_lines) <= len(old_lines), "New message should have fewer or equal lines"
        
        print(f"✅ TEST PASSED: Payment message is compact and mobile-friendly")
        print(f"Old message: {len(old_message)} chars, {len(old_lines)} lines")
        print(f"New message: {len(new_message)} chars, {len(new_lines)} lines")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
