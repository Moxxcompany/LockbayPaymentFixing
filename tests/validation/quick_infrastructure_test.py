#!/usr/bin/env python3
"""
Quick Infrastructure Test for State Management Components
Validates core functionality of Redis, state manager, and database connectivity
"""

import asyncio
import sys
import logging
from datetime import datetime

sys.path.insert(0, '/home/runner/workspace')

from services.state_manager import state_manager
from database import SessionLocal
from sqlalchemy import text
import uuid

logger = logging.getLogger(__name__)


async def test_redis_basic_operations():
    """Test basic Redis connectivity and operations"""
    print("🔗 Testing Redis Basic Operations...")
    
    try:
        # Initialize Redis connection
        initialized = await state_manager.initialize()
        if not initialized:
            print("  ❌ Redis initialization failed")
            return False
        
        print("  ✅ Redis connection established")
        
        # Test basic set/get
        test_key = f"validation_test_{uuid.uuid4()}"
        test_value = {"test": "data", "timestamp": datetime.utcnow().isoformat()}
        
        success = await state_manager.set_state(test_key, test_value, ttl=60)
        if success:
            print("  ✅ State set operation successful")
        else:
            print("  ❌ State set operation failed")
            return False
        
        # Test retrieval
        retrieved = await state_manager.get_state(test_key)
        if retrieved == test_value:
            print("  ✅ State get operation successful")
        else:
            print(f"  ❌ State get operation failed: {retrieved} != {test_value}")
            return False
        
        # Test deletion
        deleted = await state_manager.delete_state(test_key)
        if deleted:
            print("  ✅ State delete operation successful")
        else:
            print("  ❌ State delete operation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Redis operation failed: {e}")
        return False


def test_database_connectivity():
    """Test database connectivity"""
    print("🗄️ Testing Database Connectivity...")
    
    try:
        with SessionLocal() as session:
            result = session.execute(text("SELECT 1 as test")).fetchone()
            if result[0] == 1:
                print("  ✅ Database connection successful")
                return True
            else:
                print("  ❌ Database query returned unexpected result")
                return False
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False


async def test_state_manager_performance():
    """Test state manager performance with multiple operations"""
    print("⚡ Testing State Manager Performance...")
    
    try:
        operations = 20
        keys = []
        
        # Rapid operations test
        for i in range(operations):
            key = f"perf_test_{i}_{uuid.uuid4()}"
            value = {"iteration": i, "data": f"test_data_{i}"}
            
            success = await state_manager.set_state(key, value, ttl=60)
            if success:
                keys.append(key)
        
        print(f"  ✅ Successfully set {len(keys)} states")
        
        # Retrieve all
        retrieved_count = 0
        for key in keys:
            value = await state_manager.get_state(key)
            if value is not None:
                retrieved_count += 1
        
        print(f"  ✅ Successfully retrieved {retrieved_count} states")
        
        # Clean up
        for key in keys:
            await state_manager.delete_state(key)
        
        if len(keys) == operations and retrieved_count == operations:
            print("  ✅ Performance test completed successfully")
            return True
        else:
            print(f"  ❌ Performance test failed: {len(keys)}/{operations} set, {retrieved_count}/{operations} retrieved")
            return False
        
    except Exception as e:
        print(f"  ❌ Performance test failed: {e}")
        return False


async def main():
    """Run quick infrastructure validation"""
    print("🔍 QUICK INFRASTRUCTURE VALIDATION")
    print("="*60)
    
    # Configure logging to reduce noise
    logging.basicConfig(level=logging.WARNING)
    
    tests_passed = 0
    total_tests = 3
    
    # Test database
    if test_database_connectivity():
        tests_passed += 1
    
    # Test Redis operations
    if await test_redis_basic_operations():
        tests_passed += 1
    
    # Test performance
    if await test_state_manager_performance():
        tests_passed += 1
    
    print("\n" + "="*60)
    print(f"VALIDATION SUMMARY: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✅ All infrastructure tests PASSED!")
        print("🚀 Basic state management infrastructure is operational.")
        return 0
    else:
        print("❌ Some infrastructure tests FAILED!")
        print("⚠️ Issues must be resolved before proceeding.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)