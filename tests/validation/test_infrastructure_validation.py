#!/usr/bin/env python3
"""
Infrastructure Validation Test Suite
Validates Redis connectivity, state manager functionality, and optimistic locking operations
"""

import asyncio
import logging
import sys
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path
sys.path.insert(0, '/home/runner/workspace')

from services.state_manager import state_manager
from utils.optimistic_locking import OptimisticLockManager, VersionMixin, OptimisticLockingError
from database import SessionLocal, engine
from models import Base, Escrow, Cashout, UnifiedTransaction
from config import Config

logger = logging.getLogger(__name__)


class InfrastructureValidationResults:
    """Track validation test results"""
    
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.errors = []
        
    def add_result(self, test_name: str, passed: bool, error: Optional[str] = None):
        """Add test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            logger.info(f"✅ {test_name} - PASSED")
        else:
            self.failed_tests += 1
            logger.error(f"❌ {test_name} - FAILED: {error}")
            self.errors.append(f"{test_name}: {error}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("INFRASTRUCTURE VALIDATION SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%" if self.total_tests > 0 else "0.0%")
        
        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  • {error}")
        
        return self.failed_tests == 0


async def test_redis_connectivity(results: InfrastructureValidationResults):
    """Test basic Redis connectivity and operations"""
    try:
        # Test basic connection
        await state_manager.ensure_connection()
        results.add_result("Redis Basic Connection", True)
        
        # Test basic set/get operations
        test_key = f"test:connectivity:{uuid.uuid4()}"
        test_value = {"timestamp": datetime.utcnow().isoformat(), "data": "test"}
        
        success = await state_manager.set_state(
            test_key, test_value, ttl=60, tags=['test'], source='validation'
        )
        if not success:
            results.add_result("Redis Set Operation", False, "Failed to set test key")
            return
        
        retrieved = await state_manager.get_state(test_key)
        if retrieved != test_value:
            results.add_result("Redis Get Operation", False, f"Retrieved value mismatch: {retrieved} != {test_value}")
            return
        
        results.add_result("Redis Set/Get Operations", True)
        
        # Test key deletion
        deleted = await state_manager.delete_state(test_key)
        if not deleted:
            results.add_result("Redis Delete Operation", False, "Failed to delete test key")
            return
        
        # Verify deletion
        after_delete = await state_manager.get_state(test_key)
        if after_delete is not None:
            results.add_result("Redis Delete Verification", False, "Key still exists after deletion")
            return
        
        results.add_result("Redis Delete Operation", True)
        
    except Exception as e:
        results.add_result("Redis Connectivity", False, str(e))


async def test_distributed_locking(results: InfrastructureValidationResults):
    """Test distributed locking functionality"""
    try:
        # Test lock acquisition and release
        lock_name = f"test_lock_{uuid.uuid4()}"
        
        async with state_manager.get_distributed_lock(lock_name, timeout=30) as lock_acquired:
            if not lock_acquired:
                results.add_result("Distributed Lock Acquisition", False, "Failed to acquire lock")
                return
            
            results.add_result("Distributed Lock Acquisition", True)
            
            # Test that the same lock cannot be acquired again
            async with state_manager.get_distributed_lock(lock_name, timeout=1, blocking_timeout=1) as second_lock:
                if second_lock:
                    results.add_result("Distributed Lock Exclusivity", False, "Second lock was acquired when it shouldn't have been")
                    return
                    
        results.add_result("Distributed Lock Exclusivity", True)
        
        # Test lock is properly released
        async with state_manager.get_distributed_lock(lock_name, timeout=30) as released_lock:
            if not released_lock:
                results.add_result("Distributed Lock Release", False, "Lock was not properly released")
                return
                
        results.add_result("Distributed Lock Release", True)
        
    except Exception as e:
        results.add_result("Distributed Locking", False, str(e))


async def test_state_manager_operations(results: InfrastructureValidationResults):
    """Test comprehensive state manager operations"""
    try:
        # Test different data types
        test_data = {
            "string_key": "test_string",
            "dict_key": {"nested": {"value": 123, "timestamp": datetime.utcnow().isoformat()}},
            "list_key": [1, 2, 3, "four", {"five": 5}],
            "number_key": 42.5
        }
        
        for key, value in test_data.items():
            full_key = f"validation:{key}:{uuid.uuid4()}"
            
            # Test set with TTL and tags
            success = await state_manager.set_state(
                full_key, value, ttl=300, 
                tags=['validation', 'data_type_test'], 
                source='validation_suite'
            )
            
            if not success:
                results.add_result(f"State Manager Set ({key})", False, "Failed to set state")
                continue
            
            # Test get
            retrieved = await state_manager.get_state(full_key)
            if retrieved != value:
                results.add_result(f"State Manager Get ({key})", False, f"Value mismatch: {retrieved} != {value}")
                continue
                
            results.add_result(f"State Manager Operations ({key})", True)
            
            # Clean up
            await state_manager.delete_state(full_key)
        
        # Test TTL functionality
        ttl_key = f"validation:ttl:{uuid.uuid4()}"
        await state_manager.set_state(ttl_key, "ttl_test", ttl=1, tags=['ttl_test'], source='validation')
        
        # Verify key exists
        value = await state_manager.get_state(ttl_key)
        if value != "ttl_test":
            results.add_result("State Manager TTL Setup", False, "TTL key not set properly")
            return
            
        # Wait for TTL expiration
        await asyncio.sleep(2)
        
        # Verify key expired
        expired_value = await state_manager.get_state(ttl_key)
        if expired_value is not None:
            results.add_result("State Manager TTL Expiration", False, "Key did not expire as expected")
            return
            
        results.add_result("State Manager TTL Functionality", True)
        
    except Exception as e:
        results.add_result("State Manager Operations", False, str(e))


def test_database_connectivity(results: InfrastructureValidationResults):
    """Test database connectivity and basic operations"""
    try:
        # Test database connection
        with SessionLocal() as session:
            # Test basic query
            result = session.execute("SELECT 1 as test").fetchone()
            if result[0] != 1:
                results.add_result("Database Basic Query", False, "Test query returned unexpected result")
                return
                
        results.add_result("Database Connectivity", True)
        
        # Test table existence for key models
        with SessionLocal() as session:
            tables_to_check = ['escrows', 'cashouts', 'unified_transactions', 'wallets']
            
            for table_name in tables_to_check:
                result = session.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                    (table_name,)
                ).fetchone()
                
                if not result[0]:
                    results.add_result(f"Database Table ({table_name})", False, f"Table {table_name} does not exist")
                    continue
                    
                results.add_result(f"Database Table ({table_name})", True)
        
    except Exception as e:
        results.add_result("Database Connectivity", False, str(e))


def test_optimistic_locking_setup(results: InfrastructureValidationResults):
    """Test optimistic locking infrastructure"""
    try:
        # Check if key models have version columns
        with SessionLocal() as session:
            models_to_check = [
                ('escrows', Escrow),
                ('cashouts', Cashout),
                ('unified_transactions', UnifiedTransaction)
            ]
            
            for table_name, model_class in models_to_check:
                # Check if version column exists
                result = session.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = %s AND column_name = 'version')",
                    (table_name,)
                ).fetchone()
                
                if not result[0]:
                    results.add_result(f"Optimistic Locking Column ({table_name})", False, f"Version column missing in {table_name}")
                    continue
                    
                # Check if updated_at column exists
                result = session.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = %s AND column_name = 'updated_at')",
                    (table_name,)
                ).fetchone()
                
                if not result[0]:
                    results.add_result(f"Updated At Column ({table_name})", False, f"updated_at column missing in {table_name}")
                    continue
                    
                results.add_result(f"Optimistic Locking Setup ({table_name})", True)
        
    except Exception as e:
        results.add_result("Optimistic Locking Setup", False, str(e))


async def test_performance_metrics(results: InfrastructureValidationResults):
    """Test performance metrics and resource usage"""
    try:
        # Test Redis performance
        start_time = time.time()
        operations = 100
        
        for i in range(operations):
            key = f"perf:test:{i}"
            await state_manager.set_state(key, {"iteration": i}, ttl=60)
            value = await state_manager.get_state(key)
            if value is None:
                results.add_result("Redis Performance Test", False, f"Failed to retrieve key {key}")
                return
            await state_manager.delete_state(key)
        
        duration = time.time() - start_time
        ops_per_second = operations * 3 / duration  # 3 operations per iteration (set, get, delete)
        
        if ops_per_second < 100:  # Minimum performance threshold
            results.add_result("Redis Performance", False, f"Performance too low: {ops_per_second:.1f} ops/sec")
            return
            
        results.add_result("Redis Performance", True)
        logger.info(f"Redis Performance: {ops_per_second:.1f} operations/second")
        
    except Exception as e:
        results.add_result("Performance Metrics", False, str(e))


async def main():
    """Run all infrastructure validation tests"""
    print("🔍 INFRASTRUCTURE VALIDATION TEST SUITE")
    print("="*80)
    
    results = InfrastructureValidationResults()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Test database connectivity first
        print("\n📊 Testing Database Connectivity...")
        test_database_connectivity(results)
        
        # Test Redis connectivity and operations
        print("\n🔗 Testing Redis Connectivity...")
        await test_redis_connectivity(results)
        
        # Test distributed locking
        print("\n🔒 Testing Distributed Locking...")
        await test_distributed_locking(results)
        
        # Test state manager operations
        print("\n📋 Testing State Manager Operations...")
        await test_state_manager_operations(results)
        
        # Test optimistic locking setup
        print("\n🔄 Testing Optimistic Locking Setup...")
        test_optimistic_locking_setup(results)
        
        # Test performance metrics
        print("\n⚡ Testing Performance Metrics...")
        await test_performance_metrics(results)
        
    except Exception as e:
        logger.error(f"Critical error during validation: {e}")
        results.add_result("Critical Infrastructure Error", False, str(e))
    
    # Print summary and exit
    success = results.print_summary()
    
    if success:
        print("\n✅ All infrastructure validation tests PASSED!")
        print("🚀 Infrastructure is ready for production use.")
        return 0
    else:
        print("\n❌ Some infrastructure validation tests FAILED!")
        print("⚠️ Issues must be resolved before production deployment.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)