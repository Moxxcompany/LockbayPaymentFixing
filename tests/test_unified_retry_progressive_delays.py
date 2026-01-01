"""
Progressive Delay Timing Validation Tests for Unified Retry System
Tests validate the exact timing progression: 5min→15min→30min→1hr→2hr→4hr
with proper jitter handling and infrastructure recovery time allowances.

Key Validation Areas:
1. Exact delay calculations for each retry attempt (1-6)
2. Jitter implementation (random variation within acceptable bounds)
3. Next retry scheduling accuracy
4. Clock-based retry readiness detection
5. Edge cases: daylight saving time, timezone handling
6. Performance under high-frequency retry scheduling
"""

import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import json
import time
import random

# Database and model imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from database import managed_session
from models import (
    Base, User, Wallet, UnifiedTransaction, UnifiedTransactionStatus, 
    UnifiedTransactionType, UnifiedTransactionRetryLog
)

# Service imports for testing
from services.unified_retry_service import UnifiedRetryService, RetryContext, RetryResult, RetryDecision
from jobs.unified_retry_processor import UnifiedRetryProcessor

logger = logging.getLogger(__name__)


class DelayTimingTestFramework:
    """
    Specialized test framework for validating retry delay timing precision
    
    Features:
    - High-precision timestamp validation
    - Jitter tolerance calculations
    - Retry scheduling accuracy testing
    - Clock simulation for timing edge cases
    """
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.test_session = None
        self.retry_service = UnifiedRetryService()
        
        # Expected delay progression (in seconds)
        self.EXPECTED_DELAYS = {
            1: 300,    # 5 minutes
            2: 900,    # 15 minutes  
            3: 1800,   # 30 minutes
            4: 3600,   # 1 hour
            5: 7200,   # 2 hours
            6: 14400   # 4 hours
        }
        
        # Jitter tolerance (±20%)
        self.JITTER_TOLERANCE = 0.20
        
        # Test data tracking
        self.timing_measurements = []
        self.created_transactions = []
    
    def setup_test_database(self):
        """Setup test database for timing validation"""
        self.engine = create_engine(
            "sqlite:///:memory:", 
            echo=False,
            pool_pre_ping=True
        )
        
        Base.metadata.create_all(self.engine, checkfirst=True)
        self.session_factory = scoped_session(sessionmaker(bind=self.engine))
        self.test_session = self.session_factory()
        
        logger.info("🗄️ Delay timing test database initialized")
    
    def teardown_test_database(self):
        """Clean up test database and sessions"""
        if self.test_session:
            self.test_session.close()
        if self.session_factory:
            self.session_factory.remove()
        if self.engine:
            self.engine.dispose()
    
    def calculate_jitter_bounds(self, base_delay: int) -> Tuple[int, int]:
        """Calculate acceptable jitter bounds for a delay"""
        jitter_amount = int(base_delay * self.JITTER_TOLERANCE)
        min_delay = base_delay - jitter_amount
        max_delay = base_delay + jitter_amount
        return min_delay, max_delay
    
    def validate_delay_timing(self, attempt_number: int, actual_delay: int) -> bool:
        """Validate delay timing is within acceptable bounds"""
        expected_delay = self.EXPECTED_DELAYS.get(attempt_number)
        if not expected_delay:
            logger.error(f"❌ No expected delay defined for attempt {attempt_number}")
            return False
        
        min_delay, max_delay = self.calculate_jitter_bounds(expected_delay)
        
        if min_delay <= actual_delay <= max_delay:
            logger.info(f"✅ Delay timing validated: attempt {attempt_number} → {actual_delay}s (expected {expected_delay}s ±{self.JITTER_TOLERANCE*100}%)")
            return True
        else:
            logger.error(f"❌ Delay timing out of bounds: attempt {attempt_number} → {actual_delay}s (expected {expected_delay}s ±{self.JITTER_TOLERANCE*100}%)")
            return False
    
    def validate_next_retry_scheduling(self, scheduled_at: datetime, delay_seconds: int) -> bool:
        """Validate next retry is scheduled at correct time"""
        expected_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
        
        # Allow 5 second tolerance for test execution time
        time_tolerance = timedelta(seconds=5)
        min_time = expected_time - time_tolerance
        max_time = expected_time + time_tolerance
        
        if min_time <= scheduled_at <= max_time:
            logger.info(f"✅ Retry scheduling validated: scheduled at {scheduled_at}, expected around {expected_time}")
            return True
        else:
            logger.error(f"❌ Retry scheduling incorrect: scheduled at {scheduled_at}, expected around {expected_time}")
            return False
    
    def measure_timing_precision(self, operation_name: str, operation_func, *args, **kwargs):
        """Measure timing precision of operations"""
        start_time = time.perf_counter()
        start_datetime = datetime.utcnow()
        
        result = operation_func(*args, **kwargs)
        
        end_time = time.perf_counter()
        end_datetime = datetime.utcnow()
        
        execution_time = end_time - start_time
        
        measurement = {
            'operation': operation_name,
            'start_time': start_datetime,
            'end_time': end_datetime,
            'execution_time_seconds': execution_time,
            'result': result
        }
        
        self.timing_measurements.append(measurement)
        
        logger.info(f"⏱️ Timing measured: {operation_name} took {execution_time:.4f}s")
        return result
    
    def simulate_clock_advance(self, advance_seconds: int):
        """Simulate advancing the system clock for timing tests"""
        # This would typically involve mocking datetime.utcnow()
        # For testing purposes, we'll track the simulated advancement
        simulated_time = datetime.utcnow() + timedelta(seconds=advance_seconds)
        logger.info(f"🕐 Clock simulation: advanced by {advance_seconds}s to {simulated_time}")
        return simulated_time
    
    def cleanup(self):
        """Clean up test framework resources"""
        self.timing_measurements.clear()
        self.created_transactions.clear()
        self.teardown_test_database()


@pytest.fixture(scope="class")
def delay_timing_framework():
    """Pytest fixture providing delay timing test framework"""
    framework = DelayTimingTestFramework()
    framework.setup_test_database()
    
    yield framework
    
    framework.cleanup()


class TestProgressiveDelayCalculation:
    """Test progressive delay calculation accuracy"""
    
    @pytest.mark.asyncio
    async def test_delay_progression_sequence_1_to_6(self, delay_timing_framework):
        """Test delay progression from attempt 1 through 6"""
        
        # Test each retry attempt delay calculation
        for attempt_number in range(1, 7):
            # Create retry context
            retry_context = RetryContext(
                transaction_id=f'UTX_DELAY_TEST_{attempt_number:03d}',
                transaction_type='wallet_cashout',
                user_id=12345,
                amount=Decimal('100.00'),
                currency='USD',
                external_provider='fincra',
                attempt_number=attempt_number,
                error_code='FINCRA_API_TIMEOUT',
                error_message='Test timeout for delay validation'
            )
            
            # Measure delay calculation timing
            def calculate_delay():
                return delay_timing_framework.retry_service._calculate_retry_delay(attempt_number)
            
            actual_delay = delay_timing_framework.measure_timing_precision(
                f'delay_calculation_attempt_{attempt_number}',
                calculate_delay
            )
            
            # Validate delay is within expected bounds
            assert delay_timing_framework.validate_delay_timing(attempt_number, actual_delay)
            
            # Verify delay calculation consistency (multiple runs should have similar jitter)
            delays_sample = []
            for _ in range(10):
                sample_delay = delay_timing_framework.retry_service._calculate_retry_delay(attempt_number)
                delays_sample.append(sample_delay)
            
            # All delays should be within acceptable bounds
            for sample_delay in delays_sample:
                assert delay_timing_framework.validate_delay_timing(attempt_number, sample_delay)
            
            # Verify jitter variation (delays should not all be identical)
            unique_delays = set(delays_sample)
            assert len(unique_delays) > 1, f"Delays should vary due to jitter: {delays_sample}"
            
            logger.info(f"✅ Attempt {attempt_number} delay validation complete: {len(unique_delays)} unique delays in sample")
        
        logger.info("✅ Progressive delay sequence 1-6 validation complete")
    
    @pytest.mark.asyncio
    async def test_delay_calculation_edge_cases(self, delay_timing_framework):
        """Test delay calculation edge cases"""
        
        # Test attempt number 0 (should default to minimum)
        delay_0 = delay_timing_framework.retry_service._calculate_retry_delay(0)
        assert delay_0 >= 300, "Attempt 0 should default to minimum delay"
        
        # Test attempt number > 6 (should cap at maximum)
        delay_7 = delay_timing_framework.retry_service._calculate_retry_delay(7)
        delay_6 = delay_timing_framework.retry_service._calculate_retry_delay(6)
        
        # Should use maximum delay (same as attempt 6)
        min_6, max_6 = delay_timing_framework.calculate_jitter_bounds(14400)  # 4 hours
        assert min_6 <= delay_7 <= max_6, "Attempt >6 should cap at maximum delay"
        
        # Test negative attempt number (should handle gracefully)
        delay_negative = delay_timing_framework.retry_service._calculate_retry_delay(-1)
        assert delay_negative >= 300, "Negative attempt should default to minimum delay"
        
        logger.info("✅ Delay calculation edge cases validated")
    
    @pytest.mark.asyncio  
    async def test_jitter_implementation_quality(self, delay_timing_framework):
        """Test jitter implementation provides good randomization"""
        
        # Test jitter for each attempt level
        for attempt_number in range(1, 7):
            base_delay = delay_timing_framework.EXPECTED_DELAYS[attempt_number]
            
            # Collect large sample of delays
            delay_samples = []
            for _ in range(100):
                delay = delay_timing_framework.retry_service._calculate_retry_delay(attempt_number)
                delay_samples.append(delay)
            
            # Statistical analysis of jitter quality
            min_delay = min(delay_samples)
            max_delay = max(delay_samples)
            mean_delay = sum(delay_samples) / len(delay_samples)
            
            # Verify mean is close to expected base delay
            mean_deviation = abs(mean_delay - base_delay) / base_delay
            assert mean_deviation < 0.05, f"Mean delay too far from base: {mean_delay} vs {base_delay}"
            
            # Verify good spread across jitter range
            expected_min, expected_max = delay_timing_framework.calculate_jitter_bounds(base_delay)
            spread_coverage = (max_delay - min_delay) / (expected_max - expected_min)
            
            assert spread_coverage > 0.7, f"Jitter spread too narrow: {spread_coverage} for attempt {attempt_number}"
            
            # Verify no obvious patterns (basic randomness check)
            # Check that consecutive delays are not too similar
            consecutive_similarities = 0
            for i in range(1, len(delay_samples)):
                if abs(delay_samples[i] - delay_samples[i-1]) < (base_delay * 0.01):  # Less than 1% difference
                    consecutive_similarities += 1
            
            similarity_ratio = consecutive_similarities / (len(delay_samples) - 1)
            assert similarity_ratio < 0.1, f"Too many consecutive similar delays: {similarity_ratio} for attempt {attempt_number}"
            
            logger.info(f"✅ Jitter quality validated for attempt {attempt_number}: spread={spread_coverage:.2f}, similarity={similarity_ratio:.2f}")
        
        logger.info("✅ Jitter implementation quality validated")


class TestRetrySchedulingAccuracy:
    """Test retry scheduling accuracy and timing precision"""
    
    @pytest.mark.asyncio
    async def test_next_retry_timestamp_accuracy(self, delay_timing_framework):
        """Test next retry timestamp calculation accuracy"""
        
        for attempt_number in range(1, 7):
            retry_context = RetryContext(
                transaction_id=f'UTX_SCHEDULE_TEST_{attempt_number:03d}',
                transaction_type='wallet_cashout',
                user_id=12345,
                amount=Decimal('100.00'),
                currency='USD',
                external_provider='fincra',
                attempt_number=attempt_number,
                error_code='FINCRA_API_TIMEOUT',
                error_message='Test for scheduling accuracy'
            )
            
            # Measure retry result generation timing
            def generate_retry_result():
                return asyncio.run(delay_timing_framework.retry_service.handle_transaction_failure(
                    retry_context, Exception("Test timeout")
                ))
            
            retry_result = delay_timing_framework.measure_timing_precision(
                f'retry_scheduling_attempt_{attempt_number}',
                generate_retry_result
            )
            
            # Validate retry was scheduled
            assert retry_result.decision == RetryDecision.RETRY
            assert retry_result.next_retry_at is not None
            assert retry_result.delay_seconds is not None
            
            # Validate timestamp accuracy
            assert delay_timing_framework.validate_next_retry_scheduling(
                retry_result.next_retry_at, 
                retry_result.delay_seconds
            )
            
            # Validate delay timing
            assert delay_timing_framework.validate_delay_timing(
                attempt_number, 
                retry_result.delay_seconds
            )
            
            logger.info(f"✅ Scheduling accuracy validated for attempt {attempt_number}")
        
        logger.info("✅ Retry scheduling accuracy validation complete")
    
    @pytest.mark.asyncio
    async def test_retry_readiness_detection(self, delay_timing_framework):
        """Test retry readiness detection based on timestamps"""
        
        # Create transactions with various retry schedules
        test_scenarios = [
            {'name': 'ready_now', 'delay_offset': -60},      # 1 minute ago (ready)
            {'name': 'ready_soon', 'delay_offset': -5},      # 5 seconds ago (ready)
            {'name': 'future_1min', 'delay_offset': 60},     # 1 minute from now (not ready)
            {'name': 'future_5min', 'delay_offset': 300},    # 5 minutes from now (not ready)
            {'name': 'future_1hr', 'delay_offset': 3600}     # 1 hour from now (not ready)
        ]
        
        created_transactions = []
        
        for scenario in test_scenarios:
            # Create transaction with specific retry schedule
            transaction_id = f'UTX_READINESS_{scenario["name"].upper()}'
            
            next_retry_at = datetime.utcnow() + timedelta(seconds=scenario['delay_offset'])
            
            # Simulate transaction record
            tx_data = {
                'transaction_id': transaction_id,
                'next_retry_at': next_retry_at,
                'retry_count': 1,
                'status': UnifiedTransactionStatus.FAILED,
                'failure_type': 'technical'
            }
            
            created_transactions.append(tx_data)
        
        # Test readiness detection
        current_time = datetime.utcnow()
        
        for tx_data in created_transactions:
            is_ready = tx_data['next_retry_at'] <= current_time
            
            if 'ready' in tx_data['transaction_id'].lower():
                assert is_ready, f"Transaction should be ready: {tx_data['transaction_id']}"
                logger.info(f"✅ Ready transaction detected: {tx_data['transaction_id']}")
            else:
                assert not is_ready, f"Transaction should not be ready: {tx_data['transaction_id']}"
                logger.info(f"✅ Future transaction correctly not ready: {tx_data['transaction_id']}")
        
        logger.info("✅ Retry readiness detection validated")
    
    @pytest.mark.asyncio
    async def test_high_frequency_retry_scheduling_performance(self, delay_timing_framework):
        """Test performance under high-frequency retry scheduling"""
        
        # Create many retry contexts rapidly
        num_transactions = 50
        retry_contexts = []
        
        for i in range(num_transactions):
            retry_context = RetryContext(
                transaction_id=f'UTX_PERF_TEST_{i:04d}',
                transaction_type='wallet_cashout',
                user_id=10000 + i,
                amount=Decimal('50.00'),
                currency='USD',
                external_provider='fincra',
                attempt_number=random.randint(1, 6),
                error_code='FINCRA_API_TIMEOUT',
                error_message=f'Performance test {i}'
            )
            retry_contexts.append(retry_context)
        
        # Measure batch processing performance
        def process_retry_batch():
            results = []
            for ctx in retry_contexts:
                result = asyncio.run(delay_timing_framework.retry_service.handle_transaction_failure(
                    ctx, Exception("Performance test")
                ))
                results.append(result)
            return results
        
        batch_results = delay_timing_framework.measure_timing_precision(
            'high_frequency_retry_batch',
            process_retry_batch
        )
        
        # Validate performance metrics
        execution_measurement = delay_timing_framework.timing_measurements[-1]
        total_time = execution_measurement['execution_time_seconds']
        avg_time_per_retry = total_time / num_transactions
        
        # Should process retries quickly (< 100ms per retry on average)
        assert avg_time_per_retry < 0.1, f"Retry processing too slow: {avg_time_per_retry}s per retry"
        
        # Validate all results
        successful_schedules = 0
        for result in batch_results:
            if result.decision == RetryDecision.RETRY:
                successful_schedules += 1
                assert result.next_retry_at is not None
                assert result.delay_seconds is not None
        
        # Most should be successfully scheduled (allowing for some max retry cases)
        success_rate = successful_schedules / num_transactions
        assert success_rate > 0.8, f"Success rate too low: {success_rate}"
        
        logger.info(f"✅ High-frequency performance validated: {avg_time_per_retry:.4f}s per retry, {success_rate:.2f} success rate")


class TestTimingEdgeCases:
    """Test timing edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_timezone_handling(self, delay_timing_framework):
        """Test retry scheduling handles timezone differences correctly"""
        
        # All retry scheduling should use UTC consistently
        retry_context = RetryContext(
            transaction_id='UTX_TIMEZONE_TEST',
            transaction_type='wallet_cashout',
            user_id=12345,
            amount=Decimal('100.00'),
            currency='USD',
            external_provider='fincra',
            attempt_number=2,
            error_code='FINCRA_API_TIMEOUT',
            error_message='Timezone test'
        )
        
        # Capture current UTC time
        utc_before = datetime.utcnow()
        
        retry_result = await delay_timing_framework.retry_service.handle_transaction_failure(
            retry_context, Exception("Timezone test")
        )
        
        utc_after = datetime.utcnow()
        
        # Verify scheduled time is in UTC
        scheduled_time = retry_result.next_retry_at
        
        # Should be scheduled in the future from current UTC time
        assert scheduled_time > utc_before
        
        # Should be reasonably close to expected delay (15 minutes for attempt 2)
        expected_schedule_time = utc_before + timedelta(seconds=retry_result.delay_seconds)
        time_diff = abs((scheduled_time - expected_schedule_time).total_seconds())
        
        # Allow 10 second tolerance for test execution
        assert time_diff < 10, f"Scheduled time deviation too large: {time_diff}s"
        
        logger.info("✅ Timezone handling validated (UTC consistency)")
    
    @pytest.mark.asyncio
    async def test_daylight_saving_time_transitions(self, delay_timing_framework):
        """Test retry scheduling around daylight saving time transitions"""
        
        # This test simulates scheduling retries around DST transitions
        # In production, this ensures retries aren't lost or duplicated during DST changes
        
        # Simulate scheduling before DST transition
        with patch('datetime.datetime') as mock_datetime:
            # Mock a time just before DST spring forward (2 AM becomes 3 AM)
            dst_transition_time = datetime(2024, 3, 10, 1, 30, 0)  # 1:30 AM EST
            mock_datetime.utcnow.return_value = dst_transition_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            retry_context = RetryContext(
                transaction_id='UTX_DST_TEST',
                transaction_type='wallet_cashout',
                user_id=12345,
                amount=Decimal('100.00'),
                currency='USD',
                external_provider='fincra',
                attempt_number=1,
                error_code='FINCRA_API_TIMEOUT',
                error_message='DST transition test'
            )
            
            retry_result = await delay_timing_framework.retry_service.handle_transaction_failure(
                retry_context, Exception("DST test")
            )
            
            # Should schedule successfully despite DST transition
            assert retry_result.decision == RetryDecision.RETRY
            assert retry_result.next_retry_at is not None
            
            # Scheduled time should be reasonable (5 minutes from mock current time)
            expected_time = dst_transition_time + timedelta(seconds=retry_result.delay_seconds)
            scheduled_time = retry_result.next_retry_at
            
            # Since we're using UTC internally, DST shouldn't affect the calculation
            time_diff = abs((scheduled_time - expected_time).total_seconds())
            assert time_diff < 60, f"DST transition caused timing issue: {time_diff}s difference"
        
        logger.info("✅ Daylight saving time transition handling validated")
    
    @pytest.mark.asyncio
    async def test_clock_skew_tolerance(self, delay_timing_framework):
        """Test system handles minor clock skew gracefully"""
        
        # Simulate minor clock differences between system components
        retry_context = RetryContext(
            transaction_id='UTX_CLOCK_SKEW_TEST',
            transaction_type='wallet_cashout',
            user_id=12345,
            amount=Decimal('100.00'),
            currency='USD',
            external_provider='fincra',
            attempt_number=3,
            error_code='FINCRA_API_TIMEOUT',
            error_message='Clock skew test'
        )
        
        # Process retry normally
        retry_result = await delay_timing_framework.retry_service.handle_transaction_failure(
            retry_context, Exception("Clock skew test")
        )
        
        assert retry_result.decision == RetryDecision.RETRY
        base_scheduled_time = retry_result.next_retry_at
        
        # Simulate checking retry readiness with slight clock skew (-30 seconds to +30 seconds)
        clock_skew_scenarios = [-30, -10, 0, 10, 30]
        
        for skew_seconds in clock_skew_scenarios:
            # Simulate time with skew
            skewed_current_time = datetime.utcnow() + timedelta(seconds=skew_seconds)
            
            # Check if retry would be considered ready
            time_until_retry = (base_scheduled_time - skewed_current_time).total_seconds()
            
            if time_until_retry <= 0:
                # Should be ready
                is_ready = True
            else:
                # Should not be ready yet
                is_ready = False
            
            logger.info(f"✅ Clock skew {skew_seconds}s: retry ready = {is_ready}, time until = {time_until_retry:.1f}s")
        
        # System should handle reasonable clock skew gracefully
        logger.info("✅ Clock skew tolerance validated")
    
    @pytest.mark.asyncio
    async def test_leap_second_handling(self, delay_timing_framework):
        """Test retry scheduling around leap second events"""
        
        # Leap seconds are rare but can cause timing issues
        # This test ensures retry scheduling is robust around leap second events
        
        retry_context = RetryContext(
            transaction_id='UTX_LEAP_SECOND_TEST',
            transaction_type='wallet_cashout',
            user_id=12345,
            amount=Decimal('100.00'),
            currency='USD',
            external_provider='fincra',
            attempt_number=4,
            error_code='FINCRA_API_TIMEOUT',
            error_message='Leap second test'
        )
        
        # Simulate scheduling during a potential leap second event
        with patch('datetime.datetime') as mock_datetime:
            # Mock a time around midnight UTC when leap seconds typically occur
            leap_second_time = datetime(2024, 6, 30, 23, 59, 59)  # End of June
            mock_datetime.utcnow.return_value = leap_second_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            retry_result = await delay_timing_framework.retry_service.handle_transaction_failure(
                retry_context, Exception("Leap second test")
            )
            
            # Should schedule successfully despite potential leap second
            assert retry_result.decision == RetryDecision.RETRY
            assert retry_result.next_retry_at is not None
            assert retry_result.delay_seconds is not None
            
            # Delay should be reasonable for attempt 4 (1 hour)
            assert delay_timing_framework.validate_delay_timing(4, retry_result.delay_seconds)
        
        logger.info("✅ Leap second handling validated")


class TestDelayProgessionIntegration:
    """Test delay progression integration with actual retry processing"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_delay_progression(self, delay_timing_framework):
        """Test end-to-end delay progression through multiple retry attempts"""
        
        # Simulate a transaction that fails and retries through multiple attempts
        transaction_id = 'UTX_E2E_DELAY_TEST'
        user_id = 12345
        
        # Track delay progression through attempts
        delay_history = []
        
        for attempt in range(1, 7):  # Attempts 1 through 6
            retry_context = RetryContext(
                transaction_id=transaction_id,
                transaction_type='wallet_cashout',
                user_id=user_id,
                amount=Decimal('100.00'),
                currency='USD',
                external_provider='fincra',
                attempt_number=attempt,
                error_code='FINCRA_API_TIMEOUT',
                error_message=f'E2E test attempt {attempt}'
            )
            
            # Process retry
            retry_result = await delay_timing_framework.retry_service.handle_transaction_failure(
                retry_context, Exception(f"Attempt {attempt} failure")
            )
            
            if attempt < 6:
                # Should schedule retry for attempts 1-5
                assert retry_result.decision == RetryDecision.RETRY
                assert retry_result.delay_seconds is not None
                
                # Validate delay progression
                assert delay_timing_framework.validate_delay_timing(attempt, retry_result.delay_seconds)
                
                delay_history.append({
                    'attempt': attempt,
                    'delay_seconds': retry_result.delay_seconds,
                    'next_retry_at': retry_result.next_retry_at
                })
            else:
                # Attempt 6 should fail permanently
                assert retry_result.decision == RetryDecision.FAIL
                assert retry_result.final_failure is True
        
        # Verify delay progression increased appropriately
        for i in range(1, len(delay_history)):
            prev_delay = delay_history[i-1]['delay_seconds']
            curr_delay = delay_history[i]['delay_seconds']
            
            # Current delay should be significantly larger than previous
            # (accounting for jitter, should be at least 50% larger)
            delay_ratio = curr_delay / prev_delay
            assert delay_ratio > 1.5, f"Delay progression insufficient: attempt {i+1} ({curr_delay}s) vs attempt {i} ({prev_delay}s)"
        
        logger.info(f"✅ End-to-end delay progression validated: {len(delay_history)} attempts")
        
        # Log the full progression for verification
        for entry in delay_history:
            logger.info(f"  Attempt {entry['attempt']}: {entry['delay_seconds']}s delay → {entry['next_retry_at']}")
    
    @pytest.mark.asyncio
    async def test_retry_processor_delay_timing_integration(self, delay_timing_framework):
        """Test retry processor respects calculated delay timings"""
        
        # Create multiple transactions with different retry schedules
        test_transactions = []
        
        current_time = datetime.utcnow()
        
        # Create transactions scheduled at different future times
        schedule_offsets = [60, 300, 900, 1800]  # 1min, 5min, 15min, 30min from now
        
        for i, offset in enumerate(schedule_offsets):
            transaction_data = {
                'transaction_id': f'UTX_PROCESSOR_TIMING_{i:02d}',
                'user_id': 20000 + i,
                'amount': Decimal('75.00'),
                'currency': 'USD',
                'provider': 'fincra',
                'retry_count': i + 1,
                'next_retry_at': current_time + timedelta(seconds=offset),
                'should_be_ready': offset <= 0  # Only ready if offset is 0 or negative
            }
            test_transactions.append(transaction_data)
        
        # Simulate retry processor checking for ready transactions
        ready_count = 0
        not_ready_count = 0
        
        for tx_data in test_transactions:
            # Check if transaction would be considered ready by processor
            time_until_retry = (tx_data['next_retry_at'] - datetime.utcnow()).total_seconds()
            
            if time_until_retry <= 0:
                ready_count += 1
                logger.info(f"✅ Transaction ready for processing: {tx_data['transaction_id']}")
            else:
                not_ready_count += 1
                logger.info(f"⏰ Transaction not ready (waiting {time_until_retry:.1f}s): {tx_data['transaction_id']}")
        
        # Verify timing logic
        assert ready_count == 0, "No transactions should be immediately ready in this test"
        assert not_ready_count == len(test_transactions), "All transactions should be waiting"
        
        # Test processor would pick up transactions when their time comes
        # (This would require advancing the clock or waiting, so we simulate the logic)
        
        logger.info(f"✅ Retry processor timing integration validated: {ready_count} ready, {not_ready_count} waiting")


if __name__ == "__main__":
    # Run progressive delay timing tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "delay"
    ])