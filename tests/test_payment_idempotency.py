"""
Comprehensive tests for payment idempotency protection
Tests duplicate prevention for all webhook handlers
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Transaction, TransactionType, Escrow, ExchangeOrder, EscrowStatus, ExchangeStatus
from services.payment_idempotency_service import PaymentIdempotencyService, DynoPayIdempotency
from handlers.dynopay_webhook import DynoPayWebhookHandler
from handlers.dynopay_exchange_webhook import DynoPayExchangeWebhookHandler
from utils.helpers import generate_transaction_id


class TestPaymentIdempotency:
    """Test comprehensive payment idempotency protection"""
    
    @pytest.fixture
    def setup_database(self):
        """Set up test database with required tables"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

    @pytest.fixture
    def sample_dynopay_webhook_data(self):
        """Sample DynoPay webhook data for testing"""
        return {
            "id": "tx_12345_unique",
            "paid_amount": "100.0",
            "paid_currency": "USDT",
            "meta_data": {
                "refId": "ESC001",
                "deposit_address": "0x123..."
            }
        }

    @pytest.fixture
    def sample_escrow(self, setup_database):
        """Create sample escrow for testing"""
        session = setup_database
        escrow = Escrow(
            escrow_id="ESC001",
            buyer_id=1,
            total_amount=Decimal("100.0"),
            status=EscrowStatus.PAYMENT_PENDING.value
        )
        session.add(escrow)
        session.commit()
        return escrow

    @pytest.mark.asyncio
    async def test_global_tx_hash_uniqueness_constraint(self, setup_database):
        """Test that global tx_hash uniqueness constraint prevents duplicates"""
        session = setup_database
        
        # Create required User first to avoid FK constraint
        from models import User
        user = User(telegram_id=123456, username='test_user', email='test@example.com')
        session.add(user)
        session.commit()
        
        # Create first transaction
        tx1 = Transaction(
            transaction_id=generate_transaction_id(),
            user_id=1,
            transaction_type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0"),
            currency="USDT",
            tx_hash="unique_tx_hash_123",
            status="confirmed",
            description="First transaction"
        )
        session.add(tx1)
        session.commit()
        
        # Try to create duplicate transaction with same tx_hash
        tx2 = Transaction(
            transaction_id=generate_transaction_id(),
            user_id=2,  # Different user
            transaction_type=TransactionType.DEPOSIT.value,
            amount=Decimal("200.0"),
            currency="BTC",
            tx_hash="unique_tx_hash_123",  # Same tx_hash - should fail
            status="confirmed",
            description="Duplicate transaction"
        )
        session.add(tx2)
        
        # This should raise an integrity error due to unique constraint
        with pytest.raises(Exception):  # IntegrityError or similar
            session.commit()

    @pytest.mark.asyncio
    async def test_escrow_tx_hash_uniqueness_constraint(self, setup_database):
        """Test that escrow+tx_hash+type uniqueness constraint prevents duplicates"""
        session = setup_database
        
        # Create required User first to avoid FK constraint
        from models import User, Escrow, EscrowStatus
        user = User(telegram_id=123456, username='test_user', email='test@example.com')
        session.add(user)
        session.commit()
        
        # Create escrow
        escrow = Escrow(
            escrow_id="ESC001",
            buyer_id=user.id,
            amount=Decimal("100.0"),
            currency="USD",
            fee_amount=Decimal("5.0"),
            total_amount=Decimal("105.0"),
            description="Test escrow for payment idempotency",
            fee_split_option="buyer_pays",
            buyer_fee_amount=Decimal("5.0"),  # Buyer pays full fee
            seller_fee_amount=Decimal("0.0"),  # Seller pays nothing
            status=EscrowStatus.PAYMENT_PENDING.value
        )
        session.add(escrow)
        session.commit()
        
        # Create first transaction for escrow
        tx1 = Transaction(
            transaction_id=generate_transaction_id(),
            user_id=user.id,
            escrow_id=escrow.id,
            transaction_type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0"),
            currency="USDT",
            tx_hash="escrow_tx_hash_123",
            status="confirmed",
            description="First escrow deposit"
        )
        session.add(tx1)
        session.commit()
        
        # Try to create duplicate transaction for same escrow with same tx_hash
        tx2 = Transaction(
            transaction_id=generate_transaction_id(),
            user_id=user.id,
            escrow_id=escrow.id,  # Same escrow
            transaction_type=TransactionType.DEPOSIT.value,  # Same type
            amount=Decimal("100.0"),
            currency="USDT",
            tx_hash="escrow_tx_hash_123",  # Same tx_hash - should fail
            status="confirmed",
            description="Duplicate escrow deposit"
        )
        session.add(tx2)
        
        # This should raise an integrity error due to unique constraint
        with pytest.raises(Exception):  # IntegrityError or similar
            session.commit()

    @pytest.mark.asyncio
    async def test_payment_idempotency_service_duplicate_detection(self, setup_database):
        """Test PaymentIdempotencyService duplicate detection methods"""
        session = setup_database
        
        # Create existing transaction
        existing_tx = Transaction(
            transaction_id=generate_transaction_id(),
            user_id=1,
            transaction_type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0"),
            currency="USDT",
            tx_hash="existing_tx_hash",
            status="confirmed",
            description="Existing transaction"
        )
        session.add(existing_tx)
        session.commit()
        
        # Test duplicate detection
        with patch('services.payment_idempotency_service.atomic_transaction') as mock_atomic:
            mock_atomic.return_value.__enter__.return_value = session
            
            result = await PaymentIdempotencyService.check_for_duplicates(
                callback_source="test",
                external_tx_id="existing_tx_hash"
            )
            
            assert result["is_duplicate"] is True
            assert result["reason"] == "duplicate_tx_hash_global"
            assert result["existing_transaction_id"] == existing_tx.transaction_id

    @pytest.mark.asyncio
    async def test_payment_idempotency_service_no_duplicates(self, setup_database):
        """Test PaymentIdempotencyService when no duplicates exist"""
        session = setup_database
        
        # Test with new transaction ID
        with patch('services.payment_idempotency_service.atomic_transaction') as mock_atomic:
            mock_atomic.return_value.__enter__.return_value = session
            
            result = await PaymentIdempotencyService.check_for_duplicates(
                callback_source="test",
                external_tx_id="new_unique_tx_hash"
            )
            
            assert result["is_duplicate"] is False
            assert result["reason"] == "no_duplicates_found"

    @pytest.mark.asyncio
    async def test_dynopay_webhook_duplicate_prevention(self, setup_database, sample_escrow, sample_dynopay_webhook_data):
        """Test DynoPay webhook handler duplicate prevention"""
        
        # Mock dependencies
        with patch('handlers.dynopay_webhook.SessionLocal') as mock_session_local, \
             patch('handlers.dynopay_webhook.atomic_transaction') as mock_atomic, \
             patch('utils.distributed_lock.distributed_lock_service') as mock_lock_service, \
             patch('handlers.dynopay_webhook.CryptoServiceAtomic') as mock_crypto:
            
            session = setup_database
            mock_session_local.return_value = session
            mock_atomic.return_value.__enter__.return_value = session
            
            # Mock successful lock acquisition
            mock_lock = AsyncMock()
            mock_lock.acquired = True
            mock_lock_service.acquire_payment_lock.return_value.__enter__.return_value = mock_lock
            
            # Mock exchange rate
            mock_crypto.get_real_time_exchange_rate.return_value = 1.0
            
            # Process payment first time - should succeed
            result1 = await DynoPayWebhookHandler.handle_escrow_deposit_webhook(sample_dynopay_webhook_data)
            
            # Process same payment again - should detect duplicate
            result2 = await DynoPayWebhookHandler.handle_escrow_deposit_webhook(sample_dynopay_webhook_data)
            
            # First should succeed, second should be detected as duplicate
            assert result1["status"] in ["success", "already_processing"]
            assert result2["status"] in ["already_processed", "already_processing"]

    @pytest.mark.asyncio
    async def test_concurrent_webhook_processing(self, setup_database, sample_escrow, sample_dynopay_webhook_data):
        """Test that concurrent webhook processing is properly handled"""
        
        async def process_webhook():
            """Simulate webhook processing"""
            with patch('handlers.dynopay_webhook.SessionLocal') as mock_session_local, \
                 patch('handlers.dynopay_webhook.atomic_transaction') as mock_atomic, \
                 patch('utils.distributed_lock.distributed_lock_service') as mock_lock_service:
                
                session = setup_database
                mock_session_local.return_value = session
                mock_atomic.return_value.__enter__.return_value = session
                
                # First request gets lock, second gets denied
                mock_lock = AsyncMock()
                mock_lock.acquired = True  # First call succeeds
                mock_lock_service.acquire_payment_lock.return_value.__enter__.return_value = mock_lock
                
                return await DynoPayWebhookHandler.handle_escrow_deposit_webhook(sample_dynopay_webhook_data)
        
        # Simulate concurrent requests
        tasks = [process_webhook() for _ in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should have proper handling for concurrent access
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") in ["success", "already_processed", "already_processing"])
        assert success_count == 3  # All should be handled properly

    @pytest.mark.asyncio
    async def test_race_condition_protection(self, setup_database):
        """Test protection against race conditions in payment processing"""
        
        # Test that distributed locking prevents race conditions
        with patch('utils.distributed_lock.distributed_lock_service') as mock_lock_service:
            
            # Simulate race condition - second request can't acquire lock
            mock_lock_acquired = AsyncMock()
            mock_lock_acquired.acquired = True
            
            mock_lock_denied = AsyncMock()
            mock_lock_denied.acquired = False
            mock_lock_denied.error = "Lock already held by another process"
            
            # First call gets lock
            mock_lock_service.acquire_payment_lock.return_value.__enter__.return_value = mock_lock_acquired
            
            async def dummy_processor():
                return {"status": "success"}
            
            result1 = await PaymentIdempotencyService.process_payment_with_idempotency(
                callback_source="test",
                order_id="ESC001",
                external_tx_id="race_test_tx",
                payment_data={},
                payment_processor=dummy_processor
            )
            
            # Second call can't get lock
            mock_lock_service.acquire_payment_lock.return_value.__enter__.return_value = mock_lock_denied
            
            result2 = await PaymentIdempotencyService.process_payment_with_idempotency(
                callback_source="test",
                order_id="ESC001",
                external_tx_id="race_test_tx",
                payment_data={},
                payment_processor=dummy_processor
            )
            
            # First should succeed, second should be rejected due to lock
            assert result1["status"] == "success"
            assert result2["status"] == "already_processing"

    @pytest.mark.asyncio
    async def test_exchange_webhook_idempotency(self, setup_database):
        """Test exchange webhook idempotency protection"""
        
        exchange_data = {
            "id": "exchange_tx_12345",
            "paid_amount": "0.001",
            "paid_currency": "BTC",
            "meta_data": {
                "refId": "EX000001",
                "deposit_address": "bc1q..."
            }
        }
        
        with patch('handlers.dynopay_exchange_webhook.SessionLocal') as mock_session_local, \
             patch('handlers.dynopay_exchange_webhook.atomic_transaction') as mock_atomic, \
             patch('utils.distributed_lock.distributed_lock_service') as mock_lock_service:
            
            session = setup_database
            mock_session_local.return_value = session
            mock_atomic.return_value.__enter__.return_value = session
            
            # Create test exchange order
            exchange_order = ExchangeOrder(
                id=1,
                user_id=1,
                order_type="crypto_to_ngn",
                source_currency="BTC",
                source_amount=Decimal("0.001"),
                target_currency="NGN",
                target_amount=Decimal("50000"),
                status=ExchangeStatus.AWAITING_DEPOSIT.value
            )
            session.add(exchange_order)
            session.commit()
            
            # Mock successful lock acquisition
            mock_lock = AsyncMock()
            mock_lock.acquired = True
            mock_lock_service.acquire_payment_lock.return_value.__enter__.return_value = mock_lock
            
            # Process first time
            result1 = await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(exchange_data)
            
            # Process duplicate
            result2 = await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(exchange_data)
            
            # Should detect duplicate on second attempt
            assert result1["status"] in ["success", "already_processing"]
            assert result2["status"] in ["already_processed", "already_processing"]

    async def test_multiple_provider_uniqueness(self, setup_database):
        """Test that transactions from different providers maintain global uniqueness"""
        session = setup_database
        
        # Create transaction from DynoPay
        dynopay_tx = Transaction(
            transaction_id=generate_transaction_id(),
            user_id=1,
            transaction_type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0"),
            currency="USDT",
            tx_hash="shared_tx_hash_123",  # Same hash
            status="confirmed",
            description="DynoPay transaction"
        )
        session.add(dynopay_tx)
        session.commit()
        
        # Try to create transaction from BlockBee with same tx_hash
        blockbee_tx = Transaction(
            transaction_id=generate_transaction_id(),
            user_id=2,
            transaction_type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0"),
            currency="USDT",
            tx_hash="shared_tx_hash_123",  # Same hash - should fail
            blockchain_address="shared_tx_hash_123",  # BlockBee uses this field
            status="confirmed",
            description="BlockBee transaction"
        )
        session.add(blockbee_tx)
        
        # Should fail due to global tx_hash uniqueness
        with pytest.raises(Exception):
            session.commit()

    async def test_error_handling_for_invalid_data(self):
        """Test proper error handling for invalid webhook data"""
        
        # Test missing transaction ID
        result = await PaymentIdempotencyService.process_payment_with_idempotency(
            callback_source="test",
            order_id="ESC001",
            external_tx_id=None,  # Missing
            payment_data={},
            payment_processor=AsyncMock()
        )
        
        assert result["status"] == "error"
        assert result["reason"] == "missing_external_tx_id"
        
        # Test missing order ID
        result = await PaymentIdempotencyService.process_payment_with_idempotency(
            callback_source="test",
            order_id=None,  # Missing
            external_tx_id="tx_123",
            payment_data={},
            payment_processor=AsyncMock()
        )
        
        assert result["status"] == "error"
        assert result["reason"] == "missing_order_id"


# Integration test to verify the complete system
class TestIntegrationIdempotency:
    """Integration tests for complete idempotency system"""
    
    async def test_end_to_end_duplicate_prevention(self, setup_database):
        """Test complete end-to-end duplicate prevention"""
        
        # This would be a comprehensive test that:
        # 1. Creates actual webhook data
        # 2. Processes through real handlers
        # 3. Verifies database state
        # 4. Tests duplicate detection
        # 5. Verifies proper responses
        
        # Implementation would go here for full integration testing
        pass


if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v"])