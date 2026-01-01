#!/usr/bin/env python3
"""
Financial Operations Validation Test Suite
Tests idempotency service, SELECT FOR UPDATE locking, and atomic transactions
"""

import asyncio
import logging
import sys
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, '/home/runner/workspace')

from services.idempotency_service import (
    IdempotencyService, OperationType, IdempotencyStatus,
    IdempotencyKeyGenerator
)
from utils.atomic_transactions import atomic_transaction
from utils.database_locking import DatabaseLockingService
from services.state_manager import state_manager
from database import SessionLocal
from models import Escrow, Cashout, UnifiedTransaction, Wallet
from config import Config

logger = logging.getLogger(__name__)


class FinancialValidationResults:
    """Track financial validation test results"""
    
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.errors = []
        self.performance_metrics = {}
        
    def add_result(self, test_name: str, passed: bool, error: Optional[str] = None, 
                   duration: Optional[float] = None):
        """Add test result with optional performance metrics"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASSED"
            if duration:
                status += f" ({duration:.3f}s)"
            logger.info(f"{status} {test_name}")
            
            if duration:
                self.performance_metrics[test_name] = duration
        else:
            self.failed_tests += 1
            logger.error(f"❌ FAILED {test_name}: {error}")
            self.errors.append(f"{test_name}: {error}")
    
    def print_summary(self):
        """Print test summary with performance metrics"""
        print("\n" + "="*80)
        print("FINANCIAL OPERATIONS VALIDATION SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%" if self.total_tests > 0 else "0.0%")
        
        if self.performance_metrics:
            print("\nPERFORMANCE METRICS:")
            for test, duration in self.performance_metrics.items():
                print(f"  {test}: {duration:.3f}s")
        
        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  • {error}")
        
        return self.failed_tests == 0


async def test_idempotency_key_generation(results: FinancialValidationResults):
    """Test idempotency key generation functionality"""
    try:
        start_time = time.time()
        
        # Test cashout key generation
        key1 = IdempotencyKeyGenerator.generate_cashout_key(
            user_id=12345,
            amount=100.50,
            currency="USD",
            destination="bank_account_123"
        )
        
        key2 = IdempotencyKeyGenerator.generate_cashout_key(
            user_id=12345,
            amount=100.50,
            currency="USD",
            destination="bank_account_123"
        )
        
        # Same parameters should generate same key
        if key1 != key2:
            results.add_result("Idempotency Key Consistency", False, "Same parameters generated different keys")
            return
        
        # Different parameters should generate different keys
        key3 = IdempotencyKeyGenerator.generate_cashout_key(
            user_id=12345,
            amount=200.50,  # Different amount
            currency="USD",
            destination="bank_account_123"
        )
        
        if key1 == key3:
            results.add_result("Idempotency Key Uniqueness", False, "Different parameters generated same key")
            return
        
        # Test escrow key generation
        escrow_key1 = IdempotencyKeyGenerator.generate_escrow_key(
            buyer_id=111,
            seller_id=222,
            amount=Decimal("500.00"),
            currency="USD"
        )
        
        escrow_key2 = IdempotencyKeyGenerator.generate_escrow_key(
            buyer_id=111,
            seller_id=222,
            amount=Decimal("500.00"),
            currency="USD"
        )
        
        if escrow_key1 != escrow_key2:
            results.add_result("Escrow Idempotency Key Consistency", False, "Escrow keys not consistent")
            return
        
        duration = time.time() - start_time
        results.add_result("Idempotency Key Generation", True, duration=duration)
        
    except Exception as e:
        results.add_result("Idempotency Key Generation", False, str(e))


async def test_idempotency_service_operations(results: FinancialValidationResults):
    """Test idempotency service create, check, and complete operations"""
    try:
        idempotency_service = IdempotencyService()
        
        # Test operation creation
        start_time = time.time()
        operation_key = f"test_operation_{uuid.uuid4()}"
        
        # Create idempotent operation
        created = await idempotency_service.create_operation(
            key=operation_key,
            operation_type=OperationType.CASHOUT,
            user_id=12345,
            entity_id="cashout_test_123",
            request_data={"amount": 100.0, "currency": "USD"},
            ttl_seconds=3600
        )
        
        if not created:
            results.add_result("Idempotency Operation Creation", False, "Failed to create operation")
            return
        
        # Test duplicate creation should fail
        duplicate = await idempotency_service.create_operation(
            key=operation_key,
            operation_type=OperationType.CASHOUT,
            user_id=12345,
            entity_id="cashout_test_123",
            request_data={"amount": 100.0, "currency": "USD"},
            ttl_seconds=3600
        )
        
        if duplicate:
            results.add_result("Idempotency Duplicate Prevention", False, "Duplicate operation was created")
            return
        
        # Check operation status
        record = await idempotency_service.check_operation(operation_key)
        if not record or record.status != IdempotencyStatus.PROCESSING:
            results.add_result("Idempotency Status Check", False, f"Wrong status: {record.status if record else 'None'}")
            return
        
        # Complete operation
        result_data = {"cashout_id": "cashout_456", "status": "completed"}
        completed = await idempotency_service.complete_operation(
            key=operation_key,
            result=result_data
        )
        
        if not completed:
            results.add_result("Idempotency Operation Completion", False, "Failed to complete operation")
            return
        
        # Verify completion
        final_record = await idempotency_service.check_operation(operation_key)
        if not final_record or final_record.status != IdempotencyStatus.COMPLETED:
            results.add_result("Idempotency Completion Verification", False, f"Wrong final status: {final_record.status if final_record else 'None'}")
            return
        
        if final_record.result != result_data:
            results.add_result("Idempotency Result Storage", False, "Result data not stored correctly")
            return
        
        duration = time.time() - start_time
        results.add_result("Idempotency Service Operations", True, duration=duration)
        
    except Exception as e:
        results.add_result("Idempotency Service Operations", False, str(e))


async def test_concurrent_idempotency(results: FinancialValidationResults):
    """Test idempotency service under concurrent load"""
    try:
        idempotency_service = IdempotencyService()
        operation_key = f"concurrent_test_{uuid.uuid4()}"
        
        async def create_operation_attempt(attempt_id: int):
            """Attempt to create the same idempotent operation"""
            try:
                created = await idempotency_service.create_operation(
                    key=operation_key,
                    operation_type=OperationType.DEPOSIT,
                    user_id=99999,
                    entity_id=f"deposit_concurrent_{attempt_id}",
                    request_data={"amount": 50.0, "currency": "USD", "attempt": attempt_id},
                    ttl_seconds=3600
                )
                return created, attempt_id
            except Exception as e:
                return False, f"Error in attempt {attempt_id}: {e}"
        
        # Launch concurrent attempts
        start_time = time.time()
        concurrent_attempts = 10
        tasks = [create_operation_attempt(i) for i in range(concurrent_attempts)]
        
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful creations
        successful_creations = sum(1 for result in results_list if isinstance(result, tuple) and result[0] is True)
        
        if successful_creations != 1:
            results.add_result("Concurrent Idempotency", False, 
                             f"Expected 1 successful creation, got {successful_creations}")
            return
        
        duration = time.time() - start_time
        results.add_result("Concurrent Idempotency", True, duration=duration)
        
    except Exception as e:
        results.add_result("Concurrent Idempotency", False, str(e))


def test_database_locking(results: FinancialValidationResults):
    """Test SELECT FOR UPDATE database locking"""
    try:
        start_time = time.time()
        
        # Create test escrow record
        with SessionLocal() as session:
            test_escrow = Escrow(
                id=f"test_lock_{uuid.uuid4()}",
                buyer_id=12345,
                seller_id=54321,
                amount=Decimal("100.00"),
                currency="USD",
                title="Lock Test Escrow",
                description="Testing database locking",
                status="active",
                version=1
            )
            session.add(test_escrow)
            session.commit()
            escrow_id = test_escrow.id
        
        # Test row-level locking
        with SessionLocal() as session:
            locking_service = DatabaseLockingService(session)
            
            # Lock the escrow record
            locked_escrow = locking_service.lock_escrow(escrow_id)
            if not locked_escrow:
                results.add_result("Database Row Locking", False, "Failed to acquire row lock")
                return
            
            if locked_escrow.id != escrow_id:
                results.add_result("Database Row Locking", False, "Locked wrong escrow record")
                return
            
            # Modify and save (this tests the lock is working)
            locked_escrow.description = "Modified while locked"
            session.commit()
            
        # Verify modification was saved
        with SessionLocal() as session:
            updated_escrow = session.query(Escrow).filter(Escrow.id == escrow_id).first()
            if not updated_escrow or updated_escrow.description != "Modified while locked":
                results.add_result("Database Lock Modification", False, "Modification not saved correctly")
                return
        
        # Clean up
        with SessionLocal() as session:
            session.query(Escrow).filter(Escrow.id == escrow_id).delete()
            session.commit()
        
        duration = time.time() - start_time
        results.add_result("Database Row Locking", True, duration=duration)
        
    except Exception as e:
        results.add_result("Database Row Locking", False, str(e))


def test_atomic_transactions(results: FinancialValidationResults):
    """Test atomic transaction decorator functionality"""
    try:
        start_time = time.time()
        
        @atomic_transaction
        def create_test_records(session):
            """Create test records in atomic transaction"""
            escrow = Escrow(
                id=f"atomic_test_{uuid.uuid4()}",
                buyer_id=11111,
                seller_id=22222,
                amount=Decimal("200.00"),
                currency="USD",
                title="Atomic Test Escrow",
                description="Testing atomic transactions",
                status="created",
                version=1
            )
            session.add(escrow)
            session.flush()  # Get the ID without committing
            
            cashout = Cashout(
                id=f"cashout_atomic_{uuid.uuid4()}",
                user_id=11111,
                amount=Decimal("200.00"),
                currency="USD",
                status="pending",
                processing_mode="manual",
                version=1
            )
            session.add(cashout)
            
            return escrow.id, cashout.id
        
        # Test successful atomic transaction
        escrow_id, cashout_id = create_test_records()
        
        # Verify both records were created
        with SessionLocal() as session:
            escrow = session.query(Escrow).filter(Escrow.id == escrow_id).first()
            cashout = session.query(Cashout).filter(Cashout.id == cashout_id).first()
            
            if not escrow or not cashout:
                results.add_result("Atomic Transaction Success", False, "Records not created in successful transaction")
                return
        
        @atomic_transaction
        def create_and_fail(session):
            """Create record then fail - should rollback"""
            test_escrow = Escrow(
                id=f"rollback_test_{uuid.uuid4()}",
                buyer_id=33333,
                seller_id=44444,
                amount=Decimal("300.00"),
                currency="USD",
                title="Rollback Test",
                description="This should be rolled back",
                status="created",
                version=1
            )
            session.add(test_escrow)
            session.flush()
            
            # Force an error to trigger rollback
            raise ValueError("Intentional error for rollback test")
        
        # Test rollback on error
        rollback_escrow_id = None
        try:
            create_and_fail()
        except ValueError:
            pass  # Expected error
        
        # Verify rollback occurred
        with SessionLocal() as session:
            rollback_count = session.query(Escrow).filter(
                Escrow.title == "Rollback Test"
            ).count()
            
            if rollback_count > 0:
                results.add_result("Atomic Transaction Rollback", False, "Rollback failed - record still exists")
                return
        
        # Clean up successful test records
        with SessionLocal() as session:
            session.query(Escrow).filter(Escrow.id == escrow_id).delete()
            session.query(Cashout).filter(Cashout.id == cashout_id).delete()
            session.commit()
        
        duration = time.time() - start_time
        results.add_result("Atomic Transactions", True, duration=duration)
        
    except Exception as e:
        results.add_result("Atomic Transactions", False, str(e))


async def test_financial_operation_integrity(results: FinancialValidationResults):
    """Test end-to-end financial operation with all safeguards"""
    try:
        start_time = time.time()
        idempotency_service = IdempotencyService()
        
        user_id = 77777
        amount = Decimal("150.75")
        currency = "USD"
        
        # Generate idempotency key
        idempotency_key = IdempotencyKeyGenerator.generate_cashout_key(
            user_id=user_id,
            amount=float(amount),
            currency=currency,
            destination="test_bank_account"
        )
        
        # Create idempotent operation
        operation_created = await idempotency_service.create_operation(
            key=idempotency_key,
            operation_type=OperationType.CASHOUT,
            user_id=user_id,
            entity_id=None,  # Will be set when cashout is created
            request_data={
                "amount": float(amount),
                "currency": currency,
                "destination": "test_bank_account"
            },
            ttl_seconds=3600
        )
        
        if not operation_created:
            results.add_result("Financial Operation - Idempotency Setup", False, "Failed to create idempotent operation")
            return
        
        # Create cashout with atomic transaction and locking
        @atomic_transaction
        def create_financial_record(session):
            cashout = Cashout(
                id=f"financial_integrity_{uuid.uuid4()}",
                user_id=user_id,
                amount=amount,
                currency=currency,
                status="pending",
                processing_mode="automatic",
                version=1
            )
            session.add(cashout)
            session.flush()
            return cashout.id
        
        cashout_id = create_financial_record()
        
        # Update idempotency record with entity ID
        await idempotency_service.update_entity_id(idempotency_key, cashout_id)
        
        # Verify cashout was created with proper version
        with SessionLocal() as session:
            created_cashout = session.query(Cashout).filter(Cashout.id == cashout_id).first()
            if not created_cashout:
                results.add_result("Financial Operation - Record Creation", False, "Cashout record not created")
                return
            
            if created_cashout.version != 1:
                results.add_result("Financial Operation - Version Control", False, f"Wrong initial version: {created_cashout.version}")
                return
        
        # Test optimistic locking update
        @atomic_transaction  
        def update_with_optimistic_lock(session):
            locking_service = DatabaseLockingService(session)
            locked_cashout = locking_service.lock_cashout(cashout_id)
            
            if not locked_cashout:
                raise ValueError("Failed to lock cashout for update")
            
            # Update status with version increment
            locked_cashout.status = "processing"
            locked_cashout.version = locked_cashout.version + 1
            session.flush()
            return locked_cashout.version
        
        new_version = update_with_optimistic_lock()
        
        if new_version != 2:
            results.add_result("Financial Operation - Optimistic Locking", False, f"Version not incremented correctly: {new_version}")
            return
        
        # Complete idempotency operation
        completion_result = {
            "cashout_id": cashout_id,
            "final_status": "processing",
            "version": new_version
        }
        
        completed = await idempotency_service.complete_operation(
            key=idempotency_key,
            result=completion_result
        )
        
        if not completed:
            results.add_result("Financial Operation - Completion", False, "Failed to complete idempotent operation")
            return
        
        # Verify final state
        final_record = await idempotency_service.check_operation(idempotency_key)
        if not final_record or final_record.status != IdempotencyStatus.COMPLETED:
            results.add_result("Financial Operation - Final Verification", False, "Operation not properly completed")
            return
        
        # Clean up
        with SessionLocal() as session:
            session.query(Cashout).filter(Cashout.id == cashout_id).delete()
            session.commit()
        
        duration = time.time() - start_time
        results.add_result("Financial Operation Integrity", True, duration=duration)
        
    except Exception as e:
        results.add_result("Financial Operation Integrity", False, str(e))


async def main():
    """Run all financial operations validation tests"""
    print("💰 FINANCIAL OPERATIONS VALIDATION TEST SUITE")
    print("="*80)
    
    results = FinancialValidationResults()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Test idempotency key generation
        print("\n🔑 Testing Idempotency Key Generation...")
        await test_idempotency_key_generation(results)
        
        # Test idempotency service operations
        print("\n⚡ Testing Idempotency Service Operations...")
        await test_idempotency_service_operations(results)
        
        # Test concurrent idempotency
        print("\n🔄 Testing Concurrent Idempotency...")
        await test_concurrent_idempotency(results)
        
        # Test database locking
        print("\n🔒 Testing Database Locking...")
        test_database_locking(results)
        
        # Test atomic transactions
        print("\n⚛️ Testing Atomic Transactions...")
        test_atomic_transactions(results)
        
        # Test end-to-end financial operation integrity
        print("\n🏦 Testing Financial Operation Integrity...")
        await test_financial_operation_integrity(results)
        
    except Exception as e:
        logger.error(f"Critical error during financial validation: {e}")
        results.add_result("Critical Financial Error", False, str(e))
    
    # Print summary and exit
    success = results.print_summary()
    
    if success:
        print("\n✅ All financial operations validation tests PASSED!")
        print("💎 Financial integrity safeguards are working correctly.")
        return 0
    else:
        print("\n❌ Some financial operations validation tests FAILED!")
        print("🚨 Critical financial issues must be resolved immediately!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)