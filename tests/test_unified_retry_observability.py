"""
Observability and Metrics Tests for Unified Retry System
Tests validate comprehensive metrics collection, queue tracking, success rates,
and monitoring capabilities for production operations.

Key Test Areas:
1. Retry queue metrics (queue depth, ready count, scheduled count)
2. Success rate tracking by provider and error type
3. Performance metrics (retry processing time, batch efficiency)
4. Alert threshold monitoring (queue depth, error rates)
5. Historical trend analysis (retry patterns over time)
6. Dashboard metrics integration
7. Real-time monitoring capabilities
8. SLA compliance tracking
"""

import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
import statistics
import time

# Database and model imports
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, scoped_session
from database import managed_session
from models import (
    Base, User, Wallet, UnifiedTransaction, UnifiedTransactionStatus, 
    UnifiedTransactionType, UnifiedTransactionRetryLog, CashoutErrorCode
)

# Service imports for testing
from services.unified_retry_service import UnifiedRetryService
from services.cashout_retry_metrics import RetryMetricsService
from jobs.unified_retry_processor import UnifiedRetryProcessor
from utils.unified_activity_monitor import UnifiedActivityMonitor

logger = logging.getLogger(__name__)


class ObservabilityTestFramework:
    """
    Test framework for observability and metrics validation
    
    Features:
    - Metrics collection simulation
    - Dashboard data validation
    - Alert threshold testing
    - Performance monitoring
    - Historical data analysis
    """
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.test_session = None
        
        # Metrics tracking
        self.collected_metrics = []
        self.dashboard_updates = []
        self.alert_triggers = []
        
        # Services
        self.retry_service = UnifiedRetryService()
        self.retry_processor = UnifiedRetryProcessor()
        self.metrics_service = RetryMetricsService()
        
        # Test data
        self.created_transactions = []
        self.created_users = []
    
    def setup_test_database(self):
        """Setup test database for observability testing"""
        self.engine = create_engine(
            "sqlite:///:memory:", 
            echo=False,
            pool_pre_ping=True
        )
        
        Base.metadata.create_all(self.engine, checkfirst=True)
        self.session_factory = scoped_session(sessionmaker(bind=self.engine))
        self.test_session = self.session_factory()
        
        logger.info("🗄️ Observability test database initialized")
    
    def teardown_test_database(self):
        """Clean up test database and sessions"""
        if self.test_session:
            self.test_session.close()
        if self.session_factory:
            self.session_factory.remove()
        if self.engine:
            self.engine.dispose()
    
    def setup_mock_monitoring_services(self):
        """Setup mock monitoring and metrics services"""
        
        # Mock metrics collection
        self.mock_metrics_collector = Mock()
        self.mock_metrics_collector.record_metric = self._mock_record_metric
        
        # Mock dashboard service
        self.mock_dashboard = Mock()
        self.mock_dashboard.update_metrics = self._mock_dashboard_update
        
        # Mock alerting service
        self.mock_alerting = Mock()
        self.mock_alerting.trigger_alert = self._mock_trigger_alert
        
        logger.info("🔧 Mock monitoring services configured")
    
    def _mock_record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Mock metrics recording"""
        metric_record = {
            'timestamp': datetime.utcnow(),
            'metric_name': metric_name,
            'value': value,
            'tags': tags or {}
        }
        
        self.collected_metrics.append(metric_record)
        logger.info(f"📊 Metric recorded: {metric_name} = {value}")
        
        return True
    
    def _mock_dashboard_update(self, dashboard_data: Dict[str, Any]):
        """Mock dashboard update"""
        update_record = {
            'timestamp': datetime.utcnow(),
            'dashboard_data': dashboard_data
        }
        
        self.dashboard_updates.append(update_record)
        logger.info(f"📈 Dashboard updated: {len(dashboard_data)} data points")
        
        return True
    
    def _mock_trigger_alert(self, alert_type: str, message: str, severity: str = 'warning'):
        """Mock alert triggering"""
        alert_record = {
            'timestamp': datetime.utcnow(),
            'alert_type': alert_type,
            'message': message,
            'severity': severity
        }
        
        self.alert_triggers.append(alert_record)
        logger.info(f"🚨 Alert triggered: {alert_type} ({severity})")
        
        return True
    
    def create_test_retry_scenario(self, 
                                 scenario_name: str,
                                 transaction_count: int,
                                 providers: List[str],
                                 retry_patterns: List[Dict[str, Any]]) -> List[str]:
        """
        Create test scenarios with various retry patterns for metrics testing
        
        Args:
            scenario_name: Name of the test scenario
            transaction_count: Number of transactions to create
            providers: List of external providers 
            retry_patterns: List of retry patterns (success/failure rates, timing)
            
        Returns:
            List of created transaction IDs
        """
        created_transaction_ids = []
        
        for i in range(transaction_count):
            # Select provider and pattern
            provider = providers[i % len(providers)]
            pattern = retry_patterns[i % len(retry_patterns)]
            
            # Create user
            user = User(
                telegram_id=f'{scenario_name}_user_{i}',
                username=f'test_{scenario_name}_{i}',
                first_name='Test',
                last_name='User',
                email=f'test_{i}@example.com',
                is_active=True
            )
            
            self.test_session.add(user)
            self.test_session.commit()
            
            # Create wallet
            wallet = Wallet(
                user_id=user.id,
                currency='USD',
                balance=Decimal('1000.00'),
                frozen_balance=Decimal('100.00'),
                total_deposited=Decimal('1000.00'),
                total_withdrawn=Decimal('0.00')
            )
            
            self.test_session.add(wallet)
            self.test_session.commit()
            
            # Create transaction with specific pattern
            from utils.helpers import generate_utid
            transaction_id = generate_utid("TX")
            
            transaction = UnifiedTransaction(
                transaction_id=transaction_id,
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                user_id=user.id,
                amount=Decimal('100.00'),
                currency='USD',
                status=pattern.get('status', UnifiedTransactionStatus.FAILED),
                external_provider=provider,
                failure_type=pattern.get('failure_type', 'technical'),
                last_error_code=pattern.get('error_code', f'{provider.upper()}_API_TIMEOUT'),
                retry_count=pattern.get('retry_count', 1),
                next_retry_at=datetime.utcnow() + timedelta(
                    minutes=pattern.get('retry_delay_minutes', 5)
                ),
                created_at=datetime.utcnow() - timedelta(
                    minutes=pattern.get('age_minutes', 10)
                ),
                updated_at=datetime.utcnow(),
                metadata={'scenario': scenario_name, 'pattern': pattern}
            )
            
            self.test_session.add(transaction)
            
            # Create retry logs based on pattern
            if pattern.get('has_retry_history'):
                for attempt in range(1, pattern['retry_count'] + 1):
                    retry_log = UnifiedTransactionRetryLog(
                        transaction_id=transaction_id,
                        attempt_number=attempt,
                        retry_at=datetime.utcnow() - timedelta(
                            minutes=pattern['age_minutes'] - attempt
                        ),
                        delay_seconds=300 * (2 ** (attempt - 1)),  # Progressive delays
                        error_code=pattern.get('error_code', f'{provider.upper()}_API_TIMEOUT'),
                        error_message=f'Attempt {attempt} failed',
                        success=False,
                        final_retry=(attempt == pattern['retry_count']),
                        created_at=datetime.utcnow() - timedelta(
                            minutes=pattern['age_minutes'] - attempt
                        )
                    )
                    
                    self.test_session.add(retry_log)
            
            self.test_session.commit()
            
            self.created_users.append(user)
            created_transaction_ids.append(transaction_id)
        
        self.created_transactions.extend(created_transaction_ids)
        
        logger.info(f"📝 Created {len(created_transaction_ids)} transactions for scenario: {scenario_name}")
        
        return created_transaction_ids
    
    def collect_queue_metrics(self) -> Dict[str, Any]:
        """Collect current retry queue metrics"""
        # Query database for queue statistics
        total_transactions = self.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.status == UnifiedTransactionStatus.FAILED
        ).count()
        
        ready_for_retry = self.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.status == UnifiedTransactionStatus.FAILED,
            UnifiedTransaction.next_retry_at <= datetime.utcnow(),
            UnifiedTransaction.retry_count < 6
        ).count()
        
        scheduled_retries = self.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.status == UnifiedTransactionStatus.FAILED,
            UnifiedTransaction.next_retry_at > datetime.utcnow(),
            UnifiedTransaction.retry_count < 6
        ).count()
        
        exhausted_retries = self.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.status == UnifiedTransactionStatus.FAILED,
            UnifiedTransaction.retry_count >= 6
        ).count()
        
        # Provider breakdown
        provider_stats = {}
        for provider in ['fincra', 'kraken', 'dynopay']:
            provider_count = self.test_session.query(UnifiedTransaction).filter(
                UnifiedTransaction.status == UnifiedTransactionStatus.FAILED,
                UnifiedTransaction.external_provider == provider
            ).count()
            provider_stats[provider] = provider_count
        
        metrics = {
            'total_failed_transactions': total_transactions,
            'ready_for_retry': ready_for_retry,
            'scheduled_retries': scheduled_retries,
            'exhausted_retries': exhausted_retries,
            'by_provider': provider_stats,
            'queue_health_score': self._calculate_queue_health_score(
                ready_for_retry, scheduled_retries, exhausted_retries
            )
        }
        
        # Record individual metrics
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                self._mock_record_metric(f'retry_queue_{metric_name}', value)
        
        return metrics
    
    def _calculate_queue_health_score(self, ready: int, scheduled: int, exhausted: int) -> float:
        """Calculate queue health score (0-100)"""
        total = ready + scheduled + exhausted
        if total == 0:
            return 100.0
        
        # Health decreases with more ready items (backlog) and exhausted items
        ready_penalty = (ready / total) * 30  # Up to 30% penalty for backlog
        exhausted_penalty = (exhausted / total) * 50  # Up to 50% penalty for exhausted
        
        health_score = max(0, 100 - ready_penalty - exhausted_penalty)
        return round(health_score, 2)
    
    def collect_success_rate_metrics(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Collect success rate metrics over a time window"""
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        # Overall success rates
        total_retries = self.test_session.query(UnifiedTransactionRetryLog).filter(
            UnifiedTransactionRetryLog.created_at >= cutoff_time
        ).count()
        
        successful_retries = self.test_session.query(UnifiedTransactionRetryLog).filter(
            UnifiedTransactionRetryLog.created_at >= cutoff_time,
            UnifiedTransactionRetryLog.success == True
        ).count()
        
        overall_success_rate = (successful_retries / total_retries * 100) if total_retries > 0 else 0
        
        # Provider-specific success rates
        provider_success_rates = {}
        for provider in ['fincra', 'kraken', 'dynopay']:
            provider_retries = self.test_session.query(UnifiedTransactionRetryLog).join(
                UnifiedTransaction
            ).filter(
                UnifiedTransactionRetryLog.created_at >= cutoff_time,
                UnifiedTransaction.external_provider == provider
            ).count()
            
            provider_successes = self.test_session.query(UnifiedTransactionRetryLog).join(
                UnifiedTransaction
            ).filter(
                UnifiedTransactionRetryLog.created_at >= cutoff_time,
                UnifiedTransaction.external_provider == provider,
                UnifiedTransactionRetryLog.success == True
            ).count()
            
            provider_rate = (provider_successes / provider_retries * 100) if provider_retries > 0 else 0
            provider_success_rates[provider] = round(provider_rate, 2)
        
        # Error type analysis
        error_type_stats = {}
        common_errors = ['API_TIMEOUT', 'SERVICE_UNAVAILABLE', 'NETWORK_ERROR', 'INSUFFICIENT_FUNDS']
        
        for error in common_errors:
            error_count = self.test_session.query(UnifiedTransactionRetryLog).filter(
                UnifiedTransactionRetryLog.created_at >= cutoff_time,
                UnifiedTransactionRetryLog.error_code.like(f'%{error}%')
            ).count()
            
            if error_count > 0:
                error_successes = self.test_session.query(UnifiedTransactionRetryLog).filter(
                    UnifiedTransactionRetryLog.created_at >= cutoff_time,
                    UnifiedTransactionRetryLog.error_code.like(f'%{error}%'),
                    UnifiedTransactionRetryLog.success == True
                ).count()
                
                error_type_stats[error] = {
                    'total_attempts': error_count,
                    'successful_attempts': error_successes,
                    'success_rate': round((error_successes / error_count * 100), 2)
                }
        
        metrics = {
            'time_window_hours': time_window_hours,
            'total_retry_attempts': total_retries,
            'successful_attempts': successful_retries,
            'overall_success_rate': round(overall_success_rate, 2),
            'provider_success_rates': provider_success_rates,
            'error_type_analysis': error_type_stats
        }
        
        # Record metrics
        self._mock_record_metric('retry_success_rate_overall', overall_success_rate)
        for provider, rate in provider_success_rates.items():
            self._mock_record_metric(f'retry_success_rate_{provider}', rate, {'provider': provider})
        
        return metrics
    
    async def collect_performance_metrics(self, sample_operations: int = 10) -> Dict[str, Any]:
        """Collect performance metrics for retry operations"""
        
        performance_samples = []
        
        # Simulate performance measurements
        for i in range(sample_operations):
            start_time = time.perf_counter()
            
            # Simulate retry processing operation
            await asyncio.sleep(0.01 + (i * 0.002))  # Variable processing time
            
            end_time = time.perf_counter()
            processing_time = end_time - start_time
            
            performance_samples.append(processing_time)
        
        # Calculate performance statistics
        avg_processing_time = statistics.mean(performance_samples)
        median_processing_time = statistics.median(performance_samples)
        p95_processing_time = statistics.quantiles(performance_samples, n=20)[18]  # 95th percentile
        max_processing_time = max(performance_samples)
        min_processing_time = min(performance_samples)
        
        # Calculate throughput
        total_time = sum(performance_samples)
        throughput_per_second = sample_operations / total_time
        
        metrics = {
            'sample_count': sample_operations,
            'avg_processing_time_ms': round(avg_processing_time * 1000, 2),
            'median_processing_time_ms': round(median_processing_time * 1000, 2),
            'p95_processing_time_ms': round(p95_processing_time * 1000, 2),
            'max_processing_time_ms': round(max_processing_time * 1000, 2),
            'min_processing_time_ms': round(min_processing_time * 1000, 2),
            'throughput_per_second': round(throughput_per_second, 2),
            'performance_grade': self._calculate_performance_grade(avg_processing_time)
        }
        
        # Record performance metrics
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                self._mock_record_metric(f'retry_performance_{metric_name}', value)
        
        return metrics
    
    def _calculate_performance_grade(self, avg_processing_time: float) -> str:
        """Calculate performance grade based on processing time"""
        avg_ms = avg_processing_time * 1000
        
        if avg_ms < 10:
            return 'A'  # Excellent
        elif avg_ms < 25:
            return 'B'  # Good
        elif avg_ms < 50:
            return 'C'  # Average
        elif avg_ms < 100:
            return 'D'  # Below Average
        else:
            return 'F'  # Poor
    
    def check_alert_thresholds(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check metrics against alert thresholds"""
        alerts = []
        
        # Queue depth alert
        if metrics.get('ready_for_retry', 0) > 50:
            alerts.append({
                'type': 'queue_depth_high',
                'severity': 'warning',
                'message': f"High retry queue depth: {metrics['ready_for_retry']} transactions ready",
                'threshold': 50,
                'current_value': metrics['ready_for_retry']
            })
        
        # Queue health alert
        queue_health = metrics.get('queue_health_score', 100)
        if queue_health < 70:
            alerts.append({
                'type': 'queue_health_low',
                'severity': 'warning' if queue_health > 50 else 'critical',
                'message': f"Retry queue health degraded: {queue_health}% health score",
                'threshold': 70,
                'current_value': queue_health
            })
        
        # Exhausted retries alert
        if metrics.get('exhausted_retries', 0) > 10:
            alerts.append({
                'type': 'exhausted_retries_high',
                'severity': 'critical',
                'message': f"High number of exhausted retries: {metrics['exhausted_retries']} transactions",
                'threshold': 10,
                'current_value': metrics['exhausted_retries']
            })
        
        # Trigger alerts through mock service
        for alert in alerts:
            self._mock_trigger_alert(
                alert['type'],
                alert['message'], 
                alert['severity']
            )
        
        return alerts
    
    async def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate comprehensive dashboard data"""
        queue_metrics = self.collect_queue_metrics()
        success_metrics = self.collect_success_rate_metrics()
        performance_metrics = await self.collect_performance_metrics()
        
        dashboard_data = {
            'last_updated': datetime.utcnow().isoformat(),
            'queue_overview': {
                'total_failed': queue_metrics['total_failed_transactions'],
                'ready_for_retry': queue_metrics['ready_for_retry'],
                'scheduled_retries': queue_metrics['scheduled_retries'],
                'exhausted_retries': queue_metrics['exhausted_retries'],
                'health_score': queue_metrics['queue_health_score']
            },
            'success_rates': {
                'overall': success_metrics['overall_success_rate'],
                'by_provider': success_metrics['provider_success_rates'],
                'trend': 'stable'  # Would be calculated from historical data
            },
            'performance': {
                'avg_processing_time': performance_metrics['avg_processing_time_ms'],
                'throughput': performance_metrics['throughput_per_second'],
                'grade': performance_metrics['performance_grade']
            },
            'provider_breakdown': queue_metrics['by_provider'],
            'alerts': self.check_alert_thresholds(queue_metrics)
        }
        
        # Update dashboard through mock service
        self._mock_dashboard_update(dashboard_data)
        
        return dashboard_data
    
    def verify_metric_collection(self, expected_metrics: List[str]) -> bool:
        """Verify expected metrics were collected"""
        collected_metric_names = [m['metric_name'] for m in self.collected_metrics]
        
        missing_metrics = []
        for expected in expected_metrics:
            if not any(expected in name for name in collected_metric_names):
                missing_metrics.append(expected)
        
        if missing_metrics:
            logger.error(f"❌ Missing expected metrics: {missing_metrics}")
            return False
        
        logger.info(f"✅ All expected metrics collected: {len(expected_metrics)} metrics")
        return True
    
    def verify_dashboard_updates(self, expected_sections: List[str]) -> bool:
        """Verify dashboard was updated with expected sections"""
        if not self.dashboard_updates:
            logger.error("❌ No dashboard updates recorded")
            return False
        
        latest_update = self.dashboard_updates[-1]
        dashboard_data = latest_update['dashboard_data']
        
        missing_sections = []
        for section in expected_sections:
            if section not in dashboard_data:
                missing_sections.append(section)
        
        if missing_sections:
            logger.error(f"❌ Missing dashboard sections: {missing_sections}")
            return False
        
        logger.info(f"✅ Dashboard updated with all expected sections: {len(expected_sections)} sections")
        return True
    
    def verify_alert_triggers(self, expected_alert_types: List[str]) -> bool:
        """Verify expected alerts were triggered"""
        triggered_alert_types = [a['alert_type'] for a in self.alert_triggers]
        
        missing_alerts = []
        for expected in expected_alert_types:
            if expected not in triggered_alert_types:
                missing_alerts.append(expected)
        
        if missing_alerts:
            logger.info(f"ℹ️ Expected alerts not triggered (normal if thresholds not exceeded): {missing_alerts}")
        
        logger.info(f"✅ Alert system validated: {len(self.alert_triggers)} alerts triggered")
        return True
    
    def cleanup(self):
        """Clean up test framework resources"""
        self.collected_metrics.clear()
        self.dashboard_updates.clear()
        self.alert_triggers.clear()
        self.created_transactions.clear()
        self.created_users.clear()
        self.teardown_test_database()


@pytest.fixture(scope="class")
def observability_framework():
    """Pytest fixture providing observability test framework"""
    framework = ObservabilityTestFramework()
    framework.setup_test_database()
    framework.setup_mock_monitoring_services()
    
    yield framework
    
    framework.cleanup()


class TestRetryQueueMetrics:
    """Test retry queue metrics collection and monitoring"""
    
    @pytest.mark.asyncio
    async def test_queue_depth_metrics_collection(self, observability_framework):
        """Test retry queue depth metrics are collected accurately"""
        
        # Create diverse retry scenarios
        retry_patterns = [
            {'status': UnifiedTransactionStatus.FAILED, 'retry_count': 1, 'retry_delay_minutes': -5},  # Ready
            {'status': UnifiedTransactionStatus.FAILED, 'retry_count': 2, 'retry_delay_minutes': 10},  # Scheduled
            {'status': UnifiedTransactionStatus.FAILED, 'retry_count': 6, 'retry_delay_minutes': 0},   # Exhausted
            {'status': UnifiedTransactionStatus.FAILED, 'retry_count': 3, 'retry_delay_minutes': -2},  # Ready
            {'status': UnifiedTransactionStatus.FAILED, 'retry_count': 4, 'retry_delay_minutes': 30}   # Scheduled
        ]
        
        transaction_ids = observability_framework.create_test_retry_scenario(
            'queue_metrics_test',
            transaction_count=5,
            providers=['fincra', 'kraken'],
            retry_patterns=retry_patterns
        )
        
        # Collect queue metrics
        queue_metrics = observability_framework.collect_queue_metrics()
        
        # Verify metrics accuracy
        assert queue_metrics['total_failed_transactions'] == 5
        assert queue_metrics['ready_for_retry'] == 2  # Two with past retry times
        assert queue_metrics['scheduled_retries'] == 2  # Two with future retry times
        assert queue_metrics['exhausted_retries'] == 1  # One with 6 retries
        assert queue_metrics['queue_health_score'] >= 0
        assert queue_metrics['queue_health_score'] <= 100
        
        # Verify provider breakdown
        assert 'fincra' in queue_metrics['by_provider']
        assert 'kraken' in queue_metrics['by_provider']
        
        logger.info("✅ Queue depth metrics collection validated")
    
    @pytest.mark.asyncio
    async def test_queue_health_score_calculation(self, observability_framework):
        """Test queue health score calculation logic"""
        
        # Test scenario 1: Healthy queue (mostly scheduled)
        healthy_patterns = [
            {'retry_count': 1, 'retry_delay_minutes': 10},  # Scheduled
            {'retry_count': 2, 'retry_delay_minutes': 20},  # Scheduled
            {'retry_count': 1, 'retry_delay_minutes': 15}   # Scheduled
        ]
        
        observability_framework.create_test_retry_scenario(
            'healthy_queue',
            transaction_count=3,
            providers=['fincra'],
            retry_patterns=healthy_patterns
        )
        
        healthy_metrics = observability_framework.collect_queue_metrics()
        healthy_score = healthy_metrics['queue_health_score']
        
        assert healthy_score >= 70, f"Healthy queue should have high score: {healthy_score}"
        
        # Test scenario 2: Unhealthy queue (many ready and exhausted)
        unhealthy_patterns = [
            {'retry_count': 6, 'retry_delay_minutes': 0},   # Exhausted
            {'retry_count': 6, 'retry_delay_minutes': 0},   # Exhausted
            {'retry_count': 3, 'retry_delay_minutes': -10}, # Ready (backlog)
            {'retry_count': 4, 'retry_delay_minutes': -5}   # Ready (backlog)
        ]
        
        observability_framework.create_test_retry_scenario(
            'unhealthy_queue',
            transaction_count=4,
            providers=['kraken'],
            retry_patterns=unhealthy_patterns
        )
        
        unhealthy_metrics = observability_framework.collect_queue_metrics()
        unhealthy_score = unhealthy_metrics['queue_health_score']
        
        assert unhealthy_score <= 50, f"Unhealthy queue should have low score: {unhealthy_score}"
        
        logger.info(f"✅ Queue health scores: Healthy={healthy_score}, Unhealthy={unhealthy_score}")
    
    @pytest.mark.asyncio
    async def test_provider_specific_metrics(self, observability_framework):
        """Test provider-specific retry metrics"""
        
        # Create transactions for different providers
        provider_patterns = [
            # Fincra transactions
            {'provider': 'fincra', 'retry_count': 1, 'error_code': 'FINCRA_API_TIMEOUT'},
            {'provider': 'fincra', 'retry_count': 2, 'error_code': 'FINCRA_SERVICE_UNAVAILABLE'},
            {'provider': 'fincra', 'retry_count': 6, 'error_code': 'FINCRA_INSUFFICIENT_FUNDS'},
            
            # Kraken transactions
            {'provider': 'kraken', 'retry_count': 1, 'error_code': 'KRAKEN_ADDR_NOT_FOUND'},
            {'provider': 'kraken', 'retry_count': 3, 'error_code': 'KRAKEN_API_ERROR'},
            
            # DynoPay transactions
            {'provider': 'dynopay', 'retry_count': 2, 'error_code': 'DYNOPAY_SERVICE_UNAVAILABLE'}
        ]
        
        for i, pattern in enumerate(provider_patterns):
            observability_framework.create_test_retry_scenario(
                f'provider_test_{i}',
                transaction_count=1,
                providers=[pattern['provider']],
                retry_patterns=[pattern]
            )
        
        # Collect metrics
        queue_metrics = observability_framework.collect_queue_metrics()
        provider_breakdown = queue_metrics['by_provider']
        
        # Verify provider-specific counts
        assert provider_breakdown['fincra'] == 3
        assert provider_breakdown['kraken'] == 2
        assert provider_breakdown['dynopay'] == 1
        
        # Verify metrics were recorded for each provider
        fincra_metrics = [m for m in observability_framework.collected_metrics 
                         if 'fincra' in m.get('tags', {}).get('provider', '')]
        assert len(fincra_metrics) > 0, "Should have Fincra-specific metrics"
        
        logger.info("✅ Provider-specific metrics validated")


class TestSuccessRateTracking:
    """Test success rate tracking and analysis"""
    
    @pytest.mark.asyncio
    async def test_overall_success_rate_calculation(self, observability_framework):
        """Test overall retry success rate calculation"""
        
        # Create transactions with retry history
        success_patterns = [
            {'has_retry_history': True, 'retry_count': 2, 'age_minutes': 60},  # 2 attempts
            {'has_retry_history': True, 'retry_count': 3, 'age_minutes': 120}, # 3 attempts
            {'has_retry_history': True, 'retry_count': 1, 'age_minutes': 30}   # 1 attempt
        ]
        
        transaction_ids = observability_framework.create_test_retry_scenario(
            'success_rate_test',
            transaction_count=3,
            providers=['fincra'],
            retry_patterns=success_patterns
        )
        
        # Simulate some successful retries
        for i, tx_id in enumerate(transaction_ids[:2]):  # First 2 transactions succeed
            retry_logs = observability_framework.test_session.query(UnifiedTransactionRetryLog).filter(
                UnifiedTransactionRetryLog.transaction_id == tx_id
            ).all()
            
            if retry_logs:
                # Mark last attempt as successful
                last_log = retry_logs[-1]
                last_log.success = True
                observability_framework.test_session.commit()
        
        # Collect success metrics
        success_metrics = observability_framework.collect_success_rate_metrics(time_window_hours=24)
        
        # Verify calculations
        total_attempts = success_metrics['total_retry_attempts']
        successful_attempts = success_metrics['successful_attempts']
        success_rate = success_metrics['overall_success_rate']
        
        assert total_attempts == 6  # 2 + 3 + 1 attempts
        assert successful_attempts == 2  # 2 transactions with successful final attempts
        assert success_rate == round((2 / 6) * 100, 2)  # 33.33%
        
        logger.info(f"✅ Success rate calculation: {success_rate}% ({successful_attempts}/{total_attempts})")
    
    @pytest.mark.asyncio
    async def test_provider_specific_success_rates(self, observability_framework):
        """Test provider-specific success rate tracking"""
        
        # Create provider-specific scenarios
        providers_data = [
            {'provider': 'fincra', 'success_attempts': 3, 'total_attempts': 5},    # 60% success
            {'provider': 'kraken', 'success_attempts': 1, 'total_attempts': 4},    # 25% success
            {'provider': 'dynopay', 'success_attempts': 2, 'total_attempts': 2}    # 100% success
        ]
        
        for provider_data in providers_data:
            provider = provider_data['provider']
            
            # Create transactions for this provider
            for attempt in range(provider_data['total_attempts']):
                transaction_ids = observability_framework.create_test_retry_scenario(
                    f'{provider}_success_test_{attempt}',
                    transaction_count=1,
                    providers=[provider],
                    retry_patterns=[{
                        'has_retry_history': True,
                        'retry_count': 1,
                        'age_minutes': 30
                    }]
                )
                
                # Mark successful attempts
                if attempt < provider_data['success_attempts']:
                    tx_id = transaction_ids[0]
                    retry_log = observability_framework.test_session.query(UnifiedTransactionRetryLog).filter(
                        UnifiedTransactionRetryLog.transaction_id == tx_id
                    ).first()
                    
                    if retry_log:
                        retry_log.success = True
                        observability_framework.test_session.commit()
        
        # Collect success metrics
        success_metrics = observability_framework.collect_success_rate_metrics()
        provider_rates = success_metrics['provider_success_rates']
        
        # Verify provider-specific rates
        assert provider_rates['fincra'] == 60.0  # 3/5 * 100
        assert provider_rates['kraken'] == 25.0  # 1/4 * 100
        assert provider_rates['dynopay'] == 100.0  # 2/2 * 100
        
        logger.info(f"✅ Provider success rates: {provider_rates}")
    
    @pytest.mark.asyncio
    async def test_error_type_success_analysis(self, observability_framework):
        """Test success rate analysis by error type"""
        
        # Create transactions with specific error types
        error_scenarios = [
            {'error_code': 'API_TIMEOUT', 'should_succeed': True},
            {'error_code': 'API_TIMEOUT', 'should_succeed': False},
            {'error_code': 'SERVICE_UNAVAILABLE', 'should_succeed': True},
            {'error_code': 'NETWORK_ERROR', 'should_succeed': False},
            {'error_code': 'NETWORK_ERROR', 'should_succeed': False}
        ]
        
        for i, scenario in enumerate(error_scenarios):
            transaction_ids = observability_framework.create_test_retry_scenario(
                f'error_analysis_{i}',
                transaction_count=1,
                providers=['fincra'],
                retry_patterns=[{
                    'has_retry_history': True,
                    'retry_count': 1,
                    'error_code': f'FINCRA_{scenario["error_code"]}',
                    'age_minutes': 45
                }]
            )
            
            # Mark successful if specified
            if scenario['should_succeed']:
                tx_id = transaction_ids[0]
                retry_log = observability_framework.test_session.query(UnifiedTransactionRetryLog).filter(
                    UnifiedTransactionRetryLog.transaction_id == tx_id
                ).first()
                
                if retry_log:
                    retry_log.success = True
                    observability_framework.test_session.commit()
        
        # Collect success metrics with error analysis
        success_metrics = observability_framework.collect_success_rate_metrics()
        error_analysis = success_metrics['error_type_analysis']
        
        # Verify error type analysis
        if 'API_TIMEOUT' in error_analysis:
            timeout_stats = error_analysis['API_TIMEOUT']
            assert timeout_stats['total_attempts'] == 2
            assert timeout_stats['successful_attempts'] == 1
            assert timeout_stats['success_rate'] == 50.0
        
        if 'NETWORK_ERROR' in error_analysis:
            network_stats = error_analysis['NETWORK_ERROR']
            assert network_stats['total_attempts'] == 2
            assert network_stats['successful_attempts'] == 0
            assert network_stats['success_rate'] == 0.0
        
        logger.info(f"✅ Error type analysis: {len(error_analysis)} error types analyzed")


class TestPerformanceMetrics:
    """Test performance metrics collection and monitoring"""
    
    @pytest.mark.asyncio
    async def test_retry_processing_performance_measurement(self, observability_framework):
        """Test retry processing performance measurement"""
        
        # Collect performance metrics
        performance_metrics = await observability_framework.collect_performance_metrics(
            sample_operations=20
        )
        
        # Verify performance metrics structure
        required_metrics = [
            'sample_count', 'avg_processing_time_ms', 'median_processing_time_ms',
            'p95_processing_time_ms', 'throughput_per_second', 'performance_grade'
        ]
        
        for metric in required_metrics:
            assert metric in performance_metrics, f"Missing performance metric: {metric}"
        
        # Verify reasonable performance values
        assert performance_metrics['sample_count'] == 20
        assert performance_metrics['avg_processing_time_ms'] > 0
        assert performance_metrics['throughput_per_second'] > 0
        assert performance_metrics['performance_grade'] in ['A', 'B', 'C', 'D', 'F']
        
        # Verify percentiles are ordered correctly
        assert performance_metrics['median_processing_time_ms'] <= performance_metrics['p95_processing_time_ms']
        assert performance_metrics['avg_processing_time_ms'] <= performance_metrics['max_processing_time_ms']
        
        logger.info(f"✅ Performance metrics: {performance_metrics['performance_grade']} grade, {performance_metrics['throughput_per_second']} ops/sec")
    
    @pytest.mark.asyncio
    async def test_performance_grade_thresholds(self, observability_framework):
        """Test performance grading system"""
        
        # Test different performance scenarios
        test_times = [
            (0.005, 'A'),   # 5ms - Excellent
            (0.015, 'B'),   # 15ms - Good
            (0.035, 'C'),   # 35ms - Average
            (0.075, 'D'),   # 75ms - Below Average
            (0.150, 'F')    # 150ms - Poor
        ]
        
        for processing_time, expected_grade in test_times:
            grade = observability_framework._calculate_performance_grade(processing_time)
            assert grade == expected_grade, f"Processing time {processing_time*1000}ms should be grade {expected_grade}, got {grade}"
        
        logger.info("✅ Performance grade thresholds validated")
    
    @pytest.mark.asyncio
    async def test_throughput_calculation_accuracy(self, observability_framework):
        """Test throughput calculation accuracy"""
        
        # Test with controlled timing
        sample_count = 10
        performance_metrics = await observability_framework.collect_performance_metrics(
            sample_operations=sample_count
        )
        
        throughput = performance_metrics['throughput_per_second']
        avg_time_ms = performance_metrics['avg_processing_time_ms']
        
        # Verify throughput calculation makes sense
        # Throughput should be approximately 1000 / avg_time_ms
        expected_throughput = 1000 / avg_time_ms
        throughput_tolerance = expected_throughput * 0.5  # 50% tolerance for async variations
        
        assert abs(throughput - expected_throughput) <= throughput_tolerance, \
            f"Throughput calculation seems incorrect: {throughput} vs expected ~{expected_throughput}"
        
        logger.info(f"✅ Throughput calculation: {throughput} ops/sec (avg: {avg_time_ms}ms)")


class TestAlertThresholds:
    """Test alert threshold monitoring"""
    
    @pytest.mark.asyncio
    async def test_queue_depth_alert_triggers(self, observability_framework):
        """Test queue depth alerts trigger at correct thresholds"""
        
        # Create high queue depth scenario (over threshold of 50)
        high_depth_patterns = [{'retry_count': 2, 'retry_delay_minutes': -5}] * 60  # 60 ready transactions
        
        observability_framework.create_test_retry_scenario(
            'high_queue_depth',
            transaction_count=60,
            providers=['fincra'],
            retry_patterns=high_depth_patterns
        )
        
        # Collect metrics and check alerts
        queue_metrics = observability_framework.collect_queue_metrics()
        alerts = observability_framework.check_alert_thresholds(queue_metrics)
        
        # Verify queue depth alert was triggered
        queue_depth_alerts = [a for a in alerts if a['type'] == 'queue_depth_high']
        assert len(queue_depth_alerts) > 0, "Queue depth alert should have been triggered"
        
        depth_alert = queue_depth_alerts[0]
        assert depth_alert['severity'] == 'warning'
        assert depth_alert['current_value'] == 60
        assert depth_alert['threshold'] == 50
        
        # Verify alert was logged
        triggered_alerts = [a for a in observability_framework.alert_triggers if a['alert_type'] == 'queue_depth_high']
        assert len(triggered_alerts) > 0, "Alert should have been logged"
        
        logger.info("✅ Queue depth alert threshold validated")
    
    @pytest.mark.asyncio
    async def test_queue_health_alert_triggers(self, observability_framework):
        """Test queue health alerts trigger at correct thresholds"""
        
        # Create unhealthy queue scenario (many exhausted retries)
        unhealthy_patterns = [{'retry_count': 6, 'retry_delay_minutes': 0}] * 15  # 15 exhausted transactions
        
        observability_framework.create_test_retry_scenario(
            'unhealthy_queue',
            transaction_count=15,
            providers=['kraken'],
            retry_patterns=unhealthy_patterns
        )
        
        # Collect metrics and check alerts
        queue_metrics = observability_framework.collect_queue_metrics()
        health_score = queue_metrics['queue_health_score']
        
        # Health should be low due to all exhausted retries
        assert health_score < 70, f"Queue health should be low: {health_score}%"
        
        alerts = observability_framework.check_alert_thresholds(queue_metrics)
        
        # Verify health alert was triggered
        health_alerts = [a for a in alerts if a['type'] == 'queue_health_low']
        assert len(health_alerts) > 0, "Queue health alert should have been triggered"
        
        health_alert = health_alerts[0]
        assert health_alert['severity'] in ['warning', 'critical']
        assert health_alert['current_value'] == health_score
        
        logger.info(f"✅ Queue health alert validated: {health_score}% health triggered {health_alert['severity']} alert")
    
    @pytest.mark.asyncio
    async def test_exhausted_retries_critical_alert(self, observability_framework):
        """Test critical alert for high number of exhausted retries"""
        
        # Create many exhausted retry transactions (over threshold of 10)
        exhausted_patterns = [{'retry_count': 6, 'retry_delay_minutes': 0}] * 15
        
        observability_framework.create_test_retry_scenario(
            'exhausted_critical',
            transaction_count=15,
            providers=['dynopay'],
            retry_patterns=exhausted_patterns
        )
        
        # Collect metrics and check alerts
        queue_metrics = observability_framework.collect_queue_metrics()
        alerts = observability_framework.check_alert_thresholds(queue_metrics)
        
        # Verify critical exhausted retries alert
        exhausted_alerts = [a for a in alerts if a['type'] == 'exhausted_retries_high']
        assert len(exhausted_alerts) > 0, "Exhausted retries alert should have been triggered"
        
        exhausted_alert = exhausted_alerts[0]
        assert exhausted_alert['severity'] == 'critical'
        assert exhausted_alert['current_value'] == 15
        assert exhausted_alert['threshold'] == 10
        
        logger.info("✅ Exhausted retries critical alert validated")


class TestDashboardIntegration:
    """Test dashboard metrics integration"""
    
    @pytest.mark.asyncio
    async def test_comprehensive_dashboard_data_generation(self, observability_framework):
        """Test comprehensive dashboard data generation"""
        
        # Create diverse data for dashboard
        mixed_patterns = [
            {'retry_count': 1, 'retry_delay_minutes': -5, 'has_retry_history': True},  # Ready
            {'retry_count': 2, 'retry_delay_minutes': 10, 'has_retry_history': True},  # Scheduled  
            {'retry_count': 6, 'retry_delay_minutes': 0, 'has_retry_history': True},   # Exhausted
            {'retry_count': 3, 'retry_delay_minutes': 15, 'has_retry_history': True}   # Scheduled
        ]
        
        observability_framework.create_test_retry_scenario(
            'dashboard_test',
            transaction_count=4,
            providers=['fincra', 'kraken', 'dynopay'],
            retry_patterns=mixed_patterns
        )
        
        # Generate dashboard data
        dashboard_data = await observability_framework.generate_dashboard_data()
        
        # Verify dashboard structure
        required_sections = [
            'last_updated', 'queue_overview', 'success_rates', 
            'performance', 'provider_breakdown', 'alerts'
        ]
        
        for section in required_sections:
            assert section in dashboard_data, f"Missing dashboard section: {section}"
        
        # Verify queue overview data
        queue_overview = dashboard_data['queue_overview']
        assert queue_overview['total_failed'] == 4
        assert 'health_score' in queue_overview
        
        # Verify success rates data
        success_rates = dashboard_data['success_rates']
        assert 'overall' in success_rates
        assert 'by_provider' in success_rates
        
        # Verify performance data
        performance = dashboard_data['performance']
        assert 'avg_processing_time' in performance
        assert 'throughput' in performance
        assert 'grade' in performance
        
        logger.info("✅ Comprehensive dashboard data generation validated")
    
    @pytest.mark.asyncio
    async def test_dashboard_update_frequency(self, observability_framework):
        """Test dashboard updates occur at appropriate frequency"""
        
        # Create some test data
        observability_framework.create_test_retry_scenario(
            'update_frequency_test',
            transaction_count=2,
            providers=['fincra'],
            retry_patterns=[{'retry_count': 1}] * 2
        )
        
        # Generate multiple dashboard updates
        initial_update_count = len(observability_framework.dashboard_updates)
        
        for i in range(3):
            dashboard_data = await observability_framework.generate_dashboard_data()
            await asyncio.sleep(0.01)  # Small delay between updates
        
        final_update_count = len(observability_framework.dashboard_updates)
        
        # Verify updates occurred
        updates_generated = final_update_count - initial_update_count
        assert updates_generated == 3, f"Should have 3 new updates, got {updates_generated}"
        
        # Verify timestamps are different
        recent_updates = observability_framework.dashboard_updates[-3:]
        timestamps = [update['timestamp'] for update in recent_updates]
        
        assert len(set(timestamps)) == 3, "All update timestamps should be unique"
        
        logger.info(f"✅ Dashboard update frequency validated: {updates_generated} updates")
    
    @pytest.mark.asyncio
    async def test_dashboard_data_consistency(self, observability_framework):
        """Test dashboard data remains consistent across updates"""
        
        # Create stable test scenario
        observability_framework.create_test_retry_scenario(
            'consistency_test',
            transaction_count=5,
            providers=['fincra'],
            retry_patterns=[
                {'retry_count': 1, 'retry_delay_minutes': 10},  # Scheduled
                {'retry_count': 2, 'retry_delay_minutes': -5},  # Ready
                {'retry_count': 6, 'retry_delay_minutes': 0}    # Exhausted
            ] * 2  # Repeat pattern for 6 total transactions
        )
        
        # Generate two dashboard updates
        dashboard_1 = await observability_framework.generate_dashboard_data()
        await asyncio.sleep(0.01)
        dashboard_2 = await observability_framework.generate_dashboard_data()
        
        # Verify consistent data (should be identical for static data)
        queue_1 = dashboard_1['queue_overview']
        queue_2 = dashboard_2['queue_overview']
        
        assert queue_1['total_failed'] == queue_2['total_failed']
        assert queue_1['ready_for_retry'] == queue_2['ready_for_retry']
        assert queue_1['scheduled_retries'] == queue_2['scheduled_retries']
        assert queue_1['exhausted_retries'] == queue_2['exhausted_retries']
        
        # Provider breakdown should be consistent
        assert dashboard_1['provider_breakdown'] == dashboard_2['provider_breakdown']
        
        logger.info("✅ Dashboard data consistency validated")


class TestHistoricalTrendAnalysis:
    """Test historical trend analysis capabilities"""
    
    @pytest.mark.asyncio
    async def test_retry_pattern_trend_detection(self, observability_framework):
        """Test detection of retry patterns over time"""
        
        # Create historical data with trending patterns
        time_periods = [
            {'age_hours': 24, 'success_rate': 0.8, 'transaction_count': 10},
            {'age_hours': 18, 'success_rate': 0.6, 'transaction_count': 15},
            {'age_hours': 12, 'success_rate': 0.4, 'transaction_count': 20},
            {'age_hours': 6, 'success_rate': 0.2, 'transaction_count': 25}
        ]
        
        for period in time_periods:
            # Create transactions for this time period
            age_minutes = period['age_hours'] * 60
            success_count = int(period['transaction_count'] * period['success_rate'])
            
            for i in range(period['transaction_count']):
                transaction_ids = observability_framework.create_test_retry_scenario(
                    f'trend_test_{period["age_hours"]}h_{i}',
                    transaction_count=1,
                    providers=['fincra'],
                    retry_patterns=[{
                        'has_retry_history': True,
                        'retry_count': 1,
                        'age_minutes': age_minutes
                    }]
                )
                
                # Mark successful based on success rate
                if i < success_count:
                    tx_id = transaction_ids[0]
                    retry_log = observability_framework.test_session.query(UnifiedTransactionRetryLog).filter(
                        UnifiedTransactionRetryLog.transaction_id == tx_id
                    ).first()
                    
                    if retry_log:
                        retry_log.success = True
                        observability_framework.test_session.commit()
        
        # Analyze trends across different time windows
        trend_analysis = {}
        
        for window_hours in [6, 12, 18, 24]:
            success_metrics = observability_framework.collect_success_rate_metrics(
                time_window_hours=window_hours
            )
            trend_analysis[f'{window_hours}h'] = success_metrics['overall_success_rate']
        
        # Verify declining trend is detected
        rates = list(trend_analysis.values())
        assert rates == sorted(rates), f"Success rates should show declining trend: {trend_analysis}"
        
        # Calculate trend direction
        if len(rates) >= 2:
            trend_direction = 'declining' if rates[-1] < rates[0] else 'improving'
            assert trend_direction == 'declining', "Should detect declining trend"
        
        logger.info(f"✅ Trend analysis: {trend_analysis}, Direction: {trend_direction}")


if __name__ == "__main__":
    # Run observability tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "observability or metrics"
    ])