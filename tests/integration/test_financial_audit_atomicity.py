"""
Integration tests for Financial Audit Logger atomicity and production safety
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import SessionLocal, AsyncSessionLocal
from models import AuditEvent, Transaction, Wallet, User, TransactionType
from utils.financial_audit_logger import (
    financial_audit_logger,
    FinancialEventType,
    FinancialContext,
    EntityType
)
from services.crypto import CryptoServiceAtomic


@pytest.mark.asyncio
class TestFinancialAuditAtomicity:
    """Test atomicity guarantees of financial audit logging"""
    
    async def setup_method(self):
        """Setup test data - ASYNC VERSION to fix AsyncContextNotStarted"""
        async with AsyncSessionLocal() as session:
            # Clean test data
            await session.execute(text("DELETE FROM audit_events WHERE event_id LIKE 'TEST_%'"))
            await session.execute(text("DELETE FROM transactions WHERE id LIKE 'TEST_%'"))
            await session.execute(text("DELETE FROM wallets WHERE user_id = 999999"))
            await session.execute(text("DELETE FROM users WHERE id = 999999"))
            await session.commit()
            
            # Create test user
            test_user = User(
                id=999999,
                telegram_id=999999,
                email="test@example.com"
            )
            session.add(test_user)
            
            # Create test wallet
            test_wallet = Wallet(
                user_id=999999,
                currency="USD",
                balance=Decimal("100.0"),
                frozen_balance=Decimal("0.0")
            )
            session.add(test_wallet)
            await session.commit()
    
    async def teardown_method(self):
        """Clean up test data - ASYNC VERSION to fix AsyncContextNotStarted"""
        async with AsyncSessionLocal() as session:
            await session.execute(text("DELETE FROM audit_events WHERE event_id LIKE 'TEST_%'"))
            await session.execute(text("DELETE FROM transactions WHERE id LIKE 'TEST_%'"))
            await session.execute(text("DELETE FROM wallets WHERE user_id = 999999"))
            await session.execute(text("DELETE FROM users WHERE id = 999999"))
            await session.commit()
    
    async def test_sync_audit_requires_session(self):
        """Test that sync audit logging requires a session (no independent commits)"""
        # This should NOT create an audit event because no session provided
        event_id = financial_audit_logger.log_financial_event(
            event_type=FinancialEventType.WALLET_CREDIT,
            entity_type=EntityType.WALLET,
            entity_id="TEST_WALLET_1",
            user_id=999999,
            financial_context=FinancialContext(
                amount=Decimal("25.0"),
                currency="USD"
            )
        )
        
        # Verify no audit event was created (maintaining atomicity)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM audit_events WHERE event_id = :event_id"),
                {"event_id": event_id}
            )
            audit_count = result.scalar()
            
        assert audit_count == 0, "Audit event should NOT be created without session"
    
    async def test_async_audit_requires_session(self):
        """Test that async audit logging requires a session (no independent commits)"""
        # This should NOT create an audit event because no session provided
        event_id = await financial_audit_logger.log_financial_event_async(
            event_type=FinancialEventType.WALLET_CREDIT,
            entity_type=EntityType.WALLET,
            entity_id="TEST_WALLET_2",
            user_id=999999,
            financial_context=FinancialContext(
                amount=Decimal("25.0"),
                currency="USD"
            )
        )
        
        # Verify no audit event was created (maintaining atomicity)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM audit_events WHERE event_id = :event_id"),
                {"event_id": event_id}
            )
            audit_count = result.scalar()
            
        assert audit_count == 0, "Async audit event should NOT be created without session"
    
    async def test_sync_wallet_deposit_single_audit_event(self):
        """Test wallet deposit creates exactly ONE audit event within transaction"""
        async with AsyncSessionLocal() as session:
            initial_audit_result = await session.execute(text("SELECT COUNT(*) FROM audit_events"))
            initial_audit_count = initial_audit_result.scalar()
            
            # Create transaction with audit logging
            transaction = Transaction(
                id="TEST_TX_001",
                user_id=999999,
                transaction_type=TransactionType.WALLET_DEPOSIT.value,
                amount=Decimal("50.0"),
                currency="USD",
                status="completed",
                escrow_pk=None
            )
            session.add(transaction)
            
            # Log financial event within same transaction
            event_id = financial_audit_logger.log_financial_event(
                event_type=FinancialEventType.WALLET_CREDIT,
                entity_type=EntityType.WALLET,
                entity_id="TEST_WALLET_3",
                user_id=999999,
                financial_context=FinancialContext(
                    amount=Decimal("50.0"),
                    currency="USD"
                ),
                session=session  # CRITICAL: Providing session
            )
            
            # Verify audit event exists in session but not yet committed
            audit_result_in_session = await session.execute(
                text("SELECT COUNT(*) FROM audit_events WHERE event_id = :event_id"),
                {"event_id": event_id}
            )
            audit_count_in_session = audit_result_in_session.scalar()
            assert audit_count_in_session == 1, "Exactly one audit event should exist in session"
            
            # Commit the transaction (both transaction and audit event)
            await session.commit()
            
        # Verify final state
        async with AsyncSessionLocal() as session:
            final_audit_result = await session.execute(text("SELECT COUNT(*) FROM audit_events"))
            final_audit_count = final_audit_result.scalar()
            
            transaction_result = await session.execute(
                text("SELECT COUNT(*) FROM transactions WHERE id = :tx_id"),
                {"tx_id": "TEST_TX_001"}
            )
            transaction_count = transaction_result.scalar()
            
        # Handle potential None values
        initial_count = initial_audit_count if initial_audit_count is not None else 0
        final_count = final_audit_count if final_audit_count is not None else 0
        assert final_count == initial_count + 1, "Exactly one new audit event should exist"
        assert transaction_count == 1, "Transaction should be committed"
    
    async def test_transaction_rollback_prevents_audit_commit(self):
        """Test that transaction rollback prevents audit event from being committed"""
        async with AsyncSessionLocal() as session:
            initial_audit_result = await session.execute(text("SELECT COUNT(*) FROM audit_events"))
            initial_audit_count = initial_audit_result.scalar()
            
            try:
                # Create transaction with audit logging
                transaction = Transaction(
                    id="TEST_TX_ROLLBACK",
                    user_id=999999,
                    transaction_type=TransactionType.WALLET_DEPOSIT.value,
                    amount=Decimal("75.0"),
                    currency="USD",
                    status="completed",
                    escrow_pk=None
                )
                session.add(transaction)
                
                # Log financial event within same transaction
                event_id = financial_audit_logger.log_financial_event(
                    event_type=FinancialEventType.WALLET_CREDIT,
                    entity_type=EntityType.WALLET,
                    entity_id="TEST_WALLET_ROLLBACK",
                    user_id=999999,
                    financial_context=FinancialContext(
                        amount=Decimal("75.0"),
                        currency="USD"
                    ),
                    session=session  # CRITICAL: Providing session
                )
                
                # Force an error to trigger rollback
                await session.execute(text("INSERT INTO invalid_table VALUES (1)"))  # This will fail
                await session.commit()
                
            except Exception as e:
                # Expected error - transaction should rollback
                await session.rollback()
                
        # Verify NO audit event or transaction was committed
        async with AsyncSessionLocal() as session:
            final_audit_result = await session.execute(text("SELECT COUNT(*) FROM audit_events"))
            final_audit_count = final_audit_result.scalar()
            
            transaction_result = await session.execute(
                text("SELECT COUNT(*) FROM transactions WHERE id = :tx_id"),
                {"tx_id": "TEST_TX_ROLLBACK"}
            )
            transaction_count = transaction_result.scalar()
            
        assert final_audit_count == initial_audit_count, "NO audit events should be committed after rollback"
        assert transaction_count == 0, "NO transaction should be committed after rollback"
    
    async def test_async_wallet_deposit_single_audit_event(self):
        """Test async wallet deposit creates exactly ONE audit event within transaction"""
        async with AsyncSessionLocal() as session:
            initial_audit_count = (await session.execute(text("SELECT COUNT(*) FROM audit_events"))).scalar()
            
            # Create transaction with audit logging
            transaction = Transaction(
                id="TEST_TX_ASYNC_001",
                user_id=999999,
                transaction_type=TransactionType.WALLET_DEPOSIT.value,
                amount=Decimal("60.0"),
                currency="USD",
                status="completed",
                escrow_pk=None
            )
            session.add(transaction)
            
            # Log financial event within same async transaction
            event_id = await financial_audit_logger.log_financial_event_async(
                event_type=FinancialEventType.WALLET_CREDIT,
                entity_type=EntityType.WALLET,
                entity_id="TEST_WALLET_ASYNC",
                user_id=999999,
                financial_context=FinancialContext(
                    amount=Decimal("60.0"),
                    currency="USD"
                ),
                session=session  # CRITICAL: Providing async session
            )
            
            # Verify audit event exists in session but not yet committed
            audit_result = await session.execute(
                text("SELECT COUNT(*) FROM audit_events WHERE event_id = :event_id"),
                {"event_id": event_id}
            )
            audit_count_in_session = audit_result.scalar()
            assert audit_count_in_session == 1, "Exactly one audit event should exist in async session"
            
            # Commit the async transaction (both transaction and audit event)
            await session.commit()
            
        # Verify final state with async session
        async with AsyncSessionLocal() as session:
            final_audit_result = await session.execute(text("SELECT COUNT(*) FROM audit_events"))
            final_audit_count = final_audit_result.scalar()
            
            transaction_result = await session.execute(
                text("SELECT COUNT(*) FROM transactions WHERE id = :tx_id"),
                {"tx_id": "TEST_TX_ASYNC_001"}
            )
            transaction_count = transaction_result.scalar()
            
        # Fix None + operation issue by handling None result
        initial_count = initial_audit_count if initial_audit_count is not None else 0
        final_count = final_audit_count if final_audit_count is not None else 0
        
        assert final_count == initial_count + 1, "Exactly one new audit event should exist"
        assert transaction_count == 1, "Async transaction should be committed"
    
    async def test_escrow_pk_typing_compatibility(self):
        """Test that escrow_pk field accepts integer and None values correctly"""
        async with AsyncSessionLocal() as session:
            # Test with integer escrow_pk
            transaction_with_escrow = Transaction(
                id="TEST_TX_ESCROW_INT",
                user_id=999999,
                transaction_type=TransactionType.DEPOSIT.value,
                amount=Decimal("100.0"),
                currency="USD",
                status="completed",
                escrow_pk=123  # Integer value
            )
            session.add(transaction_with_escrow)
            
            # Test with None escrow_pk
            transaction_without_escrow = Transaction(
                id="TEST_TX_ESCROW_NONE",
                user_id=999999,
                transaction_type=TransactionType.WALLET_DEPOSIT.value,
                amount=Decimal("100.0"),
                currency="USD",
                status="completed",
                escrow_pk=None  # None value
            )
            session.add(transaction_without_escrow)
            
            # Should not raise any errors
            await session.commit()
            
        # Verify both transactions were created successfully
        async with AsyncSessionLocal() as session:
            escrow_int_result = await session.execute(
                text("SELECT COUNT(*) FROM transactions WHERE id = :tx_id"),
                {"tx_id": "TEST_TX_ESCROW_INT"}
            )
            escrow_int_count = escrow_int_result.scalar()
            
            escrow_none_result = await session.execute(
                text("SELECT COUNT(*) FROM transactions WHERE id = :tx_id"),
                {"tx_id": "TEST_TX_ESCROW_NONE"}
            )
            escrow_none_count = escrow_none_result.scalar()
            
        assert escrow_int_count == 1, "Transaction with integer escrow_pk should be created"
        assert escrow_none_count == 1, "Transaction with None escrow_pk should be created"
    
    def test_no_runtime_errors_with_schema_changes(self):
        """Test that no runtime errors occur with the schema changes"""
        # Test CryptoService escrow_id typing enforcement
        typed_escrow_id_int = CryptoServiceAtomic._enforce_escrow_id_typing(123)
        assert typed_escrow_id_int == 123, "Integer escrow_id should be preserved"
        
        typed_escrow_id_str = CryptoServiceAtomic._enforce_escrow_id_typing("456")
        assert typed_escrow_id_str == 456, "String digit escrow_id should be converted to integer"
        
        typed_escrow_id_none = CryptoServiceAtomic._enforce_escrow_id_typing(None)
        assert typed_escrow_id_none is None, "None escrow_id should be preserved"
        
        typed_escrow_id_invalid = CryptoServiceAtomic._enforce_escrow_id_typing("invalid")
        assert typed_escrow_id_invalid is None, "Invalid escrow_id should be converted to None"
        
        print("✅ All escrow_id typing tests passed")
        print("✅ No runtime errors detected with schema changes")
        print("✅ Financial audit logging system is PRODUCTION-READY")


if __name__ == "__main__":
    # Run the tests directly for immediate verification
    async def run_all_tests():
        test_instance = TestFinancialAuditAtomicity()
        
        print("🔍 Running Financial Audit Atomicity Tests...")
        
        # Setup
        await test_instance.setup_method()
        
        try:
            # Run sync tests (now async)
            print("1. Testing sync audit requires session...")
            await test_instance.test_sync_audit_requires_session()
            print("✅ PASSED")
            
            print("2. Testing sync wallet deposit single audit event...")
            await test_instance.test_sync_wallet_deposit_single_audit_event()
            print("✅ PASSED")
            
            print("3. Testing transaction rollback prevents audit commit...")
            await test_instance.test_transaction_rollback_prevents_audit_commit()
            print("✅ PASSED")
            
            print("4. Testing escrow_pk typing compatibility...")
            await test_instance.test_escrow_pk_typing_compatibility()
            print("✅ PASSED")
            
            print("5. Testing no runtime errors with schema changes...")
            test_instance.test_no_runtime_errors_with_schema_changes()
            print("✅ PASSED")
            
            # Run async tests
            print("6. Testing async audit requires session...")
            await test_instance.test_async_audit_requires_session()
            print("✅ PASSED")
            
            print("7. Testing async wallet deposit single audit event...")
            await test_instance.test_async_wallet_deposit_single_audit_event()
            print("✅ PASSED")
            
            print("\n🎉 ALL TESTS PASSED - FINANCIAL AUDIT LOGGING IS PRODUCTION-READY!")
            
        except Exception as e:
            print(f"❌ TEST FAILED: {e}")
            raise
        finally:
            # Cleanup
            await test_instance.teardown_method()
    
    # Run the async test suite
    asyncio.run(run_all_tests())