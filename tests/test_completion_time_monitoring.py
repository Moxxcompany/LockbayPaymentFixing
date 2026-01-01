"""
Test suite for Completion Time Trends Monitoring system
Verifies the monitoring system works correctly without impacting performance
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from utils.completion_time_trends_monitor import (
    CompletionTimeTrendsMonitor,
    OperationType,
    TrendDirection,
    CompletionTimeRecord,
    TrendMetrics
)
from utils.completion_time_integration import (
    track_onboarding_step,
    track_webhook_processing,
    track_database_operation,
    completion_time_integration,
    record_onboarding_completion_time,
    get_system_performance_overview
)


class TestCompletionTimeTrendsMonitor:
    """Test cases for the core monitoring system"""
    
    def setup_method(self):
        """Setup for each test"""
        self.monitor = CompletionTimeTrendsMonitor()
    
    def test_monitor_initialization(self):
        """Test monitor initializes correctly"""
        assert self.monitor.max_records_per_operation == 1000
        assert self.monitor.trend_analysis_hours == 4
        assert self.monitor.baseline_analysis_days == 7
        assert not self.monitor.is_monitoring_active
        assert len(self.monitor.completion_records) == 0
        assert len(self.monitor.trend_metrics) == 0
    
    def test_record_completion_time(self):
        """Test recording completion times"""
        # Record a completion time
        self.monitor.record_completion_time(
            OperationType.ONBOARDING,
            "email_verification",
            1500.0,
            user_id=12345,
            success=True
        )
        
        key = "onboarding:email_verification"
        assert key in self.monitor.completion_records
        assert len(self.monitor.completion_records[key]) == 1
        
        record = self.monitor.completion_records[key][0]
        assert record.operation_type == OperationType.ONBOARDING
        assert record.operation_name == "email_verification"
        assert record.completion_time_ms == 1500.0
        assert record.user_id == 12345
        assert record.success is True
    
    def test_record_multiple_completion_times(self):
        """Test recording multiple completion times"""
        operation_type = OperationType.WEBHOOK_PROCESSING
        operation_name = "payment_webhook"
        
        # Record multiple times
        for i in range(5):
            self.monitor.record_completion_time(
                operation_type,
                operation_name,
                1000 + i * 100,  # 1000, 1100, 1200, 1300, 1400
                success=True
            )
        
        key = f"{operation_type.value}:{operation_name}"
        assert len(self.monitor.completion_records[key]) == 5
        
        # Check the times are recorded correctly
        times = [r.completion_time_ms for r in self.monitor.completion_records[key]]
        expected_times = [1000, 1100, 1200, 1300, 1400]
        assert times == expected_times
    
    def test_maxlen_enforcement(self):
        """Test that max records per operation is enforced"""
        # Create monitor with small maxlen for testing
        monitor = CompletionTimeTrendsMonitor(max_records_per_operation=3)
        
        operation_type = OperationType.DATABASE_QUERY
        operation_name = "test_query"
        
        # Add more records than maxlen
        for i in range(5):
            monitor.record_completion_time(
                operation_type,
                operation_name,
                i * 100,
                success=True
            )
        
        key = f"{operation_type.value}:{operation_name}"
        # Should only keep the last 3 records
        assert len(monitor.completion_records[key]) == 3
        
        # Check it kept the most recent ones
        times = [r.completion_time_ms for r in monitor.completion_records[key]]
        assert times == [200, 300, 400]  # Last 3 records
    
    def test_performance_thresholds(self):
        """Test performance threshold configuration"""
        onboarding_thresholds = self.monitor.performance_thresholds[OperationType.ONBOARDING]
        assert onboarding_thresholds['baseline_ms'] == 15000
        assert onboarding_thresholds['warning_ms'] == 25000
        assert onboarding_thresholds['critical_ms'] == 45000
        
        webhook_thresholds = self.monitor.performance_thresholds[OperationType.WEBHOOK_PROCESSING]
        assert webhook_thresholds['baseline_ms'] == 500
        assert webhook_thresholds['warning_ms'] == 2000
        assert webhook_thresholds['critical_ms'] == 5000
    
    async def test_trend_calculation_insufficient_data(self):
        """Test trend calculation with insufficient data"""
        # Record only a few data points
        for i in range(3):
            self.monitor.record_completion_time(
                OperationType.ONBOARDING,
                "test_operation",
                1000 + i * 100,
                success=True
            )
        
        key = "onboarding:test_operation"
        records = self.monitor.completion_records[key]
        
        # Calculate trends
        trends = await self.monitor._calculate_trend_metrics(key, records)
        
        assert trends.trend_direction == TrendDirection.INSUFFICIENT_DATA
        assert trends.sample_count == 3
        assert trends.performance_score == 0


class TestCompletionTimeIntegration:
    """Test cases for integration with existing systems"""
    
    def test_track_onboarding_decorator(self):
        """Test onboarding tracking decorator"""
        
        @track_onboarding_step("test_step")
        async def test_onboarding_function():
            await asyncio.sleep(0.1)  # Simulate work
            return "success"
        
        # Test that it's a proper async function
        assert asyncio.iscoroutinefunction(test_onboarding_function)
    
    def test_track_webhook_decorator(self):
        """Test webhook tracking decorator"""
        
        @track_webhook_processing("test_webhook")
        async def test_webhook_function():
            await asyncio.sleep(0.05)
            return {"status": "processed"}
        
        assert asyncio.iscoroutinefunction(test_webhook_function)
    
    def test_track_database_decorator(self):
        """Test database tracking decorator"""
        
        @track_database_operation("test_query", "test_table")
        def test_db_function():
            time.sleep(0.01)
            return {"rows": 5}
        
        # Test sync function
        assert not asyncio.iscoroutinefunction(test_db_function)
    
    def test_manual_recording(self):
        """Test manual completion time recording"""
        from utils.completion_time_trends_monitor import completion_time_monitor
        
        # Clear existing records
        completion_time_monitor.completion_records.clear()
        
        # Record manually
        record_onboarding_completion_time(
            "manual_test",
            2500.0,
            user_id=99999,
            success=True
        )
        
        # Verify it was recorded
        key = "onboarding:onboarding_manual_test"
        assert key in completion_time_monitor.completion_records
        assert len(completion_time_monitor.completion_records[key]) == 1
        
        record = completion_time_monitor.completion_records[key][0]
        assert record.completion_time_ms == 2500.0
        assert record.user_id == 99999
        assert record.success is True


class TestTrendAnalysis:
    """Test cases for trend analysis functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.monitor = CompletionTimeTrendsMonitor()
    
    def test_determine_trend_direction_stable(self):
        """Test trend direction detection - stable"""
        direction = self.monitor._determine_trend_direction(5.0, 3.0, 2.0)  # Small changes
        assert direction == TrendDirection.STABLE
    
    def test_determine_trend_direction_improving(self):
        """Test trend direction detection - improving"""
        direction = self.monitor._determine_trend_direction(-20.0, -18.0, -22.0)  # Significant improvement
        assert direction == TrendDirection.IMPROVING
    
    def test_determine_trend_direction_degrading(self):
        """Test trend direction detection - degrading"""
        direction = self.monitor._determine_trend_direction(25.0, 30.0, 20.0)  # Significant degradation
        assert direction == TrendDirection.DEGRADING
    
    def test_determine_trend_direction_volatile(self):
        """Test trend direction detection - volatile"""
        direction = self.monitor._determine_trend_direction(-30.0, 40.0, 10.0)  # High variance
        assert direction == TrendDirection.VOLATILE
    
    def test_calculate_performance_score(self):
        """Test performance score calculation"""
        baseline_ms = 1000.0
        
        # At baseline (should be 100)
        score = self.monitor._calculate_performance_score(1000.0, baseline_ms)
        assert score == 100.0
        
        # Better than baseline (should be > 100, capped at 100)
        score = self.monitor._calculate_performance_score(500.0, baseline_ms)  # 2x better
        assert score == 100.0
        
        # Worse than baseline (should be < 100)
        score = self.monitor._calculate_performance_score(2000.0, baseline_ms)  # 2x worse
        assert score == 0.0  # Significantly worse
        
        # No baseline (should be neutral)
        score = self.monitor._calculate_performance_score(1000.0, 0.0)
        assert score == 50.0


class TestPerformanceImpact:
    """Test that monitoring doesn't impact system performance"""
    
    def test_monitoring_overhead(self):
        """Test that monitoring adds minimal overhead"""
        monitor = CompletionTimeTrendsMonitor()
        
        # Time normal operation
        start_time = time.time()
        for _ in range(1000):
            pass  # No monitoring
        baseline_time = time.time() - start_time
        
        # Time with monitoring
        start_time = time.time()
        for i in range(1000):
            monitor.record_completion_time(
                OperationType.DATABASE_QUERY,
                "test_query",
                10.0 + i,
                success=True
            )
        monitoring_time = time.time() - start_time
        
        # Monitoring overhead should be minimal (< 5x baseline)
        overhead_ratio = monitoring_time / max(baseline_time, 0.001)  # Avoid division by zero
        assert overhead_ratio < 5.0, f"Monitoring overhead too high: {overhead_ratio:.2f}x"
    
    def test_memory_usage_bounds(self):
        """Test that memory usage is bounded by maxlen"""
        monitor = CompletionTimeTrendsMonitor(max_records_per_operation=100)
        
        # Add many records for different operations
        for op_id in range(10):  # 10 different operations
            for i in range(150):  # 150 records each (more than maxlen)
                monitor.record_completion_time(
                    OperationType.DATABASE_QUERY,
                    f"operation_{op_id}",
                    i * 10,
                    success=True
                )
        
        # Check memory is bounded
        total_records = sum(len(records) for records in monitor.completion_records.values())
        assert total_records <= 10 * 100  # 10 operations × 100 max records each
        assert total_records == 10 * 100  # Should be exactly at the limit


class TestRealWorldScenarios:
    """Test realistic usage scenarios"""
    
    def test_onboarding_flow_monitoring(self):
        """Test monitoring a complete onboarding flow"""
        monitor = CompletionTimeTrendsMonitor()
        
        # Simulate onboarding steps with realistic times
        onboarding_steps = [
            ("email_capture", 800),
            ("email_verification", 15000),
            ("otp_verification", 5000),
            ("terms_acceptance", 1200),
            ("wallet_creation", 3000)
        ]
        
        for step_name, duration_ms in onboarding_steps:
            monitor.record_completion_time(
                OperationType.ONBOARDING,
                step_name,
                duration_ms,
                user_id=12345,
                success=True
            )
        
        # Verify all steps were recorded
        for step_name, _ in onboarding_steps:
            key = f"onboarding:{step_name}"
            assert key in monitor.completion_records
            assert len(monitor.completion_records[key]) == 1
    
    def test_webhook_burst_monitoring(self):
        """Test monitoring webhook bursts (realistic load)"""
        monitor = CompletionTimeTrendsMonitor()
        
        # Simulate webhook burst with varying processing times
        webhook_types = ["payment", "escrow_update", "balance_change"]
        
        for webhook_type in webhook_types:
            for i in range(20):  # 20 webhooks of each type
                # Simulate realistic processing times with some variance
                base_time = 200 if webhook_type == "payment" else 100
                processing_time = base_time + (i % 10) * 50  # Add variance
                
                monitor.record_completion_time(
                    OperationType.WEBHOOK_PROCESSING,
                    webhook_type,
                    processing_time,
                    success=True
                )
        
        # Verify all webhooks were recorded
        for webhook_type in webhook_types:
            key = f"webhook_processing:{webhook_type}"
            assert key in monitor.completion_records
            assert len(monitor.completion_records[key]) == 20


# Integration test with async context manager
@pytest.mark.asyncio
async def test_async_context_manager():
    """Test the async context manager for tracking operations"""
    from utils.completion_time_trends_monitor import completion_time_monitor
    
    # Clear existing records
    completion_time_monitor.completion_records.clear()
    
    # Use context manager
    async with completion_time_monitor.track_operation(
        OperationType.TRANSACTION_PROCESSING,
        "test_transaction",
        user_id=54321,
        metadata={"currency": "USD", "amount": 100.0}
    ):
        await asyncio.sleep(0.1)  # Simulate work
    
    # Verify it was recorded
    key = "transaction_processing:test_transaction"
    assert key in completion_time_monitor.completion_records
    assert len(completion_time_monitor.completion_records[key]) == 1
    
    record = completion_time_monitor.completion_records[key][0]
    assert record.operation_type == OperationType.TRANSACTION_PROCESSING
    assert record.operation_name == "test_transaction"
    assert record.user_id == 54321
    assert record.success is True
    assert record.metadata["currency"] == "USD"
    assert record.metadata["amount"] == 100.0
    assert record.completion_time_ms > 100  # Should be > 100ms due to sleep


# Performance regression detection test
@pytest.mark.asyncio
async def test_performance_regression_detection():
    """Test that the system can detect performance regressions"""
    monitor = CompletionTimeTrendsMonitor(trend_analysis_hours=1)  # Shorter for testing
    
    operation_type = OperationType.DATABASE_QUERY
    operation_name = "performance_test"
    
    # Create baseline performance (good times)
    baseline_time = datetime.now() - timedelta(hours=2)
    for i in range(10):
        record = CompletionTimeRecord(
            operation_type=operation_type,
            operation_name=operation_name,
            completion_time_ms=500 + i * 10,  # 500-590ms (good performance)
            timestamp=baseline_time + timedelta(minutes=i),
            success=True
        )
        key = f"{operation_type.value}:{operation_name}"
        monitor.completion_records[key].append(record)
    
    # Create recent degraded performance
    recent_time = datetime.now() - timedelta(minutes=30)
    for i in range(10):
        record = CompletionTimeRecord(
            operation_type=operation_type,
            operation_name=operation_name,
            completion_time_ms=1500 + i * 20,  # 1500-1680ms (degraded performance)
            timestamp=recent_time + timedelta(minutes=i),
            success=True
        )
        key = f"{operation_type.value}:{operation_name}"
        monitor.completion_records[key].append(record)
    
    # Calculate trends
    key = f"{operation_type.value}:{operation_name}"
    records = monitor.completion_records[key]
    trends = await monitor._calculate_trend_metrics(key, records)
    
    # Should detect regression
    assert trends.regression_detected is True
    assert trends.avg_change_percent > 100  # Significant increase
    assert trends.trend_direction == TrendDirection.DEGRADING


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])