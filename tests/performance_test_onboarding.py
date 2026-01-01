#!/usr/bin/env python3
"""
Performance test for onboarding flow optimizations
Tests the actual response times after optimization to verify < 200ms target
"""

import time
import asyncio
import logging
from unittest.mock import Mock, patch
from telegram import Update, User as TelegramUser
from telegram.ext import ContextTypes

from handlers.onboarding_router import start_new_user_onboarding, onboarding_router
from services.onboarding_service import OnboardingService
from services.email_verification_service import EmailVerificationService
from database import managed_session
from models import User

logger = logging.getLogger(__name__)

class PerformanceTestOnboarding:
    """Performance tests for onboarding flow"""
    
    def __init__(self):
        self.test_results = []
    
    async def test_new_user_creation_performance(self):
        """Test new user creation performance"""
        
        # Mock objects
        telegram_user = TelegramUser(
            id=99999999,
            is_bot=False,
            first_name="TestUser",
            username="test_performance_user"
        )
        
        update = Mock(spec=Update)
        update.effective_user = telegram_user
        
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Test multiple runs to get average
        times = []
        
        for i in range(5):
            # Clean up any existing test user
            with managed_session() as session:
                existing = session.query(User).filter(
                    User.telegram_id == str(telegram_user.id)
                ).first()
                if existing:
                    session.delete(existing)
                    session.commit()
            
            # Measure time
            start_time = time.perf_counter()
            
            try:
                await start_new_user_onboarding(update, context)
                end_time = time.perf_counter()
                
                execution_time = (end_time - start_time) * 1000  # Convert to ms
                times.append(execution_time)
                
                logger.info(f"Test run {i+1}: {execution_time:.2f}ms")
                
            except Exception as e:
                logger.error(f"Test run {i+1} failed: {e}")
                times.append(999999)  # Mark as failed
        
        # Clean up test user
        try:
            with managed_session() as session:
                test_user = session.query(User).filter(
                    User.telegram_id == str(telegram_user.id)
                ).first()
                if test_user:
                    session.delete(test_user)
                    session.commit()
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
        
        # Calculate statistics
        valid_times = [t for t in times if t < 999999]
        if not valid_times:
            return {"test": "new_user_creation", "status": "FAILED", "error": "All runs failed"}
        
        avg_time = sum(valid_times) / len(valid_times)
        min_time = min(valid_times)
        max_time = max(valid_times)
        
        status = "PASS" if avg_time < 200 else "FAIL"
        
        result = {
            "test": "new_user_creation",
            "status": status,
            "avg_time_ms": round(avg_time, 2),
            "min_time_ms": round(min_time, 2),
            "max_time_ms": round(max_time, 2),
            "target_ms": 200,
            "successful_runs": len(valid_times),
            "total_runs": len(times)
        }
        
        self.test_results.append(result)
        return result
    
    async def test_onboarding_service_start_performance(self):
        """Test OnboardingService.start() performance"""
        
        # Create a test user first
        with managed_session() as session:
            test_user = User(
                telegram_id="88888888",
                username="perf_test_user",
                first_name="Performance",
                last_name="Test",
                email_verified=False
            )
            session.add(test_user)
            session.commit()
            session.refresh(test_user)
            user_id = test_user.id
        
        times = []
        
        for i in range(5):
            start_time = time.perf_counter()
            
            try:
                result = OnboardingService.start(user_id)
                end_time = time.perf_counter()
                
                execution_time = (end_time - start_time) * 1000
                times.append(execution_time)
                
                logger.info(f"OnboardingService.start() run {i+1}: {execution_time:.2f}ms")
                
            except Exception as e:
                logger.error(f"OnboardingService.start() run {i+1} failed: {e}")
                times.append(999999)
        
        # Clean up test user
        try:
            with managed_session() as session:
                test_user = session.query(User).filter(User.id == user_id).first()
                if test_user:
                    session.delete(test_user)
                    session.commit()
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
        
        valid_times = [t for t in times if t < 999999]
        if not valid_times:
            return {"test": "onboarding_service_start", "status": "FAILED", "error": "All runs failed"}
        
        avg_time = sum(valid_times) / len(valid_times)
        min_time = min(valid_times)
        max_time = max(valid_times)
        
        status = "PASS" if avg_time < 100 else "FAIL"  # Service calls should be faster
        
        result = {
            "test": "onboarding_service_start",
            "status": status,
            "avg_time_ms": round(avg_time, 2),
            "min_time_ms": round(min_time, 2),
            "max_time_ms": round(max_time, 2),
            "target_ms": 100,
            "successful_runs": len(valid_times),
            "total_runs": len(times)
        }
        
        self.test_results.append(result)
        return result
    
    async def test_email_verification_performance(self):
        """Test EmailVerificationService performance"""
        
        # Create test user
        with managed_session() as session:
            test_user = User(
                telegram_id="77777777",
                username="email_test_user",
                first_name="Email",
                last_name="Test",
                email_verified=False
            )
            session.add(test_user)
            session.commit()
            session.refresh(test_user)
            user_id = test_user.id
        
        times = []
        
        for i in range(3):  # Fewer runs to avoid rate limiting
            start_time = time.perf_counter()
            
            try:
                # Test the rate limiting checks (not actual email sending)
                with managed_session() as session:
                    user_within_limit, user_count = EmailVerificationService._check_user_daily_limit(
                        session, user_id
                    )
                    ip_within_limit, ip_count = EmailVerificationService._check_ip_daily_limit(
                        session, "127.0.0.1"
                    )
                
                end_time = time.perf_counter()
                
                execution_time = (end_time - start_time) * 1000
                times.append(execution_time)
                
                logger.info(f"Email verification checks run {i+1}: {execution_time:.2f}ms")
                
            except Exception as e:
                logger.error(f"Email verification run {i+1} failed: {e}")
                times.append(999999)
        
        # Clean up
        try:
            with managed_session() as session:
                test_user = session.query(User).filter(User.id == user_id).first()
                if test_user:
                    session.delete(test_user)
                    session.commit()
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
        
        valid_times = [t for t in times if t < 999999]
        if not valid_times:
            return {"test": "email_verification", "status": "FAILED", "error": "All runs failed"}
        
        avg_time = sum(valid_times) / len(valid_times)
        min_time = min(valid_times)
        max_time = max(valid_times)
        
        status = "PASS" if avg_time < 50 else "FAIL"  # Database checks should be very fast
        
        result = {
            "test": "email_verification_checks",
            "status": status,
            "avg_time_ms": round(avg_time, 2),
            "min_time_ms": round(min_time, 2),
            "max_time_ms": round(max_time, 2),
            "target_ms": 50,
            "successful_runs": len(valid_times),
            "total_runs": len(times)
        }
        
        self.test_results.append(result)
        return result
    
    async def run_all_tests(self):
        """Run all performance tests"""
        
        logger.info("🚀 Starting onboarding performance tests...")
        
        # Test 1: New user creation
        logger.info("📧 Testing new user creation performance...")
        result1 = await self.test_new_user_creation_performance()
        
        # Test 2: OnboardingService.start()
        logger.info("🔧 Testing OnboardingService.start() performance...")
        result2 = await self.test_onboarding_service_start_performance()
        
        # Test 3: Email verification checks
        logger.info("📨 Testing email verification performance...")
        result3 = await self.test_email_verification_performance()
        
        # Summary
        logger.info("📊 Performance Test Results:")
        logger.info("="*50)
        
        all_passed = True
        for result in self.test_results:
            status_emoji = "✅" if result["status"] == "PASS" else "❌"
            logger.info(f"{status_emoji} {result['test']}: {result['avg_time_ms']}ms (target: {result['target_ms']}ms)")
            
            if result["status"] != "PASS":
                all_passed = False
        
        logger.info("="*50)
        overall_status = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
        logger.info(f"Overall Status: {overall_status}")
        
        return {
            "overall_status": "PASS" if all_passed else "FAIL",
            "results": self.test_results
        }

async def main():
    """Run performance tests"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    test_runner = PerformanceTestOnboarding()
    results = await test_runner.run_all_tests()
    
    print("\n🎯 PERFORMANCE OPTIMIZATION RESULTS:")
    print("="*60)
    
    for result in results["results"]:
        status_symbol = "✅" if result["status"] == "PASS" else "❌"
        improvement = ""
        
        if result["avg_time_ms"] < result["target_ms"]:
            improvement = f" (Target achieved! {result['target_ms'] - result['avg_time_ms']:.1f}ms under target)"
        else:
            improvement = f" (Target missed by {result['avg_time_ms'] - result['target_ms']:.1f}ms)"
        
        print(f"{status_symbol} {result['test']}: {result['avg_time_ms']}ms{improvement}")
        print(f"   Range: {result['min_time_ms']}ms - {result['max_time_ms']}ms")
        print(f"   Success rate: {result['successful_runs']}/{result['total_runs']}")
        print()
    
    if results["overall_status"] == "PASS":
        print("🎉 SUCCESS: All performance targets achieved!")
        print("🚀 Onboarding flow optimizations successful - sub-200ms response times confirmed!")
    else:
        print("⚠️ WARNING: Some performance targets not met")
        print("🔧 Additional optimization may be required")

if __name__ == "__main__":
    asyncio.run(main())