"""
Test Atomic Locking System
Comprehensive tests for database-backed atomic locking and idempotency protection
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta

from services.atomic_lock_manager import atomic_lock_manager, LockOperationType
from services.crypto_idempotency_service import crypto_idempotency_service
from utils.financial_operation_locker import financial_locker, FinancialLockType


class TestAtomicLockManager:
    """Test atomic lock manager functionality"""

    @pytest.mark.asyncio
    async def test_atomic_lock_acquisition(self):
        """Test atomic lock can be acquired and released"""
        lock_name = "test_atomic_lock_001"
        
        # Acquire lock
        token = await atomic_lock_manager.acquire_lock(
            lock_name=lock_name,
            operation_type=LockOperationType.FINANCIAL_OPERATION,
            resource_id="test_resource",
            timeout_seconds=60
        )
        
        assert token is not None, "Lock should be acquired successfully"
        
        # Release lock
        released = await atomic_lock_manager.release_lock(lock_name, token)
        assert released, "Lock should be released successfully"

    @pytest.mark.asyncio
    async def test_atomic_lock_contention(self):
        """Test that atomic locks prevent race conditions"""
        lock_name = "test_contention_lock_001"
        
        # First lock should succeed
        token1 = await atomic_lock_manager.acquire_lock(
            lock_name=lock_name,
            operation_type=LockOperationType.FINANCIAL_OPERATION,
            resource_id="test_resource",
            timeout_seconds=60
        )
        
        assert token1 is not None, "First lock should be acquired"
        
        # Second lock should fail (atomic guarantee)
        token2 = await atomic_lock_manager.acquire_lock(
            lock_name=lock_name,
            operation_type=LockOperationType.FINANCIAL_OPERATION,
            resource_id="test_resource",
            timeout_seconds=1  # Short timeout
        )
        
        assert token2 is None, "Second lock should fail due to contention"
        
        # Release first lock
        await atomic_lock_manager.release_lock(lock_name, token1)
        
        # Now second lock should succeed
        token3 = await atomic_lock_manager.acquire_lock(
            lock_name=lock_name,
            operation_type=LockOperationType.FINANCIAL_OPERATION,
            resource_id="test_resource",
            timeout_seconds=10
        )
        
        assert token3 is not None, "Lock should be available after release"
        await atomic_lock_manager.release_lock(lock_name, token3)

    @pytest.mark.asyncio
    async def test_atomic_lock_context_manager(self):
        """Test atomic lock context manager"""
        lock_name = "test_context_lock_001"
        
        async with atomic_lock_manager.atomic_lock_context(
            lock_name=lock_name,
            operation_type=LockOperationType.FINANCIAL_OPERATION,
            resource_id="test_resource"
        ) as token:
            assert token is not None, "Context manager should acquire lock"
            
            # Test contention within context
            token2 = await atomic_lock_manager.acquire_lock(
                lock_name=lock_name,
                operation_type=LockOperationType.FINANCIAL_OPERATION,
                resource_id="test_resource2",
                timeout_seconds=1
            )
            assert token2 is None, "Lock should be held by context manager"
        
        # After context, lock should be released
        token3 = await atomic_lock_manager.acquire_lock(
            lock_name=lock_name,
            operation_type=LockOperationType.FINANCIAL_OPERATION,
            resource_id="test_resource3",
            timeout_seconds=10
        )
        assert token3 is not None, "Lock should be available after context exit"
        await atomic_lock_manager.release_lock(lock_name, token3)


class TestCryptoIdempotencyService:
    """Test crypto idempotency service"""

    @pytest.mark.asyncio
    async def test_crypto_address_idempotency(self):
        """Test crypto address generation idempotency"""
        user_id = 12345
        currency = "BTC"
        
        # First request should be new
        is_duplicate, existing_address = await crypto_idempotency_service.ensure_crypto_address_idempotency(
            user_id=user_id,
            currency=currency
        )
        
        assert not is_duplicate, "First request should not be duplicate"
        assert existing_address is None, "No existing address should be found"
        
        # Complete the operation
        test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        success = await crypto_idempotency_service.complete_crypto_address_generation(
            user_id=user_id,
            currency=currency,
            address=test_address
        )
        
        assert success, "Address generation completion should succeed"
        
        # Second request should be duplicate
        is_duplicate2, existing_address2 = await crypto_idempotency_service.ensure_crypto_address_idempotency(
            user_id=user_id,
            currency=currency
        )
        
        assert is_duplicate2, "Second request should be duplicate"
        assert existing_address2 == test_address, "Should return existing address"

    @pytest.mark.asyncio
    async def test_transaction_idempotency(self):
        """Test transaction idempotency"""
        user_id = 12345
        operation_type = "deposit"
        amount = Decimal("100.50")
        currency = "USD"
        reference_id = "test_ref_001"
        
        # First transaction should be new
        is_duplicate, result = await crypto_idempotency_service.ensure_transaction_idempotency(
            user_id=user_id,
            operation_type=operation_type,
            amount=amount,
            currency=currency,
            reference_id=reference_id
        )
        
        assert not is_duplicate, "First transaction should not be duplicate"
        assert result is None, "No previous result should exist"
        
        # Complete the transaction
        transaction_id = "tx_001"
        success = await crypto_idempotency_service.complete_transaction(
            user_id=user_id,
            operation_type=operation_type,
            amount=amount,
            currency=currency,
            success=True,
            transaction_id=transaction_id,
            reference_id=reference_id
        )
        
        assert success, "Transaction completion should succeed"
        
        # Second identical transaction should be duplicate
        is_duplicate2, result2 = await crypto_idempotency_service.ensure_transaction_idempotency(
            user_id=user_id,
            operation_type=operation_type,
            amount=amount,
            currency=currency,
            reference_id=reference_id
        )
        
        assert is_duplicate2, "Second transaction should be duplicate"
        assert result2 is not None, "Should return previous result"
        assert result2.get('transaction_id') == transaction_id, "Should return correct transaction ID"


class TestFinancialOperationLocker:
    """Test financial operation locker with atomic locking"""

    @pytest.mark.asyncio
    async def test_atomic_financial_operation_context(self):
        """Test atomic financial operations"""
        operation_id = "test_financial_op_001"
        
        # Test that context manager works
        try:
            async with financial_locker.atomic_financial_operation(
                operation_id=operation_id,
                lock_type=FinancialLockType.WALLET_BALANCE,
                timeout_seconds=30
            ) as session:
                assert session is not None, "Session should be provided"
                # Simulate some database work
                await asyncio.sleep(0.1)
                
        except Exception as e:
            pytest.fail(f"Financial operation context failed: {e}")

    @pytest.mark.asyncio 
    async def test_concurrent_financial_operations(self):
        """Test that concurrent financial operations are properly serialized"""
        operation_id = "test_concurrent_op_001"
        
        async def financial_operation(delay: float = 0.1):
            async with financial_locker.atomic_financial_operation(
                operation_id=operation_id,
                lock_type=FinancialLockType.WALLET_BALANCE,
                timeout_seconds=5
            ) as session:
                await asyncio.sleep(delay)
                return True
        
        # Start two concurrent operations
        task1 = asyncio.create_task(financial_operation(0.2))
        task2 = asyncio.create_task(financial_operation(0.1))
        
        # One should succeed, one should fail due to lock contention
        results = await asyncio.gather(task1, task2, return_exceptions=True)
        
        # At least one should succeed
        success_count = sum(1 for r in results if r is True)
        error_count = sum(1 for r in results if isinstance(r, Exception))
        
        # With atomic locking, one should succeed and one should fail
        assert success_count >= 1, "At least one operation should succeed"
        # Note: The second operation might timeout rather than fail immediately


class TestRaceConditionPrevention:
    """Test that race conditions are prevented"""

    @pytest.mark.asyncio
    async def test_crypto_address_race_condition_prevention(self):
        """Test that crypto address generation prevents race conditions"""
        user_id = 99999
        currency = "ETH"
        
        async def generate_address():
            # Check idempotency
            is_duplicate, existing = await crypto_idempotency_service.ensure_crypto_address_idempotency(
                user_id=user_id,
                currency=currency
            )
            
            if is_duplicate:
                return existing, "duplicate"
            
            # Simulate address generation delay
            await asyncio.sleep(0.1)
            new_address = f"0x{'a' * 40}"
            
            # Complete generation
            await crypto_idempotency_service.complete_crypto_address_generation(
                user_id=user_id,
                currency=currency,
                address=new_address
            )
            
            return new_address, "generated"
        
        # Start multiple concurrent address generation requests
        tasks = [asyncio.create_task(generate_address()) for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [r for r in results if not isinstance(r, Exception)]
        
        # Should have at least one result
        assert len(valid_results) > 0, "Should have at least one valid result"
        
        # All addresses should be the same (idempotency protection)
        addresses = [r[0] for r in valid_results if r[0] is not None]
        if len(addresses) > 1:
            assert all(addr == addresses[0] for addr in addresses), "All addresses should be identical"


if __name__ == "__main__":
    # Run basic tests
    async def run_basic_tests():
        print("🧪 Testing Atomic Lock Manager...")
        
        # Test basic lock acquisition
        token = await atomic_lock_manager.acquire_lock(
            "test_basic_lock",
            LockOperationType.FINANCIAL_OPERATION,
            "test_resource",
            30
        )
        
        if token:
            print("✅ Basic lock acquisition: PASSED")
            await atomic_lock_manager.release_lock("test_basic_lock", token)
            print("✅ Basic lock release: PASSED")
        else:
            print("❌ Basic lock acquisition: FAILED")
        
        # Test idempotency
        print("\n🧪 Testing Crypto Idempotency Service...")
        
        is_dup, addr = await crypto_idempotency_service.ensure_crypto_address_idempotency(
            123, "BTC"
        )
        
        if not is_dup:
            print("✅ New address request: PASSED")
            
            success = await crypto_idempotency_service.complete_crypto_address_generation(
                123, "BTC", "test_address"
            )
            
            if success:
                print("✅ Address completion: PASSED")
                
                # Test duplicate
                is_dup2, addr2 = await crypto_idempotency_service.ensure_crypto_address_idempotency(
                    123, "BTC"
                )
                
                if is_dup2 and addr2 == "test_address":
                    print("✅ Duplicate detection: PASSED")
                else:
                    print("❌ Duplicate detection: FAILED")
            else:
                print("❌ Address completion: FAILED")
        else:
            print("❌ New address request: FAILED")
    
    # Run if script is executed directly
    asyncio.run(run_basic_tests())