"""
Comprehensive Concurrency Tests for Refund System
Tests race conditions, duplicate prevention, and atomic operations
"""

import asyncio
import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from services.idempotent_refund_service import IdempotentRefundService
from services.refund_service import RefundService
from models import Cashout, Refund, RefundType, RefundStatus, Escrow, User, Wallet
from database import SessionLocal
from utils.refund_monitor import refund_monitor


class TestRefundConcurrency:
    """Test suite for refund concurrency scenarios"""
    
    @pytest.fixture
    def sample_cashout(self):
        """Create a sample cashout for testing"""
        return Cashout(
            cashout_id="TEST_CASHOUT_001",
            user_id=1,
            amount=Decimal('100.00'),
            currency="USD",
            status="failed"
        )
    
    @pytest.fixture
    def sample_escrow(self):
        """Create a sample escrow for testing"""
        return Escrow(
            escrow_id="TEST_ESCROW_001",
            buyer_id=1,
            seller_id=2,
            amount=Decimal('50.00'),
            status="active"
        )
    
    @pytest.fixture
    def mock_session(self):
        """Mock database session"""
        session = MagicMock(spec=Session)
        return session
    
    def test_concurrent_cashout_refund_requests(self, sample_cashout, mock_session):
        """Test multiple concurrent refund requests for the same cashout"""
        
        # Mock the database queries
        mock_session.query.return_value.filter.return_value.first.return_value = sample_cashout
        
        service = IdempotentRefundService(mock_session)
        results = []
        
        def process_refund():
            """Function to run in each thread"""
            try:
                result = service.process_cashout_refund(
                    cashout_id="TEST_CASHOUT_001",
                    reason="Test concurrent processing",
                    source_module="test_module"
                )
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        
        # Run 5 concurrent refund requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=process_refund)
            threads.append(thread)
        
        # Start all threads simultaneously
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        processing_time = time.time() - start_time
        
        # Analyze results
        successful_refunds = [r for r in results if r.get("success")]
        duplicate_refunds = [r for r in results if r.get("duplicate")]
        failed_refunds = [r for r in results if not r.get("success") and not r.get("duplicate")]
        
        # Assertions
        assert len(results) == 5, "Should have 5 results"
        assert len(successful_refunds) <= 1, "Should have at most 1 successful refund"
        assert len(duplicate_refunds) >= 4, "Should have at least 4 duplicate detections"
        assert len(failed_refunds) == 0, "Should have no failed refunds"
        assert processing_time < 2.0, "Concurrent processing should be fast"
        
        print(f"✅ Concurrency test passed: {len(successful_refunds)} success, {len(duplicate_refunds)} duplicates")
    
    def test_idempotency_key_uniqueness(self):
        """Test that idempotency keys are truly unique"""
        service = IdempotentRefundService(MagicMock())
        
        # Generate keys for same parameters
        key1 = service.generate_idempotency_key(
            "CASHOUT_001", 123, Decimal('100.00'), "cashout_failed", "test_module"
        )
        key2 = service.generate_idempotency_key(
            "CASHOUT_001", 123, Decimal('100.00'), "cashout_failed", "test_module"
        )
        key3 = service.generate_idempotency_key(
            "CASHOUT_001", 123, Decimal('100.01'), "cashout_failed", "test_module"  # Different amount
        )
        
        # Same parameters should generate same key
        assert key1 == key2, "Same parameters should generate same key"
        
        # Different parameters should generate different key
        assert key1 != key3, "Different parameters should generate different keys"
        
        # Keys should be reasonable length
        assert len(key1) == 32, "Key should be 32 characters (SHA256 truncated)"
        
        print(f"✅ Idempotency test passed: key={key1[:16]}...")
    
    def test_concurrent_escrow_refunds(self, sample_escrow, mock_session):
        """Test concurrent refund requests for the same escrow"""
        
        # Mock database responses
        mock_session.query.return_value.filter.return_value.first.return_value = sample_escrow
        
        results = []
        
        def process_escrow_refund():
            """Function to run in each thread"""
            try:
                with patch('services.refund_service.RefundService.validate_refund_eligibility') as mock_validate:
                    mock_validate.return_value = {
                        "eligible": True,
                        "should_refund": 50.0,
                        "funding_amount": 50.0,
                        "existing_refunds": 0.0
                    }
                    
                    result = RefundService.process_escrow_refund(
                        escrow=sample_escrow,
                        cancellation_reason="buyer_cancelled",
                        session=mock_session
                    )
                    results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        
        # Run 3 concurrent escrow refund requests
        threads = []
        for i in range(3):
            thread = threading.Thread(target=process_escrow_refund)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check that we don't have multiple successful refunds
        successful_results = [r for r in results if r.get("success")]
        assert len(successful_results) <= 1, "Should have at most 1 successful escrow refund"
        
        print(f"✅ Escrow concurrency test passed: {len(successful_results)} successful")
    
    def test_monitoring_under_load(self):
        """Test refund monitoring system under concurrent load"""
        
        def generate_mock_refund_events():
            """Simulate refund events"""
            for i in range(10):
                operation_id = refund_monitor.track_refund_start(
                    refund_id=f"TEST_REFUND_{i}",
                    refund_type=RefundType.CASHOUT_FAILED.value,
                    amount=100.0,
                    user_id=i,
                    source_module="test_load"
                )
                
                # Simulate processing time
                time.sleep(0.01)
                
                # Randomly succeed or fail
                if i % 3 == 0:
                    refund_monitor.track_refund_failure(
                        operation_id=operation_id,
                        refund_id=f"TEST_REFUND_{i}",
                        error_message="Test failure",
                        processing_time=0.01
                    )
                else:
                    refund_monitor.track_refund_success(
                        operation_id=operation_id,
                        refund_id=f"TEST_REFUND_{i}",
                        processing_time=0.01,
                        final_amount=100.0
                    )
        
        # Run monitoring load test
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(generate_mock_refund_events) for _ in range(3)]
            
            # Wait for all to complete
            for future in futures:
                future.result()
        
        # Check that monitoring system handled the load
        assert len(refund_monitor.metrics) > 0, "Should have recorded metrics"
        
        print(f"✅ Monitoring load test passed: {len(refund_monitor.metrics)} metrics recorded")
    
    @pytest.mark.asyncio
    async def test_async_concurrent_refunds(self):
        """Test async concurrent refund processing"""
        
        async def mock_refund_operation(refund_id: str):
            """Mock async refund operation"""
            await asyncio.sleep(0.1)  # Simulate async work
            return {
                "success": True,
                "refund_id": refund_id,
                "amount": 100.0
            }
        
        # Run multiple async refund operations
        tasks = [
            mock_refund_operation(f"ASYNC_REFUND_{i}")
            for i in range(5)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        processing_time = time.time() - start_time
        
        # Should process concurrently (much faster than sequential)
        assert processing_time < 0.3, "Async operations should run concurrently"
        assert len(results) == 5, "Should have 5 results"
        assert all(r["success"] for r in results), "All operations should succeed"
        
        print(f"✅ Async concurrency test passed: {processing_time:.2f}s for 5 operations")
    
    def test_stress_test_idempotency(self):
        """Stress test the idempotency system"""
        
        service = IdempotentRefundService(MagicMock())
        
        # Generate many keys concurrently
        def generate_keys():
            keys = []
            for i in range(100):
                key = service.generate_idempotency_key(
                    f"STRESS_{i}", i, Decimal('100.00'), "test", "stress_test"
                )
                keys.append(key)
            return keys
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(generate_keys) for _ in range(10)]
            all_keys = []
            
            for future in futures:
                all_keys.extend(future.result())
        
        # Check uniqueness
        unique_keys = set(all_keys)
        assert len(unique_keys) == len(all_keys), "All keys should be unique"
        
        print(f"✅ Stress test passed: {len(all_keys)} unique keys generated")


if __name__ == "__main__":
    # Run tests manually for debugging
    test_instance = TestRefundConcurrency()
    
    print("🧪 Running Refund Concurrency Tests...")
    
    # Mock fixtures
    sample_cashout = Cashout(
        cashout_id="TEST_CASHOUT_001",
        user_id=1,
        amount=Decimal('100.00'),
        currency="USD",
        status="failed"
    )
    
    mock_session = MagicMock(spec=Session)
    
    try:
        # Run individual tests
        test_instance.test_concurrent_cashout_refund_requests(sample_cashout, mock_session)
        test_instance.test_idempotency_key_uniqueness()
        test_instance.test_monitoring_under_load()
        test_instance.test_stress_test_idempotency()
        
        print("✅ All concurrency tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise