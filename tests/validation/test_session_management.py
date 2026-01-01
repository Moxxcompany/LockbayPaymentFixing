#!/usr/bin/env python3
"""
Session Management Validation Test Suite
Validate Redis-backed session storage and migration compatibility
"""

import asyncio
import logging
import sys
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, '/home/runner/workspace')

from utils.redis_session_foundation import (
    RedisSessionManager, SessionState
)
from services.state_manager import state_manager
from config import Config

logger = logging.getLogger(__name__)


class SessionValidationResults:
    """Track session validation test results"""
    
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
        print("SESSION MANAGEMENT VALIDATION SUMMARY")
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


async def test_session_creation_and_retrieval(results: SessionValidationResults):
    """Test basic session creation and retrieval"""
    try:
        session_manager = RedisSessionManager()
        start_time = time.time()
        
        user_id = 12345
        conversation_flow = "escrow_creation"
        initial_data = {
            "step": "amount_input",
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Create session
        session_id = await session_manager.create_session(
            user_id=user_id,
            conversation_flow=conversation_flow,
            initial_data=initial_data,
            ttl_seconds=1800
        )
        
        if not session_id or not session_id.startswith(f"sess_{user_id}"):
            results.add_result("Session Creation", False, f"Invalid session ID: {session_id}")
            return
        
        # Retrieve session
        retrieved_session = await session_manager.get_session(session_id)
        
        if not retrieved_session:
            results.add_result("Session Retrieval", False, "Failed to retrieve created session")
            return
        
        # Verify session data
        if retrieved_session.user_id != user_id:
            results.add_result("Session User ID", False, f"Wrong user ID: {retrieved_session.user_id}")
            return
        
        if retrieved_session.conversation_flow != conversation_flow:
            results.add_result("Session Conversation Flow", False, f"Wrong flow: {retrieved_session.conversation_flow}")
            return
        
        if retrieved_session.data != initial_data:
            results.add_result("Session Initial Data", False, f"Data mismatch: {retrieved_session.data}")
            return
        
        # Clean up
        await session_manager.delete_session(session_id)
        
        duration = time.time() - start_time
        results.add_result("Session Creation and Retrieval", True, duration=duration)
        
    except Exception as e:
        results.add_result("Session Creation and Retrieval", False, str(e))


async def test_session_updates(results: SessionValidationResults):
    """Test session data updates and step progression"""
    try:
        session_manager = RedisSessionManager()
        start_time = time.time()
        
        user_id = 23456
        initial_data = {"step": "start", "progress": 0}
        
        # Create session
        session_id = await session_manager.create_session(
            user_id=user_id,
            conversation_flow="wallet_management",
            initial_data=initial_data
        )
        
        # Test data updates
        update_steps = [
            {"step": "amount_input", "progress": 25, "amount": "100.50"},
            {"step": "currency_selection", "progress": 50, "amount": "100.50", "currency": "USD"},
            {"step": "confirmation", "progress": 75, "amount": "100.50", "currency": "USD", "confirmed": True},
            {"step": "complete", "progress": 100, "amount": "100.50", "currency": "USD", "confirmed": True, "completed": True}
        ]
        
        for update_data in update_steps:
            success = await session_manager.update_session_data(session_id, update_data)
            if not success:
                results.add_result("Session Data Update", False, f"Failed to update with: {update_data}")
                return
            
            # Verify update
            updated_session = await session_manager.get_session(session_id)
            if not updated_session or updated_session.data != update_data:
                results.add_result("Session Data Verification", False, 
                                 f"Data not updated correctly: {updated_session.data if updated_session else None}")
                return
        
        # Test step progression
        step_progression = ["step1", "step2", "step3", "final_step"]
        for step in step_progression:
            success = await session_manager.update_current_step(session_id, step)
            if not success:
                results.add_result("Session Step Update", False, f"Failed to update step to: {step}")
                return
            
            # Verify step update
            session = await session_manager.get_session(session_id)
            if not session or session.current_step != step:
                results.add_result("Session Step Verification", False, 
                                 f"Step not updated: expected {step}, got {session.current_step if session else None}")
                return
        
        # Clean up
        await session_manager.delete_session(session_id)
        
        duration = time.time() - start_time
        results.add_result("Session Updates", True, duration=duration)
        
    except Exception as e:
        results.add_result("Session Updates", False, str(e))


async def test_session_ttl_and_expiration(results: SessionValidationResults):
    """Test session TTL and automatic expiration"""
    try:
        session_manager = RedisSessionManager()
        start_time = time.time()
        
        user_id = 34567
        short_ttl = 2  # 2 seconds for quick testing
        
        # Create session with short TTL
        session_id = await session_manager.create_session(
            user_id=user_id,
            conversation_flow="ttl_test",
            initial_data={"test": "ttl_expiration"},
            ttl_seconds=short_ttl
        )
        
        # Verify session exists
        session = await session_manager.get_session(session_id)
        if not session:
            results.add_result("Session TTL Setup", False, "Session not created with TTL")
            return
        
        # Wait for TTL to expire
        await asyncio.sleep(short_ttl + 1)
        
        # Verify session expired
        expired_session = await session_manager.get_session(session_id)
        if expired_session is not None:
            results.add_result("Session TTL Expiration", False, "Session did not expire as expected")
            return
        
        # Test TTL extension
        user_id2 = 34568
        session_id2 = await session_manager.create_session(
            user_id=user_id2,
            conversation_flow="ttl_extension_test",
            initial_data={"test": "ttl_extension"},
            ttl_seconds=short_ttl
        )
        
        # Extend TTL before expiration
        await asyncio.sleep(1)  # Wait 1 second
        extended = await session_manager.extend_session_ttl(session_id2, short_ttl + 3)
        
        if not extended:
            results.add_result("Session TTL Extension", False, "Failed to extend session TTL")
            return
        
        # Wait original TTL time and verify session still exists
        await asyncio.sleep(short_ttl)
        extended_session = await session_manager.get_session(session_id2)
        
        if not extended_session:
            results.add_result("Session TTL Extension Verification", False, "Session expired despite TTL extension")
            return
        
        # Clean up
        await session_manager.delete_session(session_id2)
        
        duration = time.time() - start_time
        results.add_result("Session TTL and Expiration", True, duration=duration)
        
    except Exception as e:
        results.add_result("Session TTL and Expiration", False, str(e))


async def test_conversation_state_management(results: SessionValidationResults):
    """Test conversation state and temporary state management"""
    try:
        session_manager = RedisSessionManager()
        start_time = time.time()
        
        user_id = 45678
        
        # Test conversation state
        conversation_data = {
            "flow": "escrow_creation",
            "current_step": "amount_input",
            "collected_data": {
                "title": "Test Escrow",
                "description": "Testing conversation state"
            }
        }
        
        # Set conversation state
        success = await session_manager.set_conversation_state(
            user_id, "escrow_creation", conversation_data
        )
        
        if not success:
            results.add_result("Conversation State Setting", False, "Failed to set conversation state")
            return
        
        # Get conversation state
        retrieved_state = await session_manager.get_conversation_state(user_id, "escrow_creation")
        
        if not retrieved_state or retrieved_state != conversation_data:
            results.add_result("Conversation State Retrieval", False, 
                             f"State mismatch: {retrieved_state}")
            return
        
        # Test temporary state
        temp_key = "payment_verification"
        temp_data = {
            "payment_id": "temp_123",
            "amount": 100.50,
            "verification_code": "ABC123"
        }
        
        success = await session_manager.set_temporary_state(
            user_id, temp_key, temp_data, ttl_seconds=300
        )
        
        if not success:
            results.add_result("Temporary State Setting", False, "Failed to set temporary state")
            return
        
        # Get temporary state
        retrieved_temp = await session_manager.get_temporary_state(user_id, temp_key)
        
        if not retrieved_temp or retrieved_temp != temp_data:
            results.add_result("Temporary State Retrieval", False, 
                             f"Temp state mismatch: {retrieved_temp}")
            return
        
        # Clean up conversation state
        await session_manager.clear_conversation_state(user_id, "escrow_creation")
        
        # Verify cleanup
        cleared_state = await session_manager.get_conversation_state(user_id, "escrow_creation")
        if cleared_state is not None:
            results.add_result("Conversation State Cleanup", False, "State not cleared properly")
            return
        
        duration = time.time() - start_time
        results.add_result("Conversation State Management", True, duration=duration)
        
    except Exception as e:
        results.add_result("Conversation State Management", False, str(e))


async def test_multi_user_session_isolation(results: SessionValidationResults):
    """Test session isolation between multiple users"""
    try:
        session_manager = RedisSessionManager()
        start_time = time.time()
        
        # Create sessions for multiple users
        users = [
            {"id": 11111, "flow": "escrow_creation", "data": {"type": "buyer", "amount": 100}},
            {"id": 22222, "flow": "wallet_management", "data": {"type": "cashout", "amount": 200}},
            {"id": 33333, "flow": "exchange", "data": {"type": "exchange", "from": "USD", "to": "NGN"}}
        ]
        
        session_ids = {}
        
        # Create all sessions
        for user in users:
            session_id = await session_manager.create_session(
                user_id=user["id"],
                conversation_flow=user["flow"],
                initial_data=user["data"]
            )
            session_ids[user["id"]] = session_id
        
        # Verify each user can only access their own session
        for user in users:
            user_session = await session_manager.get_session(session_ids[user["id"]])
            
            if not user_session:
                results.add_result("Multi-User Session Creation", False, f"Session not found for user {user['id']}")
                return
            
            if user_session.user_id != user["id"]:
                results.add_result("Multi-User Session Isolation", False, 
                                 f"Wrong user ID in session: expected {user['id']}, got {user_session.user_id}")
                return
            
            if user_session.data != user["data"]:
                results.add_result("Multi-User Data Isolation", False, 
                                 f"Wrong data for user {user['id']}: {user_session.data}")
                return
        
        # Test that users can't access other users' sessions
        for user in users:
            for other_user_id, other_session_id in session_ids.items():
                if other_user_id != user["id"]:
                    # This should not be possible through the API, but let's verify the session contains correct user_id
                    other_session = await session_manager.get_session(other_session_id)
                    if other_session and other_session.user_id != other_user_id:
                        results.add_result("Session User ID Consistency", False, 
                                         f"Session {other_session_id} has wrong user_id")
                        return
        
        # Clean up all sessions
        for user_id, session_id in session_ids.items():
            await session_manager.delete_session(session_id)
        
        duration = time.time() - start_time
        results.add_result("Multi-User Session Isolation", True, duration=duration)
        
    except Exception as e:
        results.add_result("Multi-User Session Isolation", False, str(e))


async def test_session_performance(results: SessionValidationResults):
    """Test session performance under load"""
    try:
        session_manager = RedisSessionManager()
        start_time = time.time()
        
        # Test batch session operations
        num_sessions = 50
        user_base = 100000
        
        session_ids = []
        
        # Create multiple sessions rapidly
        for i in range(num_sessions):
            session_id = await session_manager.create_session(
                user_id=user_base + i,
                conversation_flow=f"performance_test_{i % 5}",  # Vary flows
                initial_data={"iteration": i, "test": "performance"}
            )
            session_ids.append(session_id)
        
        # Verify all sessions were created
        if len(session_ids) != num_sessions:
            results.add_result("Session Performance - Creation", False, 
                             f"Only {len(session_ids)} of {num_sessions} sessions created")
            return
        
        # Test rapid retrieval
        retrieval_start = time.time()
        retrieved_count = 0
        
        for session_id in session_ids:
            session = await session_manager.get_session(session_id)
            if session:
                retrieved_count += 1
        
        retrieval_time = time.time() - retrieval_start
        
        if retrieved_count != num_sessions:
            results.add_result("Session Performance - Retrieval", False, 
                             f"Only retrieved {retrieved_count} of {num_sessions} sessions")
            return
        
        # Test rapid updates
        update_start = time.time()
        update_count = 0
        
        for i, session_id in enumerate(session_ids):
            success = await session_manager.update_session_data(
                session_id, {"updated": True, "iteration": i, "timestamp": time.time()}
            )
            if success:
                update_count += 1
        
        update_time = time.time() - update_start
        
        if update_count != num_sessions:
            results.add_result("Session Performance - Updates", False, 
                             f"Only updated {update_count} of {num_sessions} sessions")
            return
        
        # Test rapid deletion
        deletion_start = time.time()
        deletion_count = 0
        
        for session_id in session_ids:
            success = await session_manager.delete_session(session_id)
            if success:
                deletion_count += 1
        
        deletion_time = time.time() - deletion_start
        
        total_time = time.time() - start_time
        
        # Performance thresholds
        max_total_time = 10.0  # 10 seconds for all operations
        min_ops_per_second = 20  # At least 20 operations per second
        
        total_operations = num_sessions * 4  # create, retrieve, update, delete
        ops_per_second = total_operations / total_time
        
        if total_time > max_total_time:
            results.add_result("Session Performance - Time Threshold", False, 
                             f"Operations took {total_time:.2f}s, max allowed {max_total_time}s")
            return
        
        if ops_per_second < min_ops_per_second:
            results.add_result("Session Performance - Throughput", False, 
                             f"Only {ops_per_second:.1f} ops/sec, minimum {min_ops_per_second}")
            return
        
        logger.info(f"Session Performance Metrics:")
        logger.info(f"  Total sessions: {num_sessions}")
        logger.info(f"  Retrieval time: {retrieval_time:.3f}s")
        logger.info(f"  Update time: {update_time:.3f}s") 
        logger.info(f"  Deletion time: {deletion_time:.3f}s")
        logger.info(f"  Operations per second: {ops_per_second:.1f}")
        
        results.add_result("Session Performance", True, duration=total_time)
        
    except Exception as e:
        results.add_result("Session Performance", False, str(e))


async def main():
    """Run all session management validation tests"""
    print("👤 SESSION MANAGEMENT VALIDATION TEST SUITE")
    print("="*80)
    
    results = SessionValidationResults()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Test basic session operations
        print("\n🔧 Testing Session Creation and Retrieval...")
        await test_session_creation_and_retrieval(results)
        
        # Test session updates
        print("\n📝 Testing Session Updates...")
        await test_session_updates(results)
        
        # Test TTL and expiration
        print("\n⏰ Testing Session TTL and Expiration...")
        await test_session_ttl_and_expiration(results)
        
        # Test conversation state management
        print("\n💬 Testing Conversation State Management...")
        await test_conversation_state_management(results)
        
        # Test multi-user isolation
        print("\n👥 Testing Multi-User Session Isolation...")
        await test_multi_user_session_isolation(results)
        
        # Test performance
        print("\n⚡ Testing Session Performance...")
        await test_session_performance(results)
        
    except Exception as e:
        logger.error(f"Critical error during session validation: {e}")
        results.add_result("Critical Session Error", False, str(e))
    
    # Print summary and exit
    success = results.print_summary()
    
    if success:
        print("\n✅ All session management validation tests PASSED!")
        print("🎯 Redis-backed session management is working correctly.")
        return 0
    else:
        print("\n❌ Some session management validation tests FAILED!")
        print("⚠️ Session management issues must be resolved before production.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)