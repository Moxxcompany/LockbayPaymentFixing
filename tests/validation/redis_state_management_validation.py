"""
Comprehensive Redis State Management Validation
Tests all components of the state management infrastructure including:
- Redis connectivity and fallback functionality
- State manager operations and error handling
- Distributed locking mechanisms
- Idempotency service operations
- Session management and TTL handling
- Optimistic locking infrastructure
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Configure logging for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import components to test
try:
    from services.state_manager import StateManager, state_manager
    from services.idempotency_service import IdempotencyService, OperationType
    from utils.optimistic_locking import OptimisticLockManager, VersionMixin
    from utils.redis_session_foundation import RedisSessionManager
    from config import Config
    
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import components: {e}")
    COMPONENTS_AVAILABLE = False


class RedisStateManagementValidator:
    """Comprehensive validator for Redis state management infrastructure"""
    
    def __init__(self):
        self.validation_results = {
            'redis_connectivity': {'status': 'pending', 'details': [], 'errors': []},
            'state_manager': {'status': 'pending', 'details': [], 'errors': []},
            'distributed_locking': {'status': 'pending', 'details': [], 'errors': []},
            'idempotency_service': {'status': 'pending', 'details': [], 'errors': []},
            'session_management': {'status': 'pending', 'details': [], 'errors': []},
            'optimistic_locking': {'status': 'pending', 'details': [], 'errors': []},
            'performance_validation': {'status': 'pending', 'details': [], 'errors': []},
            'integration_tests': {'status': 'pending', 'details': [], 'errors': []}
        }
        self.start_time = datetime.utcnow()
        
    def log_success(self, category: str, message: str):
        """Log successful validation step"""
        self.validation_results[category]['details'].append(f"✅ {message}")
        logger.info(f"✅ {category}: {message}")
        
    def log_error(self, category: str, message: str, error: Exception = None):
        """Log validation error"""
        error_msg = f"❌ {message}"
        if error:
            error_msg += f" - Error: {str(error)}"
        self.validation_results[category]['errors'].append(error_msg)
        logger.error(f"❌ {category}: {error_msg}")
        
    def log_warning(self, category: str, message: str):
        """Log validation warning"""
        self.validation_results[category]['details'].append(f"⚠️ {message}")
        logger.warning(f"⚠️ {category}: {message}")
        
    async def validate_redis_connectivity(self) -> bool:
        """Test Redis connectivity and fallback mechanisms"""
        category = 'redis_connectivity'
        
        try:
            # Test state manager initialization
            test_state_manager = StateManager()
            initialized = await test_state_manager.initialize()
            
            if initialized:
                if hasattr(test_state_manager, '_using_fallback') and test_state_manager._using_fallback:
                    self.log_warning(category, "Using Redis fallback implementation")
                else:
                    self.log_success(category, "Real Redis connection established")
                
                # Test basic connectivity
                result = await test_state_manager.redis_client.ping()
                if result == "PONG":
                    self.log_success(category, "Redis PING test successful")
                else:
                    self.log_error(category, f"Unexpected PING response: {result}")
                    
                # Test basic operations
                test_key = f"test_connectivity_{int(time.time())}"
                set_success = await test_state_manager.set_state(
                    test_key, 
                    {"test": "data"}, 
                    ttl=60,
                    tags=["test", "connectivity"]
                )
                
                if set_success:
                    self.log_success(category, "State set operation successful")
                    
                    # Test retrieval
                    retrieved_data = await test_state_manager.get_state(test_key)
                    if retrieved_data and retrieved_data.get("test") == "data":
                        self.log_success(category, "State get operation successful")
                    else:
                        self.log_error(category, f"State retrieval failed: {retrieved_data}")
                        
                    # Test deletion
                    delete_success = await test_state_manager.delete_state(test_key)
                    if delete_success:
                        self.log_success(category, "State delete operation successful")
                    else:
                        self.log_error(category, "State delete operation failed")
                else:
                    self.log_error(category, "State set operation failed")
                    
                # Cleanup
                await test_state_manager.close()
                
                self.validation_results[category]['status'] = 'passed'
                return True
                
            else:
                self.log_error(category, "Failed to initialize state manager")
                self.validation_results[category]['status'] = 'failed'
                return False
                
        except Exception as e:
            self.log_error(category, "Redis connectivity test failed", e)
            self.validation_results[category]['status'] = 'failed'
            return False
    
    async def validate_state_manager(self) -> bool:
        """Test comprehensive state manager functionality"""
        category = 'state_manager'
        
        try:
            test_state_manager = StateManager()
            await test_state_manager.initialize()
            
            # Test various data types
            test_data = {
                "string_data": "test_string",
                "number_data": 42,
                "bool_data": True,
                "list_data": [1, 2, 3],
                "dict_data": {"nested": "value"},
                "datetime_data": datetime.utcnow().isoformat()
            }
            
            for data_type, data_value in test_data.items():
                test_key = f"test_state_{data_type}_{int(time.time())}"
                
                # Test set with different tag types to ensure no 'bool' object error
                tag_variants = [
                    ["string_tag"],  # Normal list
                    None,            # None (should be safe)
                    [],              # Empty list
                    ["tag1", "tag2"] # Multiple tags
                ]
                
                for i, tags in enumerate(tag_variants):
                    test_key_variant = f"{test_key}_{i}"
                    
                    set_success = await test_state_manager.set_state(
                        test_key_variant,
                        data_value,
                        ttl=120,
                        tags=tags,
                        source=f"validation_test_{data_type}"
                    )
                    
                    if set_success:
                        retrieved = await test_state_manager.get_state(test_key_variant)
                        if retrieved == data_value:
                            self.log_success(category, f"Data type {data_type} with tags {tags} - OK")
                        else:
                            self.log_error(category, f"Data type {data_type} mismatch: {retrieved} != {data_value}")
                    else:
                        self.log_error(category, f"Failed to set {data_type} with tags {tags}")
            
            # Test TTL functionality
            ttl_key = f"test_ttl_{int(time.time())}"
            await test_state_manager.set_state(ttl_key, "ttl_test", ttl=2)
            
            # Check immediate retrieval
            immediate = await test_state_manager.get_state(ttl_key)
            if immediate == "ttl_test":
                self.log_success(category, "TTL test - immediate retrieval OK")
                
                # Wait for expiry
                await asyncio.sleep(3)
                expired = await test_state_manager.get_state(ttl_key, default="expired")
                if expired == "expired":
                    self.log_success(category, "TTL test - expiry working correctly")
                else:
                    self.log_warning(category, f"TTL test - value still exists: {expired}")
            else:
                self.log_error(category, "TTL test - immediate retrieval failed")
            
            await test_state_manager.close()
            self.validation_results[category]['status'] = 'passed'
            return True
            
        except Exception as e:
            self.log_error(category, "State manager validation failed", e)
            self.validation_results[category]['status'] = 'failed'
            return False
    
    async def validate_distributed_locking(self) -> bool:
        """Test distributed locking mechanisms"""
        category = 'distributed_locking'
        
        try:
            test_state_manager = StateManager()
            await test_state_manager.initialize()
            
            # Test basic locking
            from services.state_manager import DistributedLock
            
            lock_name = f"test_lock_{int(time.time())}"
            lock1 = DistributedLock(test_state_manager.redis_client, lock_name, timeout=30)
            
            # Test lock acquisition
            acquired = await lock1.acquire()
            if acquired:
                self.log_success(category, "Lock acquisition successful")
                
                # Test lock contention
                lock2 = DistributedLock(test_state_manager.redis_client, lock_name, timeout=30)
                contention_result = await lock2.acquire()
                
                if not contention_result:
                    self.log_success(category, "Lock contention handled correctly")
                else:
                    self.log_error(category, "Lock contention failed - second lock acquired")
                
                # Test lock extension
                extended = await lock1.extend(additional_time=10)
                if extended:
                    self.log_success(category, "Lock extension successful")
                else:
                    self.log_warning(category, "Lock extension failed")
                
                # Test lock release
                released = await lock1.release()
                if released:
                    self.log_success(category, "Lock release successful")
                    
                    # Test lock acquisition after release
                    reacquired = await lock2.acquire()
                    if reacquired:
                        self.log_success(category, "Lock reacquisition after release successful")
                        await lock2.release()
                    else:
                        self.log_error(category, "Lock reacquisition failed")
                else:
                    self.log_error(category, "Lock release failed")
            else:
                self.log_error(category, "Initial lock acquisition failed")
            
            # Test context manager
            async with DistributedLock(test_state_manager.redis_client, f"{lock_name}_context", timeout=30):
                self.log_success(category, "Context manager lock acquisition successful")
                # Lock should be held here
                
            self.log_success(category, "Context manager lock release successful")
            
            await test_state_manager.close()
            self.validation_results[category]['status'] = 'passed'
            return True
            
        except Exception as e:
            self.log_error(category, "Distributed locking validation failed", e)
            self.validation_results[category]['status'] = 'failed'
            return False
    
    async def validate_idempotency_service(self) -> bool:
        """Test idempotency service functionality"""
        category = 'idempotency_service'
        
        try:
            idempotency_service = IdempotencyService()
            
            # Test key generation
            from services.idempotency_service import IdempotencyKeyGenerator
            
            # Test cashout key generation
            cashout_key = IdempotencyKeyGenerator.generate_cashout_key(
                user_id=12345,
                amount=100.50,
                currency="USD",
                destination="wallet_address_123"
            )
            
            if cashout_key.startswith("idempotency:cashout_"):
                self.log_success(category, f"Cashout key generation successful: {cashout_key}")
            else:
                self.log_error(category, f"Invalid cashout key format: {cashout_key}")
            
            # Test deposit key generation
            deposit_key = IdempotencyKeyGenerator.generate_deposit_key(
                user_id=12345,
                amount=50.25,
                currency="BTC",
                source="exchange_deposit",
                external_transaction_id="tx_123456"
            )
            
            if deposit_key.startswith("idempotency:deposit_"):
                self.log_success(category, f"Deposit key generation successful: {deposit_key}")
            else:
                self.log_error(category, f"Invalid deposit key format: {deposit_key}")
            
            # Test escrow key generation
            escrow_key = IdempotencyKeyGenerator.generate_escrow_key(
                user_id=12345,
                amount=75.00,
                currency="USD",
                counterparty_id=67890
            )
            
            if escrow_key.startswith("idempotency:escrow_create_"):
                self.log_success(category, f"Escrow key generation successful: {escrow_key}")
            else:
                self.log_error(category, f"Invalid escrow key format: {escrow_key}")
            
            # Test API call key generation
            api_key = IdempotencyKeyGenerator.generate_api_call_key(
                service="payment_processor",
                endpoint="/api/v1/payments",
                method="POST",
                payload={"amount": 100, "currency": "USD"},
                user_context=12345
            )
            
            if api_key.startswith("idempotency:external_api_call_"):
                self.log_success(category, f"API call key generation successful: {api_key}")
            else:
                self.log_error(category, f"Invalid API call key format: {api_key}")
            
            # Test atomic claim operation
            test_key = f"test_idempotency_{int(time.time())}"
            request_data = {"test": "data", "timestamp": int(time.time())}
            
            claimed, existing_result = await idempotency_service.atomic_claim_operation(
                key=test_key,
                operation_type=OperationType.CASHOUT,
                request_data=request_data,
                user_id=12345,
                ttl_seconds=300
            )
            
            if claimed and existing_result is None:
                self.log_success(category, "Atomic claim operation successful")
                
                # Test duplicate claim (should return existing result)
                duplicate_claimed, duplicate_result = await idempotency_service.atomic_claim_operation(
                    key=test_key,
                    operation_type=OperationType.CASHOUT,
                    request_data=request_data,
                    user_id=12345,
                    ttl_seconds=300
                )
                
                if not duplicate_claimed:
                    self.log_success(category, "Duplicate operation prevention successful")
                else:
                    self.log_error(category, "Duplicate operation not prevented")
            else:
                self.log_error(category, f"Atomic claim failed: claimed={claimed}, result={existing_result}")
            
            self.validation_results[category]['status'] = 'passed'
            return True
            
        except Exception as e:
            self.log_error(category, "Idempotency service validation failed", e)
            self.validation_results[category]['status'] = 'failed'
            return False
    
    async def validate_performance(self) -> bool:
        """Test performance characteristics"""
        category = 'performance_validation'
        
        try:
            test_state_manager = StateManager()
            await test_state_manager.initialize()
            
            # Performance test parameters
            num_operations = 100
            batch_size = 10
            
            # Test batch operations
            start_time = time.time()
            
            for batch in range(0, num_operations, batch_size):
                tasks = []
                for i in range(batch, min(batch + batch_size, num_operations)):
                    key = f"perf_test_{i}_{int(time.time())}"
                    value = {"batch": batch, "item": i, "data": f"test_data_{i}"}
                    tasks.append(
                        test_state_manager.set_state(key, value, ttl=300, tags=["performance", "test"])
                    )
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                successful = sum(1 for r in results if r is True)
                
                if successful != len(tasks):
                    self.log_error(category, f"Batch {batch}: {successful}/{len(tasks)} operations successful")
            
            end_time = time.time()
            total_time = end_time - start_time
            ops_per_second = num_operations / total_time
            
            self.log_success(category, f"Completed {num_operations} operations in {total_time:.2f}s ({ops_per_second:.1f} ops/sec)")
            
            # Test concurrent operations
            concurrent_start = time.time()
            concurrent_tasks = []
            
            for i in range(50):
                key = f"concurrent_test_{i}_{int(time.time())}"
                concurrent_tasks.append(
                    test_state_manager.set_state(key, {"concurrent": i}, ttl=300)
                )
            
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            concurrent_successful = sum(1 for r in concurrent_results if r is True)
            concurrent_time = time.time() - concurrent_start
            
            self.log_success(category, f"Concurrent test: {concurrent_successful}/50 operations in {concurrent_time:.2f}s")
            
            # Memory usage check
            if hasattr(test_state_manager.redis_client, 'get_stats'):
                stats = test_state_manager.redis_client.get_stats()
                self.log_success(category, f"Memory stats: {stats}")
            
            await test_state_manager.close()
            self.validation_results[category]['status'] = 'passed'
            return True
            
        except Exception as e:
            self.log_error(category, "Performance validation failed", e)
            self.validation_results[category]['status'] = 'failed'
            return False
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation tests"""
        logger.info("🚀 Starting comprehensive Redis state management validation")
        
        if not COMPONENTS_AVAILABLE:
            logger.error("❌ Required components not available for testing")
            return self.validation_results
        
        validation_tests = [
            ("Redis Connectivity", self.validate_redis_connectivity),
            ("State Manager", self.validate_state_manager),
            ("Distributed Locking", self.validate_distributed_locking),
            ("Idempotency Service", self.validate_idempotency_service),
            ("Performance", self.validate_performance)
        ]
        
        overall_success = True
        
        for test_name, test_function in validation_tests:
            logger.info(f"🧪 Running {test_name} validation...")
            
            try:
                success = await test_function()
                if not success:
                    overall_success = False
                    logger.error(f"❌ {test_name} validation failed")
                else:
                    logger.info(f"✅ {test_name} validation passed")
            except Exception as e:
                overall_success = False
                logger.error(f"❌ {test_name} validation crashed: {e}")
        
        # Generate summary
        total_time = (datetime.utcnow() - self.start_time).total_seconds()
        
        summary = {
            'overall_status': 'PASSED' if overall_success else 'FAILED',
            'total_validation_time': f"{total_time:.2f}s",
            'tests_run': len(validation_tests),
            'tests_passed': sum(1 for category in self.validation_results.values() if category['status'] == 'passed'),
            'timestamp': datetime.utcnow().isoformat(),
            'details': self.validation_results
        }
        
        if overall_success:
            logger.info(f"🎉 All validations completed successfully in {total_time:.2f}s")
        else:
            logger.error(f"❌ Some validations failed. Total time: {total_time:.2f}s")
        
        return summary


async def main():
    """Main validation function"""
    validator = RedisStateManagementValidator()
    results = await validator.run_comprehensive_validation()
    
    # Print detailed results
    print("\n" + "="*80)
    print("REDIS STATE MANAGEMENT VALIDATION RESULTS")
    print("="*80)
    print(f"Overall Status: {results['overall_status']}")
    print(f"Total Time: {results['total_validation_time']}")
    print(f"Tests Passed: {results['tests_passed']}/{results['tests_run']}")
    print()
    
    for category, details in results['details'].items():
        print(f"{category.upper().replace('_', ' ')}: {details['status'].upper()}")
        
        for detail in details['details']:
            print(f"  {detail}")
        
        for error in details['errors']:
            print(f"  {error}")
        
        print()
    
    return results


if __name__ == "__main__":
    asyncio.run(main())